{
    "name": "C\u00e1 nh\u00e2n h\u00f3a kh\u00e1ch h\u00e0ng v\u00e0 Loyalty - Vinatex \u0110\u00e0 N\u1eb5ng",
    "version": "17.0.1.0.0",
    "summary": "Ch\u1ea5m \u0111i\u1ec3m kh\u00e1ch h\u00e0ng, ph\u00e2n h\u1ea1ng loyalty v\u00e0 chi\u1ebfn d\u1ecbch ch\u0103m s\u00f3c c\u00e1 nh\u00e2n h\u00f3a",
    "category": "Marketing",
    "depends": [
        "base",
        "mail",
        "utm",
        "campaign",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/cron_personalization.xml",
        "data/email_template_personalization.xml",
        "views/res_partner_views.xml",
        "views/loyalty_rule_wizard_views.xml",
        "views/mail_campaign_views.xml",
        "views/personalization_menu.xml",
        "data/recompute_personalization.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "campaign_personalization/static/src/css/personalization_list.css",
        ],
    },
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
