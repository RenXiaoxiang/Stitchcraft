---
name: build
description: Assemble the planned routes and components into a static site and record a reproducible build manifest for later stages.
---

# Site Assembly

## Job

Turn the approved plan, page content and design tokens into a working static site,
then seal what was built (framework, routes, components, assets, build settings)
into a build manifest. Never rewrite copy or invent tokens here.

## Inputs

- `site-plan` — `contracts/site-plan.schema.json`. Fields: `sitemap[].path`,
  `title`, `goal_id`, `navigation`, `content_inventory`.
- `page-content` — `contracts/page-content.schema.json`. Fields: `pages[].path`,
  `sections[].type`/`id`/`media`, `global`, `meta`.
- `design-tokens` — `contracts/design-tokens.schema.json`. Fields: `color.roles`,
  `typography.scale`, `spacing`, `components`, `motion`.

## Outputs

- Artifact: `build-manifest` at `.stitch/05-build/build-manifest.json`; contract
  `contracts/build-manifest.schema.json`.
- Non-negotiable fields: `stack.framework`/`runtime`, `routes[].path`/`file`,
  `components[].name`/`file`, `assets[].file`/`alt`, `build.command`/`output`.

## Procedure

1. Choose the framework from the enum (`astro`, `next-static`, `sveltekit-static`,
   `eleventy`, `hugo`, `plain-html`); default to `astro` with `runtime: "static"`
   unless the plan or constraints clearly require otherwise.
2. Map every `sitemap[].path` to one `routes[]` entry with `path`, generated
   `file` (for example `site/index.astro`) and the plan `goal_id`; every
   page-content page gets a route and every route a page.
3. Generate route files from `page-content.sections`, shared components and a
   layout built from `site-plan.navigation`; generate CSS custom properties from
   the tokens. Keep sources in one project folder and record every path.
4. Create `components[]` for every section type and layout part actually used:
   `name`, `file`, `props`, `variants`. No orphan components and no unrendered
   section types.
5. Build `assets[]` from page-content `media[].src`/`alt` plus provided
   `content_inventory` entries; every asset keeps the exact `alt` text.
6. Fill `build` with the exact `command`, the `output` directory, the `env` keys
   the build reads and `node_version` where relevant.
7. Run the command from a clean state; fix failures until it exits 0 and the
   output directory contains one HTML file per route.
8. Write the JSON and run `python -m stitchcraft validate`; reconcile every
   manifest entry with a real file. The manifest describes what exists.

## Quality bar

- `routes[].path` equals `site-plan.sitemap[].path` exactly; every route `file`
  exists after a clean build.
- `stack.framework` is one of the six enum values; `runtime` is `static` unless
  the brief explicitly requires otherwise.
- Every section type used in page-content has a matching `components[]` entry.
- Every `assets[]` entry has a `file`; every image-bearing `alt` is preserved.
- `build.command` exits 0 and `build.output` contains the expected pages.
- `python -m stitchcraft validate` passes.

## Hand-off

- Save `.stitch/05-build/build-manifest.json` and run `python -m stitchcraft validate`.
- SEO derives metadata and sitemap paths from `routes`; accessibility audits
  `routes[].file`; QA runs `build.command`; deploy needs `build.command` and
  `build.output`.
- Missing assets or unresolved stack constraints go in a top-level
  `open_questions` array (allowed by `additionalProperties`), not in fake routes.
- If page-content or tokens are wrong, report it to the owning module; the build
  stage does not edit them.

## Failure modes

- **Manifest diverges from disk.** Never list a route you did not generate.
- **Adding pages absent from the plan.** Structure belongs to site-plan.
- **Alt text lost during rendering.** Missing alt is an accessibility defect.
- **Hardcoded colors or type outside tokens.** Style through token variables only.
- **Build failing at hand-off.** Fix and regenerate the manifest before QA.
