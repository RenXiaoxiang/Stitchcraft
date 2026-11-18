# Product Steering

Stitchcraft is a solo AI site builder: specialised skills stitched into one
pipeline, each module doing one job, with Kiro specs and hooks holding the seams.

## Vision

A solo builder and an AI agent ship a complete, accessible, search-ready
marketing site from a raw request in one run, with every hand-off checked.

## Target user

One person building one site: a founder, freelancer or designer-engineer with a
coding agent such as Kiro. No team, no design system, no copywriter: they review
artifacts, approve gates and edit files while the agent does the rest.

## The problem

Ask one generalist agent to run intake, IA, design, copy, build, SEO, a11y, QA
and deploy in one context window and quality degrades predictably:

- The brief drifts: by the hero copy, the audience is three summarisations old.
- Every stage is done "well enough" by one generalist, and evidence disappears;
  nothing downstream can prove what it was handed.
- Seams break silently: copy ignores the plan, the build ignores the tokens, QA
  finds the defect the accessibility pass was meant to catch.

## The stitch answer

Nine narrow modules, one artifact each, wired into a fixed pipeline:

1. `brief` - Brief Intake
2. `site-plan` - Information Architecture
3. `design-system` - Design System
4. `copy` - Copywriting
5. `build` - Site Assembly
6. `seo` - Discovery Layer
7. `a11y` - Accessibility Pass
8. `qa` - Release Gate (gated)
9. `deploy` - Ship It

A module is a `SKILL.md` procedure plus a `module.toml` manifest. A seam is a
JSON Schema contract in `contracts/`. A stage output is a sealed artifact at
`.stitch/<NN>-<stage>/<artifact>.json`. `pipeline/pipeline.toml` wires the graph,
Kiro steering carries global rules, Kiro specs describe the build, and Kiro hooks
re-check the seams whenever they are edited.

## Five principles

1. **One module, one job.** A module owns exactly one artifact; two jobs means two modules.
2. **Artifacts, not conversations.** Context crosses a seam only as a schema-validated JSON file, never as remembered prose.
3. **Specs before code.** Requirements, design and tasks describe the work first; the code follows the spec, not the reverse.
4. **Hooks enforce seams.** A rule without a check is a suggestion; hooks run the validator after relevant edits.
5. **Boring, portable tech.** Python standard library, JSON, TOML, Markdown - technology a solo builder can maintain anywhere.

## What "done" means

- `stitch validate --strict` exits clean; `stitch plan` renders all nine stages.
- Every declared input exists upstream; every artifact has a contract.
- `stitch run --dry-run` writes one prompt per stage naming its artifact path
  and contract, and changes nothing else.
- Steering, specs and hooks describe the same pipeline as the code and contracts.

## Non-goals

- A hosted SaaS, dashboard or account system.
- A general-purpose CMS, page builder or component marketplace.
- Fine-tuned models, vector stores or an agent framework.
- Framework-specific code generators: the build module picks the stack; Stitchcraft ships the plan, not the generator.
- Replacing human judgement: gates and dry runs exist so the builder decides.
