# AGENTS.md — how an AI agent should work in this repo

This repository is **agent-first**: the product is a set of skills an AI agent
executes, and the repository itself is held together by contracts, specs and
hooks. Read this before changing anything.

## Read order

1. `README.md` — what Stitchcraft is and how the studio works.
2. `.kiro/steering/*.md` — persistent rules for product, tech and structure.
3. `.kiro/specs/stitchcraft-core/`, `.kiro/specs/desktop-studio/` and
   `.kiro/specs/security-hardening/` — requirements, design and tasks for the
   pipeline, the desktop studio and the local-API threat model.
4. `pipeline/pipeline.toml` + `contracts/README.md` — the originals seam rules.
5. `skills/ATTRIBUTION.md`, `vendor/ATTRIBUTION.md` and `themes/registry.toml` —
   third-party and theme data. `THIRD_PARTY_NOTICES.md` is the canonical index.

## The one rule

**Every hand-off is an artifact, and every artifact has a contract.** Modules,
themes and skills never reach into each other's internals. If a downstream
consumer needs data, amend the upstream contract or theme data — never reach
across the seam.

## Commands

```bash
python -m unittest discover -s tests -v
python -m stitchcraft validate --strict
python -m stitchcraft themes verify
python -m stitchcraft skills verify
python -m stitchcraft libraries verify
python -m stitchcraft browser status
python -m stitchcraft app --smoke-test --no-window
python -m stitchcraft app                 # real desktop window (Edge)
python -m stitchcraft generate --theme warehouse-ops --prompt "..." --engine mock
```

`PYTHONPATH=src python -m stitchcraft ...` works before `pip install -e .`.

## Layout

| Path | Owns |
| --- | --- |
| `src/stitchcraft/` | Loader, validator, renderer, CLI, settings, AI client, storage, themes/skills loaders, generator, server, desktop launcher, optional Obscura browser manager. |
| `app/web/` | Local studio UI (vanilla JS + vendored GSAP). No frameworks, no CDN. |
| `themes/` | Theme packages: `theme.toml`, `SKILL.md`, `data-model.json`, optional `sample/`; shared `_blocks/`. |
| `skills/` | Vendored official skill packs (unmodified, licensed, `UPSTREAM.md`) + house skills + `registry.toml`. |
| `vendor/` | Six MIT browser libraries (unmodified dist + `LICENSE` + `UPSTREAM.md` + `README.md` per folder) + `registry.toml` + `ATTRIBUTION.md`. |
| `pipeline/` `contracts/` `modules/` | The original nine-module stitch spine and its JSON Schema seams. |
| `.kiro/` | Steering, specs and hooks (Kiro governance layer). |
| `hackathon/` `docs/` | Kiroween submission kit and GitHub Pages showcase. |
| `tests/` | Repo-health tests, studio tests and API smoke tests. |

## Editing rules

- **Contracts and theme data first.** Changing an artifact shape starts in
  `contracts/`; changing a theme starts in `themes/<id>/theme.toml` + `SKILL.md`
  and propagates to the registry, blocks and sample.
- **Never weaken a check to silence the validator.** Fix the model, the theme or
  the producer; a green validator via a loose schema is a bug.
- **One module, one job.** The nine-module stitch and the theme packages both
  follow this; do not merge jobs for convenience.
- **Keep the backend dependency-free.** Python 3.11+ standard library only
  (`tomllib`, `json`, `sqlite3`, `http.server`, `urllib`). No SDKs, no frameworks.
- **Lean by default.** `.kiro/steering/lean-engineering.md` is the necessity
  ladder: reuse the existing module, theme block or standard library before
  adding a new layer or dependency. Never trim validation, security,
  accessibility or tests to make a diff smaller.
- **Never edit vendored files** under `skills/vendor/`. Re-vendor from the pinned
  upstream commit, update `UPSTREAM.md` + `ATTRIBUTION.md` + the registry.
- **Secrets never enter the repo, logs or generated sites.** AI keys and
  database credentials live only in `%LOCALAPPDATA%\Stitchcraft\config.json`
  (tests use `STITCHCRAFT_HOME`). Generated sites may contain only the remote REST
  URL / public anon key the user configured.
- **The local API is a security boundary.** Keep the Host/Origin/Content-Type
  checks, the management-API-only-on-`127.0.0.1` rule, the `localhost`-preview
  origin, the sandboxed preview iframe and the CSP headers in
  `server.py`/`app/web/`. Builds must publish through a staging directory and
  atomically replace the previous site only after success; keep `--out`
  cleaning behind the Stitchcraft marker or `--force`. Security and data-loss
  regressions belong in `tests/test_studio.py`.
- **Do not commit generated output.** `.stitch/`, user project sites and ZIP
  exports are gitignored and rebuildable.
- **Kiro hooks are part of the product.** If you change a seam, a theme or the
  desktop server, check that the matching `.kiro/hooks/*.kiro.hook` still points
  at the right paths and commands.

## Third-party browser libraries (`vendor/`)

- **They live under `vendor/<id>/` and are never edited.** Dist files are
  byte-for-byte copies of the pinned upstream release; a fix goes upstream or
  into a new pinned version, never into the vendored file.
- **Every folder keeps `LICENSE` + `UPSTREAM.md` + `README.md`.** The license
  text and copyright line are the source of truth for redistribution; the
  upstream record names the repository, pinned version, download URL and copied
  files.
- **`THIRD_PARTY_NOTICES.md` must stay current.** It is the canonical index of
  all third-party material; adding, upgrading or removing a file updates it, plus
  `vendor/ATTRIBUTION.md` and `vendor/registry.toml`.
- **Generated sites may only reference copied `vendor/<id>/` paths.** The
  generator writes the libraries a site actually uses into `site/vendor/<id>/`;
  a generated site must never load a CDN or any other external URL for code.
- **`stitch libraries verify` must stay green.** It checks folders, versions,
  licenses and the registry together; a red result blocks a release.

## Optional AI browser runtime (`browser.py`)

- **The runtime is downloaded, never committed.** Obscura is a ~70 MB
  Apache-2.0 binary fetched into the user's app-data directory after explicit
  consent. Never add it, its archive, or `browser/` output to the repository.
- **Pin version and digests together.** `OBSCURA_VERSION` and the `ASSETS`
  SHA-256 values must match one upstream release; upgrading means updating
  both, the tests and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
- **Keep the license material current.** `src/stitchcraft/data/obscura-LICENSE.txt`
  and `obscura-NOTICE.txt` are copied into the install directory; the canonical
  index is `THIRD_PARTY_NOTICES.md`.
- **Checks are optional and local.** A missing runtime must never fail site
  generation or the studio smoke test. Browser checks may only target loopback
  previews (`http://localhost:<port>`); no remote browser service.
- **Respect restricted networks.** `STITCHCRAFT_BROWSER_MIRROR` may rewrite the
  GitHub URL; the pinned SHA-256 check still applies before extraction.
- **Never weaken archive safety.** Zip/tar extraction rejects absolute paths,
  `..`, links and anything outside the install directory.

## Definition of done

A change is done when all of these are true:

```bash
python -m unittest discover -s tests -v
python -m stitchcraft validate --strict
python -m stitchcraft libraries verify
python -m stitchcraft app --smoke-test --no-window
```

plus: the pipeline still renders (`stitch plan`), new/changed files are in the
right layer, and the README (if the change is user-visible) is updated.
