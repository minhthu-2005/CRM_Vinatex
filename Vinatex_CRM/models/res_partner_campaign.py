# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    segment = fields.Selection(
        [
            ("high", "Khách hàng giá trị cao"),
            ("medium", "Khách hàng giá trị trung bình"),
            ("low", "Khách hàng giá trị thấp"),
            ("dormant", "Khách hàng lâu chưa tương tác"),
        ],
        string="Nhóm khách hàng",
        default="medium",
    )
    customer_status = fields.Selection(
        [
            ("new", "Lead mới"),
            ("contacted", "Đã liên hệ"),
            ("qualified", "Lead đủ điều kiện"),
            ("quotation", "Đã gửi báo giá"),
            ("negotiation", "Đang thương lượng"),
            ("won", "Chốt thành công"),
            ("lost", "Thất bại"),
            ("dormant", "Lâu chưa tương tác"),
        ],
        string="Tình trạng khách hàng",
        default="new",
    )
    potential_level = fields.Selection(
        [
            ("high", "Tiềm năng cao"),
            ("medium", "Tiềm năng trung bình"),
            ("low", "Tiềm năng thấp"),
        ],
        string="Mức độ tiềm năng",
        default="medium",
    )
    lead_source_id = fields.Many2one("utm.source", string="Nguồn lead")
