from odoo import api, fields, models

BOOKING_STATES = [
    ('pending', 'Čeká na potvrzení'),
    ('confirmed', 'Potvrzeno'),
    ('done', 'Zákazník přišel'),
    ('no_show', 'Nedorazil'),
    ('cancelled', 'Zrušeno'),
]


class BwBookingStage(models.Model):
    """Column of the booking board + the e-mail sent when a booking enters it."""

    _name = 'bw.booking.stage'
    _description = 'Brothers Wash – sloupec boardu rezervací'
    _order = 'sequence, id'

    name = fields.Char(string='Název sloupce', required=True)
    sequence = fields.Integer(string='Pořadí', default=10)
    fold = fields.Boolean(string='Sbaleno v boardu', help='Sloupec bude v boardu sbalený (hodí se pro koncové stavy).')
    booking_state = fields.Selection(
        BOOKING_STATES, string='Stav rezervace',
        help='Co se s rezervací stane po přetažení do sloupce: „Potvrzeno“ založí událost v kalendáři, '
             '„Zákazník přišel“ označí CRM příležitost jako vyhranou a pošle konverzi do Meta, '
             '„Nedorazil“ ji uzavře jako ztracenou. Prázdné = jen tvůj interní krok.',
    )
    mail_enabled = fields.Boolean(
        string='Poslat e-mail zákazníkovi',
        help='Když rezervace vstoupí do sloupce, pošle se zákazníkovi vybraný e-mail '
             '(v jazyce, ve kterém rezervoval). Každý e-mail jen jednou.',
    )
    mail_template_id = fields.Many2one(
        'mail.template', string='E-mail', domain=[('model', '=', 'bw.booking')],
    )
    booking_count = fields.Integer(compute='_compute_booking_count', string='Rezervací')

    @api.depends('name')
    def _compute_booking_count(self):
        counts = dict(self.env['bw.booking']._read_group([('stage_id', 'in', self.ids)], ['stage_id'], ['__count']))
        for stage in self:
            stage.booking_count = counts.get(stage, 0)
