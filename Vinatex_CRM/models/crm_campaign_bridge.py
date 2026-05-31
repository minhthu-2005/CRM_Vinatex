# -*- coding: utf-8 -*-
from odoo import api, models


class CrmLeadCampaignBridge(models.Model):
    _inherit = "crm.lead"

    def _crm_campaign_status(self):
        self.ensure_one()
        stage_name = (self.stage_id.name or "").casefold()
        if not self.active:
            return "dormant"
        if "lost" in stage_name or (self.probability == 0 and self.stage_id):
            return "lost"
        if "won" in stage_name or self.probability == 100:
            return "won"
        if "quotation" in stage_name or "bao gia" in stage_name or "báo giá" in stage_name:
            return "quotation"
        if "negotiation" in stage_name or "thuong luong" in stage_name or "thương lượng" in stage_name:
            return "negotiation"
        if self.cskh_profile_ids:
            return "contacted"
        return "new"

    def _sync_partner_campaign_profile(self):
        for lead in self.filtered("partner_id"):
            partner = lead.partner_id
            values = {
                "customer_status": lead._crm_campaign_status(),
            }
            if lead.source_id:
                values["lead_source_id"] = lead.source_id.id
            if lead.expected_revenue and lead.expected_revenue > partner.crm_estimated_revenue:
                values["crm_estimated_revenue"] = lead.expected_revenue
            if lead.probability >= 70:
                values["potential_level"] = "high"
            elif lead.probability and lead.probability < 30:
                values["potential_level"] = "low"
            partner.sudo().write(values)

    @api.model_create_multi
    def create(self, vals_list):
        leads = super().create(vals_list)
        leads._sync_partner_campaign_profile()
        return leads

    def write(self, vals):
        result = super().write(vals)
        sync_fields = {"partner_id", "stage_id", "probability", "active", "source_id", "expected_revenue"}
        if sync_fields.intersection(vals):
            self._sync_partner_campaign_profile()
        return result


class CskhProfileCampaignBridge(models.Model):
    _inherit = "crm.cskh.profile"

    def _sync_partner_care_segment(self):
        for profile in self.filtered("customer_id"):
            profile.customer_id.sudo().write({
                "customer_status": "contacted",
                "segment": "medium",
            })

    @api.model_create_multi
    def create(self, vals_list):
        profiles = super().create(vals_list)
        profiles._sync_partner_care_segment()
        return profiles

    def write(self, vals):
        result = super().write(vals)
        if {"customer_id", "interaction_date", "state", "result"}.intersection(vals):
            self._sync_partner_care_segment()
        return result


class ComplaintTicketCampaignBridge(models.Model):
    _inherit = "crm.service.complaint.ticket"

    def _sync_partner_complaint_metrics(self):
        partners = (self.mapped("customer_id") | self.mapped("lead_id.partner_id")).filtered(lambda partner: partner)
        Ticket = self.env["crm.service.complaint.ticket"].sudo()
        for partner in partners:
            count = Ticket.search_count(["|", ("customer_id", "=", partner.id), ("lead_id.partner_id", "=", partner.id)])
            partner.write({
                "complaint_count": count,
                "customer_status": "dormant" if count >= 3 else partner.customer_status,
            })

    @api.model_create_multi
    def create(self, vals_list):
        tickets = super().create(vals_list)
        tickets._sync_partner_complaint_metrics()
        return tickets

    def write(self, vals):
        previous_partners = self.mapped("customer_id") | self.mapped("lead_id.partner_id")
        result = super().write(vals)
        if {"customer_id", "lead_id", "state", "satisfaction_score"}.intersection(vals):
            (self | self.with_context(active_test=False))._sync_partner_complaint_metrics()
            if previous_partners:
                self.env["crm.service.complaint.ticket"].browse().with_context(
                    active_test=False
                )._sync_partner_complaint_metrics_for(previous_partners)
        return result

    def unlink(self):
        partners = self.mapped("customer_id") | self.mapped("lead_id.partner_id")
        result = super().unlink()
        if partners:
            self._sync_partner_complaint_metrics_for(partners)
        return result

    def _sync_partner_complaint_metrics_for(self, partners):
        Ticket = self.env["crm.service.complaint.ticket"].sudo()
        for partner in partners:
            count = Ticket.search_count(["|", ("customer_id", "=", partner.id), ("lead_id.partner_id", "=", partner.id)])
            partner.sudo().write({"complaint_count": count})
