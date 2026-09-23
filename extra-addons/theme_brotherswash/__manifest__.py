{
    'name': 'Brothers Wash Detailing Theme',
    'description': 'Premium auto detailing website theme for Brothers Wash Detailing Praha 5.',
    'category': 'Theme/Services',
    'version': '18.0.7.0.0',
    'author': 'Michal Varys',
    'depends': [
        'theme_common',
        'website',
        'bw_booking',
    ],
    'data': [
        'data/ir_asset.xml',
        'data/generate_primary_template.xml',
        'data/menu.xml',

        'views/snippets/s_bwd_hero.xml',
        'views/snippets/s_bwd_about.xml',
        'views/snippets/s_bwd_premium.xml',
        'views/snippets/s_bwd_programs.xml',
        'views/snippets/s_bwd_extras.xml',
        'views/snippets/s_bwd_reviews.xml',
        'views/snippets/s_bwd_gallery.xml',
        'views/snippets/s_bwd_booking.xml',
        'views/snippets/s_bwd_contact.xml',
        'views/snippets/s_bwd_footer.xml',
        'views/snippets/snippets_registry.xml',

        'views/layout.xml',
        'views/pages.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'theme_brotherswash/static/src/js/main.js',
            'theme_brotherswash/static/src/js/booking_form.js',
            'theme_brotherswash/static/src/js/snippets.js',
        ],
    },
    'images': [
        'static/description/banner.png',
    ],
    'license': 'LGPL-3',
    'application': False,
    'installable': True,
}
