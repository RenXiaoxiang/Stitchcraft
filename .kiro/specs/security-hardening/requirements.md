# Security Hardening (v0.6) — Requirements

## R1 — Local write protection

- State-changing requests (`POST`, `DELETE`) MUST reject a foreign `Origin`.
- `POST` MUST require `Content-Type: application/json`.
- All requests MUST reject a `Host` that is not `127.0.0.1`, `localhost` or
  `::1` (DNS-rebinding protection).
- Oversized request bodies MUST be rejected with 413 before being read.

## R2 — Preview isolation

- Generated sites and demo samples MUST be served from `http://localhost:<port>`,
  a different origin from the studio UI/API on `http://127.0.0.1:<port>`.
- The preview iframe MUST carry a sandbox attribute and `referrerpolicy`.
- Preview responses MUST carry a CSP header suitable for generated static sites.
- The studio UI HTML MUST carry its own CSP and `X-Frame-Options: DENY`.

## R3 — Output-directory safety

- `generate_site` MUST refuse to clear a non-empty output directory that has no
  Stitchcraft marker.
- An explicit `--force` MAY override this, and the marker must never be exported
  or counted as a generated file.

## R4 — Regression tests

- Tests MUST cover cross-origin POST, text/plain POST, foreign Host, oversized
  bodies, preview origin separation + CSP, the sandboxed iframe, and the output
  directory guard.

## R5 — Honest generation stages

- The UI's nine-stage progress model MUST not claim that every stage is a model
  call. Full providers make a planning call + a build call; compact providers
  make one build call with a deterministic plan.
- `themes/_blocks/` reference HTML MUST be included in the build prompt.

## R6 — QA signals

- The generator MUST report local files referenced by `index.html` but never
  generated.
- The optional Obscura check remains the visual QA evidence.
