---
name: a11y
description: Audit the built routes against WCAG 2.2 AA, publish evidence and fixes, and never rewrite the copy it is checking.
---

# Accessibility Pass

## Job

Audit every built route against WCAG 2.2 AA, patch defects that are purely
structural or presentational, and seal evidence, remaining issues and keyboard
verdicts into an accessibility audit. Content and design decisions are reported,
never rewritten.

## Inputs

- `build-manifest` — `contracts/build-manifest.schema.json`. Fields:
  `routes[].path`/`file`, `components[].name`/`file`, `assets[].file`/`alt`,
  `build.output`.
- `page-content` — `contracts/page-content.schema.json`. Fields:
  `pages[].sections[].type`/`headline`/`media.alt`, `global.nav_labels`, `meta`.

## Outputs

- Artifact: `a11y-audit` at `.stitch/07-a11y/a11y-audit.json`; contract
  `contracts/a11y-audit.schema.json`.
- Non-negotiable fields: `standard` exactly `WCAG 2.2 AA`, `checks[].id`/
  `status`/`path`, `issues[].severity`/`path`/`summary`/`fix`,
  `keyboard.tab_order_ok`/`focus_visible`/`skip_link`, `summary.pass`/`fail`/`manual`.

## Procedure

1. Build a fixed check list from the routes and components: alt text (1.1.1),
   heading order and landmarks (1.3.1), contrast (1.4.3), reflow (1.4.10),
   keyboard (2.1.1), focus visible (2.4.7), focus not obscured (2.4.11), target
   size (2.5.8), link purpose (2.4.4), form labels and errors (3.3.1/3.3.2), and
   reduced motion.
2. Run the checks against the built output and page-content: compare
   `assets[].alt` with `media.alt`, inspect heading order per page, confirm every
   interactive element is reachable, and compute contrast from rendered colors.
3. Patch only safe structural fixes in the built files: skip link, landmarks,
   heading levels, visible focus styles, control labels, reduced motion. Keep each
   patch minimal and record it in the issue `fix` text.
4. Where a defect needs content judgement (alt text with no factual basis, link
   text, error copy), do not invent it: record an issue with `severity` and an
   actionable `fix` naming the owning module.
5. Record one `checks[]` row per check per route with `id`, `path`, `status`
   (`pass`, `fail`, `manual`) and `notes`; use `manual` honestly for anything that
   needs a human or a browser you cannot drive.
6. Fill `issues[]` only for `fail` rows and serious manual risks: `severity`
   (`minor`, `serious`, `critical`), `path`, `selector` where known, `summary`,
   `fix`. Critical blocks QA.
7. Walk the tab order on home and one interactive page to fill `keyboard`
   (`tab_order_ok`, `focus_visible`, `skip_link`), then re-run affected checks.
8. Fill `summary` counts from `checks`, write the JSON and run
   `python -m stitchcraft validate`.

## Quality bar

- `standard` is exactly `"WCAG 2.2 AA"` and `checks` is non-empty.
- Every route has at least one check; no check points at a nonexistent path.
- Every `fail` check has an `issues[]` entry with severity, path, summary and fix.
- `keyboard` booleans are present and reflect a real inspection, not defaults.
- `summary` counts equal the number of pass, fail and manual check rows.
- `python -m stitchcraft validate` passes.

## Hand-off

- Save `.stitch/07-a11y/a11y-audit.json` and run `python -m stitchcraft validate`.
- QA treats `critical` issues as blockers and forwards each to its owning module.
- Fixes that belong to copy (alt text, link text) or design-system (contrast
  tokens) are listed as issues, never applied silently.
- Human-judgement questions go in a top-level `open_questions` array (allowed by
  `additionalProperties`).

## Failure modes

- **Auditing only the home page.** Interior pages carry most form and heading defects.
- **Passing checks you did not run.** Use `manual`; a false pass is the worst bug here.
- **Patching copy to fix a label.** Report the issue against copy instead.
- **Trusting design tokens for contrast.** Measure the rendered output.
- **Summary counts drifting from check rows.** Recompute them before saving.
