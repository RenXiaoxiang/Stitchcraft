# AI Browser (v0.4) — Requirements

**Feature:** an optional, locally installed headless browser (Obscura) that the AI
can use to render, screenshot and audit generated sites, so the product works on
customer machines that do not have a modern Chrome or Edge.

## R1 — Optional download, never bundled

- The repository MUST NOT contain an Obscura binary, archive or extracted runtime.
- Installation MUST happen only after an explicit user action (CLI `stitch browser
  install` or the studio's **Install AI browser** button).
- The download MUST be pinned to one upstream release and verified against the
  SHA-256 digests recorded in source before extraction.

## R2 — Cross-platform

- Supported platforms: Windows x86_64, Linux x86_64/aarch64, macOS Intel/Apple
  silicon.
- Unsupported platforms MUST report a clear status instead of failing a build.

## R3 — Studio and CLI surface

- CLI: `stitch browser status|install|remove|check|serve|mcp`.
- The studio MUST expose browser status, install/remove and an automatic-check
  toggle in the Setup step.
- An **AI browser** tab MUST show the latest screenshot and DOM audit.
- Missing runtime MUST NOT fail generation; the check is skipped and logged.

## R4 — Local-only checks

- Browser checks MUST target the local studio preview (`127.0.0.1`) and pass
  `--allow-private-network` to Obscura.
- No remote browser service, no telemetry and no uploaded page content.

## R5 — License compliance

- The runtime is Apache-2.0; the install directory MUST receive `LICENSE` and
  `NOTICE`, and `THIRD_PARTY_NOTICES.md` MUST index the runtime download.
- License snapshots live in `src/stitchcraft/data/`.

## R6 — Network reality

- A user-configurable `STITCHCRAFT_BROWSER_MIRROR` prefix/template MUST allow the
  pinned asset to be fetched through a mirror; SHA-256 verification is unchanged.

## R7 — Archive safety

- Zip/tar extraction MUST reject absolute paths, `..`, links and paths outside
  the install directory.

## R8 — Evidence

- A check MUST produce a JSON report (title, lang, h1, rendered text length, links,
  images with alt coverage, missing anchors, warnings) plus a PNG screenshot, and
  store it under the app-data browser directory.
