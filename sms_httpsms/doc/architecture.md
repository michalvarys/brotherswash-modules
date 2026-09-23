# Architecture and Logic Overview

This module (`sms_httpsms`) integrates the HttpSMS service (httpsms.com) with Odoo, replacing the default IAP (In-App Purchase) SMS service.

## Core Architecture

### Odoo SMS Architecture
Odoo's native SMS handling is built around the `sms.sms` model and the `sms.api` tool.
1.  **Queue Processing**: Odoo uses a scheduled action (cron) `SMS: SMS Queue Manager` which calls `_process_queue` on `sms.sms`.
2.  **Batching**: `_process_queue` selects a batch of outgoing SMS (default 500) and calls the `send` method.
3.  **Provider Logic**: The `send` method eventually calls `_send` (protected method), which in standard Odoo interacts with `iap_mail` to send messages via Odoo's IAP servers.

### HttpSMS Integration Strategy
We override the `_send` method in `sms.sms` to redirect outgoing messages to the HttpSMS API instead of Odoo IAP.

## Implementation Details

### 1. SMS Sending (`models/sms_sms.py`)
We override `sms.sms._send` to implement our custom sending logic.

**Key challenges addressed:**
*   **Rate Limiting**: HttpSMS (and Android phones) have physical limitations on sending speed. We implement a configurable rate limit (default 60s) between messages.
*   **Transaction Timeouts**: Odoo cron jobs have a hard execution time limit (typically 120s or 300s). If we were to sleep for 60s between messages in a batch of 50, the transaction would take 50 minutes, causing Odoo to kill the thread and rollback the transaction. This rollback would revert SMS states from 'sent' to 'outgoing', causing duplicate sends on the next cron run (infinite loop).

**The Fix (Transaction Management):**
To handle rate limiting without losing state:
1.  We iterate through the batch of SMS records **individually**.
2.  For each SMS, we make the API call to HttpSMS.
3.  Upon success, we immediately update the SMS status to `pending` (Sent).
4.  **CRITICAL**: We call `self.env.cr.commit()` after *each* SMS. This saves the state change to the database permanently.
5.  We sleep for the configured rate limit duration *after* the commit.

If the cron job times out, only the *current* uncommitted work is lost. All previously sent SMS are already committed as `pending` and will not be picked up by the next cron run (which only looks for `outgoing` records).

### 2. Status Mapping
We map HttpSMS states to Odoo SMS states to ensure compatibility and correct behavior.

| HttpSMS Event/Status | Meaning | Odoo State | Odoo Label | Effect |
| :--- | :--- | :--- | :--- | :--- |
| API Call Success | Message queued on server | `pending` | Sent | **Prevents Resend**. Waiting for delivery report. |
| `message.phone.sent` | Sent from Android phone | `pending` | Sent | Confirmation that phone processed it. Still waiting for delivery. |
| `message.phone.delivered` | Delivered to recipient | `sent` | Delivered | Final success state. |
| `message.send.failed` | Failed to send | `error` | Error | Final failure state. |
| `message.send.expired` | TTL expired | `error` | Error | Final failure state. |

**Note on Odoo States:**
*   `outgoing`: The only state Odoo cron picks up for sending.
*   `pending`: Means "Sent to provider" in standard Odoo. It is **NOT** picked up by the send cron.
*   `sent`: Means "Delivered" in standard Odoo.

### 3. Duplicate Prevention
Duplicate sends are prevented by ensuring the SMS record transitions out of `outgoing` state immediately after the API call is successful.
*   **Mechanism**: The `_send` method sets state to `pending` and commits the transaction immediately.
*   **Safety**: Even if the subsequent sleep causes a timeout, the record is already saved as `pending`. The next cron execution filters for `state='outgoing'`, so it will **skip** this record.
*   **Webhooks**: The `message.phone.sent` webhook updates state to `pending` (idempotent if already pending). It does **not** revert to `outgoing`.

### 4. Webhooks (`controllers/main.py`)
We provide a webhook endpoint `/httpsms/webhook` to receive real-time status updates from HttpSMS.
*   **Security**: We verify the `X-Httpsms-Signature` header using the configured signing key.
*   **Flow**: Webhook events update the `sms.sms` record state.
    *   `message.phone.sent`: Sets state to `pending` (Sent).
    *   `message.phone.delivered`: Sets state to `sent` (Delivered).
*   **Chatter**: Incoming SMS (`message.phone.received`) are logged in the partner's chatter if the phone number matches a contact.

## Logic Flow Summary

1.  **Creation**: `sms.sms` record created with state `outgoing`.
2.  **Cron Job**: Picks up `outgoing` records.
3.  **Sending (`_send`)**:
    *   Calls HttpSMS API.
    *   Updates state to `pending` (Sent).
    *   **Commits Transaction**.
    *   Sleeps (Rate Limit).
4.  **Webhooks**:
    *   `message.phone.sent` -> Confirms `pending`.
    *   `message.phone.delivered` -> Updates to `sent` (Delivered).

This architecture ensures reliability, prevents duplicate sends even with strict rate limiting/timeouts, and provides accurate status tracking.
