/** @odoo-module **/

const TEXT_REPLACEMENTS = new Map([
    ["New", "Mới"],
    ["Generate Leads", "Tạo lead tự động"],
    ["Convert to Opportunity", "Chuyển thành cơ hội"],
    ["Lost", "Thất bại"],
    ["Won", "Thành công"],
    ["Opportunity", "Lead / cơ hội"],
    ["Expected Revenue", "Doanh thu kỳ vọng"],
    ["Stage", "Giai đoạn"],
    ["Probability", "Xác suất"],
    ["Customer", "Khách hàng"],
    ["Address", "Địa chỉ"],
    ["Sales Team", "Nhóm kinh doanh"],
    ["Internal Notes", "Ghi chú nội bộ"],
    ["Extra Info", "Thông tin bổ sung"],
    ["Extra Information", "Thông tin bổ sung"],
    ["Job Position", "Chức vụ"],
    ["Mobile", "Di động"],
    ["Priority", "Mức ưu tiên"],
    ["Tags", "Thẻ phân loại"],
]);

const PLACEHOLDER_REPLACEMENTS = new Map([
    ["e.g. Product Pricing", "VD: Báo giá đồng phục công sở"],
    ["Add a description...", "Nhập ghi chú hoặc nhu cầu khách hàng..."],
    ["Street...", "Địa chỉ..."],
    ["Street 2...", "Địa chỉ bổ sung..."],
    ["City", "Thành phố"],
    ["State", "Tỉnh/Thành"],
    ["ZIP", "Mã bưu chính"],
    ["Country", "Quốc gia"],
    ["Title", "Xưng danh"],
]);

function replaceTextNodes(root) {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes = [];
    let node = walker.nextNode();
    while (node) {
        nodes.push(node);
        node = walker.nextNode();
    }
    for (const textNode of nodes) {
        const raw = textNode.nodeValue || "";
        const trimmed = raw.trim();
        const replacement = TEXT_REPLACEMENTS.get(trimmed);
        if (replacement) {
            textNode.nodeValue = raw.replace(trimmed, replacement);
        }
    }
}

function replaceAttributes(root) {
    const selector = "[placeholder], [title], [aria-label]";
    for (const el of root.querySelectorAll(selector)) {
        for (const attr of ["placeholder", "title", "aria-label"]) {
            const value = el.getAttribute(attr);
            if (!value) {
                continue;
            }
            if (PLACEHOLDER_REPLACEMENTS.has(value)) {
                el.setAttribute(attr, PLACEHOLDER_REPLACEMENTS.get(value));
            } else if (TEXT_REPLACEMENTS.has(value)) {
                el.setAttribute(attr, TEXT_REPLACEMENTS.get(value));
            }
        }
    }
}

function localizeBackend(root = document.body) {
    replaceTextNodes(root);
    replaceAttributes(root);
}

if (document.body) {
    localizeBackend();
    const observer = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
            for (const node of mutation.addedNodes) {
                if (node.nodeType === Node.ELEMENT_NODE) {
                    localizeBackend(node);
                } else if (node.nodeType === Node.TEXT_NODE) {
                    const trimmed = node.nodeValue.trim();
                    if (TEXT_REPLACEMENTS.has(trimmed)) {
                        node.nodeValue = node.nodeValue.replace(trimmed, TEXT_REPLACEMENTS.get(trimmed));
                    }
                }
            }
        }
    });
    observer.observe(document.body, { childList: true, subtree: true });
}
