"""Optional Obscura browser sidecar for AI site checks.

Stitchcraft never ships a browser runtime. On first use the studio can download
the pinned, Apache-2.0 licensed Obscura release into the user's app-data
directory and drive it locally through its CLI:

* ``obscura fetch`` renders a generated page, dumps its text and captures a PNG;
* the same call is what the studio uses to verify a freshly generated site when
  the customer's machine has no modern Chrome/Edge installed.

Everything here is Python standard library only. The runtime is a downloadable
state, not a package dependency: no import of Obscura, no network call unless
the user explicitly installs or checks.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from . import settings

OBSCURA_VERSION = "0.2.7"
OBSCURA_UPSTREAM = "https://github.com/h4ckf0r0day/obscura"
OBSCURA_RELEASE_BASE = f"https://github.com/h4ckf0r0day/obscura/releases/download/v{OBSCURA_VERSION}"
OBSCURA_LICENSE = "Apache-2.0"
OBSCURA_MIRROR_ENV = "STITCHCRAFT_BROWSER_MIRROR"

# Release 0.2.7 assets (rendering build, no stealth). Digests come from the
# GitHub release API for this exact tag; changing the version means updating
# these together with the tests.
ASSETS: dict[str, dict[str, object]] = {
    "windows-x86_64": {
        "asset": "obscura-x86_64-windows.zip",
        "archive": "zip",
        "size": 72_427_564,
        "sha256": "be983b663552e11faf8c1e07696578bad622dbeb48afb9f59036032ca8e97fb3",
    },
    "linux-x86_64": {
        "asset": "obscura-x86_64-linux.tar.gz",
        "archive": "tar.gz",
        "size": 72_018_118,
        "sha256": "11b53d27cd743e00e196e216920e7f3f794cf378e3f1792b8d25d3beabaf9cad",
    },
    "linux-aarch64": {
        "asset": "obscura-aarch64-linux.tar.gz",
        "archive": "tar.gz",
        "size": 69_952_302,
        "sha256": "4ee0aeeb38fa8bb2cb004ba104abe1c79f1bdfd02f51672c694e8234a5ae0e5c",
    },
    "macos-x86_64": {
        "asset": "obscura-x86_64-macos.tar.gz",
        "archive": "tar.gz",
        "size": 69_818_596,
        "sha256": "c47383e5b5551e09d2055ee7bdcce788af409fb4394e39bdaf179734df18e829",
    },
    "macos-aarch64": {
        "asset": "obscura-aarch64-macos.tar.gz",
        "archive": "tar.gz",
        "size": 67_612_634,
        "sha256": "fc7e73f23058f18d6d5be983d83b24ba374d12167677657a307a9476c0f5a7c1",
    },
}

PLATFORM_LABELS = {
    "windows-x86_64": "Windows x86_64",
    "linux-x86_64": "Linux x86_64",
    "linux-aarch64": "Linux aarch64",
    "macos-x86_64": "macOS Intel",
    "macos-aarch64": "macOS Apple silicon",
}

METRICS_JS = (
    "(() => {"
    "const links=[...document.querySelectorAll('a[href]')].map(a=>a.getAttribute('href')||'');"
    "const anchors=links.filter(h=>h.startsWith('#')).map(h=>h.slice(1)).filter(Boolean);"
    "const missing=anchors.filter(id=>!document.getElementById(id)&&!document.getElementsByName(id).length);"
    "const images=[...document.images];"
    "return JSON.stringify({"
    "title:document.title||'',"
    "lang:document.documentElement.getAttribute('lang')||'',"
    "h1:document.querySelectorAll('h1').length,"
    "textChars:(document.body?document.body.innerText:'').length,"
    "links:{total:links.length,external:links.filter(h=>/^https?:/i.test(h)).length,"
    "anchors:anchors.length,empty:links.filter(h=>!h.trim()||h==='#').length},"
    "missingAnchors:missing.slice(0,20),"
    "images:{total:images.length,missingAlt:images.filter(i=>!i.getAttribute('alt')).length},"
    "forms:document.querySelectorAll('form').length,"
    "buttons:document.querySelectorAll('button,[role=\"button\"]').length,"
    "landmarks:{main:document.querySelectorAll('main').length,nav:document.querySelectorAll('nav').length}"
    "});})()"
)

METRICS_KEYS = ("title", "lang", "h1", "textChars", "links", "missingAnchors", "images", "forms", "buttons", "landmarks")


class BrowserError(RuntimeError):
    """Raised when the optional browser cannot be installed or driven."""


def platform_key(system: str | None = None, machine: str | None = None) -> str | None:
    """Map the current machine to an Obscura release asset family."""
    system = (system or sys.platform).lower()
    machine = (machine or platform.machine()).lower()
    if system.startswith("win"):
        if machine in {"amd64", "x86_64"}:
            return "windows-x86_64"
        return None
    if system == "darwin":
        if machine in {"arm64", "aarch64"}:
            return "macos-aarch64"
        if machine in {"x86_64", "amd64"}:
            return "macos-x86_64"
        return None
    if system.startswith("linux"):
        if machine in {"aarch64", "arm64"}:
            return "linux-aarch64"
        if machine in {"x86_64", "amd64"}:
            return "linux-x86_64"
        return None
    return None


def asset_for(key: str | None) -> dict[str, object] | None:
    if not key:
        return None
    entry = ASSETS.get(key)
    if entry is None:
        return None
    return dict(entry)


def download_url(entry: dict[str, object], mirror: str | None = None) -> str:
    """Direct release URL, optionally rewritten through a user mirror prefix.

    A mirror may be a plain prefix (``https://gh-proxy.com``) or a template
    containing ``{url}`` for the complete GitHub URL.
    """
    direct = f"{OBSCURA_RELEASE_BASE}/{entry['asset']}"
    if not mirror:
        return direct
    mirror = str(mirror).strip()
    if "{url}" in mirror:
        return mirror.replace("{url}", direct)
    return mirror.rstrip("/") + "/" + direct


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_member(name: str) -> bool:
    candidate = name.replace("\\", "/")
    if candidate.startswith("/") or re.match(r"^[A-Za-z]:", candidate):
        return False
    return not any(part == ".." for part in candidate.split("/"))


def _extract_zip(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with zipfile.ZipFile(archive) as bundle:
        for info in bundle.infolist():
            if not _safe_member(info.filename):
                raise BrowserError(f"Unsafe path in browser archive: {info.filename!r}")
            target = (destination / info.filename).resolve()
            if not target.is_relative_to(root):
                raise BrowserError(f"Unsafe path in browser archive: {info.filename!r}")
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(info) as source, target.open("wb") as sink:
                shutil.copyfileobj(source, sink)


def _extract_tar(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with tarfile.open(archive, "r:gz") as bundle:
        for member in bundle.getmembers():
            if member.issym() or member.islnk():
                raise BrowserError(f"Links are not allowed in the browser archive: {member.name!r}")
            if not _safe_member(member.name):
                raise BrowserError(f"Unsafe path in browser archive: {member.name!r}")
            target = (destination / member.name).resolve()
            if not target.is_relative_to(root):
                raise BrowserError(f"Unsafe path in browser archive: {member.name!r}")
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            if not member.isfile():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            source = bundle.extractfile(member)
            if source is None:
                raise BrowserError(f"Could not read {member.name!r} from the browser archive")
            with source, target.open("wb") as sink:
                shutil.copyfileobj(source, sink)


def _find_binary(root: Path) -> Path | None:
    names = ("obscura.exe", "obscura")
    for name in names:
        direct = root / name
        if direct.is_file():
            return direct
    for name in names:
        for candidate in root.rglob(name):
            if candidate.is_file():
                return candidate
    return None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _tail(text: str, limit: int = 600) -> str:
    text = (text or "").strip()
    return text[-limit:] if len(text) > limit else text


class BrowserManager:
    """Install, inspect and drive the optional Obscura runtime."""

    def __init__(
        self,
        base_dir: Path | None = None,
        *,
        system: str | None = None,
        machine: str | None = None,
        runner: Callable[[list[str], float], object] | None = None,
        downloader: Callable[[str, Path, Callable[[int, int], None] | None], None] | None = None,
        mirror: str | None = None,
    ) -> None:
        self.base_dir = Path(base_dir) if base_dir is not None else settings.app_dir() / "browser"
        self._system = system
        self._machine = machine
        self.mirror = (mirror if mirror is not None else os.environ.get(OBSCURA_MIRROR_ENV)) or None
        self._runner = runner or self._default_runner
        self._downloader = downloader or self._default_download
        self.install_dir = self.base_dir / f"obscura-{OBSCURA_VERSION}"
        self.manifest_path = self.base_dir / "install.json"
        self.checks_dir = self.base_dir / "checks"

    # -- state ---------------------------------------------------------------
    @property
    def platform(self) -> str | None:
        return platform_key(self._system, self._machine)

    @property
    def entry(self) -> dict[str, object] | None:
        return asset_for(self.platform)

    def _read_manifest(self) -> dict:
        try:
            data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}
        return data if isinstance(data, dict) else {}

    def binary_path(self) -> Path | None:
        manifest = self._read_manifest()
        relative = manifest.get("binary")
        if not isinstance(relative, str) or not relative:
            return None
        candidate = (self.install_dir / relative).resolve()
        if not candidate.is_relative_to(self.install_dir.resolve()):
            return None
        return candidate if candidate.is_file() else None

    def status(self) -> dict:
        entry = self.entry
        manifest = self._read_manifest()
        binary = self.binary_path()
        installed = binary is not None and manifest.get("version") == OBSCURA_VERSION
        supported = entry is not None
        return {
            "supported": supported,
            "platform": self.platform,
            "platform_label": PLATFORM_LABELS.get(self.platform or "", self.platform or ""),
            "version": OBSCURA_VERSION,
            "license": OBSCURA_LICENSE,
            "upstream": OBSCURA_UPSTREAM,
            "asset": (entry or {}).get("asset"),
            "download_url": download_url(entry, self.mirror) if entry else None,
            "mirror": self.mirror,
            "download_bytes": int((entry or {}).get("size", 0)),
            "sha256": (entry or {}).get("sha256"),
            "installed": bool(installed),
            "installed_version": manifest.get("version"),
            "binary": str(binary) if binary else None,
            "install_dir": str(self.install_dir) if installed else None,
            "installed_at": manifest.get("installed_at"),
            "missing_reason": None if supported else "Obscura has no release for this platform/architecture.",
        }

    # -- network / extraction ------------------------------------------------
    def _default_runner(self, command: list[str], timeout: float) -> object:
        flags = 0x08000000 if sys.platform == "win32" else 0  # CREATE_NO_WINDOW
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=flags,
        )

    def _default_download(
        self,
        url: str,
        destination: Path,
        progress: Callable[[int, int], None] | None = None,
    ) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "Stitchcraft/0.4 (+https://github.com/RenXiaoxiang/Stitchcraft)"},
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as sink:
                total = int(response.headers.get("Content-Length") or 0)
                done = 0
                if progress:
                    progress(0, total)
                while True:
                    chunk = response.read(1024 * 256)
                    if not chunk:
                        break
                    sink.write(chunk)
                    done += len(chunk)
                    if progress:
                        progress(done, total)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            destination.unlink(missing_ok=True)
            raise BrowserError(
                "Could not download Obscura: "
                f"{exc}. If GitHub is slow or blocked, set {OBSCURA_MIRROR_ENV} "
                "(for example https://gh-proxy.com) and run the install again."
            ) from exc

    def _write_sidecar_files(self) -> None:
        data_dir = Path(__file__).resolve().parent / "data"
        license_source = data_dir / "obscura-LICENSE.txt"
        notice_source = data_dir / "obscura-NOTICE.txt"
        if license_source.is_file():
            shutil.copyfile(license_source, self.install_dir / "LICENSE")
        if notice_source.is_file():
            shutil.copyfile(notice_source, self.install_dir / "NOTICE")

    def install(self, progress: Callable[[int, int], None] | None = None, force: bool = False) -> dict:
        platform_name = self.platform
        entry = self.entry
        if entry is None:
            raise BrowserError(
                "Obscura does not publish a build for this platform/architecture. "
                "Use a 64-bit Windows, Linux or macOS machine, or keep the system browser fallback."
            )
        if self.status()["installed"] and not force:
            return self.status()

        self.base_dir.mkdir(parents=True, exist_ok=True)
        download_dir = self.base_dir / "downloads"
        download_dir.mkdir(parents=True, exist_ok=True)
        archive = download_dir / str(entry["asset"])
        expected = str(entry["sha256"]).lower()
        url = download_url(entry, self.mirror)

        if not archive.is_file() or _sha256_file(archive) != expected:
            archive.unlink(missing_ok=True)
            part = archive.with_suffix(archive.suffix + ".part")
            self._downloader(url, part, progress)
            if _sha256_file(part) != expected:
                part.unlink(missing_ok=True)
                raise BrowserError("The downloaded Obscura archive failed its SHA-256 check.")
            part.replace(archive)

        staging = self.base_dir / f"staging-{uuid.uuid4().hex[:8]}"
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        try:
            if entry["archive"] == "zip":
                _extract_zip(archive, staging)
            else:
                _extract_tar(archive, staging)
            binary = _find_binary(staging)
            if binary is None:
                raise BrowserError("The Obscura archive did not contain an obscura executable.")
            if sys.platform != "win32":
                binary.chmod(0o755)
            completed = self._runner([str(binary), "--version"], 20)
            if int(getattr(completed, "returncode", 1)) != 0:
                raise BrowserError(
                    "The downloaded Obscura binary could not start: "
                    + _tail(str(getattr(completed, "stderr", "") or getattr(completed, "stdout", "")))
                )
            if force:
                shutil.rmtree(self.install_dir, ignore_errors=True)
            if self.install_dir.exists():
                shutil.rmtree(self.install_dir, ignore_errors=True)
            shutil.move(str(staging), str(self.install_dir))
            installed_binary = _find_binary(self.install_dir)
            if installed_binary is None:
                raise BrowserError("Obscura extraction finished without an executable.")
            self._write_sidecar_files()
            relative = installed_binary.relative_to(self.install_dir).as_posix()
            manifest = {
                "version": OBSCURA_VERSION,
                "platform": platform_name,
                "asset": entry["asset"],
                "sha256": expected,
                "installed_at": _now(),
                "binary": relative,
                "install_dir": str(self.install_dir),
            }
            self.manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            version_output = (str(getattr(completed, "stdout", "")) or str(getattr(completed, "stderr", ""))).strip()
            if version_output:
                (self.install_dir / "VERSION").write_text(version_output + "\n", encoding="utf-8")
            return self.status()
        finally:
            shutil.rmtree(staging, ignore_errors=True)

    def remove(self) -> bool:
        removed = False
        for target in (self.install_dir, self.base_dir / "downloads", self.checks_dir):
            if target.exists():
                shutil.rmtree(target, ignore_errors=True)
                removed = True
        self.manifest_path.unlink(missing_ok=True)
        return removed

    # -- checks --------------------------------------------------------------
    def _fetch(self, binary: Path, arguments: list[str], timeout: float) -> object:
        command = [str(binary), "fetch", *arguments]
        completed = self._runner(command, timeout)
        if int(getattr(completed, "returncode", 1)) != 0:
            raise BrowserError(
                "Obscura could not render the page: "
                + _tail(str(getattr(completed, "stderr", "") or getattr(completed, "stdout", "")))
            )
        return completed

    @staticmethod
    def _parse_metrics(output: str) -> dict:
        raw = (output or "").strip()
        if not raw:
            return {}
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            start = raw.find("{")
            end = raw.rfind("}")
            if start < 0 or end <= start:
                return {}
            try:
                value = json.loads(raw[start : end + 1])
            except json.JSONDecodeError:
                return {}
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                return {}
        if not isinstance(value, dict):
            return {}
        return {key: value.get(key) for key in METRICS_KEYS if key in value}

    def check(
        self,
        url: str,
        out_dir: Path | None = None,
        *,
        timeout: int = 30,
        screenshot: bool = True,
        allow_private_network: bool = True,
    ) -> dict:
        status = self.status()
        if not status["installed"]:
            raise BrowserError("Obscura is not installed yet. Run `stitch browser install` or install it in the studio.")
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise BrowserError(f"Browser checks need an http(s) URL, got {url!r}.")
        binary = Path(str(status["binary"]))
        target = Path(out_dir) if out_dir is not None else self.checks_dir / uuid.uuid4().hex[:12]
        target.mkdir(parents=True, exist_ok=True)
        text_path = target / "page.txt"
        shot_path = target / "screenshot.png"
        started = time.perf_counter()

        common = ["--wait-until", "networkidle0", "--timeout", str(max(5, int(timeout))), "--quiet"]
        if allow_private_network:
            common.append("--allow-private-network")
        # `--dump` and `--screenshot` are separate operations in Obscura: combining
        # them silently drops the dump, so run text extraction and capture apart.
        self._fetch(binary, [url, "--dump", "text", "--output", str(text_path), *common], timeout + 30)
        if screenshot:
            self._fetch(binary, [url, "--screenshot", str(shot_path), *common], timeout + 30)

        metrics: dict = {}
        try:
            completed = self._fetch(
                binary,
                [url, "--eval", METRICS_JS, *common],
                timeout + 30,
            )
            metrics = self._parse_metrics(str(getattr(completed, "stdout", "")))
        except BrowserError:
            metrics = {}

        text = text_path.read_text(encoding="utf-8", errors="replace") if text_path.is_file() else ""
        title = str(metrics.get("title") or "")
        lang = str(metrics.get("lang") or "")
        h1 = int(metrics.get("h1") or 0)
        text_chars = int(metrics.get("textChars") or len(text))
        links = metrics.get("links") if isinstance(metrics.get("links"), dict) else {}
        images = metrics.get("images") if isinstance(metrics.get("images"), dict) else {}
        missing_anchors = metrics.get("missingAnchors") if isinstance(metrics.get("missingAnchors"), list) else []
        warnings: list[str] = []
        critical: list[str] = []
        if not title:
            critical.append("The page has no <title>.")
        if h1 == 0:
            critical.append("The page has no <h1>.")
        elif h1 > 1:
            warnings.append(f"The page has {h1} <h1> elements; keep one primary heading.")
        if text_chars < 120:
            warnings.append("Very little readable text was rendered.")
        if not lang:
            warnings.append('The <html> element has no lang attribute.')
        missing_alt = int(images.get("missingAlt") or 0)
        if missing_alt:
            warnings.append(f"{missing_alt} image(s) are missing alt text.")
        if int(links.get("empty") or 0):
            warnings.append(f"{int(links.get('empty') or 0)} link(s) have an empty href.")
        if missing_anchors:
            warnings.append("Missing in-page anchors: " + ", ".join("#" + str(item) for item in missing_anchors[:5]))
        screenshot_path = shot_path if shot_path.is_file() else None
        if screenshot and screenshot_path is None:
            warnings.append("The screenshot was not produced.")
        report = {
            "ok": not critical,
            "url": url,
            "checked_at": _now(),
            "duration_ms": int((time.perf_counter() - started) * 1000),
            "browser": {"name": "Obscura", "version": OBSCURA_VERSION, "license": OBSCURA_LICENSE},
            "title": title,
            "lang": lang,
            "h1": h1,
            "text_chars": text_chars,
            "links": links,
            "missing_anchors": missing_anchors,
            "images": images,
            "warnings": warnings,
            "critical": critical,
            "screenshot": str(screenshot_path) if screenshot_path else None,
            "text": str(text_path) if text_path.is_file() else None,
            "out_dir": str(target),
        }
        (target / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return report

    def evaluate(
        self,
        url: str,
        expression: str,
        *,
        timeout: int = 30,
        wait_seconds: float = 2.0,
        allow_private_network: bool = True,
        storage_dir: Path | None = None,
    ) -> dict:
        """Run one JavaScript expression after a page settles and return its object."""
        status = self.status()
        if not status["installed"]:
            raise BrowserError("Obscura is not installed yet. Run `stitch browser install` or install it in the studio.")
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise BrowserError(f"Browser evaluation needs an http(s) URL, got {url!r}.")
        command = [
            str(status["binary"]),
            "fetch",
            url,
            "--eval",
            expression,
            "--wait",
            str(int(max(0, float(wait_seconds)))),
            "--wait-until",
            "networkidle0",
            "--timeout",
            str(max(5, int(timeout))),
            "--quiet",
        ]
        if storage_dir is not None:
            command.extend(["--storage-dir", str(Path(storage_dir))])
        if allow_private_network:
            command.append("--allow-private-network")
        completed = self._runner(command, timeout + 30)
        if int(getattr(completed, "returncode", 1)) != 0:
            raise BrowserError(
                "Obscura could not evaluate the page: "
                + _tail(str(getattr(completed, "stderr", "") or getattr(completed, "stdout", "")))
            )
        raw = str(getattr(completed, "stdout", "") or "").strip()
        if not raw:
            raise BrowserError("Obscura returned an empty evaluation result.")
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            start, end = raw.find("{"), raw.rfind("}")
            if start < 0 or end <= start:
                raise BrowserError(f"Obscura returned non-JSON evaluation output: {raw[:200]!r}")
            try:
                value = json.loads(raw[start : end + 1])
            except json.JSONDecodeError as exc:
                raise BrowserError(f"Obscura returned invalid JSON: {raw[:200]!r}") from exc
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                pass
        if not isinstance(value, dict):
            raise BrowserError("The browser evaluation did not return a JSON object.")
        return value

    # -- manual commands -----------------------------------------------------
    def serve_command(
        self,
        port: int = 9222,
        *,
        allow_private_network: bool = True,
        stealth: bool = False,
        workers: int = 1,
    ) -> list[str]:
        status = self.status()
        if not status["installed"]:
            raise BrowserError("Obscura is not installed yet. Run `stitch browser install` first.")
        command = [str(status["binary"]), "serve", "--port", str(int(port))]
        if allow_private_network:
            command.append("--allow-private-network")
        if stealth:
            command.append("--stealth")
        if workers and int(workers) > 1:
            command.extend(["--workers", str(int(workers))])
        return command

    def mcp_command(self, *, http_port: int | None = None, stealth: bool = False) -> list[str]:
        status = self.status()
        if not status["installed"]:
            raise BrowserError("Obscura is not installed yet. Run `stitch browser install` first.")
        command = [str(status["binary"]), "mcp"]
        if http_port:
            command.extend(["--http", "--port", str(int(http_port))])
        if stealth:
            command.append("--stealth")
        return command
