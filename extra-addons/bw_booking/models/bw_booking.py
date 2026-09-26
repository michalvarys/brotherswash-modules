import hashlib
import logging
import re
from datetime import datetime

import pytz
import requests

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import format_datetime, plaintext2html

_logger = logging.getLogger(__name__)

BUSINESS_TZ = 'Europe/Prague'
# All service prices are maintained in CZK (",- Kč" everywhere)
BOOKING_CURRENCY = 'CZK'
META_GRAPH_URL = 'https://graph.facebook.com/v21.0/%s/events'

# Attribution keys accepted from the frontend (tracking.js) -> bw.booking field
TRACKING_FIELDS = {
    'gclid': 'gclid',
    'gbraid': 'gbraid',
    'wbraid': 'wbraid',
    'fbclid': 'fbclid',
    'fbc': 'fbc',
    'fbp': 'fbp',
    'landing_url': 'landing_url',
    'referrer': 'referrer',
}


class BwBooking(models.Model):
    _name = 'bw.booking'
    _description = 'Detailing Booking'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _order = 'create_date desc'

    name = fields.Char(compute='_compute_name', store=True)
    state = fields.Selection([
        ('pending', 'Awaiting confirmation'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('no_show', 'No-show'),
        ('cancelled', 'Cancelled'),
    ], default='pending', tracking=True, required=True)
    stage_id = fields.Many2one(
        'bw.booking.stage', string='Sloupec (board)', tracking=True, index=True, copy=False,
        group_expand='_read_group_stage_ids',
        default=lambda self: self.env['bw.booking.stage'].search([('booking_state', '=', 'pending')], limit=1),
    )
    mailed_stage_ids = fields.Many2many(
        'bw.booking.stage', 'bw_booking_mailed_stage_rel', 'booking_id', 'stage_id',
        string='E-mail už odeslán ve sloupcích', copy=False,
    )

    # Customer info
    customer_name = fields.Char(required=True, string='Jméno zákazníka')
    customer_email = fields.Char(required=True, string='Email')
    customer_phone = fields.Char(required=True, string='Telefon')
    customer_note = fields.Text(string='Poznámka zákazníka')

    # Vehicle
    vehicle_type_id = fields.Many2one('bw.vehicle.type', required=True, string='Typ vozidla')
    vehicle_info = fields.Char(string='Vozidlo (značka/model)')

    # Services
    service_ids = fields.Many2many('bw.service', string='Vybrané služby')
    line_ids = fields.One2many('bw.booking.line', 'booking_id', string='Položky')

    # Financials
    total_price = fields.Float(compute='_compute_total_price', store=True, string='Celková cena')
    is_price_approximate = fields.Boolean(
        compute='_compute_total_price', store=True,
        string='Orientační cena',
        help='True pokud alespoň jedna služba má prefix "od"',
    )

    # Preferred date/time (stored in UTC like every Odoo datetime)
    preferred_date = fields.Datetime(string='Preferovaný termín')

    # Language (set from website visitor language)
    lang = fields.Char(string='Jazyk', default='cs_CZ')
    website_id = fields.Many2one('website', string='Web', readonly=True)

    # CRM & Calendar links
    lead_id = fields.Many2one('crm.lead', string='CRM příležitost', readonly=True)
    calendar_event_id = fields.Many2one('calendar.event', string='Událost v kalendáři', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Kontakt', readonly=True)

    # Ad attribution (campaign_id / source_id / medium_id come from utm.mixin)
    ad_platform = fields.Selection([
        ('google', 'Google Ads'),
        ('meta', 'Meta (Facebook / Instagram)'),
        ('other', 'Jiná kampaň'),
        ('none', 'Bez reklamy'),
    ], string='Reklama', compute='_compute_ad_platform', store=True)
    gclid = fields.Char(string='Google gclid', readonly=True)
    gbraid = fields.Char(string='Google gbraid', readonly=True)
    wbraid = fields.Char(string='Google wbraid', readonly=True)
    fbclid = fields.Char(string='Meta fbclid', readonly=True)
    fbc = fields.Char(string='Meta fbc', readonly=True)
    fbp = fields.Char(string='Meta fbp', readonly=True)
    landing_url = fields.Char(string='Vstupní stránka', readonly=True)
    referrer = fields.Char(string='Odkud přišel (referrer)', readonly=True)
    client_ip = fields.Char(string='IP adresa', readonly=True)
    client_user_agent = fields.Char(string='Prohlížeč', readonly=True)
    tracking_event_id = fields.Char(
        string='ID události', compute='_compute_tracking_event_id',
        help='Shared event ID of the browser Pixel and the Conversions API (deduplication).',
    )
    meta_lead_sent = fields.Boolean(string='Lead odeslán do Meta CAPI', readonly=True, copy=False)
    meta_purchase_sent = fields.Boolean(string='Návštěva odeslána do Meta CAPI', readonly=True, copy=False)

    @api.depends('customer_name', 'create_date')
    def _compute_name(self):
        for rec in self:
            date_str = rec.create_date.strftime('%d.%m.%Y') if rec.create_date else 'Nový'
            rec.name = f"BWD-{rec.id or 'X'} {rec.customer_name or ''} ({date_str})"

    @api.depends('line_ids.price', 'line_ids.price_prefix')
    def _compute_total_price(self):
        for rec in self:
            rec.total_price = sum(rec.line_ids.mapped('price'))
            rec.is_price_approximate = any(rec.line_ids.mapped('price_prefix'))

    @api.depends('gclid', 'gbraid', 'wbraid', 'fbclid', 'fbc', 'source_id', 'medium_id', 'campaign_id')
    def _compute_ad_platform(self):
        for rec in self:
            source = (rec.source_id.name or '').lower()
            if rec.gclid or rec.gbraid or rec.wbraid or source in ('google', 'google ads', 'adwords'):
                rec.ad_platform = 'google'
            elif rec.fbclid or source in ('facebook', 'fb', 'instagram', 'ig', 'meta'):
                rec.ad_platform = 'meta'
            elif rec.campaign_id or rec.source_id or rec.medium_id:
                rec.ad_platform = 'other'
            else:
                rec.ad_platform = 'none'

    def _compute_tracking_event_id(self):
        for rec in self:
            rec.tracking_event_id = f"bwd-{rec.id}" if rec.id else False

    # ------------------------------------------------------------------
    # Website submission helpers
    # ------------------------------------------------------------------

    @api.model
    def _bw_parse_local_datetime(self, value):
        """datetime-local from the form is Prague wall time; Odoo stores UTC."""
        if not value:
            return False
        try:
            local_dt = datetime.strptime(value, '%Y-%m-%dT%H:%M')
        except ValueError:
            return False
        return pytz.timezone(BUSINESS_TZ).localize(local_dt).astimezone(pytz.utc).replace(tzinfo=None)

    @api.model
    def _bw_prepare_tracking_vals(self, tracking, httprequest=None):
        """Sanitised attribution values from tracking.js (+ request metadata)."""
        tracking = tracking if isinstance(tracking, dict) else {}
        vals = {}
        for key, fname in TRACKING_FIELDS.items():
            value = tracking.get(key)
            if value and isinstance(value, str):
                vals[fname] = value.strip()[:500]

        Utm = self.env['utm.mixin']
        source = (tracking.get('utm_source') or '').strip()
        medium = (tracking.get('utm_medium') or '').strip()
        campaign = (tracking.get('utm_campaign') or '').strip()
        # Ad clicks without utm_* parameters still get a readable source in CRM
        if not source and (vals.get('gclid') or vals.get('gbraid') or vals.get('wbraid')):
            source, medium = 'google', medium or 'cpc'
        elif not source and vals.get('fbclid'):
            source = 'facebook'
        if source:
            vals['source_id'] = Utm._find_or_create_record('utm.source', source[:100]).id
        if medium:
            vals['medium_id'] = Utm._find_or_create_record('utm.medium', medium[:100]).id
        if campaign:
            vals['campaign_id'] = Utm._find_or_create_record('utm.campaign', campaign[:100]).id

        if httprequest is not None:
            vals['client_ip'] = (httprequest.headers.get('X-Forwarded-For') or httprequest.remote_addr or '').split(',')[0].strip()
            vals['client_user_agent'] = (httprequest.headers.get('User-Agent') or '')[:500]
        return vals

    def _bw_tracking_payload(self):
        """Data for the browser-side conversion events (Pixel / gtag / dataLayer)."""
        self.ensure_one()
        return {
            'event_id': self.tracking_event_id,
            'booking_ref': f"BWD-{self.id}",
            'value': self.total_price,
            'currency': BOOKING_CURRENCY,
            'email': self.customer_email or '',
            'phone': self._bw_phone_e164() or '',
            'vehicle': self.vehicle_type_id.name or '',
            'items': [{
                'item_id': str(line.service_id.id),
                'item_name': line.service_id.name,
                'price': line.price,
                'quantity': 1,
            } for line in self.line_ids],
        }

    def _bw_phone_e164(self):
        digits = re.sub(r'\D', '', self.customer_phone or '')
        if not digits:
            return ''
        if (self.customer_phone or '').strip().startswith('+'):
            return '+' + digits
        if digits.startswith('00'):
            return '+' + digits[2:]
        if len(digits) == 9:  # Czech number without the country code
            return '+420' + digits
        return '+' + digits

    # ------------------------------------------------------------------
    # Mail helpers (used by the QWeb mail templates)
    # ------------------------------------------------------------------

    def _bw_price(self, amount, prefix=''):
        amount_str = f"{amount:,.0f}".replace(',', ' ')
        return f"{prefix + ' ' if prefix else ''}{amount_str},- Kč"

    def _bw_line_price_str(self, line):
        # The stored prefix is the Czech "od" whatever the visitor language: translate it here
        return self._bw_price(line.price, _('from') if line.price_prefix else '')

    def _bw_total_price_str(self):
        self.ensure_one()
        return self._bw_price(self.total_price, _('from') if self.is_price_approximate else '')

    def _bw_preferred_date_str(self):
        self.ensure_one()
        if not self.preferred_date:
            return _('not specified')
        return format_datetime(self.env, self.preferred_date, tz=BUSINESS_TZ, dt_format='dd.MM.yyyy HH:mm')

    def _bw_company_address(self):
        company = self.website_id.company_id or self.env.company
        return ', '.join(filter(None, [company.street, company.zip and company.city and f"{company.zip} {company.city}" or company.city]))

    def _bw_mail_texts(self):
        """All customer facing e-mail texts, translated to the language of the rendering context."""
        return {
            'subject_pending': _('Your reservation BWD-%s', self.id),
            'subject_confirmed': _('Reservation BWD-%s confirmed', self.id),
            'pending_title': _('Thank you for your reservation!'),
            'confirmed_title': _('Your reservation has been confirmed!'),
            'hello': _('Hello'),
            'pending_intro': _('We have received your reservation and it is now awaiting confirmation. We will contact you shortly to confirm the appointment.'),
            'confirmed_intro': _('We are pleased to confirm your reservation. We look forward to seeing you.'),
            'reservation_number': _('Reservation number'),
            'vehicle': _('Vehicle'),
            'preferred_date': _('Preferred date'),
            'date': _('Date and time'),
            'total_price': _('Total price'),
            'services': _('Selected services'),
            'your_note': _('Your note'),
            'status': _('Reservation status'),
            'awaiting': _('Awaiting confirmation'),
            'address': _('Address'),
            'change_date': _('If you need to change the appointment, just reply to this e-mail or call us.'),
            'not_specified': _('not specified'),
        }

    @api.model
    def _bw_reset_mail_template_translations(self):
        """Drop stale cs/uk copies of subject/body (they held the broken {{ }} version).

        The templates are language neutral now: every text comes from _bw_mail_texts().
        """
        xmlids = ['mail_template_booking_pending', 'mail_template_booking_confirmed', 'mail_template_booking_owner']
        templates = self.env['mail.template']
        for xmlid in xmlids:
            templates |= self.env.ref(f'bw_booking.{xmlid}', raise_if_not_found=False) or templates.browse()
        if not templates:
            return
        self.env.flush_all()
        self.env.cr.execute("""
            UPDATE mail_template
               SET body_html = jsonb_build_object('en_US', body_html->'en_US'),
                   subject = jsonb_build_object('en_US', subject->'en_US')
             WHERE id IN %s
        """, [tuple(templates.ids)])
        templates.invalidate_recordset(['body_html', 'subject'])

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------

    # The booking board (kanban) and the buttons drive the same workflow:
    # moving a card into a column applies the column's booking state, a button
    # moves the card into the column of the new state. E-mails are sent by the
    # column (bw.booking.stage), once per column.

    def action_confirm(self):
        """Owner confirms the booking — creates calendar event and sends confirmation email."""
        for rec in self:
            if rec.state != 'pending':
                raise UserError(_('Can only confirm a reservation in "Awaiting confirmation" state.'))
        self._bw_set_state('confirmed')

    def action_done(self):
        """Customer showed up — this is the real conversion (CRM won + Meta Purchase)."""
        self._bw_set_state('done')

    def action_no_show(self):
        self._bw_set_state('no_show')

    def action_cancel(self):
        self._bw_set_state('cancelled')

    def _bw_set_state(self, state, move_card=True):
        lost_reason = self.env.ref('bw_booking.lost_reason_no_show', raise_if_not_found=False)
        for rec in self:
            if rec.state == state:
                continue
            if state == 'confirmed':
                if not rec.partner_id:
                    rec._create_or_find_partner()
                if not rec.calendar_event_id:
                    rec._create_calendar_event()
            elif state == 'done':
                if rec.lead_id and rec.lead_id.active:
                    rec.lead_id.action_set_won()
                rec._bw_meta_send('Purchase')
            elif state == 'no_show':
                if rec.lead_id and rec.lead_id.active:
                    rec.lead_id.action_set_lost(lost_reason_id=lost_reason.id if lost_reason else False)
            elif state == 'cancelled':
                if rec.lead_id:
                    rec.lead_id.active = False
                if rec.calendar_event_id:
                    rec.calendar_event_id.unlink()
            rec.with_context(bw_stage_sync=True).state = state
            if move_card:
                stage = self.env['bw.booking.stage'].search([('booking_state', '=', state)], limit=1)
                if stage and rec.stage_id != stage:
                    rec.with_context(bw_stage_sync=True).stage_id = stage
                    rec._bw_stage_notify()

    @api.model
    def _bw_assign_stages(self):
        Stage = self.env['bw.booking.stage']
        sent_before = {
            'pending': ['pending'],
            'confirmed': ['pending', 'confirmed'],
            'done': ['pending', 'confirmed'],
            'no_show': ['pending', 'confirmed'],
            'cancelled': ['pending'],
        }
        for rec in self.search([('stage_id', '=', False)]):
            stage = Stage.search([('booking_state', '=', rec.state)], limit=1)
            mailed = Stage.search([('booking_state', 'in', sent_before.get(rec.state, []))])
            rec.with_context(bw_stage_sync=True).write({
                'stage_id': stage.id,
                'mailed_stage_ids': [(6, 0, mailed.ids)],
            })

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        """Show empty columns on the board too."""
        return self.env['bw.booking.stage'].search([])

    def write(self, vals):
        res = super().write(vals)
        if 'stage_id' in vals and not self.env.context.get('bw_stage_sync'):
            # Card moved on the board
            for rec in self:
                if rec.stage_id.booking_state:
                    rec._bw_set_state(rec.stage_id.booking_state, move_card=False)
                rec._bw_stage_notify()
        return res

    def _bw_stage_notify(self):
        """Send the column e-mail (once per column and booking)."""
        for rec in self:
            stage = rec.stage_id
            template = stage.mail_template_id
            if not stage.mail_enabled or not template or not rec.customer_email or stage in rec.mailed_stage_ids:
                continue
            try:
                template.sudo().send_mail(rec.id, force_send=True)
                rec.with_context(bw_stage_sync=True).mailed_stage_ids = [(4, stage.id)]
            except Exception:
                # a broken SMTP must never block the board
                _logger.exception('Booking %s: e-mail of column %s failed', rec.id, stage.name)

    def _create_or_find_partner(self):
        """Find or create res.partner from customer info."""
        self.ensure_one()
        Partner = self.env['res.partner']
        partner = Partner.search([('email', '=ilike', self.customer_email)], limit=1)
        if not partner:
            partner = Partner.create({
                'name': self.customer_name,
                'email': self.customer_email,
                'phone': self.customer_phone,
                'lang': self.lang if self.lang in dict(self.env['res.lang'].get_installed()) else False,
            })
        self.partner_id = partner

    def _bw_attribution_text(self):
        self.ensure_one()
        platform = dict(self._fields['ad_platform']._description_selection(self.env)).get(self.ad_platform, '')
        rows = [
            f"Reklama: {platform}",
            f"Zdroj / médium / kampaň: {self.source_id.name or '-'} / {self.medium_id.name or '-'} / {self.campaign_id.name or '-'}",
        ]
        if self.gclid:
            rows.append(f"gclid: {self.gclid}")
        if self.fbclid:
            rows.append(f"fbclid: {self.fbclid}")
        if self.landing_url:
            rows.append(f"Vstupní stránka: {self.landing_url}")
        if self.referrer:
            rows.append(f"Referrer: {self.referrer}")
        return '\n'.join(rows)

    def _create_crm_lead(self):
        """Create CRM lead for new booking (carries the ad attribution)."""
        self.ensure_one()
        if not self.partner_id:
            self._create_or_find_partner()

        services_text = '\n'.join(
            f"• {line.service_id.name}: {self._bw_price(line.price, 'od' if line.price_prefix else '')}"
            for line in self.line_ids
        )
        preferred = format_datetime(self.env, self.preferred_date, tz=BUSINESS_TZ, dt_format='dd.MM.yyyy HH:mm') if self.preferred_date else 'neuvedeno'
        description = (
            f"Zákazník: {self.customer_name}\n"
            f"Email: {self.customer_email}\n"
            f"Telefon: {self.customer_phone}\n"
            f"Vozidlo: {self.vehicle_type_id.name} — {self.vehicle_info or 'neuvedeno'}\n"
            f"Preferovaný termín: {preferred}\n\n"
            f"Vybrané služby:\n{services_text}\n\n"
            f"Celková cena: {self._bw_price(self.total_price, 'od' if self.is_price_approximate else '')}\n\n"
            f"{self._bw_attribution_text()}\n"
        )
        if self.customer_note:
            description += f"\nPoznámka: {self.customer_note}"

        lead_vals = {
            'name': f"Rezervace: {self.customer_name} — {self.vehicle_type_id.name}",
            'partner_id': self.partner_id.id,
            'email_from': self.customer_email,
            'phone': self.customer_phone,
            'description': plaintext2html(description),
            'expected_revenue': self.total_price,
            'type': 'opportunity',
            'user_id': False,
            'source_id': self.source_id.id,
            'medium_id': self.medium_id.id,
            'campaign_id': self.campaign_id.id,
        }
        tag = {
            'google': 'bw_booking.crm_tag_google_ads',
            'meta': 'bw_booking.crm_tag_meta_ads',
        }.get(self.ad_platform)
        tag = tag and self.env.ref(tag, raise_if_not_found=False)
        if tag:
            lead_vals['tag_ids'] = [(4, tag.id)]
        self.lead_id = self.env['crm.lead'].create(lead_vals)

    def _create_calendar_event(self):
        """Create calendar event with invitation on confirm."""
        self.ensure_one()
        if not self.preferred_date:
            return

        services_list = ', '.join(self.line_ids.mapped('service_id.name'))
        event_vals = {
            'name': f"BWD: {self.customer_name} — {services_list}",
            'start': self.preferred_date,
            'stop': fields.Datetime.add(self.preferred_date, hours=2),
            'partner_ids': [(4, self.partner_id.id)],
            'description': (
                f"Zákazník: {self.customer_name}\n"
                f"Telefon: {self.customer_phone}\n"
                f"Vozidlo: {self.vehicle_type_id.name} — {self.vehicle_info or ''}\n"
                f"Služby: {services_list}\n"
                f"Cena: {self._bw_price(self.total_price)}"
            ),
            'location': self._bw_company_address(),
        }
        if self.lead_id:
            event_vals['opportunity_id'] = self.lead_id.id
        event = self.env['calendar.event'].create(event_vals)
        self.calendar_event_id = event

    # ------------------------------------------------------------------
    # Meta Conversions API (server side, optional — needs a token)
    # ------------------------------------------------------------------

    @staticmethod
    def _bw_sha256(value):
        return hashlib.sha256(value.encode('utf-8')).hexdigest() if value else None

    def _bw_meta_user_data(self):
        self.ensure_one()
        names = (self.customer_name or '').strip().lower().split()
        user_data = {
            'em': [self._bw_sha256((self.customer_email or '').strip().lower())],
            'ph': [self._bw_sha256(re.sub(r'\D', '', self._bw_phone_e164()))],
            'fn': [self._bw_sha256(names[0])] if names else None,
            'ln': [self._bw_sha256(names[-1])] if len(names) > 1 else None,
            'country': [self._bw_sha256('cz')],
            'external_id': [self._bw_sha256(str(self.partner_id.id))] if self.partner_id else None,
            'client_ip_address': self.client_ip or None,
            'client_user_agent': self.client_user_agent or None,
            'fbc': self.fbc or None,
            'fbp': self.fbp or None,
        }
        return {k: v for k, v in user_data.items() if v and v != [None]}

    def _bw_meta_send(self, event_name):
        """Send Lead / Purchase to the Meta Conversions API. Never raises."""
        for rec in self:
            flag = 'meta_lead_sent' if event_name == 'Lead' else 'meta_purchase_sent'
            website = rec.website_id or self.env['website'].get_current_website()
            website = website.sudo()
            pixel_id = website.facebook_pixel_key
            token = website.bw_meta_capi_token
            if not pixel_id or not token or rec[flag]:
                continue
            event = {
                'event_name': event_name,
                'event_time': int((rec.create_date if event_name == 'Lead' else fields.Datetime.now()).timestamp()),
                # Same ID as the browser Pixel Lead event -> Meta deduplicates them
                'event_id': rec.tracking_event_id if event_name == 'Lead' else f"{rec.tracking_event_id}-visit",
                'action_source': 'website' if event_name == 'Lead' else 'physical_store',
                'user_data': rec._bw_meta_user_data(),
                'custom_data': {
                    'currency': BOOKING_CURRENCY,
                    'value': rec.total_price,
                    'content_ids': [str(sid) for sid in rec.line_ids.service_id.ids],
                    'content_type': 'product',
                    'order_id': f"BWD-{rec.id}",
                },
            }
            if event_name == 'Lead' and rec.landing_url:
                event['event_source_url'] = rec.landing_url
            payload = {'data': [event], 'access_token': token}
            if website.bw_meta_test_event_code:
                payload['test_event_code'] = website.bw_meta_test_event_code
            try:
                response = requests.post(META_GRAPH_URL % pixel_id, json=payload, timeout=5)
                ok = response.ok
                body = response.text[:300]
            except requests.RequestException as e:
                ok, body = False, str(e)
            if ok:
                rec[flag] = True
                rec.message_post(body=_('Meta Conversions API: event "%s" sent.', event_name))
            else:
                _logger.warning('Meta CAPI %s for booking %s failed: %s', event_name, rec.id, body)
                rec.message_post(body=_('Meta Conversions API: event "%(event)s" failed: %(error)s', event=event_name, error=body))


class BwBookingLine(models.Model):
    _name = 'bw.booking.line'
    _description = 'Booking Line'
    _order = 'sequence, id'

    booking_id = fields.Many2one('bw.booking', required=True, ondelete='cascade')
    service_id = fields.Many2one('bw.service', required=True, string='Služba')
    price = fields.Float(string='Cena')
    price_prefix = fields.Char(string='Prefix ceny', help='e.g. "od"')
    sequence = fields.Integer(default=10)
