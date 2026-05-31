/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class CrmTongHopDashboard extends Component {
    setup() {
        this.action = useService("action");
        this.rpc = useService("rpc");
        this.state = useState({
            loading: true,
            data: {},
        });

        onWillStart(async () => {
            this.state.data = await this.rpc("/crm_tong_hop/dashboard/data", {});
            this.state.loading = false;
        });
    }

    openAction(xmlId) {
        this.action.doAction(xmlId);
    }
}

CrmTongHopDashboard.template = "crm_tong_hop.Dashboard";

registry.category("actions").add("crm_tong_hop.dashboard", CrmTongHopDashboard);
