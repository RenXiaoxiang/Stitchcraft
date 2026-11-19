# Security Hardening (v0.6) — Design

## Threat model

The studio is a local HTTP server that holds AI keys and can mutate settings.
Threats:

1. A web page open in the user's browser makes a cross-site write to
   `127.0.0.1` (CSRF) to redirect `base_url` and exfiltrate the saved key.
2. DNS rebinding: a hostile hostname resolves to `127.0.0.1`, so the browser
   treats the API as same-origin.
3. A generated site runs on the same origin as the studio API and calls
   `/api/settings` directly.
4. `generate --out` points at a real folder and the generator clears it.

## Controls

| Threat | Control |
| --- | --- |
| CSRF | `Origin` allow-list for writes; JSON-only content type; no CORS headers |
| DNS rebinding | `Host` allow-list on every request (`127.0.0.1`, `localhost`, `::1`) |
| Generated-site origin | management API only on `127.0.0.1`; `localhost` serves previews only; iframe sandbox + CSP |
| Framed studio | studio CSP + `X-Frame-Options: DENY`; preview iframe sandbox |
| Generated-site injection | preview CSP (self/data/blob, inline allowed, remote code not) |
| Directory wipe | `.stitchcraft-site` marker, staging build, atomic publish or explicit `--force` |
| Failed build | staging directory discarded; previous published site untouched |
| Oversized body | `MAX_BODY_BYTES` → 413 before reading |
| Request errors | `RequestError` → 400/403/413/415 JSON responses |

## Notes

- `Origin` is optional so CLI/curl use still works; browsers send it for writes.
- `localhost` is a preview-only host: `/api/preview` and `/api/demo` are allowed,
  every other path is rejected. The studio API and UI remain on `127.0.0.1`.
- The management write `Origin` allow-list contains only `127.0.0.1`/`::1`, so
  a generated page on `localhost` cannot mutate settings even if it can reach
  the port.
- Generated builds use a private staging directory; `os.replace` publishes only
  after success and a backup/restore path protects the previous site.
- The generation plan/build split lives in `generator.py`; blocks from
  `themes/_blocks/` are injected into the build prompt, and plan navigation is
  validated against the final page set before the build call.
