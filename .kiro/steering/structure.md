# Structure Steering

## Repository map

```text
Stitchcraft/
├── .kiro/                      # governance: process, not product
│   ├── steering/               # product.md, tech.md, structure.md
│   ├── specs/stitchcraft-core/ # requirements.md, design.md, tasks.md
│   └── hooks/                  # seam-check, module-anatomy, pipeline-gate, spec-sync
├── modules/                    # nine skills: 01-brief ... 09-deploy
│   └── <NN>-<slug>/{module.toml, SKILL.md}
├── contracts/                  # one JSON Schema per artifact seam
│   └── <artifact>.schema.json
├── pipeline/
│   └── pipeline.toml           # stage order, dependencies, gates
├── src/stitchcraft/            # dependency-free CLI
│   ├── model.py                # Project, Stage, Module, Repo, Issue
│   ├── loader.py               # disk -> model; LoadError for unusable input
│   ├── validate.py             # six validation layers, Issue codes
│   ├── render.py               # Mermaid graph, tables, dry-run prompts
│   └── cli.py                  # argparse subcommands and exit codes
├── tests/                      # unittest suite and repo-health checks
├── examples/coffee-roastery/   # reference request and .stitch/ layout
├── docs/                       # architecture, authoring, Kiro workflow, roadmap
├── .github/workflows/ci.yml    # tests, validate, plan, dry-run smoke
├── AGENTS.md                   # rules for agents working in the repo
├── pyproject.toml              # packaging and the `stitch` console command
├── README.md
└── LICENSE
```

## Ownership rules

1. **Modules own their procedure.** A module reads only the artifacts listed in its `module.toml`; it never imports, calls or edits another module.
2. **Contracts own the seams.** Only `contracts/` defines what crosses a stage boundary; new data means updating the upstream contract and its producer.
3. **Pipeline owns the graph.** `pipeline/pipeline.toml` is the only place that declares stage order, dependencies and gates; modules do not know their position.
4. **The CLI owns enforcement.** `src/stitchcraft/` loads, validates and renders; it contains no site copy, templates or stage-specific knowledge.
5. **Kiro owns process, not product.** `.kiro/` states how to work on the repo; product behaviour lives in modules, contracts, pipeline and src.

## Naming rules

| Thing | Convention | Example |
| --- | --- | --- |
| Module folder | `<NN>-<module id>` | `modules/02-site-plan/` |
| Module id | kebab-case | `design-system` |
| Stage id | short, stable | `plan`, `design` |
| Artifact | `<artifact>.json` | `site-plan.json` |
| Contract | `<artifact>.schema.json` | `site-plan.schema.json` |
| Python file | snake_case | `validate.py` |
| Kiro hook | `<purpose>.kiro.hook` | `seam-check.kiro.hook` |
| Skill file | always `SKILL.md` | `04-copy/SKILL.md` |

## Artifact path convention

`.stitch/<NN>-<stage>/<artifact>.json`, where `NN` is the 1-based stage position in `pipeline.toml`, `stage` is the pipeline stage id (not the module id), and `artifact` is the name in the module's `produces`.

| # | Stage | Module | Artifact path |
| --- | --- | --- | --- |
| 1 | `brief` | `brief` | `.stitch/01-brief/brief.json` |
| 2 | `plan` | `site-plan` | `.stitch/02-plan/site-plan.json` |
| 3 | `design` | `design-system` | `.stitch/03-design/design-tokens.json` |
| 4 | `copy` | `copy` | `.stitch/04-copy/page-content.json` |
| 5 | `build` | `build` | `.stitch/05-build/build-manifest.json` |
| 6 | `seo` | `seo` | `.stitch/06-seo/seo-report.json` |
| 7 | `a11y` | `a11y` | `.stitch/07-a11y/a11y-audit.json` |
| 8 | `qa` | `qa` | `.stitch/08-qa/qa-report.json` |
| 9 | `deploy` | `deploy` | `.stitch/09-deploy/deploy-plan.json` |

Generated prompts and artifacts stay out of git: `.stitch/` is rebuildable from a request plus the skills, so it never enters the repository.

## Desktop studio layout (v0.2)

```text
app/web/           local single-page UI (vanilla JS + vendored GSAP)
themes/            theme packages (5) + _blocks + registry.toml
skills/            vendored official skill packs + house skills + registry.toml
src/stitchcraft/   loader/validator/renderer/CLI + settings, ai_client, storage,
                   themes, skills, generator, server, desktop
hackathon/         Devpost submission kit (description, video script, Kiro write-up, checklist)
docs/              long-form docs + the GitHub Pages showcase (docs/index.html)
```

- **Ownership:** `app/` owns the browser experience; `src/stitchcraft/` owns everything the browser calls; `themes/` and `skills/` own prompt context. A UI change must not require a Python change to theme content, and a theme change must not require a UI change.
- **Generated output never enters the repo:** project sites live under the user's app-data directory; `.stitch/generated/` (headless CLI output) is gitignored.
- **Third-party code:** only under `skills/vendor/`, unmodified, with `LICENSE` + `UPSTREAM.md`; attribution in `skills/ATTRIBUTION.md`. Never edit a vendored file by hand.
- **Hackathon artifacts:** `hackathon/` and `docs/index.html` are part of the deliverable (Kiroween 2026 submission), so they follow the same validation and review rules as code.
