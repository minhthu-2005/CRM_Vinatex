from odoo import _, api, fields, models


class ComplaintTicket(models.Model):
    _inherit = "crm.service.complaint.ticket"

    cskh_profile_id = fields.Many2one(
        "crm.cskh.profile",
        string="Ho so CSKH lien quan",
        copy=False,
        ondelete="set null",
    )

    @api.model_create_multi
    def create(self, vals_list):
        tickets = super().create(vals_list)
        tickets._ensure_complaint_cskh_profile()
        return tickets

    def write(self, vals):
        result = super().write(vals)
        if set(vals) & {"state", "solution", "customer_feedback", "satisfaction_score"}:
            self._sync_resolution_to_cskh()
        return result

    def _ensure_complaint_cskh_profile(self):
        CskhProfile = self.env["crm.cskh.profile"]
        for ticket in self.filtered(lambda item: item.lead_id and not item.cskh_profile_id):
            profile = CskhProfile.create(
                {
                    "lead_id": ticket.lead_id.id,
                    "customer_id": ticket.customer_id.id,
                    "user_id": ticket.assigned_user_id.id or ticket.sale_user_id.id or self.env.user.id,
                    "interaction_type": "complaint",
                    "interaction_date": ticket.create_date or fields.Datetime.now(),
                    "content": ticket.description or ticket.title,
                    "result": _("Da tao phieu khieu nai %s trong quy trinh CRM.") % ticket.name,
                    "next_action": _("Xu ly khieu nai theo SLA va cap nhat ket qua cho khach hang."),
                    "followup_deadline": fields.Date.to_date(ticket.deadline) if ticket.deadline else False,
                }
            )
            ticket.cskh_profile_id = profile.id

    def _sync_resolution_to_cskh(self):
        for ticket in self.filtered("cskh_profile_id"):
            updates = {}
            if ticket.solution:
                updates["result"] = ticket.solution
            if ticket.customer_feedback:
                updates["content"] = "%s\n\n%s" % (
                    ticket.cskh_profile_id.content or ticket.title,
                    ticket.customer_feedback,
                )
            if ticket.state in ("resolved", "closed"):
                updates["state"] = "done"
                updates["next_action"] = _("Theo doi muc do hai long sau xu ly khieu nai.")
            if updates:
                ticket.cskh_profile_id.write(updates)
