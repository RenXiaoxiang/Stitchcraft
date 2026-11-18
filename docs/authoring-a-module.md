# Authoring a module

A module is one job, two files and one contract: `module.toml` declares its seam,
`SKILL.md` tells an agent how to do the job, and the artifact's JSON Schema
defines what may cross it. Adding or replacing a module is a data change.

## Prerequisites

- Python 3.11+ and Git, commands run from the repo root.
- Read `AGENTS.md`, `modules/README.md`, `contracts/README.md`, `pipeline/README.md`.
- Install with `python -m pip install -e .` or use `PYTHONPATH=src`.
- Keep `03-design-system` open as the reference; state the job in one sentence.

## Step-by-step

### 1. Pick the stage and the single job

Name the stage id in kebab-case (`analytics`) and write the job as "Given X,
produce Y". If it joins two independent jobs, split it; if an existing module
owns the job, fix that module instead.

The stage number is the 1-based position in `pipeline/pipeline.toml`; it drives
the folder (`modules/10-analytics/`) and artifact path
(`.stitch/10-analytics/<artifact>.json`). Append stages rather than inserting them.

### 2. Choose the produced artifact

Name it as a singular kebab-case noun (`analytics-plan`) and list its consumers.
It must carry the minimum consumers need; a job with no artifact is not a module.
If two stages need the same data, amend the producer instead of forking it.

### 3. Add the contract schema

Create `contracts/<artifact>.schema.json`, modelled on the existing nine:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://stitchcraft.dev/contracts/analytics-plan.schema.json",
  "title": "Analytics Plan",
  "type": "object",
  "required": ["events"],
  "properties": { "events": { "type": "array", "minItems": 1, "items": { "type": "object", "required": ["name", "trigger"], "properties": { "name": { "type": "string" }, "trigger": { "type": "string" } }, "additionalProperties": true } } },
  "additionalProperties": true
}
```

List only genuinely required fields, keep `additionalProperties: true` so
producers can carry evidence forward, and use enums for closed vocabularies.

### 4. Create `module.toml`

Create `modules/<NN>-<slug>/module.toml` with exactly one `[module]` table, keys
in this order, no extra keys:

```toml
[module]
id = "analytics"
name = "Analytics Plan"
stage = 10
summary = "Turn the site plan and build manifest into a minimal, privacy-safe event plan."
skill = "SKILL.md"
consumes = ["site-plan", "build-manifest"]
produces = ["analytics-plan"]
gate = false
```

`stage` matches the folder prefix and pipeline position; `consumes` names only
real contracts; `produces` has exactly one owner. `gate = true` only for
human-verdict gates.

### 5. Write `SKILL.md`

The skill is the authoritative procedure an agent executes: YAML frontmatter
with `name` equal to the module id, then the seven required sections in order:

```markdown
---
name: analytics
description: Turn the site plan and build manifest into a minimal event plan.
---
# Analytics Plan
## Job
Given the plan and build manifest, produce the smallest event plan that measures
the brief's goals without collecting personal data.
## Inputs
- `site-plan` at `.stitch/02-plan/site-plan.json`.
- `build-manifest` at `.stitch/05-build/build-manifest.json`.
- Contract: `contracts/analytics-plan.schema.json`.
## Outputs
`analytics-plan` at `.stitch/10-analytics/analytics-plan.json`; required
`events[].name`, `events[].trigger`, one event per goal.
## Procedure
1. Map every `goals[].id` to an event; keep only goal-supporting routes.
2. Name events `object_action`, define triggers, drop personal-data events.
3. Write the JSON and run `python -m stitchcraft validate`.
## Quality bar
- Every goal has an event; every event names a real route.
- No personal data; `validate --strict` reports no new findings.
## Hand-off
Save the artifact and validate; consumers read only contract fields.
## Failure modes
- **Event sprawl.** One event per goal, one support event per path.
- **The brief is thin.** Record the question in `open_questions`.
```

Keep the procedure numbered and concrete, the quality bar mechanically
checkable, and the hand-off naming the exact artifact path.

### 6. Wire the stage in the pipeline

Append a `[[stages]]` entry to `pipeline/pipeline.toml`:

```toml
[[stages]]
id = "analytics"
module = "analytics"
depends_on = ["plan", "build"]
description = "Turn the site plan and build manifest into a minimal, privacy-safe event plan."
```

`depends_on` lists stage ids, not module ids; every consumed artifact must come
from an ancestor stage in that list, and the step-3 contract must exist.

### 7. Prove it

```bash
stitch validate --strict                 # wiring, contracts, hooks — must be clean
stitch plan                              # graph and table include the new stage
stitch run --dry-run --stage analytics   # stages .stitch/10-analytics/PROMPT.md
python -m unittest discover -s tests -v  # repo-health tests
```

`validate` must exit `0`. Fix warnings too: `--strict` treats them as failures.

### 8. Touch Kiro only for a new seam class

`seam-check` fires on contract, `module.toml` or `pipeline.toml` changes and
`module-anatomy` on `SKILL.md`/`module.toml` edits; both re-validate the stitch,
so a new module needs no hook changes. Add a hook only for a genuinely new seam
class — a new artifact path convention or an editable surface that can break the
graph. Hooks are JSON (`version`, `enabled`, `name`, `when`, `then`); valid types
live in `src/stitchcraft/validate.py`. Keep `pipeline-gate` as the backstop.

## Checklist

- [ ] One job, one sentence, one produced artifact.
- [ ] Contract is valid JSON Schema and uses `additionalProperties: true`.
- [ ] `module.toml` has eight keys in order; `id`/`stage` match slug and `NN`.
- [ ] Frontmatter `name` equals module id; all seven sections are present.
- [ ] `pipeline.toml` entry's `depends_on` covers every consumed artifact.
- [ ] `validate --strict` exits 0, `plan` shows the stage, and `run --dry-run`
      writes the expected prompt and path.
- [ ] [architecture.md](architecture.md), module tables and tests stay accurate.

## Common validator errors and fixes

| Finding | Meaning | Fix |
| --- | --- | --- |
| `stage.module.unknown` | A stage names a module with no `module.toml`. | Match an existing module id or add the folder and manifest. |
| `module.slug.mismatch` (warning) | Folder is not `NN-<module id>`. | Rename to `modules/{stage:02d}-{id}`. |
| `module.unwired` (warning) | Module exists but no stage uses it. | Add its `[[stages]]` entry or remove the folder. |
| `module.skill.missing` | `skill` points at a missing file. | Create `SKILL.md` or correct the key. |
| `seam.missing_contract` | A produced or consumed artifact has no schema. | Add `contracts/<artifact>.schema.json`. |
| `seam.unavailable_input` | A consumer names an artifact no ancestor produces. | Add the producer to `depends_on`, or move the field upstream. |
| `seam.duplicate_producer` | Two modules produce one artifact. | Keep the module that owns the job as producer. |
| `pipeline.unknown_dependency` | `depends_on` names a nonexistent stage. | Use stage ids from `pipeline.toml`. |
| `pipeline.cycle` | Dependencies form a loop. | Move the data into an already-upstream artifact. |
| `hook.patterns_missing` | `fileEdited` hook has no `patterns`. | Add the globs the hook watches. |
| `stitch: no pipeline/pipeline.toml found` (exit 2) | Command run outside the repo. | `cd` to the repo root or pass `--root`. |
