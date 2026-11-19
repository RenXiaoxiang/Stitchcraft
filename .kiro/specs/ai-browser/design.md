# AI Browser (v0.4) — Design

## Components

| Component | Responsibility |
| --- | --- |
| `src/stitchcraft/browser.py` | Pinned asset table, platform mapping, download, SHA-256 check, safe extraction, manifest/status, `check()`, serve/MCP command builders. |
| `src/stitchcraft/settings.py` | `BrowserSettings` (`auto_check`, `allow_private_network`) persisted with the rest of the local config. |
| `src/stitchcraft/server.py` | `/api/browser`, install worker, manual check endpoints, auto-check after generation, report/screenshot routes. |
| `src/stitchcraft/cli.py` | `stitch browser …` commands and `stitch doctor` status line. |
| `app/web/` | Setup card (install / remove / auto-check) and the **AI browser** tab with screenshot and audit. |
| `src/stitchcraft/data/` | Apache-2.0 license and notice snapshots copied beside the installed runtime. |

## Install flow

1. Resolve `(system, machine)` to a pinned asset; unsupported → status, no error.
2. Download to `<app-data>/browser/downloads/<asset>` (optionally through
   `STITCHCRAFT_BROWSER_MIRROR`), computing SHA-256 while streaming.
3. Compare with the pinned digest; mismatch deletes the partial file and raises.
4. Extract into a staging directory with path traversal and link rejection.
5. Locate `obscura`/`obscura.exe`, run `--version`, then move the whole tree to
   `browser/obscura-<version>/`.
6. Write `LICENSE`, `NOTICE`, `VERSION` and `install.json` (version, platform,
   asset, SHA-256, timestamp, relative binary path).

## Check flow

- `obscura fetch <url> --dump text --output page.txt …`
- `obscura fetch <url> --screenshot screenshot.png …` (separate call: Obscura
  drops the dump when both flags are combined)
- `obscura fetch <url> --eval <metrics JS> …`
- Report warnings: missing title/h1 (critical), little text, missing `lang`,
  images without `alt`, empty hrefs, missing in-page anchors.
- Artifacts: `page.txt`, `screenshot.png`, `report.json` in
  `<app-data>/browser/checks/<project_id>/`.

## Server API

- `GET /api/browser` — status, settings, install progress.
- `POST /api/browser/install` — starts a background download; poll the GET.
- `POST /api/browser/check` — `{project_id}`; synchronous check.
- `GET /api/browser/check/<project_id>` — saved report.
- `GET /api/browser/screenshot/<project_id>` — PNG.
- `DELETE /api/browser` — remove runtime, downloads and checks.
- Generation calls `run_browser_check` after the files are written when
  `auto_check` is on and the runtime is installed; failures are logged and never
  fail the generation.

## UI

- Setup → **AI browser** card: status badge, size/version/license, install/remove,
  progress bar, auto-check switch, local path hint.
- Stage tabs → **AI browser**: screenshot, metric cards, warnings and re-run.

## License

Obscura is Apache-2.0. The repo stores only the license/notice snapshots and the
pinned digests; the binary is downloaded to the user's app-data directory.
`THIRD_PARTY_NOTICES.md` is the canonical index.
