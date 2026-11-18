---
name: design-system
description: Choose one visual direction and express it as design tokens for color, type, spacing, motion and components that the build stage can consume.
---

# Design System

## Job

Translate the brief's brand tone and constraints into a single visual direction
expressed as tokens: color roles, type families and scale, spacing, motion and the
component inventory the site plan requires. No markup and no copy are produced here.

## Inputs

- `brief` — `contracts/brief.schema.json`. Fields: `project.name`,
  `project.one_liner`, `brand.tone`, `brand.constraints`, `brand.assets`, `constraints`.
- `site-plan` — `contracts/site-plan.schema.json`. Fields: `sitemap[].sections`,
  `navigation`, `conversion_paths`; these decide which components must exist.

## Outputs

- Artifact: `design-tokens` at `.stitch/03-design/design-tokens.json`; contract:
  `contracts/design-tokens.schema.json`.
- Non-negotiable fields: `direction.name`/`keywords`, `color.roles` including
  `focus`, `typography.families`/`scale`, `spacing`, `components[].name`.

## Procedure

1. Re-read `brief.brand.tone` and `constraints` and choose one named `direction`
   with three to five `keywords`, a `rationale` and only supplied `references`.
2. Define semantic `color.roles`: `surface`, `text`, `muted`, `primary`, `accent`,
   `border`, `focus`, `success`, `danger`, each a CSS color. Compute contrast
   pairs, require 4.5:1 for body text and 3:1 for large text, focus and borders,
   record measured pairs under `color.contrast`, and set `contrast_checked` true.
3. Choose `typography.families` (`display`, `body`, `mono`) from system or
   licensed fonts allowed by `constraints`. Build `typography.scale` from `xs` to
   `3xl`, each with `size`, `line_height`, `weight`; body line-height 1.4-1.7.
4. Define `spacing.unit` (for example `4px`) and a numeric `spacing.scale` such
   as 4, 8, 12, 16, 24, 32, 48, 64 that every component shares.
5. Set `motion.durations`, `motion.easing` and `motion.reduced_motion_fallback`.
   The fallback must describe real behaviour, not "ignore motion".
6. Inventory components from `site-plan.sitemap[].sections` and `navigation`:
   header/nav, footer, hero, card, cta, form controls, one per section type, each
   with `name`, `variants`, `states`, `notes`; no CSS or page-specific styles.
7. Verify coverage: every section type in the plan maps to a component or to a
   documented `rich-text` layout, and every navigation element has states.
8. Write the JSON and run `python -m stitchcraft validate`; re-read as the build
   module: are token names stable enough to generate CSS custom properties?

## Quality bar

- `direction.keywords` has at least three entries and `direction.rationale`
  connects them to `brief.brand.tone`.
- `color.roles` contains `text`, `surface`, `primary`, `accent`, `border`, `focus`;
  `contrast_checked` is true with recorded ratios of at least 4.5:1 for text or
  3:1 for large text and UI.
- Every `typography.scale` step has `step`, `size` and `line_height`.
- `spacing`, `motion` and `components` are populated with real values, easing and
  states, not placeholders.
- Every section type in `site-plan.sitemap[].sections` maps to a token component.
- `python -m stitchcraft validate` passes.

## Hand-off

- Save `.stitch/03-design/design-tokens.json` and run `python -m stitchcraft validate`.
- Build reads this as the only visual source of truth and turns the roles, scale
  and spacing into CSS variables; decide stable names once.
- Accessibility verifies focus, contrast and reduced-motion in the built output;
  token claims are not evidence.
- Untested font licensing or brand constraints go in a top-level `open_questions`
  array (allowed by `additionalProperties`), not into invented values.

## Failure modes

- **Moodboard instead of tokens.** A direction without roles, scale and
  components is unusable; convert every choice into a value.
- **Decorative palette without roles.** Build cannot map hex colors to purpose;
  assign roles and check each pair.
- **Contrast claimed but never measured.** Either measure and record ratios or
  set `contrast_checked` false; never claim true without numbers.
- **Components invented beyond the plan.** Every component must be justified by a
  plan section or navigation element.
- **Page-specific styling.** Tokens are shared; one-off styles still follow them.
