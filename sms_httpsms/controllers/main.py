# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import hmac
import hashlib
import json

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class HttpSmsWebhookController(http.Controller):
    """Controller to handle HttpSMS webhook events"""

    @http.route('/httpsms/webhook', type='http', auth='public', methods=['POST'], csrf=False)
    def httpsms_webhook(self, **kwargs):
        """Handle HttpSMS webhook events
        
        HttpSMS sends webhooks for these events:
        - message.phone.received: SMS received
        - message.phone.sent: SMS sent from phone
        - message.phone.delivered: SMS delivered to recipient
        - message.send.failed: SMS sending failed
        - message.send.expired: SMS expired before delivery
        - message.call.missed: Missed call
        - phone.heartbeat.offline: Phone went offline
        - phone.heartbeat.online: Phone came online
        
        Webhook payload example:
        {
            "event": "message.phone.delivered",
            "data": {
                "id": "message-id",
                "owner": "owner-id",
                "contact": "+420123456789",
                "content": "Message content",
                "status": "delivered",
                "type": "sent",
                "created_at": "2025-01-07T14:00:00Z",
                "updated_at": "2025-01-07T14:01:00Z"
            }
        }
        """
        try:
            # Parse JSON from request body
            try:
                body = request.httprequest.get_data(as_text=True)
                _logger.info(f"HttpSMS webhook raw body: {body}")
                
                if body:
                    payload = json.loads(body)
                else:
                    payload = {}
            except json.JSONDecodeError as e:
                _logger.error(f"Failed to parse webhook JSON: {str(e)}")
                return request.make_response(
                    json.dumps({'status': 'error', 'message': 'Invalid JSON'}),
                    headers=[('Content-Type', 'application/json')]
                )
            
            # Get webhook data - HttpSMS uses CloudEvents format
            # Event type is in 'type' field, not 'event'
            event = payload.get('type') or payload.get('event')
            data = payload.get('data', {})
            
            _logger.info(f"HttpSMS webhook received: event={event}, data={data}")
            
            # Verify webhook signature if configured
            if not self._verify_webhook_signature(request.httprequest):
                _logger.warning("HttpSMS webhook signature verification failed")
                return request.make_response(
                    json.dumps({'status': 'error', 'message': 'Invalid signature'}),
                    headers=[('Content-Type', 'application/json')]
                )
            
            # Handle different event types
            if event == 'message.phone.delivered':
                self._handle_message_delivered(data)
            elif event == 'message.send.failed':
                self._handle_message_failed(data)
            elif event == 'message.send.expired':
                self._handle_message_expired(data)
            elif event == 'message.phone.sent':
                self._handle_message_sent(data)
            elif event == 'message.phone.received':
                self._handle_message_received(data)
            else:
                _logger.info(f"HttpSMS webhook event '{event}' not handled")
            
            return request.make_response(
                json.dumps({'status': 'ok'}),
                headers=[('Content-Type', 'application/json')]
            )
            
        except Exception as e:
            _logger.error(f"Error processing HttpSMS webhook: {str(e)}", exc_info=True)
            return request.make_response(
                json.dumps({'status': 'error', 'message': str(e)}),
                headers=[('Content-Type', 'application/json')]
            )
    
    def _verify_webhook_signature(self, http_request):
        """Verify webhook signature if signing key is configured
        
        HttpSMS signs webhooks with HMAC-SHA256 if a signing key is configured.
        The signature is sent in the X-Httpsms-Signature header.
        """
        # Use the global request object to access env
        signing_key = request.env['ir.config_parameter'].sudo().get_param('sms_httpsms.webhook_signing_key', '')
        
        if not signing_key or not isinstance(signing_key, str):
            # No signing key configured, skip verification
            return True
        
        signature = http_request.headers.get('X-Httpsms-Signature', '')
        if not signature:
            return False
        
        # Get request body
        body = http_request.get_data()
        
        # Calculate expected signature
        expected_signature = hmac.new(
            signing_key.encode('utf-8'),
            body,
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        return hmac.compare_digest(signature, expected_signature)
    
    def _handle_message_delivered(self, data):
        """Handle message.phone.delivered event
        
        Update SMS status to 'sent' (delivered in Odoo terms)
        """
        # HttpSMS uses 'id' field for message.phone.delivered
        message_id = data.get('id') or data.get('message_id')
        if not message_id:
            _logger.warning("HttpSMS webhook: message.phone.delivered without message ID")
            return
        
        if message_id:
            request.env['sms.sms'].sudo()._update_sms_delivery_status(message_id, 'sent')
        else:
            _logger.warning("HttpSMS webhook: message.phone.delivered without message ID")
    
    def _handle_message_received(self, data):
        """Handle message.phone.received event
        
        Create a message in the chatter for the contact who sent the SMS
        According to HttpSMS docs, this event uses 'message_id' field
        """
        message_id = data.get('message_id')
        contact_number = data.get('contact')
        content = data.get('content')
        timestamp = data.get('timestamp')
        
        if not contact_number or not content:
            _logger.warning("HttpSMS webhook: message.phone.received without contact or content")
            return
        
        _logger.info(f"HttpSMS: Received SMS from {contact_number}: {content[:50]}...")
        
        # Find partner by phone number
        # Try to find by mobile or phone field
        partner = request.env['res.partner'].sudo().search([
            '|',
            ('mobile', '=', contact_number),
            ('phone', '=', contact_number)
        ], limit=1)
        
        if not partner:
            # Try to find by sanitized phone number (without spaces, dashes, etc.)
            sanitized = contact_number.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            partner = request.env['res.partner'].sudo().search([
                '|',
                ('mobile', 'ilike', sanitized),
                ('phone', 'ilike', sanitized)
            ], limit=1)
        
        if partner:
            _logger.info(f"HttpSMS: Found partner {partner.id} ({partner.name}) for number {contact_number}")
            
            # Create message in chatter
            try:
                partner.message_post(
                    body=f"Příchozí SMS: {content}",
                    subject=f"SMS od {contact_number}",
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment',
                )
                _logger.info(f"HttpSMS: Created chatter message for partner {partner.id}")
            except Exception as e:
                _logger.error(f"HttpSMS: Failed to create chatter message: {str(e)}")
        else:
            _logger.warning(f"HttpSMS: No partner found for phone number {contact_number}")
            
            # Optionally create a lead or log somewhere else
            # For now, just log it
            _logger.info(f"HttpSMS: Received SMS from unknown number {contact_number}: {content}")
    
    def _handle_message_failed(self, data):
        """Handle message.send.failed event
        
        Update SMS status to 'error'
        According to HttpSMS docs, this event uses 'id' field
        """
        message_id = data.get('id') or data.get('message_id')
        if not message_id:
            _logger.warning("HttpSMS webhook: message.send.failed without message ID")
            return
        
        if message_id:
            request.env['sms.sms'].sudo()._update_sms_delivery_status(message_id, 'error', failure_code='sms_server')
        else:
            _logger.warning("HttpSMS webhook: message.send.failed without message ID")
    
    def _handle_message_expired(self, data):
        """Handle message.send.expired event
        
        Update SMS status to 'error' with expired failure type
        According to HttpSMS docs, this event uses 'message_id' field (not 'id')
        """
        message_id = data.get('message_id') or data.get('id')
        if not message_id:
            _logger.warning("HttpSMS webhook: message.send.expired without message ID")
            return
        
        if message_id:
            request.env['sms.sms'].sudo()._update_sms_delivery_status(message_id, 'error', failure_code='sms_expired')
        else:
            _logger.warning("HttpSMS webhook: message.send.expired without message ID")
    
    def _handle_message_sent(self, data):
        """Handle message.phone.sent event
        
        Update SMS status to 'pending' (sent from phone, waiting for delivery)
        According to HttpSMS docs, this event uses 'id' field
        """
        message_id = data.get('id') or data.get('message_id')
        if not message_id:
            _logger.warning("HttpSMS webhook: message.phone.sent without message ID")
            return
        
        if message_id:
            # Map 'message.phone.sent' to 'pending' (Sent) in Odoo
            # 'sent' in Odoo means Delivered. 'pending' means Sent (waiting for delivery).
            sms = request.env['sms.sms'].sudo().search([('uuid', '=', message_id)], limit=1)
            if sms and sms.state in ('outgoing', 'process'):
                request.env['sms.sms'].sudo()._update_sms_delivery_status(message_id, 'pending')
        else:
            _logger.warning("HttpSMS webhook: message.phone.sent without message ID")
