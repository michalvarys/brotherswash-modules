# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    """Add HttpSMS configuration to general settings"""
    
    _inherit = 'res.config.settings'

    sms_httpsms_api_key = fields.Char(
        string='HttpSMS API Key',
        config_parameter='sms_httpsms.api_key',
        help='API Key from https://httpsms.com/settings'
    )
    
    sms_httpsms_default_sender = fields.Char(
        string='Default Sender Phone Number',
        config_parameter='sms_httpsms.default_sender',
        help='Default phone number to use as sender (e.g., +18005550199). Must be in international format with + prefix.'
    )
    
    sms_httpsms_webhook_signing_key = fields.Char(
        string='Webhook Signing Key',
        config_parameter='sms_httpsms.webhook_signing_key',
        help='Optional signing key from HttpSMS webhook settings for security'
    )
    
    sms_httpsms_rate_limit = fields.Integer(
        string='SMS Rate Limit (seconds)',
        config_parameter='sms_httpsms.rate_limit',
        default=60,
        help='Delay in seconds between sending each SMS to avoid Android rate limiting. Recommended: 60 seconds (1 SMS per minute)'
    )

    sms_httpsms_base_url = fields.Char(
        string='HttpSMS Base URL',
        config_parameter='sms_httpsms.base_url',
        default='https://sms-api.varyshop.eu',
        help='Base URL for HttpSMS API. Default is the Varyshop self-hosted instance.'
    )

    sms_httpsms_webhook_url = fields.Char(
        string='Webhook URL',
        compute='_compute_sms_httpsms_webhook_url',
        help='URL to configure in HttpSMS webhook settings'
    )
    
    sms_httpsms_enabled = fields.Boolean(
        string='Use HttpSMS',
        compute='_compute_sms_httpsms_enabled',
        help='HttpSMS integration is enabled when API key and sender are configured'
    )

    def _compute_sms_httpsms_webhook_url(self):
        """Compute webhook URL for HttpSMS configuration"""
        for record in self:
            base_url = record.env['ir.config_parameter'].sudo().get_param('web.base.url')
            record.sms_httpsms_webhook_url = f"{base_url}/httpsms/webhook"
    
    @api.depends('sms_httpsms_api_key', 'sms_httpsms_default_sender')
    def _compute_sms_httpsms_enabled(self):
        """Check if HttpSMS is properly configured"""
        for record in self:
            record.sms_httpsms_enabled = bool(
                record.sms_httpsms_api_key and record.sms_httpsms_default_sender
            )
    
    def action_test_httpsms_connection(self):
        """Test HttpSMS API connection"""
        self.ensure_one()

        if not self.sms_httpsms_api_key:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Configuration Error',
                    'message': 'Please configure HttpSMS API Key first.',
                    'type': 'warning',
                    'sticky': False,
                }
            }

        if not self.sms_httpsms_default_sender:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Configuration Error',
                    'message': 'Please configure Default Sender Phone Number first.',
                    'type': 'warning',
                    'sticky': False,
                }
            }

        try:
            # Try to validate configuration by creating an API instance
            from odoo.addons.sms_httpsms.tools.httpsms_api import HttpSmsApi
            api = HttpSmsApi(self.env)
            api._validate_config()

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': 'HttpSMS configuration is valid! You can now send SMS messages.',
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Configuration Error',
                    'message': f'HttpSMS configuration test failed: {str(e)}',
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def action_cleanup_stuck_sms(self):
        """Clean up stuck SMS messages that are causing duplicate sends"""
        self.ensure_one()
        return self.env['sms.sms'].cleanup_stuck_sms()
