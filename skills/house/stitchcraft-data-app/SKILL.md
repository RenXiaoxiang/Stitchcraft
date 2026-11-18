---
name: stitchcraft-data-app
description: Build CRUD data interfaces (inventory, staff, shipments) that read and write through a configurable local or remote data adapter.
---

# Stitchcraft Data App

## Job

Give a Stitchcraft data-theme site a working data layer and the interface that
operates it: KPIs, a filterable table, a create/edit form, delete confirmation
and an honest empty state. This skill is the contract between the generated UI
and whatever database the user configured.

## When to use

- The selected theme category is `data` (warehouse-ops, staff-directory,
  logistics-control).
- The generated site stores records the user must add, edit, search or remove.

## Data layer contract

The app must read the database configuration from `window.STITCHCRAFT_DB`
(written by the generator into `data-config.js`):

```js
window.STITCHCRAFT_DB = {
  mode: "local",              // "local" | "remote"
  kind: "supabase",           // "supabase" | "rest"
  url: "",                    // remote base URL, empty for local
  anonKey: "",                // remote anon/public key, empty for local
  tablePrefix: "stitchcraft"
};
```

Implement one adapter with two backends:

- `local`: `localStorage` under `stitchcraft:<table>`, seeded from the theme's
  example records on first load. Works with `file://` and offline.
- `remote`: REST calls to `${url}/rest/v1/<table>` with `apikey` and
  `Authorization: Bearer <anonKey>` headers (Supabase-compatible). GET with
  `?select=*`, POST with `Prefer: return=representation`, PATCH with
  `?id=eq.<id>`, DELETE with `?id=eq.<id>`.
- If a remote call fails, show a non-blocking error and fall back to read-only
  cached data. Never lose the user's edits silently.

## Interface requirements

1. Stat cards summarise the collection (counts, alerts, value totals).
2. Table: search box, status filter, sortable key columns, responsive card
   layout under 720px.
3. Create/edit dialog with real validation, focus trap, Escape to close and
   inline errors tied to labels.
4. Delete asks for confirmation and reports the removed record.
5. Empty state explains how to add the first record.

## Motion

Use GSAP only when `window.gsap` exists; animate `transform` and `opacity`,
stagger row entrance, and respect `prefers-reduced-motion`. Never animate
layout properties.

## Quality bar

- Adding a record survives a page reload (local mode).
- Remote mode never stores secrets in code; only the configured public/anon key.
- Keyboard-only users can operate every control.
- No inline event handlers; no `innerHTML` with user-supplied strings.

## Output contract

Return `{"files":[{"path":"index.html","content":"..."},...],"summary":"..."}`
with `index.html`, `styles.css`, `app.js` and `data-config.js` referenced in
that order; `data-config.js` must be linked before `app.js`.
