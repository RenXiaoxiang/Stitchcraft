"""Studio tests: settings, registries, generation engine and the HTTP API.

These run offline. Mock generation needs the themed sample sites, and the API
tests start a real ThreadingHTTPServer on an ephemeral port against a temporary
project store.
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from stitchcraft import settings  # noqa: E402
from stitchcraft import browser  # noqa: E402
from stitchcraft import designs  # noqa: E402
from stitchcraft import generator  # noqa: E402
from stitchcraft.generator import GenerationError, GenerationRequest, generate_site  # noqa: E402
from stitchcraft.libraries import load_libraries, verify_libraries  # noqa: E402
from stitchcraft.server import make_server  # noqa: E402
from stitchcraft.server import Job, StudioContext  # noqa: E402
from stitchcraft.settings import AppConfig, SUPPORTED_LANGUAGES, provider_catalog, provider_requires_key  # noqa: E402
from stitchcraft.skills import build_skill_context, select_for_theme, verify_registry  # noqa: E402
from stitchcraft.storage import ProjectStore  # noqa: E402
from stitchcraft.themes import get_theme, load_themes, verify_themes  # noqa: E402


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


def _raw_request(url: str, method: str = "GET", data: bytes | None = None, headers: dict | None = None):
    request = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as exc:
        return int(exc.code), dict(exc.headers), exc.read()


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

    def test_save_config_is_atomic_and_keeps_old_file_on_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            config = AppConfig()
            settings.save_config(config, path)
            original = path.read_text(encoding="utf-8")
            self.assertFalse(list(path.parent.glob("config.json.tmp-*")))
            with mock.patch("stitchcraft.settings.os.replace", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    settings.save_config(config, path)
            self.assertEqual(path.read_text(encoding="utf-8"), original)
            self.assertFalse(list(path.parent.glob("config.json.tmp-*")))

    def test_language_roundtrip_and_validation(self) -> None:
        self.assertEqual(set(SUPPORTED_LANGUAGES), {"en", "zh", "de", "ar", "ru"})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            config = AppConfig()
            self.assertEqual(config.ui.language, "")
            for language in SUPPORTED_LANGUAGES:
                config.merge_patch({"ui": {"language": language}})
                self.assertEqual(config.ui.language, language)
            config.merge_patch({"ui": {"language": "xx"}})
            self.assertEqual(config.ui.language, "ru")
            settings.save_config(config, path)
            loaded = settings.load_config(path)
            self.assertEqual(loaded.ui.language, "ru")
            self.assertEqual(loaded.public_dict()["ui"]["language"], "ru")


class RegistryTests(unittest.TestCase):
    def test_skill_registry_is_healthy(self) -> None:
        self.assertEqual(verify_registry(ROOT), [])

    def test_theme_registry_is_healthy(self) -> None:
        self.assertEqual(verify_themes(ROOT), [])

    def test_library_registry_is_healthy(self) -> None:
        self.assertEqual(verify_libraries(ROOT), [])

    def test_design_registry_is_healthy(self) -> None:
        self.assertEqual(designs.verify_designs(ROOT), [])

    def test_every_gsap_copy_ships_attribution(self) -> None:
        copies = [
            path for path in ROOT.rglob("gsap.min.js")
            if ".stitch" not in path.parts and ".git" not in path.parts
        ]
        self.assertGreaterEqual(len(copies), 7)
        for path in copies:
            self.assertTrue((path.parent / "GSAP-LICENSE.txt").is_file(), path)
            self.assertTrue((path.parent / "GSAP-UPSTREAM.md").is_file(), path)
        fabric_demo = ROOT / "docs" / "demo" / "whiteboard" / "vendor"
        self.assertTrue((fabric_demo / "fabric.LICENSE.txt").is_file())
        self.assertTrue((fabric_demo / "UPSTREAM.md").is_file())

    def test_every_gsap_copy_is_listed_in_canonical_notice(self) -> None:
        notice = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
        copies = [
            path.relative_to(ROOT).as_posix()
            for path in ROOT.rglob("gsap.min.js")
            if ".stitch" not in path.parts and ".git" not in path.parts
        ]
        self.assertGreaterEqual(len(copies), 7)
        for relative in copies:
            self.assertIn(relative, notice, f"canonical notice is missing GSAP copy {relative}")

    def test_third_party_notice_links_all_component_indexes(self) -> None:
        notice = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
        for relative in (
            "vendor/ATTRIBUTION.md",
            "skills/ATTRIBUTION.md",
            "designs/ATTRIBUTION.md",
            "themes/brand-launch/sample/vendor/gsap.min.js",
        ):
            self.assertIn(relative, notice)

    def test_every_vendored_skill_pack_keeps_its_license(self) -> None:
        packs = [path for path in (ROOT / "skills" / "vendor").iterdir() if path.is_dir()]
        self.assertGreaterEqual(len(packs), 4)
        for pack in packs:
            self.assertTrue((pack / "UPSTREAM.md").is_file(), pack)
            if pack.name == "gsap-lib":
                self.assertTrue((pack / "GSAP-LICENSE.txt").is_file(), pack)
            else:
                self.assertTrue((pack / "LICENSE").is_file(), pack)

    def test_vendored_library_hashes_match_upstream_records(self) -> None:
        libraries = load_libraries(ROOT)
        self.assertGreaterEqual(len(libraries), 6)
        for library in libraries:
            record = (library.folder / "UPSTREAM.md").read_text(encoding="utf-8")
            digest = hashlib.sha256(library.dist_path.read_bytes()).hexdigest()
            self.assertIn(digest, record, library.id)

    def test_all_gsap_copies_are_byte_identical(self) -> None:
        copies = [
            path for path in ROOT.rglob("gsap.min.js")
            if ".stitch" not in path.parts and ".git" not in path.parts
        ]
        self.assertGreaterEqual(len(copies), 7)
        digests = {hashlib.sha256(path.read_bytes()).hexdigest() for path in copies}
        self.assertEqual(len(digests), 1)

    def test_gitignore_blocks_local_secrets(self) -> None:
        text = (ROOT / ".gitignore").read_text(encoding="utf-8")
        for pattern in (".env", "*.pem", "*.key", "config.json", "secrets*.json"):
            self.assertIn(pattern, text)

    def test_theme_design_references_resolve(self) -> None:
        for theme in load_themes(ROOT):
            if theme.design_reference:
                self.assertIsNotNone(designs.get_design(ROOT, theme.design_reference), theme.id)

    def test_design_context_is_usable(self) -> None:
        context = designs.build_prompt_context(ROOT, "linear", max_chars=2000)
        self.assertIn("DESIGN.md reference: Linear", context)
        self.assertIn("MIT", context)
        with self.assertRaises(designs.DesignError):
            designs.build_prompt_context(ROOT, "does-not-exist")

    def test_landing_page_design_is_vendored(self) -> None:
        pack = ROOT / "skills" / "vendor" / "ai-design-skills"
        self.assertTrue((pack / "LICENSE").is_file())
        self.assertTrue((pack / "UPSTREAM.md").is_file())
        self.assertTrue((pack / "skills" / "landing-page-design" / "SKILL.md").is_file())

    def test_brand_theme_includes_landing_page_design(self) -> None:
        selected = select_for_theme(
            ROOT,
            ["modern-web-guidance", "landing-page-design", "gsap-core", "gsap-scrolltrigger"],
        )
        ids = [skill.id for skill in selected]
        self.assertIn("landing-page-design", ids)
        context = build_skill_context(ROOT, ids, budget_chars=26000)
        self.assertIn("Landing Page Design", context)
        self.assertIn("landing page", context.lower())


class FreeProviderTests(unittest.TestCase):
    def test_keyless_providers_are_free(self) -> None:
        self.assertFalse(provider_requires_key("pollinations"))
        self.assertFalse(provider_requires_key("ollama"))
        self.assertTrue(provider_requires_key("openai"))
        self.assertTrue(provider_requires_key("groq"))

    def test_catalog_exposes_free_options(self) -> None:
        catalog = {entry["id"]: entry for entry in provider_catalog()}
        self.assertIn("pollinations", catalog)
        self.assertFalse(catalog["pollinations"]["requires_key"])
        self.assertTrue(catalog["pollinations"]["free"])
        self.assertTrue(catalog["pollinations"]["compact"])
        self.assertTrue(catalog["zhipu"]["free"])
        self.assertTrue(catalog["zhipu"]["compact"])
        self.assertTrue(catalog["github"]["free"])
        self.assertTrue(catalog["groq"]["free"])
        self.assertTrue(catalog["deepseek"]["requires_key"])
        self.assertFalse(catalog["deepseek"]["free"])

    def test_default_config_uses_a_keyless_provider(self) -> None:
        config = AppConfig()
        self.assertFalse(provider_requires_key(config.ai.provider))
        self.assertTrue(config.ai.base_url)


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
            self.assertTrue((out / "vendor" / "gsap.min.js").is_file())
            self.assertTrue((out / "vendor" / "GSAP-LICENSE.txt").is_file())
            self.assertTrue((out / "vendor" / "GSAP-UPSTREAM.md").is_file())

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

    def test_keyless_provider_can_generate_with_ai_without_a_key(self) -> None:
        config = AppConfig()
        config.ai.provider = "pollinations"
        config.ai.base_url = "https://text.pollinations.ai/openai"
        config.ai.model = "openai"
        config.ai.api_key = ""
        payload = {
            "files": [
                {"path": "index.html", "content": "<!doctype html><html lang=\"en\"><head><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"><title>Free AI test</title></head><body><h1>Warehouse</h1><p>Built through a free provider.</p><script src=\"data-config.js\"></script><script src=\"app.js\"></script></body></html>"},
                {"path": "styles.css", "content": "body{font-family:system-ui,sans-serif}"},
                {"path": "app.js", "content": "document.documentElement.dataset.ready='true';"},
            ],
            "summary": "A keyless-provider test site.",
        }
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "site"
            with mock.patch("stitchcraft.ai_client.chat", return_value=json.dumps(payload)) as patched:
                result = generate_site(
                    ROOT,
                    config,
                    GenerationRequest(
                        theme_id="warehouse-ops",
                        prompt="A small warehouse dashboard with inventory.",
                        engine="ai",
                        database={"mode": "local", "remote": {}},
                    ),
                    out,
                    sleep=lambda _seconds: None,
                )
            patched.assert_called_once()
            self.assertTrue((out / "index.html").is_file())
            self.assertTrue((out / "data-config.js").is_file())
            self.assertEqual(result.engine, "ai")
            self.assertEqual(result.summary, "A keyless-provider test site.")


    def test_ai_generation_copies_referenced_libraries(self) -> None:
        config = AppConfig()
        config.ai.provider = "pollinations"
        config.ai.base_url = "https://text.pollinations.ai/openai"
        config.ai.model = "openai"
        config.ai.api_key = ""
        html = (
            "<!doctype html><html lang=\"en\"><head>"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            "<title>Tools test</title></head><body><h1>Whiteboard</h1><div id=\"board\"></div>"
            "<script src=\"vendor/fabric/fabric.min.js\"></script>"
            "<script src=\"data-config.js\"></script>"
            "<script src=\"app.js\"></script></body></html>"
        )
        payload = {
            "files": [
                {"path": "index.html", "content": html},
                {"path": "app.js", "content": "document.documentElement.dataset.ready='true';"},
            ],
            "summary": "A whiteboard test site.",
        }
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "site"
            with mock.patch("stitchcraft.ai_client.chat", return_value=json.dumps(payload)):
                result = generate_site(
                    ROOT,
                    config,
                    GenerationRequest(
                        theme_id="personal-space",
                        prompt="A personal space with a drawing board.",
                        engine="ai",
                        database={"mode": "local", "remote": {}},
                    ),
                    out,
                    sleep=lambda _seconds: None,
                )
            self.assertTrue((out / "vendor" / "fabric" / "fabric.min.js").is_file())
            self.assertTrue((out / "vendor" / "fabric" / "LICENSE").is_file())
            self.assertTrue((out / "vendor" / "fabric" / "UPSTREAM.md").is_file())
            self.assertIn("vendor/fabric/fabric.min.js", result.files)


class QualityWarningTests(unittest.TestCase):
    def test_external_runtime_assets_are_flagged_but_anchors_are_not(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "index.html").write_text(
                '<!doctype html><html><head>'
                '<link rel="stylesheet" href="https://fonts.example/site.css">'
                '</head><body>'
                '<a href="https://example.com/learn-more">Read more</a>'
                '<script src="https://cdn.example/app.js"></script>'
                '<img src="//cdn.example/photo.png" alt="photo">'
                '</body></html>',
                encoding="utf-8",
            )
            (out / "styles.css").write_text('@import url("https://cdn.example/font.css");', encoding="utf-8")
            warnings = generator._external_asset_warnings(out)
        joined = "\n".join(warnings)
        self.assertIn("https://cdn.example/app.js", joined)
        self.assertIn("https://fonts.example/site.css", joined)
        self.assertIn("https://cdn.example/font.css", joined)
        self.assertNotIn("https://example.com/learn-more", joined)

    def test_packaged_samples_are_offline(self) -> None:
        for theme in load_themes(ROOT):
            if theme.sample_path is None:
                continue
            self.assertEqual(generator._external_asset_warnings(theme.sample_path), [], theme.id)


class OutputSafetyTests(unittest.TestCase):
    def _request(self) -> GenerationRequest:
        return GenerationRequest(
            theme_id="warehouse-ops",
            prompt="A warehouse operations dashboard with inventory CRUD.",
            engine="mock",
            database={"mode": "local", "remote": {}},
        )

    def test_refuses_to_clean_a_foreign_non_empty_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "precious"
            out.mkdir()
            kept = out / "notes.txt"
            kept.write_text("do not delete", encoding="utf-8")
            with self.assertRaises(GenerationError):
                generate_site(ROOT, AppConfig(), self._request(), out)
            self.assertTrue(kept.is_file())
            self.assertEqual(kept.read_text(encoding="utf-8"), "do not delete")

    def test_marker_allows_replacing_a_previous_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "site"
            out.mkdir()
            (out / ".stitchcraft-site").write_text("owned", encoding="utf-8")
            (out / "stale.html").write_text("old", encoding="utf-8")
            result = generate_site(ROOT, AppConfig(), self._request(), out)
            self.assertFalse((out / "stale.html").exists())
            self.assertTrue((out / "index.html").is_file())
            self.assertIn("index.html", result.files)

    def test_force_allows_a_foreign_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "scratch"
            out.mkdir()
            (out / "old.txt").write_text("old", encoding="utf-8")
            result = generate_site(ROOT, AppConfig(), self._request(), out, force=True)
            self.assertFalse((out / "old.txt").exists())
            self.assertTrue((out / "index.html").is_file())
            self.assertIn("index.html", result.files)

    def test_failed_generation_preserves_the_previous_site(self) -> None:
        config = AppConfig()
        config.ai.provider = "openai"
        config.ai.base_url = "https://api.openai.com/v1"
        config.ai.model = "gpt-4o-mini"
        config.ai.api_key = "sk-test-key-12345678"
        request = GenerationRequest(
            theme_id="warehouse-ops",
            prompt="A warehouse dashboard with inventory and inbound shipments.",
            engine="ai",
            database={"mode": "local", "remote": {}},
        )
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "site"
            out.mkdir()
            (out / ".stitchcraft-site").write_text("owned", encoding="utf-8")
            (out / "index.html").write_text("OLD SITE", encoding="utf-8")
            with mock.patch("stitchcraft.ai_client.chat", side_effect=RuntimeError("network down")):
                with self.assertRaises(RuntimeError):
                    generate_site(ROOT, config, request, out)
            self.assertEqual((out / "index.html").read_text(encoding="utf-8"), "OLD SITE")
            self.assertFalse(list(Path(tmp).glob(".*.build-*")), "staging directory was not cleaned up")


class PlanValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.theme = get_theme(ROOT, "warehouse-ops")

    def _plan(self) -> dict:
        return {
            "sitemap": [{"path": "/", "title": "Home"}],
            "navigation": {"primary": [{"label": "Home", "path": "/"}]},
            "sections": [],
        }

    def test_valid_plan_is_accepted(self) -> None:
        plan = generator._validate_site_plan(self._plan(), self.theme)
        self.assertEqual(plan["navigation"]["primary"][0]["path"], "/")

    def test_navigation_item_needs_label_and_path(self) -> None:
        plan = self._plan()
        plan["navigation"]["primary"] = [{"label": "", "path": "/"}]
        with self.assertRaises(GenerationError):
            generator._validate_site_plan(plan, self.theme)
        plan["navigation"]["primary"] = [{"label": "Home", "path": "#missing"}]
        with self.assertRaises(GenerationError):
            generator._validate_site_plan(plan, self.theme)

    def test_navigation_target_must_exist_in_sitemap(self) -> None:
        plan = self._plan()
        plan["navigation"]["primary"] = [{"label": "Missing", "path": "/missing"}]
        with self.assertRaises(GenerationError):
            generator._validate_site_plan(plan, self.theme)

    def test_duplicate_pages_are_rejected(self) -> None:
        plan = self._plan()
        plan["sitemap"].append({"path": "/", "title": "Duplicate"})
        with self.assertRaises(GenerationError):
            generator._validate_site_plan(plan, self.theme)

    def test_invalid_model_plan_falls_back_to_theme_plan(self) -> None:
        invalid_plan = {"sitemap": [{"path": "/", "title": "Home"}], "navigation": {"primary": [{"label": "", "path": "#"}]}}
        files = {
            "files": [
                {"path": "index.html", "content": '<!doctype html><html lang="en"><head><title>Fallback</title><link rel="stylesheet" href="styles.css"></head><body><h1>Fallback</h1></body></html>'},
                {"path": "styles.css", "content": "body{color:#222}"},
            ],
            "summary": "Fallback build.",
        }
        calls: list[list[dict]] = []

        def fake_chat(_config, messages, json_mode=True):
            calls.append(messages)
            return json.dumps(invalid_plan if len(calls) == 1 else files)

        config = AppConfig()
        config.ai.provider = "openai"
        config.ai.base_url = "https://api.openai.com/v1"
        config.ai.model = "gpt-4o-mini"
        config.ai.api_key = "sk-test-key-12345678"
        with tempfile.TemporaryDirectory() as tmp, mock.patch("stitchcraft.ai_client.chat", side_effect=fake_chat):
            result = generate_site(
                ROOT,
                config,
                GenerationRequest(
                    theme_id="warehouse-ops",
                    prompt="A warehouse dashboard with inventory and inbound shipments.",
                    engine="ai",
                    database={"mode": "local", "remote": {}},
                ),
                Path(tmp) / "site",
            )
        self.assertEqual(len(calls), 2)
        self.assertTrue(any("model plan was invalid" in warning for warning in result.warnings), result.warnings)
        self.assertEqual(result.model_calls, 2)
        self.assertEqual(result.retries, 0)


class AIGenerationTests(unittest.TestCase):
    def _config(self, provider: str = "openai") -> AppConfig:
        config = AppConfig()
        config.ai.provider = provider
        config.ai.base_url = "https://api.openai.com/v1"
        config.ai.model = "gpt-4o-mini"
        config.ai.api_key = "sk-test-key-12345678"
        return config

    def test_non_compact_provider_gets_a_planning_call_and_block_context(self) -> None:
        plan = {
            "sitemap": [{"path": "/", "title": "Warehouse", "sections": ["hero", "stat-grid"]}],
            "navigation": {"primary": [{"label": "Home", "path": "/"}]},
            "sections": [{"id": "hero", "block": "hero", "purpose": "Open with the headline"}],
            "design": {"mood": "operations", "accent": "#ff8a3d"},
        }
        files = {
            "files": [
                {"path": "index.html", "content": '<!doctype html><html lang="en"><head><title>Warehouse</title><link rel="stylesheet" href="styles.css"></head><body><h1>Warehouse</h1><script src="app.js"></script><script src="data-config.js"></script></body></html>'},
                {"path": "styles.css", "content": "body{color:#222}"},
                {"path": "app.js", "content": "document.documentElement.dataset.ready='true';"},
            ],
            "summary": "Warehouse operations.",
        }
        calls: list[list[dict]] = []

        def fake_chat(_config, messages, json_mode=True):
            calls.append(messages)
            return json.dumps(plan if len(calls) == 1 else files)

        with tempfile.TemporaryDirectory() as tmp, mock.patch("stitchcraft.ai_client.chat", side_effect=fake_chat):
            result = generate_site(ROOT, self._config(), GenerationRequest(
                theme_id="warehouse-ops",
                prompt="A warehouse dashboard with inventory and inbound shipments.",
                engine="ai",
                database={"mode": "local", "remote": {}},
            ), Path(tmp) / "site")
        self.assertEqual(len(calls), 2)
        build_prompt = calls[1][1]["content"]
        self.assertIn("Approved site plan", build_prompt)
        self.assertIn("Theme reference blocks", build_prompt)
        self.assertIn("DESIGN.md reference: Linear", build_prompt)
        self.assertIn("index.html", result.files)
        self.assertEqual(result.model_calls, 2)
        self.assertEqual(result.retries, 0)
        self.assertFalse(result.placeholder)

    def test_missing_local_reference_is_reported(self) -> None:
        files = {
            "files": [
                {"path": "index.html", "content": '<!doctype html><html lang="en"><head><title>Missing</title><link rel="stylesheet" href="missing.css"></head><body><h1>Missing asset</h1><script src="app.js"></script></body></html>'},
                {"path": "app.js", "content": "document.documentElement.dataset.ready='true';"},
            ],
            "summary": "Broken reference test.",
        }
        with tempfile.TemporaryDirectory() as tmp, mock.patch("stitchcraft.ai_client.chat", return_value=json.dumps(files)):
            result = generate_site(
                ROOT,
                self._config("pollinations"),
                GenerationRequest(
                    theme_id="warehouse-ops",
                    prompt="A warehouse dashboard with a deliberately missing stylesheet reference.",
                    engine="ai",
                    database={"mode": "local", "remote": {}},
                ),
                Path(tmp) / "site",
            )
        self.assertTrue(any("missing local file" in warning for warning in result.warnings), result.warnings)

    def test_continue_mode_completes_imported_site_and_preserves_untouched_files(self) -> None:
        imported = [
            {"path": "index.html", "content": '<!doctype html><html lang="en"><head><title>Half built</title><link rel="stylesheet" href="styles.css"></head><body><h1>Half built</h1><footer>Old footer</footer></body></html>'},
            {"path": "styles.css", "content": "body{color:#234}"},
            {"path": "notes.txt", "content": "keep this imported note"},
        ]
        files = {
            "files": [{"path": "index.html", "content": '<!doctype html><html lang="en"><head><title>Finished</title><link rel="stylesheet" href="styles.css"></head><body><h1>Finished</h1><footer>New footer</footer><script src="data-config.js"></script></body></html>'}],
            "summary": "Completed the imported landing page.",
        }
        calls: list[list[dict]] = []

        def fake_chat(_config, messages, json_mode=True):
            calls.append(messages)
            return json.dumps(files)

        with tempfile.TemporaryDirectory() as tmp, mock.patch("stitchcraft.ai_client.chat", side_effect=fake_chat):
            out = Path(tmp) / "site"
            result = generate_site(
                ROOT,
                self._config("pollinations"),
                GenerationRequest(
                    theme_id="brand-launch",
                    prompt="Finish the pricing section and keep the existing footer tone.",
                    engine="ai",
                    database={"mode": "local", "remote": {}},
                    import_files=imported,
                ),
                out,
            )
            self.assertEqual(len(calls), 1)
            prompt_text = "\n".join(str(message.get("content", "")) for message in calls[0])
            self.assertIn("Existing half-built site", prompt_text)
            self.assertIn("## styles.css", prompt_text)
            self.assertIn("Finished", (out / "index.html").read_text(encoding="utf-8"))
            self.assertEqual((out / "styles.css").read_text(encoding="utf-8"), "body{color:#234}")
            self.assertTrue((out / "notes.txt").is_file())
            self.assertIn("styles.css", result.files)
            self.assertEqual(result.model_calls, 1)

    def test_continue_mode_rejects_mock_engine(self) -> None:
        request = GenerationRequest(
            theme_id="brand-launch",
            prompt="Finish this half-built page.",
            engine="mock",
            import_files=[{"path": "index.html", "content": "<!doctype html><html><body>draft</body></html>"}],
        )
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(GenerationError):
                generate_site(ROOT, AppConfig(), request, Path(tmp) / "site")


class ImportValidationTests(unittest.TestCase):
    def test_rejects_traversal_and_missing_index(self) -> None:
        with self.assertRaises(GenerationError):
            generator.normalize_import_files([{"path": "../outside.html", "content": "x"}])
        with self.assertRaises(GenerationError):
            generator.normalize_import_files([{"path": "styles.css", "content": "body{}"}])

    def test_collects_text_files_and_skips_binary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text("<!doctype html><html><body>draft</body></html>", encoding="utf-8")
            (root / "styles.css").write_text("body{color:#111}", encoding="utf-8")
            (root / "photo.png").write_bytes(b"\x89PNG\r\n")
            (root / "notes.txt").write_text("keep", encoding="utf-8")
            files = generator.collect_import_files(root)
        self.assertEqual({item["path"] for item in files}, {"index.html", "styles.css", "notes.txt"})


class JobQueueTests(unittest.TestCase):
    def _job(self, title: str = "job") -> Job:
        request = GenerationRequest(
            theme_id="warehouse-ops",
            prompt="A warehouse dashboard with inventory and inbound shipments.",
            engine="mock",
            database={"mode": "local", "remote": {}},
        )
        return Job(request, theme_id="warehouse-ops", title=title, engine="mock")

    def test_cancel_queued_job_removes_it_without_touching_the_active_slot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"STITCHCRAFT_HOME": tmp}):
            context = StudioContext(ROOT, config=AppConfig(), store=ProjectStore(Path(tmp) / "data"))
            context.active_jobs = 1
            queued = self._job("queued")
            result = context.enqueue_generation(queued)
            self.assertTrue(result["queued"])
            cancelled = context.cancel_job(queued.id)
            self.assertEqual(cancelled["status"], "cancelled")
            self.assertEqual(queued.status, "cancelled")
            self.assertEqual(context.queue_status()["queued"], 0)
            self.assertEqual(context.queue_status()["active"], 1)

    def test_cancel_running_job_requests_cooperative_stop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"STITCHCRAFT_HOME": tmp}):
            context = StudioContext(ROOT, config=AppConfig(), store=ProjectStore(Path(tmp) / "data"))
            running = self._job("running")
            running.status = "running"
            context.jobs[running.id] = running
            context.active_jobs = 1
            result = context.cancel_job(running.id)
            self.assertTrue(result["cancelling"])
            self.assertTrue(running.cancel_requested)
            self.assertEqual(running.status, "running")
            context._cancel_running(running)
            self.assertEqual(running.status, "cancelled")

    def test_second_job_waits_for_the_active_build(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"STITCHCRAFT_HOME": tmp}):
            context = StudioContext(ROOT, config=AppConfig(), store=ProjectStore(Path(tmp) / "data"))
            started = threading.Event()
            release = threading.Event()

            def fake_run(job) -> None:
                started.set()
                release.wait(5)
                with context.lock:
                    job.status = "done"
                    job.progress = 100
                context.job_finished(job)

            context.run_generation = fake_run

            def make_job(title: str) -> Job:
                request = GenerationRequest(
                    theme_id="warehouse-ops",
                    prompt="A warehouse dashboard with inventory and inbound shipments.",
                    engine="mock",
                    database={"mode": "local", "remote": {}},
                )
                return Job(request, theme_id="warehouse-ops", title=title, engine="mock")

            first, second = make_job("first"), make_job("second")
            first_result = context.enqueue_generation(first)
            self.assertTrue(first_result["accepted"])
            self.assertTrue(started.wait(2), "the first job did not start")
            second_result = context.enqueue_generation(second)
            self.assertTrue(second_result["queued"])
            self.assertEqual(second_result["position"], 1)
            self.assertEqual(second.status, "queued")
            release.set()
            deadline = time.time() + 5
            while time.time() < deadline and second.status != "done":
                time.sleep(0.02)
            self.assertEqual(first.status, "done")
            self.assertEqual(second.status, "done")
            self.assertEqual(context.queue_status()["active"], 0)
            self.assertEqual(context.queue_status()["queued"], 0)


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
        cls.preview_base = f"http://localhost:{cls.port}"
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
        status, payload = _get_json(self.base + "/api/ai/providers")
        self.assertEqual(status, 200)
        providers = {entry["id"]: entry for entry in payload["providers"]}
        self.assertIn("pollinations", providers)
        self.assertFalse(providers["pollinations"]["requires_key"])
        status, payload = _get_json(self.base + "/api/libraries")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(payload["libraries"]), 6)
        status, payload = _get_json(self.base + "/api/designs")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(payload["designs"]), 5)
        self.assertIn("linear", [item["id"] for item in payload["designs"]])
        status, payload = _get_json(self.base + "/api/ai/local")
        self.assertEqual(status, 200)
        self.assertIn("ok", payload)

    def test_browser_status_endpoint(self) -> None:
        status, payload = _get_json(self.base + "/api/browser")
        self.assertEqual(status, 200)
        self.assertEqual(payload["version"], browser.OBSCURA_VERSION)
        self.assertEqual(payload["license"], "Apache-2.0")
        self.assertIn("installed", payload)
        self.assertIn("settings", payload)
        self.assertIn("auto_check", payload["settings"])
        self.assertFalse(payload["installed"])

    def test_browser_settings_roundtrip(self) -> None:
        status, payload = _get_json(
            self.base + "/api/settings",
            "POST",
            {"browser": {"auto_check": False, "allow_private_network": False}},
        )
        self.assertEqual(status, 200)
        self.assertFalse(payload["settings"]["browser"]["auto_check"])
        status, payload = _get_json(self.base + "/api/settings")
        self.assertFalse(payload["browser"]["auto_check"])

    def test_settings_roundtrip(self) -> None:
        status, payload = _get_json(
            self.base + "/api/settings",
            "POST",
            {"ai": {"provider": "openai", "model": "gpt-4o-mini"}},
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])

    def test_language_setting_roundtrip(self) -> None:
        for language in SUPPORTED_LANGUAGES:
            status, payload = _get_json(
                self.base + "/api/settings",
                "POST",
                {"ui": {"language": language}},
            )
            self.assertEqual(status, 200)
            self.assertEqual(payload["settings"]["ui"]["language"], language)
        status, payload = _get_json(
            self.base + "/api/settings",
            "POST",
            {"ui": {"language": "not-a-language"}},
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["settings"]["ui"]["language"], "ru")

    def test_rejects_cross_origin_settings_write(self) -> None:
        payload = json.dumps({"ai": {"base_url": "https://evil.example/v1"}}).encode("utf-8")
        status, _headers, _body = _raw_request(
            self.base + "/api/settings",
            "POST",
            payload,
            {"Content-Type": "application/json", "Origin": "https://evil.example"},
        )
        self.assertEqual(status, 403)
        status, settings = _get_json(self.base + "/api/settings")
        self.assertEqual(status, 200)
        self.assertNotIn("evil.example", json.dumps(settings))

    def test_rejects_text_plain_settings_write(self) -> None:
        payload = json.dumps({"ai": {"base_url": "https://evil.example/v1"}}).encode("utf-8")
        status, _headers, _body = _raw_request(
            self.base + "/api/settings",
            "POST",
            payload,
            {"Content-Type": "text/plain"},
        )
        self.assertEqual(status, 415)

    def test_rejects_foreign_host_header(self) -> None:
        status, _headers, _body = _raw_request(
            self.base + "/api/settings",
            "GET",
            None,
            {"Host": "evil.example"},
        )
        self.assertEqual(status, 403)

    def test_rejects_oversized_request_body(self) -> None:
        # Send only the headers: the server must reject on Content-Length before
        # reading the body. This avoids a platform-dependent reset while the
        # client is still uploading 2 MB.
        with socket.create_connection(("127.0.0.1", self.port), timeout=10) as sock:
            request = (
                f"POST /api/settings HTTP/1.1\r\n"
                f"Host: 127.0.0.1:{self.port}\r\n"
                "Content-Type: application/json\r\n"
                f"Content-Length: {2 * 1024 * 1024 + 1}\r\n"
                "Connection: close\r\n\r\n"
            )
            sock.sendall(request.encode("ascii"))
            response = sock.recv(4096)
        self.assertIn(b" 413 ", response.split(b"\r\n", 1)[0])

    def test_preview_is_cross_origin_and_has_csp(self) -> None:
        status, _headers, _body = _raw_request(self.base + "/api/demo/personal-space/")
        self.assertEqual(status, 403)
        status, headers, body = _raw_request(self.preview_base + "/api/demo/personal-space/")
        self.assertEqual(status, 200)
        self.assertIn("Content-Security-Policy", headers)
        self.assertIn(b"Notes from the attic", body)

    def test_preview_host_only_serves_previews(self) -> None:
        for path in ("/", "/api/settings", "/api/status", "/api/projects"):
            status, _headers, _body = _raw_request(self.preview_base + path)
            self.assertEqual(status, 403, path)
        status, _headers, _body = _raw_request(self.preview_base + "/api/demo/personal-space/")
        self.assertEqual(status, 200)

    def test_preview_host_cannot_write_management_settings(self) -> None:
        payload = json.dumps({"ai": {"base_url": "https://evil.example/v1"}}).encode("utf-8")
        status, _headers, _body = _raw_request(
            self.preview_base + "/api/settings",
            "POST",
            payload,
            {"Content-Type": "application/json", "Origin": self.preview_base},
        )
        self.assertEqual(status, 403)
        status, settings = _get_json(self.base + "/api/settings")
        self.assertEqual(status, 200)
        self.assertNotIn("evil.example", json.dumps(settings))

    def test_status_exposes_cross_origin_preview_base(self) -> None:
        status, payload = _get_json(self.base + "/api/status")
        self.assertEqual(status, 200)
        self.assertEqual(payload["preview_base"], self.preview_base)

    def test_same_origin_json_write_is_accepted(self) -> None:
        payload = json.dumps({"browser": {"auto_check": True}}).encode("utf-8")
        status, _headers, body = _raw_request(
            self.base + "/api/settings",
            "POST",
            payload,
            {"Content-Type": "application/json", "Origin": self.base},
        )
        self.assertEqual(status, 200)

    def test_frontend_security_contract(self) -> None:
        html = (ROOT / "app" / "web" / "index.html").read_text(encoding="utf-8")
        self.assertIn('sandbox="allow-scripts', html)
        self.assertIn("preview-frame", html)
        app_js = (ROOT / "app" / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn("preview_base", app_js)
        self.assertIn("function previewBase", app_js)

    def test_frontend_language_contract(self) -> None:
        html = (ROOT / "app" / "web" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="language-select"', html)
        self.assertIn("i18n.js", html)
        self.assertIn('dir="ltr"', html)
        i18n_js = (ROOT / "app" / "web" / "i18n.js").read_text(encoding="utf-8")
        self.assertIn("var SUPPORTED = ['zh', 'en', 'de', 'ar', 'ru']", i18n_js)
        self.assertIn("document.documentElement.dir", i18n_js)
        self.assertIn("'rtl'", i18n_js)
        app_js = (ROOT / "app" / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn("bindLanguage", app_js)
        self.assertIn("StitchcraftI18n", app_js)

    def test_frontend_continuation_contract(self) -> None:
        html = (ROOT / "app" / "web" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="import-input"', html)
        self.assertIn('id="pipeline-cancel"', html)
        self.assertIn("js/jobs.js", html)
        self.assertIn("js/import-site.js", html)
        jobs_js = (ROOT / "app" / "web" / "js" / "jobs.js").read_text(encoding="utf-8")
        self.assertIn("ReadableStream", jobs_js)
        self.assertIn("/events", jobs_js)
        self.assertIn("ended before the job finished", jobs_js)
        import_js = (ROOT / "app" / "web" / "js" / "import-site.js").read_text(encoding="utf-8")
        self.assertIn("readFolder", import_js)
        app_js = (ROOT / "app" / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn("StitchcraftJobs", app_js)
        self.assertIn("StitchcraftImport", app_js)
        self.assertIn("StitchcraftConfig", app_js)
        self.assertIn("js/config.js", html)
        config_js = (ROOT / "app" / "web" / "js" / "config.js").read_text(encoding="utf-8")
        self.assertIn("StitchcraftConfig", config_js)
        self.assertIn("STAGES", config_js)

    def test_job_events_streams_a_terminal_snapshot(self) -> None:
        job = Job(
            GenerationRequest(theme_id="warehouse-ops", prompt="A warehouse dashboard.", engine="mock", database={"mode": "local", "remote": {}}),
            theme_id="warehouse-ops",
            title="event job",
            engine="mock",
        )
        job.status = "done"
        self.context.jobs[job.id] = job
        try:
            with urllib.request.urlopen(self.base + f"/api/jobs/{job.id}/events", timeout=10) as response:
                self.assertIn("text/event-stream", response.headers.get("Content-Type", ""))
                body = response.read().decode("utf-8", "replace")
            self.assertIn("data:", body)
            self.assertIn('"done"', body)
        finally:
            self.context.jobs.pop(job.id, None)

    def test_cancel_endpoint_rejects_unknown_job(self) -> None:
        status, _headers, body = _raw_request(
            self.base + "/api/jobs/not-a-job/cancel",
            "POST",
            json.dumps({}).encode("utf-8"),
            {"Content-Type": "application/json", "Origin": self.base},
        )
        self.assertEqual(status, 404)
        self.assertFalse(json.loads(body)["ok"])

    def test_generate_imported_site_with_ai(self) -> None:
        imported = [{
            "path": "index.html",
            "content": '<!doctype html><html lang="en"><head><title>Draft</title><link rel="stylesheet" href="styles.css"></head><body><h1>Draft</h1></body></html>',
        }, {"path": "styles.css", "content": "body{color:#123}"}]
        model = {
            "files": [{"path": "index.html", "content": '<!doctype html><html lang="en"><head><title>Finished</title><link rel="stylesheet" href="styles.css"></head><body><h1>Finished</h1><script src="data-config.js"></script></body></html>'}],
            "summary": "Finished imported site.",
        }
        with mock.patch("stitchcraft.ai_client.chat", return_value=json.dumps(model)):
            status, payload = _get_json(
                self.base + "/api/generate",
                "POST",
                {
                    "theme_id": "brand-launch",
                    "title": "Imported draft",
                    "prompt": "Finish the page and keep the existing styles.",
                    "engine": "ai",
                    "database": {"mode": "local", "remote": {}},
                    "import_files": imported,
                },
            )
            self.assertEqual(status, 202, payload)
            job_id = payload["job_id"]
            job = {}
            for _ in range(300):
                status, job = _get_json(self.base + f"/api/jobs/{job_id}")
                if job.get("status") in {"done", "error", "cancelled"}:
                    break
                time.sleep(0.05)
        self.assertEqual(job.get("status"), "done", job.get("error"))
        self.assertTrue(job.get("import_mode"))
        self.assertTrue(job.get("project_id"))

    def test_import_requires_ai_engine(self) -> None:
        status, _headers, body = _raw_request(
            self.base + "/api/generate",
            "POST",
            json.dumps({
                "theme_id": "brand-launch",
                "prompt": "Finish this draft.",
                "engine": "mock",
                "import_files": [{"path": "index.html", "content": "<!doctype html><html><body>draft</body></html>"}],
            }).encode("utf-8"),
            {"Content-Type": "application/json", "Origin": self.base},
        )
        self.assertEqual(status, 400)
        self.assertIn("AI", json.loads(body)["error"])

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
        self.assertEqual(_status(self.preview_base + f"/api/preview/{project_id}/"), 200)
        self.assertEqual(_status(self.base + f"/api/preview/{project_id}/"), 403)
        self.assertEqual(_status(self.base + f"/api/export/{project_id}"), 200)
        status, payload = _get_json(self.base + "/api/projects")
        self.assertIn(project_id, [item["id"] for item in payload["projects"]])
        self.assertEqual(_status(self.base + f"/api/projects/{project_id}", "DELETE"), 200)
        self.assertEqual(_status(self.preview_base + f"/api/preview/{project_id}/"), 404)


if __name__ == "__main__":
    unittest.main()
