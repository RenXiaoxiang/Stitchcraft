"""Tests for the optional Obscura browser runtime (offline; no downloads)."""

from __future__ import annotations

import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from stitchcraft import browser  # noqa: E402


def _zip_bytes(entries: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    return buffer.getvalue()


def _runner(command: list[str], timeout: float):
    if "--version" in command:
        return SimpleNamespace(returncode=0, stdout="obscura 0.2.7\\n", stderr="")
    if "--eval" in command:
        metrics = {
            "title": "Test site",
            "lang": "en",
            "h1": 1,
            "textChars": 420,
            "links": {"total": 4, "external": 1, "anchors": 2, "empty": 0},
            "missingAnchors": [],
            "images": {"total": 2, "missingAlt": 0},
            "forms": 1,
            "buttons": 3,
            "landmarks": {"main": 1, "nav": 1},
        }
        return SimpleNamespace(returncode=0, stdout=json.dumps(json.dumps(metrics)), stderr="")
    if "--output" in command:
        Path(command[command.index("--output") + 1]).write_text("Hello rendered page. " * 10, encoding="utf-8")
    if "--screenshot" in command:
        Path(command[command.index("--screenshot") + 1]).write_bytes(b"\x89PNG\r\n")
    return SimpleNamespace(returncode=0, stdout="", stderr="")


class PlatformTests(unittest.TestCase):
    def test_platform_mapping(self) -> None:
        self.assertEqual(browser.platform_key("win32", "AMD64"), "windows-x86_64")
        self.assertEqual(browser.platform_key("linux", "x86_64"), "linux-x86_64")
        self.assertEqual(browser.platform_key("linux", "aarch64"), "linux-aarch64")
        self.assertEqual(browser.platform_key("darwin", "arm64"), "macos-aarch64")
        self.assertEqual(browser.platform_key("darwin", "x86_64"), "macos-x86_64")
        self.assertIsNone(browser.platform_key("win32", "ARM64"))
        self.assertIsNone(browser.platform_key("freebsd", "x86_64"))

    def test_assets_are_pinned_with_checksums(self) -> None:
        self.assertIn("windows-x86_64", browser.ASSETS)
        for key, entry in browser.ASSETS.items():
            self.assertIn("asset", entry)
            self.assertIn("sha256", entry)
            self.assertRegex(str(entry["sha256"]), r"^[0-9a-f]{64}$")
            self.assertGreater(int(entry["size"]), 1_000_000)
            self.assertTrue(browser.download_url(entry).startswith("https://github.com/h4ckf0r0day/obscura/releases/"))

    def test_download_url_through_mirror(self) -> None:
        entry = browser.ASSETS["windows-x86_64"]
        direct = browser.download_url(entry)
        self.assertEqual(browser.download_url(entry, "https://gh-proxy.com"), "https://gh-proxy.com/" + direct)
        self.assertEqual(
            browser.download_url(entry, "https://mirror.example/{url}"),
            "https://mirror.example/" + direct,
        )

    def test_bundled_license_files(self) -> None:
        data = Path(browser.__file__).resolve().parent / "data"
        license_text = (data / "obscura-LICENSE.txt").read_text(encoding="utf-8")
        self.assertIn("Apache License", license_text)
        notice = (data / "obscura-NOTICE.txt").read_text(encoding="utf-8")
        self.assertIn("obscura", notice.lower())


class ManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name) / "browser"
        self.manager = browser.BrowserManager(
            self.base,
            system="win32",
            machine="AMD64",
            runner=_runner,
        )
        self.payload = _zip_bytes(
            {
                "obscura.exe": b"fake-binary",
                "obscura-worker.exe": b"fake-worker",
                "runtime.dll": b"fake-dll",
            }
        )
        self.digest = hashlib.sha256(self.payload).hexdigest()
        self.asset = {
            "asset": "fake-obscura.zip",
            "archive": "zip",
            "size": len(self.payload),
            "sha256": self.digest,
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _patch_asset(self):
        return mock.patch.dict(browser.ASSETS, {"windows-x86_64": self.asset})

    def test_status_before_install(self) -> None:
        status = self.manager.status()
        self.assertTrue(status["supported"])
        self.assertFalse(status["installed"])
        self.assertEqual(status["version"], browser.OBSCURA_VERSION)
        self.assertEqual(status["license"], "Apache-2.0")

    def test_install_downloads_verifies_and_writes_manifest(self) -> None:
        progress: list[tuple[int, int]] = []

        def fake_download(url: str, destination: Path, callback=None) -> None:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(self.payload)
            if callback:
                callback(len(self.payload), len(self.payload))

        with self._patch_asset(), mock.patch.object(self.manager, "_downloader", side_effect=fake_download):
            status = self.manager.install(progress=lambda done, total: progress.append((done, total)), force=True)
        self.assertTrue(status["installed"])
        self.assertTrue(self.manager.binary_path().is_file())
        self.assertTrue((self.manager.install_dir / "LICENSE").is_file())
        self.assertTrue((self.manager.install_dir / "NOTICE").is_file())
        manifest = json.loads(self.manager.manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["sha256"], self.digest)
        self.assertEqual(manifest["version"], browser.OBSCURA_VERSION)
        self.assertEqual(progress[-1][0], len(self.payload))

    def test_install_rejects_bad_digest(self) -> None:
        def fake_download(url: str, destination: Path, callback=None) -> None:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(self.payload + b"tampered")

        bad_asset = dict(self.asset)
        with self._patch_asset():
            with mock.patch.object(self.manager, "_downloader", side_effect=fake_download):
                with self.assertRaises(browser.BrowserError):
                    self.manager.install(force=True)

    def test_zip_traversal_is_rejected(self) -> None:
        evil = _zip_bytes({"../evil.txt": b"nope", "obscura.exe": b"fake"})
        asset = {
            "asset": "evil.zip",
            "archive": "zip",
            "size": len(evil),
            "sha256": hashlib.sha256(evil).hexdigest(),
        }
        with mock.patch.dict(browser.ASSETS, {"windows-x86_64": asset}), mock.patch.object(
            self.manager, "_downloader", side_effect=lambda url, dest, cb: (dest.parent.mkdir(parents=True, exist_ok=True), dest.write_bytes(evil))
        ):
            with self.assertRaises(browser.BrowserError):
                self.manager.install(force=True)
        self.assertFalse((self.base / "evil.txt").exists())

    def test_check_produces_report_and_screenshot(self) -> None:
        def fake_download(url: str, destination: Path, callback=None) -> None:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(self.payload)
        with self._patch_asset(), mock.patch.object(self.manager, "_downloader", side_effect=fake_download):
            self.manager.install(force=True)
        report = self.manager.check("http://127.0.0.1:9999/api/preview/demo/", self.base / "check")
        self.assertTrue(report["ok"])
        self.assertEqual(report["title"], "Test site")
        self.assertTrue(Path(report["screenshot"]).is_file())
        self.assertTrue(Path(report["text"]).is_file())
        self.assertTrue((self.base / "check" / "report.json").is_file())
        self.assertEqual(report["warnings"], [])

    def test_check_requires_install(self) -> None:
        with self.assertRaises(browser.BrowserError):
            self.manager.check("http://127.0.0.1:9999/")

    def test_remove(self) -> None:
        def fake_download(url: str, destination: Path, callback=None) -> None:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(self.payload)
        with self._patch_asset(), mock.patch.object(self.manager, "_downloader", side_effect=fake_download):
            self.manager.install(force=True)
        self.assertTrue(self.manager.remove())
        self.assertFalse(self.manager.status()["installed"])


class CliTests(unittest.TestCase):
    def test_browser_status_runs_offline(self) -> None:
        from stitchcraft import cli

        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"STITCHCRAFT_HOME": tmp}):
            output = io.StringIO()
            with redirect_stdout(output):
                code = cli.main(["browser", "status"])
        self.assertEqual(code, 0)
        self.assertIn("Obscura AI browser", output.getvalue())


class SettingsTests(unittest.TestCase):
    def test_browser_settings_roundtrip(self) -> None:
        from stitchcraft.settings import AppConfig

        config = AppConfig()
        self.assertTrue(config.browser.auto_check)
        config.merge_patch({"browser": {"auto_check": False, "allow_private_network": False}})
        self.assertFalse(config.browser.auto_check)
        self.assertFalse(config.browser.allow_private_network)
        public = config.public_dict()["browser"]
        self.assertFalse(public["auto_check"])


if __name__ == "__main__":
    unittest.main()
