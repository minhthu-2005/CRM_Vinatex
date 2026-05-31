from odoo import models, fields


class CrmCskhWorkflowRule(models.Model):
    # CUSTOM THÊM MỚI
    # Model cấu hình quy tắc quy trình CSKH theo từng trạng thái cơ hội
    _name = 'crm.cskh.workflow.rule'
    _description = 'Quy tắc quy trình CSKH theo trạng thái cơ hội'
    _order = 'sequence, id'

    name = fields.Char(
        string='Tên quy tắc',
        required=True
    )

    sequence = fields.Integer(
        string='Thứ tự',
        default=10
    )

    active = fields.Boolean(
        string='Đang áp dụng',
        default=True
    )

    # KẾ THỪA MODULE CRM
    # Model crm.stage
    #
    # CUSTOM THÊM MỚI
    # Chọn trạng thái cơ hội sẽ áp dụng quy tắc quy trình CSKH
    stage_id = fields.Many2one(
        'crm.stage',
        string='Trạng thái cơ hội',
        required=True,
        ondelete='cascade'
    )

    followup_days = fields.Integer(
        string='Số ngày chăm sóc tiếp',
        default=1,
        required=True
    )

    next_action = fields.Char(
        string='Hành động tiếp theo',
        required=True
    )

    content = fields.Text(
        string='Nội dung quy trình',
        required=True
    )

    send_email = fields.Boolean(
        string='Tự động gửi email',
        default=True
    )

    # KẾ THỪA MODULE MAIL
    # Model mail.template
    #
    # CUSTOM THÊM MỚI
    # Chọn mẫu email gửi tự động khi quy trình được kích hoạt
    email_template_id = fields.Many2one(
        'mail.template',
        string='Mẫu email',
        domain="[('model', '=', 'crm.cskh.profile')]"
    )
