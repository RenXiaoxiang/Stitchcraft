# Pipeline

`pipeline.toml` is the single source of truth for the stitch: which modules run,
in what order, and which artifact each stage hands over.

## Fields

| Field | Meaning |
| --- | --- |
| `[project].name` / `version` | Identity used by the CLI and rendered docs. |
| `[project].artifact_dir` | Where stage outputs and dry-run prompts are written. Default `.stitch/`. |
| `[[stages]].id` | Stable stage name used in CLI output and artifact paths. |
| `[[stages]].module` | Module id from `modules/<slug>/module.toml`. |
| `[[stages]].depends_on` | Stage ids that must complete first. Empty list for the entry stage. |
| `[[stages]].gate` | `true` means the stage's verdict blocks everything downstream. |
| `[[stages]].description` | One sentence shown in `stitch plan` and dry-run prompts. |

## Rules the validator enforces

1. Every `module` reference exists and is used by exactly one stage.
2. Every stage is reachable from the entry stage and the graph has no cycles.
3. A stage only consumes artifacts that an ancestor stage already produced.
4. Every produced artifact has a JSON Schema in `contracts/` and is produced
   by exactly one module.
5. Every module consumes what its skill claims to read — no implicit shortcuts.

## Adding a stage

1. Author the module under `modules/<slug>/` (see `modules/README.md`).
2. Add its artifact schema under `contracts/`.
3. Add a `[[stages]]` entry here with `depends_on` pointing at the stages whose
   artifacts it reads.
4. Run `stitch validate --strict` and `stitch plan` to confirm the new seam
   renders correctly.
