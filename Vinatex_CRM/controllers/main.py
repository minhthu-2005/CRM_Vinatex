from datetime import timedelta

from odoo import fields, http
from odoo.http import request


class WebsiteCrmVinatex(http.Controller):
    def _fmt_number(self, value):
        return f"{int(value or 0):,}".replace(",", ".")

    def _fmt_money(self, value):
        return f"{int(value or 0):,}".replace(",", ".") + " đ"

    def _safe_float(self, value):
        try:
            return float(str(value or "0").replace(",", "."))
        except ValueError:
            return 0.0

    @http.route("/crm_tong_hop/dashboard/data", type="json", auth="user")
    def crm_tong_hop_dashboard_data(self):
        Lead = request.env["crm.lead"].sudo()
        Cskh = request.env["crm.cskh.profile"].sudo()
        Ticket = request.env["crm.service.complaint.ticket"].sudo()
        Campaign = request.env["custom.mail.campaign"].sudo()
        Approval = request.env["crm.lead.data.approval"].sudo()

        lead_domain = [("type", "in", ["lead", "opportunity"])]
        opportunity_domain = [("type", "=", "opportunity")]
        open_ticket_domain = [("state", "=", "open")]
        duplicate_domain = lead_domain + [("duplicate_state", "in", ["similar", "exact"])]
        missing_domain = lead_domain + [("data_quality_state", "in", ["missing", "invalid"])]
        approval_domain = [("state", "=", "submitted")]
        revenue = sum(Lead.search(opportunity_domain).mapped("expected_revenue"))
        total_leads = Lead.search_count(lead_domain)
        won_count = Lead.search_count(lead_domain + ["|", ("stage_id.is_won", "=", True), ("probability", ">=", 100)])
        conversion_rate = round((won_count / total_leads) * 100, 2) if total_leads else 0

        stage_groups = Lead.read_group(
            lead_domain,
            ["stage_id"],
            ["stage_id"],
            orderby="stage_id",
            lazy=False,
        )
        max_count = max([group.get("__count", 0) for group in stage_groups] or [1])
        pipeline = [
            {
                "key": "stage-%s" % group["stage_id"][0] if group.get("stage_id") else "stage-empty",
                "name": group["stage_id"][1] if group.get("stage_id") else "Chưa có giai đoạn",
                "count": group.get("__count", 0),
                "percent": round((group.get("__count", 0) / max_count) * 100),
                "share": round((group.get("__count", 0) / total_leads) * 100, 1) if total_leads else 0,
            }
            for group in stage_groups[:8]
        ]

        today = fields.Date.context_today(request.env.user)
        followups = []
        for item in Cskh.search(
            [("state", "not in", ["done", "cancel"])],
            order="followup_deadline asc, interaction_date desc, id desc",
            limit=5,
        ):
            deadline = item.followup_deadline
            if deadline and deadline < today:
                badge = "Quá hạn %s ngày" % ((today - deadline).days or 1)
                urgency = "danger"
            elif deadline == today:
                badge = "Hôm nay"
                urgency = "warning"
            elif deadline == today + timedelta(days=1):
                badge = "Ngày mai"
                urgency = "success"
            elif deadline:
                badge = deadline.strftime("%d/%m")
                urgency = "info"
            else:
                badge = "Cần cập nhật"
                urgency = "muted"
            followups.append(
                {
                    "id": item.id,
                    "customer": item.customer_id.name or item.lead_id.partner_name or item.lead_id.name or "Khách hàng",
                    "next_action": item.next_action or item.content or "Cần cập nhật hành động tiếp theo",
                    "badge": badge,
                    "urgency": urgency,
                    "initial": (item.customer_id.name or item.lead_id.name or "K")[:1].upper(),
                }
            )

        campaigns = []
        for campaign in Campaign.search([], order="create_date desc", limit=5):
            campaigns.append(
                {
                    "id": campaign.id,
                    "name": campaign.name,
                    "recipients": getattr(campaign, "recipient_count", 0),
                    "state": dict(campaign._fields["state"].selection).get(campaign.state, campaign.state),
                    "tone": "success" if campaign.state == "sent" else "info" if campaign.state == "scheduled" else "muted",
                }
            )

        duplicate_count = Lead.search_count(duplicate_domain)
        missing_count = Lead.search_count(missing_domain)
        approval_count = Approval.search_count(approval_domain)

        return {
            "meta": {
                "conversion_rate": str(conversion_rate).replace(".", ","),
                "won_count": won_count,
                "total_leads": total_leads,
                "last_updated": fields.Datetime.context_timestamp(
                    request.env.user,
                    fields.Datetime.now(),
                ).strftime("%d/%m/%Y %H:%M"),
            },
            "kpis": [
                {
                    "key": "lead",
                    "label": "Lead & cơ hội",
                    "value": self._fmt_number(total_leads),
                    "caption": "đang hoạt động",
                    "trend": "Khớp module",
                    "icon": "fa-users",
                    "tone": "blue",
                },
                {
                    "key": "opportunity",
                    "label": "Cơ hội",
                    "value": self._fmt_number(Lead.search_count(opportunity_domain)),
                    "caption": "cơ hội đang hoạt động",
                    "trend": "Đang theo pipeline",
                    "icon": "fa-bullseye",
                    "tone": "teal",
                },
                {
                    "key": "revenue",
                    "label": "Doanh thu kỳ vọng",
                    "value": self._fmt_money(revenue),
                    "caption": "từ cơ hội CRM",
                    "trend": "Tổng expected revenue",
                    "icon": "fa-usd",
                    "tone": "amber",
                },
                {
                    "key": "cskh",
                    "label": "Hồ sơ CSKH",
                    "value": self._fmt_number(Cskh.search_count([])),
                    "caption": "lần chăm sóc",
                    "trend": "Theo module CSKH",
                    "icon": "fa-headphones",
                    "tone": "blue",
                },
                {
                    "key": "campaign",
                    "label": "Chiến dịch",
                    "value": self._fmt_number(Campaign.search_count([])),
                    "caption": "chiến dịch",
                    "trend": "Theo campaign",
                    "icon": "fa-bullhorn",
                    "tone": "teal",
                },
                {
                    "key": "ticket",
                    "label": "Khiếu nại mở",
                    "value": self._fmt_number(Ticket.search_count(open_ticket_domain)),
                    "caption": "cần xử lý",
                    "trend": "Theo phiếu khiếu nại",
                    "icon": "fa-exclamation-circle",
                    "tone": "red",
                },
            ],
            "pipeline": pipeline,
            "followups": followups,
            "campaigns": campaigns,
            "quality": {
                "duplicates": duplicate_count,
                "missing": missing_count,
                "approvals": approval_count,
                "cards": [
                    {
                        "key": "duplicates",
                        "label": "Lead nghi trùng",
                        "value": duplicate_count,
                        "caption": "Cần kiểm tra" if duplicate_count else "Không có mới",
                        "icon": "fa-users",
                        "tone": "danger" if duplicate_count else "success",
                        "action": "crm_tong_hop.action_crm_lead_duplicate_review",
                    },
                    {
                        "key": "missing",
                        "label": "Lead thiếu dữ liệu",
                        "value": missing_count,
                        "caption": "Cần bổ sung" if missing_count else "Không có mới",
                        "icon": "fa-file-text-o",
                        "tone": "warning" if missing_count else "success",
                        "action": "crm_tong_hop.action_crm_lead_missing_data",
                    },
                    {
                        "key": "approvals",
                        "label": "Chờ phê duyệt",
                        "value": approval_count,
                        "caption": "Cần xử lý" if approval_count else "Không có mới",
                        "icon": "fa-clock-o",
                        "tone": "info" if approval_count else "success",
                        "action": "crm_tong_hop.action_crm_lead_data_approval",
                    },
                ],
            },
        }

    @http.route("/crm-vinatex", type="http", auth="public", website=True)
    def crm_vinatex(self, **kwargs):
        Lead = request.env["crm.lead"].sudo()
        Cskh = request.env["crm.cskh.profile"].sudo()
        Ticket = request.env["crm.service.complaint.ticket"].sudo()
        Campaign = request.env["custom.mail.campaign"].sudo()
        Template = request.env["mail.template"].sudo()
        lead_domain = [("type", "in", ["lead", "opportunity"])]
        open_ticket_domain = [("state", "=", "open")]
        values = {
            "success": kwargs.get("success"),
            "lead_count": Lead.search_count(lead_domain),
            "cskh_count": Cskh.search_count([]),
            "ticket_count": Ticket.search_count(open_ticket_domain),
            "ticket_total_count": Ticket.search_count([]),
            "campaign_count": Campaign.search_count([]),
            "recent_leads": Lead.search(lead_domain, order="create_date desc", limit=6),
            "recent_cskh": Cskh.search([], order="interaction_date desc, id desc", limit=5),
            "recent_tickets": Ticket.search(open_ticket_domain, order="create_date desc", limit=5),
            "recent_campaigns": Campaign.search([], order="create_date desc", limit=5),
            "campaign_templates": Template.search(
                [
                    ("is_campaign_template", "=", True),
                    ("model", "=", "res.partner"),
                ],
                order="name asc",
                limit=20,
            ),
        }
        return request.render("crm_tong_hop.website_crm_vinatex_page", values)

    def _demo_source(self):
        Source = request.env["utm.source"].sudo()
        source = Source.search([("name", "in", ["Cổng website VINATEX CRM", "Website CRM Vinatex"])], limit=1)
        if source and source.name != "Cổng website VINATEX CRM":
            source.write({"name": "Cổng website VINATEX CRM"})
        return source or Source.create({"name": "Cổng website VINATEX CRM"})

    def _demo_user(self):
        return request.env.ref("base.user_admin").sudo()

    def _campaign_template(self, template_type="follow_up"):
        Template = request.env["mail.template"].sudo()
        template = Template.search(
            [
                ("is_campaign_template", "=", True),
                ("campaign_template_type", "=", template_type),
                ("model", "=", "res.partner"),
            ],
            limit=1,
        )
        if template:
            return template
        fallback = Template.search([("model", "=", "res.partner")], limit=1)
        if fallback:
            return fallback
        partner_model = request.env["ir.model"].sudo().search([("model", "=", "res.partner")], limit=1)
        return Template.create(
            {
                "name": "VINATEX CRM - theo dõi chăm sóc",
                "model_id": partner_model.id,
                "subject": "VINATEX - cập nhật chăm sóc khách hàng",
                "body_html": "<p>VINATEX trân trọng cảm ơn quý khách đã quan tâm đến sản phẩm và dịch vụ.</p>",
                "is_campaign_template": True,
                "campaign_template_type": template_type,
            }
        )

    def _partner_from_post(self, post):
        Partner = request.env["res.partner"].sudo()
        email = (post.get("email") or "").strip()
        partner = email and Partner.search([("email", "=", email)], limit=1)
        if partner:
            return partner
        return Partner.create(
            {
                "name": (post.get("customer_name") or post.get("partner_name") or "Khách hàng website").strip(),
                "email": email,
                "phone": (post.get("phone") or "").strip(),
                "company_type": "company",
            }
        )

    def _find_or_create_lead(self, post):
        Lead = request.env["crm.lead"].sudo()
        email = (post.get("email") or "").strip()
        phone = (post.get("phone") or "").strip()
        domain = []
        if email:
            domain = [("email_from", "=", email)]
        elif phone:
            domain = [("phone", "=", phone)]
        lead = domain and Lead.search(domain, order="create_date desc", limit=1)
        if lead:
            return lead

        partner = self._partner_from_post(post)
        customer_name = (post.get("customer_name") or post.get("partner_name") or partner.name).strip()
        contact_name = (post.get("contact_name") or customer_name).strip()
        requirement = (post.get("requirement") or post.get("customer_need") or "Nhu cầu dệt may từ website").strip()
        user = self._demo_user()
        values = {
            "name": "%s - %s" % (customer_name, requirement[:60]),
            "type": post.get("lead_type") or "lead",
            "partner_id": partner.id,
            "partner_name": customer_name,
            "contact_name": contact_name,
            "email_from": email or "demo@vinatex.local",
            "phone": phone or "0900000000",
            "website": (post.get("website") or "https://vinatex.com.vn").strip(),
            "source_id": self._demo_source().id,
            "user_id": user.id,
            "initial_product_requirement": requirement,
            "description": (post.get("description") or post.get("requirement") or "").strip(),
        }
        if "expected_revenue" in Lead._fields:
            values["expected_revenue"] = self._safe_float(post.get("expected_revenue"))
        if "probability" in Lead._fields and post.get("probability"):
            values["probability"] = self._safe_float(post.get("probability"))
        return Lead.create(values)

    @http.route("/crm-vinatex/lead", type="http", auth="public", website=True, methods=["POST"], csrf=True)
    def crm_vinatex_create_lead(self, **post):
        self._find_or_create_lead(post)
        return request.redirect("/crm-vinatex?success=lead#lead")

    @http.route("/crm-vinatex/cskh", type="http", auth="public", website=True, methods=["POST"], csrf=True)
    def crm_vinatex_create_cskh(self, **post):
        lead = self._find_or_create_lead(post)
        request.env["crm.cskh.profile"].sudo().create(
            {
                "lead_id": lead.id,
                "customer_id": lead.partner_id.id or self._partner_from_post(post).id,
                "user_id": lead.user_id.id or self._demo_user().id,
                "interaction_type": post.get("interaction_type") or "call",
                "content": (post.get("content") or "Ghi nhan cham soc tu website").strip(),
                "result": (post.get("result") or "Đã cập nhật hồ sơ CSKH").strip(),
                "customer_need": (post.get("customer_need") or post.get("requirement") or "").strip(),
                "product_category": (post.get("product_category") or "").strip(),
                "design_sample": (post.get("design_sample") or "").strip(),
                "material_info": (post.get("material_info") or "").strip(),
                "technical_requirement": (post.get("technical_requirement") or "").strip(),
                "expected_order_qty": self._safe_float(post.get("expected_order_qty")),
                "delivery_terms": (post.get("delivery_terms") or "").strip(),
                "next_action": (post.get("next_action") or "Tiếp tục chăm sóc khách hàng").strip(),
                "followup_deadline": post.get("followup_deadline") or False,
                "state": post.get("state") or "pending",
            }
        )
        return request.redirect("/crm-vinatex?success=cskh#cskh")

    @http.route("/crm-vinatex/complaint", type="http", auth="public", website=True, methods=["POST"], csrf=True)
    def crm_vinatex_create_complaint(self, **post):
        lead = self._find_or_create_lead(post)
        request.env["crm.service.complaint.ticket"].sudo().create(
            {
                "customer_id": lead.partner_id.id or self._partner_from_post(post).id,
                "lead_id": lead.id,
                "sale_user_id": lead.user_id.id or self._demo_user().id,
                "assigned_user_id": self._demo_user().id,
                "title": (post.get("title") or "Khiếu nại từ website").strip(),
                "description": (post.get("description") or "Khách hàng gửi phản hồi cần xử lý").strip(),
                "severity": post.get("severity") or "medium",
                "root_cause": (post.get("root_cause") or "").strip(),
                "solution": (post.get("solution") or "").strip(),
                "customer_feedback": (post.get("customer_feedback") or "").strip(),
                "satisfaction_score": int(self._safe_float(post.get("satisfaction_score"))),
            }
        )
        return request.redirect("/crm-vinatex?success=complaint#khieu-nai")

    @http.route("/crm-vinatex/campaign", type="http", auth="public", website=True, methods=["POST"], csrf=True)
    def crm_vinatex_create_campaign(self, **post):
        template_type = post.get("campaign_template_type") or "follow_up"
        template = False
        template_id = int(post.get("template_id") or 0)
        if template_id:
            template = request.env["mail.template"].sudo().browse(template_id).exists()
        if not template and (post.get("email_subject") or post.get("email_body")):
            partner_model = request.env["ir.model"].sudo().search([("model", "=", "res.partner")], limit=1)
            template = request.env["mail.template"].sudo().create(
                {
                    "name": (post.get("template_name") or post.get("name") or "Mẫu email VINATEX").strip(),
                    "model_id": partner_model.id,
                    "subject": (post.get("email_subject") or "VINATEX - thông tin chăm sóc khách hàng").strip(),
                    "body_html": "<div>%s</div>" % (post.get("email_body") or "").replace("\n", "<br/>"),
                    "is_campaign_template": True,
                    "campaign_template_type": template_type,
                }
            )
        if not template:
            template = self._campaign_template(template_type)
        values = {
            "name": (post.get("name") or "Chiến dịch chăm sóc khách hàng VINATEX").strip(),
            "template_id": template.id,
            "segment": post.get("segment") or False,
            "customer_status": post.get("customer_status") or False,
            "potential_level": post.get("potential_level") or False,
            "retention_segment": post.get("retention_segment") or False,
            "personalization_goal": post.get("personalization_goal") or False,
            "remarketing": template_type == "remarketing",
        }
        campaign = request.env["custom.mail.campaign"].sudo().create(values)
        partners = campaign._get_target_customers()
        manual_emails = [
            email.strip()
            for raw in (post.get("manual_recipient_emails") or "").replace(";", ",").split(",")
            for email in [raw]
            if email.strip()
        ]
        if manual_emails:
            Partner = request.env["res.partner"].sudo()
            manual_partners = Partner.browse()
            for email in manual_emails:
                partner = Partner.search([("email", "=", email)], limit=1)
                if not partner:
                    partner = Partner.create({"name": email.split("@")[0], "email": email})
                manual_partners |= partner
            partners |= manual_partners
        if partners:
            campaign.write({"recipient_ids": [(6, 0, partners.ids)]})
        if post.get("send_now") and campaign.recipient_ids:
            campaign.action_send_now()
        return request.redirect("/crm-vinatex?success=campaign#campaign")
