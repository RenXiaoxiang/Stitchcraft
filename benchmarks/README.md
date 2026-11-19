# Acceptance benchmark

Five fixed tasks in `tasks/` exercise the themes and the planning/build path:

| Task | Theme | What it checks |
| --- | --- | --- |
| `warehouse-inventory` | warehouse-ops | data table, CRUD, KPI, inbound |
| `personal-space` | personal-space | essays, search, photo wall |
| `brand-launch` | brand-launch | landing-page structure + design skill |
| `staff-directory` | staff-directory | people cards, filters, onboarding |
| `logistics-control` | logistics-control | shipments, timeline, incident workflow |

A **pass** means the build completed and produced every file in
`required_files` with at least `min_files` files. Warnings, missing local
references and retry notes are recorded for review; they are not hidden.

## Run it

```bash
# Offline: deterministic mock builds (themes with samples copy their sample;
# themes without samples use the placeholder build).
python -m stitchcraft benchmark --engine mock

# Real model: uses the studio's configured provider (keys stay local).
python -m stitchcraft benchmark --engine ai --repeat 2

# One task at a time, custom output directory:
python -m stitchcraft benchmark --task warehouse-inventory --out .stitch/my-run
```

The CLI prints a pass/fail table and writes:

- `<out>/report.json` — machine-readable results and summary
- `<out>/report.md` — human-readable table
- `<out>/<task>-<attempt>/` — the generated site for review

Default output: `.stitch/benchmarks/<timestamp>-<id>/` (gitignored).

## Reading the numbers

- **pass_rate** — attempts that produced the required files.
- **first_pass_rate** — tasks whose first attempt passed; the practical
  "write a brief, get a usable site first time" number.
- **average_duration_ms** — generation latency (mock is deterministic; AI is
  provider-dependent).
- **repairs** — warnings that indicate a compact/rate-limit retry; other
  warnings stay in each result for human review.

This is a product-quality probe, not a promise: a reviewer should still open
the generated sites and check copy, layout and interactions.
