---
name: brand-launch
description: Build a bold black-and-white editorial launch page with manifesto copy, a launch timeline and one conversion band.
---

# Brand Launch

## Job
Generate a high-contrast launch page for a new brand or product: a manifesto-led opening, a short story, proof numbers, a launch timeline and one conversion band. There is no data app. The page succeeds when a visitor understands the position and takes one action.

## When to use
- The user is launching a brand, product, studio or event and needs a landing page, "coming soon" or campaign site.
- The mood is confident and editorial, with one loud accent colour.
- There is no dashboard, directory or inventory; the goal is a single conversion.

## Data model
No data model. Content is static copy in `index.html`; no collections, no CRUD. Any form collects an email address client-side and shows a success state, or links out when generation settings name a store.

## Layout blueprint
1. Nav: wordmark, three links, one hard button; hairline border under.
2. Hero: full-width manifesto headline (clamp text), one-sentence positioning, primary CTA plus secondary text link, launch date and location meta.
3. Marquee band: repeated launch phrase, huge type, accent on every third word.
4. Story: two-column editorial text with a pull quote; first-person brand voice.
5. Proof: three numbers with short labels (founding year, first run size, city/partner count).
6. Launch timeline: 4 phases from now to open, with dates and one-line detail.
7. CTA band: single action, short form or link, accent background, no clutter.
8. Footer: contact, social links, legal line, back-to-top.

## Components
Use `themes/_blocks/`: `hero` (bold variant), `stat-grid` (three-up proof), `timeline` (launch phases), `cta-band`. Keep the marquee local and optional.

## Motion
Transform and opacity only, guarded by `if (window.gsap)`.
- Hero: headline lines rise 32px with 0.08s stagger, 0.8s `power3.out`; meta fades last.
- Marquee: continuous translateX loop, 30-40s, pausing on hover and stopping entirely under reduced motion.
- Reveals: blocks fade and rise 20px on entry; never animate text colour.
- Hover: buttons shift 2px and accent underlines wipe with scaleX.
- Respect `prefers-reduced-motion`; the static page must look complete.

## Data layer
Static content only. If the CTA is a form, validate the email client-side, show an inline success message, and do not invent a backend. When generation settings provide `window.STITCHCRAFT_DATA = {mode:"remote", apiBase:"..."}`, POST the signup to `{apiBase}/signups` and show an error state if it fails. No localStorage content store is needed beyond remembering dismissed notices.

## Quality bar
- Strict palette: black #0a0a0a, off-white #f5f2ec, one accent #ff4d1f. No decorative gradients, no second accent.
- Editorial type: display at `clamp(2.5rem, 9vw, 8rem)`, tight leading, generous whitespace, real paragraph measure under headings.
- Borders 1px black or 1px off-white; blocky buttons; no soft consumer shadows.
- Responsive: hero stays under one screen at 1440px, stacks cleanly at 390px; marquee never causes horizontal scroll.
- Accessible: semantic headings, skip link, focus-visible, CTA contrast both ways, decorative marquee `aria-hidden`, reduced motion honoured.
- Copy is concrete brand language, not generic "revolutionary" filler.

## Output contract
Return only `{"files":[{"path","content"}],"summary":"..."}` with `index.html`, `styles.css` and `app.js` required (`app.js` handles menu, motion and form state). No external fonts, images or CDNs. `summary` states the CTA target and whether a signup endpoint is configured.
