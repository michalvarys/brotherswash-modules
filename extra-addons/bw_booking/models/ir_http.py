from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _get_translation_frontend_modules_name(cls):
        # Without this the _t() strings of the booking widgets stay in English on /cs and /uk.
        mods = super()._get_translation_frontend_modules_name()
        return mods + ['bw_booking', 'theme_brotherswash']
