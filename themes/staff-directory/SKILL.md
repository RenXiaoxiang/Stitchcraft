---
name: staff-directory
description: Build an indigo-and-lime people directory with employee cards, department groupings and onboarding checklists.
---

# Staff Directory

## Job
Generate a people-first staff directory for a growing company: searchable employee cards grouped by department, a detail drawer with contact and profile information, department snapshots and an onboarding checklist that keeps new hires moving. The site is a data app with seeded, editable people data.

## When to use
- The user runs HR, people operations or a growing team and asks for a staff directory, team page, org chart or onboarding tracker.
- They want internal lookup, not recruitment marketing.
- The brief mentions departments, headcount, new hires or employee records.

## Data model
Read `data-model.json`; three writable collections.
- `employees`: `id`, `name`, `role`, `department`, `email`, `location`, `started_on`, `status`.
- `departments`: `name`, `head`, `headcount`, `location`, `budget_line`.
- `onboarding_tasks`: `id`, `employee_id`, `task`, `owner`, `due_on`, `done`.
Seed 14-20 employees across 5 departments and 6-10 onboarding tasks. Use initials for avatars, never photos. Derive department headcounts from employees rather than trusting the static number.

## Layout blueprint
1. Top bar: company name, page title, global search shortcut, `Add employee`.
2. Hero: short line about the company, headcount and location summary, search.
3. Stat grid: total headcount, departments, open roles, onboarding in progress.
4. Directory: department filter chips, status filter, employee cards grouped by department with initials, role, email and location; table view toggle for dense screens.
5. Detail drawer: profile, contact links, start date, onboarding checklist with progress bar.
6. CRUD modal: add/edit employee with labelled fields; deactivate uses a confirm dialog, never a bare click.

## Components
Use `themes/_blocks/`: `stat-grid` (KPI cards), `data-table` (dense toggle), `crud-modal` (add/edit dialog), `hero` (compact directory header). Build the employee card and department group locally; they are theme-specific.

## Motion
Only `transform` and `opacity`, guarded by `if (window.gsap)`.
- Entrance: cards stagger 0.03s with y 12px and opacity, 0.4s `power2.out`.
- Filtering: animate the incoming card grid with a short fade; never re-animate the whole page.
- Drawer: slide in 24px from the right; scrim fades. Modal scales 0.97 to 1.
- Respect `prefers-reduced-motion`; no looping animation anywhere.

## Data layer
Local mode seeds `localStorage` under a namespaced key and persists every create, update and delete; wrap access in try/catch so `file://` works. Remote mode comes from generation settings: `window.STITCHCRAFT_DATA = {mode:"remote", apiBase:"..."}` or `data-data-mode`/`data-api-base` on `<body>`. Use one REST adapter over `employees`, `departments` and `onboarding_tasks`; show an offline badge and the local copy when a request fails.

## Quality bar
- Deep indigo (#141834, panels #1d2350) with lime (#b6f24a) reserved for actions, focus and live status; never lime body text on light backgrounds.
- Directory feel: initials tiles, department rules, compact metadata lines, tabular numbers for headcount.
- Responsive: 3-4 cards per row at 1440px, one column at 390px; filters wrap.
- Accessible: `fieldset`/`legend` for filters, labelled search, visible focus, drawer focus trap, Escape closes, empty state per department.
- Status is never colour-only (Active / On leave / New hire text labels).

## Output contract
Return only `{"files":[{"path","content"}],"summary":"..."}` with `index.html`, `styles.css` and `app.js` required. No external fonts, images or CDNs; relative assets only. `summary` states the seeded headcount, data mode and any endpoint.
