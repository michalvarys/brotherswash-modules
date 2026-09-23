# SMS HttpSMS Integration for Odoo

This module replaces the default Odoo IAP SMS service with [HttpSMS](https://httpsms.com) API, allowing you to send SMS messages directly through HttpSMS without needing Odoo IAP credits.

## Features

- ✅ Direct integration with HttpSMS API
- ✅ No Odoo IAP credits required
- ✅ Compatible with all Odoo SMS features (SMS Marketing, CRM SMS, etc.)
- ✅ Full error handling and delivery tracking
- ✅ Easy configuration through Odoo settings
- ✅ Test connection functionality
- ✅ Maintains compatibility with existing SMS infrastructure

## Requirements

- Odoo 18.0 or later
- HttpSMS account (sign up at https://httpsms.com)
- Android phone configured as SMS gateway with HttpSMS app
- Python `requests` library (usually included with Odoo)

## Installation

1. **Copy the module to your Odoo addons directory:**
   ```bash
   cp -r varyshop/sms_httpsms /path/to/odoo/addons/
   ```

2. **Update the addons list:**
   - Go to Apps menu in Odoo
   - Click "Update Apps List"
   - Search for "SMS HttpSMS Integration"

3. **Install the module:**
   - Click "Install" on the SMS HttpSMS Integration module

## Configuration

### 1. Get HttpSMS API Key

1. Sign up at [httpsms.com](https://httpsms.com)
2. Install the HttpSMS app on your Android phone
3. Configure your phone as an SMS gateway
4. Get your API key from [HttpSMS Settings](https://httpsms.com/settings)

### 2. Configure Odoo

1. Go to **Settings > General Settings**
2. Scroll down to **SMS HttpSMS** section
3. Enter your **HttpSMS API Key**
4. Enter your **Default Sender Phone Number** (must be in international format with + prefix, e.g., `+18005550199`)
5. Click **Save**
6. Click **Test HttpSMS Connection** to verify your configuration

## Usage

Once configured, the module automatically replaces all SMS sending functionality in Odoo:

### Sending SMS from CRM
1. Open any Lead/Opportunity
2. Click "Send SMS" button
3. Compose your message
4. Click "Send" - the SMS will be sent via HttpSMS

### SMS Marketing Campaigns
1. Go to **SMS Marketing** app
2. Create a new SMS campaign
3. Select recipients and compose message
4. Send - all messages will be delivered via HttpSMS

### Automated SMS
All automated SMS (notifications, alerts, etc.) will automatically use HttpSMS.

## Technical Details

### Architecture

The module works by:
1. Inheriting the `sms.sms` model
2. Overriding the `_send()` method
3. Replacing IAP API calls with HttpSMS API calls
4. Maintaining compatibility with existing SMS tracking and delivery reports

### API Integration

The module uses the HttpSMS REST API:
- **Endpoint:** `https://api.httpsms.com/v1/messages/send`
- **Method:** POST
- **Authentication:** API Key via `x-api-key` header
- **Format:** JSON

### Error Handling

The module maps HttpSMS errors to Odoo SMS states:
- `200 OK` → Success
- `401 Unauthorized` → Invalid API key
- `400 Bad Request` → Wrong number format or invalid data
- `429 Too Many Requests` → Rate limit exceeded
- Other errors → Server error

### File Structure

```
sms_httpsms/
├── __init__.py
├── __manifest__.py
├── README.md
├── models/
│   ├── __init__.py
│   ├── sms_sms.py              # Override SMS sending
│   └── res_config_settings.py  # Configuration settings
├── tools/
│   ├── __init__.py
│   └── httpsms_api.py          # HttpSMS API client
└── views/
    └── res_config_settings_views.xml  # Settings UI
```

## Troubleshooting

### SMS not sending

1. **Check configuration:**
   - Verify API key is correct
   - Verify sender phone number is in international format (+...)
   - Use "Test HttpSMS Connection" button

2. **Check logs:**
   ```bash
   tail -f /var/log/odoo/odoo.log | grep -i httpsms
   ```

3. **Common issues:**
   - Invalid API key → Get new key from HttpSMS settings
   - Wrong phone format → Use international format with + prefix
   - Phone not connected → Check HttpSMS app on Android phone
   - Rate limit → Wait and try again

### Configuration not saving

- Make sure you have admin rights
- Check that the module is properly installed
- Restart Odoo server after installation

### Import errors

If you see import errors:
```bash
# Make sure the module is in the correct location
ls -la /path/to/odoo/addons/sms_httpsms

# Restart Odoo
sudo systemctl restart odoo
```

## Development

### Testing

To test the module:

1. **Manual testing:**
   - Configure the module
   - Send a test SMS from CRM or SMS Marketing
   - Check HttpSMS dashboard for delivery

2. **Check logs:**
   ```python
   # Enable debug logging
   import logging
   _logger = logging.getLogger(__name__)
   _logger.setLevel(logging.DEBUG)
   ```

### Extending

To customize the module:

1. **Custom sender per message:**
   Override `_send_single_sms()` in `httpsms_api.py`

2. **Delivery webhooks:**
   Implement webhook handler in controllers (HttpSMS supports webhooks)

3. **Custom error handling:**
   Extend error mapping in `httpsms_api.py`

## API Reference

### HttpSmsApi Class

```python
from odoo.addons.sms_httpsms.tools.httpsms_api import HttpSmsApi

# Initialize
api = HttpSmsApi(env)

# Send batch
results = api._send_sms_batch(messages, delivery_reports_url)

# Send single SMS
result = api._send_single_sms(content, to_number, uuid)
```

### Configuration Parameters

- `sms_httpsms.api_key` - HttpSMS API key
- `sms_httpsms.default_sender` - Default sender phone number

## Support

- **HttpSMS Documentation:** https://docs.httpsms.com/
- **HttpSMS GitHub:** https://github.com/NdoleStudio/httpsms-recipes
- **Odoo SMS Documentation:** https://www.odoo.com/documentation/18.0/developer/reference/backend/sms.html

## License

LGPL-3

## Author

VaryShop (https://www.varyshop.eu)

## Changelog

### Version 1.0.0 (2025-01-07)
- Initial release
- HttpSMS API integration
- Configuration UI
- Error handling
- Delivery tracking
- Test connection functionality
