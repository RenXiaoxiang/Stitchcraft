# AGENTS.md — how an AI agent should work in this repo

This repository is **agent-first**: the product is a set of skills an AI agent
executes, and the repository itself is held together by contracts, specs and
hooks. Read this before changing anything.

## Read order

1. `README.md` — what Stitchcraft is and the pipeline at a glance.
2. `.kiro/steering/*.md` — persistent rules for product, tech and structure.
3. `.kiro/specs/stitchcraft-core/` — requirements, design, tasks for the core.
4. `pipeline/pipeline.toml` — the wiring you must not break.
5. `contracts/README.md` — the seam rule.

## The one rule

**Every hand-off is an artifact, and every artifact has a contract.** A module
never reads another module's internals, prompts or intermediate notes. If a
downstream module needs data, amend the upstream contract and the upstream
module — never reach across the seam.

## Commands

```bash
python -m unittest discover -s tests -v     # tests
PYTHONPATH=src python -m stitchcraft validate --strict
PYTHONPATH=src python -m stitchcraft plan
PYTHONPATH=src python -m stitchcraft run --dry-run
PYTHONPATH=src python -m stitchcraft doctor
```

After `pip install -e .` the same commands are available as `stitch validate`,
`stitch plan`, `stitch run --dry-run` and `stitch doctor`.

## Layout

| Path | Owns |
| --- | --- |
| `pipeline/pipeline.toml` | Stage order, dependencies and gates. |
| `contracts/*.schema.json` | The seam: JSON Schema for every artifact. |
| `modules/<NN-slug>/` | One module: `module.toml` + `SKILL.md`, one job. |
| `src/stitchcraft/` | Loader, validator, renderer, CLI. No model calls. |
| `.kiro/` | Steering, specs and hooks (process, not product). |
| `docs/` | Longer explanations and the roadmap. |
| `tests/` | Repo-health smoke tests. |

## Editing rules

- **Contracts first.** Changing an artifact shape starts in `contracts/` and
  propagates through modules and the pipeline in the same change.
- **Never weaken a contract to silence the validator.** Fix the model or the
  producer; a green validator via a loose schema is a bug.
- **One module, one job.** If a skill starts doing two jobs, split it or hand
  the second job to the right module.
- **Keep the CLI dependency-free.** Python 3.11+ standard library only
  (`tomllib`, `json`, `argparse`, `pathlib`). No runtime dependencies.
- **Do not commit generated artifacts.** `.stitch/` and `.tmp-auth/` are
  gitignored; artifacts are rebuildable from requests plus skills.
- **Kiro hooks are part of the product.** If you change a seam, check that
  `.kiro/hooks/seam-check.kiro.hook` still points at the right paths and
  command.

## Definition of done

A change is done when all of these are true:

```bash
stitch validate --strict      # no errors, no warnings
python -m unittest discover -s tests -v
```

plus: the pipeline still renders (`stitch plan`), new/changed files are in the
right layer, and the README (if the change is user-visible) is updated.
