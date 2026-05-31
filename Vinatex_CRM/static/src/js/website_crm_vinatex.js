(function () {
  function initWebsiteCrmVinatex() {
    const root = document.querySelector("#website-crm-vinatex");
    if (!root) return;

    const panels = root.querySelectorAll("[data-panel]");
    const buttons = root.querySelectorAll("[data-panel-target]");

    function activate(panelId) {
      panels.forEach((panel) => panel.classList.toggle("active", panel.dataset.panel === panelId));
      buttons.forEach((button) => button.classList.toggle("active", button.dataset.panelTarget === panelId));
      if (window.location.hash !== `#${panelId}`) {
        history.replaceState(null, "", `#${panelId}`);
      }
    }

    const normalize = (value) =>
      (value || "")
        .toString()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .toLowerCase()
        .trim();

    const keywordPanels = [
      { keys: ["lead", "co hoi", "khach hang"], panel: "lead" },
      { keys: ["cskh", "cham soc"], panel: "cskh" },
      { keys: ["campaign", "chien dich", "loyalty", "email"], panel: "campaign" },
      { keys: ["khieu nai", "dich vu", "complaint"], panel: "khieu-nai" },
      { keys: ["phan tich", "bao cao"], panel: "phan-tich" },
      { keys: ["kiem soat", "du lieu", "trung"], panel: "kiem-soat" },
    ];

    function panelFromKeyword(query) {
      const found = keywordPanels.find((item) => item.keys.some((key) => query.includes(key)));
      return found && root.querySelector(`[data-panel="${found.panel}"]`) ? found.panel : null;
    }

    buttons.forEach((button) => {
      button.addEventListener("click", (event) => {
        event.preventDefault();
        activate(button.dataset.panelTarget);
      });
    });

    const initial = (window.location.hash || "#tong-quan").slice(1);
    activate(root.querySelector(`[data-panel="${initial}"]`) ? initial : "tong-quan");

    const searchInput = root.querySelector("[data-crm-search]");
    const searchClear = root.querySelector("[data-search-clear]");
    const searchStatus = root.querySelector("[data-search-status]");
    const searchItems = Array.from(root.querySelectorAll("[data-search-item]"));

    function updateSearch() {
      const query = normalize(searchInput.value);
      let matchCount = 0;
      let firstMatchPanel = null;

      searchItems.forEach((item) => {
        const isMatch = !query || normalize(item.textContent).includes(query);
        item.classList.toggle("wv-search-hidden", !isMatch);
        if (query && isMatch) {
          matchCount += 1;
          firstMatchPanel = firstMatchPanel || item.closest("[data-panel]")?.dataset.panel;
        }
      });

      if (searchClear) {
        searchClear.hidden = !query;
      }
      if (searchStatus) {
        searchStatus.textContent = query ? (matchCount ? `${matchCount} kết quả` : "Không có kết quả") : "";
      }
      if (query) {
        const panelId = panelFromKeyword(query) || firstMatchPanel;
        if (panelId) {
          activate(panelId);
        }
      }
    }

    if (searchInput) {
      searchInput.addEventListener("input", updateSearch);
      searchInput.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
          searchInput.value = "";
          updateSearch();
        }
      });
    }
    if (searchClear) {
      searchClear.addEventListener("click", () => {
        searchInput.value = "";
        searchInput.focus();
        updateSearch();
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initWebsiteCrmVinatex);
  } else {
    initWebsiteCrmVinatex();
  }
})();
