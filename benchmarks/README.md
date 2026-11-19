# Acceptance benchmark

Five fixed tasks in `tasks/` exercise the themes and the planning/build path:

| Task | Theme | Functional scenario |
| --- | --- | --- |
| `warehouse-inventory` | warehouse-ops | add → search → fresh-run persistence → delete → low-stock indicator |
| `personal-space` | personal-space | no scenario (build only) |
| `brand-launch` | brand-launch | 390 px viewport: CTA visible, no overflow, click reaches destination |
| `staff-directory` | staff-directory | no scenario (build only) |
| `logistics-control` | logistics-control | no scenario (build only) |

A **build pass** means the build completed and produced every file in
`required_files` with at least `min_files` files. A **functional pass** is
separate and browser-driven; `untested` means Obscura is missing, the build is a
placeholder, or the task has no functional scenario. Functional `untested` is
never counted as a pass, and placeholder builds are counted separately.

## Run it

```bash
# Offline: deterministic mock builds (themes with samples copy their sample;
# themes without samples use the placeholder build).
python -m stitchcraft benchmark --engine mock

# Real model: uses the studio's configured provider (keys stay local).
python -m stitchcraft benchmark --engine ai --repeat 2

# One task at a time, custom output parent:
python -m stitchcraft benchmark --task warehouse-inventory --out .stitch/my-runs
```

Each run creates a **new** `run-<timestamp>-<id>/` directory under the output
parent. A pre-existing user directory with a task-like name is never reused or
wiped; the benchmark never passes `force=True` to the generator.

The CLI prints a table and writes:

- `<run>/report.json` — machine-readable results and summary
- `<run>/report.md` — human-readable table
- `<run>/<task>-<attempt>/` — the generated site for review

## Reading the numbers

- **build_passed** — attempts that produced the required files.
- **functional_passed/failed/untested** — browser operation chains.
- **placeholders** — builds that used the placeholder fallback (no sample).
- **model_calls** — actual model requests, including planning and retries.
- **retries** — extra model attempts after the first build attempt.
- **no_retry_passes** — builds that succeeded without any retry.
- **recovered_after_retry** — builds that failed/retried first, then passed.
- **first_pass_rate** — tasks whose first attempt built without a retry.
- **average_duration_ms** — generation latency.

Functional checks need the optional Obscura runtime (`stitch browser install`)
and a local loopback server; without them the report stays honest with
`untested`. A reviewer should still open the sites: copy, layout and
interactions beyond these checks are not scored automatically.
