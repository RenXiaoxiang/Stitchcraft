"""Local project store and remote database helpers for the desktop studio.

The studio keeps its own project history in SQLite (standard library). The
remote database configured by the user is *not* used to store projects here;
it is embedded into generated sites whose data layer talks to it directly.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import threading
import urllib.error
import urllib.request
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

__all__ = [
    "ProjectStore",
    "test_remote_database",
    "utc_now",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ProjectStore:
    """SQLite-backed project history plus on-disk generated sites."""

    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.base_dir / "projects.sqlite3"
        self._lock = threading.Lock()
        self._init_db()

    @property
    def projects_root(self) -> Path:
        return self.base_dir / "projects"

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=15)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def _session(self) -> Iterator[sqlite3.Connection]:
        """A transaction whose connection is always closed (Windows file locks)."""
        connection = self._connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _init_db(self) -> None:
        with self._session() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    theme_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    engine TEXT NOT NULL,
                    database_mode TEXT NOT NULL,
                    summary TEXT NOT NULL DEFAULT '',
                    files INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    site_dir TEXT NOT NULL
                )
                """
            )

    def create(
        self,
        *,
        theme_id: str,
        title: str,
        prompt: str,
        engine: str,
        database_mode: str,
    ) -> dict:
        project_id = uuid.uuid4().hex[:12]
        site_dir = self.projects_root / project_id / "site"
        site_dir.mkdir(parents=True, exist_ok=True)
        now = utc_now()
        record = {
            "id": project_id,
            "theme_id": theme_id,
            "title": title or "Untitled site",
            "prompt": prompt,
            "engine": engine,
            "database_mode": database_mode,
            "summary": "",
            "files": 0,
            "created_at": now,
            "updated_at": now,
            "site_dir": str(site_dir),
        }
        with self._lock, self._session() as connection:
            connection.execute(
                """
                INSERT INTO projects (id, theme_id, title, prompt, engine, database_mode,
                                      summary, files, created_at, updated_at, site_dir)
                VALUES (:id, :theme_id, :title, :prompt, :engine, :database_mode,
                        :summary, :files, :created_at, :updated_at, :site_dir)
                """,
                record,
            )
        return record

    def update(self, project_id: str, **fields: object) -> None:
        if not fields:
            return
        allowed = {"title", "summary", "files", "theme_id", "engine", "database_mode"}
        assignments = {key: value for key, value in fields.items() if key in allowed}
        if not assignments:
            return
        assignments["updated_at"] = utc_now()
        columns = ", ".join(f"{key} = :{key}" for key in assignments)
        params = {**assignments, "id": project_id}
        with self._lock, self._session() as connection:
            connection.execute(f"UPDATE projects SET {columns} WHERE id = :id", params)

    def list(self, limit: int = 50) -> list[dict]:
        with self._session() as connection:
            rows = connection.execute(
                "SELECT * FROM projects ORDER BY created_at DESC LIMIT ?", (max(1, min(limit, 500)),)
            ).fetchall()
        return [dict(row) for row in rows]

    def get(self, project_id: str) -> dict | None:
        with self._session() as connection:
            row = connection.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        return dict(row) if row else None

    def site_dir(self, project_id: str) -> Path | None:
        project = self.get(project_id)
        if project is None:
            return None
        return Path(project["site_dir"])

    def delete(self, project_id: str) -> bool:
        project = self.get(project_id)
        if project is None:
            return False
        with self._lock, self._session() as connection:
            connection.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        shutil.rmtree(self.projects_root / project_id, ignore_errors=True)
        return True


def test_remote_database(url: str, anon_key: str = "", kind: str = "supabase") -> dict:
    """Check that a configured remote database endpoint is reachable."""
    if not url:
        return {"ok": False, "message": "Database URL is empty."}
    target = url.rstrip("/")
    if kind == "supabase":
        target = target + "/rest/v1/"
    headers = {"Accept": "application/json", "User-Agent": "stitchcraft-studio"}
    if anon_key:
        headers["apikey"] = anon_key
        headers["Authorization"] = f"Bearer {anon_key}"
    request = urllib.request.Request(target, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            response.read(2048)
            return {
                "ok": True,
                "message": f"Reached the database endpoint (HTTP {response.status}).",
            }
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            return {
                "ok": False,
                "message": f"Server reachable but the credentials were rejected (HTTP {exc.code}).",
            }
        if exc.code == 404:
            return {
                "ok": False,
                "message": "Server reachable, but the REST endpoint was not found (HTTP 404). Check the URL.",
            }
        return {"ok": True, "message": f"Reached the database endpoint (HTTP {exc.code})."}
    except (urllib.error.URLError, TimeoutError) as exc:
        reason = getattr(exc, "reason", exc)
        return {"ok": False, "message": f"Cannot reach the database URL: {reason}"}
    except OSError as exc:
        return {"ok": False, "message": f"Cannot reach the database URL: {exc}"}


def project_public_dict(project: dict) -> dict:
    """Convert a stored row into the JSON shape the UI expects."""
    return {
        "id": project.get("id"),
        "theme_id": project.get("theme_id"),
        "title": project.get("title"),
        "prompt": project.get("prompt"),
        "engine": project.get("engine"),
        "database_mode": project.get("database_mode"),
        "summary": project.get("summary"),
        "files": project.get("files"),
        "created_at": project.get("created_at"),
        "path": project.get("site_dir"),
    }


def dump_json(data: object) -> str:
    return json.dumps(data, ensure_ascii=False)
