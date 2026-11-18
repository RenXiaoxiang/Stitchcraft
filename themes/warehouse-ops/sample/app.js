/* Ember & Bean Fulfilment — offline warehouse inventory board.
 * Sections: config · storage · seed · state · helpers · rendering · filters ·
 * dialogs/CRUD · motion · remote read · boot.
 * Records render through <template> clones and textContent; no innerHTML.
 * Edits persist in localStorage (with an in-memory fallback for file://).
 */
(function () {
  "use strict";

  /* 1. Configuration ------------------------------------------------------ */
  const DB = window.STITCHCRAFT_DB || {};
  const MODE = DB.mode === "remote" && typeof DB.url === "string" && DB.url ? "remote" : "local";
  const NS = String(DB.tablePrefix || "stitchcraft") + ":warehouse-ops:v1:";
  const KEYS = { items: NS + "inventory_items", inbound: NS + "inbound_shipments", activity: NS + "activity_log" };
  const ZONES = ["A", "B", "C", "D"];
  const STATUS_LABEL = { "in-stock": "In stock", low: "Low", out: "Out of stock" };
  const ERROR_IDS = { sku: "sku-error", name: "name-error", quantity: "quantity-error", reorder_point: "reorder-error", unit_cost: "cost-error" };
  const REDUCED = window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)") : { matches: false };
  const fmtNumber = new Intl.NumberFormat("en-US");
  const fmtTime = new Intl.DateTimeFormat("en-US", { hour: "numeric", minute: "2-digit" });
  const fmtDay = new Intl.DateTimeFormat("en-US", { weekday: "short", month: "short", day: "numeric" });
  /* 2. Storage: localStorage, with an in-memory fallback for locked file:// */
  const memory = new Map();
  let storageOk = true;
  const store = {
    read: (key) => {
      try { const raw = window.localStorage.getItem(key); return raw ? JSON.parse(raw) : null; }
      catch (err) { storageOk = false; return memory.has(key) ? memory.get(key) : null; }
    },
    write: (key, value) => {
      memory.set(key, value);
      try { window.localStorage.setItem(key, JSON.stringify(value)); storageOk = true; } catch (err) { storageOk = false; }
    },
    clear: (key) => {
      memory.delete(key);
      try { window.localStorage.removeItem(key); } catch (err) { storageOk = false; }
    }
  };
  /* 3. Seed records ------------------------------------------------------- */
  function isoIn(hours) {
    const date = new Date();
    date.setHours(date.getHours() + hours);
    return date.toISOString();
  }
  function seedInventory() {
    const rows = [
      ["EB-1042", "Espresso beans, 1kg", "Coffee", "A", 18, 24, 12.5], ["EB-1088", "Filter roast, 1kg", "Coffee", "A", 96, 30, 11.2],
      ["EB-2210", "Oat milk, 1L", "Dairy alt", "C", 0, 20, 2.4], ["EB-3051", "Kraft bags, 1kg", "Packaging", "B", 540, 200, 0.38],
      ["EB-3120", "Valve bags, 250g", "Packaging", "B", 46, 150, 0.21], ["EB-4106", "Cold brew concentrate", "Coffee", "D", 34, 12, 6.8],
      ["EB-4277", "Compostable cups", "Packaging", "C", 12, 60, 0.09], ["EB-5011", "House blend, 1kg", "Coffee", "A", 210, 80, 9.4],
      ["EB-5182", "Decaf whole bean", "Coffee", "D", 4, 15, 10.6], ["EB-6044", "Shipping labels, roll", "Supplies", "B", 1800, 500, 0.04]
    ];
    return rows.map((row, index) => ({
      id: "itm-" + row[0].toLowerCase(), sku: row[0], name: row[1], category: row[2], zone: row[3],
      quantity: row[4], reorder_point: row[5], unit_cost: row[6],
      status: deriveStatus(row[4], row[5]), updated_at: isoIn(-(index + 2) * 3)
    }));
  }
  const seedInbound = () => [
    { id: "IN-8841", supplier: "Highland Roasters", dock: "Dock 2", eta: isoIn(-3), lines: 18, status: "arrived" },
    { id: "IN-8842", supplier: "Marlow Packaging", dock: "Dock 4", eta: isoIn(2), lines: 6, status: "at dock" },
    { id: "IN-8843", supplier: "Cold Chain North", dock: "Dock 1", eta: isoIn(22), lines: 12, status: "scheduled" },
    { id: "IN-8844", supplier: "Cascadia Labels", dock: "Dock 3", eta: isoIn(1), lines: 4, status: "delayed" }
  ];
  const seedActivity = () => [
    { id: "act-1", at: isoIn(-0.4), text: "Sold 24 × EB-1088 at the counter" },
    { id: "act-2", at: isoIn(-1.6), text: "Cycle count completed for zone C" },
    { id: "act-3", at: isoIn(-3.2), text: "Received 18 lines from Highland Roasters" }
  ];
  /* 4. State -------------------------------------------------------------- */
  const state = {
    items: [], inbound: [], activity: [], search: "", status: "all", zone: "all",
    sort: { key: "sku", dir: 1 }, editingId: null, confirmAction: null, opener: null, toastTimer: 0, remoteOk: false
  };
  /* 5. Helpers ------------------------------------------------------------ */
  const $ = (id) => document.getElementById(id);
  const field = (name) => itemForm.elements.namedItem(name);
  const number = (value) => fmtNumber.format(Number(value) || 0);
  const itemLabel = (item) => item.sku + " · " + item.name;
  const setText = (id, value) => { $(id).textContent = value; };
  function todayKey(value) {
    const date = new Date(value);
    return date.getFullYear() + "-" + date.getMonth() + "-" + date.getDate();
  }
  function deriveStatus(quantity, reorderPoint) {
    const qty = Number(quantity) || 0;
    return qty <= 0 ? "out" : qty <= (Number(reorderPoint) || 0) ? "low" : "in-stock";
  }
  function loadOrSeed(key, factory) {
    const stored = store.read(key);
    if (Array.isArray(stored)) return stored;
    const seeded = factory();
    store.write(key, seeded);
    return seeded;
  }
  const saveItems = () => store.write(KEYS.items, state.items);
  function logActivity(text) {
    state.activity.unshift({ id: "act-" + Date.now().toString(36), at: new Date().toISOString(), text });
    state.activity = state.activity.slice(0, 12);
    store.write(KEYS.activity, state.activity);
    renderActivity();
  }
  function toast(message) {
    const node = $("toast");
    node.textContent = message;
    node.hidden = false;
    window.clearTimeout(state.toastTimer);
    state.toastTimer = window.setTimeout(() => { node.hidden = true; }, 2800);
  }
  function updateModeBadge() {
    const badge = $("data-mode");
    if (MODE === "remote") {
      badge.textContent = state.remoteOk ? "Remote · synced" : "Remote offline · local cache";
      badge.dataset.state = state.remoteOk ? "remote" : "offline";
    } else {
      badge.textContent = storageOk ? "Local demo · saved" : "Local demo · memory only";
      badge.dataset.state = storageOk ? "local" : "memory";
    }
  }
  /* 6. Rendering ---------------------------------------------------------- */
  function renderKpis() {
    const count = (status) => state.items.filter((item) => item.status === status).length;
    const low = count("low");
    const out = count("out");
    const today = todayKey(new Date().toISOString());
    const inbound = state.inbound.filter((shipment) => shipment.status !== "arrived" && todayKey(shipment.eta) === today).length;
    const plural = (value, word) => value + " " + word + (value === 1 ? "" : "s");
    setText("kpi-total", number(state.items.length)); setText("kpi-total-note", state.items.length === 1 ? "tracked line" : "tracked lines");
    setText("kpi-low", number(low)); setText("kpi-low-note", low ? "at or below reorder" : "all above reorder");
    setText("kpi-inbound", number(inbound)); setText("kpi-inbound-note", inbound ? "trailers expected" : "no drops left today");
    setText("kpi-out", number(out)); setText("kpi-out-note", out ? "expedite today" : "none, nice");
    setText("hero-lede", low || out
      ? plural(low, "line") + " at or below reorder and " + plural(out, "item") + " out of stock; " + plural(inbound, "trailer") + " still due today."
      : "Every line is above its reorder level; " + plural(inbound, "trailer") + " due today.");
  }
  function visibleItems() {
    const query = state.search.trim().toLowerCase();
    const rows = state.items.filter((item) => {
      if (state.status !== "all" && item.status !== state.status) return false;
      if (state.zone !== "all" && item.zone !== state.zone) return false;
      return !query || [item.sku, item.name, item.category || ""].join(" ").toLowerCase().includes(query);
    });
    const key = state.sort.key; const dir = state.sort.dir;
    rows.sort((a, b) => {
      let left = a[key]; let right = b[key];
      if (key === "quantity") { left = Number(left) || 0; right = Number(right) || 0; }
      else { left = String(left || "").toLowerCase(); right = String(right || "").toLowerCase(); }
      return left < right ? -dir : left > right ? dir : String(a.sku).localeCompare(String(b.sku));
    });
    return rows;
  }
  function renderTable(options) {
    const rows = visibleItems();
    const template = $("row-template");
    const body = $("inventory-body");
    const rendered = [];
    body.replaceChildren();
    rows.forEach((item) => {
      const fragment = template.content.cloneNode(true);
      const row = fragment.querySelector("tr");
      const fill = (selector, value) => { fragment.querySelector(selector).textContent = value; };
      row.dataset.id = item.id;
      fill(".row-sku", item.sku); fill(".row-name", item.name); fill(".row-category", item.category || "—");
      fill(".row-qty", number(item.quantity)); fill(".row-reorder", number(item.reorder_point)); fill(".row-zone", item.zone);
      const pill = fragment.querySelector(".row-status");
      pill.dataset.status = item.status;
      pill.textContent = STATUS_LABEL[item.status] || item.status;
      fragment.querySelector(".js-edit").setAttribute("aria-label", "Edit " + itemLabel(item));
      fragment.querySelector(".js-delete").setAttribute("aria-label", "Delete " + itemLabel(item));
      body.appendChild(fragment);
      rendered.push(row);
    });
    const isEmpty = rows.length === 0;
    $("inventory-table").hidden = isEmpty;
    $("empty-state").hidden = !isEmpty;
    setText("empty-title", state.items.length === 0 ? "No items on the board yet" : "No items match those filters");
    setText("empty-copy", state.items.length === 0
      ? "Add the first item to start the inventory board."
      : "Try another search term, clear a filter, or add a new item.");
    setText("result-count", rows.length + " of " + state.items.length + " item" + (state.items.length === 1 ? "" : "s"));
    if (options && options.animate) animateRows(rendered);
  }
  function renderInbound() {
    const list = $("inbound-list");
    const template = $("inbound-template");
    const today = todayKey(new Date().toISOString());
    list.replaceChildren();
    state.inbound.forEach((shipment) => {
      const fragment = template.content.cloneNode(true);
      const eta = new Date(shipment.eta);
      const time = fragment.querySelector("time");
      time.dateTime = shipment.eta;
      time.textContent = todayKey(shipment.eta) === today ? fmtTime.format(eta) : fmtDay.format(eta);
      const status = fragment.querySelector(".timeline__state");
      status.textContent = shipment.status;
      status.dataset.state = { arrived: "done", "at dock": "active", scheduled: "next", delayed: "late" }[shipment.status] || "next";
      fragment.querySelector(".timeline__title").textContent = shipment.supplier + " · " + shipment.dock;
      fragment.querySelector(".timeline__body").textContent = shipment.lines + " lines · " + shipment.id;
      list.appendChild(fragment);
    });
  }
  function renderActivity() {
    const list = $("activity-list");
    const template = $("activity-template");
    list.replaceChildren();
    if (!state.activity.length) {
      const item = document.createElement("li");
      item.className = "activity__empty";
      item.textContent = "No activity yet — edits will appear here.";
      list.appendChild(item);
      return;
    }
    state.activity.slice(0, 6).forEach((entry) => {
      const fragment = template.content.cloneNode(true);
      fragment.querySelector(".activity__time").textContent = fmtTime.format(new Date(entry.at));
      fragment.querySelector(".activity__text").textContent = entry.text;
      list.appendChild(fragment);
    });
  }
  function renderAll(options) {
    renderKpis(); renderTable(options); renderInbound(); renderActivity(); updateModeBadge();
  }
  /* 7. Filters, sort and row actions -------------------------------------- */
  function resetFilters(shouldFocus) {
    state.search = ""; state.status = "all"; state.zone = "all";
    $("search").value = "";
    $("status-filter").value = "all";
    $("zone-filter").value = "all";
    renderTable();
    if (shouldFocus !== false) $("search").focus();
  }
  function applySort(key) {
    state.sort = { key, dir: state.sort.key === key ? -state.sort.dir : 1 };
    document.querySelectorAll(".th-sort").forEach((button) => {
      const active = button.dataset.sort === key;
      button.closest("th").setAttribute("aria-sort", active ? (state.sort.dir === 1 ? "ascending" : "descending") : "none");
      button.querySelector("span").textContent = active ? (state.sort.dir === 1 ? "↑" : "↓") : "↕";
    });
    renderTable();
  }
  function wireFilters() {
    $("search").addEventListener("input", (event) => { state.search = event.target.value; renderTable(); });
    $("status-filter").addEventListener("change", (event) => { state.status = event.target.value; renderTable(); });
    $("zone-filter").addEventListener("change", (event) => { state.zone = event.target.value; renderTable(); });
    $("reset-filters").addEventListener("click", () => resetFilters(true));
    $("empty-reset").addEventListener("click", () => resetFilters(true));
    $("empty-add").addEventListener("click", (event) => openItemDialog(null, event.currentTarget));
    document.querySelectorAll(".th-sort").forEach((button) => button.addEventListener("click", () => applySort(button.dataset.sort)));
    $("inventory-body").addEventListener("click", (event) => {
      const button = event.target.closest("button");
      if (!button) return;
      const item = state.items.find((entry) => entry.id === button.closest("tr").dataset.id);
      if (!item) return;
      if (button.classList.contains("js-edit")) openItemDialog(item, button);
      if (button.classList.contains("js-delete")) askDelete(item, button);
    });
  }
  /* 8. Dialogs and CRUD --------------------------------------------------- */
  const itemDialog = $("item-dialog");
  const confirmDialog = $("confirm-dialog");
  const itemForm = $("item-form");
  function openDialog(dialog, opener) {
    state.opener = opener || document.activeElement;
    if (typeof dialog.showModal === "function") dialog.showModal();
    else dialog.setAttribute("open", "");
  }
  function closeDialog(dialog) {
    if (typeof dialog.close === "function") dialog.close();
    else dialog.removeAttribute("open");
  }
  function restoreFocus() {
    const target = state.opener;
    state.opener = null;
    if (target && target.isConnected && typeof target.focus === "function") target.focus();
    else $("search").focus();
  }
  function clearErrors() {
    Object.keys(ERROR_IDS).forEach((name) => {
      const input = field(name);
      if (input) input.removeAttribute("aria-invalid");
      setText(ERROR_IDS[name], "");
    });
    setText("form-error", "");
    $("form-error").hidden = true;
  }
  function showErrors(errors) {
    Object.keys(errors).forEach((name) => {
      const input = field(name);
      if (input) input.setAttribute("aria-invalid", "true");
      setText(ERROR_IDS[name], errors[name]);
    });
    setText("form-error", "Check the highlighted fields before saving.");
    $("form-error").hidden = false;
  }
  function updateStatusPreview() {
    const status = deriveStatus(field("quantity").value, field("reorder_point").value);
    setText("status-preview", (STATUS_LABEL[status] || status) + " — derived from quantity and reorder level");
  }
  function openItemDialog(item, opener) {
    state.editingId = item ? item.id : null;
    setText("item-dialog-title", item ? "Edit item" : "Add item");
    itemForm.reset();
    clearErrors();
    const values = item
      ? { sku: item.sku, name: item.name, category: item.category || "", zone: item.zone, quantity: item.quantity, reorder_point: item.reorder_point, unit_cost: item.unit_cost || "" }
      : { zone: "A", quantity: 0, reorder_point: 10 };
    Object.keys(values).forEach((name) => { field(name).value = String(values[name]); });
    updateStatusPreview();
    openDialog(itemDialog, opener);
    field("sku").focus();
  }
  function validate(values) {
    const errors = {};
    const sku = values.sku.trim().toUpperCase();
    if (!/^[A-Za-z0-9][A-Za-z0-9-]{2,11}$/.test(sku)) errors.sku = "Use 3–12 letters, digits or hyphens, e.g. EB-1042.";
    else if (state.items.some((item) => item.sku.toUpperCase() === sku && item.id !== state.editingId)) errors.sku = "That SKU is already on the board.";
    if (values.name.trim().length < 2) errors.name = "Give the item a name of at least 2 characters.";
    if (!/^\d+$/.test(values.quantity.trim())) errors.quantity = "Quantity must be a whole number, 0 or more.";
    if (!/^\d+$/.test(values.reorder_point.trim())) errors.reorder_point = "Reorder level must be a whole number, 0 or more.";
    if (values.unit_cost.trim() !== "" && !/^\d+(\.\d{1,2})?$/.test(values.unit_cost.trim())) errors.unit_cost = "Unit cost must be 0 or more, with up to 2 decimals.";
    return errors;
  }
  function saveItem(event) {
    event.preventDefault();
    clearErrors();
    const values = { sku: field("sku").value, name: field("name").value, category: field("category").value,
      zone: field("zone").value, quantity: field("quantity").value, reorder_point: field("reorder_point").value, unit_cost: field("unit_cost").value };
    const errors = validate(values);
    if (Object.keys(errors).length) {
      showErrors(errors);
      const first = field(Object.keys(errors)[0]);
      if (first) first.focus();
      return;
    }
    const quantity = parseInt(values.quantity, 10);
    const reorderPoint = parseInt(values.reorder_point, 10);
    const record = {
      id: state.editingId || "itm-" + Date.now().toString(36), sku: values.sku.trim().toUpperCase(),
      name: values.name.trim(), category: values.category.trim() || "Uncategorised", zone: ZONES.includes(values.zone) ? values.zone : "A",
      quantity, reorder_point: reorderPoint, unit_cost: values.unit_cost.trim() === "" ? 0 : Math.round(Number(values.unit_cost) * 100) / 100,
      status: deriveStatus(quantity, reorderPoint), updated_at: new Date().toISOString()
    };
    if (state.editingId) {
      const index = state.items.findIndex((item) => item.id === state.editingId);
      if (index !== -1) state.items[index] = record;
      logActivity("Edited " + itemLabel(record));
      toast(record.sku + " updated");
    } else {
      state.items.push(record);
      logActivity("Added " + itemLabel(record));
      toast(record.sku + " added");
    }
    state.editingId = null;
    saveItems();
    closeDialog(itemDialog);
    renderKpis();
    renderTable({ animate: true });
    updateModeBadge();
  }
  function askDelete(item, opener) {
    state.confirmAction = function () {
      state.items = state.items.filter((entry) => entry.id !== item.id);
      saveItems();
      logActivity("Deleted " + itemLabel(item));
      toast(item.sku + " deleted");
      renderKpis();
      renderTable({ animate: true });
      updateModeBadge();
    };
    setText("confirm-title", "Delete this item?");
    setText("confirm-copy", item.name + " (" + item.sku + ") will be removed from the board. This cannot be undone.");
    setText("confirm-action", "Delete item");
    $("confirm-action").className = "btn btn--danger";
    openDialog(confirmDialog, opener);
  }
  function resetDemo() {
    state.items = seedInventory();
    state.inbound = seedInbound();
    state.activity = seedActivity();
    store.write(KEYS.items, state.items);
    store.write(KEYS.inbound, state.inbound);
    store.write(KEYS.activity, state.activity);
    logActivity("Demo reset to the seed records");
    renderAll({ animate: true });
    toast("Demo reset to 10 seed items");
  }
  function askReset(opener) {
    state.confirmAction = resetDemo;
    setText("confirm-title", "Reset the demo?");
    setText("confirm-copy", "This restores the 10 seed items, the dock schedule and the seeded activity log on this device.");
    setText("confirm-action", "Reset demo data");
    $("confirm-action").className = "btn btn--primary";
    openDialog(confirmDialog, opener);
  }
  function wireDialogs() {
    document.querySelectorAll("[data-close]").forEach((button) => button.addEventListener("click", () => closeDialog(button.closest("dialog"))));
    itemDialog.addEventListener("close", restoreFocus);
    confirmDialog.addEventListener("close", restoreFocus);
    itemForm.addEventListener("submit", saveItem);
    itemForm.addEventListener("input", (event) => {
      if (event.target === field("quantity") || event.target === field("reorder_point")) updateStatusPreview();
    });
    $("add-item").addEventListener("click", (event) => openItemDialog(null, event.currentTarget));
    $("reset-demo").addEventListener("click", (event) => askReset(event.currentTarget));
    $("confirm-action").addEventListener("click", () => {
      const action = state.confirmAction;
      state.confirmAction = null;
      closeDialog(confirmDialog);
      if (typeof action === "function") action();
    });
  }
  /* 9. Motion: GSAP when vendored, CSS keyframes otherwise; always recover - */
  function canAnimate() { return !REDUCED.matches; }
  function forceReveal() {
    const targets = document.querySelectorAll(".hero__copy > *, .stat, .panel, #inventory-body tr");
    try {
      if (window.gsap) {
        window.gsap.killTweensOf(targets);
        window.gsap.set(targets, { clearProps: "opacity,transform,translate" });
      }
    } catch (err) { /* the CSS fallback keeps content visible */ }
    targets.forEach((node) => node.classList.add("is-in"));
    document.documentElement.classList.remove("motion-pending");
  }
  function animateEntrance() {
    const root = document.documentElement;
    if (!canAnimate()) { root.classList.remove("motion-pending"); return; }
    try {
      if (!window.gsap) throw new Error("gsap unavailable");
      root.classList.remove("motion-pending");
      /* Transform-only entrance: content stays readable even if frames stall. */
      window.gsap.from(".hero__copy > *", { y: 12, duration: 0.4, stagger: 0.05, ease: "power2.out" });
      window.gsap.from(".stat", { y: 14, duration: 0.4, stagger: 0.03, delay: 0.05, ease: "power2.out" });
      window.gsap.from(".panel", { y: 12, duration: 0.45, stagger: 0.04, delay: 0.1, ease: "power2.out" });
      window.setTimeout(forceReveal, 1100);
    } catch (err) {
      document.querySelectorAll(".hero__copy > *, .stat, .panel").forEach((node, index) => {
        node.style.animationDelay = Math.min(index * 45, 360) + "ms";
        node.classList.add("is-in");
      });
      window.setTimeout(() => root.classList.remove("motion-pending"), 1000);
    }
  }
  function animateRows(rows) {
    if (!rows.length || !canAnimate()) return;
    try {
      if (window.gsap) {
        window.gsap.fromTo(rows, { opacity: 0.4, y: 8 }, { opacity: 1, y: 0, duration: 0.26, stagger: 0.02, ease: "power1.out", overwrite: "auto", clearProps: "opacity,transform" });
      } else {
        rows.forEach((row) => row.classList.add("row-in"));
      }
    } catch (err) {
      rows.forEach((row) => row.classList.add("row-in"));
    }
  }
  /* 10. Remote read: only when data-config.js sets mode "remote" ----------- */
  function normaliseRow(row) {
    return {
      id: String(row.id || row.sku), sku: String(row.sku || "UNKNOWN"), name: String(row.name || "Untitled"),
      category: String(row.category || "Uncategorised"), zone: String(row.zone || "A"), quantity: Number(row.quantity) || 0,
      reorder_point: Number(row.reorder_point) || 0, unit_cost: Number(row.unit_cost) || 0,
      status: deriveStatus(row.quantity, row.reorder_point), updated_at: row.updated_at || new Date().toISOString()
    };
  }
  function readRemote() {
    if (MODE !== "remote" || typeof window.fetch !== "function") return;
    const headers = { Accept: "application/json" };
    if (DB.kind === "supabase") { headers.apikey = DB.anonKey; headers.Authorization = "Bearer " + DB.anonKey; }
    window.fetch(DB.url.replace(/\/$/, "") + "/rest/v1/inventory_items?select=*", { headers })
      .then((response) => { if (!response.ok) throw new Error("HTTP " + response.status); return response.json(); })
      .then((rows) => {
        if (!Array.isArray(rows)) throw new Error("Unexpected payload");
        state.items = rows.map(normaliseRow); state.remoteOk = true; saveItems();
        renderKpis(); renderTable({ animate: true }); updateModeBadge();
        toast("Loaded " + rows.length + " items from the remote API");
      })
      .catch(() => {
        state.remoteOk = false; updateModeBadge();
        toast("Remote API unavailable — showing the local cache");
      });
  }
  /* 11. Boot -------------------------------------------------------------- */
  function boot() {
    state.items = loadOrSeed(KEYS.items, seedInventory); state.inbound = loadOrSeed(KEYS.inbound, seedInbound);
    state.activity = loadOrSeed(KEYS.activity, seedActivity);
    setText("sync-time", "Synced " + fmtTime.format(new Date()));
    wireFilters(); wireDialogs(); renderAll({ animate: true });
    animateEntrance(); window.setTimeout(forceReveal, 2400); readRemote();
  }
  try {
    boot();
  } catch (err) {
    forceReveal();
    toast("The demo failed to load — reload the page to try again.");
    if (window.console && window.console.error) window.console.error(err);
  }
})();
