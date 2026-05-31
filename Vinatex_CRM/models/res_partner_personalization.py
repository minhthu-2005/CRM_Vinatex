# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models


LOYALTY_RULE_HTML = """
<div>
    <h3>Quy định chấm điểm loyalty trong phạm vi CRM</h3>
    <p>Điểm khách hàng thân thiết được tính từ dữ liệu CRM của khách hàng, chưa bắt buộc phải có dữ liệu bán hàng/hóa đơn.</p>
    <ul>
        <li><b>Tình trạng khách hàng:</b> Lead mới +5, Đã liên hệ +5, Lead đủ điều kiện +10, Đã gửi báo giá +15, Đang thương lượng +20, Chốt thành công +30, Thất bại -15, Lâu chưa tương tác -20.</li>
        <li><b>Mức độ tiềm năng:</b> Cao +20, Trung bình +10, Thấp +5.</li>
        <li><b>Nhóm khách hàng:</b> Giá trị cao +20, Giá trị trung bình +10, Giá trị thấp +5, Lâu chưa tương tác -20.</li>
        <li><b>Nguồn lead:</b> Có nguồn lead +5.</li>
        <li><b>Giá trị CRM dự kiến:</b> Trên 500 triệu +20, trên 200 triệu +15, trên 50 triệu +10, có giá trị nhỏ hơn +5.</li>
        <li><b>Tương tác CRM:</b> 1 lần +5, từ 5 lần +10, từ 10 lần +15.</li>
        <li><b>Tương tác gần đây:</b> Trong 30 ngày +10; không tương tác từ 90 ngày -15; từ 180 ngày -25.</li>
        <li><b>Khiếu nại:</b> Mỗi khiếu nại -5 điểm, trừ tối đa 20 điểm.</li>
    </ul>
    <p><b>Ví dụ:</b> Khách hàng giá trị trung bình (+10), tiềm năng trung bình (+10), Lead mới (+5) sẽ có ít nhất 25 điểm nếu không có điểm trừ.</p>
    <p><b>Phân hạng:</b> VIP từ 80 điểm, Vàng từ 60 điểm, Bạc từ 35 điểm, dưới 35 là Tiêu chuẩn.</p>
    <p>Giai đoạn mở rộng có thể liên kết thêm dữ liệu bán hàng/hóa đơn để tính doanh thu thực tế và giá trị vòng đời khách hàng.</p>
</div>
"""


CARE_POLICY_RULE_HTML = """
<div>
    <h3>Quy định chọn chính sách chăm sóc ưu tiên</h3>
    <p>Chính sách chăm sóc ưu tiên là gợi ý nghiệp vụ cho nhân viên CRM khi chăm sóc khách hàng theo xếp hạng, tình trạng và tiềm năng.</p>
    <ul>
        <li><b>Ưu tiên phản hồi và lịch chăm sóc:</b> áp dụng cho khách VIP/Vàng, khách đang thương lượng hoặc khách có đơn hàng/yêu cầu sản xuất cần phản hồi nhanh.</li>
        <li><b>Quà tri ân khách hàng thân thiết:</b> áp dụng cho khách VIP/Vàng, khách hàng lâu năm, khách có mức độ tương tác tốt hoặc đã chốt thành công.</li>
        <li><b>Chiết khấu/ưu đãi theo tiềm năng:</b> áp dụng cho khách tiềm năng cao, khách đang cân nhắc báo giá hoặc cần kích hoạt mua lại.</li>
        <li><b>Tư vấn mẫu mã/nguyên phụ liệu:</b> áp dụng cho lead mới, khách chưa rõ nhu cầu, khách cần tư vấn mẫu thiết kế, chất liệu hoặc phương án gia công.</li>
        <li><b>Theo dõi điều khoản hợp tác:</b> áp dụng cho khách có yêu cầu riêng về thanh toán, tiến độ giao hàng, nguồn nguyên phụ liệu hoặc điều kiện sản xuất.</li>
    </ul>
    <p><b>Gợi ý nhanh:</b> VIP/Vàng ưu tiên chăm sóc nhanh và tri ân; Bạc ưu tiên theo dõi báo giá; Tiêu chuẩn tập trung tư vấn nhu cầu và nuôi dưỡng lead.</p>
</div>
"""


class ResPartner(models.Model):
    _inherit = "res.partner"

    crm_estimated_revenue = fields.Monetary(
        string="Giá trị CRM dự kiến",
        currency_field="company_currency_id",
        help="Giá trị dự kiến do bộ phận CRM/kinh doanh ghi nhận, dùng khi chưa tích hợp dữ liệu bán hàng/hóa đơn.",
    )
    company_currency_id = fields.Many2one(
        "res.currency",
        string="Tiền tệ công ty",
        default=lambda self: self.env.company.currency_id,
        readonly=True,
    )
    interaction_count = fields.Integer(
        string="Số lần tương tác CRM",
        compute="_compute_crm_personalization_metrics",
        store=True,
    )
    last_interaction_date = fields.Datetime(
        string="Lần tương tác gần nhất",
        compute="_compute_crm_personalization_metrics",
        store=True,
    )
    complaint_count = fields.Integer(
        string="Số khiếu nại",
        default=0,
        help="Có thể nhập tay hoặc sau này liên kết với hồ sơ khiếu nại để tự động tính.",
    )
    loyalty_score = fields.Integer(
        string="Điểm loyalty",
        compute="_compute_loyalty_profile",
        store=True,
    )
    loyalty_tier = fields.Selection(
        [
            ("standard", "Tiêu chuẩn"),
            ("silver", "Bạc"),
            ("gold", "Vàng"),
            ("vip", "VIP"),
        ],
        string="Xếp hạng",
        compute="_compute_loyalty_profile",
        store=True,
    )
    retention_segment = fields.Selection(
        [
            ("new", "Khách hàng mới"),
            ("active", "Đang chăm sóc"),
            ("loyal", "Khách hàng thân thiết"),
            ("at_risk", "Có nguy cơ rời bỏ"),
            ("dormant", "Lâu chưa tương tác"),
        ],
        string="Nhóm chăm sóc",
        compute="_compute_loyalty_profile",
        store=True,
    )
    personalization_note = fields.Text(
        string="Ghi chú cá nhân hóa",
        help="Ghi chú về nhu cầu may mặc, mẫu thiết kế, nguyên phụ liệu hoặc chính sách chăm sóc riêng.",
    )
    preferred_offer = fields.Selection(
        [
            ("discount", "Chiết khấu/ưu đãi theo tiềm năng"),
            ("priority", "Ưu tiên phản hồi và lịch chăm sóc"),
            ("credit", "Theo dõi điều khoản hợp tác"),
            ("gift", "Quà tri ân khách hàng thân thiết"),
            ("consulting", "Tư vấn mẫu mã/nguyên phụ liệu"),
        ],
        string="Chính sách chăm sóc ưu tiên",
    )

    @api.depends("message_ids.date")
    def _compute_crm_personalization_metrics(self):
        for partner in self:
            messages = partner.message_ids.filtered(lambda msg: msg.message_type in ("email", "comment"))
            partner.interaction_count = len(messages)
            dates = messages.mapped("date")
            partner.last_interaction_date = max(dates) if dates else False

    @api.depends(
        "segment", "customer_status", "potential_level", "lead_source_id",
        "crm_estimated_revenue", "interaction_count", "last_interaction_date",
        "complaint_count",
    )
    def _compute_loyalty_profile(self):
        today = fields.Date.context_today(self)
        for partner in self:
            score = 0
            days_since_interaction = None

            status_score = {
                "new": 5,
                "contacted": 5,
                "qualified": 10,
                "quotation": 15,
                "negotiation": 20,
                "won": 30,
                "lost": -15,
                "dormant": -20,
            }
            potential_score = {"high": 20, "medium": 10, "low": 5}
            segment_score = {"high": 20, "medium": 10, "low": 5, "dormant": -20}

            score += status_score.get(partner.customer_status, 0)
            score += potential_score.get(partner.potential_level, 0)
            score += segment_score.get(partner.segment, 0)

            if partner.lead_source_id:
                score += 5

            if partner.crm_estimated_revenue >= 500000000:
                score += 20
            elif partner.crm_estimated_revenue >= 200000000:
                score += 15
            elif partner.crm_estimated_revenue >= 50000000:
                score += 10
            elif partner.crm_estimated_revenue > 0:
                score += 5

            if partner.interaction_count >= 10:
                score += 15
            elif partner.interaction_count >= 5:
                score += 10
            elif partner.interaction_count >= 1:
                score += 5

            if partner.last_interaction_date:
                days_since_interaction = (today - partner.last_interaction_date.date()).days
                if days_since_interaction <= 30:
                    score += 10
                elif days_since_interaction >= 180:
                    score -= 25
                elif days_since_interaction >= 90:
                    score -= 15

            score -= min(partner.complaint_count * 5, 20)
            partner.loyalty_score = max(score, 0)

            if partner.loyalty_score >= 80:
                partner.loyalty_tier = "vip"
            elif partner.loyalty_score >= 60:
                partner.loyalty_tier = "gold"
            elif partner.loyalty_score >= 35:
                partner.loyalty_tier = "silver"
            else:
                partner.loyalty_tier = "standard"

            if partner.customer_status == "dormant" or partner.segment == "dormant":
                partner.retention_segment = "dormant"
            elif days_since_interaction is not None and days_since_interaction >= 90:
                partner.retention_segment = "at_risk"
            elif partner.loyalty_tier in ("gold", "vip"):
                partner.retention_segment = "loyal"
            elif partner.interaction_count or partner.customer_status in ("contacted", "qualified", "quotation", "negotiation", "won"):
                partner.retention_segment = "active"
            else:
                partner.retention_segment = "new"

    def action_open_loyalty_rules(self):
        self.ensure_one()
        wizard = self.env["campaign.loyalty.rule.wizard"].create({"rule_html": LOYALTY_RULE_HTML})
        return {
            "type": "ir.actions.act_window",
            "name": "Quy định chấm điểm loyalty",
            "res_model": "campaign.loyalty.rule.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }


    def action_open_care_policy_rules(self):
        self.ensure_one()
        wizard = self.env["campaign.loyalty.rule.wizard"].create({"rule_html": CARE_POLICY_RULE_HTML})
        return {
            "type": "ir.actions.act_window",
            "name": "Quy định chính sách chăm sóc",
            "res_model": "campaign.loyalty.rule.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }

    @api.model
    def _recompute_campaign_personalization_profiles(self):
        partners = self.search([])
        partners._compute_crm_personalization_metrics()
        partners._compute_loyalty_profile()
        return True

    @api.model
    def cron_sync_retention_segments(self):
        partners = self.search([])
        partners._compute_crm_personalization_metrics()
        partners._compute_loyalty_profile()
        dormant_date = fields.Date.context_today(self) - timedelta(days=90)
        partners.filtered(
            lambda p: p.last_interaction_date and p.last_interaction_date.date() <= dormant_date
        ).write({"segment": "dormant", "customer_status": "dormant"})
