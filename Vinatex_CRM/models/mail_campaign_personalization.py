# -*- coding: utf-8 -*-
from odoo import fields, models


class MailCampaign(models.Model):
    _inherit = "custom.mail.campaign"

    loyalty_tier = fields.Selection(
        [
            ("standard", "Tiêu chuẩn"),
            ("silver", "Bạc"),
            ("gold", "Vàng"),
            ("vip", "VIP"),
        ],
        string="Hạng khách hàng",
    )
    retention_segment = fields.Selection(
        [
            ("new", "Khách hàng mới"),
            ("active", "Đang giao dịch"),
            ("loyal", "Khách hàng thân thiết"),
            ("at_risk", "Có nguy cơ rời bỏ"),
            ("dormant", "Lâu chưa giao dịch"),
        ],
        string="Nhóm chăm sóc",
    )
    min_loyalty_score = fields.Integer(string="Điểm loyalty tối thiểu")
    personalization_goal = fields.Selection(
        [
            ("upsell", "Tăng doanh thu từ khách hàng hiện hữu"),
            ("retention", "Giữ chân khách hàng có nguy cơ rời bỏ"),
            ("winback", "Kích hoạt lại khách hàng lâu chưa giao dịch"),
            ("loyalty", "Tri ân khách hàng thân thiết"),
        ],
        string="Mục tiêu cá nhân hóa",
    )

    def _get_target_customers(self):
        partners = super()._get_target_customers()
        for campaign in self:
            if campaign.loyalty_tier:
                partners = partners.filtered(lambda partner: partner.loyalty_tier == campaign.loyalty_tier)
            if campaign.retention_segment:
                partners = partners.filtered(lambda partner: partner.retention_segment == campaign.retention_segment)
            if campaign.min_loyalty_score:
                partners = partners.filtered(lambda partner: partner.loyalty_score >= campaign.min_loyalty_score)
        return partners

    def action_create_loyalty_campaigns(self):
        template = self.env["mail.template"].search(
            [
                ("is_campaign_template", "=", True),
                ("campaign_template_type", "=", "loyalty"),
                ("model", "=", "res.partner"),
            ],
            limit=1,
        )
        if not template:
            return False

        for tier, label in [("vip", "VIP"), ("gold", "Vàng"), ("silver", "Bạc")]:
            partners = self.env["res.partner"].search([("loyalty_tier", "=", tier), ("email", "!=", False)])
            if partners:
                self.create(
                    {
                        "name": "Tri ân khách hàng thân thiết - %s" % label,
                        "template_id": template.id,
                        "recipient_ids": [(6, 0, partners.ids)],
                        "state": "draft",
                        "approved": False,
                        "loyalty_tier": tier,
                        "retention_segment": "loyal",
                        "personalization_goal": "loyalty",
                    }
                )
        return True
