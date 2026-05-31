import re
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class CrmLead(models.Model):
    _inherit = "crm.lead"

    partner_name = fields.Char(string="Tên công ty")
    contact_name = fields.Char(string="Người liên hệ chính")
    email_from = fields.Char(string="Email")
    phone = fields.Char(string="Số điện thoại")
    website = fields.Char(string="Trang web")
    source_id = fields.Many2one("utm.source", string="Nguồn lead")
    user_id = fields.Many2one("res.users", string="Nhân viên phụ trách", tracking=True)
    initial_product_requirement = fields.Text(
        string="Nhu cầu sản phẩm ban đầu",
        tracking=True,
    )
    last_interaction_date = fields.Date(
        string="Ngày tương tác cuối",
        default=fields.Date.context_today,
        tracking=True,
    )
    inactive_archive_date = fields.Date(
        string="Ngày lưu trữ tự động",
        readonly=True,
        copy=False,
        tracking=True,
    )
    archived_by_cron = fields.Boolean(
        string="Lưu trữ tự động",
        readonly=True,
        copy=False,
    )
    duplicate_state = fields.Selection(
        [
            ("clean", "Không trùng"),
            ("similar", "Có dữ liệu tương tự"),
            ("exact", "Trùng hoàn toàn"),
        ],
        string="Tình trạng trùng dữ liệu",
        compute="_compute_duplicate_data",
        store=True,
    )
    duplicate_lead_ids = fields.Many2many(
        "crm.lead",
        "crm_lead_duplicate_rel",
        "lead_id",
        "duplicate_id",
        compute="_compute_duplicate_data",
        store=True,
        string="Lead nghi trùng",
    )
    duplicate_count = fields.Integer(
        string="Số lead nghi trùng",
        compute="_compute_duplicate_data",
        store=True,
    )
    data_quality_state = fields.Selection(
        [
            ("valid", "Hợp lệ"),
            ("missing", "Thiếu dữ liệu"),
            ("invalid", "Sai định dạng"),
        ],
        string="Chất lượng dữ liệu",
        compute="_compute_data_quality",
        store=True,
    )
    missing_required_fields = fields.Char(
        string="Trường còn thiếu",
        compute="_compute_data_quality",
        store=True,
    )

    @api.model
    def _required_lead_fields(self):
        return {
            "partner_name": _("Tên công ty"),
            "contact_name": _("Người liên hệ chính"),
            "email_from": _("Email"),
            "phone": _("Số điện thoại"),
            "website": _("Trang web"),
            "source_id": _("Nguồn lead"),
            "user_id": _("Nhân viên phụ trách"),
            "initial_product_requirement": _("Nhu cầu sản phẩm ban đầu"),
        }

    @api.model
    def _normalize_text(self, value):
        return re.sub(r"\s+", " ", (value or "").strip()).casefold()

    @api.model
    def _normalize_phone(self, value):
        return re.sub(r"\D+", "", value or "")

    def _get_duplicate_candidates(self):
        self.ensure_one()
        domain = [("active", "in", [True, False])]
        if isinstance(self.id, int):
            domain.append(("id", "!=", self.id))
        clauses = []
        if self.email_from:
            clauses.append(("email_from", "=ilike", self.email_from.strip()))
        if self.phone:
            clauses.append(("phone", "=ilike", self.phone.strip()))
        if self.partner_name:
            clauses.append(("partner_name", "=ilike", self.partner_name.strip()))
        if self.contact_name:
            clauses.append(("contact_name", "=ilike", self.contact_name.strip()))
        if not clauses:
            return self.browse()
        if len(clauses) == 1:
            return self.with_context(active_test=False).search(domain + clauses, limit=20)
        duplicate_domain = ["|"] * (len(clauses) - 1) + clauses
        return self.with_context(active_test=False).search(domain + duplicate_domain, limit=20)

    def _duplicate_score(self, other):
        self.ensure_one()
        score = 0
        if self._normalize_text(self.partner_name) and self._normalize_text(self.partner_name) == self._normalize_text(other.partner_name):
            score += 2
        if self._normalize_text(self.contact_name) and self._normalize_text(self.contact_name) == self._normalize_text(other.contact_name):
            score += 1
        if self._normalize_text(self.email_from) and self._normalize_text(self.email_from) == self._normalize_text(other.email_from):
            score += 3
        if self._normalize_phone(self.phone) and self._normalize_phone(self.phone) == self._normalize_phone(other.phone):
            score += 3
        return score

    def _is_exact_duplicate(self, other):
        self.ensure_one()
        return (
            self._normalize_text(self.partner_name)
            and self._normalize_text(self.partner_name) == self._normalize_text(other.partner_name)
            and self._normalize_text(self.contact_name) == self._normalize_text(other.contact_name)
            and self._normalize_text(self.email_from) == self._normalize_text(other.email_from)
            and self._normalize_phone(self.phone) == self._normalize_phone(other.phone)
        )

    @api.depends("partner_name", "contact_name", "email_from", "phone")
    def _compute_duplicate_data(self):
        for lead in self:
            similar_leads = self.browse()
            exact_leads = self.browse()
            if lead.partner_name or lead.contact_name or lead.email_from or lead.phone:
                for candidate in lead._get_duplicate_candidates():
                    if lead._is_exact_duplicate(candidate):
                        exact_leads |= candidate
                    elif lead._duplicate_score(candidate) >= 3:
                        similar_leads |= candidate
            duplicates = exact_leads | similar_leads
            lead.duplicate_lead_ids = duplicates
            lead.duplicate_count = len(duplicates)
            if exact_leads:
                lead.duplicate_state = "exact"
            elif similar_leads:
                lead.duplicate_state = "similar"
            else:
                lead.duplicate_state = "clean"

    @api.depends("partner_name", "contact_name", "email_from", "phone", "website", "source_id", "user_id", "initial_product_requirement")
    def _compute_data_quality(self):
        for lead in self:
            missing = [
                label
                for field_name, label in lead._required_lead_fields().items()
                if not lead[field_name]
            ]
            invalid = bool(
                (lead.email_from and not lead._is_valid_email(lead.email_from))
                or (lead.phone and not lead._is_valid_phone(lead.phone))
            )
            lead.missing_required_fields = ", ".join(missing)
            if missing:
                lead.data_quality_state = "missing"
            elif invalid:
                lead.data_quality_state = "invalid"
            else:
                lead.data_quality_state = "valid"

    @api.model
    def _is_valid_email(self, value):
        return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value or ""))

    @api.model
    def _is_valid_phone(self, value):
        return bool(re.match(r"^[0-9+().\-\s]{7,20}$", value or ""))

    def _validate_crm_lead_data(self):
        for lead in self.filtered(lambda item: item.active and item.type == "lead"):
            missing = [
                label
                for field_name, label in lead._required_lead_fields().items()
                if not lead[field_name]
            ]
            if missing:
                raise ValidationError(_("Vui lòng nhập đầy đủ thông tin bắt buộc: %s") % ", ".join(missing))
            if lead.email_from and not lead._is_valid_email(lead.email_from):
                raise ValidationError(_("Email khách hàng không đúng định dạng."))
            if lead.phone and not lead._is_valid_phone(lead.phone):
                raise ValidationError(_("Số điện thoại không đúng định dạng."))

    def _check_exact_duplicate_policy(self):
        manager_group = "sales_team.group_sale_manager"
        if self.env.user.has_group(manager_group):
            return
        for lead in self.filtered(lambda item: item.type == "lead"):
            exact_duplicates = lead._get_duplicate_candidates().filtered(lambda candidate: lead._is_exact_duplicate(candidate))
            if exact_duplicates:
                raise UserError(
                    _(
                        "Lead này trùng hoàn toàn với hồ sơ đã tồn tại: %s. "
                        "Vui lòng kiểm tra lại hoặc yêu cầu quản lý kinh doanh phê duyệt xử lý dữ liệu trùng."
                    )
                    % ", ".join(exact_duplicates.mapped("display_name"))
                )

    @api.onchange("partner_name", "contact_name", "email_from", "phone")
    def _onchange_duplicate_fields(self):
        for lead in self:
            if not lead.partner_name and not lead.contact_name and not lead.email_from and not lead.phone:
                continue
            candidates = lead._get_duplicate_candidates()
            duplicates = candidates.filtered(lambda candidate: lead._is_exact_duplicate(candidate) or lead._duplicate_score(candidate) >= 3)
            if duplicates:
                return {
                    "warning": {
                        "title": _("Cảnh báo dữ liệu trùng"),
                        "message": _("Hệ thống tìm thấy lead có dữ liệu tương tự: %s") % ", ".join(duplicates.mapped("display_name")),
                    }
                }
        return {}

    @api.model_create_multi
    def create(self, vals_list):
        default_stage = self.env.ref("crm_tong_hop.stage_new_lead", raise_if_not_found=False)
        for vals in vals_list:
            vals.setdefault("last_interaction_date", fields.Date.context_today(self))
            if vals.get("type", "lead") == "lead" and not vals.get("stage_id") and default_stage:
                vals["stage_id"] = default_stage.id
        leads = super().create(vals_list)
        leads._validate_crm_lead_data()
        leads._check_exact_duplicate_policy()
        return leads

    def write(self, vals):
        result = super().write(vals)
        if set(vals) & (set(self._required_lead_fields()) | {"type", "active"}):
            self._validate_crm_lead_data()
        if set(vals) & {"partner_name", "contact_name", "email_from", "phone", "type"}:
            self._check_exact_duplicate_policy()
        return result

    def unlink(self):
        if not self.env.user.has_group("sales_team.group_sale_manager") and not self.env.context.get("crm_delete_approval_id"):
            raise UserError(_("Xóa lead phải được quản lý kinh doanh phê duyệt trước."))
        return super().unlink()

    def action_open_duplicate_leads(self):
        self.ensure_one()
        return {
            "name": _("Lead nghi trùng"),
            "type": "ir.actions.act_window",
            "res_model": "crm.lead",
            "view_mode": "tree,form",
            "domain": [("id", "in", self.duplicate_lead_ids.ids)],
            "context": {"create": False},
        }

    def action_mark_interaction_today(self):
        self.write({"last_interaction_date": fields.Date.context_today(self)})
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Đã ghi nhận tương tác"),
                "message": _("Ngày tương tác cuối đã được cập nhật."),
                "type": "success",
                "sticky": False,
            },
        }

    def action_request_delete_approval(self):
        self.ensure_one()
        approval = self.env["crm.lead.data.approval"].create(
            {
                "request_type": "delete",
                "lead_id": self.id,
                "reason": _("Yêu cầu xóa dữ liệu lead."),
            }
        )
        return approval.action_open_form()

    def action_request_merge_approval(self):
        self.ensure_one()
        duplicate = self.duplicate_lead_ids[:1]
        if not duplicate:
            raise UserError(_("Không có lead nghi trùng để yêu cầu phê duyệt merge."))
        approval = self.env["crm.lead.data.approval"].create(
            {
                "request_type": "merge",
                "lead_id": self.id,
                "duplicate_lead_id": duplicate.id,
                "reason": _("Yêu cầu phê duyệt merge dữ liệu trùng."),
            }
        )
        return approval.action_open_form()

    def action_open_transfer_owner_wizard(self):
        return {
            "name": _("Chuyển nhân viên phụ trách"),
            "type": "ir.actions.act_window",
            "res_model": "crm.lead.transfer.owner.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_lead_ids": [(6, 0, self.ids)]},
        }

    @api.model
    def _cron_archive_inactive_leads(self):
        cutoff_date = fields.Date.context_today(self) - timedelta(days=180)
        cutoff_datetime = fields.Datetime.to_datetime(cutoff_date)
        inactive_leads = self.search(
            [
                ("active", "=", True),
                ("type", "=", "lead"),
                "|",
                ("last_interaction_date", "<=", cutoff_date),
                "&",
                ("last_interaction_date", "=", False),
                ("write_date", "<=", cutoff_datetime),
            ]
        )
        inactive_leads.write(
            {
                "active": False,
                "archived_by_cron": True,
                "inactive_archive_date": fields.Date.context_today(self),
            }
        )
        return True
