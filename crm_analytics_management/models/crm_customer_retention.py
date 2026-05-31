from odoo import models, fields, api


class CrmCustomerRetentionAnalytics(models.Model):
    _name = 'crm.customer.retention.analytics'
    _description = 'Phân tích khách hàng quay lại'
    _order = 'retention_rate desc, total_revenue desc'

    customer_id = fields.Many2one('res.partner', string='Khách hàng')
    total_orders = fields.Integer(string='Tổng đơn hàng', default=0)
    total_revenue = fields.Float(string='Tổng doanh thu', default=0)
    is_returning_customer = fields.Boolean(string='Khách hàng quay lại')
    retention_status = fields.Char(string='Trạng thái quay lại')

    retention_rate = fields.Float(
        string='Tỷ lệ mua lại (%)',
        group_operator='avg'
    )

    @api.model
    def generate_retention_analytics(self):
        self.search([]).unlink()

        orders = self.env['sale.order'].search([
            ('state', '=', 'sale'),
            ('partner_id', '!=', False)
        ])

        customers = orders.mapped('partner_id')

        for customer in customers:
            sale_orders = orders.filtered(
                lambda order: order.partner_id.id == customer.id
            )

            total_orders = len(sale_orders)
            total_revenue = sum(sale_orders.mapped('amount_total'))
            is_returning = total_orders >= 2

            retention_rate = (
                ((total_orders - 1) / total_orders) * 100
                if total_orders > 1
                else 0.0
            )

            self.create({
                'customer_id': customer.id,
                'total_orders': total_orders,
                'total_revenue': total_revenue,
                'is_returning_customer': is_returning,
                'retention_status': (
                    'Returning Customer'
                    if is_returning
                    else 'New Customer'
                ),
                'retention_rate': round(retention_rate, 2),
            })

        return True