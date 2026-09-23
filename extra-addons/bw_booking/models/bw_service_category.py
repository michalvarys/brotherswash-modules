from odoo import _, fields, models


class BwServiceCategory(models.Model):
    _name = 'bw.service.category'
    _description = 'Service Category'
    _order = 'sequence, id'

    name = fields.Char(required=True, translate=True)
    description = fields.Text(translate=True)
    sequence = fields.Integer(default=10)
    icon = fields.Char(help='Font Awesome class, e.g. fa-star')
    category_type = fields.Selection([
        ('program', _('Program (ceník)')),
        ('premium', _('Prémiová služba')),
        ('extra', _('Doplňková služba')),
    ], required=True, default='program')
    service_ids = fields.One2many('bw.service', 'category_id', string='Services')
    active = fields.Boolean(default=True)
