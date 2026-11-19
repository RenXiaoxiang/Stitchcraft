# Attribution — bundled browser libraries

`vendor/` bundles six permissively licensed browser libraries so generated sites
can use them fully offline. Dist files are vendored, unmodified upstream builds.
The machine-readable index is [`registry.toml`](registry.toml).

| Library | Version | License | Copyright | Upstream | Files |
| --- | --- | --- | --- | --- | --- |
| Fabric.js (`fabric`) | 5.2.4 | MIT | Copyright (c) 2008-2015 Printio (Juriy Zaytsev, Maxim Chernyak) | https://github.com/fabricjs/fabric.js | `vendor/fabric/fabric.min.js` |
| Chart.js (`chartjs`; npm package `chart.js`) | 4.4.7 | MIT | Copyright (c) 2014-2024 Chart.js Contributors | https://github.com/chartjs/Chart.js | `vendor/chartjs/chart.umd.min.js` |
| SortableJS (`sortablejs`) | 1.15.6 | MIT | Copyright (c) 2019 All contributors to Sortable | https://github.com/SortableJS/Sortable | `vendor/sortablejs/Sortable.min.js` |
| Rough.js (`roughjs`) | 4.6.6 | MIT | Copyright (c) 2019 Preet Shihn | https://github.com/pshihn/rough | `vendor/roughjs/rough.min.js` |
| Swiper (`swiper`) | 11.2.6 | MIT | Copyright (c) 2019 Vladimir Kharlampidi | https://github.com/nolimits4web/swiper | `vendor/swiper/swiper-bundle.min.js`, `vendor/swiper/swiper-bundle.min.css` |
| GridStack (`gridstack`) | 10.3.1 | MIT | Copyright (c) 2019-2023 Alain Dumesny. v0.4.0 and older (c) 2014-2018 Pavel Reznikov, Dylan Weiss | https://github.com/gridstack/gridstack.js | `vendor/gridstack/gridstack-all.js`, `vendor/gridstack/gridstack.min.css`, `vendor/gridstack/gridstack-all.js.LICENSE.txt` |

## Every folder keeps its paperwork

Each `vendor/<id>/` folder contains the complete, unmodified upstream license
in `LICENSE`, provenance in `UPSTREAM.md` (upstream repo, pinned npm version,
download URL(s), SPDX id, exact copyright, vendored date 2026-11-19, files
copied with SHA-256, one-line purpose) and `README.md` (what the library
enables, plus the exact relative `<script>`/`<link>` paths a generated site
should use).

## Unmodified distribution

The dist files are byte-for-byte as downloaded from the pinned jsDelivr URLs
recorded in each `UPSTREAM.md`; they were never edited after download. Chart.js
and Rough.js are served at their pinned URLs as jsDelivr's generated `.min`
aliases of the packages' bundled UMD builds — the vendored bytes are exactly
what those pinned URLs return. No file under `vendor/` is patched or otherwise
transformed by Stitchcraft; individual upstream builds may already be minified.

## Canonical notice

This folder is a summary. The repository-wide, canonical third-party notice
index is [`../THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md). Vendored
2026-11-19.
