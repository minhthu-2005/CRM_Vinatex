# -*- coding: utf-8 -*-
from odoo import api, fields, models


class MailTemplate(models.Model):
    _inherit = "mail.template"

    is_campaign_template = fields.Boolean(string="Dùng cho chiến dịch", default=False)
    campaign_template_type = fields.Selection(
        [
            ("welcome", "Chào mừng khách hàng"),
            ("follow_up", "Chăm sóc lại"),
            ("remarketing", "Remarketing khách hàng cũ"),
            ("subscription", "Subscription"),
            ("promotion", "Khuyến mãi"),
            ("thank_you", "Cảm ơn"),
        ],
        string="Loại mẫu",
        default=False,
    )
    campaign_usage_status = fields.Selection(
        [("active", "Đang dùng"), ("inactive", "Chưa dùng")],
        string="Trạng thái sử dụng",
        compute="_compute_campaign_usage_status",
        store=False,
    )

    @api.depends()
    def _compute_campaign_usage_status(self):
        usage_by_template = {}
        template_ids = [template.id for template in self if template.id]
        if template_ids:
            groups = self.env["custom.mail.campaign"].sudo().read_group(
                [("template_id", "in", template_ids)],
                ["template_id"],
                ["template_id"],
                lazy=False,
            )
            usage_by_template = {
                group["template_id"][0]: group.get("__count", 0)
                for group in groups
                if group.get("template_id")
            }
        for rec in self:
            rec.campaign_usage_status = "active" if usage_by_template.get(rec.id) else "inactive"

    @api.model
    def hide_legacy_campaign_templates(self):
        legacy_names = [
            "Email chào mừng khách hàng",
            "Email chăm sóc lại khách hàng",
            "Email Remarketing khách hàng cũ",
            "Email ch\u00c3\u00a0o m\u00c3\u00a1\u00bb\u00abng kh\u00c3\u00a1ch h\u00c3\u00a0ng",
            "Email ch\u00c4\u0192m s\u00c3\u00b3c l\u00c3\u00a1\u00ba\u00a1i kh\u00c3\u00a1ch h\u00c3\u00a0ng",
            "Email Remarketing kh\u00c3\u00a1ch h\u00c3\u00a0ng c\u00c3\u0085\u00c2\u00a9",
        ]
        self.search([("name", "in", legacy_names)]).write({
            "is_campaign_template": False,
            "campaign_template_type": False,
        })

    @api.model
    def cleanup_duplicate_campaign_templates(self):
        preferred_pairs = [
            ("campaign.template_welcome_email_vn", "crm_tong_hop.template_welcome_email_vn"),
            ("campaign.template_followup_email_vn", "crm_tong_hop.template_followup_email_vn"),
            ("campaign.template_remarketing_email_vn", "crm_tong_hop.template_remarketing_email_vn"),
            ("campaign.template_subscription_email_vn", "crm_tong_hop.template_subscription_email_vn"),
            ("campaign_personalization.template_loyalty_appreciation_vn", "crm_tong_hop.template_loyalty_appreciation_vn"),
        ]
        Campaign = self.env["custom.mail.campaign"].sudo()
        for old_xmlid, new_xmlid in preferred_pairs:
            old_template = self.env.ref(old_xmlid, raise_if_not_found=False)
            new_template = self.env.ref(new_xmlid, raise_if_not_found=False)
            if not old_template or not new_template or old_template == new_template:
                continue
            Campaign.search([("template_id", "=", old_template.id)]).write({
                "template_id": new_template.id,
            })
            old_template.write({
                "is_campaign_template": False,
                "campaign_template_type": False,
            })
        return True
