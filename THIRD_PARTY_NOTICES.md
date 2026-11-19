# Third-Party Notices

Stitchcraft is an offline-first tool: it vendors the browser libraries and the
agent skill packs it needs instead of fetching them at runtime. It can also
download one optional browser runtime (Obscura) on the user's request; that
runtime is not redistributed in this repository and is covered in section 3.
This file is the **canonical notice index** for every third-party component
redistributed with Stitchcraft. All third-party files are redistributed
**unmodified**, their licenses are preserved in-tree, and provenance (pinned
version, source URL, copy/vendoring date) is recorded in the matching
`UPSTREAM.md` files. Vendored: **2026-11-19**.

Component-level detail: [`vendor/ATTRIBUTION.md`](vendor/ATTRIBUTION.md),
[`vendor/registry.toml`](vendor/registry.toml),
[`skills/ATTRIBUTION.md`](skills/ATTRIBUTION.md).

## 1. Browser libraries (`vendor/`)

Six pinned browser builds are bundled so generated sites work with no network.
All are MIT. The dist files are byte-for-byte as served by the pinned jsDelivr
URLs recorded in each folder's `UPSTREAM.md`.

### Fabric.js

- Version: 5.2.4 (npm `fabric`)
- License: MIT
- Copyright: Copyright (c) 2008-2015 Printio (Juriy Zaytsev, Maxim Chernyak)
- Upstream: https://github.com/fabricjs/fabric.js
- License text: [`vendor/fabric/LICENSE`](vendor/fabric/LICENSE)
- Distributed files: [`vendor/fabric/fabric.min.js`](vendor/fabric/fabric.min.js)

### Chart.js

- Version: 4.4.7 (npm `chart.js`)
- License: MIT
- Copyright: Copyright (c) 2014-2024 Chart.js Contributors
- Upstream: https://github.com/chartjs/Chart.js
- License text: [`vendor/chartjs/LICENSE`](vendor/chartjs/LICENSE)
- Distributed files: [`vendor/chartjs/chart.umd.min.js`](vendor/chartjs/chart.umd.min.js)

### SortableJS

- Version: 1.15.6 (npm `sortablejs`)
- License: MIT
- Copyright: Copyright (c) 2019 All contributors to Sortable
- Upstream: https://github.com/SortableJS/Sortable
- License text: [`vendor/sortablejs/LICENSE`](vendor/sortablejs/LICENSE)
- Distributed files: [`vendor/sortablejs/Sortable.min.js`](vendor/sortablejs/Sortable.min.js)

### Rough.js

- Version: 4.6.6 (npm `roughjs`)
- License: MIT
- Copyright: Copyright (c) 2019 Preet Shihn
- Upstream: https://github.com/pshihn/rough
- License text: [`vendor/roughjs/LICENSE`](vendor/roughjs/LICENSE)
- Distributed files: [`vendor/roughjs/rough.min.js`](vendor/roughjs/rough.min.js)

### Swiper

- Version: 11.2.6 (npm `swiper`)
- License: MIT
- Copyright: Copyright (c) 2019 Vladimir Kharlampidi (dist headers: Copyright 2014-2025 Vladimir Kharlampidi)
- Upstream: https://github.com/nolimits4web/swiper
- License text: [`vendor/swiper/LICENSE`](vendor/swiper/LICENSE)
- Distributed files: [`vendor/swiper/swiper-bundle.min.js`](vendor/swiper/swiper-bundle.min.js), [`vendor/swiper/swiper-bundle.min.css`](vendor/swiper/swiper-bundle.min.css)

### GridStack

- Version: 10.3.1 (npm `gridstack`)
- License: MIT
- Copyright: Copyright (c) 2019-2023 Alain Dumesny. v0.4.0 and older (c) 2014-2018 Pavel Reznikov, Dylan Weiss
- Upstream: https://github.com/gridstack/gridstack.js
- License text: [`vendor/gridstack/LICENSE`](vendor/gridstack/LICENSE)
- Distributed files: [`vendor/gridstack/gridstack-all.js`](vendor/gridstack/gridstack-all.js), [`vendor/gridstack/gridstack.min.css`](vendor/gridstack/gridstack.min.css), [`vendor/gridstack/gridstack-all.js.LICENSE.txt`](vendor/gridstack/gridstack-all.js.LICENSE.txt)

## 2. Agent skill packs (`skills/vendor/`)

Upstream agent skills are vendored at pinned commits so site generation is
deterministic. Skill content is copied unmodified; `UPSTREAM.md` next to each
pack records the commit, license and what was copied.

### Modern Web Guidance — Google LLC (Apache-2.0)

Modern Web Guidance — Copyright 2025 Google LLC. Licensed under the Apache
License, Version 2.0.

- Upstream: https://github.com/GoogleChrome/modern-web-guidance (commit `64a6d708f5a43f2cd3fde5d4d7db3905ba1bdf65`)
- License: Apache License 2.0 — [`skills/vendor/modern-web-guidance/LICENSE`](skills/vendor/modern-web-guidance/LICENSE)
- Attribution notice: [`skills/vendor/modern-web-guidance/NOTICE`](skills/vendor/modern-web-guidance/NOTICE) (added here because upstream ships no NOTICE file; Apache-2.0 §4(d))
- Provenance: [`skills/vendor/modern-web-guidance/UPSTREAM.md`](skills/vendor/modern-web-guidance/UPSTREAM.md)

### GSAP official skills — GreenSock (MIT)

- Copyright: Copyright (c) 2026 GreenSock
- Upstream: https://github.com/greensock/gsap-skills (commit `aed9cfd3277740755f6bfc1155c7aa645403b760`)
- License: MIT — [`skills/vendor/gsap-skills/LICENSE`](skills/vendor/gsap-skills/LICENSE)
- Provenance: [`skills/vendor/gsap-skills/UPSTREAM.md`](skills/vendor/gsap-skills/UPSTREAM.md)

### Web Animation Skills — iart.ai (MIT)

- Copyright: Copyright (c) 2026 iart.ai
- Upstream: https://github.com/iart-ai/web-animation-skills (commit `ed3a045192679b24d32090ee7a983871311ababd`)
- License: MIT — [`skills/vendor/web-animation-skills/LICENSE`](skills/vendor/web-animation-skills/LICENSE)
- Provenance: [`skills/vendor/web-animation-skills/UPSTREAM.md`](skills/vendor/web-animation-skills/UPSTREAM.md)

### GSAP browser build — GreenSock, Inc. (GSAP standard license)

- Version: 3.13.0 (npm `gsap`)
- Copyright: Copyright GreenSock, Inc.
- Upstream: https://cdn.jsdelivr.net/npm/gsap@3.13.0/dist/gsap.min.js — <https://gsap.com/licensing/>
- License: the GSAP standard license (not an OSI license); terms at <https://gsap.com/licensing/>. No separate license text is bundled with this browser build; the source URL and license are recorded in [`skills/vendor/gsap-lib/UPSTREAM.md`](skills/vendor/gsap-lib/UPSTREAM.md).
- Distributed file: [`skills/vendor/gsap-lib/gsap.min.js`](skills/vendor/gsap-lib/gsap.min.js)

## 3. Optional runtime download — Obscura (Apache-2.0)

Stitchcraft does **not** redistribute this binary. When the user chooses
**Install AI browser**, `src/stitchcraft/browser.py` downloads the pinned
upstream release into the user's app-data directory, verifies its SHA-256
digest, extracts it locally, and writes the license and notice beside it.

- Component: Obscura headless browser (rendering build)
- Version: **0.2.7** (`v0.2.7`)
- License: **Apache-2.0**
- Upstream: https://github.com/h4ckf0r0day/obscura
- Release assets: `obscura-x86_64-windows.zip`, `obscura-x86_64-linux.tar.gz`,
  `obscura-aarch64-linux.tar.gz`, `obscura-x86_64-macos.tar.gz`,
  `obscura-aarch64-macos.tar.gz` — sizes and SHA-256 digests are pinned in
  [`src/stitchcraft/browser.py`](src/stitchcraft/browser.py).
- License text snapshot: [`src/stitchcraft/data/obscura-LICENSE.txt`](src/stitchcraft/data/obscura-LICENSE.txt)
- Notice snapshot: [`src/stitchcraft/data/obscura-NOTICE.txt`](src/stitchcraft/data/obscura-NOTICE.txt)
- Installed files: the runtime plus `LICENSE`, `NOTICE`, `VERSION` and
  `install.json` in `%LOCALAPPDATA%\Stitchcraft\browser\obscura-0.2.7\`
  (platform app-data equivalents elsewhere).
- The download is optional; without it the studio falls back to skipping the
  AI browser check. The user can set `STITCHCRAFT_BROWSER_MIRROR` to fetch the
  same pinned asset through a mirror; the SHA-256 verification is unchanged.

## 4. Trademark notes

- **GSAP** and **GreenSock** are trademarks of GreenSock, Inc. The official
  skills are used under MIT; the GSAP browser build is used under the GSAP
  standard license.
- **Google**, **Chrome** and **Chrome DevTools** are trademarks of Google LLC.
  Modern Web Guidance is a Google Chrome project.
- **Kiro** and **AWS** are trademarks of Amazon.com, Inc. or its affiliates.
  Stitchcraft is an independent Kiroween 2026 entry; it is not affiliated with,
  sponsored or endorsed by Amazon Web Services.
- **npm** and npm package names/logos are trademarks of their respective package
  owners; packages in this repository are used under their own published
  licenses.
- **Obscura** is the name of the Apache-2.0 headless browser by its upstream
  authors (https://github.com/h4ckf0r0day/obscura), used here under that license.
- **Fabric.js**, **Chart.js**, **SortableJS**, **Rough.js**, **Swiper** and
  **GridStack** are names/projects of their respective authors and are used
  under the MIT license.
- All other product, company and library names are trademarks or registered
  trademarks of their respective owners and are used for identification only.
  No third-party name or logo here implies endorsement of Stitchcraft.

## 5. Redistribution policy

- No upstream file's contents are modified: vendored code, skill text and
  license files are byte-for-byte upstream. Provenance and notice files
  (`UPSTREAM.md`, `README.md`, `NOTICE`, `ATTRIBUTION.md`, `registry.toml`)
  are added beside them, never inside them.
- Every license is preserved in-tree at the paths listed above, and every
  vendored folder retains its `LICENSE` + `UPSTREAM.md`.
- Dist files are never edited after download; sizes and SHA-256 hashes are
  recorded in the per-folder `UPSTREAM.md` files (and sizes in
  `vendor/registry.toml`).
- Apache-2.0 §4(d) notice for Google's Modern Web Guidance is provided at
  `skills/vendor/modern-web-guidance/NOTICE`.
- To re-vendor: re-download the same pinned artifact, update `UPSTREAM.md`,
  `vendor/registry.toml` / `vendor/ATTRIBUTION.md` and this file, and recompute
  the hashes.
- This file is the canonical third-party notice index for the repository.
