# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class MailCampaign(models.Model):
    _name = "custom.mail.campaign"
    _description = "Quản lý chiến dịch email"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(string="Tên chiến dịch", required=True, tracking=True)
    template_id = fields.Many2one(
        "mail.template",
        string="Mẫu email",
        required=True,
        domain=[("is_campaign_template", "=", True), ("model", "=", "res.partner")],
    )
    email_subject = fields.Char(
        string="Tiêu đề email",
        tracking=True,
        help="Nội dung được lấy từ mẫu email và có thể chỉnh riêng cho chiến dịch.",
    )
    email_body_html = fields.Html(
        string="Nội dung email",
        sanitize=False,
        help="Có thể dùng biến QWeb như object.name, object.email để cá nhân hóa theo từng khách hàng.",
    )
    segment = fields.Selection(
        [
            ("high", "Khách hàng giá trị cao"),
            ("medium", "Khách hàng giá trị trung bình"),
            ("low", "Khách hàng giá trị thấp"),
            ("dormant", "Khách hàng lâu chưa tương tác"),
        ],
        string="Nhóm khách hàng",
    )
    customer_status = fields.Selection(
        [
            ("new", "Lead mới"),
            ("contacted", "Đã liên hệ"),
            ("qualified", "Lead đủ điều kiện"),
            ("quotation", "Đã gửi báo giá"),
            ("negotiation", "Đang thương lượng"),
            ("won", "Chốt thành công"),
            ("lost", "Thất bại"),
            ("dormant", "Lâu chưa tương tác"),
        ],
        string="Tình trạng khách hàng",
    )
    potential_level = fields.Selection(
        [
            ("high", "Tiềm năng cao"),
            ("medium", "Tiềm năng trung bình"),
            ("low", "Tiềm năng thấp"),
        ],
        string="Mức độ tiềm năng",
    )
    lead_source_id = fields.Many2one("utm.source", string="Nguồn lead")
    recipient_ids = fields.Many2many("res.partner", string="Danh sách người nhận")
    recipient_count = fields.Integer(string="Số lượng người nhận", compute="_compute_recipient_count")
    scheduled_date = fields.Datetime(string="Thời gian gửi dự kiến", readonly=True)
    state = fields.Selection(
        [
            ("draft", "Nháp"),
            ("scheduled", "Đã lên lịch"),
            ("sent", "Đã gửi"),
            ("cancel", "Đã hủy"),
        ],
        default="draft",
        string="Trạng thái",
        tracking=True,
    )
    remarketing = fields.Boolean(string="Remarketing khách hàng cũ")
    approved = fields.Boolean(string="Đã duyệt")
    sent_log_ids = fields.One2many("custom.mail.log", "campaign_id", string="Nhật ký gửi email")

    @api.depends("recipient_ids")
    def _compute_recipient_count(self):
        for rec in self:
            rec.recipient_count = len(rec.recipient_ids)

    def _copy_template_content(self, force=False):
        for rec in self:
            if not rec.template_id:
                continue
            vals = {}
            if force or not rec.email_subject:
                vals["email_subject"] = rec.template_id.subject or ""
            if force or not rec.email_body_html:
                vals["email_body_html"] = rec.template_id.body_html or ""
            if vals:
                rec.update(vals)

    @api.onchange("template_id")
    def _onchange_template_id(self):
        self._copy_template_content(force=True)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._copy_template_content(force=False)
        return records

    def write(self, vals):
        res = super().write(vals)
        if "template_id" in vals and "email_subject" not in vals and "email_body_html" not in vals:
            self._copy_template_content(force=True)
        return res

    def action_reload_template_content(self):
        self._copy_template_content(force=True)
        return {"type": "ir.actions.client", "tag": "reload"}

    def _get_target_customers(self):
        self.ensure_one()
        domain = [("email", "!=", False)]
        if self.segment:
            domain.append(("segment", "=", self.segment))
        if self.customer_status:
            domain.append(("customer_status", "=", self.customer_status))
        if self.potential_level:
            domain.append(("potential_level", "=", self.potential_level))
        if self.lead_source_id:
            domain.append(("lead_source_id", "=", self.lead_source_id.id))

        return self.env["res.partner"].search(domain)

    def action_load_recipients(self):
        for rec in self:
            partners = rec._get_target_customers()
            if not partners:
                raise ValidationError("Không tìm thấy khách hàng phù hợp với điều kiện đã chọn.")
            rec.recipient_ids = [(6, 0, partners.ids)]

    def _check_ready_to_send(self):
        for rec in self:
            if not rec.template_id:
                raise ValidationError("Vui lòng chọn mẫu email.")
            if rec.template_id.model != "res.partner":
                raise ValidationError("Mẫu email phải áp dụng cho Liên hệ.")
            rec._copy_template_content(force=False)
            if not rec.email_subject or not rec.email_body_html:
                raise ValidationError("Nội dung email phải có tiêu đề và nội dung.")
            if not rec.recipient_ids:
                raise ValidationError("Vui lòng chọn hoặc tải ít nhất một người nhận.")
            emails = [p.email for p in rec.recipient_ids if p.email]
            if len(emails) != len(rec.recipient_ids):
                raise ValidationError("Một số người nhận chưa có email.")
            if len(emails) != len(set(emails)):
                raise ValidationError("Danh sách người nhận có email bị trùng.")

    def action_send_now(self):
        for rec in self:
            rec._check_ready_to_send()
            if rec.state != "draft":
                raise ValidationError("Chỉ có thể gửi ngay chiến dịch đang ở trạng thái Nháp.")
            rec.scheduled_date = fields.Datetime.now()
            rec._send_campaign_email()
            rec.state = "sent"
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_schedule(self):
        self.ensure_one()
        self._check_ready_to_send()
        if self.state != "draft":
            raise ValidationError("Chỉ có thể lên lịch gửi cho chiến dịch đang ở trạng thái Nháp.")
        return {
            "type": "ir.actions.act_window",
            "name": "Lên lịch gửi chiến dịch",
            "res_model": "schedule.campaign.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_campaign_id": self.id},
        }

    def action_cancel(self):
        for rec in self:
            if rec.state == "sent":
                raise ValidationError("Chiến dịch đã gửi không thể hủy.")
            rec.state = "cancel"
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_reset_to_draft(self):
        for rec in self:
            rec.state = "draft"
            rec.scheduled_date = False
        return {"type": "ir.actions.client", "tag": "reload"}

    def _send_campaign_email(self):
        for campaign in self:
            template = campaign.template_id
            renderer = self.env["mail.render.mixin"]
            for partner in campaign.recipient_ids:
                try:
                    rendered_subject = renderer._render_template(
                        campaign.email_subject or template.subject or "",
                        "res.partner",
                        [partner.id],
                        engine="inline_template",
                    ).get(partner.id, "")
                    rendered_body = renderer._render_template(
                        campaign.email_body_html or template.body_html or "",
                        "res.partner",
                        [partner.id],
                        engine="qweb",
                        options={"post_process": True},
                    ).get(partner.id, "")
                    template.send_mail(
                        partner.id,
                        force_send=False,
                        email_values={
                            "email_to": partner.email,
                            "subject": rendered_subject,
                            "body_html": rendered_body,
                            "body": rendered_body,
                        },
                    )
                    status = "sent"
                    error_message = False
                except Exception as error:
                    status = "failed"
                    error_message = str(error)
                self.env["custom.mail.log"].sudo().create(
                    {
                        "campaign_id": campaign.id,
                        "partner_id": partner.id,
                        "email_to": partner.email or "",
                        "sent_date": fields.Datetime.now(),
                        "status": status,
                        "error_message": error_message,
                    }
                )

    @api.model
    def cron_send_scheduled_campaigns(self):
        campaigns = self.search([("state", "=", "scheduled"), ("scheduled_date", "<=", fields.Datetime.now())])
        for campaign in campaigns:
            campaign._check_ready_to_send()
            campaign._send_campaign_email()
            campaign.state = "sent"

    @api.model
    def automated_email_workflow(self):
        template = self.env["mail.template"].search(
            [
                ("is_campaign_template", "=", True),
                ("campaign_template_type", "=", "follow_up"),
                ("model", "=", "res.partner"),
            ],
            limit=1,
        )
        if not template:
            return
        partners = self.env["res.partner"].search(
            [("customer_status", "in", ["contacted", "quotation"]), ("email", "!=", False)]
        )
        for partner in partners:
            template.send_mail(partner.id, force_send=False, email_values={"email_to": partner.email})

    @api.model
    def send_dormant_remarketing(self):
        template = self.env["mail.template"].search(
            [
                ("is_campaign_template", "=", True),
                ("campaign_template_type", "=", "remarketing"),
                ("model", "=", "res.partner"),
            ],
            limit=1,
        )
        if not template:
            return
        dormant_customers = self.env["res.partner"].search([("segment", "=", "dormant"), ("email", "!=", False)])
        if dormant_customers:
            self.create(
                {
                    "name": "Chiến dịch remarketing khách hàng lâu chưa giao dịch",
                    "template_id": template.id,
                    "recipient_ids": [(6, 0, dormant_customers.ids)],
                    "state": "draft",
                    "remarketing": True,
                    "approved": False,
                    "segment": "dormant",
                    "customer_status": "dormant",
                }
            )
