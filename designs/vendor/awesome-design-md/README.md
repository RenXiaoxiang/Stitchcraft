# Awesome DESIGN.md — design references

A vendored copy of five DESIGN.md documents from
[VoltAgent/awesome-design-md](https://github.com/VoltAgent/awesome-design-md)
(MIT, Copyright (c) 2026 VoltAgent). DESIGN.md is a plain-text design-system
document popularised by Google Stitch: it describes palette, typography,
components, layout, elevation, do/don't rules and responsive behaviour so an AI
agent can generate a UI that matches a chosen visual language.

Stitchcraft uses these as **design references**, not as templates or brand
guidelines: a theme declares `design_reference = "<id>"`, and the generator
injects the selected `DESIGN.md` into the build prompt (truncated to a prompt
budget). The sites remain original compositions; no brand assets, logos or
images are copied.

| Reference | Theme | Upstream file |
| --- | --- | --- |
| `linear` | warehouse-ops | `design-md/linear.app/DESIGN.md` |
| `notion` | staff-directory | `design-md/notion/DESIGN.md` |
| `supabase` | logistics-control | `design-md/supabase/DESIGN.md` |
| `airbnb` | personal-space | `design-md/airbnb/DESIGN.md` |
| `stripe` | brand-launch | `design-md/stripe/DESIGN.md` |

- `LICENSE` — upstream MIT license.
- `UPSTREAM.md` — pinned commit, copied files and SHA-256 digests.
- `*/DESIGN.md` — unmodified upstream files.

The upstream project is not affiliated with Stitchcraft, and the DESIGN.md
analyses are not official guidelines from the named brands. Brand names are used
only for identification.
