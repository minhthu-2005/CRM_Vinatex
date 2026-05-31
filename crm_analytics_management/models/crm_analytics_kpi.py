from odoo import models, fields

class CrmAnalyticsKpi(models.Model):
    _name = 'crm.analytics.kpi'
    _description = 'Dashboard KPI CRM'
    _auto = False
    _table = 'crm_dashboard_kpi_report'
    _order = 'expected_revenue desc'

    lead_id = fields.Many2one('crm.lead', string='Lead', readonly=True)
    lead_name = fields.Char(string='Tên Lead', readonly=True)
    stage_id = fields.Many2one('crm.stage', string='Giai đoạn', readonly=True)
    salesperson_id = fields.Many2one('res.users', string='Nhân viên Sales', readonly=True)
    expected_revenue = fields.Float(string='Doanh thu kỳ vọng', readonly=True)
    probability = fields.Float(string='Xác suất', readonly=True)
    lead_count = fields.Integer(string='Tổng Lead', readonly=True)
    event_type = fields.Char(string='Loại dữ liệu', readonly=True)

    def init(self):
        self.env.cr.execute("""DO $$ BEGIN
IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE c.relname='crm_dashboard_kpi_report' AND n.nspname='public' AND c.relkind IN ('v','m')) THEN
    EXECUTE 'DROP VIEW IF EXISTS crm_dashboard_kpi_report CASCADE';
ELSIF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE c.relname='crm_dashboard_kpi_report' AND n.nspname='public' AND c.relkind='r') THEN
    EXECUTE 'DROP TABLE IF EXISTS crm_dashboard_kpi_report CASCADE';
END IF;
END $$;""")
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW crm_dashboard_kpi_report AS (
                SELECT l.id AS id, l.id AS lead_id, l.name AS lead_name,
                       l.stage_id AS stage_id, l.user_id AS salesperson_id,
                       COALESCE(l.expected_revenue, 0) AS expected_revenue,
                       COALESCE(l.probability, 0) AS probability,
                       1 AS lead_count, 'CRM Lead' AS event_type
                FROM crm_lead l
                WHERE l.type = 'opportunity'
            )
        """)
