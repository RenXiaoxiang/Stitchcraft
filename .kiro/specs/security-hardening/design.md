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
| Generated-site origin | preview served from `http://localhost:<port>`; API/preview host split |
| Framed studio | studio CSP + `X-Frame-Options: DENY`; preview iframe sandbox |
| Generated-site injection | preview CSP (self/data/blob, inline allowed, remote code not) |
| Directory wipe | `.stitchcraft-site` marker or explicit `--force` |
| Oversized body | `MAX_BODY_BYTES` → 413 before reading |
| Request errors | `RequestError` → 400/403/413/415 JSON responses |

## Notes

- `Origin` is optional so CLI/curl use still works; browsers send it for writes.
- The preview host is a different origin from the studio by hostname, not a
  second process, so lifecycle stays simple and offline.
- Preview CSP allows inline scripts/styles because generated sites are static
  and offline; external code is still blocked by the `'self'` allow-lists.
- The generation plan/build split lives in `generator.py`; blocks from
  `themes/_blocks/` are injected into the build prompt.
