---
name: seo
description: Produce the metadata, structured data, sitemap and robots policy the built site needs to be discoverable and indexable.
---

# Discovery Layer

## Job

Produce the complete discovery layer for the built routes: per-page metadata,
structured data, a sitemap and a robots policy. It reports content problems as
issues instead of rewriting copy.

## Inputs

- `build-manifest` — `contracts/build-manifest.schema.json`. Fields:
  `routes[].path`/`file`/`goal_id`, `stack`, `build.output`, `assets`.
- `page-content` — `contracts/page-content.schema.json`. Fields:
  `pages[].path`/`title`/`sections[].type`, `meta[].title`/`description`, `global`.
- `site-plan` — `contracts/site-plan.schema.json`. Fields: `sitemap[].path`,
  `title`, `goal_id`, `navigation.footer`.

## Outputs

- Artifact: `seo-report` at `.stitch/06-seo/seo-report.json`; contract
  `contracts/seo-report.schema.json`.
- Non-negotiable fields: `meta[].path`/`title`/`description`,
  `structured_data[].path`/`type`/`status`, `sitemap.url`/`included_paths`,
  `robots.allow`, `issues[].severity`/`path`/`message`.

## Procedure

1. Match every `build-manifest.routes` path to its `page-content.pages` and
   `site-plan.sitemap` entry; a route without both is an `error` issue.
2. Write one `meta` row per route: `title` from page-content `meta` (fallback to
   `title`), `description` from `meta.description`, and `title_length`/
   `description_length` as real character counts. Flag titles over 60 or
   descriptions over 160 as warnings; never silently truncate.
3. Set `canonical` as origin plus path, and `og_image` from the route's first
   image asset where one exists.
4. Assign `structured_data` per page (`WebSite`/`Organization` on `/`,
   `Product`/`Offer` on pricing, `FAQPage` for `faq`, `BreadcrumbList` on interior
   pages) and set `status` to `valid`, `invalid` or `missing` from real content.
5. Build `sitemap` with `url` for its absolute location and `included_paths`
   exactly the indexable routes. Base the origin only on absolute URLs in the
   consumed artifacts; if none exists use `https://example.com`, add a warning
   issue and an open question; never read the brief or deploy plan.
6. Set `robots.allow` for the public site, `disallow` for non-public paths and
   `sitemap_ref` equal to `sitemap.url`.
7. Record `issues[]` for duplicate titles or descriptions, missing canonical,
   invalid structured data, thin pages and routes missing from the sitemap; use
   `error` only for defects that must block QA.
8. Check counts (one meta row per route, included paths a subset of routes),
   write the JSON and run `python -m stitchcraft validate`.

## Quality bar

- Exactly one `meta` row per built route, with lengths matching real strings.
- Every `meta` entry has non-empty `title` and `description`; duplicates reported.
- `sitemap.included_paths` is a subset of route paths and covers every indexable
  page; `sitemap.url` and `robots.sitemap_ref` are absolute and agree.
- Every page has a `structured_data` decision, including `missing` with a note.
- Every `issues[]` entry has `severity`, `path` and `message`.
- `python -m stitchcraft validate` passes.

## Hand-off

- Save `.stitch/06-seo/seo-report.json` and run `python -m stitchcraft validate`.
- QA fails on any `issues[]` row with `severity: "error"`; deploy needs the
  sitemap and robots expectations for post-deploy checks.
- Content problems (long titles, thin pages, duplicate descriptions) belong to
  copy: report them here and let QA route the blocker.
- A missing site origin goes in a top-level `open_questions` array (allowed by
  `additionalProperties`); deploy owns the final domain.

## Failure modes

- **Rewriting copy to fit limits.** This module reports; copy edits.
- **Structured data marked valid without evidence.** Use `invalid` or `missing`.
- **Sitemap built from memory.** Derive paths from `build-manifest.routes`.
- **Origin invented or scraped from the brief.** Use consumed artifacts, flag it.
- **Noindex pages bundled into the sitemap.** Keep metadata; exclude the paths.
