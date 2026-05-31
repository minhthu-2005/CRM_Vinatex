{
    'name': 'CRM Analytics Management',
    'version': '17.0.1.0.0',
    'category': 'CRM',
    'summary': 'CRM analytics for dashboard KPI, lead conversion, sales performance, retention and lost deal tracking',
    'license': 'LGPL-3',
    'depends': [
        'crm',
        'sale_management',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/security_rules.xml',
        'views/crm_analytics_kpi_views.xml',
        'views/crm_conversion_report_views.xml',
        'views/crm_sales_performance_views.xml',
        'views/crm_customer_retention_views.xml',
        'views/crm_lost_reason_analytics_views.xml',
        'data/cron.xml',
    ],
    'installable': True,
    'application': True,
}