{
    'name': 'Quản lý hồ sơ CSKH',
    'version': '1.0',
    'summary': 'Quản lý hồ sơ chăm sóc khách hàng trên CRM',
    'category': 'CRM',

    # KẾ THỪA MODULE CRM + MAIL
    'depends': [
        'crm',
        'mail',
    ],

    'data': [
        'security/ir.model.access.csv',

        'data/sequence.xml',
        'data/mail_template.xml',
        'data/cron_job.xml',

        'views/crm_cskh_profile_views.xml',
        'views/crm_lead_views.xml',
        'views/crm_cskh_workflow_rule_views.xml',
        'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'Ho_So_CSKH/static/src/js/cskh_form_helpers.js',
        ],
    },

    'installable': True,
    'application': True,
}
