from odoo import _, api, fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    unified_crm_state = fields.Selection(
        [
            ("lead", "Lead"),
            ("qualified", "Dang cham soc"),
            ("complaint", "Co khieu nai"),
            ("won", "Thanh cong"),
            ("lost", "That bai"),
            ("archived", "Luu tru"),
        ],
        string="Trang thai CRM tong",
        compute="_compute_unified_crm_state",
    )
    latest_cskh_profile_id = fields.Many2one(
        "crm.cskh.profile",
        string="Ho so CSKH gan nhat",
        compute="_compute_latest_cskh_profile",
    )

    @api.depends("active", "stage_id", "probability", "complaint_count", "cskh_profile_ids.state")
    def _compute_unified_crm_state(self):
        for lead in self:
            stage_name = (lead.stage_id.name or "").casefold()
            if not lead.active:
                lead.unified_crm_state = "archived"
            elif "lost" in stage_name or lead.probability == 0 and lead.stage_id:
                lead.unified_crm_state = "lost"
            elif lead.complaint_count:
                lead.unified_crm_state = "complaint"
            elif "won" in stage_name or lead.probability == 100:
                lead.unified_crm_state = "won"
            elif lead.cskh_profile_ids:
                lead.unified_crm_state = "qualified"
            else:
                lead.unified_crm_state = "lead"

    @api.depends("cskh_profile_ids.interaction_date")
    def _compute_latest_cskh_profile(self):
        for lead in self:
            lead.latest_cskh_profile_id = lead.cskh_profile_ids[:1]

    def action_create_cskh_profile(self):
        self.ensure_one()
        return {
            "name": _("Tao ho so CSKH"),
            "type": "ir.actions.act_window",
            "res_model": "crm.cskh.profile",
            "view_mode": "form",
            "target": "current",
            "context": {
                "default_lead_id": self.id,
                "default_customer_id": self.partner_id.id,
                "default_user_id": self.user_id.id or self.env.user.id,
                "default_interaction_type": "note",
            },
        }

    def action_view_cskh_profiles(self):
        self.ensure_one()
        return {
            "name": _("Ho so CSKH"),
            "type": "ir.actions.act_window",
            "res_model": "crm.cskh.profile",
            "view_mode": "tree,form",
            "domain": [("lead_id", "=", self.id)],
            "context": {
                "default_lead_id": self.id,
                "default_customer_id": self.partner_id.id,
                "default_user_id": self.user_id.id or self.env.user.id,
            },
        }

    def action_create_complaint_ticket(self):
        self.ensure_one()
        return {
            "name": _("Tao khieu nai"),
            "type": "ir.actions.act_window",
            "res_model": "crm.service.complaint.ticket",
            "view_mode": "form",
            "target": "current",
            "context": {
                "default_lead_id": self.id,
                "default_customer_id": self.partner_id.id,
                "default_sale_user_id": self.user_id.id or self.env.user.id,
            },
        }
