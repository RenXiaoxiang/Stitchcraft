---
name: qa
description: Run the release gate over build, links, SEO, accessibility and performance, then publish a verdict that deploy can trust.
---

# Release Gate

## Job

Act as the pipeline's guard: prove the site builds, its links resolve, and the SEO
and accessibility evidence is good enough to release, then issue one verdict deploy
must obey. This module reports and routes blockers; it fixes nothing itself.

## Inputs

- `build-manifest` — `contracts/build-manifest.schema.json`. Fields:
  `build.command`/`output`/`env`, `routes[].path`/`file`, `assets`.
- `seo-report` — `contracts/seo-report.schema.json`. Fields: `issues[].severity`,
  `meta[]`, `sitemap.included_paths`, `robots`.
- `a11y-audit` — `contracts/a11y-audit.schema.json`. Fields: `standard`,
  `checks[]`, `issues[].severity`, `keyboard`, `summary`.

## Outputs

- Artifact: `qa-report` at `.stitch/08-qa/qa-report.json`; contract
  `contracts/qa-report.schema.json`.
- Non-negotiable fields: `verdict` (`pass`, `conditional`, `fail`),
  `build.status`, `links.checked`/`broken[]`, `performance.lighthouse` when
  measured, `blockers[].id`/`severity`/`owner_module`/`summary`, `release_notes`.

## Procedure

1. Run `build-manifest.build.command` from a clean state with the `build.env` keys
   available; record `build.status` and `duration_s`. A failed build is a `fail`
   verdict immediately.
2. Confirm every `routes[].file` exists under `build.output`; a missing page is a
   blocker owned by `build`.
3. Crawl the built output: collect every internal `href`, resolve it against
   `routes[].path`, and fill `links.checked` plus `links.broken[]` with `href` and
   `from` for every failure.
4. Roll up `seo-report`: each `issues[]` row with `severity: "error"` becomes a
   blocker owned by `seo` or `copy`; warnings go in `release_notes` only.
5. Roll up `a11y-audit`: each `critical` issue becomes a blocker owned by the
   module named in its `fix`; a false `keyboard` boolean becomes a `build` blocker.
6. Measure Lighthouse on home and one interior page when available and record
   scores under `performance.lighthouse`; if unavailable, omit scores and say so
   in `release_notes`. Never invent numbers.
7. Set `verdict`: `fail` if the build failed, a link is broken or any `blocker`
   remains; `conditional` if only `major`/`minor` blockers remain with owners;
   otherwise `pass`.
8. Fill `blockers[]` with unique ids (`QA-1`, `QA-2`, ...), schema severities,
   valid `owner_module` ids and summaries that state defect plus expected fix.
9. Write `release_notes` explaining the verdict, write the JSON and run
   `python -m stitchcraft validate`.

## Quality bar

- `verdict` is consistent with `build.status`, `links.broken` and blocker
  severities; no `pass` coexists with a blocker.
- Every blocker has a unique id, a valid `owner_module` and a defect summary.
- `links.checked` equals the number of links resolved; every broken link appears
  in `links.broken` with `href` and `from`.
- Lighthouse scores, when present, are 0-100 and came from a real run.
- `release_notes` explains every `conditional` or `fail` verdict.
- `python -m stitchcraft validate` passes.

## Hand-off

- Save `.stitch/08-qa/qa-report.json` and run `python -m stitchcraft validate`.
  This artifact is the gate; deploy must refuse `fail`.
- Deploy reads `verdict` and `release_notes`; a `conditional` report must name
  residual risks so deploy can decide with open eyes.
- Blockers return to their owning modules through the pipeline owner; QA does not
  edit copy, tokens or build files.
- An unownable blocker goes in `release_notes`; the gate stays closed.

## Failure modes

- **Passing without running the build.** `build.status` needs a real run.
- **Fixing defects inside QA.** That collapses the gate; record a blocker.
- **Broken links only spot-checked.** Crawl every internal href.
- **Conditional verdict without owners.** Unowned blockers mean `fail`.
- **Invented Lighthouse scores.** Omit unmeasured performance and say so.
