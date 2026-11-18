# Tech Steering

## Stack

- **Language:** Python 3.11+; CI runs 3.12. `tomllib` is the only parser needed.
- **Runtime dependencies:** none. `json`, `tomllib`, `pathlib`, `argparse`, `dataclasses` and `re` cover the CLI; tests use `unittest`.
- **Config:** TOML - `pipeline/pipeline.toml` and each `modules/*/module.toml`.
- **Contracts:** JSON Schema draft 2020-12, `contracts/<artifact>.schema.json`.
- **Artifacts:** JSON at `.stitch/<NN>-<stage>/<artifact>.json`; packaging is `pyproject.toml` with the `stitch` entry point.

Kiro is the reference agent shell: product code never imports or assumes it, and `.kiro/` is process, not runtime.

## Runtime rules

- Python 3.11+ only, standard library only (tests included); no network at runtime.
- The repo root is the nearest ancestor containing `pipeline/pipeline.toml`; paths never depend on the caller's working directory.
- `list`, `show`, `plan`, `validate` and `doctor` are read-only; `run --dry-run` writes only `PROMPT.md` files under the artifact directory.
- Output is deterministic: stable stage order and key order, no timestamps, absolute paths or hostnames; two runs print identical bytes.
- Exit codes: `0` success, `1` validation findings, `2` usage or load errors; `validate --json` is always machine-readable.
- The CLI never calls a model. It prepares seams; the agent executes modules.

## Commands

```bash
python -m unittest discover -s tests -v                # test suite
python -m pip install -e .                             # dev install -> `stitch`
PYTHONPATH=src python -m stitchcraft validate --strict # same checker as the hooks
stitch list | show <module> | validate [--strict] [--json] | plan | doctor | run --dry-run
```

## Conventions

- Modules live in `modules/<NN>-<slug>/` where the slug is the module id:
  `01-brief`, `02-site-plan`, `03-design-system`, `04-copy`, `05-build`,
  `06-seo`, `07-a11y`, `08-qa`, `09-deploy`.
- `module.toml` has one table, `[module]`, with keys in this order: `id`, `name`,
  `stage`, `summary`, `skill`, `consumes`, `produces`, `gate`. `stage` is the
  1-based position; `consumes`/`produces` list artifact names, not paths.
- `SKILL.md` frontmatter carries `name` (equal to the module id) and
  `description`; the body has Job, Inputs, Outputs, Procedure, Quality bar,
  Hand-off and Failure modes sections.
- Python files are snake_case and single-purpose: `model.py` types, `loader.py`
  disk, `validate.py` rules, `render.py` rendering, `cli.py` arguments. JSON is
  two-space indented and ends with a newline.

## Artifact JSON rules

1. One artifact per stage at `.stitch/<NN>-<stage id>/<artifact>.json`, where `NN` is the zero-padded stage position.
2. Required keys come from the contract; extra keys are allowed where the schema permits and must carry evidence forward, not fork the format.
3. No absolute paths, secrets, personal data or timestamps; artifacts reproduce.
4. Arrays describing sections or steps keep a stable order and stable ids.
5. Never weaken required fields to pass validation; amend the upstream contract.

## Kiro-specific conventions

- `.kiro/steering/*.md` load into every agent task; keep them short, normative and true to the code.
- `.kiro/specs/stitchcraft-core/` holds EARS requirements, design and tasks; change all three together.
- `.kiro/hooks/*.kiro.hook` are JSON rules: file-edit hooks ask the agent to re-validate, `pipeline-gate` runs strict validation on human trigger.
- Hooks warn the agent; `.github/workflows/ci.yml` and `stitch validate --strict` are the authority.

## Testing and CI

- Standard `unittest`: `python -m unittest discover -s tests -v`; tests check this repo against its own seams and exercise loader, validator and renderer.
- Every validator rule gets a failing and a passing case; every CLI verb gets a happy-path test. No network, virtualenv or editable install required.
- CI (`.github/workflows/ci.yml`, Python 3.12): editable install, unit tests, `stitch validate --strict`, `stitch plan --mermaid-only`, `stitch run --dry-run --out /tmp/stitch-dryrun`.

## Where to extend

- **New artifact:** contract -> producing module -> pipeline stage.
- **New module:** `modules/<NN>-<slug>/` + contract + `[[stages]]` entry; the CLI discovers it from disk, so no Python change is needed.
- **New rule:** `src/stitchcraft/validate.py`, tests, and a matching `.kiro/hooks/` rule so agents and CI run the same check.
- **New CLI verb:** only after requirements and design change; wire it in `cli.py` and cover it in tests.
