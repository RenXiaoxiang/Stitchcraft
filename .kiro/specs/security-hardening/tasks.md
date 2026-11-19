# Security Hardening (v0.6) — Tasks

- [x] Validate `Host` on every request.
- [x] Validate `Origin` on POST/DELETE when present.
- [x] Require `application/json` for POST bodies.
- [x] Return 413 for oversized bodies before reading them.
- [x] Serve previews from `localhost` only and expose `preview_base` in status.
- [x] Add the sandboxed cross-origin iframe and studio/preview CSP headers.
- [x] Guard `--out` with a Stitchcraft marker and `--force`; keep the marker out
  of exports/file lists.
- [x] Add security regression tests (cross-origin, text/plain, bad Host, large
  body, preview origin + CSP, iframe sandbox).
- [x] Add planning/build split for full providers, deterministic compact plan,
  `themes/_blocks/` prompt injection, and missing-local-reference warnings.
- [x] Label themes without a sample as **AI only** in the UI.
- [x] Update README, AGENTS, developer plan and version 0.6.0.
