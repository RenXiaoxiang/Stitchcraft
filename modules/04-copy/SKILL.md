---
name: copy
description: Write every planned page section in the brief's voice and hand the build a complete, render-ready page-content artifact.
---

# Copywriting

## Job

Write every planned page section in the brief's voice, address the audience needs
and carry each page to its primary CTA. Content only: this module never changes
structure, design or code.

## Inputs

- `brief` — `contracts/brief.schema.json`. Fields: `audience[].needs`,
  `goals[].statement`, `brand.tone`, `non_goals`, `open_questions`.
- `site-plan` — `contracts/site-plan.schema.json`. Fields: `sitemap[].path`,
  `sections`, `primary_cta`, `navigation.primary`, `content_inventory`.

## Outputs

- Artifact: `page-content` at `.stitch/04-copy/page-content.json`; contract
  `contracts/page-content.schema.json`.
- Non-negotiable fields: `pages[].path` matching the plan, `sections[].id` and
  `type`, `headline`/`body` per section, `cta.label`/`href`, `media.alt`, and
  `meta[].title`/`description`.

## Procedure

1. Create one `pages[]` entry per `site-plan.sitemap` page, preserving `path` and
   `title`. Never add, remove or reorder pages here.
2. Map each planned section name to a `type` enum value (`hero`, `features`,
   `showcase`, `testimonials`, `pricing`, `faq`, `cta`, `footer`, `rich-text`) and
   give it a stable `id` such as `home-hero`.
3. Write `hero` first: `headline` states the offer and audience, `subhead` adds
   proof or specificity, and `cta` reuses the plan `primary_cta` label and href.
4. Write `body` for content sections as short paragraphs that answer
   `brief.audience[].needs`; use `items` for features, showcase, pricing, faq and
   testimonials with real names, values and answers. No lorem ipsum or brackets.
5. Add `media` only when the section has an approved asset; `media.alt` is a
   concrete image description and `media.src` matches `content_inventory`.
6. Place `cta` objects where `site-plan.conversion_paths` expect them; labels are
   verbs and every `href` matches a planned path or CTA.
7. Fill `global.nav_labels` from `navigation.primary` in order, `global.footer`
   with contact/legal/social lines, and one `meta` row per page with a unique
   title (<=60 chars) and description (<=160 chars).
8. Read the artifact as the build module: every section renders with no question.
   Then write the JSON and run `python -m stitchcraft validate`.

## Quality bar

- `pages[].path` values equal the plan paths exactly; every page has a section.
- Every `sections[].type` is one of the nine enum values, with `id` unique site-wide.
- No lorem ipsum, placeholders, brackets or duplicated headlines.
- Every image-bearing section has non-empty `media.alt` and an approved source.
- Every page has `meta`, titles are unique, and every CTA href resolves.
- `python -m stitchcraft validate` passes.

## Hand-off

- Save `.stitch/04-copy/page-content.json` and run `python -m stitchcraft validate`.
- Build renders sections by `type`, SEO reads `meta[]`, and accessibility checks
  `media.alt` and heading order; they trust this artifact without asking you.
- Unverified claims, missing proof or undecided pricing go in a top-level
  `open_questions` array (allowed by `additionalProperties`), never invented.
- If the plan needs a section that does not exist, request a site-plan change.

## Failure modes

- **Copying the plan verbatim.** Section names are structure, not headlines.
- **Inventing proof, prices or legal claims.** Defend the claim or flag it.
- **Writing unplanned pages.** Build has no route; change site-plan instead.
- **CTA to nowhere.** Every `cta.href` must match a planned path or CTA.
- **Lorem ipsum shipped as final.** It validates as a string and ruins the site.
