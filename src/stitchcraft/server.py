"""Local HTTP API and static server for the Stitchcraft desktop studio.

Everything is standard library: a ThreadingHTTPServer bound to 127.0.0.1 serves
the UI, the JSON API, generated-site previews, demo theme sites and ZIP exports.
Generation runs in a background thread; progress is polled through /api/jobs.
"""

from __future__ import annotations

import io
import json
import threading
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from . import __version__, ai_client, generator, libraries, settings, skills, storage, themes
from .generator import GenerationError, GenerationRequest
from .settings import AppConfig
from .storage import ProjectStore

MAX_BODY_BYTES = 2 * 1024 * 1024
MAX_JOBS = 50

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
            "error": self.error,
            "theme_id": self.theme_id,
            "title": self.title,
            "engine": self.engine,
        }


class StudioContext:
    """Shared state for the server: config, project store and jobs."""

    def __init__(self, root: Path, config: AppConfig | None = None, store: ProjectStore | None = None) -> None:
        self.root = Path(root).resolve()
        self.config = config if config is not None else settings.load_config()
        self.store = store if store is not None else ProjectStore(settings.app_dir())
        self.jobs: dict[str, Job] = {}
        self.lock = threading.Lock()

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
            )
            self.store.update(
                project["id"],
                title=result.title,
                summary=result.summary,
                files=len(result.files),
            )
            with self.lock:
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
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(
        self,
        status: int,
        body: bytes,
        content_type: str,
        download_name: str | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if download_name:
            self.send_header("Content-Disposition", f'attachment; filename="{download_name}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", "0") or "0")
        except ValueError as exc:
            raise ValueError("invalid Content-Length") from exc
        if length > MAX_BODY_BYTES:
            raise ValueError("request body is too large")
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("request body must be JSON") from exc
        if not isinstance(data, dict):
            raise ValueError("request body must be a JSON object")
        return data

    # -- HTTP verbs ----------------------------------------------------------
    def do_OPTIONS(self) -> None:  # noqa: N802
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
            if path.startswith("/api/"):
                self._api(method, path)
            else:
                self._static(path)
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
        self._send_bytes(200, target.read_bytes(), content_type)

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
        self._send_bytes(200, target.read_bytes(), content_type)

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
                site_dir = context.store.site_dir(parts[2])
                if site_dir is None:
                    return self._send_json(404, {"ok": False, "error": "project not found"})
                return self._serve_tree(site_dir, parts[3:])
            if resource == "demo" and len(parts) >= 3:
                theme = themes.get_theme(context.root, parts[2])
                if theme is None or theme.sample_path is None:
                    return self._send_json(404, {"ok": False, "error": "no demo sample for this theme"})
                return self._serve_tree(theme.sample_path, parts[3:])
            if resource == "export" and len(parts) == 3:
                return self._export(parts[2])
            return self._send_json(404, {"ok": False, "error": "unknown endpoint"})

        if method == "POST":
            try:
                body = self._read_json()
            except ValueError as exc:
                return self._send_json(400, {"ok": False, "error": str(exc)})
            if resource == "settings":
                return self._save_settings(body)
            if resource == "ai" and len(parts) == 3 and parts[2] == "test":
                return self._test_ai(body)
            if resource == "db" and len(parts) == 3 and parts[2] == "test":
                return self._test_db(body)
            if resource == "generate":
                return self._generate(body)
            return self._send_json(404, {"ok": False, "error": "unknown endpoint"})

        if method == "DELETE":
            if resource == "projects" and len(parts) == 3:
                deleted = context.store.delete(parts[2])
                return self._send_json(200 if deleted else 404, {"ok": deleted})
            return self._send_json(404, {"ok": False, "error": "unknown endpoint"})

        return self._send_json(405, {"ok": False, "error": "method not allowed"})

    def _job_status(self, job_id: str) -> None:
        job = self.context.jobs.get(job_id)
        if job is None:
            return self._send_json(404, {"ok": False, "error": "job not found"})
        with self.context.lock:
            return self._send_json(200, job.public_dict())
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
                if file_path.is_file():
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
) -> tuple[ThreadingHTTPServer, StudioContext]:
    context = StudioContext(root or _find_repo_root(), config=config, store=store)
    handler = type("BoundStudioHandler", (StudioHandler,), {"context": context})
    httpd = ThreadingHTTPServer((host, port), handler)
    httpd.daemon_threads = True
    return httpd, context
