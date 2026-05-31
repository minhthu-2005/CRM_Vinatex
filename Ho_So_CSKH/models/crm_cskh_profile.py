from datetime import timedelta

from markupsafe import Markup, escape

from odoo import models, fields, api, _
from odoo.tools import email_split, html2plaintext


class CrmCskhProfile(models.Model):
    # CUSTOM THÊM MỚI
    # Tạo model quản lý Hồ sơ CSKH
    _name = 'crm.cskh.profile'
    _description = 'Hồ sơ chăm sóc khách hàng'

    # KẾ THỪA MODULE MAIL
    # mail.thread, mail.activity.mixin
    _inherit = ['mail.thread', 'mail.activity.mixin']

    _order = 'interaction_date desc, id desc'
    _sql_constraints = [
        (
            'gmail_message_id_unique',
            'unique(gmail_message_id)',
            'Email này đã được đồng bộ vào Hồ sơ CSKH.'
        ),
    ]

    # CUSTOM THÊM MỚI
    # Sinh mã Hồ sơ CSKH tự động
    name = fields.Char(
        string='Mã hồ sơ CSKH',
        required=True,
        copy=False,
        readonly=True,
        default='Mới'
    )

    # KẾ THỪA MODULE CRM
    # Model crm.lead
    #
    # CUSTOM THÊM MỚI
    # Liên kết Hồ sơ CSKH với khách hàng tiềm năng/cơ hội
    lead_id = fields.Many2one(
        'crm.lead',
        string='Cơ hội',
        ondelete='cascade'
    )

    # KẾ THỪA MODULE CRM
    # Model res.partner
    #
    # CUSTOM THÊM MỚI
    # Cho phép chọn khách hàng trực tiếp hoặc tự lấy từ khách hàng tiềm năng/cơ hội
    customer_id = fields.Many2one(
        'res.partner',
        string='Khách hàng',
        required=True
    )

    # CUSTOM THÊM MỚI
    # Lưu nhân viên phụ trách Hồ sơ CSKH
    user_id = fields.Many2one(
        'res.users',
        string='Nhân viên phụ trách',
        default=lambda self: self.env.user
    )
    cskh_summary_message_id = fields.Many2one(
        'mail.message',
        string='Tin nhắn tóm tắt CSKH',
        readonly=True,
        copy=False,
    )
    cskh_summary_posted = fields.Boolean(
        string='Đã ghi tóm tắt CSKH',
        readonly=True,
        copy=False,
    )

    # CUSTOM THÊM MỚI
    # Phân loại tương tác với khách hàng
    interaction_type = fields.Selection([
        ('email', 'Email'),
        ('call', 'Cuộc gọi'),
        ('meeting', 'Cuộc họp'),
        ('quotation', 'Báo giá'),
        ('complaint', 'Khiếu nại'),
        ('note', 'Ghi chú trao đổi'),
    ], string='Loại tương tác', required=True)

    # CUSTOM THÊM MỚI
    # Lưu thời gian phát sinh tương tác
    interaction_date = fields.Datetime(
        string='Thời gian tương tác',
        default=fields.Datetime.now,
        required=True
    )

    # CUSTOM THÊM MỚI
    # Lưu nội dung trao đổi với khách hàng
    content = fields.Text(
        string='Nội dung trao đổi'
    )

    # CUSTOM THÊM MỚI
    # Lưu kết quả làm việc sau tương tác
    result = fields.Text(
        string='Kết quả làm việc'
    )

    # CUSTOM THÊM MỚI
    # Lưu nhu cầu khách hàng
    customer_need = fields.Text(
        string='Nhu cầu khách hàng'
    )

    # CUSTOM THÊM MỚI
    # Lưu thông tin nhu cầu sản xuất và đơn hàng dự kiến của khách hàng
    product_category = fields.Char(
        string='Chủng loại sản phẩm'
    )

    design_sample = fields.Char(
        string='Mẫu thiết kế'
    )

    material_info = fields.Text(
        string='Thông tin nguyên vật liệu'
    )

    technical_requirement = fields.Text(
        string='Yêu cầu kỹ thuật'
    )

    expected_order_qty = fields.Float(
        string='Số lượng đặt hàng dự kiến'
    )

    delivery_terms = fields.Text(
        string='Điều kiện giao hàng'
    )

    # CUSTOM THÊM MỚI
    # Lưu hành động chăm sóc tiếp theo
    next_action = fields.Char(
        string='Hành động tiếp theo'
    )

    # CUSTOM THÊM MỚI
    # Lưu hạn chăm sóc tiếp theo của khách hàng
    followup_deadline = fields.Date(
        string='Hạn chăm sóc tiếp theo'
    )

    # KẾ THỪA MODULE MAIL
    # Model mail.activity
    #
    # CUSTOM THÊM MỚI
    # Liên kết activity follow-up để cập nhật lại task cũ, tránh tạo trùng
    followup_activity_id = fields.Many2one(
        'mail.activity',
        string='Hoạt động chăm sóc tiếp theo',
        readonly=True,
        copy=False
    )

    # KẾ THỪA MODULE CRM
    # Model crm.stage
    #
    # CUSTOM THÊM MỚI
    # Lưu trạng thái cơ hội đã kích hoạt quy trình CSKH tự động
    workflow_stage_id = fields.Many2one(
        'crm.stage',
        string='Trạng thái cơ hội tạo quy trình',
        readonly=True,
        copy=False
    )

    workflow_generated = fields.Boolean(
        string='Tự động từ quy trình',
        readonly=True,
        copy=False
    )

    workflow_email_sent = fields.Boolean(
        string='Đã gửi email quy trình',
        readonly=True,
        copy=False
    )

    # KẾ THỪA MODULE MAIL
    # Model mail.template
    #
    # CUSTOM THÊM MỚI
    # Lưu mẫu email được chọn từ quy tắc quy trình CSKH
    workflow_email_template_id = fields.Many2one(
        'mail.template',
        string='Mẫu email quy trình',
        readonly=True,
        copy=False,
        domain="[('model', '=', 'crm.cskh.profile')]"
    )

    # CUSTOM THÊM MỚI
    # Quản lý trạng thái Hồ sơ CSKH
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('pending', 'Cần chăm sóc tiếp'),
        ('done', 'Hoàn thành'),
        ('cancel', 'Hủy'),
    ], string='Trạng thái', default='draft', tracking=True)

    # CUSTOM THÊM MỚI
    # Kiểm tra Hồ sơ CSKH quá hạn chăm sóc tiếp theo
    is_overdue = fields.Boolean(
        string='Quá hạn',
        compute='_compute_is_overdue'
    )

    # CUSTOM THÊM MỚI
    # Theo dõi hạn cập nhật CRM trong vòng 24 giờ sau interaction
    crm_update_deadline = fields.Datetime(
        string='Hạn cập nhật CRM',
        compute='_compute_crm_update_status'
    )

    is_crm_update_late = fields.Boolean(
        string='Trễ cập nhật CRM',
        compute='_compute_crm_update_status'
    )

    # CUSTOM THÊM MỚI
    # Lưu thông tin email được đồng bộ từ Gmail/Incoming Mail Server
    gmail_message_id = fields.Char(
        string='Mã tin nhắn Gmail',
        copy=False,
        readonly=True,
        index=True
    )

    email_subject = fields.Char(
        string='Tiêu đề email',
        readonly=True
    )

    email_from = fields.Char(
        string='Email người gửi',
        readonly=True
    )

    email_date = fields.Datetime(
        string='Thời gian email',
        readonly=True
    )

    # CUSTOM THÊM MỚI
    # Lưu lịch sử thay đổi dữ liệu của Hồ sơ CSKH
    audit_log_ids = fields.One2many(
        'crm.cskh.audit.log',
        'profile_id',
        string='Lưu vết thay đổi',
        readonly=True
    )

    @api.depends('followup_deadline', 'state')
    def _compute_is_overdue(self):
        today = fields.Date.today()
        for record in self:
            record.is_overdue = (
                record.followup_deadline
                and record.followup_deadline < today
                and record.state not in ['done', 'cancel']
            )

    @api.depends('interaction_date', 'content', 'result', 'next_action', 'state')
    def _compute_crm_update_status(self):
        # CUSTOM THÊM MỚI
        # Kiểm tra Hồ sơ CSKH có bị trễ cập nhật sau 24 giờ hay không
        now = fields.Datetime.now()
        for record in self:
            if record.interaction_date:
                record.crm_update_deadline = (
                    record.interaction_date + timedelta(days=1)
                )
            else:
                record.crm_update_deadline = False

            record.is_crm_update_late = bool(
                record.crm_update_deadline
                and record.crm_update_deadline < now
                and record.state not in ['done', 'cancel']
                and (
                    not record.content
                    or not record.result
                    or not record.next_action
                )
            )

    @api.onchange('lead_id')
    def _onchange_lead_id(self):
        # KẾ THỪA MODULE CRM
        # Model crm.lead
        #
        # CUSTOM THÊM MỚI
        # Tự động lấy khách hàng và nhân viên phụ trách khi chọn khách hàng tiềm năng/cơ hội
        for record in self:
            if record.lead_id:
                record.customer_id = record.lead_id.partner_id
                record.user_id = record.lead_id.user_id or record.user_id

    @api.model_create_multi
    def create(self, vals_list):
        # CUSTOM THÊM MỚI
        # Sinh mã Hồ sơ CSKH bằng sequence
        for vals in vals_list:
            if vals.get('lead_id') and not vals.get('customer_id'):
                lead = self.env['crm.lead'].browse(vals['lead_id']).exists()
                if lead and lead.partner_id:
                    vals['customer_id'] = lead.partner_id.id

            if vals.get('customer_id') and not vals.get('lead_id'):
                partner = self.env['res.partner'].browse(
                    vals['customer_id']
                ).exists()
                if partner:
                    lead = self.env['crm.lead'].create({
                        'name': 'CSKH - %s' % partner.name,
                        'partner_id': partner.id,
                        'user_id': vals.get('user_id') or self.env.user.id,
                    })
                    vals['lead_id'] = lead.id

            if vals.get('name', 'Mới') in ['New', 'Mới']:
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'crm.cskh.profile'
                ) or 'Mới'

        records = super().create(vals_list)

        for record in records:
            record._create_followup_activity()
            record._create_audit_log('create', 'Tạo mới hồ sơ', '', record.name)
            record._notify_workflow_event()
            record._send_workflow_email()
            if record._has_cskh_summary_content():
                record._post_cskh_message()

        return records

    def write(self, vals):
        old_values = {}
        audit_fields = self._get_audit_field_names()
        previous_states = {}
        if 'state' in vals:
            previous_states = {record.id: record.state for record in self}
        if not self.env.context.get('skip_cskh_audit'):
            for record in self:
                old_values[record.id] = {
                    field_name: record[field_name]
                    for field_name in vals
                    if field_name in audit_fields
                }

        result = super(
            CrmCskhProfile,
            self.with_context(tracking_disable=True)
        ).write(vals)

        for record in self:
            if previous_states:
                record._post_state_change_message(previous_states.get(record.id))
                if record.state == 'done':
                    record._post_cskh_message()

            # CUSTOM THÊM MỚI
            # Tạo hoạt động khi cập nhật hành động tiếp theo hoặc hạn chăm sóc
            if 'followup_deadline' in vals or 'next_action' in vals:
                record._create_followup_activity()

            if not self.env.context.get('skip_cskh_audit'):
                record._create_write_audit_logs(vals, old_values.get(record.id, {}))

            if record._should_post_cskh_summary(vals):
                record._post_cskh_message()

        return result

    def _post_state_change_message(self, old_state):
        if not old_state or old_state == self.state:
            return

        selection = dict(self._fields['state'].selection)
        self.message_post(
            body=Markup('%s → %s <i>(%s)</i>') % (
                escape(selection.get(old_state, old_state)),
                escape(selection.get(self.state, self.state)),
                escape(_('Trạng thái')),
            )
        )

    def _get_audit_field_names(self):
        # CUSTOM THÊM MỚI
        # Danh sách trường cần lưu vết khi người dùng cập nhật Hồ sơ CSKH
        return {
            'lead_id',
            'user_id',
            'interaction_type',
            'interaction_date',
            'content',
            'result',
            'customer_need',
            'product_category',
            'design_sample',
            'material_info',
            'technical_requirement',
            'expected_order_qty',
            'delivery_terms',
            'next_action',
            'followup_deadline',
            'state',
            'email_subject',
            'email_from',
            'email_date',
            'workflow_stage_id',
            'workflow_generated',
            'workflow_email_sent',
        }

    def _create_write_audit_logs(self, vals, old_values):
        # CUSTOM THÊM MỚI
        # Tạo log thay đổi cho các trường dữ liệu quan trọng
        for field_name, old_value in old_values.items():
            new_value = self[field_name]
            old_text = self._audit_value_to_text(old_value)
            new_text = self._audit_value_to_text(new_value)
            if old_text == new_text:
                continue

            self._create_audit_log(
                'write',
                self._fields[field_name].string,
                old_text,
                new_text
            )

    def _create_audit_log(self, action, field_label, old_value, new_value):
        # CUSTOM THÊM MỚI
        # Ghi một dòng lưu vết thay đổi vào model crm.cskh.audit.log
        self.env['crm.cskh.audit.log'].sudo().create({
            'profile_id': self.id,
            'lead_id': self.lead_id.id,
            'user_id': self.env.user.id,
            'action': action,
            'field_name': field_label,
            'old_value': old_value,
            'new_value': new_value,
        })

    def _audit_value_to_text(self, value):
        if not value:
            return ''
        if hasattr(value, 'display_name'):
            return value.display_name
        return str(value)

    def _notify_workflow_event(self):
        # KẾ THỪA MODULE MAIL
        # message_post của mail.thread
        #
        # CUSTOM THÊM MỚI
        # Gửi thông báo lên chatter khi quy trình tự động tạo chăm sóc tiếp theo
        for record in self:
            if not record.workflow_generated:
                continue

            body = Markup(
                '%s<br/><b>%s</b> %s<br/><b>%s</b> %s'
            ) % (
                escape(_('Hệ thống đã tạo chăm sóc tiếp theo tự động theo quy trình CRM.')),
                escape(_('Hành động tiếp theo:')),
                escape(record.next_action or ''),
                escape(_('Hạn chăm sóc tiếp theo:')),
                escape(record.followup_deadline or ''),
            )
            record.message_post(body=body)
            if record.lead_id:
                record.lead_id.message_post(body=body)

    def _send_workflow_email(self):
        # KẾ THỪA MODULE MAIL
        # Model mail.template
        #
        # CUSTOM THÊM MỚI
        # Tự động gửi email theo mẫu được cấu hình trong quy trình
        for record in self:
            if record.workflow_email_sent or not record.workflow_generated:
                continue
            if not record.customer_id.email:
                continue

            template = record.workflow_email_template_id or self.env.ref(
                'Ho_So_CSKH.email_template_workflow_followup',
                raise_if_not_found=False
            )
            if not template:
                continue

            template.send_mail(record.id, force_send=True)
            record.with_context(skip_cskh_audit=True).workflow_email_sent = True

    def _create_followup_activity(self):
        # KẾ THỪA MODULE MAIL
        # Model mail.activity
        #
        # CUSTOM THÊM MỚI
        # Tạo nhắc việc chăm sóc tiếp theo cho nhân viên phụ trách
        for record in self:
            if not record.followup_deadline or not record.next_action:
                continue

            activity_vals = {
                'activity_type_id': self.env.ref(
                    'mail.mail_activity_data_todo'
                ).id,
                'summary': 'Chăm sóc tiếp Hồ sơ CSKH',
                'note': record.next_action,
                'date_deadline': record.followup_deadline,
                'user_id': record.user_id.id,
                'res_model_id': self.env['ir.model']._get_id(
                    'crm.cskh.profile'
                ),
                'res_id': record.id,
            }

            activity = record.followup_activity_id.exists()
            if not activity:
                activity = self.env['mail.activity'].search([
                    ('res_model', '=', 'crm.cskh.profile'),
                    ('res_id', '=', record.id),
                    ('activity_type_id', '=', activity_vals['activity_type_id']),
                    ('summary', '=', activity_vals['summary']),
                ], limit=1)

            if activity:
                activity.write(activity_vals)
            else:
                activity = self.env['mail.activity'].create(activity_vals)

            record.followup_activity_id = activity.id

            record.state = 'pending'

    def _cron_sync_gmail_messages(self):
        # CUSTOM THÊM MỚI
        # Đồng bộ email đã được Gmail/Incoming Mail Server đưa vào chatter
        # thành lịch sử tương tác CSKH tập trung.
        messages = self.env['mail.message'].search([
            ('message_type', '=', 'email'),
            ('model', 'in', ['crm.lead', False]),
        ], order='date desc', limit=200)

        for message in messages:
            gmail_message_id = message.message_id or 'mail.message,%s' % message.id
            if self.search_count([('gmail_message_id', '=', gmail_message_id)]):
                continue

            lead = self._find_lead_from_email_message(message)
            if not lead:
                continue

            self.create({
                'lead_id': lead.id,
                'user_id': lead.user_id.id or self.env.user.id,
                'interaction_type': 'email',
                'interaction_date': message.date or fields.Datetime.now(),
                'content': html2plaintext(message.body or '').strip()
                           or message.subject
                           or _('Email được đồng bộ từ Gmail'),
                'result': _('Email đã được đồng bộ tự động vào CRM.'),
                'gmail_message_id': gmail_message_id,
                'email_subject': message.subject,
                'email_from': message.email_from,
                'email_date': message.date,
            })

    def _find_lead_from_email_message(self, message):
        Lead = self.env['crm.lead']

        if message.model == 'crm.lead' and message.res_id:
            lead = Lead.browse(message.res_id).exists()
            if lead:
                return lead

        emails = email_split(message.email_from or '')
        for email in emails:
            lead = Lead.search([
                '|',
                ('email_from', 'ilike', email),
                ('partner_id.email', 'ilike', email),
            ], order='write_date desc', limit=1)
            if lead:
                return lead

        return Lead.browse()

    def _cskh_refresh_existing_summary_messages(self, *args):
        records = self.search([])
        for record in records:
            if record._has_cskh_summary_content():
                record._post_cskh_message()
        return True

    def _post_cskh_message(self):
        # Ghi một bản tóm tắt dễ đọc vào chatter, bỏ qua các dòng trống.
        for record in self:
            lines = record._get_cskh_summary_lines()
            if not lines:
                continue

            body = Markup(
                '<span data-cskh-summary="%s"></span>%s<br/>%s'
            ) % (
                escape(record.id),
                escape(_('Đã cập nhật Hồ sơ CSKH.')),
                Markup('<br/>').join(lines),
            )

            summary_message = record._get_cskh_summary_message()
            if summary_message:
                summary_message.sudo().write({'body': body})
            else:
                summary_message = record.message_post(body=body)
                record.with_context(
                    skip_cskh_audit=True,
                    tracking_disable=True,
                ).write({
                    'cskh_summary_message_id': summary_message.id,
                    'cskh_summary_posted': True,
                })

                if record.lead_id:
                    record.lead_id.message_post(
                        body=Markup('%s <b>%s</b>') % (
                            escape(_('Đã cập nhật Hồ sơ CSKH:')),
                            escape(record.name or ''),
                        )
                    )

            record._remove_duplicate_cskh_summary_messages(summary_message)

    def _get_cskh_summary_message(self):
        self.ensure_one()
        if self.cskh_summary_message_id.exists():
            return self.cskh_summary_message_id

        marker = 'data-cskh-summary="%s"' % self.id
        return self.env['mail.message'].sudo().search([
            ('model', '=', self._name),
            ('res_id', '=', self.id),
            ('body', 'ilike', marker),
        ], order='id desc', limit=1)

    def _remove_duplicate_cskh_summary_messages(self, keep_message):
        self.ensure_one()
        if not keep_message:
            return

        duplicate_messages = self.env['mail.message'].sudo().search([
            ('model', '=', self._name),
            ('res_id', '=', self.id),
            ('id', '!=', keep_message.id),
            ('body', 'ilike', 'Đã cập nhật Hồ sơ CSKH.'),
        ])
        duplicate_messages.unlink()

    def _should_post_cskh_summary(self, vals):
        if not self._get_cskh_summary_field_names().intersection(vals):
            return False

        return self._has_cskh_summary_content()

    def _get_cskh_summary_field_names(self):
        return {
            'lead_id',
            'customer_id',
            'interaction_type',
            'interaction_date',
            'content',
            'result',
            'customer_need',
            'product_category',
            'design_sample',
            'material_info',
            'technical_requirement',
            'expected_order_qty',
            'delivery_terms',
            'next_action',
            'followup_deadline',
        }

    def _has_cskh_summary_content(self):
        return bool(
            self.interaction_type
            and (
                self.content
                or self.result
                or self.customer_need
                or self.product_category
                or self.next_action
                or self.followup_deadline
            )
        )

    def _get_cskh_summary_lines(self):
        lines = []
        if self.lead_id:
            lines.append(
                Markup('<b>%s</b> %s') % (
                    escape(_('Cơ hội:')),
                    escape(self.lead_id.display_name),
                )
            )
        if self.customer_id:
            lines.append(
                Markup('<b>%s</b> %s') % (
                    escape(_('Khách hàng:')),
                    escape(self.customer_id.display_name),
                )
            )
        interaction_label = self._get_interaction_type_label()
        if interaction_label:
            lines.append(
                Markup('<b>%s</b> %s') % (
                    escape(_('Loại tương tác:')),
                    escape(interaction_label),
                )
            )
        if self.content:
            lines.append(
                Markup('<b>%s</b> %s') % (
                    escape(_('Nội dung:')),
                    escape(self.content),
                )
            )
        if self.result:
            lines.append(
                Markup('<b>%s</b> %s') % (
                    escape(_('Kết quả làm việc:')),
                    escape(self.result),
                )
            )
        if self.customer_need:
            lines.append(
                Markup('<b>%s</b> %s') % (
                    escape(_('Nhu cầu khách hàng:')),
                    escape(self.customer_need),
                )
            )
        if self.product_category:
            lines.append(
                Markup('<b>%s</b> %s') % (
                    escape(_('Chủng loại sản phẩm:')),
                    escape(self.product_category),
                )
            )
        if self.expected_order_qty:
            lines.append(
                Markup('<b>%s</b> %s') % (
                    escape(_('Số lượng đặt hàng dự kiến:')),
                    escape(self.expected_order_qty),
                )
            )
        if self.delivery_terms:
            lines.append(
                Markup('<b>%s</b> %s') % (
                    escape(_('Điều kiện giao hàng:')),
                    escape(self.delivery_terms),
                )
            )
        if self.next_action:
            lines.append(
                Markup('<b>%s</b> %s') % (
                    escape(_('Hành động tiếp theo:')),
                    escape(self.next_action),
                )
            )
        if self.followup_deadline:
            lines.append(
                Markup('<b>%s</b> %s') % (
                    escape(_('Hạn chăm sóc tiếp theo:')),
                    escape(self.followup_deadline),
                )
            )
        return lines

    def _get_interaction_type_label(self):
        labels = {
            'email': _('Email'),
            'call': _('Cuộc gọi'),
            'meeting': _('Cuộc họp'),
            'quotation': _('Báo giá'),
            'complaint': _('Khiếu nại'),
            'note': _('Ghi chú trao đổi'),
        }
        if self.interaction_type in labels:
            return labels[self.interaction_type]

        selection = dict(self._fields['interaction_type'].selection)
        return selection.get(self.interaction_type, self.interaction_type or '')

    def action_done(self):
        # CUSTOM THÊM MỚI
        # Button chuyển Hồ sơ CSKH sang trạng thái Hoàn thành
        for record in self:
            record.state = 'done'

    def action_cancel(self):
        # CUSTOM THÊM MỚI
        # Button chuyển Hồ sơ CSKH sang trạng thái Hủy
        for record in self:
            record.state = 'cancel'

    def _cron_crm_update_reminder(self):
        # CUSTOM THÊM MỚI
        # Cron job nhắc cập nhật Hồ sơ CSKH quá hạn
        today = fields.Date.today()

        records = self.search([
            ('followup_deadline', '<', today),
            ('state', 'not in', ['done', 'cancel']),
        ])

        for record in records:
            record.message_post(
                body='Hồ sơ CSKH đã quá hạn chăm sóc tiếp theo. Nhân viên phụ trách cần cập nhật kết quả chăm sóc khách hàng.'
            )

            self.env['mail.activity'].create({
                'activity_type_id': self.env.ref(
                    'mail.mail_activity_data_todo'
                ).id,
                'summary': 'Nhắc cập nhật Hồ sơ CSKH',
                'note': 'Vui lòng cập nhật chăm sóc tiếp theo cho khách hàng.',
                'date_deadline': today,
                'user_id': record.user_id.id,
                'res_model_id': self.env['ir.model']._get_id(
                    'crm.cskh.profile'
                ),
                'res_id': record.id,
            })

    def _cron_crm_24h_update_reminder(self):
        # CUSTOM THÊM MỚI
        # Cron job nhắc Sales cập nhật CRM trong vòng 24 giờ sau interaction
        deadline = fields.Datetime.now() - timedelta(days=1)
        records = self.search([
            ('interaction_date', '<', deadline),
            ('state', 'not in', ['done', 'cancel']),
            '|',
            '|',
            ('content', '=', False),
            ('result', '=', False),
            ('next_action', '=', False),
        ])

        activity_type = self.env.ref('mail.mail_activity_data_todo')
        for record in records:
            summary = 'Nhắc cập nhật CRM trong 24 giờ'
            activity_vals = {
                'activity_type_id': activity_type.id,
                'summary': summary,
                'note': 'Vui lòng cập nhật đầy đủ nội dung trao đổi, kết quả làm việc và hành động tiếp theo.',
                'date_deadline': fields.Date.today(),
                'user_id': record.user_id.id,
                'res_model_id': self.env['ir.model']._get_id(
                    'crm.cskh.profile'
                ),
                'res_id': record.id,
            }

            activity = self.env['mail.activity'].search([
                ('res_model', '=', 'crm.cskh.profile'),
                ('res_id', '=', record.id),
                ('activity_type_id', '=', activity_type.id),
                ('summary', '=', summary),
            ], limit=1)

            if activity:
                activity.write(activity_vals)
            else:
                self.env['mail.activity'].create(activity_vals)

            record.message_post(
                body=_(
                    'Hồ sơ CSKH chưa được cập nhật đầy đủ trong vòng 24 giờ sau interaction.'
                )
            )


class CrmCskhAuditLog(models.Model):
    # CUSTOM THÊM MỚI
    # Model lưu vết thay đổi dữ liệu Hồ sơ CSKH
    _name = 'crm.cskh.audit.log'
    _description = 'Lưu vết thay đổi Hồ sơ CSKH'
    _order = 'create_date desc, id desc'

    profile_id = fields.Many2one(
        'crm.cskh.profile',
        string='Hồ sơ CSKH',
        required=True,
        ondelete='cascade'
    )

    lead_id = fields.Many2one(
        'crm.lead',
        string='Cơ hội',
        readonly=True
    )

    user_id = fields.Many2one(
        'res.users',
        string='Người thay đổi',
        readonly=True
    )

    action = fields.Selection([
        ('create', 'Tạo mới'),
        ('write', 'Cập nhật'),
    ], string='Hành động', readonly=True)

    field_name = fields.Char(
        string='Trường dữ liệu',
        readonly=True
    )

    old_value = fields.Text(
        string='Giá trị cũ',
        readonly=True
    )

    new_value = fields.Text(
        string='Giá trị mới',
        readonly=True
    )
