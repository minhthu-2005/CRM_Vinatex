from odoo import _, fields, models
from odoo.exceptions import UserError


class CrmLeadTransferOwnerWizard(models.TransientModel):
    _name = "crm.lead.transfer.owner.wizard"
    _description = "Chuyển Nhân Viên Phụ Trách Lead"

    lead_ids = fields.Many2many(
        "crm.lead",
        string="Lead",
        required=True,
    )
    new_user_id = fields.Many2one(
        "res.users",
        string="Nhân viên phụ trách mới",
        required=True,
    )
    reason = fields.Text(string="Lý do chuyển phụ trách")

    def action_transfer(self):
        self.ensure_one()
        if not self.lead_ids:
            raise UserError(_("Vui lòng chọn ít nhất một lead để chuyển phụ trách."))
        old_owners = {
            lead.id: lead.user_id.display_name or _("Chưa có")
            for lead in self.lead_ids
        }
        self.lead_ids.write({"user_id": self.new_user_id.id})
        for lead in self.lead_ids:
            lead.message_post(
                body=_("Đã chuyển nhân viên phụ trách từ %s sang %s. Lý do: %s")
                % (
                    old_owners.get(lead.id),
                    self.new_user_id.display_name,
                    self.reason or _("Không ghi chú"),
                )
            )
        return {"type": "ir.actions.act_window_close"}
