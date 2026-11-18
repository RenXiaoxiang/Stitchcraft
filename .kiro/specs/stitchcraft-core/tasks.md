# Stitchcraft Core - Tasks

Task list for `requirements.md`, implemented as designed in `design.md`. Each task
names the files it touches and the requirement(s) it delivers. A task is done only
when the files exist, `python -m unittest discover -s tests -v` passes and
`stitch validate --strict` is clean - ticked by whoever verifies that, not by
whoever writes the file.

## M1 - Scaffold (v0.1)

### Pipeline

- [x] R3, R4: Declare the nine stages, their `depends_on` edges and the `qa` gate in `pipeline/pipeline.toml`.
- [x] R3, R4: Document stage fields and the validator rules in `pipeline/README.md`.

### Contracts

- [x] R2: Add one draft 2020-12 schema per artifact under `contracts/`: `brief`, `site-plan`, `design-tokens`, `page-content`, `build-manifest`, `seo-report`, `a11y-audit`, `qa-report`, `deploy-plan`.
- [x] R2, R5: Explain the seam rule and the artifact ownership table in `contracts/README.md`.

### Modules

- [x] R1, R14: Author `modules/01-brief/` through `modules/09-deploy/`, each with `module.toml` (`id`, `name`, `stage`, `summary`, `skill`, `consumes`, `produces`, `gate`) and `SKILL.md`.
- [x] R1: Give every `SKILL.md` frontmatter (`name` equal to the module id, `description`) and the seven sections: Job, Inputs, Outputs, Procedure, Quality bar, Hand-off, Failure modes.
- [x] R5: Make every Hand-off section name the exact `.stitch/<NN>-<stage>/<artifact>.json` path and its contract.
- [x] R1: Document the module anatomy in `modules/README.md`.

### Kiro layer

- [x] R11: Write `.kiro/steering/product.md`, `.kiro/steering/tech.md` and `.kiro/steering/structure.md`.
- [x] R11: Write `.kiro/specs/stitchcraft-core/requirements.md`, `design.md` and `tasks.md`, with every requirement traced to the design and to at least one task.
- [x] R10: Add `.kiro/hooks/seam-check.kiro.hook`, `.kiro/hooks/module-anatomy.kiro.hook`, `.kiro/hooks/pipeline-gate.kiro.hook` and `.kiro/hooks/spec-sync.kiro.hook`.
- [x] R10: Prove every hook parses (`python -m json.tool`) and uses a known trigger and action.
- [x] R12: Document the Kiro workflow in `docs/kiro-workflow.md`.

### CLI

- [x] R1: Implement `src/stitchcraft/model.py` and `src/stitchcraft/loader.py` (root discovery, TOML parsing, module and contract discovery, `LoadError`).
- [x] R2, R3, R4, R5: Implement the six validation layers in `src/stitchcraft/validate.py` with stable issue codes.
- [x] R6: Implement `stage_prompt()`, `mermaid_flow()` and `plan_table()` in `src/stitchcraft/render.py`.
- [x] R7, R8: Implement `list`, `show`, `validate`, `plan`, `doctor` and `run --dry-run` in `src/stitchcraft/cli.py`, with exit codes `0` success, `1` findings, `2` errors.
- [x] R9: Declare the package and the `stitch` entry point in `pyproject.toml` with no runtime dependencies.

### Tests and CI

- [x] R13: Add `tests/test_stitchcraft.py` covering repo health, contract shape, skill presence, prompt contents and representative validator rules.
- [x] R13: Add `.github/workflows/ci.yml`: editable install, `python -m unittest discover -s tests -v`, `stitch validate --strict`, `stitch plan --mermaid-only` and `stitch run --dry-run`.
- [x] R14: Prove extensibility: a new module folder plus contract plus `[[stages]]` entry appears in `list`, `plan` and `run --dry-run` with no change under `src/stitchcraft/`.

### Documentation

- [x] R12: Write `README.md` (pipeline, CLI, quickstart, Kiro workflow).
- [x] R12: Write `docs/architecture.md`, `docs/authoring-a-module.md`, `docs/kiro-workflow.md` and `docs/roadmap.md`.
- [x] R12: Write `AGENTS.md` and the reference request in `examples/coffee-roastery/request.md`.

## M2 - Runner (v0.2)

- [ ] Add a runner package (for example `src/stitchcraft/runner.py`) that executes stages in pipeline order using the dry-run prompts, with no vendor code in the core.
- [ ] Validate produced artifacts against `contracts/*.schema.json` before the next stage starts; keep the schema engine optional and behind a feature gate.
- [ ] Respect the `qa` gate: continue on `pass`, require a human on `conditional`, stop on `fail`; never let `deploy` plan a failed release.
- [ ] Add `stitch run` (without `--dry-run`) and a run manifest under `.stitch/` so a failed stage can resume.
- [ ] Cover the runner with tests: happy path, missing artifact, gate stop, resume.

## M3 - Adapters (v0.3+)

- [ ] Define the adapter protocol (`available()`, `run_stage(prompt, workdir) -> StageResult`) in the runner package and document it in `docs/architecture.md`.
- [ ] Ship a Kiro adapter: open the stage `PROMPT.md` as an agent task and collect the artifact.
- [ ] Ship a subprocess adapter template for CLI agents (Claude Code, Codex) with timeouts and transcript capture.
- [ ] Ship a manual adapter that prints the prompt and waits for the human to write the artifact.
- [ ] Add adapter contract tests plus `docs/roadmap.md` updates; keep the core CLI model-free and dependency-free.

## Definition of done (every milestone)

```bash
python -m unittest discover -s tests -v
stitch validate --strict
stitch plan
stitch run --dry-run
```
