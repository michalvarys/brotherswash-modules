from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    bw_google_ads_id = fields.Char(related='website_id.bw_google_ads_id', readonly=False)
    bw_ads_booking_send_to = fields.Char(related='website_id.bw_ads_booking_send_to', readonly=False)
    bw_meta_capi_token = fields.Char(related='website_id.bw_meta_capi_token', readonly=False)
    bw_meta_test_event_code = fields.Char(related='website_id.bw_meta_test_event_code', readonly=False)
    bw_tracking_test_mode = fields.Boolean(related='website_id.bw_tracking_test_mode', readonly=False)
