# -*- coding: utf-8 -*-
from odoo import fields, models


class MailLog(models.Model):
    _name = "custom.mail.log"
    _description = "Nhật ký gửi Email"
    _order = "sent_date desc"

    campaign_id = fields.Many2one("custom.mail.campaign", string="Chiến dịch", ondelete="cascade")
    partner_id = fields.Many2one("res.partner", string="Khách hàng")
    email_to = fields.Char(string="Email người nhận")
    sent_date = fields.Datetime(string="Thời gian gửi")
    status = fields.Selection(
        [("sent", "Đã gửi"), ("failed", "Gửi thất bại")],
        string="Trạng thái",
        default="sent",
    )
    error_message = fields.Text(string="Thông báo lỗi")
