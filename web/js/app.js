/* Static frontend: displays web/data/metrics.js (exported from the reconciled database).
   No numbers are computed here except simple sums/ratios of the exported monthly table
   and the what-if arithmetic (src/scenario.py port, tested against Python). */
(function () {
  "use strict";
  var M = window.METRICS, S = window.Scenario;
  var $ = function (sel, root) { return (root || document).querySelector(sel); };
  var state = { period: "12m", partial: false, noUK: false, bridgeZero: false, price: 5, volume: 0, cost: 60 };
  var charts = {};

  /* ---------- formatting ---------- */
  function gbp(v, d) { d = d || 0; return (v < 0 ? "-" : "") + "£" + Math.abs(v).toLocaleString("en-GB", { minimumFractionDigits: d, maximumFractionDigits: d }); }
  function compact(v) { var a = Math.abs(v), s = a >= 1e6 ? (a / 1e6).toFixed(1) + "M" : a >= 1e3 ? Math.round(a / 1e3) + "k" : a.toFixed(0); return (v < 0 ? "-" : "") + "£" + s; }
  function monthLabel(ym) { var p = ym.split("-"); return ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][+p[1] - 1] + " " + p[0].slice(2); }
  function css(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function sum(rows, key) { return rows.reduce(function (a, r) { return a + r[key]; }, 0); }

  /* ---------- theme ---------- */
  function applyTheme(t) {
    document.documentElement.setAttribute("data-theme", t);
    document.querySelectorAll(".theme-icon").forEach(function (b) { b.setAttribute("aria-label", t === "dark" ? "Switch to light mode" : "Switch to dark mode"); });
    try { localStorage.setItem("lab-theme", t); } catch (e) {}
  }
  function initTheme() {
    var t = null; try { t = localStorage.getItem("lab-theme"); } catch (e) {}
    if (!t) t = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    applyTheme(t);
    function flip() {
      applyTheme(document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark"); renderAll();
    }
    document.querySelectorAll(".theme-icon").forEach(function (b) { b.addEventListener("click", flip); });
  }

  /* ---------- KPI cards ---------- */
  function kpiData() {
    var full = M.monthly.filter(function (m) { return !m.is_partial_month; });
    function agg(rows) {
      var gross = sum(rows, "gross_product_sales"), canc = sum(rows, "cancellation_value"), orders = sum(rows, "sales_invoices");
      return { net: gross + canc, gross: gross, canc: canc, orders: orders, aov: orders ? gross / orders : 0, rate: gross ? -canc / gross * 100 : 0 };
    }
    if (state.period === "all") {
      var k = M.kpis;
      return { cur: { net: k.net_product_revenue, gross: k.gross_product_sales, canc: k.cancellation_value, orders: k.sales_invoices, aov: k.avg_order_value, rate: k.cancellation_rate_pct },
               prev: null, label: "Whole period incl. 9 days of Dec 2011" };
    }
    var cur = full.slice(-12), prev = full.length >= 24 ? full.slice(-24, -12) : null;
    var prevRows = prev ? full.slice(-24, -12) : null;
    return { cur: agg(cur), prev: prev ? agg(prev) : null, label: monthLabel(cur[0].year_month) + " – " + monthLabel(cur[cur.length - 1].year_month),
             prevLabel: prevRows ? monthLabel(prevRows[0].year_month) + " – " + monthLabel(prevRows[prevRows.length - 1].year_month) : null };
  }
  function chip(delta, higherIsGood, unit) {
    var good = higherIsGood ? delta >= 0 : delta <= 0;
    var c = el("span", "chip " + (Math.abs(delta) < 0.05 ? "neutral" : good ? "good" : "bad"));
    c.textContent = (delta >= 0 ? "▲ " : "▼ ") + Math.abs(delta).toFixed(1) + unit; return c;
  }
  var KPI_DEFS = {
    net: "Gross product sales plus cancellations (credit notes count as negative). Postage, fees and stock adjustments are not included.",
    gross: "Quantity x unit price of normal sales lines. It still includes orders that were cancelled later.",
    canc: "Value of credit-note lines (negative). The % is cancellations divided by gross sales in the same period; credit notes cannot be linked to the original sale.",
    orders: "Invoices with at least one normal sales line. Credit notes are not counted.",
    aov: "Gross product sales divided by the number of invoices. Because gross sales include orders cancelled later, a net-based average would be lower."
  };
  function renderKpis() {
    var d = kpiData(), box = $("#kpis"); box.textContent = "";
    var items = [
      { key: "net", label: "Net product revenue", val: gbp(d.cur.net), hero: true, delta: d.prev && (d.cur.net / d.prev.net - 1) * 100, good: true, unit: "%" },
      { key: "gross", label: "Gross product sales", val: gbp(d.cur.gross), delta: d.prev && (d.cur.gross / d.prev.gross - 1) * 100, good: true, unit: "%" },
      { key: "canc", label: "Cancellations", val: gbp(d.cur.canc), sub: d.cur.rate.toFixed(2) + "% of gross", delta: d.prev && d.cur.rate - d.prev.rate, good: false, unit: " pp" },
      { key: "orders", label: "Orders (invoices)", val: Math.round(d.cur.orders).toLocaleString("en-GB"), delta: d.prev && (d.cur.orders / d.prev.orders - 1) * 100, good: true, unit: "%" },
      { key: "aov", label: "Average order value (gross)", val: gbp(d.cur.aov, 2), delta: d.prev && (d.cur.aov / d.prev.aov - 1) * 100, good: true, unit: "%" }
    ];
    items.forEach(function (it) {
      var card = el("div", "kpi" + (it.hero ? " hero" : ""));
      var label = el("div", "label"); label.appendChild(document.createTextNode(it.label));
      var info = el("button", "info", "i"); info.type = "button"; info.setAttribute("aria-expanded", "false");
      info.setAttribute("aria-label", "What does " + it.label + " mean?");
      var def = el("div", "kpi-def", KPI_DEFS[it.key]); def.hidden = true;
      info.addEventListener("click", function () { def.hidden = !def.hidden; info.setAttribute("aria-expanded", def.hidden ? "false" : "true"); });
      label.appendChild(info); card.appendChild(label); card.appendChild(def); card.appendChild(el("div", "value", it.val));
      var sub = el("div", "sub");
      if (it.delta != null) { sub.appendChild(chip(it.delta, it.good, it.unit)); sub.appendChild(document.createTextNode("vs prior 12 months")); }
      else sub.textContent = it.sub || d.label;
      if (it.delta != null && it.sub) sub.appendChild(document.createTextNode(" · " + it.sub));
      card.appendChild(sub); box.appendChild(card);
    });
    $("#kpi-scope").textContent = state.period === "all"
      ? "Showing the whole period, Dec 2009 – 9 Dec 2011, including the 9 days of Dec 2011."
      : "Showing " + d.label + " (the last 12 full months)" + (d.prevLabel ? ", compared with " + d.prevLabel : "") + ". The 9 days of Dec 2011 are not included.";
  }

  /* ---------- charts ---------- */
  function baseOptions() {
    return { responsive: true, maintainAspectRatio: false, animation: { duration: 250 },
      plugins: { legend: { display: false }, tooltip: { padding: 10, cornerRadius: 8 } },
      scales: { x: { grid: { display: false }, ticks: { color: css("--muted"), maxRotation: 0, autoSkip: true, maxTicksLimit: 12 } },
                y: { grid: { color: css("--border") }, border: { display: false }, ticks: { color: css("--muted") } } } };
  }
  function draw(id, config) { if (charts[id]) charts[id].destroy(); charts[id] = new Chart($("#" + id), config); }
  function renderMonthly() {
    var rows = state.partial ? M.monthly : M.monthly.filter(function (m) { return !m.is_partial_month; });
    var o = baseOptions();
    o.scales.y.ticks.callback = function (v) { return compact(v); };
    o.plugins.tooltip.callbacks = { label: function (c) { return gbp(c.parsed.y); }, afterLabel: function (c) { return rows[c.dataIndex].is_partial_month ? "Incomplete month (9 days)" : ""; } };
    draw("chart-monthly", { type: "bar", data: { labels: rows.map(function (m) { return monthLabel(m.year_month); }),
      datasets: [{ data: rows.map(function (m) { return m.net_product_revenue; }), borderRadius: 6, maxBarThickness: 28,
        backgroundColor: rows.map(function (m) { return m.is_partial_month ? css("--neutral") : css("--accent"); }) }] }, options: o });
  }
  function renderCancel() {
    var rows = state.partial ? M.monthly : M.monthly.filter(function (m) { return !m.is_partial_month; });
    var o = baseOptions();
    o.scales.y.ticks.callback = function (v) { return v + "%"; };
    o.plugins.tooltip.callbacks = { label: function (c) { return c.parsed.y.toFixed(1) + "% of gross"; } };
    draw("chart-cancel", { type: "line", data: { labels: rows.map(function (m) { return monthLabel(m.year_month); }),
      datasets: [{ data: rows.map(function (m) { return m.cancellation_rate_pct; }), borderColor: css("--bad"), backgroundColor: css("--bad"),
        pointRadius: 3, borderWidth: 2, tension: 0.25 }] }, options: o });
  }
  function renderBars(listId, items, total) {
    var ol = $(listId); ol.textContent = ""; var max = Math.max.apply(null, items.map(function (i) { return i.value; })) || 1;
    items.forEach(function (it, idx) {
      var li = el("li"), name = el("span", "name"), i = el("i", null, String(idx + 1)); name.appendChild(i); name.appendChild(document.createTextNode(it.name));
      li.appendChild(name); li.appendChild(el("span", "val", gbp(it.value) + (total ? "  ·  " + (it.value / total * 100).toFixed(1) + "%" : "")));
      var track = el("div", "track"), fill = el("div", "fill"); fill.style.width = (it.value / max * 100).toFixed(1) + "%";
      track.appendChild(fill); li.appendChild(track); ol.appendChild(li);
    });
  }
  function renderLists() {
    renderBars("#list-products", M.products.slice(0, 8).map(function (p) { return { name: p.stock_code + "  " + (p.description || ""), value: p.net_sales }; }), null);
    var total = M.kpis.net_product_revenue, rows = M.countries.slice();
    var uk = rows.filter(function (c) { return c.country === "United Kingdom"; })[0];
    if (state.noUK) rows = rows.filter(function (c) { return c.country !== "United Kingdom"; });
    rows.sort(function (a, b) { return b.net_product_revenue - a.net_product_revenue; });
    renderBars("#list-countries", rows.slice(0, 8).map(function (c) { return { name: c.country, value: c.net_product_revenue }; }), total);
    var topSum = M.products.reduce(function (a, p) { return a + p.net_sales; }, 0);
    $("#products-note").textContent = "Why it matters: the top " + M.products.length + " stock codes make up only " + (topSum / total * 100).toFixed(1) + "% of net revenue, so sales are spread across many products.";
    $("#uk-note").textContent = uk ? "The United Kingdom is " + (uk.net_product_revenue / total * 100).toFixed(0) + "% of net revenue; hide it to compare the rest." : "";
  }

  /* ---------- what-if ---------- */
  var PRICES = [-20, -15, -10, -5, 0, 5, 10, 15, 20], VOLUMES = [-30, -25, -20, -15, -10, -5, 0, 5, 10, 15, 20, 25, 30];
  function signed(v, u) { return (v > 0 ? "+" : "") + v + u; }
  function renderWhatIf() {
    var base = S.baseline(M.monthly, 12);
    $("#whatif-sub").textContent = "Baseline: " + monthLabel(base.first_month) + " – " + monthLabel(base.last_month) + " (" + base.months + " full months), cancellation rate " + (base.cancellation_rate * 100).toFixed(2) + "% held constant";
    $("#out-price").textContent = signed(state.price, "%"); $("#out-volume").textContent = signed(state.volume, "%"); $("#out-cost").textContent = state.cost + "%";
    var r = S.scenario(base, state.price, state.volume, state.cost), box = $("#sim-kpis"); box.textContent = "";
    [["Net revenue, scenario", gbp(r.net), true], ["Change in net revenue", gbp(r.net_change)], ["Profit, scenario (assumed cost)", gbp(r.profit)], ["Change in profit (assumed cost)", gbp(r.profit_change)]].forEach(function (k) {
      var c = el("div", "kpi" + (k[2] ? " hero" : "")); c.appendChild(el("div", "label", k[0])); c.appendChild(el("div", "value", k[1])); c.appendChild(el("div", "sub", "")); box.appendChild(c);
    });
    var even = S.breakevenVolumePct(state.price, state.cost), be = $("#breakeven");
    if (state.price === 0) be.textContent = "Price is unchanged, so profit changes only if volume changes.";
    else if (even === null) be.textContent = "With this price change and cost share the unit margin is zero or negative: no volume increase can restore baseline profit.";
    else be.textContent = "Break-even: with " + signed(state.price, "%") + " price and " + state.cost + "% cost share, profit stays at baseline if volume " + (even < 0 ? "can fall by up to " : "must rise by at least ") + Math.abs(even).toFixed(1) + "%.";
    var grid = S.sensitivity(base, PRICES, VOLUMES, state.cost), lim = 0;
    grid.forEach(function (row) { row.forEach(function (v) { lim = Math.max(lim, Math.abs(v)); }); }); lim = lim || 1;
    var t = el("table", "heat"), head = el("tr"); head.appendChild(el("th", null, "Price \\ Volume"));
    VOLUMES.forEach(function (v) { head.appendChild(el("th", null, signed(v, "%"))); }); t.appendChild(head);
    var accent = css("--accent"), bad = css("--bad");
    PRICES.forEach(function (p, i) {
      var tr = el("tr"); tr.appendChild(el("th", null, signed(p, "%")));
      VOLUMES.forEach(function (v, j) {
        var val = grid[i][j], td = el("td", p === state.price && v === state.volume ? "current" : "", compact(val));
        var a = Math.min(Math.abs(val) / lim, 1) * 0.72; td.style.background = "color-mix(in srgb, " + (val >= 0 ? accent : bad) + " " + Math.round(a * 100) + "%, transparent)";
        td.style.color = "inherit"; td.title = "Price " + signed(p, "%") + ", volume " + signed(v, "%") + ": " + gbp(val);
        td.addEventListener("click", function () { state.price = p; state.volume = v; $("#in-price").value = p; $("#in-volume").value = v; $("#in-price")._fill(); $("#in-volume")._fill(); renderWhatIf(); });
        tr.appendChild(td);
      }); t.appendChild(tr);
    });
    var wrap = $("#heat-wrap"), prev = wrap.scrollLeft; wrap.textContent = ""; wrap.appendChild(t);
    if (wrap.clientWidth > 0 && wrap.scrollWidth > wrap.clientWidth) {   // phone: keep the scroll position; first time, centre the chosen cell
      var cur = t.querySelector("td.current");
      if (!heatCentred && cur) { wrap.scrollLeft = cur.offsetLeft - (wrap.clientWidth - cur.offsetWidth) / 2; heatCentred = true; }
      else wrap.scrollLeft = prev;
    }
  }
  var heatCentred = false;

  /* ---------- methodology ---------- */
  function bridgeValue(part) { var r = M.bridge.filter(function (b) { return b.label.indexOf(part) !== -1; }); return r.length ? r[0].value : 0; }
  var labelPlugin = { id: "valueLabels", afterDatasetsDraw: function (chart) {
    var ctx = chart.ctx, meta = chart.getDatasetMeta(0), d = chart.data.datasets[0].labels;
    ctx.save(); ctx.fillStyle = css("--text"); ctx.font = "600 12px system-ui"; ctx.textAlign = "center";
    meta.data.forEach(function (bar, i) { ctx.fillText(d[i], bar.x, bar.y - 8); }); ctx.restore(); } };
  function renderBridge() {
    var raw = bridgeValue("Raw total"), dedup = bridgeValue("Deduplicated total"), net = bridgeValue("Net product revenue");
    var zoomFloor = Math.floor((Math.min(raw, dedup, net) - 250000) / 100000) * 100000, ink = css("--neutral");
    var floor = state.bridgeZero ? 0 : zoomFloor;
    var o = baseOptions(); o.layout = { padding: { top: 24 } };
    o.scales.y.min = floor;
    o.scales.y.max = state.bridgeZero ? Math.ceil(raw * 1.08 / 2000000) * 2000000 : Math.ceil((raw + 150000) / 100000) * 100000;
    o.scales.y.ticks.stepSize = state.bridgeZero ? 2000000 : 100000;
    o.scales.y.ticks.callback = function (v) { return state.bridgeZero ? compact(v) : gbp(v); };
    var over = dedup > 0 ? (raw / dedup - 1) * 100 : null, axis = $("#bridge-axis");
    var overText = over === null ? "" : " (" + over.toFixed(1) + "%)";
    axis.className = "axis-note" + (state.bridgeZero ? "" : " zoomed");
    axis.textContent = state.bridgeZero
      ? "Full-scale view: the axis starts at £0, so bar heights are proportional. The steps are small next to the totals."
      : "Zoomed view: the axis starts at " + gbp(zoomFloor) + ", not £0, so the bar heights exaggerate the steps." + (over === null ? "" : " The raw total is only " + over.toFixed(1) + "% above the deduplicated total.");
    $("#bridge-why").textContent = "Why it matters: without the overlap fix, revenue would be overstated by " + gbp(raw - dedup) + overText + ".";
    o.scales.x.ticks.autoSkip = false;
    o.plugins.tooltip.enabled = false;
    draw("chart-bridge", { type: "bar", plugins: [labelPlugin], options: o, data: {
      labels: [["Raw total", "(both sheets)"], ["Duplicate copies", "(sheet overlap)"], ["After removing", "duplicates"], ["Remove postage,", "fees, adjustments"], ["Net product", "revenue"]],
      datasets: [{ data: [[floor, raw], [dedup, raw], [floor, dedup], [Math.min(dedup, net), Math.max(dedup, net)], [floor, net]],
        labels: [gbp(raw), "-" + gbp(raw - dedup), gbp(dedup), (net >= dedup ? "+" : "-") + gbp(Math.abs(net - dedup)), gbp(net)],
        backgroundColor: [ink, css("--bad"), ink, css("--accent"), ink], borderRadius: 6, maxBarThickness: 90 }] } });
    var wrap = $("#bridge-table"); wrap.textContent = ""; var t = el("table"), h = el("tr");
    ["Step", "What", "Rows", "Value"].forEach(function (c, i) { h.appendChild(el("th", i > 1 ? "num" : null, c)); }); t.appendChild(h);
    M.bridge.forEach(function (b) { var tr = el("tr"); tr.appendChild(el("td", null, b.step)); tr.appendChild(el("td", null, b.label.trim()));
      tr.appendChild(el("td", "num", b.rows.toLocaleString("en-GB"))); tr.appendChild(el("td", "num", gbp(b.value, 2))); t.appendChild(tr); });
    wrap.appendChild(t);
  }
  function renderDocs() {
    function md(text) { return window.marked.parse(String(text || "").replace(/^# .*\n/, "")); }
    $("#doc-rules").innerHTML = md(M.docs.cleaning_rules); $("#doc-metrics").innerHTML = md(M.docs.metrics);   // our own project docs
  }

  /* ---------- shell ---------- */
  function renderAll() {
    renderKpis(); renderMonthly(); renderCancel(); renderLists(); renderWhatIf(); renderBridge();
  }
  function route() {
    var page = (location.hash || "#overview").slice(1); if (["overview", "whatif", "method"].indexOf(page) === -1) page = "overview";
    ["overview", "whatif", "method"].forEach(function (p) { $("#page-" + p).hidden = p !== page; });
    document.querySelectorAll(".nav-link").forEach(function (a) { a.classList.toggle("active", a.dataset.page === page); });
    renderAll(); window.scrollTo(0, 0);
  }
  function init() {
    initTheme();
    var m = M.meta;
    $("#build-line").textContent = "Built " + (m.built_at || "").replace("T", " ") + " · checks " + (m.reconciliation_checks_passed || "n/a");
    $("#foot-dataset").textContent = m.dataset; $("#foot-doi").href = m.doi; $("#foot-doi").textContent = m.doi;
    if (m.sample) { var b = $("#sample-banner"); b.hidden = false; b.textContent = m.sample_note; }
    document.querySelectorAll("[data-period]").forEach(function (b) { b.addEventListener("click", function () {
      state.period = b.dataset.period; document.querySelectorAll("[data-period]").forEach(function (x) { x.classList.toggle("active", x === b); }); renderKpis(); }); });
    document.querySelectorAll("[data-axis]").forEach(function (b) { b.addEventListener("click", function () {
      state.bridgeZero = b.dataset.axis === "zero"; document.querySelectorAll("[data-axis]").forEach(function (x) { x.classList.toggle("active", x === b); }); renderBridge(); }); });
    $("#toggle-partial").addEventListener("change", function (e) { state.partial = e.target.checked; renderMonthly(); renderCancel(); });
    $("#toggle-uk").addEventListener("change", function (e) { state.noUK = e.target.checked; renderLists(); });
    [["in-price", "price"], ["in-volume", "volume"], ["in-cost", "cost"]].forEach(function (p) {
      $("#" + p[0]).addEventListener("input", function (e) { state[p[1]] = +e.target.value; renderWhatIf(); }); });
    document.querySelectorAll("input[type=range]").forEach(function (r) {
      function fill() { r.style.setProperty("--pct", ((r.value - r.min) / (r.max - r.min) * 100) + "%"); }
      r.addEventListener("input", fill); fill(); r._fill = fill; });
    initMenu();
    renderDocs(); window.addEventListener("hashchange", route); route();
  }
  function initMenu() {
    var btn = $("#menu-btn"), side = $("#sidebar"), scrim = $("#scrim");
    function setOpen(open) {
      side.classList.toggle("open", open); scrim.hidden = !open;
      document.body.classList.toggle("menu-open", open);
      btn.setAttribute("aria-expanded", open ? "true" : "false");
      btn.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    }
    btn.addEventListener("click", function () { setOpen(!side.classList.contains("open")); });
    scrim.addEventListener("click", function () { setOpen(false); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") setOpen(false); });
    document.querySelectorAll(".nav-link").forEach(function (a) { a.addEventListener("click", function () { setOpen(false); }); });
    window.addEventListener("resize", function () { if (window.innerWidth > 760) setOpen(false); });
  }
  init();
})();
