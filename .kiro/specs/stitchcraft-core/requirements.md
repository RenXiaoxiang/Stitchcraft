# Stitchcraft Core - Requirements

These requirements define the core of Stitchcraft: the repository model, its
contracts, the validating CLI and the Kiro governance layer that holds the seams.
They are written in EARS form — "WHEN <event> THE SYSTEM SHALL <behavior>" — so
each one can be read as a testable acceptance criterion. `design.md` shows how
they are met and `tasks.md` tracks the work that delivers them.

R1. WHEN Stitchcraft loads a repository, THE SYSTEM SHALL discover every module from `modules/<NN>-<slug>/module.toml` together with its declared `SKILL.md`, using no hard-coded module list.
Rationale: adding, renaming or reordering a module must be a data change, not a code change.

R2. WHEN a module declares a produced artifact, THE SYSTEM SHALL require a matching `contracts/<artifact>.schema.json` and verify that it parses as a JSON object declaring a JSON Schema, a title and an object type with properties.
Rationale: an artifact without a contract is a conversation, not a seam.

R3. WHEN the pipeline is loaded, THE SYSTEM SHALL verify that every stage references one existing module, that every module is wired into exactly one stage, and that every consumed artifact is produced by an ancestor stage.
Rationale: miswiring is the most common seam failure and must fail loudly.

R4. WHEN the stage dependency graph is built, THE SYSTEM SHALL reject self-dependencies and cycles, report every stage unreachable from an entry stage, and flag a graph with zero or more than one entry stage.
Rationale: a graph that cannot be executed in order is not a pipeline.

R5. WHEN modules and stages are cross-checked, THE SYSTEM SHALL reject any artifact with zero or multiple producers, any module that consumes its own output, and any consumed artifact whose contract does not exist.
Rationale: one producer per seam keeps modules replaceable and makes ownership unambiguous.

R6. WHEN the user runs `stitch run --dry-run`, THE SYSTEM SHALL write one `PROMPT.md` per stage under `.stitch/<NN>-<stage>/` naming the module, its skill path, the consumed and produced artifacts with their contracts and exact paths, without calling a model or writing an artifact.
Rationale: the agent needs a precise, reviewable brief per stage; the human needs to see the plan before work starts.

R7. WHEN the user runs a documented subcommand (`list`, `show <module>`, `validate [--strict] [--json]`, `plan`, `doctor` or `run --dry-run`), THE SYSTEM SHALL perform it and exit `0` on success, `1` on validation findings and `2` on usage or load errors.
Rationale: one stable interface serves the human, the agent and CI.

R8. WHEN a read-only command runs twice against the same repository state, THE SYSTEM SHALL emit byte-identical output, free of timestamps, absolute paths and other environment-dependent values.
Rationale: diffs, snapshots and CI comparisons are only meaningful if output is reproducible.

R9. WHEN Stitchcraft is installed or executed, THE SYSTEM SHALL require only the Python 3.11+ standard library and make no network calls.
Rationale: the tool must run in any agent sandbox, offline, without a dependency supply chain.

R10. WHEN a seam file (`contracts/*.schema.json`, `modules/*/module.toml` or `pipeline/pipeline.toml`) is edited in Kiro, THE SYSTEM SHALL instruct the agent to run strict validation and repair the seam; WHEN a human triggers the pipeline gate, THE SYSTEM SHALL run `python -m stitchcraft validate --strict`.
Rationale: "never weaken a contract" only holds if something checks after every edit.

R11. WHEN the Kiro governance layer is reviewed, THE SYSTEM SHALL provide steering for product, technology and structure, and a `stitchcraft-core` spec whose requirements, design and tasks reference each other.
Rationale: an agent-first repo needs durable, checkable context that outlives one conversation.

R12. WHEN a new builder or agent opens the repository, THE SYSTEM SHALL provide a README plus docs covering the architecture, authoring a module, the Kiro workflow and the roadmap.
Rationale: the product is a process; an undocumented process does not transfer.

R13. WHEN a pull request is opened, THE SYSTEM SHALL install the package, run the unittest suite, run `stitch validate --strict`, render the plan and stage the dry-run on Python 3.12, failing on any error.
Rationale: the same checks must pass locally and on every change.

R14. WHEN a new module is added by creating `modules/<NN>-<slug>/`, a matching contract and a `[[stages]]` entry in `pipeline/pipeline.toml`, THE SYSTEM SHALL include it in discovery, validation, planning and dry-run prompts without edits to `src/stitchcraft`.
Rationale: the ninth module must be no harder than the tenth.

## Out of scope

- Generating or editing the site's HTML, CSS or JavaScript in v0.1; the build module emits a manifest, not a codebase.
- Calling any model or executing module skills; `stitch run` ships in dry-run form only.
- Running deployments or hosting sites; the deploy module produces a plan artifact.
- Validating artifact instances with a third-party schema engine; v0.1 checks contract presence and shape, and modules plus hooks own content correctness.
- Migrating existing sites, non-marketing site types and multi-user workflows.
- A GUI, dashboard, accounts or hosted service.
