# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.exceptions import ValidationError


class ScheduleCampaignWizard(models.TransientModel):
    _name = "schedule.campaign.wizard"
    _description = "Wizard chọn thời gian gửi Campaign"

    campaign_id = fields.Many2one("custom.mail.campaign", string="Campaign", required=True)
    scheduled_date = fields.Datetime(string="Thời gian gửi dự kiến", required=True)

    def action_confirm_schedule(self):
        self.ensure_one()
        if self.scheduled_date <= fields.Datetime.now():
            raise ValidationError("Thời gian gửi dự kiến phải lớn hơn thời gian hiện tại.")
        self.campaign_id.write({"scheduled_date": self.scheduled_date, "state": "scheduled"})
        return {
            "type": "ir.actions.act_window",
            "name": "Email Campaign",
            "res_model": "custom.mail.campaign",
            "res_id": self.campaign_id.id,
            "view_mode": "form",
            "target": "current",
        }
