# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup
from werkzeug.urls import url_join

from odoo import fields, models, _
from odoo.addons.sms_httpsms.tools.httpsms_api import HttpSmsApi


class MassSMSTest(models.TransientModel):
    """Override test SMS wizard to use HttpSMS instead of IAP"""
    
    _inherit = 'mailing.sms.test'

    def action_send_sms(self):
        """Override to use HttpSMS API instead of IAP"""
        self.ensure_one()

        numbers = [number.strip() for number in self.numbers.splitlines()]
        sanitized_numbers = [self.env.user._phone_format(number=number) for number in numbers]
        invalid_numbers = [number for sanitized, number in zip(sanitized_numbers, numbers) if not sanitized]

        record = self.env[self.mailing_id.mailing_model_real].search([], limit=1)
        body = self.mailing_id.body_plaintext
        if record:
            # Returns a proper error if there is a syntax error with qweb
            body = self.env['mail.render.mixin']._render_template(body, self.mailing_id.mailing_model_real, record.ids)[record.id]

        # Create SMS records with state 'sent' to prevent cron from picking them up
        new_sms_messages_sudo = self.env['sms.sms'].sudo().create([
            {'body': body, 'number': number, 'state': 'sent'} 
            for number in sanitized_numbers
        ])
        
        # Use HttpSMS API instead of IAP
        sms_api = HttpSmsApi(self.env)
        sent_sms_list = sms_api._send_sms_batch([{
            'content': body,
            'numbers': [{'number': sms_id.number, 'uuid': sms_id.uuid} for sms_id in new_sms_messages_sudo],
        }], delivery_reports_url=url_join(self[0].get_base_url(), '/sms/status'))

        error_messages = {}
        if any(sent_sms.get('state') != 'success' for sent_sms in sent_sms_list):
            error_messages = sms_api._get_sms_api_error_messages()

        notification_messages = []
        if invalid_numbers:
            notification_messages.append(_('The following numbers are not correctly encoded: %s',
                ', '.join(invalid_numbers)))

        for sent_sms in sent_sms_list:
            if sent_sms.get('state') == 'success':
                notification_messages.append(
                    _('Test SMS successfully sent to %s', sent_sms.get('res_id')))
            elif sent_sms.get('state'):
                notification_messages.append(
                    _(
                        "Test SMS could not be sent to %(destination)s: %(state)s",
                        destination=sent_sms.get("res_id"),
                        state=error_messages.get(sent_sms["state"], _("An error occurred.")),
                    )
                )

        if notification_messages:
            message_body = Markup(
                f"<ul>{''.join('<li>%s</li>' for _ in notification_messages)}</ul>"
            ) % tuple(notification_messages)
            self.mailing_id._message_log(body=message_body)

        return True
