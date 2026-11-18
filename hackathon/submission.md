# Stitchcraft

**Devpost title:** Stitchcraft — one skeleton, any site

**Tagline (49 characters):** One skeleton, any site. AI stitches nine skills.

**Category:** Skeleton Crew (primary) · Frankenstein (secondary)

**Links:** [Repository](https://github.com/RenXiaoxiang/Stitchcraft) ·
[Live showcase](https://renxiaoxiang.github.io/Stitchcraft/) ·
[Demo video — placeholder, add the public YouTube URL before submitting](#links)

---

## Inspiration

Every AI tool can now produce one convincing landing page. Ask the same tool for
a *whole website* — structure, design system, copy, SEO, accessibility, a release
check, a deploy plan — and it degrades in a predictable way. The brief drifts by
the third screen. The design and the copy stop agreeing. SEO is bolted on at the
end. The accessibility pass is done "well enough". None of it can be inspected,
because it all happened in one long conversation.

The hard part of a website was never one page. It is the hand-offs.

We wanted a builder that treats a website the way a careful engineer treats one:
nine narrow jobs, each with a written procedure and a contract, passing artifacts
instead of vibes. Kiro is where that idea became a product rather than a
diagram — steering rules that stay loaded while you work, a spec that describes
the system before it exists, and hooks that re-check the seams whenever an edit
lands. The moment we saw the Skeleton Crew category, the fit was obvious: build
one skeleton properly, then prove it by showing it dressed as two completely
different applications. That is exactly the product we wanted to make.

## What it does

Stitchcraft is a local-first desktop studio for generating complete websites
with your own AI. Nothing is uploaded to an account you do not control; the
studio runs on your machine and talks to the model endpoint you choose.

The journey, end to end:

1. **Configure your AI — or use a free one.** Pick a built-in free provider
   (Pollinations needs no key at all; 智谱 GLM-4-Flash is permanently free and
   China-friendly; GitHub Models uses your GitHub account; Ollama runs locally),
   or enter any OpenAI-compatible endpoint with your own key. Credentials are
   stored locally and never written into a generated site or into the
   repository.
2. **Choose your database.** Local: the generated site keeps its data in the
   browser's `localStorage`, with zero setup. Remote: the site talks to a REST
   table (a table URL plus account details) you already own. The choice is
   embedded into the generated site's data layer, and the same UI runs on either
   one — local mode falls back to cached data with an offline badge if a remote
   call fails.
3. **Pick a theme.** Five theme modules ship today: **Warehouse Operations**,
   **Staff Directory**, **Logistics Control**, **Personal Space** and **Brand
   Launch**. Each theme is a package — blocks, a data model, accent tokens,
   sample data, and the skills it needs — not a fork of the skeleton.
4. **Describe the site.** Type a short brief: what the site is for, who reads
   it, what it should contain. No page-by-page spec required.
5. **Watch the nine stages run.** Brief intake, site plan, design system,
   copywriting, site assembly, discovery (SEO), accessibility, the QA gate and
   the deploy plan — the same nine-module stitch that the CLI validates, now
   driven from the studio. Each stage hands the next a contract-checked JSON
   artifact instead of a chat message.
6. **Preview and export.** Preview the generated site inside the studio, then
   export it as static HTML, CSS and JavaScript that runs offline — no build
   step, no CDN, no framework.

### Two sites, one skeleton

The Skeleton Crew requirement is that one skeleton hold up under two distinct
applications. Both of ours are in the repo, generated from the same theme-block
vocabulary and the same data layer:

- **Warehouse Operations** — "Ember &amp; Bean Fulfilment", an operations dashboard: KPI
  tiles, filterable inventory with add/edit/delete, inbound dock shipments and
  an activity log. Source: [`themes/warehouse-ops/sample/`](../themes/warehouse-ops/sample/).
- **Personal Space** — "Notes from the attic", a quiet literary site: notes with
  tags and search, a photo wall, an about section, dark editorial typography.
  Source: [`themes/personal-space/sample/`](../themes/personal-space/sample/).

Same skeleton, same contracts, same export format. Nothing in the warehouse app
is a special case of the personal site, and the personal site does not ship a
table it does not need.

## How we built it

**Foundation (v0.1, in the repo).** The core is a dependency-free Python package
(`src/stitchcraft/`, Python 3.11+ standard library only) that loads the repo from
disk, discovers modules and contracts, validates six layers of seams, renders the
pipeline as a Mermaid graph, and stages deterministic `PROMPT.md` files for all
nine stages. `stitch validate --strict` is the proof that the stitch holds; the
same command runs in CI and behind the Kiro hooks. Nine modules
(`modules/01-brief/` … `modules/09-deploy/`), each one `SKILL.md` plus
`module.toml`, and nine JSON Schema contracts (`contracts/*.schema.json`)
describe the pipeline as data. No model calls, no network, no runtime
dependencies.

**The desktop studio (v0.2, this submission).**

- **Local web UI, desktop feel.** The studio is a plain HTML/CSS/JavaScript
  front end (`app/web/`) served by the local Python process. `stitch app` starts
  the server on `127.0.0.1` and opens it in an Edge app window
  (`msedge --app=…`), which gives a chrome-less desktop window without shipping
  Electron or any other runtime dependency.
- **OpenAI-compatible client.** A small client speaks the OpenAI
  chat-completions shape, so the user can point Stitchcraft at any compatible
  provider or local gateway. Keys live in local storage, never in exported
  files.
- **SQLite project store.** The studio keeps projects, settings and generation
  runs in a local SQLite database through the standard library's `sqlite3`. No
  server account, no cloud sync.
- **Theme module library.** `themes/` holds five packages with a shared
  `theme.toml` vocabulary (blocks, data model, skills, accent, sample) and a
  registry the runtime reads. Themes are data: adding one does not change the
  generator.
- **Bundled skill packs.** The generator assembles a scoped prompt per stage
  from the theme package plus the skills it declares, with per-skill character
  budgets in `skills/registry.toml`. The packs are vendored with pinning and
  attribution: Google Chrome's Modern Web Guidance (Apache-2.0), GreenSock's
  official GSAP skills (MIT), iart-ai's web-animation skills (MIT), and the GSAP
  3.13.0 browser build. Sources, commits and license texts are recorded in
  [`skills/ATTRIBUTION.md`](../skills/ATTRIBUTION.md).
- **GSAP in the UI.** The vendored `gsap.min.js` powers the studio's and the
  themes' motion — no CDN request at runtime, and every animation respects
  `prefers-reduced-motion`.
- **Kiro governance.** `.kiro/steering/` (product, tech, structure), two specs
  (`.kiro/specs/stitchcraft-core/` for v0.1 and `.kiro/specs/desktop-studio/`
  for v0.2, each with requirements, design and tasks) and seven agent hooks
  (`seam-check`, `module-anatomy`, `pipeline-gate`, `spec-sync`,
  `skill-registry`, `theme-anatomy`, `desktop-server`).
- **Delivery.** GitHub Actions runs the unit tests, `stitch validate --strict`,
  a plan render and a dry-run smoke test on every push; GitHub Pages serves the
  static showcase and both demo sites.

### Aggregated open-source tools & license hygiene

Generated sites should not re-invent a chart, a carousel or a canvas, and they
should not depend on a CDN either. We vendor six MIT-licensed browser libraries
under `vendor/<id>/` and let a theme declare the ones it needs:

| Library | Version | Use in a generated site |
| --- | --- | --- |
| Fabric.js | 5.2.4 | Whiteboards, planners and canvas annotation. |
| Chart.js | 4.4.7 | KPI panels, dashboards and reports. |
| SortableJS | 1.15.6 | Drag-and-drop lists, tables and kanban boards. |
| Rough.js | 4.6.6 | Hand-drawn sketch graphics. |
| Swiper | 11.2.6 | Carousels and gallery sliders. |
| GridStack | 10.3.1 | Draggable dashboard grids. |

Each folder carries the upstream `LICENSE`, an `UPSTREAM.md` (repository,
pinned version, download URL, copied files and date) and a `README.md`;
`vendor/registry.toml` is the machine-readable index and
`vendor/ATTRIBUTION.md` the human-readable one. The runtime exposes
`stitch libraries list|show|verify` and `GET /api/libraries`, and the generator
copies only the libraries a site actually references into `site/vendor/<id>/` —
never a CDN URL. The working Fabric.js whiteboard at
[`docs/demo/whiteboard/index.html`](../docs/demo/whiteboard/index.html) is the
end-to-end proof: it runs offline from the same vendored `fabric.min.js` a
generated site receives.

License hygiene is part of the submission, not an afterthought. The existing
GoogleChrome/modern-web-guidance pack keeps its Apache-2.0 license and Google
LLC attribution; the GSAP packs keep their license; every MIT library keeps its
copyright line; and the canonical index of all third-party material lives in
[`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md). This is also how the entry
meets Kiroween's requirement that third-party trademarks and copyrighted
material be used with permission: every vendored file is unmodified, distributed
under its upstream license, and traceable to a pinned upstream version in the
repository.

## Challenges

- **Keeping seven layers honest.** A contract, its schema, the producing module,
  the consuming module, the pipeline edge, the hook pattern and the docs all
  describe the same seam. Human discipline loses that fight. We made the
  validator the referee: every rule is a check with a stable issue code, every
  check has a passing and a failing test, and the Kiro hooks ask the agent to run
  that same check after an edit. "Never weaken a contract to silence the
  validator" became a hook instruction, not a slogan.
- **One skeleton, two apps — without a fork.** The tempting shortcut is to let
  each demo grow its own layout and data layer. We held the line that a theme is
  a package of blocks plus a data model plus declared skills, and that the
  generator knows nothing about "warehouse" or "personal". The warehouse app
  needed a table and a CRUD modal; the personal site needed notes, tags and a
  photo wall. Both had to come out of the same block vocabulary, or the Skeleton
  Crew claim would be false.
- **Bring-your-own-everything, with no backend account.** The AI endpoint and
  the database are the user's, which means the studio cannot store either on a
  server. That forced a clean split between settings (local), project state
  (local SQLite) and generated-site data (localStorage or the user's REST
  table), and it made "the generated site must work offline by default" a hard
  rule rather than a nice-to-have.
- **Desktop feel without Electron.** An app window around a local page looks
  trivial until lifecycle bites: choosing a free port, passing the real origin
  to the UI, shutting the server down when the window closes, and never leaving
  a stray process behind. Solving it in standard-library Python kept the install
  identical to the CLI's: `pip install -e .`, nothing else.
- **Vendoring skills honestly.** Copying other people's skill packs into a repo
  is easy; doing it with pinned commits, license files, upstream records and
  trademark notes is work. `skills/ATTRIBUTION.md` and the
  `skill-registry.kiro.hook` exist so the next vendor refresh cannot quietly
  lose that provenance.
- **Context budgets are real.** Eight GSAP skills and 200-plus guidance files do
  not fit in one prompt. The registry's per-skill character budgets and each
  theme's declared skill list keep the generation prompt scoped to what that
  theme actually needs.
- **Spec drift.** Two specs, each with fourteen requirements, is a lot of
  traceability to keep true. The `spec-sync` hook enforces that every numbered
  requirement is covered by the design and by at least one task, and that a task
  is never ticked for a file that does not exist.

## Accomplishments

- A complete, working path from a typed brief to a previewable, exportable
  static site, with no third-party runtime dependencies and no cloud account.
- One shared skeleton demonstrated through two genuinely different
  applications (warehouse operations and personal space), with three more
  themes shipping alongside them.
- A pipeline that is data, not code: nine modules, nine contracts, one TOML
  graph, and a validator that fails loudly when any of them disagree.
- A Kiro layer with real teeth: two specs in requirements/design/tasks form and
  seven hooks, three of which were added specifically for the v0.2 studio
  (`skill-registry`, `theme-anatomy`, `desktop-server`).
- Honest vendoring: three upstream skill packs and the GSAP browser build, all
  pinned, licensed and attributed.
- The boring infrastructure a judge can actually check: CI on every push, a
  public Pages showcase, both demo sites static and self-contained, and a
  five-minute verification path in the Kiro write-up.

## What we learned

- **Structure beats model size.** A narrow job with a written procedure and a
  schema-checked hand-off produces more reliable output than one generalist
  prompt, and the result is inspectable. When a stage goes wrong, we know which
  file to open.
- **A rule without a check is a suggestion.** The steering files describe the
  rules, but the hooks and the validator are what make them real. The line we
  kept returning to is in the repo: if the hook is easy to ignore, the rule will
  be ignored.
- **A theme is a data model, not a stylesheet.** The first version of a theme was
  colours and fonts. It became useful when it also carried the collections, the
  fields and the skills the generator should read.
- **Spec-driven development is scope control.** Writing requirements, design and
  tasks before code made the "one more feature" conversation honest, and it gave
  the hooks something concrete to enforce.
- **Local-first is a product feature, not a limitation.** Users hand an AI tool
  their brief and their API key. Saying "it runs on your machine, your key never
  leaves it, and the exported site works offline" turned out to be a stronger
  pitch than any hosted convenience.
- **Build the skeleton before you dress it.** v0.1 proved the seams; v0.2 could
  then iterate on themes and UI without the pipeline shifting underneath.

## What's next

- **Compiled-site parity.** Today the studio assembles and exports static
  files; the roadmap's next step is a dedicated compiler that produces the same
  output deterministically from artifacts alone, with snapshots in CI.
- **More themes and a theme SDK.** One more data app and one editorial theme are
  already sketched; a documented plan for a third-party theme package would let
  others ship skeletons without touching the generator.
- **Deploy adapters.** A deploy plan is produced today, but shipping still means
  moving files yourself. Adapters for Cloudflare Pages, Vercel, Netlify and
  GitHub Pages are on the roadmap, with credentials and rollback in human hands.
- **Adapter protocol for agents.** The nine-stage run is driven by the studio's
  own client. A documented adapter protocol would let Kiro, a CLI agent or a
  manual mode execute the same stages on the same artifacts.
- **Artifact instance validation.** The CLI validates contract shape; the next
  step is validating every produced artifact instance at the seam before the next
  stage starts.
- **Accessibility and motion beyond the first pass.** The web-animation skills
  already enforce reduced-motion; we want the same mechanical treatment for
  focus order, contrast tokens and keyboard navigation in generated themes.

## How Kiro was used

Kiro is not a footnote in this project; it is the reason the project stayed
coherent. The repository is agent-first: every module, contract and hook was
written in Kiro against the steering files loaded into the task, with the spec
open as the source of truth.

- **Steering** — `.kiro/steering/product.md`, `tech.md` and `structure.md` load
  on every task. They carry the normative rules: one module, one job; artifacts,
  not conversations; never weaken a contract; dependency-free core; Kiro owns
  process, not product.
- **Specs** — `.kiro/specs/stitchcraft-core/` describes the v0.1 pipeline in
  EARS form (R1–R14) with a design and a task list. The v0.2 studio was specified
  the same way in `.kiro/specs/desktop-studio/`, so the app had requirements and
  a design before it had code.
- **Hooks** — seven agent hooks re-check the seams. `seam-check` runs
  `validate --strict` and `plan` when a contract, module manifest or pipeline
  graph changes; `module-anatomy` checks the seven required skill sections and
  the exact hand-off path; `pipeline-gate` runs strict validation on human
  trigger; `spec-sync` keeps requirements, design and tasks traceable; and the
  v0.2 `skill-registry`, `theme-anatomy` and `desktop-server` hooks do the same
  job for vendored skills, theme packages and the local server.
- **Spec-driven development** — behaviour changed in this order every time:
  requirements, then design, then tasks, then implementation, then tests. The
  `spec-sync` hook is the enforcement, and `tasks.md` is only ticked when the
  file or test it cites exists.
- **Terminal workflow** — Kiro's terminal ran the same commands as CI:
  `stitch validate --strict`, `python -m unittest discover -s tests -v`,
  `stitch plan`, `stitch run --dry-run`, and later the studio smoke checks.

The full evidence table — capability, exact file path, what it enforces, and a
five-minute verification path — is in [`kiro-usage.md`](kiro-usage.md).

## Built with

`Python 3.11+` · `Python standard library` · `JavaScript (ES2019)` · `HTML5` ·
`CSS` · `SQLite` · `JSON Schema` · `TOML` · `OpenAI-compatible API` · `GSAP` ·
`Kiro` · `GitHub Actions` · `GitHub Pages` · `local-first` · `static site
generation`

## Links

- **Repository:** <https://github.com/RenXiaoxiang/Stitchcraft>
- **Live showcase (GitHub Pages):** <https://renxiaoxiang.github.io/Stitchcraft/>
- **Demo video:** *placeholder — the public YouTube URL must be pasted here
  before the Devpost deadline. The storyboard is in
  [`video-script.md`](video-script.md).*
- **License:** MIT — [`LICENSE`](../LICENSE)
- **Third-party attribution:** [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md)
  (canonical index) and [`skills/ATTRIBUTION.md`](../skills/ATTRIBUTION.md)
- **Kiro write-up:** [`kiro-usage.md`](kiro-usage.md)
- **Compliance checklist:** [`checklist.md`](checklist.md)
