import json
from datetime import datetime

from odoo import http
from odoo.http import request


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

    @http.route('/bw/api/booking/submit', type='json', auth='public', website=True)
    def api_booking_submit(self, **post):
        """AJAX booking submission from homepage form."""
        required = ['customer_name', 'customer_email', 'customer_phone', 'vehicle_type_id']
        for field in required:
            if not post.get(field):
                return {'success': False, 'error': 'missing_fields'}

        service_ids = post.get('service_ids', [])
        if not service_ids:
            return {'success': False, 'error': 'no_services'}

        preferred_date = False
        if post.get('preferred_date'):
            try:
                preferred_date = datetime.strptime(post['preferred_date'], '%Y-%m-%dT%H:%M')
            except ValueError:
                pass

        vehicle_type_id = int(post['vehicle_type_id'])
        Service = request.env['bw.service'].sudo()

        # Build price lookup from frontend data (if provided)
        frontend_prices = {}
        for item in post.get('service_data', []):
            frontend_prices[int(item['id'])] = float(item.get('price', 0))

        lines = []
        for svc_id in service_ids:
            svc = Service.browse(int(svc_id))
            if svc.exists():
                price, prefix = svc.get_price_for_vehicle(vehicle_type_id)
                if not price and svc.id in frontend_prices:
                    price = frontend_prices[svc.id]
                lines.append((0, 0, {
                    'service_id': svc.id,
                    'price': price,
                    'price_prefix': prefix,
                }))

        booking = request.env['bw.booking'].sudo().create({
            'customer_name': post['customer_name'],
            'customer_email': post['customer_email'],
            'customer_phone': post['customer_phone'],
            'customer_note': post.get('customer_note', ''),
            'vehicle_type_id': vehicle_type_id,
            'vehicle_info': post.get('vehicle_info', ''),
            'preferred_date': preferred_date,
            'lang': request.env.lang or 'cs_CZ',
            'line_ids': lines,
        })
        booking._create_crm_lead()

        template = request.env.ref('bw_booking.mail_template_booking_pending', raise_if_not_found=False)
        if template:
            template.sudo().send_mail(booking.id, force_send=True)

        return {
            'success': True,
            'booking_id': booking.id,
            'total_price': booking.total_price,
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
        # Validate required fields
        required = ['customer_name', 'customer_email', 'customer_phone', 'vehicle_type_id']
        for field in required:
            if not post.get(field):
                return request.redirect('/booking?error=missing_fields')

        # Parse selected services
        service_ids = []
        for key in post:
            if key.startswith('service_') and post[key] == 'on':
                try:
                    service_ids.append(int(key.replace('service_', '')))
                except ValueError:
                    continue

        if not service_ids:
            return request.redirect('/booking?error=no_services')

        # Parse preferred date
        preferred_date = False
        if post.get('preferred_date'):
            try:
                preferred_date = datetime.strptime(post['preferred_date'], '%Y-%m-%dT%H:%M')
            except ValueError:
                pass

        vehicle_type_id = int(post['vehicle_type_id'])

        # Build booking lines with prices
        Booking = request.env['bw.booking'].sudo()
        Service = request.env['bw.service'].sudo()

        lines = []
        for svc_id in service_ids:
            svc = Service.browse(svc_id)
            if svc.exists():
                price, prefix = svc.get_price_for_vehicle(vehicle_type_id)
                lines.append((0, 0, {
                    'service_id': svc_id,
                    'price': price,
                    'price_prefix': prefix,
                }))

        booking = Booking.create({
            'customer_name': post['customer_name'],
            'customer_email': post['customer_email'],
            'customer_phone': post['customer_phone'],
            'customer_note': post.get('customer_note', ''),
            'vehicle_type_id': vehicle_type_id,
            'vehicle_info': post.get('vehicle_info', ''),
            'preferred_date': preferred_date,
            'lang': request.env.lang or 'cs_CZ',
            'line_ids': lines,
        })

        # Create CRM lead
        booking._create_crm_lead()

        # Send pending email
        template = request.env.ref('bw_booking.mail_template_booking_pending', raise_if_not_found=False)
        if template:
            template.sudo().send_mail(booking.id, force_send=True)

        return request.render('bw_booking.booking_thank_you', {'booking': booking})
