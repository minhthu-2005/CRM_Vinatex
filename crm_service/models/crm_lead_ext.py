from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    fail_reason = fields.Char(string="Lý do thất bại", tracking=True)
    first_response_date = fields.Datetime(string="Ngày phản hồi đầu tiên", tracking=True)
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
        for lead in self:
            lead.complaint_count = 0

        leads = self.filtered("id")
        if not leads:
            return

        grouped = self.env["crm.service.complaint.ticket"]._read_group(
            [("lead_id", "in", leads.ids)],
            ["lead_id"],
            ["__count"],
        )
        counts = {lead.id: count for lead, count in grouped}
        for lead in leads:
            lead.complaint_count = counts.get(lead.id, 0)

    def action_view_complaints(self):
        self.ensure_one()
        action = self.env.ref("thuc_linh_crm_service.action_complaint_ticket").read()[0]
        action["domain"] = [("lead_id", "=", self.id)]
        action["context"] = {
            "default_lead_id": self.id,
            "default_customer_id": self.partner_id.id,
            "default_sale_user_id": self.user_id.id,
        }
        return action
