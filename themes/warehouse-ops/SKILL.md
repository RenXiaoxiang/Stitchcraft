---
name: warehouse-ops
description: Build a dense industrial inventory dashboard with amber-on-ink styling, seeded stock data and full CRUD.
---

# Warehouse Operations

## Job
Generate a working operations dashboard for a warehouse team: stock levels, low-stock exceptions, inbound shipments and one-click item maintenance. It is a data app, not a brochure: every KPI traces to a table row and every row is editable.

## When to use
- The user runs a warehouse, 3PL, stockroom, workshop or parts department.
- The request names inventory, SKUs, stock, reorder points, docks or inbound.
- Staff open the page every shift; marketing copy is secondary.

## Data model
Read `data-model.json`; both collections are writable.
- `inventory_items` - `sku`, `name`, `category`, `zone`, `quantity`, `reorder_point`, `unit_cost`, `status`, `updated_at`.
- `inbound_shipments` - `id`, `supplier`, `dock`, `eta`, `lines`, `status`.
Derive `status` from stock: `out` at 0, `low` at or below `reorder_point`, `in-stock` otherwise, and persist it so filters need no arithmetic. Seed 12-18 items across zones A-D and 3-5 inbound shipments with ISO-8601 ETAs.

## Layout blueprint
1. Top bar: warehouse name, active shift, sync timestamp, jump links.
2. Compact hero strip (max ~180px): greeting, one-line status, `Add item`.
3. Stat grid: units on hand, SKUs below reorder point, inbound today, picks queued - monospace tabular numerals.
4. Workspace: inventory panel (search, status pills, zone select, row actions) beside an inbound dock list and activity log.
5. CRUD modal: labelled form, inline validation, save/cancel; delete asks in a second dialog.
6. Footer: data-mode badge and a reset-demo action.

## Components
Adapt these blocks from `themes/_blocks/`: `hero` (compact), `stat-grid`, `data-table` (status pills, row actions, stacked mobile cards), `crud-modal` (native `<dialog>`, focus restoration). Add `timeline` for inbound ETAs if the table is not enough.

## Motion
Only `transform` and `opacity`, always guarded by `if (window.gsap)`.
- Entrance: stagger KPI cards and table rows 0.04s, y 10-14px, 0.45s `power2.out`.
- Scroll: ScrollTrigger batches when available; the sample uses IntersectionObserver plus `gsap.to`, so core-only GSAP works.
- Micro: modal from 0.97 scale, toast slides in 200ms.
- Skip every animation under `prefers-reduced-motion: reduce`; never animate data being read for more than 600ms.

## Data layer
Local mode is the default: seed once into `localStorage` under a namespaced key, then persist every create, update and delete. Guard storage access in try/catch and fall back to memory so the page works from `file://`.
Remote mode is a generation setting: `window.STITCHCRAFT_DATA = {mode:"remote", apiBase:"..."}` or `data-data-mode="remote"` plus `data-api-base` on `<body>`. Use one REST adapter (`GET/POST/PATCH/DELETE {apiBase}/inventory_items`); on failure keep the local copy and show an "offline" badge.

## Quality bar
- Industrial dark palette: ink #0b0d11, panels #12161d, amber #ff8a3d.
- Dense but calm: 1px borders, 8px spacing scale, no shadow above 12px blur.
- 4.5:1 body contrast; amber is never text on white.
- Responsive: four KPI columns at 1440px, one at 390px; table stacks into cards under 720px.
- Keyboard: visible focus, dialog focus trap, Escape closes, `aria-live` for toasts and result counts.
- Empty, loading and error states exist; seeded data is realistic, no lorem ipsum.

## Output contract
Return only `{"files":[{"path","content"}],"summary":"..."}` with `index.html`, `styles.css` and `app.js` required. All assets relative, no CDN, no external fonts or images. `summary` names the data mode and any endpoint the user must set.
