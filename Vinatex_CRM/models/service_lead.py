from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    fail_reason = fields.Char(string="Lý do thất bại", tracking=True)
    first_response_date = fields.Datetime(string="Thời gian phản hồi đầu tiên", tracking=True)
    response_time_hours = fields.Float(
        string="Thời gian phản hồi (giờ)",
        compute="_compute_response_time_hours",
        store=True,
    )
    complaint_count = fields.Integer(
        string="Khiếu nại",
        compute="_compute_complaint_count",
    )
    satisfaction_score = fields.Integer(string="Điểm hài lòng")
    is_repurchase = fields.Boolean(string="Mua lại")

    @api.depends("create_date", "first_response_date")
    def _compute_response_time_hours(self):
        for lead in self:
            if lead.create_date and lead.first_response_date:
                delta = lead.first_response_date - lead.create_date
                lead.response_time_hours = delta.total_seconds() / 3600.0
            else:
                lead.response_time_hours = 0.0

    def _compute_complaint_count(self):
        grouped = self.env["crm.service.complaint.ticket"].read_group(
            [("lead_id", "in", self.ids)],
            ["lead_id"],
            ["lead_id"],
        )
        counts = {item["lead_id"][0]: item["lead_id_count"] for item in grouped}
        for lead in self:
            lead.complaint_count = counts.get(lead.id, 0)

    def action_view_complaints(self):
        self.ensure_one()
        action = self.env.ref("crm_tong_hop.action_complaint_ticket").read()[0]
        action["domain"] = [("lead_id", "=", self.id)]
        action["context"] = {
            "default_lead_id": self.id,
            "default_customer_id": self.partner_id.id,
            "default_sale_user_id": self.user_id.id,
        }
        return action
