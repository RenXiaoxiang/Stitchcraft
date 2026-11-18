---
name: personal-space
description: Build a warm literary personal site for essays, notes and photographs with a dark editorial palette and local-first note editing.
---

# Personal Space

## Job
Generate a personal site that feels like a writer's room: an editorial masthead, a list of notes and essays, a photo wall built from CSS gradients and glyphs, and an about section written in first person. Notes and tags are editable in the browser and persist locally.

## When to use
- A writer, photographer, researcher or designer asks for a personal site, journal, blog, "personal space" or writing portfolio.
- The mood is reflective and editorial, not corporate or SaaS.
- The site has no database: content is seeded and edited in the browser.

## Data model
No `data-model.json`; personal themes ship without a server collection. Keep one store with three arrays:
- `notes`: `id`, `title`, `body`, `tags[]`, `created_at`, `pinned`.
- `photos`: `id`, `caption`, `taken_at`, `palette`, `glyph` - placeholders only.
- `about`: `name`, `role`, `location`, `paragraph`, `links[]`.
Seed 5-7 notes with 2-4 tags each and 9-12 photos spanning palettes such as dusk, moss, ink and rust. Timestamps are ISO-8601 strings.

## Layout blueprint
1. Masthead: name, small-caps nav, accent hairline, current section.
2. Hero: serif display headline with one italic word, one-paragraph intro, byline meta (place, years, note count), scroll cue.
3. Writing: featured note, then article cards; tag chips and a search field filter in place; `New note` opens the editor.
4. Photographs: masonry columns of caption-only tiles with gradient "photos".
5. About: short first-person bio, portrait placeholder, vertical timeline of places, jobs or years.
6. Footer: colophon, copyright, back-to-top.

## Components
Use `themes/_blocks/`: `hero` (editorial variant with serif and rule), `article-list`, `photo-masonry`, `timeline`; optionally `cta-band` for a newsletter line. Reuse one note editor modal as the only dialog.

## Motion
Transform and opacity only, guarded by `if (window.gsap)`.
- Hero: line-by-line rise, y 24px to 0, 0.7s `power3.out`, 0.08s stagger.
- Scroll: note cards fade and rise 16px on entry; photo tiles scale 0.98 to 1 with opacity.
- Hover: 1-2px lift only; no continuous animation on reading surfaces.
- Respect `prefers-reduced-motion`; the page must look complete with zero motion.

## Data layer
Local-first. Namespace the storage key per site, seed on first visit, persist note create, edit and delete immediately, and search across title, body and tags. If generation settings provide `window.STITCHCRAFT_DATA` with a remote `apiBase`, mirror writes to `{apiBase}/notes` with fetch and fall back to the local copy on failure. Wrap storage access in try/catch so `file://` demos never crash.

## Quality bar
- Warm editorial palette: paper #f2ead9, ink #141512, gold #c9a86a, moss #8ba888.
- Serif display (system serif stack) plus a restrained sans for metadata; measure 62-70ch; generous leading.
- Photography is never faked with stock URLs: gradients, glyphs and inline SVG only.
- Responsive: two-column notes at 1440px, one column at 390px; masonry 3-2-1.
- Accessible labels on every editor field, visible focus, dialog focus trap, body-text contrast 4.5:1; reduced motion honoured.

## Output contract
Return only `{"files":[{"path","content"}],"summary":"..."}` with `index.html`, `styles.css` and `app.js` required. No external images, fonts or CDNs; the page must work opened directly from disk. `summary` states the seeded content count and that edits are stored locally.
