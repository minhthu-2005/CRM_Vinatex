from datetime import timedelta

from odoo import models, fields, api, _


class CrmLead(models.Model):
    # KẾ THỪA MODULE CRM
    # Model crm.lead
    _inherit = 'crm.lead'

    # CUSTOM THÊM MỚI
    # Lưu danh sách Hồ sơ CSKH của khách hàng tiềm năng/cơ hội
    cskh_profile_ids = fields.One2many(
        'crm.cskh.profile',
        'lead_id',
        string='Hồ sơ CSKH'
    )

    # CUSTOM THÊM MỚI
    # Đếm số lượng Hồ sơ CSKH của khách hàng tiềm năng/cơ hội
    cskh_profile_count = fields.Integer(
        string='Số hồ sơ CSKH',
        compute='_compute_cskh_profile_count'
    )

    initial_product_requirement = fields.Text(string='Initial product requirement')
    last_interaction_date = fields.Date(
        string='Last interaction date',
        default=fields.Date.context_today,
    )
    inactive_archive_date = fields.Date(
        string='Inactive archive date',
        readonly=True,
        copy=False,
    )
    archived_by_cron = fields.Boolean(
        string='Archived by cron',
        readonly=True,
        copy=False,
    )
    duplicate_state = fields.Selection(
        [
            ('clean', 'Clean'),
            ('similar', 'Similar'),
            ('exact', 'Exact duplicate'),
        ],
        string='Duplicate state',
        default='clean',
    )
    duplicate_lead_ids = fields.Many2many(
        'crm.lead',
        'crm_lead_duplicate_rel',
        'lead_id',
        'duplicate_id',
        string='Potential duplicate leads',
    )
    duplicate_count = fields.Integer(
        string='Potential duplicate count',
        compute='_compute_duplicate_count',
    )
    data_quality_state = fields.Selection(
        [
            ('valid', 'Valid'),
            ('missing', 'Missing data'),
            ('invalid', 'Invalid data'),
        ],
        string='Data quality state',
        default='valid',
    )
    missing_required_fields = fields.Char(string='Missing required fields')

    def _compute_cskh_profile_count(self):
        for lead in self:
            lead.cskh_profile_count = len(lead.cskh_profile_ids)

    def _compute_duplicate_count(self):
        for lead in self:
            lead.duplicate_count = len(lead.duplicate_lead_ids)

    def action_open_duplicate_leads(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Potential duplicates'),
            'res_model': 'crm.lead',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.duplicate_lead_ids.ids)],
            'context': dict(self.env.context, active_test=False),
        }

    def action_open_transfer_owner_wizard(self):
        return False

    def action_mark_interaction_today(self):
        self.write({'last_interaction_date': fields.Date.context_today(self)})
        return True

    @api.model
    def _cskh_cleanup_demo_opportunity_names(self, *args):
        leads = self.search([('name', 'ilike', 'Demo - %')])
        for lead in leads:
            name = (lead.name or '').strip()
            if name.lower().startswith('demo - '):
                lead.with_context(skip_cskh_auto_profile=True).write({
                    'name': name[7:].strip(),
                })
        return True

    def action_request_merge_approval(self):
        return False

    def action_request_delete_approval(self):
        return False

    @api.model_create_multi
    def create(self, vals_list):
        # KẾ THỪA MODULE CRM
        # create của model crm.lead
        #
        # CUSTOM THÊM MỚI
        # Tự động tạo quy trình chăm sóc tiếp khi tạo khách hàng tiềm năng mới
        leads = super().create(vals_list)
        if not self.env.context.get('skip_cskh_auto_profile'):
            leads._create_stage_followup_profile()
        return leads

    def write(self, vals):
        # KẾ THỪA MODULE CRM
        # write của model crm.lead
        #
        # CUSTOM THÊM MỚI
        # Tự động tạo quy trình chăm sóc tiếp khi cơ hội đổi trạng thái
        result = super().write(vals)
        if 'stage_id' in vals and not self.env.context.get('skip_cskh_auto_profile'):
            self._create_stage_followup_profile()
        return result

    def _create_stage_followup_profile(self):
        # CUSTOM THÊM MỚI
        # Tạo hoặc cập nhật Hồ sơ CSKH chăm sóc tiếp dựa trên trạng thái cơ hội
        CskhProfile = self.env['crm.cskh.profile']

        for lead in self:
            plan = lead._get_stage_followup_plan()
            if not plan:
                continue

            existing_profile = CskhProfile.search([
                ('lead_id', '=', lead.id),
                ('workflow_generated', '=', True),
                ('workflow_stage_id', '=', lead.stage_id.id),
                ('state', 'not in', ['done', 'cancel']),
            ], limit=1)

            vals = {
                'lead_id': lead.id,
                'user_id': lead.user_id.id or self.env.user.id,
                'interaction_type': 'note',
                'interaction_date': fields.Datetime.now(),
                'content': plan['content'],
                'result': _('Hệ thống tự động tạo chăm sóc tiếp theo trạng thái cơ hội.'),
                'next_action': plan['next_action'],
                'followup_deadline': fields.Date.today()
                                     + timedelta(days=plan['days']),
                'workflow_stage_id': lead.stage_id.id,
                'workflow_generated': True,
                'workflow_email_template_id': plan.get('email_template_id'),
            }

            if existing_profile:
                existing_profile.write({
                    'next_action': vals['next_action'],
                    'followup_deadline': vals['followup_deadline'],
                    'content': vals['content'],
                    'result': vals['result'],
                    'user_id': vals['user_id'],
                    'workflow_email_template_id': vals['workflow_email_template_id'],
                })
            else:
                CskhProfile.create(vals)

    def _get_stage_followup_plan(self):
        # CUSTOM THÊM MỚI
        # Lấy kế hoạch chăm sóc tiếp từ quy tắc quy trình CSKH hoặc quy tắc mặc định
        self.ensure_one()
        if not self.stage_id:
            return False

        rule = self.env['crm.cskh.workflow.rule'].search([
            ('stage_id', '=', self.stage_id.id),
            ('active', '=', True),
        ], limit=1)
        if rule:
            return {
                'days': rule.followup_days,
                'next_action': rule.next_action,
                'content': rule.content,
                'email_template_id': (
                    rule.email_template_id.id
                    if rule.send_email and rule.email_template_id
                    else False
                ),
            }

        stage_name = (self.stage_id.name or '').strip()
        normalized_stage = stage_name.lower()

        if any(keyword in normalized_stage for keyword in [
            'lost', 'mất', 'hủy', 'huỷ', 'thất bại'
        ]):
            return False

        if any(keyword in normalized_stage for keyword in [
            'won', 'thắng', 'thành công'
        ]) or self.probability == 100:
            return {
                'days': 7,
                'next_action': _('Chăm sóc sau bán và xác nhận mức độ hài lòng.'),
                'content': _('Cơ hội chuyển sang trạng thái %s.') % stage_name,
            }

        if any(keyword in normalized_stage for keyword in [
            'qualified', 'đủ điều kiện', 'tiềm năng', 'qualify'
        ]):
            return {
                'days': 2,
                'next_action': _('Liên hệ xác nhận nhu cầu và bước tiếp theo.'),
                'content': _('Cơ hội cần được chăm sóc tiếp sau khi đủ điều kiện.'),
            }

        if any(keyword in normalized_stage for keyword in [
            'proposal', 'proposition', 'quotation', 'báo giá', 'đề xuất'
        ]):
            return {
                'days': 3,
                'next_action': _('Theo dõi phản hồi báo giá/đề xuất từ khách hàng.'),
                'content': _('Cơ hội đang ở giai đoạn báo giá/đề xuất.'),
            }

        return {
            'days': 1,
            'next_action': _('Liên hệ khách hàng để cập nhật tình trạng quan tâm.'),
            'content': _('Cơ hội chuyển sang trạng thái %s.') % stage_name,
        }
