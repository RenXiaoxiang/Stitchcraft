# Security Hardening (v0.6) — Requirements

## R1 — Local write protection

- State-changing requests (`POST`, `DELETE`) MUST reject a foreign `Origin`.
- `POST` MUST require `Content-Type: application/json`.
- All requests MUST reject a `Host` that is not `127.0.0.1`, `localhost` or
  `::1` (DNS-rebinding protection).
- Oversized request bodies MUST be rejected with 413 before being read.

## R2 — Preview isolation

- The management API MUST be served only on the Studio host (`127.0.0.1`); the
  `localhost` host MUST serve `/api/preview/...` and `/api/demo/...` only.
- Generated sites and demo samples MUST be served from `http://localhost:<port>`,
  a different origin from the studio UI/API on `http://127.0.0.1:<port>`.
- The preview iframe MUST carry a sandbox attribute and `referrerpolicy`.
- Preview responses MUST carry a CSP header suitable for generated static sites.
- The studio UI HTML MUST carry its own CSP and `X-Frame-Options: DENY`.

## R3 — Output-directory safety

- `generate_site` MUST refuse to clear a non-empty output directory that has no
  Stitchcraft marker.
- A build MUST go to a private staging directory; only a fully successful build
  may atomically replace the previous site.
- A failed or interrupted build MUST leave the previous site unchanged and clean
  up its staging directory.
- An explicit `--force` MAY override the foreign-directory check, and the marker
  must never be exported or counted as a generated file.

## R4 — Regression tests

- Tests MUST cover cross-origin POST, text/plain POST, foreign Host, oversized
  bodies, `localhost`-management-API rejection, preview origin separation + CSP,
  the sandboxed iframe, output-directory guard, failed-build preservation and
  plan navigation validation.

## R5 — Honest generation stages

- The UI's nine-stage progress model MUST not claim that every stage is a model
  call. Full providers make a planning call + a build call; compact providers
  make one build call with a deterministic plan.
- `themes/_blocks/` reference HTML MUST be included in the build prompt.
- The plan MUST be checked before the build: page paths, titles, primary
  navigation labels/paths, and every internal navigation target must exist in
  the final sitemap.

## R6 — QA signals

- The generator MUST report local files referenced by `index.html` but never
  generated.
- The optional Obscura check remains the visual QA evidence.
