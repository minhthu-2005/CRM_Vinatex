import secrets

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class CustomerFeedbackForm(models.Model):
    _name = "crm.service.feedback.form"
    _description = "Biểu Mẫu Phản Hồi Khách Hàng"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sequence, name"

    name = fields.Char(required=True, tracking=True)
    sequence = fields.Integer(default=10)
    description = fields.Text()
    state = fields.Selection(
        [
            ("draft", "Nháp"),
            ("active", "Đang hoạt động"),
            ("closed", "Đã đóng"),
            ("archived", "Đã lưu trữ"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    user_id = fields.Many2one(
        "res.users",
        string="Người phụ trách",
        default=lambda self: self.env.user,
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
    )
    partner_ids = fields.Many2many(
        "res.partner",
        "crm_service_feedback_form_partner_rel",
        "form_id",
        "partner_id",
        string="Người nhận",
    )
    question_ids = fields.One2many(
        "crm.service.feedback.question",
        "form_id",
        string="Câu hỏi",
        copy=True,
    )
    request_ids = fields.One2many(
        "crm.service.feedback.request",
        "form_id",
        string="Yêu cầu phản hồi",
    )
    request_count = fields.Integer(compute="_compute_feedback_stats")
    response_count = fields.Integer(compute="_compute_feedback_stats")
    average_score = fields.Float(compute="_compute_feedback_stats", digits=(16, 2))
    satisfaction_rate = fields.Float(
        string="Hài lòng (%)",
        compute="_compute_feedback_stats",
        digits=(16, 2),
    )

    @api.depends("request_ids.state", "request_ids.average_score", "request_ids.satisfaction_level")
    def _compute_feedback_stats(self):
        for form in self:
            requests = form.request_ids
            responses = requests.filtered(lambda request: request.state == "answered")
            scored_responses = responses.filtered(lambda request: request.average_score)
            satisfied = responses.filtered(lambda request: request.satisfaction_level == "satisfied")
            form.request_count = len(requests)
            form.response_count = len(responses)
            form.average_score = (
                sum(scored_responses.mapped("average_score")) / len(scored_responses)
                if scored_responses
                else 0.0
            )
            form.satisfaction_rate = (
                len(satisfied) / len(responses) * 100.0 if responses else 0.0
            )

    def action_activate(self):
        self.write({"state": "active"})

    def action_close(self):
        self.write({"state": "closed"})

    def action_archive(self):
        self.write({"state": "archived"})

    def action_reset_to_draft(self):
        self.write({"state": "draft"})

    def action_view_requests(self):
        self.ensure_one()
        action = self.env.ref("thuc_linh_crm_service.action_feedback_request").read()[0]
        action["domain"] = [("form_id", "=", self.id)]
        action["context"] = {
            "default_form_id": self.id,
            "search_default_group_state": 1,
        }
        return action

    def action_send_requests(self):
        request_model = self.env["crm.service.feedback.request"]
        created_or_sent = request_model.browse()
        for form in self:
            if not form.question_ids:
                raise UserError(_("Vui lòng thêm ít nhất một câu hỏi trước khi gửi phản hồi."))
            if not form.partner_ids:
                raise UserError(_("Vui lòng chọn ít nhất một người nhận."))
            if form.state == "draft":
                form.action_activate()
            for partner in form.partner_ids:
                request = request_model.search(
                    [
                        ("form_id", "=", form.id),
                        ("partner_id", "=", partner.id),
                        ("state", "!=", "cancelled"),
                    ],
                    limit=1,
                )
                if not request:
                    request = request_model.create(
                        {
                            "form_id": form.id,
                            "partner_id": partner.id,
                            "email": partner.email,
                            "user_id": form.user_id.id,
                            "company_id": form.company_id.id,
                        }
                    )
                if request.state in ("draft", "sent"):
                    request.action_send_email()
                created_or_sent |= request
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Đã chuẩn bị biểu mẫu phản hồi"),
                "message": _("%s yêu cầu phản hồi đã sẵn sàng gửi cho khách hàng.") % len(created_or_sent),
                "type": "success",
                "sticky": False,
            },
        }


class CustomerFeedbackQuestion(models.Model):
    _name = "crm.service.feedback.question"
    _description = "Câu Hỏi Phản Hồi Khách Hàng"
    _order = "sequence, id"

    form_id = fields.Many2one(
        "crm.service.feedback.form",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(string="Câu hỏi", required=True)
    description = fields.Text()
    question_type = fields.Selection(
        [
            ("rating", "Chấm điểm"),
            ("satisfaction", "Mức độ hài lòng"),
            ("boolean", "Có/Không"),
            ("text", "Văn bản tự do"),
        ],
        default="rating",
        required=True,
    )
    required = fields.Boolean(default=True)
    max_score = fields.Integer(default=5)

    @api.constrains("max_score", "question_type")
    def _check_max_score(self):
        for question in self:
            if question.question_type in ("rating", "satisfaction") and question.max_score <= 0:
                raise ValidationError(_("Câu hỏi chấm điểm phải có điểm tối đa lớn hơn 0."))


class CustomerFeedbackRequest(models.Model):
    _name = "crm.service.feedback.request"
    _description = "Yêu Cầu Phản Hồi Khách Hàng"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char(
        required=True,
        copy=False,
        readonly=True,
        default="Mới",
        tracking=True,
    )
    form_id = fields.Many2one(
        "crm.service.feedback.form",
        required=True,
        tracking=True,
        ondelete="restrict",
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Khách hàng",
        required=True,
        tracking=True,
    )
    email = fields.Char()
    lead_id = fields.Many2one(
        "crm.lead",
        string="Lead / Cơ hội",
        ondelete="set null",
        tracking=True,
    )
    user_id = fields.Many2one(
        "res.users",
        string="Người phụ trách",
        default=lambda self: self.env.user,
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
    )
    state = fields.Selection(
        [
            ("draft", "Nháp"),
            ("sent", "Đã gửi"),
            ("answered", "Đã phản hồi"),
            ("cancelled", "Đã hủy"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    access_token = fields.Char(copy=False, readonly=True, index=True)
    sent_date = fields.Datetime(tracking=True)
    answered_date = fields.Datetime(tracking=True)
    due_date = fields.Datetime(tracking=True)
    line_ids = fields.One2many(
        "crm.service.feedback.answer",
        "request_id",
        string="Câu trả lời",
        copy=True,
    )
    average_score = fields.Float(
        compute="_compute_feedback_result",
        store=True,
        digits=(16, 2),
    )
    satisfaction_level = fields.Selection(
        [
            ("satisfied", "Hài lòng"),
            ("neutral", "Trung lập"),
            ("dissatisfied", "Không hài lòng"),
        ],
        compute="_compute_feedback_result",
        store=True,
    )
    is_negative = fields.Boolean(
        string="Phản hồi tiêu cực",
        compute="_compute_feedback_result",
        store=True,
    )
    additional_note = fields.Text()
    staff_reply = fields.Text(
        string="Nội dung thư phản hồi",
        tracking=True,
    )
    staff_reply_subject = fields.Char(
        string="Tiêu đề thư phản hồi",
        tracking=True,
    )
    staff_reply_user_id = fields.Many2one(
        "res.users",
        string="Người trả lời",
        readonly=True,
        copy=False,
        tracking=True,
    )
    staff_reply_date = fields.Datetime(
        string="Ngày trả lời",
        readonly=True,
        copy=False,
        tracking=True,
    )
    staff_reply_sent_date = fields.Datetime(
        string="Ngày gửi trả lời",
        readonly=True,
        copy=False,
        tracking=True,
    )
    complaint_ticket_id = fields.Many2one(
        "crm.service.complaint.ticket",
        string="Khiếu nại liên quan",
        readonly=True,
        copy=False,
    )

    @api.depends("line_ids.score", "line_ids.has_score")
    def _compute_feedback_result(self):
        for request in self:
            scored_lines = request.line_ids.filtered("has_score")
            if scored_lines:
                request.average_score = sum(scored_lines.mapped("score")) / len(scored_lines)
            else:
                request.average_score = 0.0
            low_line = any(line.score and line.score <= 2.0 for line in scored_lines)
            if request.average_score >= 4.0:
                request.satisfaction_level = "satisfied"
            elif request.average_score >= 3.0:
                request.satisfaction_level = "neutral"
            elif scored_lines:
                request.satisfaction_level = "dissatisfied"
            else:
                request.satisfaction_level = False
            request.is_negative = bool(scored_lines and (request.average_score < 3.0 or low_line))

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        for request in self:
            request.email = request.partner_id.email

    @api.onchange("form_id")
    def _onchange_form_id(self):
        for request in self:
            if request.form_id and not request.line_ids:
                request.line_ids = request._prepare_answer_line_commands()

    @api.model
    def _clean_answer_line_commands(self, vals):
        commands = vals.get("line_ids")
        if not commands:
            return vals

        cleaned_commands = []
        for command in commands:
            if not isinstance(command, (list, tuple)) or len(command) < 3:
                cleaned_commands.append(command)
                continue
            if command[0] == 0 and not command[2].get("question_id"):
                continue
            cleaned_commands.append(command)

        vals["line_ids"] = cleaned_commands
        return vals

    def _check_form_has_questions(self):
        for request in self:
            if request.form_id and not request.form_id.question_ids:
                raise UserError(_("Biểu mẫu phản hồi phải có ít nhất một câu hỏi trước khi tạo yêu cầu phản hồi."))

    def _check_customer_submission_allowed(self):
        for request in self:
            if request.state == "draft":
                raise UserError(_("Biểu mẫu phản hồi chưa được gửi cho khách hàng."))
            if request.state == "answered":
                raise UserError(_("Yêu cầu phản hồi này đã được khách hàng gửi trả lời."))
            if request.state == "cancelled":
                raise UserError(_("Yêu cầu phản hồi này đã bị hủy."))

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            self._clean_answer_line_commands(vals)
            if vals.get("additional_note") and not self.env.context.get("customer_feedback_submit"):
                raise UserError(_("Ý kiến bổ sung chỉ được khách hàng nhập qua biểu mẫu portal/email."))
            if vals.get("name", "Mới") in ("New", "Mới"):
                vals["name"] = sequence.next_by_code("crm.service.feedback.request") or "Mới"
            vals.setdefault("access_token", secrets.token_urlsafe(32))
        requests = super().create(vals_list)
        requests._check_form_has_questions()
        for request, vals in zip(requests, vals_list):
            if not vals.get("line_ids"):
                request._sync_answer_lines()
        return requests

    def write(self, vals):
        self._clean_answer_line_commands(vals)
        if "additional_note" in vals and not self.env.context.get("customer_feedback_submit"):
            raise UserError(_("Ý kiến bổ sung chỉ được khách hàng nhập qua biểu mẫu portal/email."))
        if vals.get("state") == "answered" and not self.env.context.get("customer_feedback_submit"):
            raise UserError(_("Chỉ khách hàng được gửi phản hồi qua biểu mẫu portal/email."))
        result = super().write(vals)
        if "form_id" in vals:
            self._check_form_has_questions()
            self._sync_answer_lines()
        return result

    def _prepare_answer_line_commands(self):
        self.ensure_one()
        return [
            (
                0,
                0,
                {
                    "question_id": question.id,
                    "sequence": question.sequence,
                },
            )
            for question in self.form_id.question_ids
        ]

    def _sync_answer_lines(self):
        for request in self:
            existing_questions = request.line_ids.mapped("question_id")
            missing_questions = request.form_id.question_ids - existing_questions
            if missing_questions:
                request.write(
                    {
                        "line_ids": [
                            (
                                0,
                                0,
                                {
                                    "question_id": question.id,
                                    "sequence": question.sequence,
                                },
                            )
                            for question in missing_questions
                        ]
                    }
                )

    def get_feedback_url(self):
        self.ensure_one()
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url", "")
        return "%s/feedback/%s" % (base_url.rstrip("/"), self.access_token)

    def action_send_email(self):
        template = self.env.ref(
            "thuc_linh_crm_service.mail_template_feedback_request",
            raise_if_not_found=False,
        )
        now = fields.Datetime.now()
        for request in self:
            request._check_form_has_questions()
            if not (request.email or request.partner_id.email):
                raise UserError(_("Khách hàng %s chưa có địa chỉ email.") % request.partner_id.display_name)
            request._sync_answer_lines()
            if template:
                template.send_mail(request.id, force_send=False)
            request.write({"state": "sent", "sent_date": now})

    def _default_staff_reply_subject(self):
        self.ensure_one()
        return _("Phản hồi từ %s: %s") % (
            self.company_id.name or "Thục Linh",
            self.form_id.name,
        )

    def action_open_staff_reply_wizard(self):
        self.ensure_one()
        if self.state != "answered":
            raise UserError(_("Chỉ trả lời khách hàng sau khi khách đã gửi phản hồi."))
        return {
            "name": _("Soạn thư phản hồi khách hàng"),
            "type": "ir.actions.act_window",
            "res_model": "crm.service.feedback.reply.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_request_id": self.id,
                "default_subject": self.staff_reply_subject or self._default_staff_reply_subject(),
                "default_body": self.staff_reply,
            },
        }

    def action_send_staff_reply(self):
        template = self.env.ref(
            "thuc_linh_crm_service.mail_template_feedback_staff_reply",
            raise_if_not_found=False,
        )
        now = fields.Datetime.now()
        for request in self:
            if request.state != "answered":
                raise UserError(_("Chỉ trả lời khách hàng sau khi khách đã gửi phản hồi."))
            if not (request.staff_reply or "").strip():
                raise UserError(_("Vui lòng nhập nội dung thư phản hồi khách hàng."))
            if not (request.email or request.partner_id.email):
                raise UserError(_("Khách hàng %s chưa có địa chỉ email.") % request.partner_id.display_name)
            if template:
                template.send_mail(request.id, force_send=False)
            request.write(
                {
                    "staff_reply_user_id": self.env.user.id,
                    "staff_reply_date": now,
                    "staff_reply_sent_date": now,
                }
            )
            request.message_post(
                body=_("Đã gửi trả lời phản hồi cho khách hàng: %s")
                % request.partner_id.display_name
            )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Đã gửi trả lời khách hàng"),
                "message": _("%s phản hồi đã được gửi cho khách hàng.") % len(self),
                "type": "success",
                "sticky": False,
            },
        }

    def action_mark_answered(self):
        if not self.env.context.get("customer_feedback_submit"):
            raise UserError(_("Nhân viên chỉ gửi và theo dõi yêu cầu phản hồi; khách hàng sẽ điền biểu mẫu qua portal/email."))
        self._check_customer_submission_allowed()
        self._check_form_has_questions()
        self._check_required_answers()
        self.write({"state": "answered", "answered_date": fields.Datetime.now()})

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_reset_to_draft(self):
        self.write({"state": "draft"})

    def _check_required_answers(self):
        for request in self:
            missing = request.line_ids.filtered(lambda line: line.required and not line.is_answered)
            if missing:
                raise UserError(
                    _("Vui lòng trả lời các câu hỏi bắt buộc: %s")
                    % ", ".join(missing.mapped("question_id.name"))
                )

    def action_create_complaint(self):
        self.ensure_one()
        if self.complaint_ticket_id:
            ticket = self.complaint_ticket_id
        else:
            description = "\n".join(
                [
                    _("Biểu mẫu phản hồi: %s") % self.form_id.display_name,
                    _("Điểm trung bình: %.2f") % self.average_score,
                    self.additional_note or "",
                ]
            )
            severity = "high" if self.average_score and self.average_score < 2.5 else "medium"
            ticket = self.env["crm.service.complaint.ticket"].create(
                {
                    "customer_id": self.partner_id.id,
                    "lead_id": self.lead_id.id,
                    "sale_user_id": self.user_id.id,
                    "assigned_user_id": self.user_id.id,
                    "title": _("Khiếu nại từ phản hồi %s") % self.name,
                    "description": description,
                    "severity": severity,
                    "state": "draft",
                    "feedback_request_id": self.id,
                }
            )
            self.complaint_ticket_id = ticket.id
        action = self.env.ref("thuc_linh_crm_service.action_complaint_ticket").read()[0]
        action["views"] = [(self.env.ref("thuc_linh_crm_service.view_complaint_ticket_form").id, "form")]
        action["res_id"] = ticket.id
        return action


class CustomerFeedbackAnswer(models.Model):
    _name = "crm.service.feedback.answer"
    _description = "Câu Trả Lời Phản Hồi Khách Hàng"
    _order = "sequence, id"

    request_id = fields.Many2one(
        "crm.service.feedback.request",
        required=True,
        ondelete="cascade",
    )
    form_id = fields.Many2one(related="request_id.form_id", store=True)
    partner_id = fields.Many2one(related="request_id.partner_id", store=True)
    sequence = fields.Integer(default=10)
    question_id = fields.Many2one(
        "crm.service.feedback.question",
        required=True,
        ondelete="restrict",
    )
    question_type = fields.Selection(related="question_id.question_type", store=True)
    required = fields.Boolean(related="question_id.required", store=True)
    max_score = fields.Integer(related="question_id.max_score", store=True)
    rating_value = fields.Integer(string="Điểm đánh giá")
    boolean_value = fields.Selection([("yes", "Có"), ("no", "Không")], string="Câu trả lời")
    text_value = fields.Text(string="Ý kiến")
    score = fields.Float(compute="_compute_answer_state", store=True)
    has_score = fields.Boolean(compute="_compute_answer_state", store=True)
    is_answered = fields.Boolean(compute="_compute_answer_state", store=True)

    @api.depends("question_type", "rating_value", "boolean_value", "text_value")
    def _compute_answer_state(self):
        for line in self:
            line.score = 0.0
            line.has_score = False
            if line.question_type in ("rating", "satisfaction"):
                line.is_answered = bool(line.rating_value)
                if line.rating_value:
                    line.score = float(line.rating_value)
                    line.has_score = True
            elif line.question_type == "boolean":
                line.is_answered = bool(line.boolean_value)
                if line.boolean_value:
                    line.score = 5.0 if line.boolean_value == "yes" else 0.0
                    line.has_score = True
            else:
                line.is_answered = bool((line.text_value or "").strip())

    @api.model
    def _answer_value_fields(self):
        return {"rating_value", "boolean_value", "text_value"}

    @api.model
    def _check_answer_value_write_allowed(self, vals):
        if not (set(vals) & self._answer_value_fields()):
            return
        if self.env.context.get("customer_feedback_submit"):
            return
        raise UserError(_("Câu trả lời phản hồi chỉ được khách hàng nhập qua biểu mẫu portal/email."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._check_answer_value_write_allowed(vals)
        return super().create(vals_list)

    def write(self, vals):
        self._check_answer_value_write_allowed(vals)
        return super().write(vals)

    @api.constrains("rating_value", "question_type", "max_score")
    def _check_rating_value(self):
        for line in self:
            if line.question_type in ("rating", "satisfaction") and line.rating_value:
                if line.rating_value < 1 or line.rating_value > line.max_score:
                    raise ValidationError(
                        _("Điểm đánh giá cho '%s' phải nằm trong khoảng từ 1 đến %s.")
                        % (line.question_id.name, line.max_score)
                    )

    @api.constrains("question_id", "request_id")
    def _check_question_form(self):
        for line in self:
            if line.question_id.form_id != line.request_id.form_id:
                raise ValidationError(_("Câu hỏi trả lời phải thuộc biểu mẫu phản hồi."))


class CustomerFeedbackReplyWizard(models.TransientModel):
    _name = "crm.service.feedback.reply.wizard"
    _description = "Soạn Thư Phản Hồi Khách Hàng"

    request_id = fields.Many2one(
        "crm.service.feedback.request",
        string="Phản hồi khách hàng",
        required=True,
        ondelete="cascade",
    )
    subject = fields.Char(string="Tiêu đề thư", required=True)
    body = fields.Text(string="Nội dung thư", required=True)

    def action_send_reply(self):
        self.ensure_one()
        self.request_id.write(
            {
                "staff_reply_subject": self.subject,
                "staff_reply": self.body,
            }
        )
        return self.request_id.action_send_staff_reply()
