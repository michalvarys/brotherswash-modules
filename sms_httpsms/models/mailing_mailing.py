# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class Mailing(models.Model):
    _inherit = 'mailing.mailing'

    paused = fields.Boolean(
        string='Paused',
        default=False,
        help='When active, SMS/emails in the queue for this campaign will not be sent.'
    )

    def action_force_create_sms_queue(self):
        """Force create SMS records for recipients without existing mailing.trace.

        This button manually triggers SMS creation only for contacts that haven't
        been contacted yet in this campaign (no mailing.trace record exists).
        Useful for debugging when the automatic queue processing doesn't create SMS records.
        """
        self.ensure_one()

        if self.mailing_type != 'sms':
            raise UserError(_('This action is only available for SMS mailings.'))

        # Get all recipients from the filter (without any filtering)
        all_recipients = self._get_recipients()
        _logger.info(f"FORCE CREATE SMS - Mailing {self.id}: Total recipients in filter = {len(all_recipients)}")

        # Get only remaining recipients (those without mailing.trace records)
        res_ids = self._get_remaining_recipients()
        already_contacted = len(all_recipients) - len(res_ids)

        _logger.info(f"FORCE CREATE SMS - Mailing {self.id}: Remaining recipients (without trace) = {len(res_ids)}, Already contacted = {already_contacted}")

        if not res_ids:
            # Check if there are any recipients at all
            if not all_recipients:
                raise UserError(_(
                    'No recipients found matching the mailing filter.\n\n'
                    'Please check your mailing domain/filter configuration.'
                ))
            else:
                # Get trace details for debugging
                trace_count = self.env['mailing.trace'].search_count([
                    ('mass_mailing_id', '=', self.id)
                ])
                sms_count = self.env['sms.sms'].search_count([
                    ('mailing_id', '=', self.id)
                ])

                raise UserError(_(
                    'All recipients have already been contacted in this campaign.\n\n'
                    'Recipients in filter: %(total)s\n'
                    'Already contacted: %(contacted)s\n'
                    'Existing mailing.trace records: %(traces)s\n'
                    'Existing sms.sms records: %(sms)s\n\n'
                    'If you want to resend, please delete the existing mailing.trace records first.'
                ) % {
                    'total': len(all_recipients),
                    'contacted': already_contacted,
                    'traces': trace_count,
                    'sms': sms_count
                })

        _logger.info(f"FORCE CREATE SMS - Mailing {self.id}: Creating SMS for {len(res_ids)} recipients")

        try:
            # Set mailing to 'sending' state if it's not already
            if self.state == 'in_queue':
                self.state = 'sending'

            # Create composer values
            composer_vals = self._send_sms_get_composer_values(res_ids)
            _logger.info(f"FORCE CREATE SMS - Composer values: {composer_vals}")

            # Create composer and execute
            composer = self.env['sms.composer'].with_context(active_id=False).create(composer_vals)
            _logger.info(f"FORCE CREATE SMS - Composer created: {composer.id}")

            # Execute SMS creation (this also creates mailing.trace records and updates tracking URLs)
            sms_records = composer._action_send_sms()
            _logger.info(f"FORCE CREATE SMS - Created SMS records: {sms_records}")

            # Verify tracking URLs and mailing.trace records were created
            if sms_records:
                sample_sms = sms_records[0] if sms_records else None
                if sample_sms:
                    # Check for tracking URLs
                    if sample_sms.body and '/s/' in sample_sms.body:
                        _logger.info(f"FORCE CREATE SMS - Tracking URLs verified. Sample SMS {sample_sms.id} body contains /s/{sample_sms.id} tracking")
                    elif sample_sms.body:
                        _logger.warning(f"FORCE CREATE SMS - No tracking URLs found in sample SMS {sample_sms.id}. Body: {sample_sms.body[:100]}")

                    # Check for mailing.trace records
                    trace_count = len(sample_sms.mailing_trace_ids)
                    if trace_count > 0:
                        trace = sample_sms.mailing_trace_ids[0]
                        _logger.info(f"FORCE CREATE SMS - Mailing trace verified. Sample SMS {sample_sms.id} has trace {trace.id} with code {trace.sms_code}")
                    else:
                        _logger.warning(f"FORCE CREATE SMS - No mailing.trace found for sample SMS {sample_sms.id}")

            # Count created SMS by state
            if sms_records:
                sms_count = len(sms_records)
                outgoing_count = len(sms_records.filtered(lambda s: s.state == 'outgoing'))
                canceled_count = len(sms_records.filtered(lambda s: s.state == 'canceled'))

                message = _(
                    'Successfully created %(created)s SMS records for NEW recipients:\n\n'
                    '- Ready to send (outgoing): %(outgoing)s\n'
                    '- Canceled (invalid/blacklisted): %(canceled)s\n\n'
                    'Total in filter: %(total)s\n'
                    'Already contacted: %(already)s\n'
                    'Newly added to queue: %(created)s'
                ) % {
                    'created': sms_count,
                    'outgoing': outgoing_count,
                    'canceled': canceled_count,
                    'total': len(all_recipients),
                    'already': already_contacted,
                }

                _logger.info(f"FORCE CREATE SMS - {message}")
            else:
                message = _('No SMS records were created. Check the logs for details.')
                _logger.warning(f"FORCE CREATE SMS - No SMS records created for mailing {self.id}")

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('SMS Queue Created'),
                    'message': message,
                    'type': 'success' if sms_records else 'warning',
                    'sticky': True,
                }
            }

        except Exception as e:
            _logger.error(f"FORCE CREATE SMS - Error for mailing {self.id}: {e}", exc_info=True)
            raise UserError(_(
                'Failed to create SMS records.\n\n'
                'Error: %s\n\n'
                'Please check the server logs for more details.'
            ) % str(e))
