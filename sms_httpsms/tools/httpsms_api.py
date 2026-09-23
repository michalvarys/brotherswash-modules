# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import requests
import json
import time
from odoo.tools.translate import _, LazyTranslate

_logger = logging.getLogger(__name__)
_lt = LazyTranslate(__name__)

# Error messages mapping HttpSMS errors to user-friendly messages
ERROR_MESSAGES = {
    'invalid_phone_number': _lt("Invalid phone number. Please make sure to follow the international format, i.e. a plus sign (+), then country code, city code, and local phone number. For example: +1 555-555-555"),
    'unauthorized': _lt("Invalid API key. Please check your HttpSMS API key in settings."),
    'missing_api_key': _lt("HttpSMS API key is not configured. Please configure it in Settings > General Settings > SMS HttpSMS."),
    'missing_sender': _lt("Default sender phone number is not configured. Please configure it in Settings > General Settings > SMS HttpSMS."),
    'rate_limit': _lt("Rate limit exceeded. Please try again later."),
    'server_error': _lt("HttpSMS server error. Please try again later."),
    'network_error': _lt("Network error while connecting to HttpSMS. Please check your internet connection."),
    'unknown_error': _lt("An unknown error occurred. Please contact support if this error persists."),
}


class HttpSmsApi:
    """HttpSMS API client for sending SMS messages"""

    def __init__(self, env):
        self.env = env
        self._api_key = None
        self._default_sender = None
        self._base_url = None

    @property
    def api_key(self):
        """Get HttpSMS API key from system parameters"""
        if not self._api_key:
            self._api_key = self.env['ir.config_parameter'].sudo().get_param('sms_httpsms.api_key', '')
        return self._api_key

    @property
    def default_sender(self):
        """Get default sender phone number from system parameters"""
        if not self._default_sender:
            self._default_sender = self.env['ir.config_parameter'].sudo().get_param('sms_httpsms.default_sender', '')
        return self._default_sender

    @property
    def base_url(self):
        """Get HttpSMS base URL from system parameters"""
        if not self._base_url:
            base_url_param = self.env['ir.config_parameter'].sudo().get_param('sms_httpsms.base_url', 'https://sms-api.varyshop.eu')
            # Ensure we have a string
            if not base_url_param:
                base_url_param = 'https://sms-api.varyshop.eu'
            
            self._base_url = str(base_url_param).rstrip('/')
        return self._base_url

    @property
    def endpoint(self):
        """Get full endpoint URL for sending messages"""
        return f'{self.base_url}/v1/messages/send'
    
    def _validate_config(self):
        """Validate that API key and sender are configured"""
        if not self.api_key:
            raise ValueError(ERROR_MESSAGES['missing_api_key'])
        if not self.default_sender:
            raise ValueError(ERROR_MESSAGES['missing_sender'])
    
    def _send_sms_batch(self, messages, delivery_reports_url=False):
        """Send SMS using HttpSMS API in batch mode
        
        :param list messages: list of SMS (grouped by content) to send:
          formatted as ```[
              {
                  'content' : str,
                  'numbers' : [
                      { 'uuid' : str, 'number' : str },
                      { 'uuid' : str, 'number' : str },
                      ...
                  ]
              }, ...
          ]```
        :param str delivery_reports_url: url to route receiving delivery reports (not used by HttpSMS)
        :return: response from the endpoint called, which is a list of results
          formatted as ```[
              {
                  uuid: UUID of the request,
                  state: ONE of: {
                      'success', 'processing', 'server_error', 'unregistered', 'insufficient_credit',
                      'wrong_number_format', 'duplicate_message', 'country_not_supported', 'registration_needed',
                  },
                  credit: Optional: Credits spent to send SMS (provided if the actual price is known)
              }, ...
          ]```
        """
        self._validate_config()
        
        results = []
        sms_count = 0
        
        # HttpSMS API sends one message at a time, so we need to iterate
        for message_group in messages:
            content = message_group.get('content', '')
            numbers = message_group.get('numbers', [])
            
            for number_info in numbers:
                uuid = number_info.get('uuid')
                number = number_info.get('number')
                
                # NOTE: Rate limiting logic has been moved to the caller (sms.sms model)
                # to allow transaction commits between sleeps.
                
                try:
                    result = self._send_single_sms(content, number, uuid)
                    results.append(result)
                    sms_count += 1
                except Exception as e:
                    _logger.error(f"Error sending SMS to {number}: {str(e)}")
                    results.append({
                        'uuid': uuid,
                        'state': 'server_error',
                    })
                    sms_count += 1
        
        return results
    
    def _send_single_sms(self, content, to_number, uuid):
        """Send a single SMS via HttpSMS API
        
        :param str content: SMS message content
        :param str to_number: Recipient phone number
        :param str uuid: Unique identifier for tracking
        :return: dict with uuid and state
        """
        headers = {
            'x-api-key': self.api_key,
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'content': content,
            'from': self.default_sender,
            'to': to_number,
        }
        
        try:
            _logger.info(f"Sending SMS to {to_number} via HttpSMS (endpoint: {self.endpoint})")
            response = requests.post(
                self.endpoint,
                headers=headers,
                data=json.dumps(payload),
                timeout=30
            )
            
            # Log response for debugging
            _logger.info(f"HttpSMS response status: {response.status_code}")
            
            if response.status_code == 200:
                response_data = response.json()
                
                # HttpSMS returns nested structure: {'data': {'id': '...'}, 'status': 'success'}
                # Log the full response for debugging
                _logger.info(f"HttpSMS response data: {response_data}")
                
                # Extract ID from nested data structure
                data = response_data.get('data', {})
                httpsms_id = data.get('id')
                _logger.info(f"SMS sent successfully to {to_number}, HttpSMS ID: {httpsms_id}")
                
                # Store HttpSMS message ID for tracking
                return {
                    'uuid': uuid,
                    'state': 'success',
                    'credit': 1,  # Assume 1 credit per SMS
                    'httpsms_id': httpsms_id,
                }
            elif response.status_code == 401:
                _logger.error("HttpSMS authentication failed - invalid API key")
                return {
                    'uuid': uuid,
                    'state': 'unregistered',
                }
            elif response.status_code == 400:
                error_data = response.json()
                error_message = error_data.get('message', 'Bad request')
                _logger.error(f"HttpSMS bad request: {error_message}")
                
                # Check for specific error types
                if 'phone' in error_message.lower() or 'number' in error_message.lower():
                    return {
                        'uuid': uuid,
                        'state': 'wrong_number_format',
                    }
                else:
                    return {
                        'uuid': uuid,
                        'state': 'server_error',
                    }
            elif response.status_code == 429:
                _logger.error("HttpSMS rate limit exceeded")
                return {
                    'uuid': uuid,
                    'state': 'server_error',
                }
            else:
                _logger.error(f"HttpSMS unexpected status code: {response.status_code}")
                return {
                    'uuid': uuid,
                    'state': 'server_error',
                }
                
        except requests.exceptions.Timeout:
            _logger.error(f"Timeout while sending SMS to {to_number}")
            return {
                'uuid': uuid,
                'state': 'server_error',
            }
        except requests.exceptions.ConnectionError:
            _logger.error(f"Connection error while sending SMS to {to_number}")
            return {
                'uuid': uuid,
                'state': 'server_error',
            }
        except Exception as e:
            _logger.error(f"Unexpected error sending SMS to {to_number}: {str(e)}")
            return {
                'uuid': uuid,
                'state': 'server_error',
            }
    
    def _get_sms_api_error_messages(self):
        """Return a mapping of error states to error messages
        
        This method maintains compatibility with the original Odoo SMS API
        """
        return {
            'unregistered': _("Invalid HttpSMS API key. Please check your configuration."),
            'insufficient_credit': _("HttpSMS account has insufficient credits."),
            'wrong_number_format': _("The number you're trying to reach is not correctly formatted."),
            'duplicate_message': _("This SMS has been removed as the number was already used."),
            'country_not_supported': _("The destination country is not supported by HttpSMS."),
            'incompatible_content': _("The content of the message violates rules applied by HttpSMS."),
            'registration_needed': _("Country-specific registration required for HttpSMS."),
        }
