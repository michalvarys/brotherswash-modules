from odoo import fields, models

from .bw_booking import BOOKING_CURRENCY


class Website(models.Model):
    _inherit = 'website'

    bw_google_ads_id = fields.Char(
        string='Google Ads ID',
        help='Google Ads tag ID, e.g. AW-17998032792. Loaded together with the Google tag (GA4).',
    )
    bw_ads_booking_send_to = fields.Char(
        string='Google Ads booking conversion',
        help='"send_to" of the Google Ads conversion fired after a booking is submitted, '
             'e.g. AW-17998032792/n-P5CKCcyc8cEJjfkIZD.',
    )
    bw_meta_capi_token = fields.Char(
        string='Meta Conversions API token',
        groups='base.group_system',
        help='Access token from Meta Events Manager. When set, bookings are also sent server-side '
             '(Lead on submit, Purchase when the booking is marked done).',
    )
    bw_meta_test_event_code = fields.Char(
        string='Meta test event code',
        help='Test event code (TEST12345) from Meta Events Manager. Server-side events then show up '
             'only in "Test events" and do not affect ad optimisation.',
    )
    bw_tracking_test_mode = fields.Boolean(
        string='Tracking test mode',
        help='For the dev server: GA4 events are sent with debug_mode, the Google Ads conversion is not fired '
             'and every tracking call is logged into the browser console.',
    )

    def _bw_tracking_config(self):
        """Public tracking config for the frontend (rendered into the page as JSON)."""
        self.ensure_one()
        return {
            'ads_send_to': self.bw_ads_booking_send_to or '',
            'test_mode': bool(self.bw_tracking_test_mode),
            'currency': BOOKING_CURRENCY,
        }
