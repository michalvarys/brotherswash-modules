from odoo import api, fields, models, _
from odoo.exceptions import UserError


class BwBooking(models.Model):
    _name = 'bw.booking'
    _description = 'Detailing Booking'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(compute='_compute_name', store=True)
    state = fields.Selection([
        ('pending', _('Awaiting confirmation')),
        ('confirmed', _('Confirmed')),
        ('done', _('Done')),
        ('cancelled', _('Cancelled')),
    ], default='pending', tracking=True, required=True)

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

    # Preferred date/time
    preferred_date = fields.Datetime(string='Preferovaný termín')

    # Language (set from website visitor language)
    lang = fields.Char(string='Jazyk', default='cs_CZ')

    # CRM & Calendar links
    lead_id = fields.Many2one('crm.lead', string='CRM příležitost', readonly=True)
    calendar_event_id = fields.Many2one('calendar.event', string='Událost v kalendáři', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Kontakt', readonly=True)

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

    def action_confirm(self):
        """Owner confirms the booking — creates calendar event and sends confirmation email."""
        for rec in self:
            if rec.state != 'pending':
                raise UserError(_('Can only confirm a reservation in "Awaiting confirmation" state.'))

            # Ensure partner exists
            if not rec.partner_id:
                rec._create_or_find_partner()

            # Create calendar event
            rec._create_calendar_event()

            # Update CRM lead stage
            if rec.lead_id:
                won_stage = self.env['crm.stage'].search([('is_won', '=', True)], limit=1)
                if won_stage:
                    rec.lead_id.stage_id = won_stage

            rec.state = 'confirmed'

            # Send confirmation email
            template = self.env.ref('bw_booking.mail_template_booking_confirmed', raise_if_not_found=False)
            if template:
                template.send_mail(rec.id, force_send=True)

    def action_done(self):
        for rec in self:
            rec.state = 'done'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'
            if rec.lead_id:
                rec.lead_id.active = False
            if rec.calendar_event_id:
                rec.calendar_event_id.unlink()

    def _create_or_find_partner(self):
        """Find or create res.partner from customer info."""
        self.ensure_one()
        Partner = self.env['res.partner']
        partner = Partner.search([('email', '=', self.customer_email)], limit=1)
        if not partner:
            partner = Partner.create({
                'name': self.customer_name,
                'email': self.customer_email,
                'phone': self.customer_phone,
            })
        self.partner_id = partner

    def _create_crm_lead(self):
        """Create CRM lead for new booking."""
        self.ensure_one()
        if not self.partner_id:
            self._create_or_find_partner()

        services_text = '\n'.join(
            f"• {line.service_id.name}: {line.price_prefix + ' ' if line.price_prefix else ''}{line.price:,.0f},- Kč"
            for line in self.line_ids
        )
        price_prefix = 'od ' if self.is_price_approximate else ''
        description = (
            f"Zákazník: {self.customer_name}\n"
            f"Email: {self.customer_email}\n"
            f"Telefon: {self.customer_phone}\n"
            f"Vozidlo: {self.vehicle_type_id.name} — {self.vehicle_info or 'neuvedeno'}\n"
            f"Preferovaný termín: {self.preferred_date.strftime('%d.%m.%Y %H:%M') if self.preferred_date else 'neuvedeno'}\n\n"
            f"Vybrané služby:\n{services_text}\n\n"
            f"Celková cena: {price_prefix}{self.total_price:,.0f},- Kč\n"
        )
        if self.customer_note:
            description += f"\nPoznámka: {self.customer_note}"

        lead = self.env['crm.lead'].create({
            'name': f"Rezervace: {self.customer_name} — {self.vehicle_type_id.name}",
            'partner_id': self.partner_id.id,
            'email_from': self.customer_email,
            'phone': self.customer_phone,
            'description': description,
            'expected_revenue': self.total_price,
            'type': 'opportunity',
        })
        self.lead_id = lead

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
                f"Cena: {self.total_price:,.0f},- Kč"
            ),
            'location': 'Vrchlického 1325/25, Praha 5 - Košíře',
        }
        if self.lead_id:
            event_vals['opportunity_id'] = self.lead_id.id
        event = self.env['calendar.event'].create(event_vals)
        self.calendar_event_id = event


class BwBookingLine(models.Model):
    _name = 'bw.booking.line'
    _description = 'Booking Line'
    _order = 'sequence, id'

    booking_id = fields.Many2one('bw.booking', required=True, ondelete='cascade')
    service_id = fields.Many2one('bw.service', required=True, string='Služba')
    price = fields.Float(string='Cena')
    price_prefix = fields.Char(string='Prefix ceny', help='e.g. "od"')
    sequence = fields.Integer(default=10)
