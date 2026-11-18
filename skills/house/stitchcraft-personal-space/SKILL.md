---
name: stitchcraft-personal-space
description: Build an editorial personal site for essays, notes and photographs with a quiet literary mood and restrained motion.
---

# Stitchcraft Personal Space

## Job

Turn a person's notes and photographs into a personal site that reads like a
small independent magazine: an inviting hero, an essay list, a photo wall and a
short about section. The data layer is local-first by default.

## When to use

- The selected theme is `personal-space`.
- The content is personal writing, travel notes, photo journals or a portfolio
  of observations rather than operational data.

## Data model

Use `window.STITCHCRAFT_DB` when present, with the same adapter contract as
`stitchcraft-data-app`:

- `entries`: title, slug, date, excerpt, body, tags.
- `photos`: title, caption, date, gradient (oremoji placeholder when there is no
  real image asset), tags.

Local mode persists to `localStorage`; remote mode uses the same
Supabase-compatible REST calls when the user configured a remote database.

## Layout blueprint

1. Hero: name, one-line premise, latest note link.
2. Essay list: date-led rows, excerpt, reading time, tag filter.
3. Photo wall: masonry grid with captions on hover/focus.
4. About: short bio and contact.
5. Footer: quiet type, license line.

## Voice and typography

Serif display, generous measure (60-70 characters), long-form spacing, warm
paper background. No marketing hype, no gradients as decoration, no icon soup.

## Motion

GSAP or CSS entrance fades with a 120-240ms range; parallax is limited to
`translateY` under 24px; respect reduced motion. Motion should feel like pages
settling, not a showcase.

## Quality bar

- Reading experience works without JavaScript for the essay text.
- Every photo has meaningful alt text or is marked decorative.
- Tag filters and search are keyboard accessible.
- No external fonts or images are required.

## Output contract

Return `{"files":[{"path":"index.html",...},...],"summary":"..."}` with
`index.html`, `styles.css`, `app.js`, `data-config.js`; seed three example
notes and six placeholder photos so the site never looks empty.
