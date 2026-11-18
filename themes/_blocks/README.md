# Shared theme blocks

`themes/_blocks/` is a library of **self-contained HTML snippets**, not an import
system. A theme package copies the blocks it needs and adapts the copy; nothing
at runtime resolves these files, so editing a block never changes a generated
site.

Each block is one file — markup + a scoped inline `<style>` + a comment at the
top listing the fields that are safe to replace. Blocks are kept deliberately
small (30–80 lines) so they fit an AI prompt budget and are easy to re-style.

## Contract

- **Semantic HTML** — one landmark per block, real headings, `<table>` with
  `<caption>` and `scope`, `<dl>` for label/value pairs, `<dialog>` for modals.
- **Scoped styles** — every rule hangs off a `blk-*` root class, and the style
  element may be deleted once the theme CSS has equivalents. No global resets,
  no `body`, `*` or bare-element rules.
- **Themeable colours** — every colour is a CSS variable with a fallback, e.g.
  `var(--block-panel, var(--panel, #12161d))`, so a block works on dark and
  light surfaces without edits.
- **Container-friendly** — block roots declare `container-type: inline-size`
  and use `@container` queries plus `clamp()` type, so a block can sit in a
  wide dashboard column or a narrow rail.
- **No external assets** — no fonts, images, scripts or CDNs. Icons are glyphs
  or inline SVG; status colours are always paired with a text label.
- **Accessible by default** — labels on every control, `aria-live` for changing
  counts, visible `:focus-visible`, decorative glyphs marked `aria-hidden`, and
  `prefers-reduced-motion` guards on any transition.
- **Motion is optional** — blocks ship without JavaScript. Transition only
  `transform`/`opacity`, and only when `window.gsap` exists (or let CSS do a
  one-shot `@keyframes` fallback).

## Index

| Block | Purpose | Used by |
| --- | --- | --- |
| `hero.html` | Compact page header: eyebrow, title, lede, actions. | warehouse-ops, staff-directory, personal-space, brand-launch |
| `stat-grid.html` | Four KPI cards with tabular numerals and deltas. | warehouse-ops, staff-directory, logistics-control, brand-launch |
| `data-table.html` | Search + filter inventory table with status pills and row actions; stacks to cards. | warehouse-ops, staff-directory, logistics-control |
| `crud-modal.html` | Native `<dialog>` create/edit form with labelled fields and inline errors. | warehouse-ops, staff-directory, logistics-control |
| `article-list.html` | Editorial essay list: dates, excerpts, reading time, tags. | personal-space |
| `photo-masonry.html` | CSS-column photo wall built from gradients and glyphs. | personal-space |
| `timeline.html` | Vertical activity/ETA timeline with status markers. | personal-space, logistics-control, brand-launch |
| `cta-band.html` | Full-width call-to-action band with two actions. | brand-launch, personal-space |

## Adapting a block

1. Copy the markup into the theme's sample or generated page.
2. Replace the placeholder fields listed in the top comment; keep heading order
   (`<h1>` once per page) and keep every form control labelled.
3. Either keep the inline `<style>` or port its rules into the theme stylesheet,
   replacing the `--block-*` fallbacks with the theme's palette.
4. Add behaviour in the theme's `app.js`; blocks contain no JavaScript. Use
   event delegation and `textContent` for user data (never `innerHTML`).
5. Test at 1440px and 390px, with keyboard only, and with
   `prefers-reduced-motion: reduce` enabled.
