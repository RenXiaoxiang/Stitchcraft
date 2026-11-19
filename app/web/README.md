# Studio web UI

`app/web/` is the Stitchcraft Studio front end: one self-contained page, no
framework, no build step, no CDN.

- `index.html` — markup and the 5-step wizard (Setup → Data → Style → Brief → Generate) plus the Preview / Pipeline / AI browser / Logs stage and the history drawer. Setup includes the optional Obscura AI-browser card.
- `styles.css` — Kiroween visual system (ink, ember, violet), responsive down to 390px, reduced-motion aware.
- `app.js` — talks to the local API (`/api/status`, `/api/settings`, `/api/themes`, `/api/skills`, `/api/browser`, `/api/generate`, `/api/jobs/<id>`, `/api/preview/<id>/`, `/api/export/<id>`, `/api/projects`), polls generation progress and AI-browser installs, and never uses `innerHTML` for untrusted values.
- `vendor/gsap.min.js` — official GSAP 3.13 build; animations are guarded and skipped when `prefers-reduced-motion` is set.

The page is served by `src/stitchcraft/server.py` at `http://127.0.0.1:<port>/`
and is opened in a chromeless Edge window by `python -m stitchcraft app`.
