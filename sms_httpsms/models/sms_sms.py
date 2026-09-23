# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from werkzeug.urls import url_join

import time
from odoo import api, fields, models, tools
from odoo.addons.sms_httpsms.tools.httpsms_api import HttpSmsApi

_logger = logging.getLogger(__name__)


class SmsSms(models.Model):
    """Override SMS model to use HttpSMS instead of IAP"""

    _inherit = 'sms.sms'

    # Extend failure_type selection to include HttpSMS-specific error codes
    failure_type = fields.Selection(
        selection_add=[
            ('sms_expired', 'Expired'),
            ('sms_invalid_destination', 'Invalid Destination'),
        ],
        ondelete={
            'sms_expired': 'cascade',
            'sms_invalid_destination': 'cascade',
        }
    )

    @api.model
    def cleanup_stuck_sms(self):
        """EMERGENCY CLEANUP: Mark all stuck SMS (pending/outgoing with mailing_id) as sent

        This should be run ONCE to clean up the duplicate SMS problem.
        After this, the fixed _send method will prevent new stuck SMS.
        """
        stuck_sms = self.sudo().search([
            ('mailing_id', '!=', False),
            ('state', 'in', ['pending', 'outgoing'])
        ])

        if stuck_sms:
            _logger.warning(f"CLEANUP: Found {len(stuck_sms.ids)} stuck SMS in pending/outgoing state: {stuck_sms.ids}")
            _logger.warning(f"CLEANUP: These SMS will be marked as 'sent' to prevent duplicate sends")

            # Mark all stuck SMS as sent
            stuck_sms.sms_tracker_id._action_update_from_sms_state('sent')
            stuck_sms.write({'state': 'sent', 'failure_type': False})

            _logger.warning(f"CLEANUP: Marked {len(stuck_sms.ids)} stuck SMS as SENT")

            # Also update their mailings
            mailings = stuck_sms.mapped('mailing_id').filtered(lambda m: m.state == 'sending')
            for mailing in mailings:
                pending_count = self.sudo().search_count([
                    ('mailing_id', '=', mailing.id),
                    ('state', 'in', ['outgoing', 'pending'])
                ])
                if pending_count == 0:
                    mailing.sudo().write({'state': 'done', 'sent_date': fields.Datetime.now()})
                    _logger.warning(f"CLEANUP: Marked mailing {mailing.id} as done")
        else:
            _logger.info("CLEANUP: No stuck SMS found")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'SMS Cleanup Complete',
                'message': f'Cleaned up {len(stuck_sms.ids)} stuck SMS messages.',
                'type': 'success',
                'sticky': False,
            }
        }

    @api.model
    def _update_sms_delivery_status(self, httpsms_id, status, failure_code=None):
        """ Update the delivery status of an SMS message based on a webhook event.
            :param httpsms_id: The HttpSMS message ID.
            :param status: The new status ('sent', 'delivered', or 'error').
            :param failure_code: The failure code if the status is 'error'.

            CRITICAL: Only update if SMS is not already in final state!
            Never change 'sent' back to 'pending' - this would cause duplicate sends!
        """
        sms = self.sudo().search([('uuid', '=', httpsms_id)], limit=1)
        if not sms:
            _logger.warning(f"HttpSMS webhook: SMS with HttpSMS ID {httpsms_id} not found.")
            return

        # CRITICAL: Don't downgrade state from 'sent' to 'pending'
        # If SMS is already marked as 'sent', only allow upgrade to 'delivered' or downgrade to 'error'
        if sms.state == 'sent' and status in ['pending', 'process']:
            _logger.info(f"HttpSMS webhook: Ignoring status '{status}' for SMS {sms.id} - already marked as sent")
            return

        vals = {'state': status}
        if status == 'error' and failure_code:
            vals['failure_type'] = failure_code

        sms.write(vals)
        _logger.info(f"HttpSMS: Marked SMS {sms.id} as {status} (HttpSMS ID: {httpsms_id})")

    def write(self, vals):
        res = super(SmsSms, self).write(vals)
        if 'state' in vals:
            self._update_mailing_trace_status(vals)
        return res

    def _check_mailing_completion(self, traces):
        """ Check if all SMS for a mailing have been sent and update mailing status to 'done'. """
        for trace in traces:
            if not trace.mass_mailing_id:
                continue

            mailing = trace.mass_mailing_id

            # Only check mailings that are currently in 'sending' state
            if mailing.state != 'sending':
                continue

            # Skip completion check if mailing is paused
            if mailing.paused:
                _logger.info(f"Mailing {mailing.id} is paused, skipping completion check")
                continue

            # Count pending SMS for this mailing
            pending_count = self.env['sms.sms'].sudo().search_count([
                ('mailing_id', '=', mailing.id),
                ('state', 'in', ['outgoing', 'pending'])
            ])

            # If no pending SMS, mark mailing as done
            if pending_count == 0:
                _logger.info(f"All SMS for mailing {mailing.id} have been processed. Marking as done.")
                mailing.sudo().write({'state': 'done', 'sent_date': fields.Datetime.now()})

    def _update_mailing_trace_status(self, vals):
        """ Update the status of the related mailing.trace records and check if mailing is complete. """
        for sms in self:
            traces = self.env['mailing.trace'].sudo().search([('sms_id_int', '=', sms.id)])
            if not traces:
                continue

            trace_vals = {}
            if vals['state'] == 'sent':
                trace_vals['trace_status'] = 'sent'
                trace_vals['sent_datetime'] = fields.Datetime.now()
            elif vals['state'] == 'error':
                trace_vals['trace_status'] = 'failed'
                if sms.failure_type:
                    trace_vals['failure_type'] = sms.failure_type

            if trace_vals:
                traces.write(trace_vals)

                # Check if all SMS for this mailing have been processed
                self._check_mailing_completion(traces)

    def _send(self, unlink_failed=False, unlink_sent=True, raise_exception=False):
        """Override _send method to use HttpSMS API instead of IAP

        This method replaces the IAP SMS sending with HttpSMS API calls
        while maintaining compatibility with the existing Odoo SMS infrastructure.

        CRITICAL CHANGE: This method now iterates over SMS records individually
        and commits the transaction after each send. This prevents the "Transaction Rollback"
        issue where a cron timeout (due to rate limiting sleeps) would cause all
        sent SMS to revert to 'pending' state, causing infinite duplicate sends.
        """
        if not self:
            return

        # If HttpSMS is not configured (no API key or sender), pass to next provider
        ICP = self.env['ir.config_parameter'].sudo()
        api_key = ICP.get_param('sms_httpsms.api_key')
        sender = ICP.get_param('sms_httpsms.default_sender')
        if not api_key or not sender:
            return super(SmsSms, self)._send(
                unlink_failed=unlink_failed,
                unlink_sent=unlink_sent,
                raise_exception=raise_exception,
            )

        # Skip SMS assigned to another provider (e.g. sms_provider='gateway')
        httpsms_records = self.filtered(lambda s: not s.sms_provider)
        other_records = self - httpsms_records
        if other_records:
            super(SmsSms, other_records)._send(
                unlink_failed=unlink_failed,
                unlink_sent=unlink_sent,
                raise_exception=raise_exception,
            )
        if not httpsms_records:
            return

        # Get rate limit configuration (in seconds)
        rate_limit = int(ICP.get_param('sms_httpsms.rate_limit', 60))

        api_client = HttpSmsApi(self.env)
        delivery_reports_url = url_join(httpsms_records[0].get_base_url(), '/sms/status')

        # We need to check which mailings might be involved
        related_mailings = httpsms_records.mapped('mailing_id').filtered(lambda m: m.state == 'sending')

        total_processed = 0
        total_to_process = len(httpsms_records)

        for sms in httpsms_records:
            # Check if mailing is paused
            if sms.mailing_id and sms.mailing_id.paused:
                _logger.info(f'Skipping SMS {sms.id} - mailing {sms.mailing_id.id} is paused')
                continue  # Skip this SMS, it stays in 'outgoing' state

            total_processed += 1

            # Prepare message structure for the API tool (it expects a batch format)
            messages = [{
                'content': sms.body,
                'numbers': [{'number': sms.number, 'uuid': sms.uuid}],
            }]
            
            results = []
            try:
                # Send single SMS using the API client
                # Note: _send_sms_batch in httpsms_api.py has been modified to NOT sleep
                results = api_client._send_sms_batch(messages, delivery_reports_url=delivery_reports_url)
                _logger.info('Sent SMS %s via HttpSMS: results=%s', sms.id, results)
            except Exception as e:
                _logger.error('Failed to send SMS %s via HttpSMS: %s', sms.id, e)
                if raise_exception:
                    raise
                results = [{'uuid': sms.uuid, 'state': 'server_error'}]
            
            # Process the result for this single SMS immediately
            self._process_single_sms_result(sms, results, unlink_failed, unlink_sent)
            
            # CRITICAL: Commit transaction after EACH SMS to persist the 'sent' state
            # This ensures that even if the cron times out during the sleep below,
            # this SMS is already saved as 'sent' and won't be picked up again.
            self.env.cr.commit()
            
            # Apply rate limiting
            if rate_limit > 0 and total_processed < total_to_process:
                _logger.info(f"Rate limiting: waiting {rate_limit} seconds before next SMS...")
                time.sleep(rate_limit)

        # After processing all SMS, check if any mailings are complete
        # We need to re-fetch mailings because their state might have changed or counters updated
        for mailing in related_mailings:
            # Skip completion check if mailing is paused
            if mailing.paused:
                _logger.info(f"Mailing {mailing.id} is paused, skipping completion check")
                continue

            # Check if there are any pending SMS left for this mailing
            # We use a new cursor or search to be sure we see committed data,
            # though inside the same env it should be fine.
            pending_count = self.env['sms.sms'].sudo().search_count([
                ('mailing_id', '=', mailing.id),
                ('state', 'in', ['outgoing', 'pending'])
            ])
            if pending_count == 0:
                _logger.info(f"All SMS for mailing {mailing.id} have been processed. Marking as done.")
                mailing.sudo().write({'state': 'done', 'sent_date': fields.Datetime.now()})
                self.env.cr.commit()

    def _process_single_sms_result(self, sms, results, unlink_failed, unlink_sent):
        """Process result for a single SMS record and update its state"""
        if not results:
            return

        # We expect only one result since we sent one SMS
        result = results[0]
        iap_state = result['state']
        httpsms_id = result.get('httpsms_id')
        
        sms_sudo = sms.sudo().with_context(sms_skip_msg_notification=True)
        
        if httpsms_id:
            sms_sudo.write({'uuid': httpsms_id})
            _logger.info(f"Updated SMS {sms.id} with HttpSMS ID: {httpsms_id}")

        # Update SMS state
        if iap_state == 'success':
            # Mark as 'pending' (Sent) initially. Webhooks will update to 'sent' (Delivered) later.
            # Note: Since we commit after each SMS, 'pending' is safe from duplicates (cron only picks 'outgoing')
            sms_sudo.sms_tracker_id._action_update_from_sms_state('pending')
            # Don't delete yet if we are waiting for delivery report
            sms_sudo.write({'state': 'pending', 'failure_type': False})
            _logger.info(f'Marked SMS {sms.id} as PENDING (success from HttpSMS)')
        elif success_state := self.IAP_TO_SMS_STATE_SUCCESS.get(iap_state):
            sms_sudo.sms_tracker_id._action_update_from_sms_state(success_state)
            to_delete = {'to_delete': True} if unlink_sent else {}
            sms_sudo.write({'state': success_state, 'failure_type': False, **to_delete})
        else:
            failure_type = self.IAP_TO_SMS_FAILURE_TYPE.get(iap_state, 'unknown')
            if failure_type != 'unknown':
                sms_sudo.sms_tracker_id._action_update_from_sms_state('error', failure_type=failure_type)
            else:
                sms_sudo.sms_tracker_id._action_update_from_provider_error(iap_state)
            to_delete = {'to_delete': True} if unlink_failed else {}
            sms_sudo.write({'state': 'error', 'failure_type': failure_type, **to_delete})
        
        # Update mail message notifications
        sms_sudo.mail_message_id._notify_message_notification_update()
