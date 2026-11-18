# Desktop Studio - Tasks

Task list for `.kiro/specs/desktop-studio/requirements.md`, implemented as
designed in `design.md`. A task is ticked only when the files exist and
`stitch validate --strict` plus the test suite pass.

## M1 - Studio backend (v0.2)

- [x] R1, R2: `src/stitchcraft/settings.py` — local config file, provider presets, masked public view, blank-key merge semantics.
- [x] R3: `src/stitchcraft/ai_client.py` — OpenAI-compatible chat client, json-mode fallback, `test_connection`.
- [x] R4: `src/stitchcraft/storage.py` — SQLite `ProjectStore` (connections closed per call) + `test_remote_database`.
- [x] R5, R6: `src/stitchcraft/themes.py` and `src/stitchcraft/skills.py` — registry loaders, prompt-context builder, verify helpers.
- [x] R7, R8: `src/stitchcraft/generator.py` — mock and AI engines, nine named stages, file safety, `data-config.js` emission, GSAP copy.
- [x] R9, R10: `src/stitchcraft/server.py` — jobs, settings/themes/skills/generate/preview/demo/export/projects endpoints.
- [x] R11: `src/stitchcraft/desktop.py` — launcher, Edge app window, `--smoke-test`.
- [x] R12: CLI parity — `stitch app`, `stitch generate`, `stitch themes`, `stitch skills`.

## M2 - Theme library

- [x] R13: five theme packages with `theme.toml` + `SKILL.md` (+ `data-model.json` for data themes).
- [x] `themes/_blocks/` shared block snippets (hero, stat-grid, data-table, crud-modal, article-list, photo-masonry, timeline, cta-band).
- [x] `themes/warehouse-ops/sample/` complete interactive demo site.
- [x] `themes/personal-space/sample/` complete interactive demo site.
- [x] `themes/registry.toml` entries for all five themes.

## M3 - Desktop UI

- [x] `app/web/index.html` layout (wizard + preview/pipeline/logs + history).
- [x] `app/web/styles.css` Kiroween visual system, responsive, accessible focus states.
- [x] `app/web/app.js` API calls, job polling, theme cards, settings, toasts, keyboard shortcut.
- [x] `app/web/vendor/gsap.min.js` official build wired in with reduced-motion guard.

## M4 - Skills

- [x] Vendor GoogleChrome/modern-web-guidance (Apache-2.0) with LICENSE + UPSTREAM.
- [x] Vendor greensock/gsap-skills (MIT) with LICENSE + UPSTREAM.
- [x] Vendor iart-ai/web-animation-skills (MIT) with LICENSE + UPSTREAM.
- [x] Vendor GSAP 3.13 browser build with UPSTREAM licence note.
- [x] `skills/registry.toml`, `skills/ATTRIBUTION.md`, house skills `stitchcraft-data-app` and `stitchcraft-personal-space`.
- [ ] Prompt-budget tuning against a real AI endpoint (needs an author API key).

## M5 - Quality and release

- [x] `tests/test_studio.py` — settings, registries, mock generation, server API.
- [x] CI: install, unit tests, `validate --strict`, themes/skills verify, studio smoke test, JS syntax check.
- [x] `app/web` / `docs` screenshots for the README and GitHub Pages (`docs/assets/`).
- [ ] GitHub Pages showcase (`docs/index.html`) enabled and reachable.
- [x] README rewritten for v0.2 and Kiroween 2026.
- [x] `hackathon/` kit complete (submission, video script, Kiro usage, checklist).
- [ ] Demo video recorded by the author (< 3 minutes) and Devpost submission completed.

## Definition of done (every milestone)

```bash
python -m unittest discover -s tests -v
python -m stitchcraft validate --strict
python -m stitchcraft app --smoke-test --no-window
```
