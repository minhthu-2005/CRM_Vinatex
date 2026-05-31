# -*- coding: utf-8 -*-
from odoo import fields, models


class MailTemplate(models.Model):
    _inherit = "mail.template"

    campaign_template_type = fields.Selection(
        selection_add=[
            ("loyalty", "Chương trình khách hàng thân thiết"),
            ("retention", "Chăm sóc giữ chân khách hàng"),
            ("vip_offer", "Ưu đãi cá nhân hóa cho khách VIP"),
        ],
        ondelete={
            "loyalty": "set null",
            "retention": "set null",
            "vip_offer": "set null",
        },
    )
