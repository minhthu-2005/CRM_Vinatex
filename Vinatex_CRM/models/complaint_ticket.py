from datetime import timedelta

from odoo import api, fields, models


class ComplaintTicket(models.Model):
    _name = "crm.service.complaint.ticket"
    _description = "Phiếu khiếu nại khách hàng"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char(
        string="Mã phiếu",
        required=True,
        copy=False,
        readonly=True,
        default="Mới",
        tracking=True,
    )
    customer_id = fields.Many2one(
        "res.partner",
        string="Khách hàng",
        required=True,
        tracking=True,
    )
    lead_id = fields.Many2one(
        "crm.lead",
        string="Lead / Cơ hội",
        tracking=True,
        ondelete="set null",
    )
    sale_user_id = fields.Many2one(
        "res.users",
        string="Nhân viên bán hàng",
        default=lambda self: self.env.user,
        tracking=True,
    )
    assigned_user_id = fields.Many2one(
        "res.users",
        string="Người phụ trách",
        default=lambda self: self.env.user,
        tracking=True,
    )
    title = fields.Char(string="Tiêu đề", required=True, tracking=True)
    description = fields.Text(string="Mô tả")
    severity = fields.Selection(
        [
            ("high", "Cao"),
            ("medium", "Trung bình"),
            ("low", "Thấp"),
        ],
        string="Mức độ",
        required=True,
        default="medium",
        tracking=True,
    )
    state = fields.Selection(
        [
            ("open", "Đang mở"),
            ("processing", "Đang xử lý"),
            ("resolved", "Đã xử lý"),
            ("closed", "Đã đóng"),
        ],
        string="Trạng thái",
        required=True,
        default="open",
        tracking=True,
    )
    deadline = fields.Datetime(string="Hạn SLA", tracking=True)
    response_date = fields.Datetime(string="Thời gian phản hồi đầu tiên", tracking=True)
    resolved_date = fields.Datetime(string="Thời gian xử lý xong", tracking=True)
    sla_status = fields.Selection(
        [
            ("on_time", "Đúng hạn"),
            ("late", "Trễ hạn"),
        ],
        string="Trạng thái SLA",
        compute="_compute_sla_status",
        store=True,
        tracking=True,
    )
    root_cause = fields.Text(string="Nguyên nhân gốc")
    solution = fields.Text(string="Giải pháp")
    customer_feedback = fields.Text(string="Phản hồi khách hàng")
    satisfaction_score = fields.Integer(string="Điểm hài lòng")

    @api.model
    def _sla_hours_by_severity(self):
        return {
            "high": 4,
            "medium": 24,
            "low": 48,
        }

    @api.depends("deadline", "response_date", "resolved_date", "state")
    def _compute_sla_status(self):
        now = fields.Datetime.now()
        for ticket in self:
            compare_date = ticket.response_date or ticket.resolved_date
            if not ticket.deadline:
                ticket.sla_status = False
            elif compare_date:
                ticket.sla_status = "on_time" if compare_date <= ticket.deadline else "late"
            elif ticket.state in ("resolved", "closed"):
                ticket.sla_status = "late"
            else:
                ticket.sla_status = "late" if now > ticket.deadline else "on_time"

    @api.onchange("severity")
    def _onchange_severity(self):
        for ticket in self:
            if ticket.severity:
                ticket.deadline = self._get_sla_deadline(ticket.severity)

    @api.model
    def _get_sla_deadline(self, severity):
        hours = self._sla_hours_by_severity().get(severity, 24)
        return fields.Datetime.now() + timedelta(hours=hours)

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", "Mới") in ("New", "Mới"):
                vals["name"] = sequence.next_by_code("crm.service.complaint.ticket") or "Mới"
            if vals.get("severity") and not vals.get("deadline"):
                vals["deadline"] = self._get_sla_deadline(vals["severity"])
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("severity") and not vals.get("deadline"):
            vals["deadline"] = self._get_sla_deadline(vals["severity"])
        if vals.get("state") in ("processing", "resolved", "closed") and not vals.get("response_date"):
            for ticket in self.filtered(lambda item: not item.response_date):
                ticket.response_date = fields.Datetime.now()
        if vals.get("state") in ("resolved", "closed") and not vals.get("resolved_date"):
            vals["resolved_date"] = fields.Datetime.now()
        return super().write(vals)

    def action_processing(self):
        self.write({"state": "processing"})

    def action_resolved(self):
        self.write({"state": "resolved"})

    def action_closed(self):
        self.write({"state": "closed"})

    def action_reopen(self):
        self.write({"state": "open"})
