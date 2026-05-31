from odoo import _, api, fields, models
from odoo.exceptions import UserError


class CrmLeadDataApproval(models.Model):
    _name = "crm.lead.data.approval"
    _description = "Phê Duyệt Dữ Liệu Lead CRM"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char(
        string="Mã yêu cầu",
        default="Mới",
        readonly=True,
        copy=False,
        tracking=True,
    )
    request_type = fields.Selection(
        [
            ("merge", "Phê duyệt merge dữ liệu trùng"),
            ("delete", "Phê duyệt xóa dữ liệu"),
        ],
        string="Loại yêu cầu",
        required=True,
        tracking=True,
    )
    lead_id = fields.Many2one(
        "crm.lead",
        string="Lead chính",
        ondelete="set null",
        tracking=True,
    )
    duplicate_lead_id = fields.Many2one(
        "crm.lead",
        string="Lead trùng",
        ondelete="set null",
        tracking=True,
    )
    requester_id = fields.Many2one(
        "res.users",
        string="Người yêu cầu",
        default=lambda self: self.env.user,
        required=True,
        tracking=True,
    )
    manager_id = fields.Many2one(
        "res.users",
        string="Người phê duyệt",
        tracking=True,
    )
    requested_date = fields.Datetime(
        string="Ngày gửi yêu cầu",
        readonly=True,
        copy=False,
    )
    approved_date = fields.Datetime(
        string="Ngày phê duyệt",
        readonly=True,
        copy=False,
    )
    state = fields.Selection(
        [
            ("draft", "Nháp"),
            ("submitted", "Chờ phê duyệt"),
            ("approved", "Đã phê duyệt"),
            ("rejected", "Từ chối"),
            ("executed", "Đã thực hiện"),
        ],
        string="Trạng thái",
        default="draft",
        required=True,
        tracking=True,
    )
    reason = fields.Text(string="Lý do yêu cầu")
    decision_note = fields.Text(string="Ghi chú phê duyệt")

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", "Mới") == "Mới":
                vals["name"] = sequence.next_by_code("crm.lead.data.approval") or "Mới"
        return super().create(vals_list)

    def _check_manager(self):
        if not self.env.user.has_group("sales_team.group_sale_manager"):
            raise UserError(_("Chỉ quản lý kinh doanh được phê duyệt yêu cầu này."))

    def action_open_form(self):
        self.ensure_one()
        return {
            "name": _("Yêu cầu phê duyệt dữ liệu CRM"),
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_submit(self):
        self.write(
            {
                "state": "submitted",
                "requested_date": fields.Datetime.now(),
            }
        )

    def action_approve(self):
        self._check_manager()
        self.write(
            {
                "state": "approved",
                "manager_id": self.env.user.id,
                "approved_date": fields.Datetime.now(),
            }
        )

    def action_reject(self):
        self._check_manager()
        self.write(
            {
                "state": "rejected",
                "manager_id": self.env.user.id,
            }
        )

    def action_execute(self):
        self._check_manager()
        for approval in self:
            if approval.state != "approved":
                raise UserError(_("Chỉ yêu cầu đã phê duyệt mới được thực hiện."))
            lead = approval.lead_id
            approval.state = "executed"
            if approval.request_type == "delete":
                if not lead:
                    raise UserError(_("Lead cần xóa không còn tồn tại."))
                lead.with_context(crm_delete_approval_id=approval.id).unlink()
            else:
                if not lead:
                    raise UserError(_("Lead cần merge không còn tồn tại."))
                lead.message_post(
                    body=_("Quản lý kinh doanh đã phê duyệt gộp với lead trùng: %s")
                    % (approval.duplicate_lead_id.display_name or "")
                )
