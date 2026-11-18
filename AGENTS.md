# AGENTS.md — how an AI agent should work in this repo

This repository is **agent-first**: the product is a set of skills an AI agent
executes, and the repository itself is held together by contracts, specs and
hooks. Read this before changing anything.

## Read order

1. `README.md` — what Stitchcraft is and how the studio works.
2. `.kiro/steering/*.md` — persistent rules for product, tech and structure.
3. `.kiro/specs/stitchcraft-core/` and `.kiro/specs/desktop-studio/` —
   requirements, design and tasks for the pipeline and the desktop studio.
4. `pipeline/pipeline.toml` + `contracts/README.md` — the originals seam rules.
5. `skills/ATTRIBUTION.md` and `themes/registry.toml` — third-party and theme data.

## The one rule

**Every hand-off is an artifact, and every artifact has a contract.** Modules,
themes and skills never reach into each other's internals. If a downstream
consumer needs data, amend the upstream contract or theme data — never reach
across the seam.

## Commands

```bash
python -m unittest discover -s tests -v
python -m stitchcraft validate --strict
python -m stitchcraft themes verify
python -m stitchcraft skills verify
python -m stitchcraft app --smoke-test --no-window
python -m stitchcraft app                 # real desktop window (Edge)
python -m stitchcraft generate --theme warehouse-ops --prompt "..." --engine mock
```

`PYTHONPATH=src python -m stitchcraft ...` works before `pip install -e .`.

## Layout

| Path | Owns |
| --- | --- |
| `src/stitchcraft/` | Loader, validator, renderer, CLI, settings, AI client, storage, themes/skills loaders, generator, server, desktop launcher. |
| `app/web/` | Local studio UI (vanilla JS + vendored GSAP). No frameworks, no CDN. |
| `themes/` | Theme packages: `theme.toml`, `SKILL.md`, `data-model.json`, optional `sample/`; shared `_blocks/`. |
| `skills/` | Vendored official skill packs (unmodified, licensed, `UPSTREAM.md`) + house skills + `registry.toml`. |
| `pipeline/` `contracts/` `modules/` | The original nine-module stitch spine and its JSON Schema seams. |
| `.kiro/` | Steering, specs and hooks (Kiro governance layer). |
| `hackathon/` `docs/` | Kiroween submission kit and GitHub Pages showcase. |
| `tests/` | Repo-health tests, studio tests and API smoke tests. |

## Editing rules

- **Contracts and theme data first.** Changing an artifact shape starts in
  `contracts/`; changing a theme starts in `themes/<id>/theme.toml` + `SKILL.md`
  and propagates to the registry, blocks and sample.
- **Never weaken a check to silence the validator.** Fix the model, the theme or
  the producer; a green validator via a loose schema is a bug.
- **One module, one job.** The nine-module stitch and the theme packages both
  follow this; do not merge jobs for convenience.
- **Keep the backend dependency-free.** Python 3.11+ standard library only
  (`tomllib`, `json`, `sqlite3`, `http.server`, `urllib`). No SDKs, no frameworks.
- **Never edit vendored files** under `skills/vendor/`. Re-vendor from the pinned
  upstream commit, update `UPSTREAM.md` + `ATTRIBUTION.md` + the registry.
- **Secrets never enter the repo, logs or generated sites.** AI keys and
  database credentials live only in `%LOCALAPPDATA%\Stitchcraft\config.json`
  (tests use `STITCHCRAFT_HOME`). Generated sites may contain only the remote REST
  URL / public anon key the user configured.
- **Do not commit generated output.** `.stitch/`, user project sites and ZIP
  exports are gitignored and rebuildable.
- **Kiro hooks are part of the product.** If you change a seam, a theme or the
  desktop server, check that the matching `.kiro/hooks/*.kiro.hook` still points
  at the right paths and commands.

## Definition of done

A change is done when all of these are true:

```bash
python -m unittest discover -s tests -v
python -m stitchcraft validate --strict
python -m stitchcraft app --smoke-test --no-window
```

plus: the pipeline still renders (`stitch plan`), new/changed files are in the
right layer, and the README (if the change is user-visible) is updated.
