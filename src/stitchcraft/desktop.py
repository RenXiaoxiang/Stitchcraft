"""Desktop launcher for the Stitchcraft studio.

`python -m stitchcraft app` starts the local server and opens the UI in an Edge
`--app` window (a chromeless desktop window). If Edge is missing it falls back
to the default browser. `--smoke-test` runs the server headlessly and exercises
the API end-to-end, which is what CI and the Kiro desktop hook use.
"""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

from . import __version__, settings
from .server import make_server

EDGE_CANDIDATES = (
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
)
CHROME_CANDIDATES = (
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
)

BANNER = r"""
   _____ __  _     __        __
  / ___// /_(_)___/ /_____  / /_  ___________ ____  ____
  \__ \/ __/ / __/ __/ __ \/ __ \/ ___/ ___/ __ `/ __ \/ ___/
 ___/ / /_/ / /_/ /_/ /_/ / / / / /  / /__/ /_/ / /_/ / /__
/____/\__/_/\__/\__/\____/_/ /_/\___/\___/\__,_/ .___/\___/
                                              /_/
  Stitchcraft Studio — AI site builder with stitched skills
"""


def find_browser() -> Path | None:
    for candidate in (*EDGE_CANDIDATES, *CHROME_CANDIDATES):
        if candidate.is_file():
            return candidate
    return None


def pick_port(preferred: int = 8765) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", preferred))
            return preferred
        except OSError:
            pass
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def open_window(url: str) -> str:
    browser = find_browser()
    if browser is not None:
        profile = settings.app_dir() / "browser-profile"
        profile.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.Popen(
                [
                    str(browser),
                    f"--app={url}",
                    "--window-size=1440,920",
                    f"--user-data-dir={profile}",
                    "--disable-features=msEdgeSidebarV2",
                ],
                close_fds=True,
            )
            return browser.name
        except OSError:
            pass
    webbrowser.open(url)
    return "default browser"


def _request(url: str, method: str = "GET", payload: dict | None = None, timeout: float = 30.0):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read()
        return response.status, body


def _request_json(url: str, method: str = "GET", payload: dict | None = None, timeout: float = 30.0):
    status, body = _request(url, method, payload, timeout)
    return status, json.loads(body.decode("utf-8")) if body else {}


def wait_ready(base_url: str, timeout: float = 20.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            status, payload = _request_json(f"{base_url}/api/status", timeout=2.0)
            if status == 200 and payload.get("version"):
                return True
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
            time.sleep(0.25)
    return False


def _smoke_test(base_url: str, context) -> int:
    checks: list[tuple[str, bool, str]] = []

    status, payload = _request_json(f"{base_url}/api/status")
    checks.append(("api/status", status == 200 and bool(payload.get("version")), str(payload.get("version"))))
    status, payload = _request_json(f"{base_url}/api/themes")
    theme_count = len(payload.get("themes", []))
    checks.append(("api/themes", status == 200 and theme_count >= 5, f"{theme_count} themes"))
    status, payload = _request_json(f"{base_url}/api/skills")
    skill_count = len(payload.get("skills", []))
    checks.append(("api/skills", status == 200 and skill_count >= 5, f"{skill_count} skills"))
    status, payload = _request_json(f"{base_url}/api/libraries")
    library_count = len(payload.get("libraries", []))
    checks.append(("api/libraries", status == 200 and library_count >= 6, f"{library_count} libraries"))
    status, payload = _request_json(f"{base_url}/api/browser")
    browser_installed = bool(payload.get("installed"))
    checks.append(
        (
            "api/browser",
            status == 200 and bool(payload.get("version")),
            f"Obscura {payload.get('version')}: {'installed' if browser_installed else 'not installed'}",
        )
    )
    status, payload = _request_json(f"{base_url}/api/settings")
    checks.append(("api/settings", status == 200 and "ai" in payload, ""))
    status, payload = _request_json(f"{base_url}/api/ai/providers")
    provider_count = len(payload.get("providers", []))
    checks.append(("api/ai/providers", status == 200 and provider_count >= 8, f"{provider_count} providers"))

    status, payload = _request_json(
        f"{base_url}/api/generate",
        "POST",
        {
            "theme_id": "warehouse-ops",
            "title": "Smoke test",
            "prompt": "Smoke test a warehouse operations dashboard with inventory CRUD.",
            "engine": "mock",
            "database": {"mode": "local", "remote": {}},
        },
    )
    job_id = payload.get("job_id")
    checks.append(("api/generate", status == 202 and bool(job_id), str(job_id)))
    if job_id:
        deadline = time.time() + 120
        job: dict = {}
        while time.time() < deadline:
            status, job = _request_json(f"{base_url}/api/jobs/{job_id}")
            if job.get("status") in {"done", "error"}:
                break
            time.sleep(0.4)
        checks.append(("job completed", job.get("status") == "done", job.get("status", "timeout")))
        project_id = job.get("project_id")
        if project_id:
            preview_base = base_url.replace("127.0.0.1", "localhost", 1)
            status, _body = _request(f"{preview_base}/api/preview/{project_id}/")
            checks.append(("preview served", status == 200, ""))
            status, _body = _request(f"{base_url}/api/export/{project_id}")
            checks.append(("export zip", status == 200, ""))
            _request(f"{base_url}/api/projects/{project_id}", "DELETE")
    failures = 0
    print()
    for name, ok, detail in checks:
        marker = "ok  " if ok else "FAIL"
        suffix = f" ({detail})" if detail else ""
        print(f"  [{marker}] {name}{suffix}")
        failures += 0 if ok else 1
    print()
    print("stitch app smoke-test: " + ("PASS" if failures == 0 else f"{failures} check(s) failed"))
    return 0 if failures == 0 else 1


def run(
    root: Path | None = None,
    port: int = 8765,
    open_window_enabled: bool = True,
    smoke_test: bool = False,
) -> int:
    actual_port = pick_port(port)
    try:
        httpd, context = make_server(root=root, port=actual_port)
    except OSError as exc:
        print(f"stitch: could not start the local server: {exc}", file=sys.stderr)
        return 2
    actual_port = int(httpd.server_address[1])
    base_url = f"http://127.0.0.1:{actual_port}"
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        if not wait_ready(base_url):
            print("stitch: the local server did not become ready.", file=sys.stderr)
            return 1
        if smoke_test:
            return _smoke_test(base_url, context)
        print(BANNER)
        print(f"  Local studio : {base_url}")
        print(f"  Config       : {settings.config_path()}")
        print(f"  Projects     : {context.store.base_dir}")
        print("  Press Ctrl+C to stop.")
        print()
        if open_window_enabled:
            target = open_window(base_url)
            print(f"  Opened the studio in: {target}")
        try:
            while thread.is_alive():
                thread.join(0.5)
        except KeyboardInterrupt:
            print("\nStopping Stitchcraft Studio...")
        return 0
    finally:
        httpd.shutdown()
        httpd.server_close()


if __name__ == "__main__":
    raise SystemExit(run())
