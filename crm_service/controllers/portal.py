import base64

from werkzeug.exceptions import NotFound

from odoo import _, http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class CustomerServicePortal(CustomerPortal):
    def _current_partner(self):
        return request.env.user.partner_id.commercial_partner_id

    def _partner_domain(self, field_name):
        return [(field_name, "child_of", [self._current_partner().id])]

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if "feedback_count" in counters:
            values["feedback_count"] = request.env["crm.service.feedback.request"].sudo().search_count(
                self._partner_domain("partner_id")
            )
        if "complaint_count" in counters:
            values["complaint_count"] = request.env["crm.service.complaint.ticket"].sudo().search_count(
                self._partner_domain("customer_id")
            )
        return values

    def _get_feedback_request(self, feedback_id):
        feedback_request = request.env["crm.service.feedback.request"].search(
            [("id", "=", feedback_id)] + self._partner_domain("partner_id"),
            limit=1,
        )
        if not feedback_request:
            raise NotFound()
        return feedback_request.sudo()

    def _get_feedback_request_by_token(self, access_token):
        feedback_request = request.env["crm.service.feedback.request"].sudo().search(
            [("access_token", "=", access_token)],
            limit=1,
        )
        if not feedback_request:
            raise NotFound()
        return feedback_request

    def _write_feedback_answers(self, feedback_request, post):
        feedback_request.sudo()._check_customer_submission_allowed()
        for line in feedback_request.line_ids:
            values = {}
            if line.question_type in ("rating", "satisfaction"):
                rating = post.get("rating_%s" % line.id)
                try:
                    values["rating_value"] = int(rating) if rating else 0
                except ValueError as error:
                    raise UserError(_("Vui lòng nhập điểm đánh giá hợp lệ.")) from error
            elif line.question_type == "boolean":
                values["boolean_value"] = post.get("boolean_%s" % line.id) or False
            else:
                values["text_value"] = post.get("text_%s" % line.id) or False
            line.sudo().with_context(customer_feedback_submit=True).write(values)
        feedback_request.sudo().with_context(customer_feedback_submit=True).write(
            {"additional_note": post.get("additional_note") or False}
        )
        feedback_request.sudo().with_context(customer_feedback_submit=True).action_mark_answered()

    def _render_feedback_request(self, feedback_request, error=None, submitted=False):
        return request.render(
            "thuc_linh_crm_service.portal_feedback_request",
            {
                "feedback_request": feedback_request,
                "error": error,
                "submitted": submitted,
                "page_name": "feedback",
            },
        )

    @http.route(["/my/feedback"], type="http", auth="user", website=True)
    def portal_my_feedback(self, page=1, **kw):
        feedback_model = request.env["crm.service.feedback.request"]
        domain = self._partner_domain("partner_id")
        total = feedback_model.search_count(domain)
        pager = portal_pager(
            url="/my/feedback",
            total=total,
            page=page,
            step=self._items_per_page,
        )
        feedback_requests = feedback_model.search(
            domain,
            order="create_date desc",
            limit=self._items_per_page,
            offset=pager["offset"],
        )
        return request.render(
            "thuc_linh_crm_service.portal_my_feedback_requests",
            {
                "feedback_requests": feedback_requests,
                "pager": pager,
                "page_name": "feedback",
            },
        )

    @http.route(
        ["/my/feedback/<int:feedback_id>"],
        type="http",
        auth="user",
        website=True,
        methods=["GET", "POST"],
    )
    def portal_feedback_detail(self, feedback_id, **post):
        feedback_request = self._get_feedback_request(feedback_id)
        if request.httprequest.method == "POST":
            try:
                self._write_feedback_answers(feedback_request, post)
            except UserError as error:
                return self._render_feedback_request(feedback_request, error=error.args[0])
            return request.redirect("/my/feedback/%s?submitted=1" % feedback_request.id)
        return self._render_feedback_request(
            feedback_request,
            submitted=bool(post.get("submitted")),
        )

    @http.route(
        ["/feedback/<string:access_token>"],
        type="http",
        auth="public",
        website=True,
        methods=["GET", "POST"],
    )
    def portal_feedback_token(self, access_token, **post):
        feedback_request = self._get_feedback_request_by_token(access_token)
        if request.httprequest.method == "POST":
            try:
                self._write_feedback_answers(feedback_request, post)
            except UserError as error:
                return self._render_feedback_request(feedback_request, error=error.args[0])
            return request.redirect("/feedback/%s?submitted=1" % feedback_request.access_token)
        return self._render_feedback_request(
            feedback_request,
            submitted=bool(post.get("submitted")),
        )

    def _get_complaint_ticket(self, ticket_id):
        ticket = request.env["crm.service.complaint.ticket"].search(
            [("id", "=", ticket_id)] + self._partner_domain("customer_id"),
            limit=1,
        )
        if not ticket:
            raise NotFound()
        return ticket

    def _complaint_values_from_post(self, post):
        title = (post.get("title") or "").strip()
        description = (post.get("description") or "").strip()
        severity = post.get("severity") or "medium"
        if not title:
            raise UserError(_("Vui lòng nhập tiêu đề khiếu nại."))
        if not description:
            raise UserError(_("Vui lòng nhập nội dung khiếu nại."))
        if severity not in ("low", "medium", "high"):
            severity = "medium"
        return {
            "title": title,
            "description": description,
            "severity": severity,
            "related_document_ref": (post.get("related_document_ref") or "").strip() or False,
        }

    def _create_attachments(self, ticket):
        files = request.httprequest.files.getlist("attachment")
        attachment_model = request.env["ir.attachment"].sudo()
        for upload in files:
            if not upload or not upload.filename:
                continue
            attachment_model.create(
                {
                    "name": upload.filename,
                    "datas": base64.b64encode(upload.read()).decode("ascii"),
                    "res_model": ticket._name,
                    "res_id": ticket.id,
                    "type": "binary",
                }
            )

    def _get_attachments(self, ticket):
        if not ticket:
            return request.env["ir.attachment"].sudo().browse()
        return request.env["ir.attachment"].sudo().search(
            [("res_model", "=", ticket._name), ("res_id", "=", ticket.id)]
        )

    def _render_complaint_form(self, ticket=False, error=False, updated=False):
        return request.render(
            "thuc_linh_crm_service.portal_complaint_form",
            {
                "ticket": ticket,
                "attachments": self._get_attachments(ticket),
                "error": error,
                "updated": updated,
                "page_name": "complaints",
            },
        )

    @http.route(["/my/complaints"], type="http", auth="user", website=True)
    def portal_my_complaints(self, page=1, **kw):
        ticket_model = request.env["crm.service.complaint.ticket"]
        domain = self._partner_domain("customer_id")
        total = ticket_model.search_count(domain)
        pager = portal_pager(
            url="/my/complaints",
            total=total,
            page=page,
            step=self._items_per_page,
        )
        tickets = ticket_model.search(
            domain,
            order="create_date desc",
            limit=self._items_per_page,
            offset=pager["offset"],
        )
        return request.render(
            "thuc_linh_crm_service.portal_my_complaints",
            {
                "tickets": tickets,
                "pager": pager,
                "page_name": "complaints",
            },
        )

    @http.route(
        ["/my/complaints/new"],
        type="http",
        auth="user",
        website=True,
        methods=["GET", "POST"],
    )
    def portal_complaint_new(self, **post):
        if request.httprequest.method == "POST":
            try:
                values = self._complaint_values_from_post(post)
                values.update(
                    {
                        "customer_id": request.env.user.partner_id.id,
                        "sale_user_id": False,
                        "assigned_user_id": False,
                        "state": "draft",
                    }
                )
                ticket = request.env["crm.service.complaint.ticket"].create(values)
                self._create_attachments(ticket)
            except UserError as error:
                return self._render_complaint_form(error=error.args[0])
            return request.redirect("/my/complaints/%s" % ticket.id)
        return self._render_complaint_form()

    @http.route(
        ["/my/complaints/<int:ticket_id>"],
        type="http",
        auth="user",
        website=True,
        methods=["GET", "POST"],
    )
    def portal_complaint_detail(self, ticket_id, **post):
        ticket = self._get_complaint_ticket(ticket_id)
        error = False
        if request.httprequest.method == "POST":
            if post.get("delete"):
                try:
                    ticket.unlink()
                    return request.redirect("/my/complaints")
                except UserError as delete_error:
                    error = delete_error.args[0]
            elif ticket.customer_can_edit:
                try:
                    values = self._complaint_values_from_post(post)
                    ticket.write(values)
                    self._create_attachments(ticket)
                    return request.redirect("/my/complaints/%s?updated=1" % ticket.id)
                except UserError as write_error:
                    error = write_error.args[0]
            else:
                error = _("Phiếu khiếu nại này không còn được phép chỉnh sửa.")
        return self._render_complaint_form(
            ticket=ticket,
            error=error,
            updated=bool(post.get("updated")),
        )
