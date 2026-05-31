from odoo import models, fields

class CrmSalesPerformance(models.Model):
    _name = 'crm.sales.performance'
    _description = 'Phân tích hiệu suất kinh doanh'
    _auto = False
    _table = 'crm_sales_performance_report'
    _order = 'total_revenue desc'

    salesperson_id = fields.Many2one('res.users', string='Nhân viên kinh doanh', readonly=True)
    total_leads = fields.Integer(string='Tổng Lead', readonly=True)
    won_leads = fields.Integer(string='Lead thành công', readonly=True)
    lost_leads = fields.Integer(string='Lead thất bại', readonly=True)
    total_revenue = fields.Float(string='Tổng doanh thu', readonly=True)
    conversion_rate = fields.Float(string='Tỷ lệ chuyển đổi (%)', readonly=True)

    def init(self):
        self.env.cr.execute("""DO $$ BEGIN
IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE c.relname='crm_sales_performance_report' AND n.nspname='public' AND c.relkind IN ('v','m')) THEN
    EXECUTE 'DROP VIEW IF EXISTS crm_sales_performance_report CASCADE';
ELSIF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE c.relname='crm_sales_performance_report' AND n.nspname='public' AND c.relkind='r') THEN
    EXECUTE 'DROP TABLE IF EXISTS crm_sales_performance_report CASCADE';
END IF;
END $$;""")
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW crm_sales_performance_report AS (
                SELECT MIN(l.id) AS id, l.user_id AS salesperson_id,
                       COUNT(l.id) AS total_leads,
                       COUNT(CASE WHEN COALESCE(s.is_won,false)=true OR l.probability >= 100 THEN 1 END) AS won_leads,
                       COUNT(CASE WHEN l.probability = 0 THEN 1 END) AS lost_leads,
                       COALESCE(SUM(l.expected_revenue),0) AS total_revenue,
                       CASE WHEN COUNT(l.id)=0 THEN 0 ELSE ROUND((COUNT(CASE WHEN COALESCE(s.is_won,false)=true OR l.probability >= 100 THEN 1 END)::numeric / COUNT(l.id)::numeric)*100,2) END AS conversion_rate
                FROM crm_lead l
                LEFT JOIN crm_stage s ON l.stage_id = s.id
                WHERE l.type = 'opportunity'
                GROUP BY l.user_id
            )
        """)
