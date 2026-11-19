# AI Browser (v0.4) — Tasks

- [x] Add pinned Obscura 0.2.7 asset table (Windows/Linux/macOS) with SHA-256 digests.
- [x] Implement `BrowserManager.status/install/remove/check` with safe extraction.
- [x] Add `STITCHCRAFT_BROWSER_MIRROR` support without weakening digest checks.
- [x] Persist `BrowserSettings` (`auto_check`, `allow_private_network`).
- [x] Add `stitch browser status|install|remove|check|serve|mcp`.
- [x] Add `/api/browser` status/install/check/report/screenshot/remove routes.
- [x] Run an optional browser check after generation and attach it to the job.
- [x] Add the Setup browser card, progress, auto-check switch and AI browser tab.
- [x] Add screenshot + DOM audit rendering with warnings and re-run control.
- [x] Add Apache-2.0 license/notice snapshots and the THIRD_PARTY_NOTICES entry.
- [x] Add unit tests for platform mapping, digest pinning, install, traversal,
  remove, check reports and settings.
- [x] Add API tests and include `/api/browser` in the studio smoke test.
- [x] Update README, AGENTS.md and the development plan.
- [x] Verify end-to-end on Windows: install through a mirror, generate a mock
  site, screenshot captured and report served by the studio.
