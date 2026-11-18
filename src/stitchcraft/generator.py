"""Generation engine: theme + brief + skills become a complete static site.

Two engines share one pipeline:

* ``mock`` — deterministic demo output. It mounts the theme's packaged sample
  (warehouse-ops, personal-space) or a small placeholder build, so the app is
  fully demonstrable without an API key.
* ``ai``   — composes a prompt from the theme skill, the data model, the selected
  vendored skills and the user's brief, calls the user's OpenAI-compatible
  endpoint, validates the returned file plan and writes it safely.

The engine itself makes no network calls except the one the user configured.
"""

from __future__ import annotations

import json
import re
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import ai_client
from .settings import AppConfig, PRESETS, provider_requires_key
from .skills import build_skill_context, get_skill, load_registry
from .themes import Theme, get_theme, load_data_model, sample_dir, theme_skill_text

STAGES: tuple[tuple[str, str], ...] = (
    ("brief", "Brief"),
    ("structure", "Structure"),
    ("design", "Design tokens"),
    ("data", "Data layer"),
    ("layout", "Hero & layout"),
    ("components", "Components"),
    ("motion", "Motion"),
    ("a11y", "Accessibility"),
    ("qa", "QA & package"),
)

MAX_FILE_BYTES = 600_000
MAX_TOTAL_BYTES = 5_000_000
ALLOWED_SUFFIXES = {".html", ".css", ".js", ".json", ".svg", ".txt", ".md", ".webmanifest", ".xml"}

__all__ = [
    "GenerationError",
    "GenerationRequest",
    "GenerationResult",
    "STAGES",
    "generate_site",
    "stage_names",
]


class GenerationError(RuntimeError):
    """Raised when a generation cannot be completed."""


@dataclass
class GenerationRequest:
    theme_id: str
    prompt: str
    title: str = ""
    engine: str = "mock"
    database: dict = field(default_factory=dict)
    skills: list[str] | None = None


@dataclass
class GenerationResult:
    theme_id: str
    title: str
    engine: str
    out_dir: Path
    files: list[str]
    summary: str
    warnings: list[str] = field(default_factory=list)
    duration_ms: int = 0

    def public_dict(self) -> dict:
        return {
            "theme_id": self.theme_id,
            "title": self.title,
            "engine": self.engine,
            "out_dir": str(self.out_dir),
            "files": list(self.files),
            "summary": self.summary,
            "warnings": list(self.warnings),
            "duration_ms": self.duration_ms,
        }


def stage_names() -> list[str]:
    return [name for _key, name in STAGES]


def _emit(callback, index: int, status: str, message: str | None = None, level: str = "info") -> None:
    if callback is not None:
        callback(index, status, message, level)


def _clean_dir(directory: Path) -> None:
    for entry in directory.iterdir():
        if entry.is_dir():
            shutil.rmtree(entry, ignore_errors=True)
        else:
            entry.unlink(missing_ok=True)


def _safe_relpath(raw: object) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise GenerationError("AI returned a file without a path.")
    candidate = Path(raw.strip().lstrip("/"))
    if candidate.is_absolute() or any(part in {"..", ""} for part in candidate.parts):
        raise GenerationError(f"Unsafe file path returned by the AI: {raw!r}")
    if candidate.suffix.lower() not in ALLOWED_SUFFIXES:
        raise GenerationError(f"Generated file type is not allowed: {raw!r}")
    return candidate


def _write_file_plan(out_dir: Path, plan: list[dict]) -> list[str]:
    written: list[str] = []
    total = 0
    for item in plan:
        if not isinstance(item, dict):
            raise GenerationError("AI returned a malformed file entry.")
        relative = _safe_relpath(item.get("path"))
        content = item.get("content")
        if not isinstance(content, str) or not content.strip():
            raise GenerationError(f"Generated file is empty: {relative.as_posix()}")
        encoded = content.encode("utf-8")
        if len(encoded) > MAX_FILE_BYTES:
            raise GenerationError(f"Generated file is too large: {relative.as_posix()}")
        total += len(encoded)
        if total > MAX_TOTAL_BYTES:
            raise GenerationError("Generated site exceeds the size limit.")
        target = out_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        written.append(relative.as_posix())
    return written


def _list_files(directory: Path) -> list[str]:
    return sorted(
        path.relative_to(directory).as_posix()
        for path in directory.rglob("*")
        if path.is_file()
    )


def _data_config(mode: str, remote: dict) -> dict:
    if mode == "remote":
        return {
            "mode": "remote",
            "kind": str(remote.get("kind", "supabase")),
            "url": str(remote.get("url", "")).rstrip("/"),
            "anonKey": str(remote.get("anon_key", "")),
            "tablePrefix": str(remote.get("table_prefix", "stitchcraft")),
        }
    return {"mode": "local", "kind": "local", "url": "", "anonKey": "", "tablePrefix": "stitchcraft"}


def _write_data_config(out_dir: Path, config: dict) -> None:
    content = "// Written by Stitchcraft. Safe to commit: contains no AI keys.\nwindow.STITCHCRAFT_DB = " + json.dumps(
        config, indent=2
    ) + ";\n"
    (out_dir / "data-config.js").write_text(content, encoding="utf-8")


def _ensure_data_config_link(out_dir: Path, warnings: list[str]) -> None:
    index = out_dir / "index.html"
    if not index.is_file():
        return
    html = index.read_text(encoding="utf-8", errors="replace")
    if "data-config.js" in html:
        return
    snippet = '<script src="data-config.js"></script>\n'
    if "</body>" in html:
        html = html.replace("</body>", snippet + "</body>", 1)
    else:
        html = html + "\n" + snippet
    index.write_text(html, encoding="utf-8")
    warnings.append("index.html did not link data-config.js; the generator inserted it.")


def _copy_gsap_if_needed(root: Path, out_dir: Path) -> bool:
    source = Path(root) / "skills" / "vendor" / "gsap-lib" / "gsap.min.js"
    if not source.is_file():
        return False
    referenced = False
    for path in out_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".html", ".js"}:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if "vendor/gsap.min.js" in text or "gsap.min.js" in text:
                referenced = True
                break
    if not referenced:
        return False
    target = out_dir / "vendor" / "gsap.min.js"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return True


def _a11y_warnings(html: str) -> list[str]:
    warnings: list[str] = []
    lowered = html.lower()
    if "<html" in lowered and "lang=" not in lowered:
        warnings.append("index.html is missing a lang attribute.")
    if 'name="viewport"' not in lowered and "name='viewport'" not in lowered:
        warnings.append("index.html is missing a viewport meta tag.")
    if "<title" not in lowered:
        warnings.append("index.html is missing a <title>.")
    if "<img" in lowered and "alt=" not in lowered:
        warnings.append("index.html contains images without alt attributes.")
    return warnings


def _placeholder_site(theme: Theme, title: str, prompt: str, out_dir: Path) -> None:
    """A small but complete fallback site for themes without a packaged sample."""
    safe_title = re.sub(r"<[^>]+>", "", title).strip() or theme.name
    safe_prompt = re.sub(r"<[^>]+>", "", prompt).strip()
    accent = theme.accent or "#ff8a3d"
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_title}</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <a class="skip" href="#main">Skip to content</a>
  <header class="shell">
    <p class="eyebrow">{theme.category} / stitchcraft</p>
    <h1>{safe_title}</h1>
    <p class="lede">{safe_prompt}</p>
    <div class="cta">
      <a class="btn" href="#features">Explore the build</a>
      <button class="btn ghost" type="button" id="demo-action">Try the demo action</button>
    </div>
  </header>
  <main id="main" class="shell">
    <section id="features" class="grid">
      <article><h2>Module library</h2><p>This demo build is a placeholder for <strong>{theme.name}</strong>. Generate with your own AI key to compose a full site from the theme's modules.</p></article>
      <article><h2>Local or remote data</h2><p>The generated site reads <code>window.STITCHCRAFT_DB</code>. Local mode uses localStorage; remote mode calls your REST endpoint.</p></article>
      <article><h2>Skills included</h2><p>Generations receive Modern Web Guidance and official GSAP skills as prompt context.</p></article>
    </section>
  </main>
  <footer class="shell"><p>Built with Stitchcraft · {theme.name}</p></footer>
  <script src="data-config.js"></script>
  <script src="app.js"></script>
</body>
</html>
"""
    css = f""":root {{ color-scheme: dark; --accent: {accent}; --ink: #0e0c12; --paper: #f5efe6; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--ink); color: var(--paper); font: 16px/1.6 system-ui, sans-serif; }}
.shell {{ width: min(1080px, 92vw); margin: 0 auto; padding: 2.5rem 0; }}
.skip {{ position: absolute; left: -999px; }}
.skip:focus {{ left: 1rem; top: 1rem; background: var(--accent); color: #111; padding: .5rem .8rem; }}
.eyebrow {{ text-transform: uppercase; letter-spacing: .16em; color: var(--accent); font-size: .75rem; }}
h1 {{ font-size: clamp(2rem, 6vw, 4.2rem); line-height: 1.05; margin: .3rem 0 1rem; }}
.lede {{ max-width: 62ch; color: #cdc5ba; }}
.cta {{ display: flex; gap: .8rem; flex-wrap: wrap; margin-top: 1.6rem; }}
.btn {{ border: 1px solid var(--accent); background: var(--accent); color: #14100c; border-radius: 999px; padding: .7rem 1.2rem; font-weight: 600; text-decoration: none; cursor: pointer; }}
.btn.ghost {{ background: transparent; color: var(--paper); }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1rem; margin-top: 3rem; }}
article {{ border: 1px solid #ffffff1f; border-radius: 18px; padding: 1.2rem; background: #ffffff08; }}
h2 {{ margin-top: 0; font-size: 1.1rem; }}
code {{ color: var(--accent); }}
footer {{ border-top: 1px solid #ffffff1f; color: #8f877d; font-size: .85rem; }}
:focus-visible {{ outline: 3px solid var(--accent); outline-offset: 3px; }}
@media (prefers-reduced-motion: no-preference) {{
  .shell > * {{ animation: rise .6s ease both; }}
  @keyframes rise {{ from {{ opacity: 0; transform: translateY(14px); }} to {{ opacity: 1; transform: none; }} }}
}}
"""
    js = """const config = window.STITCHCRAFT_DB || { mode: "local" };
const button = document.getElementById("demo-action");
if (button) {
  button.addEventListener("click", () => {
    button.textContent = config.mode === "remote" ? "Remote endpoint configured" : "Saved locally";
    button.disabled = true;
  });
}
"""
    (out_dir / "index.html").write_text(html, encoding="utf-8")
    (out_dir / "styles.css").write_text(css, encoding="utf-8")
    (out_dir / "app.js").write_text(js, encoding="utf-8")


def _build_messages(
    root: Path,
    theme: Theme,
    title: str,
    prompt: str,
    mode: str,
    remote: dict,
    skill_context: str,
    compact: bool = False,
) -> list[dict]:
    data_model = load_data_model(root, theme)
    has_gsap = (Path(root) / "skills" / "vendor" / "gsap-lib" / "gsap.min.js").is_file()
    config = _data_config(mode, remote)
    if compact:
        system = f"""You are Stitchcraft, an expert product designer and front-end engineer.
Return a COMPLETE static website as a SINGLE self-contained HTML file.
You output code, not prose.

OUTPUT CONTRACT — return ONLY one JSON object, no markdown fences:
{{"files":[{{"path":"index.html","content":"..."}}],"summary":"one sentence describing the site"}}

HARD RULES
1. Exactly ONE file: index.html. Put all CSS in an inline <style> in <head> and all JavaScript in one inline <script> at the end of <body>. Do not return styles.css or app.js.
2. Keep the whole file under ~1000 lines and the JSON content valid (escape newlines as \\n inside the content string). Prioritise a complete, working page over extras.
3. Data layer: include <script src="data-config.js"></script> before your inline script, and read window.STITCHCRAFT_DB = {json.dumps(config, ensure_ascii=False)}.
   - local mode: persist in localStorage under keys prefixed "stitchcraft:"; seed realistic demo records on first load.
   - remote mode: fetch `${{url}}/rest/v1/${{tablePrefix}}_<table>` with headers apikey and Authorization: Bearer <anonKey>; handle failures with an inline message.
   - Never invent credentials; never write secrets into the site.
4. Fully offline: no external URLs, CDNs, web fonts or remote images. Use inline SVG, CSS gradients and emoji placeholders.
5. Accessibility: semantic landmarks, skip link, labelled controls, visible focus, prefers-reduced-motion.
6. Responsive at 1440px and 390px; no horizontal scroll.
7. Motion: CSS transitions/keyframes only (do not load GSAP in compact mode).
8. Seed realistic demo data so the page looks alive on first open.
9. Follow the theme skill and apply the bundled skills as guidance.
"""
    else:
        gsap_rule = (
            "GSAP is vendored at ./vendor/gsap.min.js and already copied into the site. "
            "You may use window.gsap for entrance/scroll motion; animate transform/opacity only; "
            "always guard with `if (window.gsap)` and respect prefers-reduced-motion."
            if has_gsap
            else "GSAP is not available: use CSS transitions/keyframes only."
        )
        system = f"""You are Stitchcraft, an expert product designer and front-end engineer.
You assemble a complete, production-quality static website from a theme module
library, a user brief and bundled expert skills. You output code, not prose.

OUTPUT CONTRACT — return ONLY one JSON object, no markdown fences:
{{"files":[{{"path":"index.html","content":"..."}},{{"path":"styles.css","content":"..."}},{{"path":"app.js","content":"..."}}],"summary":"one sentence describing the site"}}

HARD RULES
1. Required files: index.html, styles.css, app.js. Optional extra .html/.css/.js/.json/.svg files with relative paths only.
2. Fully static and offline: no external URLs, CDNs, web fonts or remote images. Use inline SVG, CSS gradients and emoji placeholders.
3. Data layer: link <script src="data-config.js"></script> BEFORE app.js. Read window.STITCHCRAFT_DB = {json.dumps(config, ensure_ascii=False)}.
   - local mode: persist in localStorage under keys prefixed "stitchcraft:"; seed realistic demo records on first load.
   - remote mode: fetch `${{url}}/rest/v1/${{tablePrefix}}_<table>` with headers apikey and Authorization: Bearer <anonKey>; GET ?select=*, POST with Prefer: return=representation, PATCH ?id=eq.<id>, DELETE ?id=eq.<id>. On failure show an inline error and keep cached data.
   - Never invent credentials; never write secrets into the site.
4. Accessibility: WCAG 2.2 AA, semantic landmarks, skip link, visible focus, labelled controls, contrast, prefers-reduced-motion.
5. Responsive: excellent at 1440px and 390px; no horizontal scroll.
6. Motion: {gsap_rule}
7. Security: no innerHTML with user content; use textContent/DOM APIs; no eval; escape strings.
8. Seed realistic demo data so the page looks alive on first open.
9. Every file must be complete and runnable; app.js under ~500 lines.
10. Follow the theme skill and apply the bundled skills as guidance.
"""
    user_parts = [
        f"# Site title\n{title}",
        f"# User brief\n{prompt}",
        f"# Theme\n{theme.name} ({theme.id}) — {theme.summary}\nCategory: {theme.category}\nAccent: {theme.accent}",
        "# Theme skill (follow it)\n" + theme_skill_text(root, theme),
    ]
    if data_model:
        user_parts.append("# Data model\n```json\n" + json.dumps(data_model, indent=2)[:8000] + "\n```")
    if skill_context:
        user_parts.append("# Bundled skills to apply\n" + skill_context)
    user_parts.append("# Database configuration\n```js\nwindow.STITCHCRAFT_DB = " + json.dumps(config, indent=2) + ";\n```")
    if compact:
        user_parts.append(
            "# Output reminder\nReturn ONE JSON object with a single index.html file "
            "(inline CSS and JS). No markdown, no prose, valid JSON only."
        )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": "\n\n".join(user_parts)},
    ]


def generate_site(
    root: Path,
    config: AppConfig,
    request: GenerationRequest,
    out_dir: Path,
    on_progress=None,
    sleep=time.sleep,
) -> GenerationResult:
    started = time.perf_counter()
    root = Path(root)
    out_dir = Path(out_dir)
    theme = get_theme(root, request.theme_id)
    if theme is None:
        raise GenerationError(f"Unknown theme '{request.theme_id}'.")
    prompt = " ".join((request.prompt or "").split())
    if len(prompt) < 8:
        raise GenerationError("Describe the site in at least a few words.")
    engine = request.engine if request.engine in {"mock", "ai"} else "mock"
    database = dict(request.database or {})
    mode = str(database.get("mode", "local")).lower()
    mode = mode if mode in {"local", "remote"} else "local"
    remote = dict(database.get("remote") or {})
    if mode == "remote" and not str(remote.get("url", "")).strip():
        raise GenerationError("Remote database mode needs a database URL.")
    title = (request.title or "").strip() or theme.name
    warnings: list[str] = []

    out_dir.mkdir(parents=True, exist_ok=True)
    _clean_dir(out_dir)

    def active(index: int, message: str) -> None:
        _emit(on_progress, index, "active", message)

    def done(index: int, message: str | None = None) -> None:
        _emit(on_progress, index, "done", message)

    active(0, f"Sealing the brief for '{title}'")
    done(0)

    active(1, f"Planning structure from {theme.name}")
    done(1)
    active(2, f"Choosing design tokens ({theme.accent})")
    done(2)
    active(3, f"Preparing data layer ({mode} mode)")
    done(3)
    active(4, "Mounting hero and layout modules")
    done(4)
    active(5, "Adding components")
    done(5)

    summary: str
    if engine == "mock":
        sample = sample_dir(root, theme)
        active(6, "Demo engine: adding packaged motion and sample data")
        sleep(0.12)
        if sample is not None:
            shutil.copytree(sample, out_dir, dirs_exist_ok=True)
            summary = f"Demo build of {theme.name} from the packaged sample."
        else:
            _placeholder_site(theme, title, prompt, out_dir)
            warnings.append(
                f"Theme '{theme.id}' has no packaged sample; demo mode wrote a placeholder build."
            )
            summary = f"Placeholder demo build of {theme.name}."
        _write_data_config(out_dir, _data_config(mode, remote))
        _ensure_data_config_link(out_dir, warnings)
        _copy_gsap_if_needed(root, out_dir)
        done(6, "Demo modules mounted")
        active(7, "Checking accessible defaults")
        html = ""
        index_path = out_dir / "index.html"
        if index_path.is_file():
            html = index_path.read_text(encoding="utf-8", errors="replace")
        warnings.extend(_a11y_warnings(html))
        done(7, "Accessibility defaults applied" if not warnings else "Accessibility check finished with notes")
        active(8, "Packaging the site")
        files = _list_files(out_dir)
        done(8, f"Packaged {len(files)} files")
        return GenerationResult(
            theme_id=theme.id,
            title=title,
            engine=engine,
            out_dir=out_dir,
            files=files,
            summary=summary,
            warnings=warnings,
            duration_ms=int((time.perf_counter() - started) * 1000),
        )

    # ---- AI engine -------------------------------------------------------
    skill_ids = request.skills or list(theme.skills)
    registry = {skill.id: skill for skill in load_registry(root)}
    resolved = [skill_id for skill_id in skill_ids if skill_id in registry and registry[skill_id].enabled]
    missing = [skill_id for skill_id in skill_ids if skill_id not in registry]
    if missing:
        warnings.append("Unknown skills ignored: " + ", ".join(sorted(missing)))
    provider_preset = PRESETS.get(config.ai.provider, {})
    compact_mode = bool(provider_preset.get("compact", False)) or provider_preset.get("kind") == "free-keyless"
    compact_max_tokens = 4096
    skill_context = build_skill_context(root, resolved, budget_chars=12000 if compact_mode else 26000)
    if provider_requires_key(config.ai.provider) and not config.ai.api_key:
        raise GenerationError(
            "This provider needs an API key. Add one in Settings → AI API, pick a free provider "
            "(Pollinations needs no key), or switch to demo mode."
        )

    def _request(messages_to_use: list[dict], max_tokens: int) -> dict:
        request_config = ai_client.AIConfig(
            provider=config.ai.provider,
            base_url=config.ai.base_url,
            model=config.ai.model,
            api_key=config.ai.api_key,
            temperature=config.ai.temperature,
            max_tokens=max_tokens,
        )
        text = ai_client.chat(request_config, messages_to_use, json_mode=True)
        parsed = ai_client.extract_json(text)
        plan = parsed.get("files")
        if not isinstance(plan, list) or not plan:
            raise ai_client.AIError("The AI response did not contain any files.")
        return parsed

    active(6, f"Assembling skills and calling {config.ai.provider}/{config.ai.model}")
    _emit(on_progress, 6, "active", f"Skills injected: {', '.join(resolved) or 'none'}")
    is_keyless = provider_preset.get("kind") == "free-keyless"
    if compact_mode:
        _emit(on_progress, 6, "active", "Free provider: generating a compact single-file site")
        minimal_context = build_skill_context(root, resolved, budget_chars=4000)
        compact_retry_messages = _build_messages(
            root, theme, title, prompt, mode, remote, minimal_context, compact=True
        )
        attempts: list[tuple[list[dict], int]] = [
            (_build_messages(root, theme, title, prompt, mode, remote, skill_context, compact=True), compact_max_tokens)
        ]
        if not is_keyless:
            attempts.append((compact_retry_messages, compact_max_tokens))
    else:
        attempts = [
            (_build_messages(root, theme, title, prompt, mode, remote, skill_context), 0),
            (_build_messages(root, theme, title, prompt, mode, remote, skill_context, compact=True), compact_max_tokens),
        ]
        compact_retry_messages = attempts[-1][0]
    payload: dict | None = None
    last_error: Exception | None = None
    for attempt, (messages_to_use, max_tokens) in enumerate(attempts, start=1):
        try:
            if attempt > 1:
                _emit(on_progress, 6, "active", "Retrying the AI with a compact single-file prompt")
                warnings.append("The AI needed a compact single-file retry.")
            payload = _request(messages_to_use, max_tokens)
            break
        except (ai_client.AIError, GenerationError) as exc:  # noqa: PERF203 - max two attempts
            last_error = exc
    if payload is None and is_keyless:
        _emit(
            on_progress,
            6,
            "active",
            "Free endpoint is rate-limited or returned partial output; waiting 40s before one retry",
        )
        warnings.append("The free endpoint needed a rate-limit retry (40s wait).")
        sleep(40)
        try:
            payload = _request(compact_retry_messages, compact_max_tokens)
        except (ai_client.AIError, GenerationError) as exc:  # noqa: PERF203
            last_error = exc
    if payload is None:
        detail = str(last_error)[:200]
        hint = ""
        lowered = detail.lower()
        if "402" in detail or "rate" in lowered or "limit" in lowered or "quota" in lowered:
            hint = (
                " This free endpoint is rate-limited. Wait about a minute, then retry — or pick "
                "智谱 GLM-4-Flash (permanently free, China-friendly key), GitHub Models (free with your "
                "GitHub PAT), or use demo mode."
            )
        raise GenerationError(
            "The AI returned an incomplete or invalid response. Try again, pick another free "
            "provider, switch to demo mode, or add your own API key. "
            f"Details: {detail}{hint}"
        )
    file_plan = payload.get("files")
    if not isinstance(file_plan, list) or not file_plan:
        raise GenerationError("The AI response did not contain any files.")
    summary = str(payload.get("summary") or "").strip() or f"{theme.name} generated from your brief."
    done(6, f"AI returned {len(file_plan)} files")

    index_html = ""
    for item in file_plan:
        if isinstance(item, dict) and str(item.get("path", "")).strip() == "index.html":
            index_html = str(item.get("content", ""))
            break
    if not index_html:
        raise GenerationError("The AI response is missing index.html.")
    active(7, "Auditing generated markup for accessibility")
    warnings.extend(_a11y_warnings(index_html))
    done(7, "Accessibility audit finished")

    active(8, "Writing files and packaging")
    written = _write_file_plan(out_dir, file_plan)
    _write_data_config(out_dir, _data_config(mode, remote))
    _ensure_data_config_link(out_dir, warnings)
    _copy_gsap_if_needed(root, out_dir)
    files = _list_files(out_dir)
    done(8, f"Packaged {len(files)} files ({len(written)} from the AI)")

    return GenerationResult(
        theme_id=theme.id,
        title=title,
        engine=engine,
        out_dir=out_dir,
        files=files,
        summary=summary,
        warnings=warnings,
        duration_ms=int((time.perf_counter() - started) * 1000),
    )
