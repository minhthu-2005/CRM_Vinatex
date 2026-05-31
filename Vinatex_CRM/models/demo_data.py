# -*- coding: utf-8 -*-
from odoo import api, models


class CrmLeadDemoData(models.Model):
    _inherit = "crm.lead"

    @api.model
    def seed_vinatex_demo_data(self):
        env = self.sudo().with_context(
            tracking_disable=True,
            mail_create_nolog=True,
            mail_notrack=True,
            no_reset_password=True,
        ).env
        imd = env["ir.model.data"].sudo()
        module = "crm_tong_hop"

        def bind_xmlid(xmlid, record):
            data = imd.search([("module", "=", module), ("name", "=", xmlid)], limit=1)
            vals = {
                "module": module,
                "name": xmlid,
                "model": record._name,
                "res_id": record.id,
                "noupdate": True,
            }
            if data:
                data.write(vals)
            else:
                imd.create(vals)
            return record

        def ref(xmlid):
            record = env.ref("%s.%s" % (module, xmlid), raise_if_not_found=False)
            return record.exists() if record else record

        def upsert(xmlid, model, vals):
            record = ref(xmlid)
            Model = env[model].sudo()
            if record:
                record.write(vals)
                return record
            if model == "crm.customer.retention.analytics" and vals.get("customer_id"):
                record = Model.search([("customer_id", "=", vals["customer_id"])], limit=1)
                if record:
                    record.write(vals)
                    return bind_xmlid(xmlid, record)
            return bind_xmlid(xmlid, Model.create(vals))

        def template(xmlid, fallback_xmlid="template_followup_email_vn"):
            return ref(xmlid) or ref(fallback_xmlid)

        admin = env.ref("base.user_admin")
        country_vn = env.ref("base.vn", raise_if_not_found=False)
        stage_new = env.ref("crm_tong_hop.stage_new_lead")
        stage_qualified = env.ref("crm_tong_hop.stage_qualified")
        stage_proposal = env.ref("crm_tong_hop.stage_proposal")
        stage_negotiation = env.ref("crm_tong_hop.stage_negotiation")
        stage_won = env.ref("crm_tong_hop.stage_won")
        stage_lost = env.ref("crm_tong_hop.stage_lost")
        stage_dormant = env.ref("crm_tong_hop.stage_dormant")

        stage_rows = [
            (stage_new, "Lead mới", "Lead mới phát sinh, cần xác nhận nhu cầu và bổ sung đủ thông tin khách hàng."),
            (stage_qualified, "Đã xác thực nhu cầu", "Đã xác nhận khách hàng có nhu cầu thực tế, sản phẩm, số lượng và thời điểm dự kiến."),
            (stage_proposal, "Đã gửi báo giá", "Đã gửi báo giá, mẫu vải hoặc đề xuất phương án sản xuất cho khách hàng."),
            (stage_negotiation, "Đang thương lượng", "Đang thương lượng giá, tiến độ, tiêu chuẩn chất lượng hoặc điều khoản thanh toán."),
            (stage_won, "Chốt thành công", "Cơ hội đã chốt thành công và cần chuyển sang chăm sóc sau bán."),
            (stage_lost, "Thất bại", "Cơ hội không thành công, cần ghi nhận lý do để phân tích và chăm sóc lại khi phù hợp."),
            (stage_dormant, "Lâu chưa tương tác", "Khách hàng chưa phản hồi trong thời gian dài, cần đưa vào danh sách chăm sóc lại."),
        ]
        for stage, name, requirements in stage_rows:
            stage.write({"name": name, "requirements": requirements})

        stage_aliases = {
            "New": stage_new,
            "New Lead": stage_new,
            "Qualified": stage_qualified,
            "Proposal": stage_proposal,
            "Proposition": stage_proposal,
            "Negotiation": stage_negotiation,
            "Won": stage_won,
            "Lost": stage_lost,
            "Dormant": stage_dormant,
        }
        for old_name, target_stage in stage_aliases.items():
            old_stages = env["crm.stage"].sudo().search([("name", "=", old_name), ("id", "!=", target_stage.id)])
            if old_stages:
                env["crm.lead"].with_context(active_test=False, skip_auto_cskh_followup=True).sudo().search([("stage_id", "in", old_stages.ids)]).write({
                    "stage_id": target_stage.id,
                })

        sources = {
            "website": upsert("demo_source_website", "utm.source", {"name": "Cổng website VINATEX CRM"}),
            "trade_fair": upsert("demo_source_trade_fair", "utm.source", {"name": "Hội chợ dệt may"}),
            "referral": upsert("demo_source_referral", "utm.source", {"name": "Khách hàng giới thiệu"}),
            "zalo": upsert("demo_source_zalo", "utm.source", {"name": "Zalo / Hotline"}),
            "email": upsert("demo_source_email", "utm.source", {"name": "Email chăm sóc khách hàng"}),
        }

        self._localize_existing_odoo_demo_leads(env, admin, country_vn, sources, {
            "new": stage_new,
            "qualified": stage_qualified,
            "proposal": stage_proposal,
            "negotiation": stage_negotiation,
            "won": stage_won,
            "lost": stage_lost,
            "dormant": stage_dormant,
        })

        partner_rows = [
            ("demo_partner_an_phu", "Công ty May An Phú", "Lan Anh", "lananh@anphu-garment.vn", "+84 236 381 2244", "https://anphu-garment.vn", "high", "negotiation", "high", "priority", 820000000, sources["website"]),
            ("demo_partner_binh_minh", "Công ty Dệt may Bình Minh", "Nguyễn Quốc Huy", "huy@binhminhtextile.vn", "+84 28 3820 1188", "https://binhminhtextile.vn", "medium", "quotation", "high", "discount", 460000000, sources["trade_fair"]),
            ("demo_partner_song_han", "Công ty Đồng phục Sông Hàn", "Trần Minh Hằng", "hang@songhanuniform.vn", "+84 236 355 7788", "https://songhanuniform.vn", "medium", "qualified", "medium", "consulting", 240000000, sources["zalo"]),
            ("demo_partner_hai_dang", "Công ty Thời trang Hải Đăng", "Lê Tuấn Kiệt", "kiet@haidangfashion.vn", "+84 24 3933 0202", "https://haidangfashion.vn", "high", "won", "high", "gift", 1150000000, sources["referral"]),
            ("demo_partner_mekong_sport", "Công ty May thể thao Mekong", "Phạm Gia Bảo", "bao@mekongsportwear.vn", "+84 292 388 5566", "https://mekongsportwear.vn", "low", "new", "medium", "consulting", 96000000, sources["website"]),
            ("demo_partner_nam_a", "Công ty Xuất khẩu Nam Á", "Võ Hoàng Nam", "nam.vo@namasia-export.vn", "+84 236 377 9900", "https://namasia-export.vn", "high", "contacted", "high", "credit", 680000000, sources["email"]),
            ("demo_partner_green_line", "Công ty Thời trang Xanh", "Mai Thanh Trúc", "truc@thoitrangxanh.vn", "+84 28 3912 6677", "https://thoitrangxanh.vn", "medium", "dormant", "medium", "discount", 180000000, sources["email"]),
            ("demo_partner_hoa_tien", "Công ty May Hòa Tiến", "Đặng Thị Thu", "thu@hoatien.vn", "+84 236 365 1010", "https://hoatien.vn", "medium", "lost", "low", "consulting", 120000000, sources["trade_fair"]),
            ("demo_partner_blue_ocean", "Công ty Đồng phục Biển Xanh", "Lý Minh Khang", "khang@bienxanh-uniform.vn", "+84 236 399 8822", "https://bienxanh-uniform.vn", "high", "quotation", "high", "priority", 540000000, sources["website"]),
            ("demo_partner_viet_kids", "Công ty May Trẻ em Việt", "Ngô Bảo Ngọc", "ngoc@treemviet.vn", "+84 28 3888 4141", "https://treemviet.vn", "medium", "negotiation", "medium", "gift", 320000000, sources["referral"]),
            ("demo_partner_lotus", "Công ty Bảo hộ Hoa Sen", "Đỗ Minh Quân", "quan@baoholoasen.vn", "+84 236 390 7788", "https://baoholoasen.vn", "dormant", "dormant", "low", "discount", 74000000, sources["email"]),
            ("demo_partner_duplicate", "Công ty May An Phú - CN Quảng Nam", "Lan Anh", "lananh.qn@anphu-garment.vn", "+84 236 381 2244", "https://anphu-garment.vn/quang-nam", "high", "contacted", "high", "priority", 360000000, sources["website"]),
            ("demo_partner_phu_thinh", "Công ty May Phú Thịnh", "Huỳnh Thảo Vy", "vy@phuthinh-garment.vn", "+84 274 388 6611", "https://phuthinh-garment.vn", "high", "quotation", "high", "priority", 610000000, sources["trade_fair"]),
            ("demo_partner_tan_phat", "Công ty Dệt Tân Phát", "Trương Minh Đức", "duc@tanphattextile.vn", "+84 251 377 7744", "https://tanphattextile.vn", "medium", "qualified", "medium", "consulting", 270000000, sources["zalo"]),
            ("demo_partner_minh_chau", "Công ty Đồng phục Minh Châu", "Phạm Ngọc Châu", "chau@minhchauuniform.vn", "+84 236 366 9090", "https://minhchauuniform.vn", "medium", "new", "medium", "discount", 155000000, sources["website"]),
            ("demo_partner_bao_ngoc", "Công ty May Bảo Ngọc", "Vũ Hoài Linh", "linh@baongoc-garment.vn", "+84 28 3999 1200", "https://baongoc-garment.vn", "high", "negotiation", "high", "credit", 720000000, sources["referral"]),
            ("demo_partner_thanh_dat", "Công ty Gia công Thành Đạt", "Nguyễn Tấn Lộc", "loc@thanhdat.vn", "+84 236 358 4455", "https://thanhdat.vn", "medium", "contacted", "medium", "consulting", 390000000, sources["email"]),
            ("demo_partner_an_khang", "Công ty Thời trang An Khang", "Đinh Khánh My", "my@ankhangfashion.vn", "+84 24 3908 2211", "https://ankhangfashion.vn", "high", "won", "high", "gift", 980000000, sources["trade_fair"]),
            ("demo_partner_dai_phat", "Công ty Xuất khẩu Đại Phát", "Bùi Hải Đăng", "dang@daiphat-export.vn", "+84 236 370 1010", "https://daiphat-export.vn", "medium", "dormant", "medium", "discount", 205000000, sources["email"]),
            ("demo_partner_hung_vuong", "Công ty May Hưng Vượng", "Lê Nhật Minh", "minh@hungvuong-garment.vn", "+84 28 3866 5151", "https://hungvuong-garment.vn", "high", "quotation", "high", "priority", 830000000, sources["website"]),
            ("demo_partner_van_xuan", "Công ty Vải kỹ thuật Vạn Xuân", "Hoàng Thu Hà", "ha@vanxuantextile.vn", "+84 236 388 2121", "https://vanxuantextile.vn", "medium", "negotiation", "medium", "credit", 430000000, sources["referral"]),
            ("demo_partner_kim_long", "Công ty Bảo hộ lao động Kim Long", "Tạ Quốc Việt", "viet@kimlong-safety.vn", "+84 251 399 2244", "https://kimlong-safety.vn", "low", "new", "medium", "consulting", 125000000, sources["zalo"]),
            ("demo_partner_sao_mai", "Công ty May Sao Mai", "Lương Mỹ Duyên", "duyen@saomai-garment.vn", "+84 236 355 8181", "https://saomai-garment.vn", "medium", "lost", "low", "discount", 165000000, sources["trade_fair"]),
            ("demo_partner_hoa_binh", "Công ty Dệt may Hòa Bình", "Đào Đức Anh", "anh@hoabinhtextile.vn", "+84 28 3911 6600", "https://hoabinhtextile.vn", "high", "contacted", "high", "priority", 575000000, sources["website"]),
        ]

        partners = {}
        for xmlid, company, contact, email, phone, website, segment, status, potential, offer, revenue, source in partner_rows:
            partners[xmlid] = upsert(xmlid, "res.partner", {
                "name": company,
                "company_type": "company",
                "function": contact,
                "email": email,
                "phone": phone,
                "website": website,
                "street": "Khu công nghiệp Hòa Khánh, Đà Nẵng",
                "city": "Đà Nẵng",
                "country_id": country_vn.id if country_vn else False,
                "segment": segment,
                "customer_status": status,
                "potential_level": potential,
                "lead_source_id": source.id,
                "crm_estimated_revenue": revenue,
                "preferred_offer": offer,
                "personalization_note": "Khách hàng mẫu phục vụ demo VINATEX CRM: lưu nhu cầu sản xuất, lịch chăm sóc, chiến dịch và dữ liệu khiếu nại liên kết với lead.",
            })

        lead_rows = [
            ("demo_lead_an_phu", "Đơn hàng áo khoác xuất khẩu - An Phú", "opportunity", partners["demo_partner_an_phu"], stage_negotiation, 820000000, 78, "2026-05-20", "Cần 35.000 áo khoác kỹ thuật, vải chống thấm, giao 2 đợt trong quý III."),
            ("demo_lead_binh_minh", "Báo giá sơ mi công sở - Bình Minh", "opportunity", partners["demo_partner_binh_minh"], stage_proposal, 460000000, 55, "2026-05-18", "Khách cần 22.000 áo sơ mi nam nữ, yêu cầu mẫu vải cotton pha và bảng size chi tiết."),
            ("demo_lead_song_han", "Đồng phục khu nghỉ dưỡng miền Trung - Sông Hàn", "opportunity", partners["demo_partner_song_han"], stage_qualified, 240000000, 35, "2026-05-22", "Đồng phục lễ tân, buồng phòng và bếp; cần tư vấn chất liệu thoáng, dễ giặt."),
            ("demo_lead_hai_dang", "Hợp đồng gia công áo khoác - Hải Đăng", "opportunity", partners["demo_partner_hai_dang"], stage_won, 1150000000, 100, "2026-05-15", "Đã chốt hợp đồng gia công áo khoác xuất khẩu, theo dõi chăm sóc sau bán."),
            ("demo_lead_mekong", "Nhu cầu đồ thể thao mới - Mekong", "lead", partners["demo_partner_mekong_sport"], stage_new, 96000000, 12, "2026-05-27", "Khách mới để lại biểu mẫu website, cần xác nhận mẫu áo chạy bộ và số lượng tối thiểu."),
            ("demo_lead_nam_a", "Tư vấn điều khoản thanh toán - Nam Á", "lead", partners["demo_partner_nam_a"], stage_new, 680000000, 20, "2026-05-26", "Khách hỏi năng lực sản xuất hàng xuất khẩu và điều khoản thanh toán theo từng lô."),
            ("demo_lead_green_line", "Chăm sóc lại khách hàng Thời trang Xanh", "opportunity", partners["demo_partner_green_line"], stage_dormant, 180000000, 10, "2026-01-18", "Khách lâu chưa tương tác, cần chiến dịch chăm sóc lại và cập nhật nhu cầu mùa mới."),
            ("demo_lead_hoa_tien", "Cơ hội thất bại - Hòa Tiến", "opportunity", partners["demo_partner_hoa_tien"], stage_lost, 120000000, 0, "2026-04-12", "Khách tạm hoãn do ngân sách, cần lưu lý do thất bại để phân tích."),
            ("demo_lead_blue_ocean", "Báo giá đồng phục Biển Xanh", "opportunity", partners["demo_partner_blue_ocean"], stage_proposal, 540000000, 60, "2026-05-21", "Cần báo giá 18.000 bộ đồng phục khách sạn, có yêu cầu thêu logo."),
            ("demo_lead_viet_kids", "Đơn hàng thời trang trẻ em Việt", "opportunity", partners["demo_partner_viet_kids"], stage_negotiation, 320000000, 72, "2026-05-19", "Đang thương lượng mẫu in và tiêu chuẩn an toàn nguyên phụ liệu cho trẻ em."),
            ("demo_lead_lotus", "Khách cũ lâu chưa phản hồi - Hoa Sen", "lead", partners["demo_partner_lotus"], stage_dormant, 74000000, 5, "2025-09-02", "Khách cũ chưa phản hồi sau nhiều lần chăm sóc, dùng để demo danh sách ngừng tương tác."),
            ("demo_lead_an_phu_duplicate", "Lead nghi trùng An Phú - chi nhánh Quảng Nam", "lead", partners["demo_partner_duplicate"], stage_new, 360000000, 18, "2026-05-28", "Lead có số điện thoại trùng với An Phú để demo kiểm soát dữ liệu trùng."),
            ("demo_lead_phu_thinh", "Báo giá áo bảo hộ chống cháy - Phú Thịnh", "opportunity", partners["demo_partner_phu_thinh"], stage_proposal, 610000000, 58, "2026-05-24", "Khách cần 16.000 bộ bảo hộ chống cháy, yêu cầu chứng nhận vật liệu và mẫu thử."),
            ("demo_lead_tan_phat", "Tư vấn vải dệt kỹ thuật - Tân Phát", "opportunity", partners["demo_partner_tan_phat"], stage_qualified, 270000000, 42, "2026-05-25", "Khách cần so sánh độ bền màu, độ co rút và thời gian cung ứng vải."),
            ("demo_lead_minh_chau", "Đồng phục trường học mùa khai giảng - Minh Châu", "lead", partners["demo_partner_minh_chau"], stage_new, 155000000, 16, "2026-05-27", "Khách cần tư vấn đồng phục học sinh, áo khoác nhẹ và lịch giao trước tháng 8."),
            ("demo_lead_bao_ngoc", "Đơn hàng áo thun xuất khẩu - Bảo Ngọc", "opportunity", partners["demo_partner_bao_ngoc"], stage_negotiation, 720000000, 70, "2026-05-23", "Đang chốt giá áo thun xuất khẩu, yêu cầu kiểm tra màu in trước sản xuất hàng loạt."),
            ("demo_lead_thanh_dat", "Gia công quần kaki doanh nghiệp - Thành Đạt", "opportunity", partners["demo_partner_thanh_dat"], stage_qualified, 390000000, 46, "2026-05-26", "Khách cần mẫu quần kaki công sở, ưu tiên độ bền đường may và lịch giao từng đợt."),
            ("demo_lead_an_khang", "Hợp đồng thời trang công sở - An Khang", "opportunity", partners["demo_partner_an_khang"], stage_won, 980000000, 100, "2026-05-14", "Đã chốt hợp đồng thời trang công sở, cần cập nhật tiến độ sản xuất hằng tuần."),
            ("demo_lead_dai_phat", "Chăm sóc lại khách xuất khẩu Đại Phát", "opportunity", partners["demo_partner_dai_phat"], stage_dormant, 205000000, 8, "2026-02-10", "Khách xuất khẩu lâu chưa phản hồi sau báo giá, cần gọi xác nhận kế hoạch đặt hàng quý III."),
            ("demo_lead_hung_vuong", "Báo giá đồng phục chuỗi nhà máy - Hưng Vượng", "opportunity", partners["demo_partner_hung_vuong"], stage_proposal, 830000000, 63, "2026-05-22", "Khách cần 28.000 bộ đồng phục nhà máy, chia giao cho ba điểm nhận hàng."),
            ("demo_lead_van_xuan", "Đơn hàng vải kỹ thuật - Vạn Xuân", "opportunity", partners["demo_partner_van_xuan"], stage_negotiation, 430000000, 68, "2026-05-21", "Đang thương lượng tiêu chuẩn kiểm định, thời gian giao mẫu và điều khoản thanh toán."),
            ("demo_lead_kim_long", "Nhu cầu bảo hộ lao động - Kim Long", "lead", partners["demo_partner_kim_long"], stage_new, 125000000, 15, "2026-05-28", "Khách hỏi nhanh về áo phản quang, mũ bảo hộ và số lượng đặt thử ban đầu."),
            ("demo_lead_sao_mai", "Cơ hội thất bại - Sao Mai", "opportunity", partners["demo_partner_sao_mai"], stage_lost, 165000000, 0, "2026-04-18", "Khách chọn nhà cung cấp khác do cần giao hàng gấp hơn năng lực hiện tại."),
            ("demo_lead_hoa_binh", "Tư vấn năng lực dệt may - Hòa Bình", "lead", partners["demo_partner_hoa_binh"], stage_new, 575000000, 24, "2026-05-28", "Khách cần hồ sơ năng lực VINATEX, bảng giá tham khảo và lịch trao đổi trực tuyến."),
        ]

        leads = {}
        for xmlid, name, lead_type, partner, stage, revenue, probability, last_date, requirement in lead_rows:
            leads[xmlid] = upsert(xmlid, "crm.lead", {
                "name": name,
                "type": lead_type,
                "partner_id": partner.id,
                "partner_name": partner.name,
                "contact_name": partner.function,
                "email_from": partner.email,
                "phone": partner.phone,
                "website": partner.website,
                "source_id": partner.lead_source_id.id,
                "user_id": admin.id,
                "stage_id": stage.id,
                "expected_revenue": revenue,
                "probability": probability,
                "initial_product_requirement": requirement,
                "description": requirement,
                "last_interaction_date": last_date,
            })
        leads["demo_lead_lotus"].write({
            "active": False,
            "archived_by_cron": True,
            "inactive_archive_date": "2026-05-28",
        })

        cskh_rows = [
            ("demo_cskh_an_phu_call", leads["demo_lead_an_phu"], "call", "2026-05-22 09:20:00", "Trao đổi thông số áo khoác chống thấm và kế hoạch duyệt mẫu.", "Khách thống nhất gửi hồ sơ kỹ thuật bản mới.", "Áo khoác kỹ thuật", "Gửi bảng vải và mẫu thử giặt", "2026-05-30", "pending"),
            ("demo_cskh_an_phu_meeting", leads["demo_lead_an_phu"], "meeting", "2026-05-24 14:00:00", "Họp trực tuyến với phòng mua hàng để chốt tiến độ giao 2 đợt.", "Cần cập nhật đơn giá cho phương án khóa kéo mới.", "Áo khoác xuất khẩu", "Gửi báo giá điều chỉnh", "2026-05-31", "pending"),
            ("demo_cskh_binh_minh_quote", leads["demo_lead_binh_minh"], "quotation", "2026-05-21 10:15:00", "Đã gửi báo giá sơ mi công sở và bảng size.", "Khách yêu cầu bổ sung mẫu vải cotton pha.", "Sơ mi công sở", "Theo dõi phản hồi mẫu vải", "2026-05-29", "pending"),
            ("demo_cskh_song_han_note", leads["demo_lead_song_han"], "note", "2026-05-23 16:40:00", "Ghi nhận nhu cầu đồng phục khu nghỉ dưỡng miền Trung.", "Khách cần phối màu theo bộ nhận diện thương hiệu.", "Đồng phục khu nghỉ dưỡng", "Lên lịch tư vấn mẫu mã", "2026-06-01", "draft"),
            ("demo_cskh_hai_dang_done", leads["demo_lead_hai_dang"], "email", "2026-05-17 08:30:00", "Gửi thư cảm ơn sau khi chốt hợp đồng.", "Khách xác nhận đầu mối theo dõi sản xuất.", "Áo khoác xuất khẩu", "Chăm sóc sau bán hàng", "2026-06-03", "done"),
            ("demo_cskh_mekong_new", leads["demo_lead_mekong"], "call", "2026-05-28 09:00:00", "Gọi xác nhận nhu cầu mới từ website.", "Khách hẹn gửi mẫu áo chạy bộ.", "Đồ thể thao", "Tạo báo giá sơ bộ", "2026-05-29", "pending"),
            ("demo_cskh_green_line_winback", leads["demo_lead_green_line"], "email", "2026-05-11 11:30:00", "Gửi email chăm sóc lại khách lâu chưa giao dịch.", "Chưa phản hồi, cần nhắc lại bằng Zalo.", "Áo polo doanh nghiệp", "Gửi chiến dịch chăm sóc lại", "2026-06-04", "pending"),
            ("demo_cskh_blue_ocean_quote", leads["demo_lead_blue_ocean"], "quotation", "2026-05-25 13:10:00", "Gửi bảng giá đồng phục khách sạn có thêu logo.", "Khách cần duyệt mẫu trước ngày 05/06.", "Đồng phục khách sạn", "Theo dõi duyệt mẫu", "2026-06-02", "pending"),
            ("demo_cskh_viet_kids_meeting", leads["demo_lead_viet_kids"], "meeting", "2026-05-26 15:00:00", "Trao đổi tiêu chuẩn an toàn nguyên phụ liệu trẻ em.", "Cần chứng từ kiểm định vải và mực in.", "Thời trang trẻ em", "Gửi hồ sơ chứng nhận", "2026-05-30", "pending"),
            ("demo_cskh_hoa_tien_lost", leads["demo_lead_hoa_tien"], "note", "2026-04-13 09:30:00", "Khách tạm dừng vì ngân sách quý này.", "Ghi nhận lý do thất bại, hẹn chăm sóc lại quý sau.", "Áo thun sự kiện", "Đưa vào danh sách chăm sóc lại", "2026-07-05", "done"),
            ("demo_cskh_phu_thinh_quote", leads["demo_lead_phu_thinh"], "quotation", "2026-05-26 10:00:00", "Gửi báo giá bảo hộ chống cháy kèm chứng nhận vật liệu.", "Khách muốn xem mẫu thử trước khi trình ban giám đốc.", "Bảo hộ chống cháy", "Gửi mẫu thử và lịch duyệt", "2026-06-01", "pending"),
            ("demo_cskh_tan_phat_consult", leads["demo_lead_tan_phat"], "call", "2026-05-26 15:20:00", "Tư vấn thông số vải dệt kỹ thuật và mức độ bền màu.", "Khách chọn hai phương án vải để so sánh.", "Vải kỹ thuật", "Gửi bảng so sánh vật liệu", "2026-05-31", "pending"),
            ("demo_cskh_minh_chau_new", leads["demo_lead_minh_chau"], "call", "2026-05-28 08:45:00", "Xác nhận nhu cầu đồng phục học sinh mùa khai giảng.", "Khách cần mẫu áo polo và áo khoác nhẹ.", "Đồng phục học sinh", "Tạo lịch tư vấn mẫu", "2026-05-30", "pending"),
            ("demo_cskh_bao_ngoc_meeting", leads["demo_lead_bao_ngoc"], "meeting", "2026-05-25 14:30:00", "Trao đổi tiêu chuẩn màu in cho áo thun xuất khẩu.", "Khách yêu cầu ảnh mẫu trước khi đặt cọc.", "Áo thun xuất khẩu", "Gửi ảnh mẫu và bảng màu", "2026-05-29", "pending"),
            ("demo_cskh_thanh_dat_note", leads["demo_lead_thanh_dat"], "note", "2026-05-27 09:10:00", "Ghi nhận yêu cầu quần kaki công sở theo từng size.", "Cần kiểm tra năng lực chuyền may trong tuần tới.", "Quần kaki công sở", "Xác nhận lịch giao mẫu", "2026-06-02", "draft"),
            ("demo_cskh_an_khang_done", leads["demo_lead_an_khang"], "email", "2026-05-16 17:00:00", "Gửi kế hoạch chăm sóc sau bán và lịch cập nhật tiến độ.", "Khách xác nhận nhận báo cáo tiến độ hằng tuần.", "Thời trang công sở", "Cập nhật tiến độ sản xuất", "2026-06-05", "done"),
            ("demo_cskh_dai_phat_winback", leads["demo_lead_dai_phat"], "call", "2026-05-20 11:00:00", "Gọi chăm sóc lại khách xuất khẩu lâu chưa phản hồi.", "Khách đang chờ kế hoạch nhập hàng quý III.", "Hàng xuất khẩu", "Gửi lại hồ sơ năng lực", "2026-06-06", "pending"),
            ("demo_cskh_hung_vuong_quote", leads["demo_lead_hung_vuong"], "quotation", "2026-05-24 16:15:00", "Gửi báo giá đồng phục chuỗi nhà máy theo ba điểm nhận hàng.", "Khách cần bổ sung chi phí vận chuyển theo khu vực.", "Đồng phục nhà máy", "Gửi phụ lục vận chuyển", "2026-05-31", "pending"),
            ("demo_cskh_van_xuan_meeting", leads["demo_lead_van_xuan"], "meeting", "2026-05-23 09:00:00", "Họp về tiêu chuẩn kiểm định vải kỹ thuật.", "Khách yêu cầu biên bản thử nghiệm trước khi chốt đơn.", "Vải kỹ thuật", "Gửi lịch thử nghiệm", "2026-06-03", "pending"),
            ("demo_cskh_kim_long_new", leads["demo_lead_kim_long"], "call", "2026-05-28 10:30:00", "Xác nhận nhu cầu áo phản quang và mũ bảo hộ.", "Khách muốn đặt thử số lượng nhỏ trước.", "Bảo hộ lao động", "Gửi báo giá đặt thử", "2026-05-30", "pending"),
            ("demo_cskh_sao_mai_lost", leads["demo_lead_sao_mai"], "note", "2026-04-19 09:00:00", "Khách chọn nhà cung cấp giao nhanh hơn.", "Lưu lý do thất bại để cải thiện năng lực phản hồi.", "Đồng phục sự kiện", "Chăm sóc lại sau mùa cao điểm", "2026-07-10", "done"),
            ("demo_cskh_hoa_binh_new", leads["demo_lead_hoa_binh"], "email", "2026-05-28 11:15:00", "Gửi hồ sơ năng lực VINATEX và đề xuất lịch trao đổi.", "Khách đề nghị lịch họp trực tuyến đầu tuần sau.", "Dệt may tổng hợp", "Xác nhận lịch họp", "2026-05-31", "pending"),
        ]

        cskh_profiles = {}
        for xmlid, lead, interaction_type, date, content, result, product, next_action, deadline, state in cskh_rows:
            cskh_profiles[xmlid] = upsert(xmlid, "crm.cskh.profile", {
                "lead_id": lead.id,
                "customer_id": lead.partner_id.id,
                "user_id": admin.id,
                "interaction_type": interaction_type,
                "interaction_date": date,
                "content": content,
                "result": result,
                "customer_need": lead.initial_product_requirement,
                "product_category": product,
                "design_sample": "Theo hồ sơ kỹ thuật hoặc mẫu nhận diện của khách hàng",
                "material_info": "Cần xác nhận mẫu vải, phụ liệu và tiêu chuẩn kiểm định trước sản xuất.",
                "technical_requirement": "Theo bảng thông số kỹ thuật và tiêu chuẩn kiểm soát chất lượng của từng đơn hàng.",
                "expected_order_qty": revenue_by_lead(lead),
                "delivery_terms": "Giao hàng theo từng đợt, ưu tiên cập nhật tiến độ qua email và Zalo.",
                "next_action": next_action,
                "followup_deadline": deadline,
                "state": state,
            })

        demo_profiles = env["crm.cskh.profile"].sudo().search(
            [], order="interaction_date desc, id desc"
        )
        for index, profile in enumerate(demo_profiles):
            bucket = index % 10
            vals = {}
            if bucket in (0, 1, 2, 3):
                vals["state"] = "pending"
                if not profile.next_action:
                    vals["next_action"] = "Theo dõi phản hồi và cập nhật tiến độ chăm sóc."
                if not profile.followup_deadline:
                    vals["followup_deadline"] = "2026-06-03"
            elif bucket in (4, 5, 6):
                vals["state"] = "done"
            elif bucket in (7, 8):
                vals.update({
                    "state": "draft",
                    "next_action": False,
                    "followup_deadline": False,
                })
            else:
                vals.update({
                    "state": "cancel",
                    "next_action": False,
                    "followup_deadline": False,
                })

            if profile.lead_id:
                production_vals = {"lead_id": profile.lead_id.id}
                profile._apply_lead_production_defaults(production_vals)
                if not profile.customer_need and production_vals.get("customer_need"):
                    vals["customer_need"] = production_vals["customer_need"]
                if not profile.product_category and production_vals.get("product_category"):
                    vals["product_category"] = production_vals["product_category"]
                if not profile.expected_order_qty and production_vals.get("expected_order_qty"):
                    vals["expected_order_qty"] = production_vals["expected_order_qty"]

            profile.with_context(
                skip_cskh_audit=True,
                tracking_disable=True,
            ).write(vals)
            profile._create_followup_activity()

        complaint_rows = [
            ("demo_complaint_an_phu_sla", leads["demo_lead_an_phu"], cskh_profiles["demo_cskh_an_phu_call"], "Chậm phản hồi mẫu thử giặt", "Khách phản ánh chưa nhận được kết quả thử giặt đúng lịch.", "medium", "processing", "2026-05-29 17:00:00", "2026-05-28 10:00:00", False, "Chưa đồng bộ lịch phản hồi giữa kiểm soát chất lượng và CSKH.", "Đã gom kết quả thử và gửi lịch phản hồi mới.", "Khách chấp nhận gia hạn tới cuối ngày.", 4),
            ("demo_complaint_binh_minh_size", leads["demo_lead_binh_minh"], cskh_profiles["demo_cskh_binh_minh_quote"], "Sai bảng size trong file báo giá", "File báo giá đính kèm nhầm bảng size nam cho dòng nữ.", "low", "resolved", "2026-05-28 16:00:00", "2026-05-28 09:40:00", "2026-05-28 11:15:00", "Nhầm phiên bản file báo giá.", "Đã gửi lại file báo giá đúng và cập nhật checklist kiểm tra.", "Khách hài lòng vì xử lý nhanh.", 5),
            ("demo_complaint_hai_dang_label", leads["demo_lead_hai_dang"], cskh_profiles["demo_cskh_hai_dang_done"], "Thiếu thông tin nhãn phụ kiện", "Khách cần bổ sung thông tin nhãn và phụ kiện trong kế hoạch sản xuất.", "medium", "closed", "2026-05-21 12:00:00", "2026-05-20 09:00:00", "2026-05-20 15:00:00", "Checklist phụ kiện chưa cập nhật đủ.", "Đã bổ sung bảng phụ kiện và gửi xác nhận cho khách.", "Khách xác nhận tiếp tục sản xuất.", 5),
            ("demo_complaint_green_line_no_reply", leads["demo_lead_green_line"], cskh_profiles["demo_cskh_green_line_winback"], "Khách chưa nhận email chăm sóc lại", "Email chăm sóc bị vào hộp thư quảng cáo nên khách chưa thấy.", "low", "open", "2026-06-02 17:00:00", False, False, "", "Gọi xác nhận email và gửi lại qua Zalo.", "", 0),
            ("demo_complaint_blue_ocean_embroidery", leads["demo_lead_blue_ocean"], cskh_profiles["demo_cskh_blue_ocean_quote"], "Mẫu thêu logo lệch màu", "Khách phản hồi màu chỉ thêu logo chưa khớp bộ nhận diện thương hiệu.", "high", "processing", "2026-05-29 12:00:00", "2026-05-28 08:50:00", False, "Bảng màu chưa được đối chiếu trước khi làm mẫu.", "Đang làm lại mẫu thêu và gửi ảnh duyệt trước.", "Khách yêu cầu phản hồi trong ngày.", 3),
            ("demo_complaint_phu_thinh_certificate", leads["demo_lead_phu_thinh"], cskh_profiles["demo_cskh_phu_thinh_quote"], "Thiếu chứng nhận vật liệu chống cháy", "Khách cần chứng nhận vật liệu trước khi duyệt mẫu bảo hộ.", "high", "open", "2026-06-01 16:00:00", False, False, "", "Liên hệ bộ phận kỹ thuật để bổ sung hồ sơ chứng nhận.", "", 0),
            ("demo_complaint_bao_ngoc_color", leads["demo_lead_bao_ngoc"], cskh_profiles["demo_cskh_bao_ngoc_meeting"], "Ảnh mẫu màu in chưa rõ", "Khách phản hồi ảnh mẫu màu in chưa đủ sáng để duyệt nội bộ.", "medium", "processing", "2026-05-30 12:00:00", "2026-05-29 08:30:00", False, "Ảnh mẫu gửi từ xưởng chưa đạt tiêu chuẩn hiển thị.", "Chụp lại mẫu dưới ánh sáng chuẩn và gửi lại.", "Khách chờ ảnh mới để đặt cọc.", 3),
            ("demo_complaint_hung_vuong_shipping", leads["demo_lead_hung_vuong"], cskh_profiles["demo_cskh_hung_vuong_quote"], "Thiếu phụ lục vận chuyển", "Báo giá chưa tách chi phí vận chuyển theo ba điểm nhận hàng.", "low", "resolved", "2026-05-30 17:00:00", "2026-05-29 10:10:00", "2026-05-29 15:45:00", "Chưa có mẫu phụ lục vận chuyển cho đơn nhiều điểm nhận.", "Đã bổ sung phụ lục và gửi lại báo giá.", "Khách xác nhận đã nhận đủ.", 4),
            ("demo_complaint_van_xuan_testing", leads["demo_lead_van_xuan"], cskh_profiles["demo_cskh_van_xuan_meeting"], "Chậm lịch thử nghiệm vải", "Khách cần lịch thử nghiệm sớm hơn để kịp kế hoạch mua hàng.", "medium", "open", "2026-06-03 15:00:00", False, False, "", "Ưu tiên đặt lịch thử nghiệm và thông báo lại trong ngày.", "", 0),
            ("demo_complaint_hoa_binh_profile", leads["demo_lead_hoa_binh"], cskh_profiles["demo_cskh_hoa_binh_new"], "Hồ sơ năng lực thiếu hình ảnh nhà máy", "Khách muốn bổ sung hình ảnh dây chuyền để trình ban lãnh đạo.", "low", "open", "2026-06-01 10:00:00", False, False, "", "Bổ sung ảnh dây chuyền, năng lực sản xuất và chứng nhận liên quan.", "", 0),
        ]

        for xmlid, lead, profile, title, desc, severity, state, deadline, response, resolved, root, solution, feedback, score in complaint_rows:
            vals = {
                "customer_id": lead.partner_id.id,
                "lead_id": lead.id,
                "cskh_profile_id": profile.id,
                "sale_user_id": admin.id,
                "assigned_user_id": admin.id,
                "title": title,
                "description": desc,
                "severity": severity,
                "state": state,
                "deadline": deadline,
                "root_cause": root,
                "solution": solution,
                "customer_feedback": feedback,
                "satisfaction_score": score,
            }
            if response:
                vals["response_date"] = response
            if resolved:
                vals["resolved_date"] = resolved
            upsert(xmlid, "crm.service.complaint.ticket", vals)

        lost_price = upsert("demo_lost_reason_price", "crm.lost.reason", {"name": "Giá chưa phù hợp ngân sách"})
        lost_timeline = upsert("demo_lost_reason_timeline", "crm.lost.reason", {"name": "Tiến độ giao hàng chưa phù hợp"})
        lost_competitor = upsert("demo_lost_reason_competitor", "crm.lost.reason", {"name": "Khách chọn nhà cung cấp khác"})
        lost_rows = [
            ("demo_lost_hoa_tien", leads["demo_lead_hoa_tien"], lost_price, 120000000, "2026-04-13 09:45:00", "Khách tạm hoãn do ngân sách quý này.", 3),
            ("demo_lost_lotus", leads["demo_lead_lotus"], lost_timeline, 74000000, "2026-02-28 16:20:00", "Khách phản hồi quá muộn so với kế hoạch đặt hàng.", 2),
            ("demo_lost_sao_mai", leads["demo_lead_sao_mai"], lost_competitor, 165000000, "2026-04-19 09:15:00", "Khách chọn nhà cung cấp có lịch giao nhanh hơn.", 2),
        ]
        for xmlid, lead, reason, revenue, lost_date, fail_reason, score in lost_rows:
            lead.write({"lost_reason_id": reason.id, "fail_reason": fail_reason, "satisfaction_score": score})
            upsert(xmlid, "crm.lost.reason.analytics", {
                "lead_id": lead.id,
                "lead_name": lead.name,
                "lost_reason_id": reason.id,
                "user_id": admin.id,
                "expected_revenue": revenue,
                "lost_date": lost_date,
            })

        campaign_rows = [
            ("demo_campaign_followup_quote", "Theo dõi khách đã nhận báo giá tháng 5", template("template_followup_email_vn"), "medium", "quotation", "high", sources["trade_fair"], "scheduled", True, "2026-05-30 08:30:00", [partners["demo_partner_binh_minh"], partners["demo_partner_blue_ocean"], partners["demo_partner_hung_vuong"]], "retention"),
            ("demo_campaign_welcome_new", "Chào mừng khách mới từ website VINATEX", template("template_welcome_email_vn"), "low", "new", "medium", sources["website"], "draft", False, False, [partners["demo_partner_mekong_sport"], partners["demo_partner_minh_chau"], partners["demo_partner_hoa_binh"]], "upsell"),
            ("demo_campaign_winback", "Chăm sóc lại khách hàng lâu chưa tương tác", template("template_remarketing_email_vn"), "dormant", "dormant", "low", sources["email"], "scheduled", True, "2026-06-03 09:00:00", [partners["demo_partner_green_line"], partners["demo_partner_lotus"], partners["demo_partner_dai_phat"]], "winback"),
            ("demo_campaign_loyalty", "Tri ân khách hàng giá trị cao", template("template_vip_priority_offer_vn"), "high", "won", "high", sources["referral"], "sent", True, "2026-05-24 09:15:00", [partners["demo_partner_hai_dang"], partners["demo_partner_an_phu"], partners["demo_partner_an_khang"]], "loyalty"),
            ("demo_campaign_material_update", "Cập nhật năng lực vật liệu mới", template("template_subscription_email_vn"), "medium", "contacted", "medium", sources["email"], "draft", False, False, [partners["demo_partner_tan_phat"], partners["demo_partner_van_xuan"], partners["demo_partner_thanh_dat"]], "upsell"),
            ("demo_campaign_sample_trial", "Mời duyệt mẫu sản xuất thử", template("template_promotion_sample_vn"), "medium", "quotation", "high", sources["trade_fair"], "scheduled", True, "2026-06-04 14:00:00", [partners["demo_partner_phu_thinh"], partners["demo_partner_bao_ngoc"], partners["demo_partner_hung_vuong"]], "retention"),
            ("demo_campaign_thank_you", "Cảm ơn sau buổi trao đổi khách hàng", template("template_thank_you_after_meeting_vn"), "high", "negotiation", "high", sources["referral"], "draft", False, False, [partners["demo_partner_an_phu"], partners["demo_partner_bao_ngoc"], partners["demo_partner_van_xuan"]], "loyalty"),
            ("demo_campaign_risk_retention", "Giữ chân khách hàng có nguy cơ rời bỏ", template("template_retention_risk_vn"), "dormant", "dormant", "medium", sources["email"], "scheduled", True, "2026-06-06 09:30:00", [partners["demo_partner_green_line"], partners["demo_partner_dai_phat"], partners["demo_partner_lotus"]], "winback"),
        ]

        campaigns = {}
        for xmlid, name, tmpl, segment, status, potential, source, state, approved, scheduled, recipients, goal in campaign_rows:
            vals = {
                "name": name,
                "template_id": tmpl.id,
                "segment": segment,
                "customer_status": status,
                "potential_level": potential,
                "lead_source_id": source.id,
                "state": state,
                "approved": approved,
                "recipient_ids": [(6, 0, [partner.id for partner in recipients])],
                "personalization_goal": goal,
            }
            if scheduled:
                vals["scheduled_date"] = scheduled
            campaigns[xmlid] = upsert(xmlid, "custom.mail.campaign", vals)

        log_rows = [
            ("demo_mail_log_loyalty_hai_dang", campaigns["demo_campaign_loyalty"], partners["demo_partner_hai_dang"], "sent", False),
            ("demo_mail_log_loyalty_an_phu", campaigns["demo_campaign_loyalty"], partners["demo_partner_an_phu"], "sent", False),
            ("demo_mail_log_loyalty_an_khang", campaigns["demo_campaign_loyalty"], partners["demo_partner_an_khang"], "sent", False),
            ("demo_mail_log_followup_binh_minh", campaigns["demo_campaign_followup_quote"], partners["demo_partner_binh_minh"], "sent", False),
            ("demo_mail_log_followup_blue_ocean", campaigns["demo_campaign_followup_quote"], partners["demo_partner_blue_ocean"], "sent", False),
            ("demo_mail_log_followup_hung_vuong", campaigns["demo_campaign_followup_quote"], partners["demo_partner_hung_vuong"], "failed", "Môi trường demo chưa cấu hình máy chủ gửi email thật."),
            ("demo_mail_log_sample_phu_thinh", campaigns["demo_campaign_sample_trial"], partners["demo_partner_phu_thinh"], "sent", False),
            ("demo_mail_log_risk_dai_phat", campaigns["demo_campaign_risk_retention"], partners["demo_partner_dai_phat"], "sent", False),
        ]
        for xmlid, campaign, partner, status, error in log_rows:
            upsert(xmlid, "custom.mail.log", {
                "campaign_id": campaign.id,
                "partner_id": partner.id,
                "email_to": partner.email,
                "sent_date": "2026-05-24 09:30:00",
                "status": status,
                "error_message": error,
            })

        workflow_rows = [
            ("demo_workflow_new", "Lead mới: phản hồi trong ngày", 1, stage_new, 1, "Gọi xác nhận nhu cầu và cập nhật đủ dữ liệu lead.", "Tạo hồ sơ CSKH đầu tiên, xác nhận sản phẩm, số lượng, thời gian giao hàng.", True),
            ("demo_workflow_proposal", "Đã gửi báo giá: theo dõi sau 2 ngày", 2, stage_proposal, 2, "Theo dõi phản hồi báo giá.", "Kiểm tra khách đã nhận đủ báo giá, mẫu vải, bảng size và điều khoản giao hàng.", True),
            ("demo_workflow_negotiation", "Đang thương lượng: ưu tiên phản hồi", 3, stage_negotiation, 1, "Cập nhật điều khoản và phản hồi trong 24h.", "Theo dõi thay đổi giá, tiến độ, điều khoản thanh toán và rủi ro mất cơ hội.", False),
            ("demo_workflow_won", "Đã chốt: chăm sóc sau bán", 4, stage_won, 7, "Gửi thư cảm ơn và tạo lịch chăm sóc sau bán.", "Xác nhận đầu mối sản xuất, lịch cập nhật tiến độ và mức độ hài lòng.", True),
            ("demo_workflow_dormant", "Lâu chưa tương tác: chăm sóc lại", 5, stage_dormant, 3, "Gọi hoặc gửi email chăm sóc lại khách hàng.", "Xác định lý do im lặng, cập nhật nhu cầu mới và đề xuất bước tiếp theo.", True),
        ]
        for xmlid, name, seq, stage, days, next_action, content, send_email in workflow_rows:
            upsert(xmlid, "crm.cskh.workflow.rule", {
                "name": name,
                "sequence": seq,
                "stage_id": stage.id,
                "followup_days": days,
                "next_action": next_action,
                "content": content,
                "send_email": send_email,
            })

        approval_rows = [
            ("demo_approval_merge_an_phu", "merge", leads["demo_lead_an_phu"], leads["demo_lead_an_phu_duplicate"], "Lead chi nhánh Quảng Nam có số điện thoại trùng với An Phú, cần kiểm tra trước khi gộp.", "submitted", "2026-05-28 10:20:00", False),
            ("demo_approval_delete_lotus", "delete", leads["demo_lead_lotus"], False, "Khách lâu chưa tương tác, cần phê duyệt trước khi xóa khỏi dữ liệu vận hành.", "approved", "2026-05-20 11:00:00", "2026-05-21 08:45:00"),
            ("demo_approval_merge_blue_ocean", "merge", leads["demo_lead_blue_ocean"], leads["demo_lead_song_han"], "Hai lead cùng nhóm đồng phục khách sạn, cần quản lý xác nhận không gộp nhầm.", "rejected", "2026-05-25 14:10:00", False),
            ("demo_approval_merge_bao_ngoc", "merge", leads["demo_lead_bao_ngoc"], leads["demo_lead_van_xuan"], "Hai hồ sơ cùng yêu cầu màu in và kiểm định vải, cần rà soát trước khi gộp dữ liệu.", "submitted", "2026-05-28 14:35:00", False),
            ("demo_approval_delete_sao_mai", "delete", leads["demo_lead_sao_mai"], False, "Cơ hội đã thất bại nhưng vẫn cần giữ lịch sử chăm sóc để phân tích nguyên nhân.", "rejected", "2026-05-22 16:00:00", False),
        ]
        for xmlid, request_type, lead, duplicate, reason, state, requested, approved in approval_rows:
            vals = {
                "request_type": request_type,
                "lead_id": lead.id,
                "duplicate_lead_id": duplicate.id if duplicate else False,
                "requester_id": admin.id,
                "manager_id": admin.id if state in ("approved", "rejected") else False,
                "requested_date": requested,
                "state": state,
                "reason": reason,
                "decision_note": "Dữ liệu demo phục vụ kiểm soát chất lượng CRM.",
            }
            if approved:
                vals["approved_date"] = approved
            upsert(xmlid, "crm.lead.data.approval", vals)

        retention_rows = [
            ("demo_retention_hai_dang", partners["demo_partner_hai_dang"], 4, 1150000000, True, "Khách hàng thân thiết", 75.0),
            ("demo_retention_an_phu", partners["demo_partner_an_phu"], 3, 820000000, True, "Khách hàng thân thiết", 66.67),
            ("demo_retention_binh_minh", partners["demo_partner_binh_minh"], 2, 460000000, True, "Khách hàng quay lại", 50.0),
            ("demo_retention_green_line", partners["demo_partner_green_line"], 1, 180000000, False, "Có nguy cơ rời bỏ", 0.0),
            ("demo_retention_lotus", partners["demo_partner_lotus"], 1, 74000000, False, "Lâu chưa tương tác", 0.0),
            ("demo_retention_an_khang", partners["demo_partner_an_khang"], 5, 980000000, True, "Khách hàng thân thiết", 80.0),
            ("demo_retention_hung_vuong", partners["demo_partner_hung_vuong"], 3, 830000000, True, "Khách hàng quay lại", 66.67),
            ("demo_retention_phu_thinh", partners["demo_partner_phu_thinh"], 2, 610000000, True, "Khách hàng quay lại", 50.0),
            ("demo_retention_dai_phat", partners["demo_partner_dai_phat"], 1, 205000000, False, "Có nguy cơ rời bỏ", 0.0),
            ("demo_retention_hoa_binh", partners["demo_partner_hoa_binh"], 2, 575000000, True, "Khách hàng quay lại", 50.0),
        ]
        for xmlid, partner, orders, revenue, returning, status, rate in retention_rows:
            upsert(xmlid, "crm.customer.retention.analytics", {
                "customer_id": partner.id,
                "total_orders": orders,
                "total_revenue": revenue,
                "is_returning_customer": returning,
                "retention_status": status,
                "retention_rate": rate,
            })

        for partner in partners.values():
            partner._compute_crm_personalization_metrics()
            partner._compute_loyalty_profile()

        return True

    def _localize_existing_odoo_demo_leads(self, env, admin, country_vn, sources, stages):
        rows = [
            ("Club Office Furnitures", "Nhu cầu đồng phục văn phòng - Lê Club", "Công ty Thương mại Lê Club", "Đỗ Nhật Duy", "duy@leclub.vn", "+84 24 3200 1001", stages["new"], 85000000, 12, "Khách hỏi mẫu đồng phục văn phòng, cần xác nhận chất liệu và số lượng."),
            ("Design Software", "Tư vấn áo thun sự kiện - Dầu khí An Bình", "Công ty Dầu khí An Bình", "Mai Đức Minh", "minh@anbinh-oil.vn", "+84 28 3200 1002", stages["new"], 120000000, 18, "Khách cần áo thun sự kiện cho hội nghị nội bộ."),
            ("Pricing for 25 desks", "Báo giá đồng phục quản lý - Kompany Việt", "Công ty Kompany Việt", "Nguyễn Thị Hạnh", "hanh@kompany.vn", "+84 236 3200 1003", stages["new"], 95000000, 16, "Khách cần đồng phục quản lý cho chi nhánh mới."),
            ("Campbell: Chairs", "Đồng phục nhân sự bán hàng - Burstein Việt Nam", "Công ty Burstein Việt Nam", "Hồ Minh Châu", "chau@burstein.vn", "+84 28 3200 1004", stages["new"], 110000000, 20, "Khách cần mẫu áo sơ mi và quần tây cho đội bán hàng."),
            ("Quotation for 50 Chairs", "Báo giá áo khoác nhân viên - Sao Nam IT", "Công ty Sao Nam IT", "Hà Lê", "ha@saonamit.vn", "+84 24 3200 1005", stages["new"], 135000000, 22, "Khách cần áo khoác nhẹ cho nhân sự kỹ thuật."),
            ("Opensides: Need Info", "Tư vấn năng lực may mặc - Mở Rộng Việt", "Công ty Mở Rộng Việt", "Trịnh Tú Anh", "anh@morongviet.vn", "+84 236 3200 1006", stages["new"], 76000000, 10, "Khách cần hồ sơ năng lực và danh mục sản phẩm dệt may."),
            ("Gardner: Desks Replacement", "Thay mới đồng phục bảo trì - Gia Định", "Công ty Gia Định", "Lê Quang Huy", "huy@giadinh.vn", "+84 28 3200 1007", stages["new"], 98000000, 12, "Khách cần thay đồng phục bảo trì cũ bằng mẫu mới bền hơn."),
            ("Product Catalog", "Gửi danh mục sản phẩm - Chuyên Gia ESM", "Công ty Chuyên Gia ESM", "Lương Gia Hân", "han@esmexpert.vn", "+84 24 3200 1008", stages["new"], 64000000, 8, "Khách yêu cầu danh mục sản phẩm và bảng chất liệu tham khảo."),
            ("Reseller: Office furnitures", "Hợp tác phân phối đồng phục - Minh Phát", "Công ty Minh Phát", "Đặng Quốc Bảo", "bao@minhphat.vn", "+84 236 3200 1009", stages["new"], 150000000, 18, "Khách muốn phân phối đồng phục doanh nghiệp tại miền Trung."),
            ("Design Software Info", "Tư vấn áo polo nhân viên - Năng lượng Mặt Trời", "Công ty Năng lượng Mặt Trời", "Trần Gia Anh", "anh@nangluongmattroi.vn", "+84 28 3200 1010", stages["new"], 88000000, 14, "Khách hỏi áo polo cho đội kỹ thuật lắp đặt."),
            ("Estimation for Office Furnitures", "Dự toán đồng phục văn phòng - Á Châu", "Công ty Á Châu", "Bùi Hữu An", "an@achau.vn", "+84 24 3200 1011", stages["new"], 132000000, 20, "Khách cần dự toán đồng phục cho văn phòng 120 nhân sự."),
            ("Quotation for 100 Desks", "Báo giá đồng phục sản xuất - Incom Việt Nam", "Công ty Incom Việt Nam", "Vũ Hoàng Long", "long@incom.vn", "+84 236 3200 1012", stages["new"], 175000000, 25, "Khách cần báo giá đồng phục xưởng sản xuất."),
            ("Quote for 12 Tables", "Báo giá khăn dệt khách sạn - Rediff Việt", "Công ty Rediff Việt", "Lê Mỹ Linh", "linh@rediff.vn", "+84 28 3200 1013", stages["proposal"], 210000000, 45, "Đã gửi báo giá khăn dệt cho chuỗi khách sạn."),
            ("Office Design Project", "Dự án đồng phục văn phòng - Á Châu", "Công ty Á Châu", "Bùi Hữu An", "an@achau.vn", "+84 24 3200 1014", stages["proposal"], 320000000, 50, "Khách đang so sánh phương án đồng phục văn phòng cao cấp."),
            ("Info about services", "Tư vấn dịch vụ may trọn gói - Á Châu", "Công ty Á Châu", "Bùi Hữu An", "an@achau.vn", "+84 24 3200 1015", stages["qualified"], 240000000, 42, "Đã xác nhận nhu cầu dịch vụ may trọn gói cho nhân viên mới."),
            ("Global Solutions: Furnitures", "Đồng phục kỹ thuật - Giải pháp Toàn Cầu", "Công ty Giải pháp Toàn Cầu", "Trần Minh Khoa", "khoa@giaiphaptoancau.vn", "+84 236 3200 1016", stages["qualified"], 260000000, 44, "Khách cần đồng phục kỹ thuật có phản quang."),
            ("Balmer Inc: Potential Distributor", "Nhà phân phối tiềm năng - Bảo Minh", "Công ty Bảo Minh", "Phạm Đức Vinh", "vinh@baominh.vn", "+84 28 3200 1017", stages["qualified"], 190000000, 38, "Đã xác nhận nhu cầu hợp tác phân phối sản phẩm đồng phục."),
            ("DeltaPC: 10 Computer Desks", "Đồng phục bộ phận công nghệ - Delta Việt", "Công ty Delta Việt", "Ngô Hải Nam", "nam@delta-viet.vn", "+84 24 3200 1018", stages["qualified"], 170000000, 36, "Khách cần đồng phục cho bộ phận công nghệ thông tin."),
            ("Customizable Desk", "Thiết kế mẫu đồng phục riêng - Vạn Phúc", "Công ty Vạn Phúc", "Lý Thu Trang", "trang@vanphuc.vn", "+84 236 3200 1019", stages["proposal"], 360000000, 58, "Đã gửi đề xuất thiết kế đồng phục theo bộ nhận diện."),
            ("Distributor Contract", "Hợp đồng phân phối đồng phục - Công nghệ Epic Việt", "Công ty Công nghệ Epic Việt", "John Bảo", "bao@epictech.vn", "+84 28 3200 1020", stages["won"], 520000000, 100, "Đã chốt hợp đồng phân phối đồng phục doanh nghiệp."),
            ("Office Design and Architecture", "Đồng phục kiến trúc sư - Ready Mat Việt", "Công ty Ready Mat Việt", "Nguyễn Hoàng Long", "long@readymat.vn", "+84 24 3200 1021", stages["proposal"], 410000000, 62, "Đã gửi báo giá đồng phục cho đội kiến trúc sư và giám sát."),
            ("5 VP Chairs", "Đồng phục quản lý cấp cao - Nebula Việt", "Công ty Nebula Việt", "Đặng Minh Phương", "phuong@nebula.vn", "+84 236 3200 1022", stages["proposal"], 145000000, 48, "Khách cần mẫu đồng phục quản lý cấp cao."),
            ("Access to Online Catalog", "Truy cập danh mục sản phẩm - Gỗ Việt", "Công ty Gỗ Việt", "Lâm Quốc Việt", "viet@goviet.vn", "+84 28 3200 1023", stages["won"], 99000000, 100, "Khách đã đồng ý dùng danh mục sản phẩm VINATEX cho đơn đặt thử."),
            ("Need 20 Desks", "Nhu cầu 20 bộ đồng phục mẫu", "Khách hàng đồng phục mẫu", "Phạm Hải Yến", "yen@khachhangmau.vn", "+84 24 3200 1024", stages["proposal"], 68000000, 40, "Khách cần 20 bộ đồng phục mẫu để duyệt nội bộ."),
            ("Modern Open Space", "Đồng phục nhà máy mới - Ánh Sáng", "Công ty Ánh Sáng", "Henry Hưng", "hung@anhsang.vn", "+84 236 3200 1025", stages["proposal"], 300000000, 54, "Khách chuẩn bị mở nhà máy mới và cần đồng phục đồng bộ."),
            ("Open Space Design", "Thiết kế đồng phục không gian mở - Á Châu", "Công ty Á Châu", "Bùi Hữu An", "an@achau.vn", "+84 24 3200 1026", stages["proposal"], 220000000, 52, "Khách cần mẫu đồng phục thoải mái cho văn phòng mở."),
            ("Interest in your products", "Quan tâm sản phẩm may mặc - Á Châu", "Công ty Á Châu", "Bùi Hữu An", "an@achau.vn", "+84 24 3200 1027", stages["won"], 180000000, 100, "Khách đã xác nhận đặt thử dòng áo polo doanh nghiệp."),
            ("Furnish a 60m² office", "Đồng phục văn phòng nhỏ - Á Châu", "Công ty Á Châu", "Bùi Hữu An", "an@achau.vn", "+84 24 3200 1028", stages["new"], 54000000, 8, "Khách hỏi đồng phục cho văn phòng nhỏ, đang chờ phản hồi."),
            ("Club Office More Desks", "Bổ sung đồng phục văn phòng - Lê Club", "Công ty Thương mại Lê Club", "Đỗ Nhật Duy", "duy@leclub.vn", "+84 24 3200 1029", stages["qualified"], 97000000, 35, "Khách muốn đặt bổ sung đồng phục cho nhân sự mới."),
            ("Acadia College Furnitures", "Đồng phục trường học - Cao đẳng Acadia", "Trường Cao đẳng Acadia", "Gaston Nguyễn", "nguyen@acadia.vn", "+84 236 3200 1030", stages["new"], 230000000, 18, "Trường cần đồng phục cho sinh viên khóa mới."),
            ("Quote for 150 carpets", "Báo giá 150 áo polo sự kiện", "Công ty Sự kiện Việt", "Erik Phúc", "phuc@sukienviet.vn", "+84 28 3200 1031", stages["proposal"], 88000000, 42, "Đã gửi báo giá áo polo sự kiện số lượng 150."),
            ("Quote for 600 Chairs", "Báo giá 600 áo khoác đồng phục", "Công ty Sự kiện Việt", "Erik Phúc", "phuc@sukienviet.vn", "+84 28 3200 1032", stages["qualified"], 260000000, 45, "Khách cần áo khoác đồng phục cho chương trình ngoài trời."),
            ("Recurring delivery contract", "Hợp đồng giao hàng định kỳ", "Công ty Dịch vụ Hậu cần Việt", "Max Minh", "minh@haucanviet.vn", "+84 24 3200 1033", stages["qualified"], 340000000, 50, "Khách muốn ký hợp đồng giao đồng phục định kỳ theo quý."),
            ("Need info about pricing", "Cần thông tin bảng giá", "Công ty Giá Trị Việt", "An Kreda", "ankreda@giatriviet.vn", "+84 236 3200 1034", stages["proposal"], 125000000, 40, "Khách cần bảng giá theo từng nhóm sản phẩm."),
            ("Trelian New Offices", "Đồng phục văn phòng mới - Ảnh Việt", "Công ty Ảnh Việt", "Roxana Thảo", "thao@anhviet.vn", "+84 28 3200 1035", stages["qualified"], 155000000, 36, "Khách mở văn phòng mới và cần đồng phục nhận diện."),
            ("Branded Furniture", "Đồng phục nhận diện thương hiệu", "Công ty Nhận diện Việt", "Mạnh Lim", "lim@nhandienviet.vn", "+84 24 3200 1036", stages["qualified"], 195000000, 44, "Khách cần đồng phục theo bộ nhận diện mới."),
            ("Design New Shelves", "Thiết kế mẫu áo khoác mới - Gia Lộc", "Công ty Gia Lộc", "An Khánh", "khanh@gialoc.vn", "+84 236 3200 1037", stages["qualified"], 175000000, 34, "Khách cần mẫu áo khoác mới cho nhân viên kho."),
            ("Office chairs", "Đồng phục văn phòng - Sao Biển", "Công ty Sao Biển", "Hoàng Jobbins", "hoang@saobien.vn", "+84 28 3200 1038", stages["qualified"], 105000000, 28, "Khách cần đồng phục văn phòng đơn giản, dễ bảo quản."),
            ("Cleaning subscription", "Đồng phục đội vệ sinh định kỳ - Sạch Việt", "Công ty Sạch Việt", "Elen Espin", "elen@sachviet.vn", "+84 24 3200 1039", stages["new"], 115000000, 20, "Khách cần đồng phục cho đội vệ sinh theo hợp đồng định kỳ."),
            ("Custom Desks (100 pieces)", "Đồng phục đặt riêng 100 bộ - Mộc Xưởng", "Công ty Mộc Xưởng", "Cường Redford", "cuong@mocxuong.vn", "+84 236 3200 1040", stages["qualified"], 142000000, 32, "Khách cần 100 bộ đồng phục đặt riêng cho xưởng."),
            ("Need a price: urgent", "Cần báo giá gấp - Skibox Việt", "Công ty Skibox Việt", "Khánh Kirvell", "khanh@skibox.vn", "+84 28 3200 1041", stages["proposal"], 92000000, 38, "Khách cần báo giá gấp cho đồng phục sự kiện cuối tháng."),
            ("Furnitures for new location", "Đồng phục cho địa điểm mới - Twin Việt", "Công ty Twin Việt", "Ngọc Grabert", "ngoc@twinviet.vn", "+84 24 3200 1042", stages["qualified"], 185000000, 42, "Khách mở địa điểm mới và cần đồng phục cho đội vận hành."),
            ("Modernize old offices", "Làm mới đồng phục văn phòng - Ý Việt", "Công ty Ý Việt", "Phương Seiller", "phuong@yviet.vn", "+84 236 3200 1043", stages["proposal"], 160000000, 45, "Khách muốn làm mới đồng phục văn phòng cũ."),
            ("Quote for 35 windows", "Báo giá 35 bộ đồng phục mẫu - Gạch Việt", "Công ty Gạch Việt", "Trọng Brock", "trong@gachviet.vn", "+84 28 3200 1044", stages["proposal"], 52000000, 35, "Khách cần 35 bộ đồng phục mẫu để kiểm tra chất lượng."),
        ]

        Partner = env["res.partner"].sudo()
        Lead = env["crm.lead"].with_context(active_test=False).sudo()
        for old_name, new_name, company, contact, email, phone, stage, revenue, probability, requirement in rows:
            lead = Lead.search(["|", ("name", "=", old_name), ("name", "=", new_name)], limit=1)
            if not lead:
                continue
            demo_website = "https://vinatex-crm.vn/khach-hang-mau"
            partner = lead.partner_id or Partner.search([("email", "=", email)], limit=1)
            if not partner:
                partner = Partner.create({
                    "name": company,
                    "company_type": "company",
                    "website": demo_website,
                    "country_id": country_vn.id if country_vn else False,
                })
            partner.write({
                "name": company,
                "company_type": "company",
                "function": contact,
                "email": email,
                "phone": phone,
                "website": demo_website,
                "country_id": country_vn.id if country_vn else False,
                "lead_source_id": sources["website"].id,
                "crm_estimated_revenue": revenue,
                "personalization_note": "Dữ liệu mẫu đã được Việt hóa để phù hợp bối cảnh VINATEX CRM.",
            })
            lead.write({
                "name": new_name,
                "partner_id": partner.id,
                "partner_name": company,
                "contact_name": contact,
                "email_from": email,
                "phone": phone,
                "website": demo_website,
                "source_id": sources["website"].id,
                "user_id": admin.id,
                "stage_id": stage.id,
                "expected_revenue": revenue,
                "probability": probability,
                "initial_product_requirement": requirement,
                "description": requirement,
                "last_interaction_date": "2026-05-20",
            })


def revenue_by_lead(lead):
    revenue = lead.expected_revenue or 0
    if revenue >= 800000000:
        return 35000
    if revenue >= 400000000:
        return 22000
    if revenue >= 200000000:
        return 12000
    return 5000
