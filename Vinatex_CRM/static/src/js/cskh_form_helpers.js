/** @odoo-module **/

import { notificationService } from "@web/core/notifications/notification_service";
import { patch } from "@web/core/utils/patch";

const CSKH_REQUIRED_LABELS = {
    lead_id: "Cơ hội",
    customer_id: "Khách hàng",
    interaction_type: "Loại tương tác",
    interaction_date: "Thời gian tương tác",
};

function getFieldWidget(form, fieldName) {
    return form.querySelector(
        `.o_field_widget[name="${fieldName}"], .o_field_widget[data-name="${fieldName}"]`
    );
}

function getInputValue(widget) {
    const input = widget.querySelector("input, textarea, select");
    return input ? input.value.trim() : widget.textContent.trim();
}

function getMissingCskhFields() {
    const form = document.querySelector(".o_form_view");
    if (!form) {
        return [];
    }

    const missing = [];
    for (const [fieldName, label] of Object.entries(CSKH_REQUIRED_LABELS)) {
        const widget = getFieldWidget(form, fieldName);
        if (!widget) {
            continue;
        }

        const isInvalid = widget.classList.contains("o_field_invalid");
        const isEmpty = !getInputValue(widget);
        if (isInvalid || isEmpty) {
            missing.push(label);
        }
    }
    return [...new Set(missing)];
}

function withMissingFields(message) {
    const missingFields = getMissingCskhFields();
    if (!missingFields.length) {
        return message;
    }
    return `${message}: ${missingFields.join(", ")}`;
}

patch(notificationService, {
    start(env, services) {
        const notification = super.start(env, services);
        const add = notification.add.bind(notification);

        notification.add = (message, options = {}) => {
            if (
                typeof message === "string" &&
                message.toLowerCase().includes("missing required fields")
            ) {
                return add(withMissingFields(message), options);
            }
            return add(message, options);
        };

        return notification;
    },
});

document.addEventListener(
    "click",
    (event) => {
        const button = event.target.closest(".o_cskh_discard_button");
        if (!button) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();

        const discardButton = document.querySelector(
            ".o_form_button_cancel, .o_form_button_discard"
        );
        if (discardButton && discardButton !== button) {
            discardButton.click();
        } else {
            window.history.back();
        }
    },
    true
);
