# Roadmap

Stitchcraft is built in public, one seam at a time. Each version has a goal,
concrete deliverables and exit criteria; a version is done when its exit
criteria hold on `main`, not when its feature list is long.

**v0.1 is a scaffold, not a finished site builder.** It defines the pipeline,
contracts, nine skills and the Kiro governance layer, and ships a CLI that
validates and stages the stitch. It does not execute modules, generate a site or
deploy anything. Status: v0.1 complete in this repo; v0.2–v0.5 planned.

## v0.1 — Scaffold

**Goal.** Make the stitch real and checkable: one graph, nine modules, nine
contracts, a governance layer, and a deterministic CLI that proves the seams.

**Deliverables.** `pipeline/pipeline.toml` with nine stages, dependencies and
the QA gate; nine JSON Schema contracts; nine modules with `module.toml` and
`SKILL.md`; the Kiro layer (three steering files, a requirements/design/tasks
spec, four hooks); the dependency-free CLI with `list`, `show`, `validate
[--strict] [--json]`, `plan`, `doctor` and `run --dry-run`; a `unittest` suite
and CI on Python 3.12; documentation and the `coffee-roastery` seed request.

**Exit criteria.**

- `stitch validate --strict` exits `0`, the test suite passes, and CI is green
  including the dry-run smoke test.
- `stitch run --dry-run` writes nine `PROMPT.md` files naming the right skills,
  contracts and artifact paths.
- A new module folder plus contract plus `[[stages]]` entry appears in `list`,
  `plan` and dry-run prompts with no changes under `src/stitchcraft/`.
- A new reader can explain the flow after README and add a module from the guide.

## v0.2 — Agent runner

**Goal.** Execute the stitch instead of only staging it: walk the graph, run
skills through a built-in execution path, validate every artifact at the seam,
and resume after a failure.

**Deliverables.** A runner package executing stages in dependency order on the
same prompts dry runs write; JSON Schema validation of artifact instances, with
the engine behind an optional feature gate; a run manifest under `.stitch/` for
resume; gate semantics in code (continue on `pass`, require a human on
`conditional`, stop on `fail`); a built-in single-agent execution path, with
the general adapter protocol deferred to later work; `stitch run` without
`--dry-run`, tested for the happy path, gaps, gate stop and resume.

**Exit criteria.**

- One end-to-end run of the coffee-roastery request produces all nine artifacts,
  each validating against its contract.
- Killing the runner mid-pipeline and re-running resumes at the failed stage
  without overwriting completed artifacts.
- A `conditional` QA verdict cannot reach deploy without human approval; a `fail`
  verdict stops the run.
- The core CLI still installs and runs with no third-party dependencies.

## v0.3 — Site compiler and preview server

**Goal.** Compile `build-manifest` and `page-content` into a static site and preview it locally.

**Deliverables.** A compiler that renders routes, components and sections to
static HTML and CSS from `design-tokens`, `page-content` and `build-manifest`
only; asset handling from the manifest; sitemap input from `seo-report`; build
output separate from `.stitch/`; `stitch build` and `stitch preview`; snapshot
tests and deterministic output.

**Exit criteria.**

- The coffee-roastery example compiles all planned routes and every internal link
  resolves.
- `stitch preview` serves the built site and a reviewer can click every page.
- A11y and SEO findings can be checked against compiled output, not just planned
  artifacts.
- Two builds of the same artifacts produce identical files.

## v0.4 — Deploy adapters

**Goal.** Execute `deploy-plan` against real hosting providers while keeping
credentials and rollback in human hands.

**Deliverables.** Adapters for Cloudflare Pages, Vercel, Netlify and GitHub Pages
behind one protocol: `preflight()`, `deploy(plan)`, `status()`, `rollback()`.
Credential resolution from environment or provider secret stores, with the plan
recording only key names and sources. `stitch deploy --dry-run` and a
confirmation before any remote write, plus rollback tests.

**Exit criteria.**

- At least two providers deploy the compiled example end to end, with a
  documented preview URL.
- A failed deploy rolls back using only the plan artifact and recorded provider
  state.
- Secrets never appear in artifacts, logs, `.stitch/` or the repository.
- Adapters are optional extras; the core CLI remains dependency-free.

## v0.5 — Multi-profile pipelines and module marketplace

**Goal.** Make the pipeline composable: more than one profile (solo, agency,
landing page, documentation site) and third-party modules on the same seams.

**Deliverables.** Profile definitions that select stages, gates and module
versions, making `default_profile` active; validation and planning for optional,
replaced or extended stages; a module registry with install, verify and pin
tooling plus contract compatibility checks; a contract versioning policy with a
migration path; profile fixtures and tests for an alternative graph.

**Exit criteria.**

- Two profiles run the full pipeline on the same request with different module
  choices and gates.
- A third-party module installs, validates and runs with no `src/stitchcraft/` edits.
- An incompatible pin fails validation with a clear error and no partial run.
- A contract change is traceable across modules, profiles and the registry.

## How versions are decided

- A version ships only when its exit criteria are met and CI proves them.
- Contract changes are SemVer: widening is minor, narrowing is major.
- Runner precedes compiler, which precedes deploy adapters; dates are not promised.
