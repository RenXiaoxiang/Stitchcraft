# Stitchcraft

> A solo AI site builder that stitches separate specialised skills into one pipeline — each module does one job, Kiro specs and hooks hold the seams together.

[![ci](https://github.com/RenXiaoxiang/Stitchcraft/actions/workflows/ci.yml/badge.svg)](https://github.com/RenXiaoxiang/Stitchcraft/actions/workflows/ci.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-ff8a3d.svg)](LICENSE)

**Stitchcraft Studio** is a local desktop app that turns one sentence and a
style choice into a complete, previewable static website. Pick a theme
(warehouse operations, staff directory, logistics control, personal space or a
brand launch page), point it at your own AI API, choose where the site's data
lives, and watch a nine-stage pipeline assemble the site from theme modules and
bundled expert skills.

It is built for [Kiroween 2026](https://kiroween.devpost.com/) (Kiro's Halloween
hackathon) in the **Skeleton Crew** category: one skeleton, two very different
apps — a warehouse operations dashboard and a personal space.

![Stitchcraft Studio](docs/assets/app.png)

## Why

A single long AI session drifts: the design brief leaks into the build prompt,
the data layer is an afterthought, accessibility is skipped and nobody can tell
which step produced which file. Stitchcraft makes every hand-off explicit:

- **One theme, one job.** Five focused theme packages instead of one giant prompt.
- **Modules, not mysteries.** Each theme is `theme.toml` + `SKILL.md` + a data
  model + an optional working sample site.
- **Skills at generation time.** Chrome's Modern Web Guidance, the official GSAP
  skills and web-animation skills are bundled, licensed and injected into the
  generation prompt.
- **Your AI, your data.** Bring any OpenAI-compatible endpoint; choose local
  browser storage or your own remote REST database for the generated site.
- **Kiro holds the seams.** `.kiro/steering`, `.kiro/specs` and `.kiro/hooks`
  keep the repo honest while it is being built.

## What you get

| Feature | Detail |
| --- | --- |
| Desktop launcher | `Stitchcraft.bat` / `启动 Stitchcraft.bat` starts a local server and opens a chromeless Edge app window. No Electron, no build step. |
| AI settings | Free and paid providers built in: **Pollinations** (no key at all), **智谱 GLM-4-Flash** (permanently free, China-friendly), **SiliconFlow** free models, **GitHub Models** (free quota with your GitHub account), plus Gemini / Groq / OpenRouter free tiers, local Ollama, or any OpenAI-compatible endpoint with your own key. Connection test included; keys stay on your machine. |
| Database choice | **Local**: the generated site persists to browser `localStorage`. **Remote**: enter a REST / Supabase-compatible URL, public anon key and table prefix — the generator embeds them into `data-config.js` and the generated site's CRUD layer talks to it directly. |
| Five themes | `warehouse-ops`, `staff-directory`, `logistics-control`, `personal-space`, `brand-launch` — each with a composition skill and (for three of them) a complete demo site. |
| Nine-stage pipeline | Brief → Structure → Design tokens → Data layer → Hero & layout → Components → Motion → Accessibility → QA & package, streamed into the UI. |
| Demo mode | No API key? Generate from the packaged sample sites so the whole flow still works (and can be recorded for the demo video). |
| Preview & export | Live iframe preview, open in a new tab, export the generated site as a ZIP. |
| Project history | SQLite-backed local history; reopen or delete any generation. |
| Skills runtime | 21 registry entries over four vendored packs plus three house skills; prompt budgets keep generations focused. |
| DESIGN.md references | Five vendored design-system references (Linear, Notion, Supabase, Airbnb, Stripe) from the MIT VoltAgent/awesome-design-md collection; each theme declares one and the generator injects an excerpt into the build prompt. |
| Aggregated tool packs | Six MIT-licensed browser libraries (Fabric.js, Chart.js, SortableJS, Rough.js, Swiper, GridStack) vendored under `vendor/` with LICENSE + UPSTREAM.md; a theme declares the ones it needs and a generated site receives only the libraries it references under `site/vendor/<id>/` — offline, no CDN. |
| Built-in AI browser | Optional Obscura runtime (Apache-2.0, ~70 MB) downloaded on demand and verified with SHA-256; it screenshots each generated site and records a DOM audit (title, headings, links, image alt coverage), so checks still work on machines without Chrome or Edge. |
| Job queue | One build runs at a time; additional requests wait with a visible queue position. Finished history is capped without evicting running or queued jobs. |
| Five UI languages | 中文 / English / Deutsch / العربية / Русский selector in the launcher; Arabic switches the whole studio to RTL. The choice is saved locally and in the app config. |
| Acceptance benchmark | Five fixed tasks under `benchmarks/tasks/` measure first-pass success, latency, warnings and retries with `stitch benchmark` (mock or your configured AI). |

## Free AI options (no paid key needed)

You do **not** need a paid API key. The studio ships with several free routes,
selectable in **Setup → Provider**:

| Provider | What it costs | Setup |
| --- | --- | --- |
| **Pollinations** (default) | **Free, no key** (community endpoint) | Nothing — select it and generate. The free tier allows roughly one request per 30s and shorter output, so it builds a compact single-file site. |
| **智谱 GLM-4-Flash** | **Permanently free** model, China-friendly | Register at [open.bigmodel.cn](https://open.bigmodel.cn/), create a free API key, paste it. Recommended when you want reliable free generations. |
| **SiliconFlow 免费模型** | Some small models are ¥0, China-friendly | Register at [cloud.siliconflow.cn](https://cloud.siliconflow.cn/), create a free key, keep or change the model id. |
| **GitHub Models** | Free quota with your GitHub account | Create a PAT with the `models: read` scope at [github.com/settings/tokens](https://github.com/settings/tokens) and paste it. |
| **Ollama** | **Free, local, private** | Install [Ollama](https://ollama.com/), run `ollama serve`, `ollama pull llama3.1`; the studio auto-detects local models. |
| **Groq / Gemini / OpenRouter** | Free tiers (may need a proxy from mainland China) | Create a free key at the provider and paste it. |
| **OpenAI / DeepSeek** | Paid | Optional: bring your own paid key. DeepSeek's official API is **not free** (low cost, requires top-up). |
| **Demo mode** | Free, no model calls | Toggle it on to generate from the packaged sample sites — always available offline. |

Free-keyless and small-model providers use a **compact single-file generation
mode** (inline CSS/JS, ~one `index.html`) so the output fits their limits. For
the richest multi-page output, use a capable model or the two demo samples.

```text
No key at all?      Pollinations (try)  →  Ollama (local)
Reliable + free:    智谱 GLM-4-Flash  ·  GitHub Models  ·  SiliconFlow
Offline demo:       toggle "Use demo mode (no API key)"
```

![A site generated by the built-in free provider, no API key](docs/assets/free-ai-site.png)

## Quickstart

Requirements: Python 3.11+ (Windows, macOS or Linux), and a modern browser
(Edge gives the chromeless window; others fall back to a normal tab).

```bash
git clone https://github.com/RenXiaoxiang/Stitchcraft.git
cd Stitchcraft
python -m pip install -e .
stitch app                       # starts the studio and opens the window
```

Windows users can also double-click `Stitchcraft.bat` (or `启动 Stitchcraft.bat`).

Inside the studio:

1. **AI API** — pick a provider, paste your key, test the connection
   (or leave it on demo mode).
2. **Data** — choose Local, or Remote and fill in your REST URL + public anon key.
3. **Style** — choose one of the five theme cards.
4. **Brief** — describe the site in a sentence or two.
5. **Generate** — watch the nine stages, then preview and export.

Headless variants:

```bash
stitch generate --theme warehouse-ops --prompt "A warehouse dashboard with inventory CRUD." --engine mock
stitch generate --theme brand-launch --prompt "Launch page for a coffee brand." --out ./my-site   # refuses to clean a foreign non-empty dir
stitch themes list
stitch skills verify
stitch validate --strict
```

## How a generation works

```mermaid
flowchart LR
    brief[Brief] --> structure[Structure]
    structure --> design[Design tokens]
    design --> data[Data layer]
    data --> layout[Hero & layout]
    layout --> components[Components]
    components --> motion[Motion]
    motion --> a11y[Accessibility]
    a11y --> qa[QA & package]
```

The generator composes a prompt from four inputs, then validates and writes the
result:

1. **Theme package** — `themes/<id>/SKILL.md` (layout blueprint, components,
   motion and data-layer rules), `data-model.json` for data themes, and the
   theme's reference HTML blocks from `themes/_blocks/`.
2. **Bundled skills** — the Modern Web Guidance reference set, landing-page
   design, official GSAP skills and web-animation skills, each truncated to its
   prompt budget.
3. **Your brief** — the sentence(s) you typed, plus an optional site title.
4. **Database configuration** — written into the site as
   `window.STITCHCRAFT_DB`; the generated `app.js` reads it and uses a
   `localStorage` adapter or a Supabase-compatible REST adapter.

### Planning and build calls

For a full-size provider the generator makes **two model calls**:

1. **Plan** — returns a contract-shaped site plan (`sitemap`, `navigation`,
   `sections`, `design`); the generator checks it against the site-plan shape
   (page paths, titles, primary navigation) before the build.
2. **Build** — receives the approved plan, the theme reference blocks and the
   selected skills, then returns the file plan.

Compact/free-keyless providers (Pollinations, Ollama and friends) use **one
build call** with a deterministic plan built from the theme, so a single
rate-limited request is enough. The nine-stage UI is a progress model: stages 2,
3, 5 and 6 are deterministic assembly/validation steps, not separate model
calls. The generator rejects absolute paths, `..`, unexpected extensions,
oversized files and sites without `index.html`, reports local files referenced
by `index.html` but never generated, builds into a private staging directory,
and only replaces the previous site after the whole build succeeds. It then
injects `data-config.js`, copies the vendored GSAP build and libraries the site
uses, and streams stage progress + logs to the UI.

Builds run **one at a time** in the studio; a second request gets a queued
status and a position, then starts automatically when the active build
finishes. The job store keeps recent history but never evicts a running or
queued job.

## Acceptance benchmark

Five fixed tasks live in [`benchmarks/tasks/`](benchmarks/tasks/); each names a
theme, a brief and the files a usable build must contain. The benchmark reports
**build success** and **functional acceptance** separately:

- **Build** — the site generated and required files exist.
- **Functional** — a browser-driven user-operation chain:
  - `warehouse-inventory`: add two items, filter by one unique SKU and prove
    the other row is hidden, verify both survive a fresh browser run, delete
    the target, and check the low-stock indicator.
  - `brand-launch`: at a 390 px viewport, the primary CTA is visible, the page
    has no horizontal overflow, and clicking the CTA reaches a destination.
- **Untested** — explicitly recorded when Obscura is not installed, the build
  is a placeholder, or the task declares no functional scenario. It is never
  counted as a pass.
- **Placeholder builds** are counted separately so mock-theme gaps cannot
  inflate the quality number.
- **Strict release gate** — `--strict` returns non-zero when a required
  functional scenario actually fails or cannot run (for example, the browser
  is missing). The default mode stays cheap for daily mock builds.

```bash
python -m stitchcraft benchmark --engine mock      # offline; placeholder + functional status
python -m stitchcraft benchmark --engine ai --repeat 2
python -m stitchcraft benchmark --engine mock --strict   # release gate
```

Reports land in a **unique run directory** under the chosen output parent
(`.stitch/benchmarks/run-<timestamp>/` by default), with `report.json`,
`report.md` and the generated sites beside them. The benchmark never passes
`force=True`, so a user-supplied `--out` cannot be overwritten.

Metrics: `build_passed`, `functional_passed/failed/untested`,
`functional_required_passed`, `functional_incomplete_required`,
`release_ready`, `placeholders`, `model_calls`, `retries`, `no_retry_passes`,
`recovered_after_retry`, `first_pass_rate` and `average_duration_ms`. See
[`benchmarks/README.md`](benchmarks/README.md).

## Themes

| Theme | Category | What it builds | Demo sample |
| --- | --- | --- | --- |
| `warehouse-ops` | data | Inventory command center: KPIs, filterable stock table, add/edit/delete, inbound timeline. | ✅ |
| `staff-directory` | data | Employee directory, departments and onboarding tasks. | AI only |
| `logistics-control` | data | Shipments, carriers and an incident board. | AI only |
| `personal-space` | personal | Essays, tag filtering, a photo wall and an about page. | ✅ |
| `brand-launch` | brand | Editorial product landing page with hero, proof and CTA. | ✅ |

Themes without a packaged sample still build a complete placeholder in demo
mode, and the UI labels them **AI only** so the sample preview is not promised
for them.

Shared building blocks live in `themes/_blocks/` (hero, stat grid, data table,
CRUD modal, article list, photo masonry, timeline, CTA band) as reference HTML
the AI can adapt. See [themes/registry.toml](themes/registry.toml) for the
machine-readable list.

## Bundled skills

| Pack | Upstream | License | What it teaches |
| --- | --- | --- | --- |
| Modern Web Guidance | [GoogleChrome/modern-web-guidance](https://github.com/GoogleChrome/modern-web-guidance) | Apache-2.0 | Accessible, modern, high-performance web UI patterns. |
| AI Design Skills | [elayadesign/ai-design-skills](https://github.com/elayadesign/ai-design-skills) | MIT | Conversion-first landing-page structure and a strict visual system for marketing pages. |
| GSAP official skills | [greensock/gsap-skills](https://github.com/greensock/gsap-skills) | MIT | Correct GSAP timelines, ScrollTrigger, plugins and cleanup. |
| Web Animation Skills | [iart-ai/web-animation-skills](https://github.com/iart-ai/web-animation-skills) | MIT | 60fps budgets, accessible motion, page transitions and micro-interactions. |
| GSAP browser build | [gsap@3.13.0](https://cdn.jsdelivr.net/npm/gsap@3.13.0/dist/gsap.min.js) | GSAP standard license | Offline animation runtime for the studio UI and generated sites. |

Skills are data: `skills/registry.toml` declares paths, license and prompt
budgets; `src/stitchcraft/skills.py` loads and injects them. Attribution is in
[skills/ATTRIBUTION.md](skills/ATTRIBUTION.md); vendored files are never edited
by hand.

## Languages

The launcher has a language selector in the top bar with five languages:

| Language | Code | Direction |
| --- | --- | --- |
| 中文 (Simplified Chinese) | `zh` | LTR |
| English | `en` | LTR |
| Deutsch (German) | `de` | LTR |
| العربية (Arabic) | `ar` | **RTL** |
| Русский (Russian) | `ru` | LTR |

The UI shell, wizard, settings, validation hints, theme labels and common status
messages are translated. The choice is stored in the local config
(`ui.language`) and in `localStorage`; first launch follows the browser language.
Arabic switches `dir="rtl"` and uses Arabic-safe font fallbacks; dynamic
technical messages from the model/backend may remain English.

The implementation is dependency-free: `app/web/i18n.js` holds the dictionaries
and a `MutationObserver` for dynamically rendered UI. Add a language by adding
its code to `SUPPORTED_LANGUAGES` in `src/stitchcraft/settings.py` and a
dictionary block to `i18n.js`.

## DESIGN.md design references

Themes can point at a vendored **DESIGN.md** design-system document
(`design_reference = "<id>"` in `theme.toml`). DESIGN.md is a plain-text format
popularised by Google Stitch: palette, typography, components, layout,
elevation, do/don't rules and responsive behaviour that an AI can follow.

Five references are vendored from the MIT
[VoltAgent/awesome-design-md](https://github.com/VoltAgent/awesome-design-md)
collection (pinned commit, unmodified files, license and per-file hashes
recorded):

| Reference | Theme | Visual language |
| --- | --- | --- |
| `linear` | `warehouse-ops` | Near-black technical canvas, lavender accent, dense data panels. |
| `notion` | `staff-directory` | Warm minimal productivity, quiet type and roomy surfaces. |
| `supabase` | `logistics-control` | Dark developer dashboard with a green accent. |
| `airbnb` | `personal-space` | Warm editorial travel, rounded cards, coral accent. |
| `stripe` | `brand-launch` | High-trust conversion design with crisp hierarchy. |

```bash
stitch designs list
stitch designs show linear
stitch designs verify
```

The generator injects a truncated DESIGN.md excerpt into the build prompt; the
generated site is still an original composition (no brand logos, images or
proprietary copy). The local studio serves `GET /api/designs`, and theme cards
show their `design: <id>` reference. License/provenance:
[designs/ATTRIBUTION.md](designs/ATTRIBUTION.md) and
[designs/vendor/awesome-design-md/UPSTREAM.md](designs/vendor/awesome-design-md/UPSTREAM.md).

## Aggregated open-source tools

Some sites need a canvas, a chart, a carousel or a dashboard grid, and asking the
model to re-invent those browser primitives on every generation produces fragile
code. Stitchcraft therefore vendors six proven, MIT-licensed browser libraries
under `vendor/<id>/` and lets a theme request them. The files are pinned,
unmodified and licensed; a generated site needs no network access to use them.

| Library | Version | License | What generated sites can build with it |
| --- | --- | --- | --- |
| [Fabric.js](https://github.com/fabricjs/fabric.js) | 5.2.4 | MIT | Interactive canvas: freehand drawing, shapes, text and object manipulation for whiteboards, planners and annotation tools. |
| [Chart.js](https://github.com/chartjs/Chart.js) | 4.4.7 | MIT | Responsive bar, line, radar and doughnut charts for KPI panels and reports. |
| [SortableJS](https://github.com/SortableJS/Sortable) | 1.15.6 | MIT | Touch-friendly drag-and-drop reordering for lists, tables and kanban boards. |
| [Rough.js](https://github.com/pshihn/rough) | 4.6.6 | MIT | Hand-drawn, sketch-style shapes and lines on canvas and SVG. |
| [Swiper](https://github.com/nolimits4web/swiper) | 11.2.6 | MIT | Touch carousels, sliders and gallery layouts with keyboard support. |
| [GridStack](https://github.com/gridstack/gridstack.js) | 10.3.1 | MIT | Draggable, resizable dashboard grids for analytics boards. |

### Whiteboard demo

[docs/demo/whiteboard/index.html](docs/demo/whiteboard/index.html) is a working
Fabric.js whiteboard that runs offline: draw with the pen and highlighter, add
shapes and text, undo, let autosave keep the board, then export a PNG. It loads
the same vendored `fabric.min.js` a generated site would use, so the demo doubles
as proof of the offline path.

![The Stitchcraft whiteboard demo](docs/assets/whiteboard.png)

[Open the whiteboard demo](docs/demo/whiteboard/index.html) ·
[Read the whiteboard skill](skills/house/stitchcraft-whiteboard/SKILL.md)

### Libraries at runtime

```bash
stitch libraries list            # every vendored library, version and license
stitch libraries show fabric     # one library's files, upstream record and entry points
stitch libraries verify          # LICENSE, UPSTREAM.md, README.md and registry agree
```

The local studio also serves `GET /api/libraries`, so the UI and scripts read the
same index. A theme package may declare the libraries it is allowed to use
(`libraries = ["fabric", "chartjs"]` in `theme.toml`); the generator copies only
the libraries the generated site actually references into `site/vendor/<id>/`,
straight from the vendored dist files. Unreferenced libraries never enter an
export, and generated sites never point at a CDN.

### Licensing

The vendor layer is MIT-only by design. Every `vendor/<id>/` folder keeps the
upstream `LICENSE`, a `UPSTREAM.md` record (repository, pinned npm version,
download URL, SPDX id, copyright line, copied files with SHA-256, vendored date)
and a `README.md` describing what the library offers and the exact relative
`<script>`/`<link>` paths a generated site should use. Distributed files are
byte-for-byte copies of the pinned upstream release: license and copyright lines
are preserved, the machine-readable index lives in `vendor/registry.toml`, and no
CDN is contacted at runtime. Generated sites receive the `LICENSE` + `UPSTREAM.md`
of every library they use, plus `GSAP-LICENSE.txt` + `GSAP-UPSTREAM.md` when GSAP
is copied into their own `vendor/` folder.

[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) is the canonical index for all
third-party material in Stitchcraft — this vendor layer, the bundled skills, the
GoogleChrome/modern-web-guidance pack (Apache-2.0, Google LLC attribution), the
GSAP packs and their standard license, plus every license text. The
human-readable companion for the six libraries is
[vendor/ATTRIBUTION.md](vendor/ATTRIBUTION.md). Adding, upgrading or removing a
third-party file starts and ends in those two files.

## Built-in AI browser (Obscura)

Stitchcraft can give the AI its own browser instead of assuming the customer has
a modern Chrome or Edge installed. On first use the studio downloads
[Obscura](https://github.com/h4ckf0r0day/obscura) — a ~70 MB, Apache-2.0
headless browser written in Rust — into the app-data directory, verifies the
release against pinned SHA-256 digests, and drives it locally. Nothing is
bundled in the repository and nothing is uploaded: the runtime stays on the
machine, renders with its own engine, and records a screenshot plus a small DOM
audit for every build.

![The AI browser tab: Obscura screenshot and DOM audit of a generated warehouse site](docs/assets/ai-browser.png)

```bash
stitch browser status            # platform, version, license, installed/path
stitch browser install           # download + SHA-256 verification + extraction
stitch browser check --url URL   # render a page, screenshot it, audit title/h1/links/alts
stitch browser serve --port 9222 # CDP server for Playwright / Puppeteer / agents
stitch browser mcp               # MCP server (browser_navigate, browser_screenshot, ...)
stitch browser remove            # delete the local runtime and its checks
```

In the studio, step 1 has an **AI browser** card (install / remove / automatic
check toggle), and the **AI browser** tab shows the latest screenshot and audit.
If the runtime is not installed the generation still succeeds; the check is
skipped and the UI says so. The check is local-only: Obscura is started with
`--allow-private-network` so it can reach `127.0.0.1`, never a remote service.

- **Platforms:** Windows x86_64, Linux x86_64/aarch64, macOS Intel/Apple silicon.
- **License:** Apache-2.0. The license and notice are written next to the
  downloaded runtime; the notice index is
  [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
- **Slow GitHub?** Set `STITCHCRAFT_BROWSER_MIRROR=https://gh-proxy.com` (or a
  `{url}` template) before installing; the SHA-256 check still applies.
- **No background daemon:** the CLI starts the runtime per check and exits; the
  server only invokes it during a build or a manual check.

## Generated data layer

Every generated site receives a `data-config.js`:

```js
window.STITCHCRAFT_DB = {
  mode: "local",            // "local" | "remote"
  kind: "local",            // "local" | "supabase" | "rest"
  url: "",                  // remote REST base URL
  anonKey: "",              // remote public/anon key only
  tablePrefix: "stitchcraft"
};
```

The theme's data skill writes one adapter with two backends: `localStorage` for
offline/local mode, or Supabase-compatible REST calls
(`${url}/rest/v1/${tablePrefix}_<table>`) for remote mode. Only public/anon keys
belong there — never an AI key, never a service key.

## Kiro integration

The repository is built as a Kiro project, not just with it:

| Layer | Path | Role |
| --- | --- | --- |
| Steering | `.kiro/steering/{product,tech,structure}.md` | Persistent rules every Kiro task loads. |
| Specs | `.kiro/specs/stitchcraft-core/`, `.kiro/specs/desktop-studio/` | Requirements (EARS) → design → tasks for the pipeline and the desktop studio. |
| Hooks | `.kiro/hooks/*.kiro.hook` | File-edit checks: seam check, module anatomy, spec sync, skill registry, theme anatomy, desktop smoke test, manual pipeline gate. |
| Validation | `stitch validate --strict` | Proves modules, contracts, pipeline, hooks, themes and skills still agree. |

`python -m stitchcraft validate --strict` is the single command that keeps the
whole repository coherent; the hooks call it whenever a seam changes.

## Repository layout

```text
.
├── 启动 Stitchcraft.bat / Stitchcraft.bat   desktop launcher
├── app/web/                                 local studio UI (vanilla JS + vendored GSAP)
├── src/stitchcraft/                         stdlib backend + CLI
│   ├── browser.py                           optional Obscura AI browser (download-on-demand)
│   └── data/                                Obscura Apache-2.0 license + notice snapshots
├── themes/                                  theme packages + _blocks + registry
├── skills/                                  vendored skill packs + registry + attribution
├── designs/                                 vendored DESIGN.md references + registry
├── vendor/                                  six MIT browser libraries + registry + attribution
├── modules/ contracts/ pipeline/            the original nine-module stitch spine
├── .kiro/                                   steering, specs and hooks
├── hackathon/                               Kiroween 2026 submission kit
├── benchmarks/                              fixed acceptance tasks + reporting
├── docs/                                    architecture/authoring/roadmap + Pages showcase
│   ├── demo/whiteboard/                     offline Fabric.js whiteboard demo
│   └── integrations/                        optional Playwright MCP setup
├── tests/                                   unit tests + API smoke tests
├── 开发文档.txt                              full development plan (Chinese)
└── examples/                                seed requests for dry runs
```

## Development

```bash
python -m unittest discover -s tests -v                      # unit + API tests
PYTHONPATH=src python -m stitchcraft validate --strict       # repository invariants
python -m stitchcraft app --smoke-test --no-window           # headless end-to-end studio test
python -m stitchcraft benchmark --engine mock               # fixed acceptance tasks
python -m stitchcraft designs verify                        # DESIGN.md references
python -m stitchcraft browser status                         # optional AI browser (Obscura)
python -m stitchcraft themes verify
python -m stitchcraft skills verify
```

CI runs the same checks on Python 3.11, 3.12 and 3.13. Read
[AGENTS.md](AGENTS.md) before changing anything: the rules apply to humans and
AI agents alike.

- [`.kiro/steering/lean-engineering.md`](.kiro/steering/lean-engineering.md) —
  necessity-first engineering guardrails (inspired by Ponytail, MIT).
- [`docs/integrations/playwright-mcp.md`](docs/integrations/playwright-mcp.md) —
  optional Playwright MCP setup for interactive E2E tests; not bundled and not
  required at runtime.

## Privacy and security

- The studio binds to `127.0.0.1` only. Requests with an unexpected `Host` are
  rejected (DNS-rebinding protection); writes with a foreign `Origin` or a
  non-JSON `Content-Type` are rejected too.
- The management API is served **only** on `127.0.0.1`; `localhost` serves
  generated previews and demo sites only and cannot read or change settings.
- AI keys and database credentials are stored in your app-data directory
  (`%LOCALAPPDATA%\Stitchcraft\config.json`), never in the repo, logs or
  generated sites.
- Generated sites are previewed from `http://localhost:<port>`, a different
  origin from the studio API, inside a sandboxed iframe, with a CSP header.
  Their JavaScript cannot call `/api/settings` or read your AI keys.
- Generated files are sandboxed: relative paths, extension whitelist, size caps.
- A build is written to a private staging directory and replaced into place only
  after it succeeds; a failed AI call keeps the previous site intact. The
  generator still refuses to replace a non-empty output directory it did not
  create; pass `--force` only when you mean it.
- No telemetry. No network calls except the AI endpoint you configure.

## Kiroween 2026

- Category: **Skeleton Crew** (one skeleton, two apps); Frankenstein flavor
  (Kiro + Chrome guidance + GSAP + bring-your-own AI) and Costume Contest styling.
- Submission materials, video storyboard and compliance checklist live in
  [hackathon/](hackathon/).
- Demo URL (GitHub Pages showcase): https://renxiaoxiang.github.io/Stitchcraft/

## 中文说明

Stitchcraft 是一个本地桌面应用：选一个网站主题，用一句话描述需求，接入你自己的
AI API，就能生成一个完整、可预览、可导出的网站。

- **桌面启动**：双击 `启动 Stitchcraft.bat`，在 Edge 应用窗口里使用，无需浏览器地址栏。
- **自带 AI**：OpenAI / DeepSeek / OpenRouter / Ollama / 任意 OpenAI 兼容接口；
  Key 只存在本机配置里。
- **本地 / 远端数据库**：选本地时生成站点用浏览器 localStorage；选远端时填入数据库
  URL 与公开 anon key，配置会被写进生成站点，站点的增删改查直接访问它。
- **风格主题**：仓储管理、人员管理、后勤管理、个人空间、品牌落地页。
- **内置技能**：Chrome 官方 Modern Web Guidance、landing-page design、GSAP 官方
  skills、web-animation skills，生成时自动注入提示词；主题的 `_blocks/` 参考区块
  也会一起交给模型。
- **设计参考**：5 份 MIT 的 DESIGN.md（Linear / Notion / Supabase / Airbnb /
  Stripe，来自 VoltAgent/awesome-design-md），每个主题声明一份，生成时按预算
  注入颜色、字体、组件与布局规则。
- **零 Key 演示**：演示模式内置三个成品站（仓储看板、个人空间、品牌发布页），断网也能完整演示；
  另外两个主题会标注 **AI only**，演示模式只输出占位页。
- **安全**：本地接口校验 Host / Origin / Content-Type；预览从 `localhost` 另一
  个源加载并放在 sandbox iframe 里；生成目录非空且不是 Stitchcraft 创建时拒绝清理。
- **参赛**：Kiroween 2026（Skeleton Crew 赛道），提交材料见 `hackathon/`。

完整开发计划见 [`开发文档.txt`](开发文档.txt)。

## License

[MIT](LICENSE) © 2026 RenXiaoxiang

Kiro and Kiroween are trademarks of Amazon Web Services. GSAP and GreenSock are
trademarks of GreenSock, Inc. Chrome and Google are trademarks of Google LLC.
Other names, including the six vendored JavaScript libraries, are the property
of their respective owners. Third-party skills, design references and libraries are used under
their upstream licenses; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)
for the canonical index, [skills/ATTRIBUTION.md](skills/ATTRIBUTION.md) for the
skill packs and [vendor/ATTRIBUTION.md](vendor/ATTRIBUTION.md) for the vendored
libraries.
