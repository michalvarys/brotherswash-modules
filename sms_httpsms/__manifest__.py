# -*- coding: utf-8 -*-
{
    'name': 'SMS HttpSMS Integration',
    'version': '18.0.1.0.2',
    'category': 'Hidden/Tools',
    'summary': 'Replace Odoo IAP SMS with HttpSMS API',
    'description': """
HttpSMS Integration for Odoo SMS
=================================

This module replaces the default Odoo IAP SMS service with HttpSMS API.

Features:
---------
* Direct integration with HttpSMS API (https://httpsms.com)
* Bypasses the need for Odoo IAP credits
* Compatible with existing SMS and Mass Mailing SMS modules
* Configurable API key and default sender phone number
* Full support for SMS sending, delivery reports, and error handling

Configuration:
--------------
1. Get your API key from https://httpsms.com/settings
2. Go to Settings > General Settings > SMS HttpSMS
3. Enter your API key and default sender phone number
4. Save and start sending SMS!
    """,
    'author': 'VaryShop',
    'website': 'https://www.varyshop.eu',
    'depends': [
        'base_setup',
        'sms',
        'mass_mailing_sms',
    ],
    'data': [
        'views/res_config_settings_views.xml',
        'views/mailing_mailing_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
