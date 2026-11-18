# How Stitchcraft uses Kiro

**Kiroween 2026 · Skeleton Crew · Kiro usage write-up**

Stitchcraft is a local-first AI website generator: nine specialised site-building
skills, one contract-checked hand-off between each stage, a dependency-free
Python core, and a desktop studio that turns one brief plus one theme into a
complete static site. Kiro is not a runtime dependency of that product. It is
the agent shell that keeps nine narrow jobs from turning back into one long,
drifting conversation.

This write-up is deliberately evidence-first. Kiro leaves its work in the
repository as steering files, specs, hooks and a validating CLI, so a judge can
inspect the same artifacts the agent worked against. Where the repository cannot
prove *who* did a piece of work, this document says so and leaves a placeholder
for the author instead of inventing an answer.

> **Scope checked:** the repository contained **16 `.kiro` files** when this
> write-up was last checked: 3 steering files, 6 spec files across 2 specs, and
> 7 agent hooks. Task-list status is a snapshot, not an authorship claim.
> Re-check the commands below on the exact revision you submit.

## The idea: make the seams explicit

A single long agent session drifts. The brief fades by the hero copy, design and
copy stop agreeing, and accessibility arrives after the build. Stitchcraft's
answer is structural:

- **One module, one job.** The pipeline has nine stages, each with a written
  procedure in `modules/<NN>-<slug>/SKILL.md`.
- **Artifacts, not conversations.** The only thing allowed across a stage
  boundary is a JSON artifact described by a schema in `contracts/`.
- **Rules, then checks.** Steering states the rules. Specs describe the system.
  Hooks tell the agent what to re-run after an edit. `stitch validate --strict`
  and CI are the authority.
- **Kiro owns process, not product.** Product behaviour lives in modules,
  contracts, the pipeline graph, themes and `src/`. Removing `.kiro/` would not
  stop the CLI from running.

That distinction is what makes the Kiro layer honest: it is the working method
recorded in the repo, not an SDK smuggled into the application.

## Capability map

| Capability | File path in repo | What it enforces / how it is used |
| --- | --- | --- |
| **Product steering** | `.kiro/steering/product.md` | The product's vision, target user, nine-stage vocabulary, five principles, definition of done and non-goals. Kiro keeps this in context so every task is checked against "one module, one job" and "artifacts, not conversations". |
| **Tech steering** | `.kiro/steering/tech.md` | Python 3.11+, standard library only, deterministic output, exit-code contract, naming and artifact conventions, and the rule that `.kiro/` is process rather than runtime. It is the guardrail against adding a convenient dependency or a model call to the CLI. |
| **Structure steering** | `.kiro/steering/structure.md` | Ownership rules and the repository map: contracts own seams, the pipeline owns the graph, the CLI owns enforcement, and modules never reach into one another. It also fixes the exact `.stitch/<NN>-<stage>/<artifact>.json` hand-off paths. |
| **Core requirements** | `.kiro/specs/stitchcraft-core/requirements.md` | Fourteen numbered, testable EARS requirements (R1–R14) for the scaffold: loader, contracts, six validation layers, renderer, CLI, tests and Kiro layer. |
| **Core design** | `.kiro/specs/stitchcraft-core/design.md` | The architecture that satisfies R1–R14: data flow, validation rules, dry-run prompt shape, error taxonomy, traceability and trade-offs. Implementation decisions are expected to point back here. |
| **Core tasks** | `.kiro/specs/stitchcraft-core/tasks.md` | Milestones M1–M3 with requirement ids. M1 records the shipped scaffold; every ticked task names the files it touches. The file also states the verification rule: a task is ticked only after the tests and strict validation pass. |
| **Desktop Studio requirements** | `.kiro/specs/desktop-studio/requirements.md` | Fourteen EARS requirements (R1–R14) for v0.2: local Edge app window, secret-safe settings, themes and skills registries, mock/AI generation, nine-stage progress, safe file writes, SQLite projects, export and Pages showcase. |
| **Desktop Studio design** | `.kiro/specs/desktop-studio/design.md` | The design for the studio: server boundaries, generation engine, prompt assembly, safety checks, persistence and API contract. It is the reference for judging whether the studio implementation matches its requirements. |
| **Desktop Studio tasks** | `.kiro/specs/desktop-studio/tasks.md` | Requirement-linked M1–M4 task list. A tick means the referenced file exists and the suite/validator pass; unfinished lines are visible instead of hidden in a chat transcript. |
| **`seam-check` hook** | `.kiro/hooks/seam-check.kiro.hook` | Fires when a contract, a `module.toml` or `pipeline/pipeline.toml` is edited. It asks the agent to run `validate --strict` and `plan`, fix modules/contracts/pipeline coherently, and never weaken a contract to silence the validator. |
| **`module-anatomy` hook** | `.kiro/hooks/module-anatomy.kiro.hook` | Fires on a module's `SKILL.md` or `module.toml`. It checks frontmatter, the seven required skill sections, real contract names, pipeline agreement and the exact hand-off artifact path, then asks for strict validation. |
| **`pipeline-gate` hook** | `.kiro/hooks/pipeline-gate.kiro.hook` | Human-triggered release gate. Unlike the edit-time hooks, it uses `runCommand` to run `python -m stitchcraft validate --strict` directly, giving the author a one-click final check before trusting the stitch. |
| **`spec-sync` hook** | `.kiro/hooks/spec-sync.kiro.hook` | Fires when anything under `.kiro/specs/**/*.md` changes. It asks the agent to keep requirements, design and tasks mutually consistent, cover every numbered requirement, and never tick a task whose referenced file or test does not exist. Its prompt currently names the core spec's R1–R14 explicitly; the Desktop Studio task list is maintained in the same folder. |
| **`skill-registry` hook** | `.kiro/hooks/skill-registry.kiro.hook` | Fires on skill files, `skills/registry.toml` and vendored `UPSTREAM.md` records. It asks for `skills verify` plus strict validation and enforces the re-vendoring rule: never hand-edit a vendored file to make a check pass. |
| **`theme-anatomy` hook** | `.kiro/hooks/theme-anatomy.kiro.hook` | Fires on theme manifests, theme skills, the theme registry and shared blocks. It verifies the package anatomy, the data model, the declared sample and the registry entry, then runs `themes verify` and strict validation. |
| **`desktop-server` hook** | `.kiro/hooks/desktop-server.kiro.hook` | Fires on `app/**`, `server.py`, `desktop.py` and `generator.py`. It asks for the unit suite plus the headless studio smoke test, checks that no API key or machine path leaked, and confirms the UI still works without an AI key in mock mode. |
| **Agent-sized terminal workflow** | `docs/kiro-workflow.md` and `src/stitchcraft/render.py` | `stitch run --dry-run` writes one `PROMPT.md` per stage naming the skill, contracts and exact upstream artifact paths. Kiro can take one stage per task instead of loading the whole repository, and the artifact files become the memory between tasks. |
| **Validation command surface** | `src/stitchcraft/cli.py` and `src/stitchcraft/validate.py` | The deterministic, model-free commands Kiro runs: `validate --strict`, `plan`, `run --dry-run`, `themes verify`, `skills verify`, `doctor`, and the desktop app's smoke test. Stable exit codes (`0` success, `1` findings, `2` usage/load error) make failures actionable for an agent. |
| **CI as the hard gate** | `.github/workflows/ci.yml` | Runs the unit suite, `stitch validate --strict`, a plan render and a dry-run smoke test on every push. Kiro hooks can be skipped by a careless agent; CI and the validator cannot. |

### What the hooks actually enforce (and what they do not)

The six `fileEdited` hooks and one `userTriggered` hook are Kiro agent hooks,
not an operating-system sandbox. Most of them use `askAgent`: Kiro supplies a
precise instruction and the agent is expected to run the relevant command and
fix the real defect. `pipeline-gate` is the exception; it uses `runCommand` and
runs strict validation directly.

That difference is intentional and worth stating plainly:

- The **hook** is the edit-time reminder that keeps a human or agent from
  forgetting the seam.
- The **validator** is the contract checker, and it has the final say on
  structural correctness.
- **CI** re-runs validation on every push, outside any agent's context.

A green hook conversation is not evidence of a green repository. A green
`validate --strict` run plus a green test suite is.

## How to verify in 5 minutes

You need Python 3.11+ and Git. The commands below are the short path; the same
checks run in CI.

### 0:00–0:01 — a clean checkout

```bash
git clone https://github.com/RenXiaoxiang/Stitchcraft.git
cd Stitchcraft
python --version
```

### 0:01–0:02 — look at the Kiro layer itself

```bash
find .kiro -type f | sort
find .kiro/hooks -name '*.kiro.hook' | wc -l
grep -n '\.kiro' .gitignore || echo 'no .kiro ignore rule'
```

You should see 3 steering files, 2 spec folders with requirements/design/tasks,
7 hook files, and no `.kiro` ignore rule. Open one hook, for example
`.kiro/hooks/seam-check.kiro.hook`, to see the trigger/action shape.

### 0:02–0:03 — run the tests

```bash
python -m unittest discover -s tests -v
```

The exact test count grows with the studio; the run must finish with `OK`, zero
failures and zero errors.

### 0:03–0:04 — run the same checker Kiro runs

```bash
PYTHONPATH=src python -m stitchcraft validate --strict
```

On the submitted revision this must end with `0 error(s), 0 warning(s)`. The
same command was green on the revision checked for this write-up. After
`pip install -e .` the shorter `stitch validate --strict` form works too.
PowerShell users can set the path for one session:

```powershell
$env:PYTHONPATH = 'src'; python -m stitchcraft validate --strict
```

### 0:04–0:05 — read the stitch

```bash
PYTHONPATH=src python -m stitchcraft plan --mermaid-only
```

The graph must contain all nine stages: `brief`, `plan`, `design`, `copy`,
`build`, `seo`, `a11y`, `qa` and `deploy`, with the QA gate wired before deploy.

**Optional sixth minute:** run the desktop smoke test without opening a window:

```bash
python -m stitchcraft app --smoke-test --no-window
```

It exercises the local API, theme/skill catalogues, a mock generation, preview
and ZIP export. This is also the command named in the `desktop-server` hook.

If any command is red, do not fix the hook or loosen a schema. Fix the producer
or the module; the whole point of the seams is that the failure has an owner.

## The spec-driven loop in practice

The working loop is the same one Kiro's spec workflow encourages:

1. **Requirements.** Read the numbered EARS requirements. If behaviour changes,
   the requirement changes first.
2. **Design.** Update the design with the decision and its trade-offs. Trace the
   requirement ids.
3. **Tasks.** Split the work into tasks that name files and requirement ids.
   Do not tick a box until the files exist and the commands pass.
4. **Implementation.** Open only the skill, contracts and upstream artifacts
   needed for one stage. Keep the context narrow.
5. **Verification.** Run the same validator the hook and CI run. Fix the seam,
   not the check.
6. **Record the evidence.** Update the task list and, if user-visible, the README.

The terminal is part of that loop, not a fallback. Kiro's agent can run the CLI
commands, read the failure codes, and return to the owning module. The
`pipeline-gate` hook turns the final validation into a deliberate human action.

### Terminal workflow used by the repo

```bash
# after an editable install
python -m stitchcraft validate --strict       # the hard structural check
python -m stitchcraft plan                    # inspect stage order and the QA gate
python -m stitchcraft run --dry-run           # one PROMPT.md per stage for Kiro

# surface-specific checks during v0.2
python -m stitchcraft themes verify
python -m stitchcraft skills verify
python -m unittest discover -s tests -v
python -m stitchcraft app --smoke-test --no-window
```

Without an editable install, prefix the same commands with
`PYTHONPATH=src python -m stitchcraft`. The hooks assume the installed form
because they run from the repository root after the normal `pip install -e .`
setup.

## Which work was done in Kiro?

The repository can prove what exists. It cannot prove which tool typed a given
file: there are no Kiro session logs, terminal recordings or authorship metadata
in the repo, and this write-up will not pretend otherwise. That distinction
matters for a "how was Kiro used" judge question.

### Verified from the repository

- The Kiro governance layer exists: 3 steering files, 2 specs in
  requirements/design/tasks form, and 7 hook files with valid trigger/action
  JSON.
- `.kiro/` is not ignored by `.gitignore`; it is part of the submitted
  repository, not local scratch space.
- The core `tasks.md` records the v0.1 scaffold as complete, with each task
  naming the files and requirement ids it covers.
- The Desktop Studio `tasks.md` records the v0.2 build task-by-task, including
  items still open at the time of writing.
- The terminal workflow above is implemented in `src/stitchcraft/`, not just
  described in a document.
- The validator, tests, plan renderer and dry-run are repeatable and
  model-free; they do not depend on Kiro being installed.

### Not verifiable from the repository — author attestation required

Replace every bracketed placeholder below before submitting. Do not replace
them with "Kiro did everything"; name the actual workstreams and, where
relevant, what was done by hand or with another agent. The repository has no
record that can back a stronger claim.

| Workstream | Evidence available in the repo | Author to complete before Devpost |
| --- | --- | --- |
| v0.1 pipeline, contracts, modules and CLI | `.kiro/specs/stitchcraft-core/tasks.md` (M1 checked), `src/stitchcraft/`, tests, CI | `[author: state which of these tasks you actually ran in a Kiro session, and which parts you reviewed or wrote by hand.]` |
| Kiro steering, specs and hooks | `.kiro/steering/`, `.kiro/specs/`, `.kiro/hooks/` | `[author: describe the requirements → design → tasks work you did in Kiro, and name any hook or spec section that was written outside it.]` |
| Desktop Studio implementation | `.kiro/specs/desktop-studio/requirements.md`, `design.md`, `tasks.md`, `src/stitchcraft/`, `app/web/` | `[author: say which studio tasks were Kiro-driven, which were other-agent-assisted, and what you verified manually.]` |
| Themes, demo sites and vendored skills | `themes/`, `skills/`, `skills/ATTRIBUTION.md` | `[author: attribute the theme/sample work and the vendoring review; note any part produced outside Kiro.]` |
| Final QA, video and submission | This kit, `hackathon/video-script.md`, `hackathon/checklist.md` | `[author: confirm the human-only decisions: category choice, final QA gate, recording, Devpost submission.]` |
| What was not Kiro | No session logs in the repository | `[author: list any tools or people besides Kiro, or write "none" only if that is true.]` |

The most credible answer is usually the specific one: "I used Kiro for the spec
revisions and the hook wiring; the generated themes were produced with [tool]
and reviewed by hand; the video and Devpost entry were mine." A judge can check
a specific claim against the repository. A claim that every file was authored by
Kiro cannot be checked and is easy to disprove.

## Before you submit this write-up

1. Replace the placeholders above and confirm the revision date.
2. Re-run the five-minute verification on the exact revision you submit.
3. If the `.kiro` tree changes, update the counts and the capability map rather
   than leaving stale claims. In particular, do not turn a planned hook or task
   into a shipped one in prose.
4. Keep the deeper walkthrough at [`docs/kiro-workflow.md`](../docs/kiro-workflow.md)
   as the long-form reference; this page is the submission answer.

Kiro and Kiroween are trademarks of Amazon Web Services. This project was built
for the Kiroween 2026 hackathon and does not claim affiliation with AWS.
