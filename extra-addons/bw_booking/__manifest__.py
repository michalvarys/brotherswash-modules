{
    'name': 'Brothers Wash Booking',
    'description': 'Service configurator, booking system with CRM and calendar integration for Brothers Wash Detailing.',
    'category': 'Website/Services',
    'version': '18.0.1.0.0',
    'author': 'Michal Varys',
    'depends': [
        'website',
        'crm',
        'calendar',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/bw_vehicle_type_data.xml',
        'data/bw_service_data.xml',
        'data/res_company_data.xml',
        'data/mail_template_data.xml',
        'views/bw_service_views.xml',
        'views/bw_booking_views.xml',
        'views/booking_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'bw_booking/static/src/scss/booking.scss',
            'bw_booking/static/src/js/configurator.js',
        ],
    },
    'license': 'LGPL-3',
    'application': True,
    'installable': True,
}
