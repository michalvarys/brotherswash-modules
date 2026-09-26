import json
import logging
from datetime import datetime

from odoo import http
from odoo.http import request
from odoo.tools import email_normalize

_logger = logging.getLogger(__name__)


class BwBookingController(http.Controller):

    @http.route('/bw/api/company-info', type='json', auth='public', website=True)
    def api_company_info(self, **kwargs):
        """JSON API — public company contact info for frontend widgets."""
        lang = request.env.lang or 'cs_CZ'
        co = request.env.company.sudo().with_context(lang=lang)
        phone = co.mobile or co.phone or ''
        return {
            'name': co.name or '',
            'phone': phone,
            'phone_clean': phone.replace(' ', '').replace('-', ''),
            'email': co.email or '',
            'street': co.street or '',
            'city': co.city or '',
            'zip': co.zip or '',
            'social_instagram': co.social_instagram or '',
            'social_facebook': co.social_facebook or '',
            'year': datetime.now().year,
        }

    @http.route('/bw/api/services', type='json', auth='public', website=True)
    def api_services(self, **kwargs):
        """JSON API — returns all bookable services with prices for the homepage form."""
        lang = request.env.lang or 'cs_CZ'
        ctx = {'lang': lang}
        vehicle_types = request.env['bw.vehicle.type'].sudo().with_context(**ctx).search([])
        categories = request.env['bw.service.category'].sudo().with_context(**ctx).search([])
        services = request.env['bw.service'].sudo().with_context(**ctx).search([('is_bookable', '=', True)])

        result = {
            'vehicle_types': [{'id': vt.id, 'name': vt.name} for vt in vehicle_types],
            'categories': [
                {
                    'id': cat.id,
                    'name': cat.name,
                    'category_type': cat.category_type,
                    'description': cat.description or '',
                }
                for cat in categories
            ],
            'services': [],
            'price_map': {},
        }
        for svc in services:
            result['services'].append({
                'id': svc.id,
                'name': svc.name,
                'category_id': svc.category_id.id,
                'category_type': svc.category_type,
                'short_description': svc.short_description or '',
                'description': svc.description or '',
                'duration_info': svc.duration_info or '',
                'is_highlighted': svc.is_highlighted,
            })
            result['price_map'][svc.id] = {}
            for pr in svc.price_ids:
                result['price_map'][svc.id][pr.vehicle_type_id.id] = {
                    'price': pr.price,
                    'prefix': pr.price_prefix or '',
                }
        return result

    def _bw_create_booking(self, post, service_ids, tracking=None):
        """Shared booking creation for the AJAX homepage form and the /booking page.

        Creates the booking with ad attribution, the CRM lead, sends the customer
        and owner e-mails and the server-side Meta Lead event.
        """
        vehicle_type_id = int(post['vehicle_type_id'])
        Booking = request.env['bw.booking'].sudo()
        Service = request.env['bw.service'].sudo()

        lines = []
        for svc_id in service_ids:
            svc = Service.browse(int(svc_id))
            if svc.exists() and svc.is_bookable:
                price, prefix = svc.get_price_for_vehicle(vehicle_type_id)
                lines.append((0, 0, {
                    'service_id': svc.id,
                    'price': price,
                    'price_prefix': prefix,
                }))
        if not lines:
            return None

        vals = {
            'customer_name': post['customer_name'].strip(),
            'customer_email': post['customer_email'].strip(),
            'customer_phone': post['customer_phone'].strip(),
            'customer_note': post.get('customer_note', ''),
            'vehicle_type_id': vehicle_type_id,
            'vehicle_info': post.get('vehicle_info', ''),
            'preferred_date': Booking._bw_parse_local_datetime(post.get('preferred_date')),
            'lang': request.env.lang or 'cs_CZ',
            'website_id': request.website.id,
            'line_ids': lines,
        }
        vals.update(Booking._bw_prepare_tracking_vals(tracking, request.httprequest))
        booking = Booking.create(vals)
        # The lead is for the (Czech speaking) owner, whatever the visitor language
        booking.with_context(lang='cs_CZ')._create_crm_lead()

        # Customer e-mail comes from the board column the booking lands in ("Nové")
        booking._bw_stage_notify()
        template = request.env.ref('bw_booking.mail_template_booking_owner', raise_if_not_found=False)
        if template:
            try:
                template.sudo().send_mail(booking.id, force_send=True)
            except Exception:
                # A broken SMTP must never lose the booking itself
                _logger.exception('Booking %s: owner e-mail failed', booking.id)

        booking._bw_meta_send('Lead')
        return booking

    @http.route('/bw/api/booking/submit', type='json', auth='public', website=True)
    def api_booking_submit(self, **post):
        """AJAX booking submission from homepage form."""
        required = ['customer_name', 'customer_email', 'customer_phone', 'vehicle_type_id']
        for field in required:
            if not post.get(field):
                return {'success': False, 'error': 'missing_fields'}
        if not email_normalize(post['customer_email']):
            return {'success': False, 'error': 'invalid_email'}

        service_ids = post.get('service_ids', [])
        if not service_ids:
            return {'success': False, 'error': 'no_services'}

        booking = self._bw_create_booking(post, service_ids, post.get('tracking'))
        if not booking:
            return {'success': False, 'error': 'no_services'}

        return {
            'success': True,
            'booking_id': booking.id,
            'total_price': booking.total_price,
            'tracking': booking._bw_tracking_payload(),
        }

    @http.route('/booking', type='http', auth='public', website=True, sitemap=True)
    def booking_page(self, **kwargs):
        """Render the service configurator / booking page."""
        vehicle_types = request.env['bw.vehicle.type'].sudo().search([])
        categories = request.env['bw.service.category'].sudo().search([])
        services = request.env['bw.service'].sudo().search([('is_bookable', '=', True)])

        # Build price map: {service_id: {vehicle_type_id: {price, prefix}}}
        price_map = {}
        for svc in services:
            price_map[svc.id] = {}
            for price_rec in svc.price_ids:
                price_map[svc.id][price_rec.vehicle_type_id.id] = {
                    'price': price_rec.price,
                    'prefix': price_rec.price_prefix or '',
                }

        values = {
            'vehicle_types': vehicle_types,
            'categories': categories,
            'services': services,
            'price_map_json': json.dumps(price_map),
        }
        return request.render('bw_booking.booking_page', values)

    @http.route('/booking/submit', type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def booking_submit(self, **post):
        """Handle booking form submission."""
        required = ['customer_name', 'customer_email', 'customer_phone', 'vehicle_type_id']
        for field in required:
            if not post.get(field):
                return request.redirect('/booking?error=missing_fields')
        if not email_normalize(post['customer_email']):
            return request.redirect('/booking?error=invalid_email')

        service_ids = []
        for key in post:
            if key.startswith('service_') and post[key] == 'on':
                try:
                    service_ids.append(int(key.replace('service_', '')))
                except ValueError:
                    continue
        if not service_ids:
            return request.redirect('/booking?error=no_services')

        try:
            tracking = json.loads(post.get('bw_tracking') or '{}')
        except ValueError:
            tracking = {}

        booking = self._bw_create_booking(post, service_ids, tracking)
        if not booking:
            return request.redirect('/booking?error=no_services')

        return request.render('bw_booking.booking_thank_you', {
            'booking': booking,
            'bw_tracking_json': json.dumps(booking._bw_tracking_payload()),
        })
