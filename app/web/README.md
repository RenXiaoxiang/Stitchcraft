# Studio web UI

`app/web/` is the Stitchcraft Studio front end: one self-contained page, no
framework, no build step, no CDN.

- `index.html` — markup and the 5-step wizard (Setup → Data → Style → Brief → Generate) plus the Preview / Pipeline / AI browser / Logs stage and the history drawer. Setup includes the optional Obscura AI-browser card.
- `styles.css` — Kiroween visual system (ink, ember, violet), responsive down to 390px, reduced-motion aware.
- `i18n.js` — dependency-free UI localisation for zh/en/de/ar/ru; Arabic switches the document to RTL, and a `MutationObserver` translates dynamically rendered labels.
- `app.js` — the orchestration shell. Talks to the local API (`/api/status`, `/api/settings`, `/api/themes`, `/api/skills`, `/api/browser`, `/api/generate`, `/api/jobs/<id>`, `/api/preview/<id>/`, `/api/export/<id>`, `/api/projects`), binds the language selector and import controls, and never uses `innerHTML` for untrusted values.
- `js/config.js` — shared front-end constants (stages, provider presets, offline theme fallback, status vocabularies).
- `js/jobs.js` — server-sent-event progress via fetch streaming, cancel POST, and fallback signalling for polling.
- `js/import-site.js` — reads a half-built local site folder into a validated text-file payload.
- `vendor/gsap.min.js` — official GSAP 3.13 build; animations are guarded and skipped when `prefers-reduced-motion` is set. `vendor/GSAP-LICENSE.txt` and `vendor/GSAP-UPSTREAM.md` travel with the unmodified build.

The page is served by `src/stitchcraft/server.py` at `http://127.0.0.1:<port>/`
and is opened in a chromeless Edge window by `python -m stitchcraft app`.
