"""Studio tests: settings, registries, generation engine and the HTTP API.

These run offline. Mock generation needs the themed sample sites, and the API
tests start a real ThreadingHTTPServer on an ephemeral port against a temporary
project store.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from stitchcraft import settings  # noqa: E402
from stitchcraft.generator import GenerationError, GenerationRequest, generate_site  # noqa: E402
from stitchcraft.server import make_server  # noqa: E402
from stitchcraft.settings import AppConfig  # noqa: E402
from stitchcraft.skills import verify_registry  # noqa: E402
from stitchcraft.storage import ProjectStore  # noqa: E402
from stitchcraft.themes import verify_themes  # noqa: E402


def _get_json(url: str, method: str = "GET", payload: dict | None = None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read()
        return response.status, (json.loads(body) if body else {})


def _status(url: str, method: str = "GET") -> int:
    request = urllib.request.Request(url, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response.read(2048)
            return response.status
    except urllib.error.HTTPError as exc:
        return int(exc.code)


class SettingsTests(unittest.TestCase):
    def test_roundtrip_masks_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            config = AppConfig()
            config.merge_patch(
                {
                    "ai": {"provider": "deepseek", "api_key": "sk-secret-12345678"},
                    "database": {
                        "mode": "remote",
                        "remote": {"url": "https://db.example.com", "anon_key": "anon-key-1234"},
                    },
                }
            )
            settings.save_config(config, path)
            loaded = settings.load_config(path)
            self.assertEqual(loaded.ai.provider, "deepseek")
            self.assertEqual(loaded.ai.api_key, "sk-secret-12345678")
            public = json.dumps(loaded.public_dict())
            self.assertTrue(loaded.public_dict()["ai"]["has_key"])
            self.assertNotIn("sk-secret-12345678", public)
            self.assertNotIn("anon-key-1234", public)

    def test_blank_key_does_not_erase_saved_key(self) -> None:
        config = AppConfig()
        config.merge_patch({"ai": {"api_key": "sk-keep-me-12345678"}})
        config.merge_patch({"ai": {"api_key": ""}})
        self.assertEqual(config.ai.api_key, "sk-keep-me-12345678")
        config.merge_patch({"ai": {"clear_api_key": True}})
        self.assertEqual(config.ai.api_key, "")


class RegistryTests(unittest.TestCase):
    def test_skill_registry_is_healthy(self) -> None:
        self.assertEqual(verify_registry(ROOT), [])

    def test_theme_registry_is_healthy(self) -> None:
        self.assertEqual(verify_themes(ROOT), [])


class GenerationTests(unittest.TestCase):
    def test_mock_generation_mounts_sample(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "site"
            result = generate_site(
                ROOT,
                AppConfig(),
                GenerationRequest(
                    theme_id="warehouse-ops",
                    prompt="A warehouse operations dashboard with inventory CRUD.",
                    engine="mock",
                ),
                out,
                sleep=lambda _seconds: None,
            )
            self.assertTrue((out / "index.html").is_file())
            self.assertTrue((out / "data-config.js").is_file())
            self.assertIn("index.html", result.files)
            self.assertGreater(len(result.files), 2)

    def test_mock_generation_remote_config_is_embedded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "site"
            generate_site(
                ROOT,
                AppConfig(),
                GenerationRequest(
                    theme_id="personal-space",
                    prompt="A personal space for notes and photographs.",
                    engine="mock",
                    database={
                        "mode": "remote",
                        "remote": {"kind": "supabase", "url": "https://demo.supabase.co", "anon_key": "public-anon-key", "table_prefix": "sc"},
                    },
                ),
                out,
                sleep=lambda _seconds: None,
            )
            config_text = (out / "data-config.js").read_text(encoding="utf-8")
            self.assertIn("https://demo.supabase.co", config_text)
            self.assertIn('"mode": "remote"', config_text)

    def test_remote_mode_requires_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(GenerationError):
                generate_site(
                    ROOT,
                    AppConfig(),
                    GenerationRequest(
                        theme_id="warehouse-ops",
                        prompt="A warehouse operations dashboard.",
                        engine="mock",
                        database={"mode": "remote", "remote": {}},
                    ),
                    Path(tmp) / "site",
                    sleep=lambda _seconds: None,
                )


class ServerApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls._old_home = os.environ.get("STITCHCRAFT_HOME")
        os.environ["STITCHCRAFT_HOME"] = cls.tmp.name
        cls.store = ProjectStore(Path(cls.tmp.name) / "data")
        cls.httpd, cls.context = make_server(ROOT, port=0, config=AppConfig(), store=cls.store)
        cls.port = int(cls.httpd.server_address[1])
        cls.base = f"http://127.0.0.1:{cls.port}"
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.httpd.shutdown()
        cls.httpd.server_close()
        if cls._old_home is None:
            os.environ.pop("STITCHCRAFT_HOME", None)
        else:
            os.environ["STITCHCRAFT_HOME"] = cls._old_home
        cls.tmp.cleanup()

    def test_status_themes_skills(self) -> None:
        status, payload = _get_json(self.base + "/api/status")
        self.assertEqual(status, 200)
        self.assertIn("version", payload)
        status, payload = _get_json(self.base + "/api/themes")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(payload["themes"]), 5)
        status, payload = _get_json(self.base + "/api/skills")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(payload["skills"]), 5)

    def test_settings_roundtrip(self) -> None:
        status, payload = _get_json(
            self.base + "/api/settings",
            "POST",
            {"ai": {"provider": "openai", "model": "gpt-4o-mini"}},
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])

    def test_generate_mock_preview_and_export(self) -> None:
        status, payload = _get_json(
            self.base + "/api/generate",
            "POST",
            {
                "theme_id": "warehouse-ops",
                "title": "Test warehouse",
                "prompt": "A warehouse operations dashboard with inventory CRUD.",
                "engine": "mock",
                "database": {"mode": "local", "remote": {}},
            },
        )
        self.assertEqual(status, 202, payload)
        job_id = payload["job_id"]
        job: dict = {}
        for _ in range(300):
            status, job = _get_json(self.base + f"/api/jobs/{job_id}")
            if job.get("status") in {"done", "error"}:
                break
            time.sleep(0.05)
        self.assertEqual(job.get("status"), "done", job.get("error"))
        project_id = job["project_id"]
        self.assertTrue(project_id)
        self.assertEqual(_status(self.base + f"/api/preview/{project_id}/"), 200)
        self.assertEqual(_status(self.base + f"/api/export/{project_id}"), 200)
        status, payload = _get_json(self.base + "/api/projects")
        self.assertIn(project_id, [item["id"] for item in payload["projects"]])
        self.assertEqual(_status(self.base + f"/api/projects/{project_id}", "DELETE"), 200)
        self.assertEqual(_status(self.base + f"/api/preview/{project_id}/"), 404)


if __name__ == "__main__":
    unittest.main()
