from collections import defaultdict

from odoo import models, fields, api

class CrmCustomerRetentionAnalytics(models.Model):
    _name = 'crm.customer.retention.analytics'
    _description = 'Phân tích khách hàng quay lại'
    _order = 'retention_rate desc, total_revenue desc'

    customer_id = fields.Many2one('res.partner', string='Khách hàng', index=True)
    total_orders = fields.Integer(string='Tổng đơn hàng', default=0)
    total_revenue = fields.Float(string='Tổng doanh thu', default=0)
    is_returning_customer = fields.Boolean(string='Khách hàng quay lại')
    retention_status = fields.Char(string='Trạng thái quay lại')
    retention_rate = fields.Float(
        string='Tỷ lệ quay lại (%)',
        group_operator='avg',
    )

    @api.model
    def _get_retention_status(self, total_orders, partner=False):
        if total_orders >= 3:
            return 'Khách hàng thân thiết'
        if total_orders == 2:
            return 'Khách hàng quay lại'
        if partner and partner.retention_segment == 'dormant':
            return 'Lâu chưa tương tác'
        if partner and partner.retention_segment == 'at_risk':
            return 'Có nguy cơ rời bỏ'
        if partner and partner.retention_segment == 'loyal':
            return 'Khách hàng thân thiết'
        if partner and partner.retention_segment == 'active':
            return 'Đang chăm sóc'
        return 'Khách hàng mới'

    @api.model
    def _get_retention_rate(self, total_orders):
        if total_orders <= 1:
            return 0.0
        return round(((total_orders - 1) / total_orders) * 100, 2)

    @api.model
    def generate_retention_analytics(self):
        self.search([]).unlink()

        partner_values = defaultdict(lambda: {
            'total_orders': 0,
            'total_revenue': 0.0,
        })

        orders = self.env['sale.order'].search([('state', 'in', ('sale', 'done'))])
        for order in orders:
            customer = order.partner_id.commercial_partner_id or order.partner_id
            if not customer:
                continue
            partner_values[customer.id]['total_orders'] += 1
            partner_values[customer.id]['total_revenue'] += order.amount_total

        crm_partners = self.env['crm.lead'].search([
            ('partner_id', '!=', False),
            ('type', '=', 'opportunity'),
        ]).mapped('partner_id')
        for partner in crm_partners:
            customer = partner.commercial_partner_id or partner
            values = partner_values[customer.id]
            if not values['total_revenue']:
                values['total_revenue'] = customer.crm_estimated_revenue or sum(
                    self.env['crm.lead'].search([
                        ('partner_id', 'child_of', customer.id),
                        ('type', '=', 'opportunity'),
                    ]).mapped('expected_revenue')
                )
            if not values['total_orders']:
                values['total_orders'] = self.env['crm.lead'].search_count([
                    ('partner_id', 'child_of', customer.id),
                    ('type', '=', 'opportunity'),
                    '|',
                    ('probability', '>=', 100),
                    ('stage_id.is_won', '=', True),
                ]) or 1

        for partner_id, values in partner_values.items():
            customer = self.env['res.partner'].browse(partner_id).exists()
            if not customer:
                continue
            total_orders = values['total_orders']
            total_revenue = values['total_revenue']
            retention_rate = self._get_retention_rate(total_orders)
            is_returning = total_orders >= 2
            self.create({
                'customer_id': customer.id,
                'total_orders': total_orders,
                'total_revenue': total_revenue,
                'is_returning_customer': is_returning,
                'retention_status': self._get_retention_status(total_orders, customer),
                'retention_rate': retention_rate,
            })
        return True
