from odoo import fields, models

class CrmLostReasonAnalytics(models.Model):
    _name = 'crm.lost.reason.analytics'
    _description = 'Theo dõi cơ hội thất bại'
    _order = 'lost_date desc'

    lead_id = fields.Many2one('crm.lead', string='Lead')
    lead_name = fields.Char(string='Tên Lead')
    lost_reason_id = fields.Many2one('crm.lost.reason', string='Lý do thất bại')
    user_id = fields.Many2one('res.users', string='Nhân viên kinh doanh')
    expected_revenue = fields.Float(string='Doanh thu kỳ vọng')
    lost_date = fields.Datetime(string='Ngày thất bại')

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    def action_set_lost(self, **additional_values):
        result = super().action_set_lost(**additional_values)
        for lead in self:
            existing = self.env['crm.lost.reason.analytics'].search([('lead_id', '=', lead.id)], limit=1)
            if not existing:
                self.env['crm.lost.reason.analytics'].create({
                    'lead_id': lead.id,
                    'lead_name': lead.name,
                    'lost_reason_id': lead.lost_reason_id.id,
                    'user_id': lead.user_id.id,
                    'expected_revenue': lead.expected_revenue,
                    'lost_date': fields.Datetime.now(),
                })
        return result
