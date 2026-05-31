# -*- coding: utf-8 -*-
from odoo import fields, models


class CampaignLoyaltyRuleWizard(models.TransientModel):
    _name = "campaign.loyalty.rule.wizard"
    _description = "Quy \u0111\u1ecbnh ch\u1ea5m \u0111i\u1ec3m loyalty"

    rule_html = fields.Html(string="Quy \u0111\u1ecbnh ch\u1ea5m \u0111i\u1ec3m", readonly=True, sanitize=False)
