---
name: site-plan
description: Convert a sealed brief into a page graph, navigation model, content inventory and conversion paths that later modules can follow.
---

# Information Architecture

## Job

Turn the sealed brief into the site's structural plan: which pages exist, what
each page is for, which sections it contains and which goal it serves. Structure
only: this module never writes copy, picks visuals or builds pages.

## Inputs

- `brief` — `contracts/brief.schema.json`. Fields: `project.one_liner`,
  `audience[].needs`, `goals[].id`/`statement`, `pages_hint`, `constraints`,
  `non_goals`, `open_questions`; the raw request belongs to stage 1.

## Outputs

- Artifact: `site-plan` at `.stitch/02-plan/site-plan.json`; contract:
  `contracts/site-plan.schema.json`.
- Non-negotiable fields: `sitemap[].path` and `title`, `sitemap[].sections` and
  `goal_id`, `navigation.primary`, `content_inventory[].asset` and `status`, and
  `conversion_paths[].from` and `to`.

## Procedure

1. List the brief `goals` and map each id to at least one page. A goal without a
   page of its own is attached to the page that can make its case; never drop one.
2. Start from `pages_hint` and decide the real sitemap: keep, rename, merge or
   drop each suggestion. Every page gets a `/`-rooted `path`, `title`, `purpose`
   and `goal_id` from the brief.
3. For each page write ordered `sections`: only the page-content types `hero`,
   `features`, `showcase`, `testimonials`, `pricing`, `faq`, `cta`, `footer`,
   `rich-text`. Every content page starts with `hero`; only home may be a kitchen sink.
4. Define `primary_cta` per page as `{label, href}`; internal `href` values must
   resolve to a `sitemap` path, and external ones must be explained in `purpose`.
5. Build `navigation.primary` from top-level pages only, in reading order, plus
   `navigation.footer` for legal/contact/utility pages; every path must exist.
6. Fill `content_inventory` with every asset a page cannot render without: logo,
   photography, testimonials, pricing tables, legal copy. Set `source` to
   `client`, `generated`, `stock` or `copy`, and `status` to `needed`,
   `provided`, `drafted` or `approved`; carry over `brief.brand.assets`.
7. Define `conversion_paths` from each entry page to the conversion page(s), with
   the `trigger` that moves a visitor along ("pricing CTA on hero").
8. Check reachability: every page is in navigation or linked from a conversion
   path, with no orphan pages or dead ends; write the JSON and run
   `python -m stitchcraft validate`.

## Quality bar

- Every `sitemap[].path` starts with `/` and is unique; every page has `title`,
  `purpose` and `goal_id`.
- Every brief goal id appears on at least one page, and no `goal_id` exists that
  is absent from the brief.
- Every page's `sections` is non-empty and every section name is a valid
  `page-content` section type.
- Every `navigation.primary` path and every internal `primary_cta.href` resolves
  to a page in `sitemap`.
- Every `brief.brand.assets` entry appears in `content_inventory`.
- `python -m stitchcraft validate` passes.

## Hand-off

- Save `.stitch/02-plan/site-plan.json` and run `python -m stitchcraft validate`.
- Copy writes `page-content` from `sitemap[].sections` and `primary_cta`; Build
  maps every path to a route; SEO derives `sitemap.included_paths` from this.
- Unresolved content sourcing stays visible as `content_inventory[].status =
  "needed"`; structural unknowns go in a plan-level `open_questions` array
  (allowed by `additionalProperties`) rather than being guessed.
- If a page needs a section type this module cannot justify, resolve it here;
  copy and build are not allowed to invent structure.

## Failure modes

- **Pages without a goal.** Delete them or attach the goal they serve; a page
  that serves no goal is scope creep.
- **Sections written as prose.** Section names must be renderable types; move
  copy ambitions to the copy module.
- **Navigation invented from thin air.** Derive labels from page titles and check
  every path against the sitemap.
- **content_inventory skipped.** Build then has no asset story; list every asset
  the plan promises even when `status` is `needed`.
- **Design decisions leaking in.** No colors, fonts or component names here;
  those belong to design-system.
