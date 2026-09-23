from odoo import fields, models


class BwVehicleType(models.Model):
    _name = 'bw.vehicle.type'
    _description = 'Vehicle Type'
    _order = 'sequence, id'

    name = fields.Char(required=True, translate=True)  # e.g. Sedan, SUV
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
