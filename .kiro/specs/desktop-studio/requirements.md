# Stitchcraft Desktop Studio - Requirements

These requirements define v0.2, the desktop studio: a local application window,
a user-configurable OpenAI-compatible AI client, a local project store, theme
and skill catalogues, and a generation engine that turns one prompt plus one
theme package into a runnable static site. They are written in EARS form —
"WHEN <event> THE SYSTEM SHALL <behavior>" — so each one can be read as a
testable acceptance criterion. `design.md` shows how they are met and
`tasks.md` tracks the work that delivers them.

The v0.1 guarantees stay in force: the package still has zero runtime
dependencies, the validating CLI still makes no model calls, and
`stitch validate --strict` still proves the stitch. The desktop studio is a
second surface over the same vocabulary — Brief, Structure, Design tokens,
Data layer, Hero & layout, Components, Motion, Accessibility, QA & package —
not a second product.

R1. WHEN the user runs `stitch app`, THE SYSTEM SHALL start a local HTTP server bound to the loopback interface and open the studio UI in a Microsoft Edge application window, falling back to the default browser when Edge is unavailable, using only the Python standard library and assets vendored in the repository — no global package, no npm install and no external service.

Rationale: a judge or solo builder must be able to run the studio from a fresh clone with `pip install -e .` and nothing else.

R2. WHEN the user saves studio settings, THE SYSTEM SHALL validate them and persist provider, model, custom base URL, theme defaults and database mode to a settings file in the user's OS config directory outside the repository, store the AI API key in that local file only with owner-only permissions where the platform supports them, and return the key masked (presence plus at most the last four characters) from every read surface, so that no log, error message, artifact, generated site or zip export contains the key.

Rationale: local-only secret storage keeps the studio free of a keychain dependency while removing the most common secret-leak path — echoing the key back.

R3. WHEN the user configures an AI provider, THE SYSTEM SHALL offer the presets OpenAI, DeepSeek, OpenRouter and Ollama plus a custom preset, allow a custom base URL and model id, apply a per-preset default base URL, and expose a connection test that reports success, a failure reason and the round-trip time without persisting the test result or exposing the key.

Rationale: one OpenAI-compatible client covers hosted and local models; presets prevent typos while custom keeps the door open.

R4. WHEN the user selects a database for generated sites, THE SYSTEM SHALL support `local` (the generated site keeps data in browser `localStorage`) and `remote` (a REST/Supabase-compatible base URL, account URL and anon/public key), validate the URL and key shape, embed only those public values into the generated site's data layer for use at runtime in that site, and refuse to embed the AI API key or a remote key that looks like a service-role secret.

Rationale: a generated site is static; it may own a public data plane but must never carry a server secret.

R5. WHEN the studio or `stitch themes` starts, THE SYSTEM SHALL discover every theme from `themes/registry.toml`, reject missing, unknown and duplicate theme ids, and verify each package declares `theme.toml`, `SKILL.md`, `data-model.json` and at least one sample directory named by the package, exposing id, name, description, tags and preview for the UI.

Rationale: themes are data, so the catalogue must be discoverable and checkable without hard-coded lists.

R6. WHEN a generation job starts, THE SYSTEM SHALL resolve the skills selected for the theme and the generation stages from `skills/registry.toml`, load each vendored skill from disk, and inject it into the prompt under a per-skill character budget and a total character budget, truncating deterministically with an explicit marker and recording in the job which skills were injected and truncated.

Rationale: vendored skill packs are large; explicit budgets keep prompts bounded, reviewable and reproducible.

R7. WHEN the user starts a generation, THE SYSTEM SHALL run in `mock` mode by default when no AI key is configured and in `ai` mode when one is, where mock mode produces a complete site deterministically from the selected theme's sample site for the same prompt and theme — byte-identical across runs and with no network access — and ai mode calls the configured OpenAI-compatible endpoint and validates the structured response before writing any file.

Rationale: mock mode is what makes the studio demoable, reviewable and testable offline; ai mode is opt-in and guarded.

R8. WHEN a generation job runs, THE SYSTEM SHALL report progress as a stream through the nine named stages — Brief, Structure, Design tokens, Data layer, Hero & layout, Components, Motion, Accessibility, QA & package — in order, with each stage transitioning queued, running, done or failed, and SHALL keep the job's latest status, stage and error queryable after the stream closes.

Rationale: generation takes minutes; streaming is the only honest way for the UI to show what is happening.

R9. WHEN generated files are written, THE SYSTEM SHALL confine every write to the job's output directory, rejecting absolute paths, drive-letter and UNC prefixes, `..` segments, empty segments and NUL bytes, refusing symlinks that resolve outside the root, enforcing per-file, per-project and file-count caps, and rejecting a site whose root has no `index.html`.

Rationale: generated content is model output; path handling is the one place where a prompt-injected response could touch the host.

R10. WHEN a generation completes or the user opens a past project, THE SYSTEM SHALL persist project and job metadata (name, theme, prompt, mode, database mode and file index, never secrets) in the local SQLite store, serve the generated site for in-app preview through the local server, and export the project as a zip whose root contains `index.html` and that includes no secrets, settings or absolute paths.

Rationale: a project is a reviewable object, not a transient stream; persistence plus export is what turns a demo into a usable tool.

R11. WHEN the showcase is regenerated for GitHub Pages, THE SYSTEM SHALL emit a self-contained static `docs/index.html` that presents the studio, the theme catalogue and the two sample sites using relative links only, so it renders from a project subpath with no server, API key or network call.

Rationale: judges and visitors must be able to evaluate the studio from a static page, before installing anything.

R12. WHEN the user prefers the terminal, THE SYSTEM SHALL provide `stitch app` to launch the studio, `stitch generate --theme <id> --prompt <text> [--mode mock|ai] [--out <dir>]` for headless generation, and read-only `stitch themes` and `stitch skills` catalogues with a `verify` check, using the v0.1 exit-code contract — `0` success, `1` findings, `2` usage or load errors — and byte-identical output for repeated read-only invocations.

Rationale: the desktop window is a convenience, not the only way in; parity keeps the studio testable in CI and usable from Kiro.

R13. WHEN the change is proposed, THE SYSTEM SHALL be covered by a `unittest` suite for settings, themes, skills, mock generation and the server API, using temporary directories and injected fake transports so tests make no network calls and never read or write the user's real settings; CI on Python 3.12 SHALL run that suite plus `stitch validate --strict`, and `pyproject.toml` SHALL continue to declare no runtime dependencies.

Rationale: the v0.2 surfaces can leak secrets or break determinism; the tests are where those properties are proved.

R14. WHEN a skill package, a theme package or a desktop-server file is edited in Kiro, THE SYSTEM SHALL fire the matching hook — `skill-registry`, `theme-anatomy` or `desktop-server` — which instructs the agent to verify the package, run the test suite and run strict validation; and `.kiro/specs/desktop-studio/` SHALL trace every requirement R1–R14 through `design.md` and at least one task in `tasks.md`.

Rationale: v0.2 adds data-heavy surfaces; without edit-time checks the drift v0.1 banned returns exactly where the studio is most tempting to hand-edit.

## Out of scope

- A hosted or cloud service: no accounts, multi-user auth, sharing links, telemetry or hosted storage.
- Billing, usage metering, model marketplaces or fine-tuning; the studio spends the user's own provider quota.
- A general-purpose page builder, CMS, arbitrary JavaScript execution or plugin runtime inside generated sites; generation emits static text files only.
- Deploying generated sites from the app; v0.2 stops at local preview and zip export (deploy adapters remain v0.4 in the roadmap).
- Editing vendored skill packs or sample sites in place: upstream content is a read-only snapshot, re-vendored via `UPSTREAM.md`.
- Supporting AI providers that do not speak the OpenAI-compatible chat-completions contract; presets and custom cover those that do.
- OS keychain or cloud secret-manager storage for the API key; v0.2 uses a local file with owner-only permissions, and keychain is future work.
- Guaranteeing the aesthetic, factual or accessibility quality of generated content beyond the structural safety and contract checks; human review remains the quality gate.
- Mobile or native shells: the target is an Edge app window with a browser-tab fallback.
