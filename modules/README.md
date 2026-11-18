# Modules

A module is one job in the Stitchcraft pipeline. It is not a library, an agent
or a folder of shared code: it is a skill an AI agent follows plus a manifest
that declares which contract-checked artifacts the job reads and writes. Modules
never call each other; the only thing that crosses a stage boundary is an
artifact in `.stitch/`, validated against a schema in `contracts/`.

## What a module is

- One module, one job. If you need two different verbs, you need two modules.
- The manifest is the module's contract with the pipeline; the skill is the
  contract with the agent. Neither may quietly grow a second job.
- Modules are replaceable. A different agent, run against the same artifacts
  with the same skill, must produce an artifact that passes the same schema.
- A module may read only the artifacts named in `consumes`, and only through
  fields declared in their contracts. It may write only the artifact in
  `produces`.

A module may not: read another module's `SKILL.md` and copy its behaviour, read
the client's raw request after stage 1, edit another module's artifact, or fix a
downstream problem by guessing upstream. Each of those is a seam violation.

## Anatomy

Every module lives in `modules/<NN>-<slug>/` and contains exactly two files:

| File | Purpose |
| --- | --- |
| `module.toml` | Manifest: one `[module]` table with `id`, `name`, `stage`, `summary`, `skill`, `consumes`, `produces`, `gate`. |
| `SKILL.md` | The job: YAML frontmatter (`name` = module id, `description` = what and when), then Job, Inputs, Outputs, Procedure, Quality bar, Hand-off, Failure modes. |

The third piece sits outside the folder: `contracts/<artifact>.schema.json` for
every artifact listed in `produces`. That schema is what the next module is
allowed to trust; the skill is how the artifact gets made.

## The nine modules

| # | Folder | id | Name | Consumes | Produces |
| --- | --- | --- | --- | --- | --- |
| 1 | `01-brief` | `brief` | Brief Intake | none | `brief` |
| 2 | `02-site-plan` | `site-plan` | Information Architecture | `brief` | `site-plan` |
| 3 | `03-design-system` | `design-system` | Design System | `brief`, `site-plan` | `design-tokens` |
| 4 | `04-copy` | `copy` | Copywriting | `brief`, `site-plan` | `page-content` |
| 5 | `05-build` | `build` | Site Assembly | `design-tokens`, `page-content`, `site-plan` | `build-manifest` |
| 6 | `06-seo` | `seo` | Discovery Layer | `build-manifest`, `page-content`, `site-plan` | `seo-report` |
| 7 | `07-a11y` | `a11y` | Accessibility Pass | `build-manifest`, `page-content` | `a11y-audit` |
| 8 | `08-qa` | `qa` | Release Gate | `build-manifest`, `seo-report`, `a11y-audit` | `qa-report` (gate) |
| 9 | `09-deploy` | `deploy` | Ship It | `build-manifest`, `qa-report` | `deploy-plan` |

## How to add a module

1. Define the seam. Name the one artifact that enters and the one that leaves.
   If the job needs data no upstream artifact carries, fix the upstream contract
   first; do not add a side channel.
2. Write the contract. Add `contracts/<artifact>.schema.json` with the minimum
   downstream modules need. Keep `additionalProperties: true` so evidence can
   travel without breaking the seam.
3. Create the folder. `modules/<NN>-<slug>/`, with `NN` one greater than the
   current last stage and `<slug>` equal to the module id.
4. Write the manifest. Add a single `[module]` table with id, name, stage,
   summary, skill, consumes, produces and gate. `consumes` must list exactly the
   artifacts the skill reads; the validator compares manifest, skill and pipeline.
5. Write the skill. Fill the seven sections in order, make the procedure
   executable by a coding agent, and use real contract field names.
6. Wire the pipeline. Add a `[[stages]]` entry in `pipeline/pipeline.toml` whose
   `depends_on` names the stages that produce the consumed artifacts.
7. Prove it. Run `python -m stitchcraft validate` and `python -m stitchcraft
   plan`; then run `python -m stitchcraft run --dry-run` and confirm the new
   prompt folder and artifact path appear.

## The contract rule

Never read another module's internals. That means no imports, no reading its
`SKILL.md` to copy behaviour, no scraping files it wrote outside its contract,
and no reaching back to the raw request because it happens to be on disk. If an
artifact is missing a field the module needs, amend the schema and the producing
module, then re-run the pipeline. The seam is the product.

## Writing a good SKILL.md

- One job per skill. The Job section is one to three sentences, and the
  procedure never ventures into another module's artifacts.
- Numbered procedure, five to nine steps, concrete verbs (ask, decide, write,
  verify) and real field names such as `sitemap[].goal_id`.
- A quality bar the agent can check mechanically, not taste-based adjectives.
- A hand-off that names the exact artifact path and the validation command.
- Failure modes with fixes, especially "record it in `open_questions` instead of
  inventing a fact".
- Refuse work that belongs to another module by name.

## Naming conventions

- Folder: `<NN>-<slug>`, where `NN` is the stage number and `slug` is the module id.
- Module id: lowercase kebab-case, matching the pipeline stage's `module` field.
- Artifact: lowercase kebab-case, singular (`design-tokens`, `page-content`);
  exactly one schema per artifact in `contracts/`.
- Output path: `.stitch/<NN>-<stage id>/<artifact>.json`, using the pipeline
  stage id (for example `.stitch/02-plan/site-plan.json`).
- JSON keys: snake_case as declared in the contracts; page paths begin with `/`.
