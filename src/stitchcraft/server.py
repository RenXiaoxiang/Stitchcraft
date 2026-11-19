"""Local HTTP API and static server for the Stitchcraft desktop studio.

Everything is standard library: a ThreadingHTTPServer bound to 127.0.0.1 serves
the UI, the JSON API, generated-site previews, demo theme sites and ZIP exports.
Generation runs in a background thread; progress is polled through /api/jobs.
"""

from __future__ import annotations

import io
import json
import re
import threading
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from . import __version__, ai_client, browser, generator, libraries, settings, skills, storage, themes
from .generator import GenerationError, GenerationRequest
from .settings import AppConfig
from .storage import ProjectStore

MAX_BODY_BYTES = 2 * 1024 * 1024
MAX_JOBS = 50
ALLOWED_HOSTNAMES = {"127.0.0.1", "localhost", "::1"}

STUDIO_CSP = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "font-src 'self'; "
    "connect-src 'self'; "
    "frame-src http://localhost:* http://127.0.0.1:*; "
    "object-src 'none'; base-uri 'none'; form-action 'self'"
)
PREVIEW_CSP = (
    "default-src 'self' data: blob:; "
    "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob: https: http:; "
    "font-src 'self' data:; "
    "connect-src 'self' https: http:; "
    "media-src 'self' data: blob:; "
    "frame-src 'self' https:; "
    "object-src 'none'; base-uri 'self'; "
    "form-action 'self' https: http:"
)


class RequestError(Exception):
    """A request rejected before reaching an API handler."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status


CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".ico": "image/x-icon",
    ".txt": "text/plain; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
    ".woff2": "font/woff2",
    ".xml": "application/xml; charset=utf-8",
    ".webmanifest": "application/manifest+json",
}

EDGE_CANDIDATES = (
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
)

__all__ = ["Job", "StudioContext", "StudioHandler", "make_server"]


def _json_bytes(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in (here.parent, *here.parents):
        if (parent / "pipeline" / "pipeline.toml").is_file():
            return parent
    return here.parents[2]


def edge_available() -> bool:
    return any(path.is_file() for path in EDGE_CANDIDATES)


class Job:
    """One generation task tracked by the server."""

    def __init__(self, request: GenerationRequest, theme_id: str, title: str, engine: str) -> None:
        self.id = uuid.uuid4().hex[:10]
        self.request = request
        self.theme_id = theme_id
        self.title = title
        self.engine = engine
        self.database_mode = str((request.database or {}).get("mode", "local"))
        self.status = "queued"
        self.stage = 0
        self.stage_name = generator.stage_names()[0]
        self.progress = 0
        self.stages = [{"name": name, "status": "pending"} for name in generator.stage_names()]
        self.logs: list[dict] = []
        self.project_id: str | None = None
        self.browser: dict | None = None
        self.error: str | None = None

    def public_dict(self) -> dict:
        return {
            "id": self.id,
            "status": self.status,
            "stage": self.stage,
            "stage_name": self.stage_name,
            "progress": self.progress,
            "stages": list(self.stages),
            "logs": list(self.logs),
            "project_id": self.project_id,
            "browser": self.browser,
            "error": self.error,
            "theme_id": self.theme_id,
            "title": self.title,
            "engine": self.engine,
        }


class StudioContext:
    """Shared state for the server: config, project store and jobs."""

    def __init__(
        self,
        root: Path,
        config: AppConfig | None = None,
        store: ProjectStore | None = None,
        browser_manager: browser.BrowserManager | None = None,
    ) -> None:
        self.root = Path(root).resolve()
        self.config = config if config is not None else settings.load_config()
        self.store = store if store is not None else ProjectStore(settings.app_dir())
        self.browser = browser_manager or browser.BrowserManager()
        self.browser_install: dict | None = None
        self.port: int | None = None
        self.jobs: dict[str, Job] = {}
        self.lock = threading.Lock()

    # -- browser helpers -----------------------------------------------------
    def browser_status(self) -> dict:
        payload = self.browser.status()
        payload["settings"] = self.config.browser.public_dict()
        payload["install"] = dict(self.browser_install) if self.browser_install else None
        payload["preview_base"] = f"http://127.0.0.1:{self.port}" if self.port else None
        return payload

    def start_browser_install(self) -> dict:
        with self.lock:
            if self.browser.status()["installed"]:
                return {"started": False, "installed": True, "status": self.browser_status()}
            current = self.browser_install or {}
            if current.get("state") in {"downloading", "extracting", "starting"}:
                return {"started": False, "installed": False, "install": dict(current)}
            self.browser_install = {
                "state": "starting",
                "percent": 0,
                "downloaded": 0,
                "total": 0,
                "error": None,
            }
        threading.Thread(target=self._install_browser_worker, daemon=True).start()
        return {"started": True, "installed": False}

    def _install_browser_worker(self) -> None:
        def progress(done: int, total: int) -> None:
            with self.lock:
                self.browser_install = {
                    "state": "downloading",
                    "percent": int((done / total) * 100) if total else 0,
                    "downloaded": done,
                    "total": total,
                    "error": None,
                }

        try:
            with self.lock:
                self.browser_install = {"state": "downloading", "percent": 0, "downloaded": 0, "total": 0, "error": None}
            installed = self.browser.install(progress=progress)
            with self.lock:
                self.browser_install = {
                    "state": "installed",
                    "percent": 100,
                    "downloaded": installed.get("download_bytes") or 0,
                    "total": installed.get("download_bytes") or 0,
                    "error": None,
                }
        except Exception as exc:  # noqa: BLE001 - surfaced through the API
            with self.lock:
                self.browser_install = {"state": "error", "percent": 0, "downloaded": 0, "total": 0, "error": str(exc)}

    def run_browser_check(self, project_id: str) -> dict:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", project_id or ""):
            raise ValueError("invalid project id")
        if self.store.site_dir(project_id) is None:
            raise ValueError("project not found")
        if not self.port:
            raise ValueError("the studio is not listening")
        url = f"http://localhost:{self.port}/api/preview/{project_id}/"
        report = self.browser.check(
            url,
            self.browser.checks_dir / project_id,
            allow_private_network=self.config.browser.allow_private_network,
        )
        report["project_id"] = project_id
        return report

    # -- job helpers ---------------------------------------------------------
    def _log(self, job: Job, message: str, level: str = "info", stage: int | None = None) -> None:
        job.logs.append(
            {
                "ts": storage.utc_now(),
                "level": level,
                "message": message,
                "stage": stage if stage is not None else job.stage,
            }
        )
        if len(job.logs) > 200:
            job.logs = job.logs[-200:]

    def update_job(
        self,
        job: Job,
        index: int | None = None,
        status: str | None = None,
        message: str | None = None,
        level: str = "info",
    ) -> None:
        with self.lock:
            if index is not None and status == "active":
                job.status = "running"
                job.stage = max(0, min(index, len(job.stages) - 1))
                job.stage_name = job.stages[job.stage]["name"]
                for position, stage in enumerate(job.stages):
                    if position < job.stage and stage["status"] not in {"done", "error"}:
                        stage["status"] = "done"
                    elif position == job.stage:
                        stage["status"] = "active"
                job.progress = int(((job.stage + 0.5) / len(job.stages)) * 100)
            elif index is not None and status == "done":
                if 0 <= index < len(job.stages):
                    job.stages[index]["status"] = "done"
                job.progress = max(job.progress, int(((index + 1) / len(job.stages)) * 100))
            if message:
                self._log(job, message, level, index)

    def _fail(self, job: Job, message: str) -> None:
        with self.lock:
            job.status = "error"
            job.error = message
            for stage in job.stages:
                if stage["status"] == "active":
                    stage["status"] = "error"
            self._log(job, message, "error")

    def run_generation(self, job: Job) -> None:
        self.update_job(job, message=f"Starting {job.engine} generation for {job.theme_id}...")
        site_dir: Path | None = None
        project: dict | None = None
        try:
            project = self.store.create(
                theme_id=job.theme_id,
                title=job.title,
                prompt=job.request.prompt,
                engine=job.engine,
                database_mode=job.database_mode,
            )
            with self.lock:
                job.project_id = project["id"]
            site_dir = Path(project["site_dir"])

            def on_progress(index: int, status: str, message: str | None = None, level: str = "info") -> None:
                self.update_job(job, index, status, message, level)

            result = generator.generate_site(
                self.root,
                self.config,
                job.request,
                site_dir,
                on_progress=on_progress,
                force=True,  # the project directory is app-managed
            )
            self.store.update(
                project["id"],
                title=result.title,
                summary=result.summary,
                files=len(result.files),
            )
            browser_report: dict | None = None
            if self.config.browser.auto_check:
                try:
                    if self.browser.status()["installed"]:
                        browser_report = self.run_browser_check(project["id"])
                        level = "success" if browser_report.get("ok") else "info"
                        self._log(
                            job,
                            "AI browser check: "
                            + (browser_report.get("title") or "untitled page")
                            + f" ({len(browser_report.get('warnings') or [])} note(s))",
                            level,
                        )
                    else:
                        self._log(
                            job,
                            "AI browser check skipped: Obscura is not installed (optional).",
                            "info",
                        )
                except Exception as exc:  # noqa: BLE001 - never fail a generation for an optional check
                    self._log(job, f"AI browser check skipped: {exc}", "warn")
            with self.lock:
                job.browser = browser_report
                job.status = "done"
                job.progress = 100
                job.stage = len(job.stages) - 1
                job.stage_name = job.stages[-1]["name"]
                for stage in job.stages:
                    stage["status"] = "done"
                self._log(
                    job,
                    f"Done: {result.summary} ({len(result.files)} files in {result.duration_ms} ms)",
                    "success",
                    len(job.stages) - 1,
                )
        except GenerationError as exc:
            self._fail(job, str(exc))
            if project is not None:
                self.store.delete(project["id"])
        except Exception as exc:  # noqa: BLE001 - surface unexpected failures to the UI
            self._fail(job, f"Unexpected error: {exc}")
            if project is not None:
                self.store.delete(project["id"])


class StudioHandler(BaseHTTPRequestHandler):
    """Routes for the studio API, the UI and generated-site previews."""

    context: StudioContext  # injected by make_server
    server_version = "StitchcraftStudio/" + __version__

    def log_message(self, format: str, *args: Any) -> None:  # keep the console quiet
        return

    # -- response helpers ----------------------------------------------------
    def _send_json(self, status: int, payload: object) -> None:
        body = _json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(
        self,
        status: int,
        body: bytes,
        content_type: str,
        download_name: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if download_name:
            self.send_header("Content-Disposition", f'attachment; filename="{download_name}"')
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    # -- request validation -------------------------------------------------
    def _hostname(self) -> str:
        raw = (self.headers.get("Host") or "").strip().lower()
        if not raw:
            return ""
        if raw.startswith("["):
            end = raw.find("]")
            return raw[1:end] if end > 0 else raw
        return raw.split(":", 1)[0]

    def _validate_request(self, method: str) -> None:
        """Reject DNS-rebinding hosts, cross-origin writes and form posts."""
        if self._hostname() not in ALLOWED_HOSTNAMES:
            raise RequestError(403, "unexpected Host header (DNS rebinding protection)")
        if method not in {"POST", "DELETE"}:
            return
        origin = (self.headers.get("Origin") or "").strip().rstrip("/")
        if origin:
            port = int(self.server.server_address[1])
            allowed = {
                f"http://127.0.0.1:{port}",
                f"http://localhost:{port}",
                f"http://[::1]:{port}",
            }
            if origin.lower() not in allowed:
                raise RequestError(403, "cross-origin request rejected")
        if method == "POST":
            content_type = (self.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
            if content_type != "application/json":
                raise RequestError(415, "Content-Type must be application/json")

    def _read_json(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", "0") or "0")
        except ValueError as exc:
            raise RequestError(400, "invalid Content-Length") from exc
        if length > MAX_BODY_BYTES:
            raise RequestError(413, "request body is too large")
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RequestError(400, "request body must be JSON") from exc
        if not isinstance(data, dict):
            raise RequestError(400, "request body must be a JSON object")
        return data

    # -- HTTP verbs ----------------------------------------------------------
    def do_OPTIONS(self) -> None:  # noqa: N802
        try:
            self._validate_request("OPTIONS")
        except RequestError as exc:
            return self._send_json(exc.status, {"ok": False, "error": str(exc)})
        self.send_response(204)
        self.send_header("Allow", "GET, POST, DELETE, OPTIONS")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        self._route("GET")

    def do_POST(self) -> None:  # noqa: N802
        self._route("POST")

    def do_DELETE(self) -> None:  # noqa: N802
        self._route("DELETE")

    def _route(self, method: str) -> None:
        parsed = urllib.parse.urlsplit(self.path)
        path = urllib.parse.unquote(parsed.path)
        try:
            self._validate_request(method)
            if path.startswith("/api/"):
                self._api(method, path)
            else:
                self._static(path)
        except RequestError as exc:
            self._send_json(exc.status, {"ok": False, "error": str(exc)})
        except Exception as exc:  # noqa: BLE001 - never kill the connection thread
            self._send_json(500, {"ok": False, "error": f"internal server error: {exc}"})

    # -- static files --------------------------------------------------------
    def _static(self, path: str) -> None:
        web_root = _find_repo_root() / "app" / "web"
        relative = path.lstrip("/") or "index.html"
        target = (web_root / relative).resolve()
        if not target.is_relative_to(web_root.resolve()) or not target.is_file():
            self._send_json(404, {"ok": False, "error": "not found"})
            return
        content_type = CONTENT_TYPES.get(target.suffix.lower(), "application/octet-stream")
        headers = {"Content-Security-Policy": STUDIO_CSP, "X-Frame-Options": "DENY"} if target.suffix.lower() == ".html" else None
        self._send_bytes(200, target.read_bytes(), content_type, extra_headers=headers)

    def _serve_tree(self, base: Path, parts: list[str]) -> None:
        base = base.resolve()
        target = (base / Path(*parts)).resolve() if parts else base
        if not target.is_relative_to(base):
            self._send_json(403, {"ok": False, "error": "forbidden"})
            return
        if target.is_dir():
            target = target / "index.html"
        if not target.is_file():
            self._send_json(404, {"ok": False, "error": "file not found"})
            return
        content_type = CONTENT_TYPES.get(target.suffix.lower(), "application/octet-stream")
        self._send_bytes(200, target.read_bytes(), content_type, extra_headers={"Content-Security-Policy": PREVIEW_CSP})

    # -- API ----------------------------------------------------------------
    def _api(self, method: str, path: str) -> None:
        context = self.context
        parts = [part for part in path.split("/") if part]
        resource = parts[1] if len(parts) > 1 else ""

        if method == "GET":
            if resource == "status":
                return self._send_json(
                    200,
                    {
                        "version": __version__,
                        "demo_mode": context.config.ui.demo_mode,
                        "config_path": str(settings.config_path()),
                        "edge": edge_available(),
                        "root": str(context.root),
                        "preview_base": f"http://localhost:{self.server.server_address[1]}",
                    },
                )
            if resource == "settings":
                return self._send_json(200, context.config.public_dict())
            if resource == "themes":
                return self._send_json(
                    200,
                    {"themes": [theme.public_dict() for theme in themes.load_themes(context.root)]},
                )
            if resource == "skills":
                return self._send_json(
                    200,
                    {
                        "skills": [
                            {
                                "id": skill.id,
                                "name": skill.name,
                                "category": skill.category,
                                "source": skill.source,
                                "license": skill.license,
                                "summary": skill.summary,
                                "enabled": skill.enabled,
                                "stages": list(skill.stages),
                                "kind": skill.kind,
                            }
                            for skill in skills.load_registry(context.root)
                        ]
                    },
                )
            if resource == "libraries":
                return self._send_json(
                    200,
                    {
                        "libraries": [
                            library.public_dict()
                            for library in libraries.load_libraries(context.root)
                        ]
                    },
                )
            if resource == "browser":
                if len(parts) == 2:
                    return self._send_json(200, context.browser_status())
                if len(parts) == 4 and parts[2] == "check":
                    return self._browser_report(parts[3])
                if len(parts) == 4 and parts[2] == "screenshot":
                    return self._browser_screenshot(parts[3])
            if resource == "ai":
                if len(parts) == 3 and parts[2] == "providers":
                    return self._send_json(200, {"providers": settings.provider_catalog()})
                if len(parts) == 3 and parts[2] == "local":
                    return self._local_ai()
            if resource == "projects":
                return self._send_json(
                    200,
                    {"projects": [storage.project_public_dict(item) for item in context.store.list()]},
                )
            if resource == "jobs" and len(parts) == 3:
                return self._job_status(parts[2])
            if resource == "preview" and len(parts) >= 3:
                if self._hostname() != "localhost":
                    raise RequestError(403, "previews are served from http://localhost:<port> only")
                site_dir = context.store.site_dir(parts[2])
                if site_dir is None:
                    return self._send_json(404, {"ok": False, "error": "project not found"})
                return self._serve_tree(site_dir, parts[3:])
            if resource == "demo" and len(parts) >= 3:
                if self._hostname() != "localhost":
                    raise RequestError(403, "previews are served from http://localhost:<port> only")
                theme = themes.get_theme(context.root, parts[2])
                if theme is None or theme.sample_path is None:
                    return self._send_json(404, {"ok": False, "error": "no demo sample for this theme"})
                return self._serve_tree(theme.sample_path, parts[3:])
            if resource == "export" and len(parts) == 3:
                return self._export(parts[2])
            return self._send_json(404, {"ok": False, "error": "unknown endpoint"})

        if method == "POST":
            body = self._read_json()
            if resource == "settings":
                return self._save_settings(body)
            if resource == "ai" and len(parts) == 3 and parts[2] == "test":
                return self._test_ai(body)
            if resource == "db" and len(parts) == 3 and parts[2] == "test":
                return self._test_db(body)
            if resource == "generate":
                return self._generate(body)
            if resource == "browser":
                if len(parts) == 3 and parts[2] == "install":
                    result = context.start_browser_install()
                    return self._send_json(202 if result.get("started") else 200, {"ok": True, **result})
                if len(parts) == 3 and parts[2] == "check":
                    return self._browser_check(body)
            return self._send_json(404, {"ok": False, "error": "unknown endpoint"})

        if method == "DELETE":
            if resource == "projects" and len(parts) == 3:
                deleted = context.store.delete(parts[2])
                return self._send_json(200 if deleted else 404, {"ok": deleted})
            if resource == "browser" and len(parts) == 2:
                removed = context.browser.remove()
                with context.lock:
                    context.browser_install = None
                return self._send_json(200, {"ok": True, "removed": removed, "status": context.browser_status()})
            return self._send_json(404, {"ok": False, "error": "unknown endpoint"})

        return self._send_json(405, {"ok": False, "error": "method not allowed"})

    def _job_status(self, job_id: str) -> None:
        job = self.context.jobs.get(job_id)
        if job is None:
            return self._send_json(404, {"ok": False, "error": "job not found"})
        with self.context.lock:
            return self._send_json(200, job.public_dict())

    # -- browser helpers -----------------------------------------------------
    def _browser_report(self, project_id: str) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", project_id or ""):
            return self._send_json(404, {"ok": False, "error": "not found"})
        report_path = self.context.browser.checks_dir / project_id / "report.json"
        if not report_path.is_file():
            return self._send_json(404, {"ok": False, "error": "no browser check for this project"})
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return self._send_json(500, {"ok": False, "error": "could not read the browser report"})
        return self._send_json(200, report)

    def _browser_screenshot(self, project_id: str) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", project_id or ""):
            return self._send_json(404, {"ok": False, "error": "not found"})
        shot_path = self.context.browser.checks_dir / project_id / "screenshot.png"
        if not shot_path.is_file():
            return self._send_json(404, {"ok": False, "error": "no screenshot for this project"})
        return self._send_bytes(200, shot_path.read_bytes(), "image/png")

    def _browser_check(self, body: dict) -> None:
        project_id = str(body.get("project_id") or "").strip()
        if not project_id:
            return self._send_json(400, {"ok": False, "error": "project_id is required"})
        try:
            report = self.context.run_browser_check(project_id)
        except browser.BrowserError as exc:
            return self._send_json(409, {"ok": False, "error": str(exc)})
        except ValueError as exc:
            return self._send_json(400, {"ok": False, "error": str(exc)})
        return self._send_json(200, report)

    def _save_settings(self, body: dict) -> None:
        self.context.config.merge_patch(body)
        path = settings.save_config(self.context.config)
        return self._send_json(200, {"ok": True, "config_path": str(path), "settings": self.context.config.public_dict()})

    def _test_ai(self, body: dict) -> None:
        stored = self.context.config.ai
        config = ai_client.AIConfig(
            provider=str(body.get("provider") or stored.provider),
            base_url=str(body.get("base_url") or stored.base_url),
            model=str(body.get("model") or stored.model),
            api_key=str(body.get("api_key") or stored.api_key),
            temperature=float(body.get("temperature", stored.temperature) or stored.temperature),
        )
        return self._send_json(200, ai_client.test_connection(config))

    def _test_db(self, body: dict) -> None:
        stored = self.context.config.database.remote
        result = storage.test_remote_database(
            str(body.get("url") or stored.url),
            str(body.get("anon_key") or stored.anon_key),
            str(body.get("kind") or stored.kind),
        )
        return self._send_json(200, result)

    def _local_ai(self) -> None:
        """Probe a local Ollama server so the UI can auto-fill a model."""
        try:
            with urllib.request.urlopen("http://127.0.0.1:11434/v1/models", timeout=2.0) as response:
                data = json.loads(response.read().decode("utf-8", "replace"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
            return self._send_json(
                200,
                {
                    "ok": False,
                    "models": [],
                    "message": (
                        "Ollama was not detected on 127.0.0.1:11434. Install it from "
                        "https://ollama.com, run `ollama serve`, then `ollama pull llama3.1`."
                    ),
                },
            )
        models = [
            str(entry.get("id"))
            for entry in data.get("data", [])
            if isinstance(entry, dict) and entry.get("id")
        ]
        return self._send_json(
            200,
            {
                "ok": True,
                "models": models,
                "message": f"Ollama is running with {len(models)} model(s).",
            },
        )

    def _generate(self, body: dict) -> None:
        theme_id = str(body.get("theme_id", "")).strip()
        prompt = str(body.get("prompt", "")).strip()
        title = str(body.get("title", "")).strip()
        engine = str(body.get("engine", "mock")).strip() or "mock"
        engine = engine if engine in {"mock", "ai"} else "mock"
        database = body.get("database")
        if not isinstance(database, dict):
            database = {"mode": self.context.config.database.mode, "remote": {}}
        theme = themes.get_theme(self.context.root, theme_id)
        if theme is None:
            return self._send_json(400, {"ok": False, "error": f"unknown theme: {theme_id}"})
        if len(prompt) < 8:
            return self._send_json(400, {"ok": False, "error": "describe the site in at least a few words."})
        if engine == "ai":
            ai_settings = self.context.config.ai
            if not ai_settings.base_url:
                return self._send_json(400, {"ok": False, "error": "No AI base URL is configured."})
            if settings.provider_requires_key(ai_settings.provider) and not ai_settings.api_key:
                return self._send_json(
                    400,
                    {
                        "ok": False,
                        "error": (
                            "This provider needs an API key. Add one in Settings, choose a free "
                            "provider (Pollinations needs no key), or switch to demo mode."
                        ),
                    },
                )
        request = GenerationRequest(
            theme_id=theme_id,
            prompt=prompt,
            title=title or theme.name,
            engine=engine,
            database=database,
        )
        job = Job(request, theme_id=theme_id, title=request.title, engine=engine)
        with self.context.lock:
            self.context.jobs[job.id] = job
            if len(self.context.jobs) > MAX_JOBS:
                for stale_id in list(self.context.jobs)[: len(self.context.jobs) - MAX_JOBS]:
                    self.context.jobs.pop(stale_id, None)
        threading.Thread(target=self.context.run_generation, args=(job,), daemon=True).start()
        return self._send_json(202, {"ok": True, "job_id": job.id})

    def _export(self, project_id: str) -> None:
        site_dir = self.context.store.site_dir(project_id)
        if site_dir is None or not site_dir.is_dir():
            return self._send_json(404, {"ok": False, "error": "project not found"})
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for file_path in sorted(site_dir.rglob("*")):
                if file_path.is_file() and file_path.name != generator.SITE_MARKER:
                    archive.write(file_path, file_path.relative_to(site_dir).as_posix())
        self._send_bytes(
            200,
            buffer.getvalue(),
            "application/zip",
            download_name=f"stitchcraft-{project_id}.zip",
        )


def make_server(
    root: Path | None = None,
    port: int = 8765,
    config: AppConfig | None = None,
    store: ProjectStore | None = None,
    host: str = "127.0.0.1",
    browser_manager: browser.BrowserManager | None = None,
) -> tuple[ThreadingHTTPServer, StudioContext]:
    context = StudioContext(
        root or _find_repo_root(),
        config=config,
        store=store,
        browser_manager=browser_manager,
    )
    handler = type("BoundStudioHandler", (StudioHandler,), {"context": context})
    httpd = ThreadingHTTPServer((host, port), handler)
    httpd.daemon_threads = True
    context.port = int(httpd.server_address[1])
    return httpd, context
