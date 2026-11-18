# Stitchcraft — Kiroween 2026 submission kit

This folder is the submission kit for **Kiroween 2026**, Kiro's Halloween
hackathon. Stitchcraft is a local-first AI website generator: a dependency-free
Python core, a nine-module site-building pipeline held together by JSON Schema
contracts and Kiro steering, specs and hooks, and a desktop studio where you
bring your own OpenAI-compatible model, choose a local or remote database, pick
a theme, describe the site you want, then watch nine stages assemble it before
you preview and export it. The project is entered in **Skeleton Crew** (one
skeleton demonstrated through two distinct applications: a warehouse operations
console and a personal space), with **Frankenstein** as the secondary flavour
(Kiro plus Google Chrome's Modern Web Guidance, GSAP's official skills and the
user's own AI stitched into one working machine). Everything here is written to
be pasted into Devpost or read by a judge, and every claim points at a file in
this repository.

## What is in the kit

| File | Use it for | Audience |
| --- | --- | --- |
| [`submission.md`](submission.md) | Devpost-ready description: title, tagline, inspiration, what it does, how it was built, challenges, accomplishments, what we learned, what's next, Kiro summary, built-with tags and links. | Devpost form, judges |
| [`video-script.md`](video-script.md) | Shot-by-shot storyboard for the required public YouTube demo (under three minutes), with exact screen actions, narration, captions and a pre-recording setup list. | Person recording the video |
| [`kiro-usage.md`](kiro-usage.md) | Evidence-based write-up of how Kiro was used: steering, specs, the spec-driven loop, all seven agent hooks, the terminal workflow, and a five-minute verification path. | Judges, "how we used Kiro" reader |
| [`checklist.md`](checklist.md) | Compliance matrix for every Kiroween requirement plus a final "before submitting" checklist. | Person hitting submit |
| [`README.md`](README.md) | This index. | Everyone |

## Canonical links

- Repository: <https://github.com/RenXiaoxiang/Stitchcraft>
- Live showcase (GitHub Pages): <https://renxiaoxiang.github.io/Stitchcraft/>
- Demo video: **placeholder — the public YouTube URL must be added to
  `submission.md` and `checklist.md` before the Devpost deadline.**
- License: MIT (see [`../LICENSE`](../LICENSE))
- Third-party attribution: [`../skills/ATTRIBUTION.md`](../skills/ATTRIBUTION.md)

## Deadline

The Devpost deadline is **December 4, 2026, 2:00 PM PT**, which is
**December 5, 2026, 6:00 AM Beijing time**. Submit early enough to leave time for
the Pages deploy and the YouTube upload to finish processing.

## Category positioning

- **Primary: Skeleton Crew.** One skeleton template — nine pipeline stages, nine
  contracts, one theme-block vocabulary, one data layer — shown through two
  applications that feel nothing alike: `warehouse-ops` and `personal-space`.
  Theme modules are data, not forks; both samples live under
  `themes/<id>/sample/` and share the same skeleton.
- **Secondary: Frankenstein.** The product itself is a deliberate stitching of
  Kiro governance, Google Chrome's Modern Web Guidance, GreenSock's official
  GSAP skills, the iart-ai web-animation skills, and the user's own
  OpenAI-compatible model. The seams between those parts are the submission.

## Status language used in this kit

The repository is built in two honest versions, and the kit keeps them
separate:

- **v0.1 — the scaffold (shipped).** Nine modules, nine contracts, the
  dependency-free `stitch` CLI, the Kiro governance layer, tests and CI. It
  validates and stages the stitch but does not generate a site.
- **v0.2 — the desktop studio (this submission).** The `stitch app` local studio,
  the theme module library, the vendored skill packs and the nine-stage
  generation flow with preview and export.

Where a fact is about v0.1 it says so. Where a repository action is still
pending (the recorded video, the Pages deploy, the GitHub "About" license),
`checklist.md` says so and names the owner action. Nothing in this kit claims a
metric, a user count or a Kiro feature that the repository does not show.
