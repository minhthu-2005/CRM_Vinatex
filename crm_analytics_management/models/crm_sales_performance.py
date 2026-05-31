from odoo import models, fields, tools


class CrmSalesPerformance(models.Model):
    _name = 'crm.sales.performance'
    _description = 'Phân tích hiệu suất Sales'
    _auto = False
    _table = 'crm_sales_performance_report'
    _order = 'total_revenue desc'

    salesperson_id = fields.Many2one(
        'res.users',
        string='Nhân viên Sales',
        readonly=True
    )

    total_leads = fields.Integer(
        string='Tổng Lead',
        readonly=True
    )

    won_leads = fields.Integer(
        string='Lead thành công',
        readonly=True
    )

    lost_leads = fields.Integer(
        string='Lead thất bại',
        readonly=True
    )

    total_revenue = fields.Float(
        string='Tổng doanh thu',
        readonly=True
    )

    conversion_rate = fields.Float(
        string='Tỷ lệ chuyển đổi (%)',
        readonly=True,
        group_operator='avg'
    )

    def init(self):

        tools.drop_view_if_exists(
            self.env.cr,
            self._table
        )

        self.env.cr.execute("""

            CREATE OR REPLACE VIEW crm_sales_performance_report AS (

                SELECT

                    MIN(l.id) AS id,

                    l.user_id AS salesperson_id,

                    COUNT(l.id) AS total_leads,

                    COUNT(
                        CASE
                            WHEN COALESCE(s.is_won, false) = true
                                 OR l.probability >= 100
                            THEN 1
                        END
                    ) AS won_leads,

                    COUNT(
                        CASE
                            WHEN l.active = false
                                 AND l.lost_reason_id IS NOT NULL
                            THEN 1
                        END
                    ) AS lost_leads,

                    COALESCE(
                        SUM(l.expected_revenue),
                        0
                    ) AS total_revenue,

                    CASE
                        WHEN COUNT(l.id) = 0
                        THEN 0

                        ELSE ROUND(

                            (
                                COUNT(
                                    CASE
                                        WHEN COALESCE(s.is_won, false) = true
                                             OR l.probability >= 100
                                        THEN 1
                                    END
                                )::numeric

                                / COUNT(l.id)::numeric

                            ) * 100,

                            2
                        )
                    END AS conversion_rate

                FROM crm_lead l

                LEFT JOIN crm_stage s
                    ON l.stage_id = s.id

                WHERE l.type = 'opportunity'
                      AND l.user_id IS NOT NULL

                GROUP BY l.user_id

            )

        """)
