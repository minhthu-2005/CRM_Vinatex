from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ComplaintTicket(models.Model):
    _name = "crm.service.complaint.ticket"
    _description = "Phiếu Khiếu Nại Khách Hàng"
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
        string="Nhân viên kinh doanh",
        default=lambda self: self.env.user,
        tracking=True,
    )
    assigned_user_id = fields.Many2one(
        "res.users",
        string="Người xử lý",
        default=lambda self: self.env.user,
        tracking=True,
    )
    feedback_request_id = fields.Many2one(
        "crm.service.feedback.request",
        string="Phản hồi nguồn",
        readonly=True,
        copy=False,
        tracking=True,
    )
    title = fields.Char(string="Tiêu đề", required=True, tracking=True)
    description = fields.Text(string="Nội dung")
    related_document_ref = fields.Char(
        string="Đơn hàng / Dịch vụ liên quan",
        tracking=True,
        help="Tham chiếu đơn hàng, hợp đồng dịch vụ, giao hàng hoặc chứng từ nghiệp vụ liên quan.",
    )
    severity = fields.Selection(
        [
            ("high", "Cao"),
            ("medium", "Trung bình"),
            ("low", "Thấp"),
        ],
        string="Mức ưu tiên",
        required=True,
        default="medium",
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Mới"),
            ("open", "Đã tiếp nhận"),
            ("processing", "Đang xử lý"),
            ("resolved", "Đã xử lý"),
            ("closed", "Đã đóng"),
        ],
        string="Trạng thái",
        required=True,
        default="draft",
        tracking=True,
    )
    deadline = fields.Datetime(string="Hạn SLA", tracking=True)
    response_date = fields.Datetime(string="Ngày phản hồi đầu tiên", tracking=True)
    resolved_date = fields.Datetime(string="Ngày xử lý xong", tracking=True)
    accepted_date = fields.Datetime(string="Ngày tiếp nhận", tracking=True)
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
    internal_note = fields.Text(string="Ghi chú nội bộ")
    customer_feedback = fields.Text(string="Phản hồi khách hàng")
    satisfaction_score = fields.Integer(string="Điểm hài lòng")
    customer_can_edit = fields.Boolean(compute="_compute_customer_permissions")
    customer_can_delete = fields.Boolean(compute="_compute_customer_permissions")

    @api.depends("state")
    def _compute_customer_permissions(self):
        editable_states = self._customer_editable_states()
        deletable_states = self._customer_deletable_states()
        for ticket in self:
            ticket.customer_can_edit = ticket.state in editable_states
            ticket.customer_can_delete = ticket.state in deletable_states

    @api.model
    def _sla_hours_by_severity(self):
        return {
            "high": 4,
            "medium": 24,
            "low": 48,
        }

    @api.model
    def _customer_editable_states(self):
        return ("draft", "open")

    @api.model
    def _customer_deletable_states(self):
        return ("draft",)

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
        tickets = super().create(vals_list)
        for ticket in tickets.filtered("feedback_request_id"):
            ticket.feedback_request_id.complaint_ticket_id = ticket.id
        return tickets

    def write(self, vals):
        if vals.get("severity") and not vals.get("deadline"):
            vals["deadline"] = self._get_sla_deadline(vals["severity"])
        if vals.get("state") == "open" and not vals.get("accepted_date"):
            for ticket in self.filtered(lambda item: not item.accepted_date):
                ticket.accepted_date = fields.Datetime.now()
        if vals.get("state") in ("processing", "resolved", "closed") and not vals.get("response_date"):
            for ticket in self.filtered(lambda item: not item.response_date):
                ticket.response_date = fields.Datetime.now()
        if vals.get("state") in ("resolved", "closed") and not vals.get("resolved_date"):
            vals["resolved_date"] = fields.Datetime.now()
        result = super().write(vals)
        if vals.get("feedback_request_id"):
            for ticket in self.filtered("feedback_request_id"):
                ticket.feedback_request_id.complaint_ticket_id = ticket.id
        return result

    def unlink(self):
        if not self.env.is_superuser():
            if self.env.user.has_group("base.group_user"):
                raise UserError(_("Người dùng nội bộ không được xóa phiếu khiếu nại."))
            blocked = self.filtered(lambda ticket: ticket.state not in ticket._customer_deletable_states())
            if blocked:
                raise UserError(_("Phiếu khiếu nại này không còn được phép xóa."))
        return super().unlink()

    def action_accept(self):
        self.write({"state": "open"})

    def action_processing(self):
        self.write({"state": "processing"})

    def action_resolved(self):
        self.write({"state": "resolved"})

    def action_closed(self):
        self.write({"state": "closed"})

    def action_reopen(self):
        self.write({"state": "open"})
