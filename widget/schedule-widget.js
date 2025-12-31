(function () {
  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    attrs = attrs || {};
    Object.keys(attrs).forEach(function (k) {
      if (k === "style") {
        Object.assign(node.style, attrs[k]);
      } else if (k === "class") {
        node.className = attrs[k];
      } else {
        node.setAttribute(k, attrs[k]);
      }
    });
    (children || []).forEach(function (c) {
      if (typeof c === "string") node.appendChild(document.createTextNode(c));
      else node.appendChild(c);
    });
    return node;
  }

  async function fetchClasses(baseUrl, startDate, endDate) {
    var url =
      baseUrl.replace(/\/+$/, "") +
      "/api/classes?start_date=" +
      encodeURIComponent(startDate) +
      "&end_date=" +
      encodeURIComponent(endDate);
    var r = await fetch(url, { headers: { Accept: "application/json" } });
    if (!r.ok) {
      var t = await r.text();
      throw new Error("API error " + r.status + ": " + t);
    }
    return await r.json();
  }

  function render(container, items) {
    container.innerHTML = "";

    var header = el("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center" } }, [
      el("div", { style: { fontWeight: "600" } }, ["Расписание"]),
      el("div", { style: { fontSize: "12px", opacity: "0.7" } }, ["Обновлено: " + new Date().toLocaleString()]),
    ]);

    var list = el("div", { style: { display: "grid", gap: "10px", marginTop: "12px" } }, []);

    if (!items.length) {
      list.appendChild(el("div", { style: { padding: "12px", border: "1px solid #eee", borderRadius: "12px" } }, ["Нет занятий в выбранном периоде."]));
    } else {
      items.forEach(function (it) {
        var badge = it.canceled ? "Отменено" : it.online ? "Онлайн" : "";
        var badgeColor = it.canceled ? "#b91c1c" : "#111827";

        list.appendChild(
          el(
            "div",
            {
              style: {
                padding: "12px",
                border: "1px solid #eee",
                borderRadius: "12px",
                background: "#fff",
              },
            },
            [
              el("div", { style: { display: "flex", gap: "8px", alignItems: "baseline" } }, [
                el("div", { style: { fontWeight: "650" } }, [String(it.title || "Занятие")]),
                badge
                  ? el(
                      "span",
                      {
                        style: {
                          fontSize: "12px",
                          padding: "2px 8px",
                          borderRadius: "999px",
                          border: "1px solid #eee",
                          color: badgeColor,
                        },
                      },
                      [badge]
                    )
                  : el("span", {}, [""]),
              ]),
              el("div", { style: { marginTop: "6px", fontSize: "13px", opacity: "0.85" } }, [
                "Время: " + String(it.start_date || "?") + " — " + String(it.end_date || "?"),
              ]),
              el("div", { style: { marginTop: "4px", fontSize: "13px", opacity: "0.85" } }, [
                "Зал: " + String((it.room && it.room.title) || "—") + " · Тренер: " + String((it.employee && it.employee.name) || "—"),
              ]),
            ]
          )
        );
      });
    }

    container.appendChild(header);
    container.appendChild(list);
  }

  async function init() {
    var nodes = document.querySelectorAll("[data-onec-schedule]");
    if (!nodes.length) return;

    for (var i = 0; i < nodes.length; i++) {
      var n = nodes[i];
      var apiBase = n.getAttribute("data-api-base") || "";
      var startDate = n.getAttribute("data-start-date") || "";
      var endDate = n.getAttribute("data-end-date") || "";

      n.style.fontFamily = "system-ui, -apple-system, Segoe UI, Roboto, Arial";
      n.style.maxWidth = n.style.maxWidth || "920px";

      if (!apiBase || !startDate || !endDate) {
        n.textContent = "Виджет: не заданы data-api-base / data-start-date / data-end-date";
        continue;
      }

      n.textContent = "Загрузка расписания...";
      try {
        var items = await fetchClasses(apiBase, startDate, endDate);
        render(n, items);
      } catch (e) {
        n.textContent = "Ошибка загрузки: " + (e && e.message ? e.message : String(e));
      }
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();


