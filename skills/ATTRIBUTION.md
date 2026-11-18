# Attribution and third-party licenses

Stitchcraft vendors upstream agent skills so that site generation works offline
and deterministically. Vendored packs are copied unmodified (their original
`SKILL.md`, references and license files are preserved); we only add an
`UPSTREAM.md` next to each pack and the registry/attribution files outside them.

## Vendored skill packs

| Pack | Upstream | Commit | License | Copied into | License file |
| --- | --- | --- | --- | --- | --- |
| Modern Web Guidance | https://github.com/GoogleChrome/modern-web-guidance | `64a6d708f5a43f2cd3fde5d4d7db3905ba1bdf65` | Apache-2.0 | `skills/vendor/modern-web-guidance/` (SKILL.md, guides/) | `skills/vendor/modern-web-guidance/LICENSE` |
| GSAP official skills | https://github.com/greensock/gsap-skills | `aed9cfd3277740755f6bfc1155c7aa645403b760` | MIT | `skills/vendor/gsap-skills/skills/` (8 skills + llms.txt) | `skills/vendor/gsap-skills/LICENSE` |
| Web Animation Skills | https://github.com/iart-ai/web-animation-skills | `ed3a045192679b24d32090ee7a983871311ababd` | MIT | `skills/vendor/web-animation-skills/skills/` (7 skills) | `skills/vendor/web-animation-skills/LICENSE` |
| GSAP browser build | https://cdn.jsdelivr.net/npm/gsap@3.13.0/dist/gsap.min.js | 3.13.0 | GSAP standard license | `skills/vendor/gsap-lib/gsap.min.js` | `skills/vendor/gsap-lib/UPSTREAM.md` |

## Trademark notes

- **GSAP** and **GreenSock** are trademarks of GreenSock, Inc. The official
  skills are used under their MIT license; the GSAP browser build is used under
  the GSAP standard license (https://gsap.com/licensing/).
- **Google Chrome**, **Chrome**, and **Modern Web Guidance** are trademarks or
  projects of Google LLC. The guidance pack is used under Apache-2.0.
- **Kiro** and **Kiroween** are trademarks of Amazon Web Services; this project
  was built for the Kiroween 2026 hackathon and does not claim affiliation.
- Other project names referenced by the skills belong to their respective owners.

## Our own content

House skills under `skills/house/` and everything outside `skills/vendor/` is
copyright RenXiaoxiang and licensed under the repository's MIT license (see
`LICENSE`).

## Re-vendoring policy

Do not edit files under `skills/vendor/` by hand. Re-vendor from upstream at a
pinned commit, update the matching `UPSTREAM.md`, this table, and
`skills/registry.toml`, then run:

```bash
python -m stitchcraft skills verify
python -m stitchcraft validate --strict
```
