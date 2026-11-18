---
name: logistics-control
description: Build a midnight-blue logistics console with shipment tracking, carrier scorecards and an incident board.
---

# Logistics Control

## Job
Generate a real-time-feeling logistics control room: shipment progress, carrier performance, an ETA timeline and an incident board for exceptions. Operators must scan status in seconds, filter the board, and open or resolve an incident from the page. Data is seeded and editable.

## When to use
- The user runs freight, delivery, supply-chain or dispatch operations.
- The request mentions shipments, carriers, tracking, ETAs, delays or incidents.
- The audience is an operations team on a large screen, with mobile as fallback.

## Data model
Read `data-model.json`; three writable collections.
- `shipments`: `id`, `reference`, `origin`, `destination`, `carrier`, `mode`, `status`, `eta`, `weight_kg`.
- `carriers`: `name`, `contact`, `on_time_rate`, `active_shipments`, `service_level`.
- `incidents`: `id`, `shipment_id`, `severity`, `summary`, `opened_at`, `resolved`.
Shipment statuses: `booked`, `in-transit`, `customs`, `delivered`, `delayed`. Incident severities: `low`, `medium`, `high`. Seed 12-16 shipments, 4-5 carriers and 3-5 incidents with realistic ports and ISO-8601 timestamps.

## Layout blueprint
1. Control bar: company/console name, UTC clock, connection dot, alert count.
2. Hero strip: "Network status" headline, active shipment count, export action.
3. Stat grid: shipments in transit, on-time percentage, open incidents, active carriers - monospace figures.
4. Board: shipment table (reference, route, carrier, ETA, status) with search, status filter and mode filter; routes read `origin -> destination`.
5. Timeline: today's ETAs and hand-offs with dock/port labels.
6. Incident board: three severity lanes with resolve actions; counters update.
7. Carrier scorecards: on-time rate as a thin bar, active shipments, contact.
8. Footer: data-mode badge, last refresh.

## Components
Use `themes/_blocks/`: `stat-grid`, `data-table`, `timeline`, `crud-modal` (incident form). Build the incident lanes locally; they are theme-specific.

## Motion
Transform and opacity only, guarded by `if (window.gsap)`.
- Entrance: KPI cards and lanes stagger 0.05s with y 10px, 0.5s `power2.out`.
- Status dot: a slow 2s opacity pulse on live shipments; stop under reduced motion and never pulse below 3 Hz.
- ETA bars: animate scaleX from 0 to the real value once on entry.
- Incident resolve: lane card fades out before the list reflows; no layout animation.

## Data layer
Local mode seeds `localStorage` under a namespaced key and persists creates, updates (resolve incident, advance shipment) and deletes; guard in try/catch. Remote mode is a generation setting: `window.STITCHCRAFT_DATA = {mode:"remote", apiBase:"..."}` or `data-data-mode`/`data-api-base` on `<body>`. One REST adapter over `shipments`, `carriers`, `incidents`; on failure keep local data and show an "offline" badge, never block the board on a slow request.

## Quality bar
- Midnight palette: base #071522, panels #0c2233, cyan #38d6e0, text #dff6fa.
- Console density: hairline rules, monospace references and times, tabular numbers, no rounded consumer-card look.
- Status always has text plus colour; high severity is not red-only.
- Responsive: board and timeline side by side at 1440px, stacked at 390px with the table becoming cards; incident lanes scroll horizontally on mobile.
- Accessible: table caption, labelled filters, focus-visible, `aria-live` for the incident count, keyboard resolve actions, minimum 4.5:1 contrast.

## Output contract
Return only `{"files":[{"path","content"}],"summary":"..."}` with `index.html`, `styles.css` and `app.js` required. No external fonts, images or CDNs; no real map tiles - use a CSS grid or inline SVG for the network feel. `summary` states seeded counts, data mode and any endpoint.
