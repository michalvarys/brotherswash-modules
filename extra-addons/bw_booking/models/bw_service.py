from odoo import api, fields, models


class BwService(models.Model):
    _name = 'bw.service'
    _description = 'Detailing Service'
    _order = 'category_id, sequence, id'

    name = fields.Char(required=True, translate=True)
    category_id = fields.Many2one('bw.service.category', required=True, ondelete='cascade')
    category_type = fields.Selection(related='category_id.category_type', store=True)
    description = fields.Html(translate=True)
    short_description = fields.Text(translate=True)
    sequence = fields.Integer(default=10)
    duration_info = fields.Char(translate=True, help='e.g. 15-25 min, cca 6 hodin')
    is_highlighted = fields.Boolean(help='Visual highlight (recommended)')
    is_bookable = fields.Boolean(default=True, help='Available in online configurator')
    active = fields.Boolean(default=True)

    # Prices per vehicle type — stored as One2many
    price_ids = fields.One2many('bw.service.price', 'service_id', string='Prices')

    def get_price_for_vehicle(self, vehicle_type_id):
        """Get price and prefix for a specific vehicle type.
        Falls back to the first available price if no exact match
        (e.g. extras with a single flat price).
        Returns (price, prefix) tuple.
        """
        price_rec = self.price_ids.filtered(lambda p: p.vehicle_type_id.id == vehicle_type_id)
        if price_rec:
            return price_rec[0].price, price_rec[0].price_prefix or ''
        # Fallback: use any available price (flat-rate extras)
        if self.price_ids:
            return self.price_ids[0].price, self.price_ids[0].price_prefix or ''
        return 0.0, ''


class BwServicePrice(models.Model):
    _name = 'bw.service.price'
    _description = 'Service Price per Vehicle Type'
    _order = 'vehicle_type_id'

    service_id = fields.Many2one('bw.service', required=True, ondelete='cascade')
    vehicle_type_id = fields.Many2one('bw.vehicle.type', required=True, ondelete='cascade')
    price = fields.Float(required=True)
    price_prefix = fields.Char(translate=True, help='e.g. "od" for "od 500,-"')
