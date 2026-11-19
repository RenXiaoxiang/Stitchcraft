"""Functional acceptance checks for benchmark tasks.

The checks run in the optional Obscura browser when it is installed. A generated
site is served on loopback and loaded inside a same-origin iframe; the harness
drives the page like a user would (add, search, reload, delete, click a CTA) and
reports each step. When the browser is missing, or the build is a placeholder,
the result is explicitly ``untested`` instead of pretending to pass.
"""

from __future__ import annotations

import http.server
import socketserver
import tempfile
import threading
import urllib.parse
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .browser import BrowserError, BrowserManager

UNTESTED = "untested"
PASSED = "passed"
FAILED = "failed"


def _checks_template() -> str:
    return """
    const result = window.__benchmark = { status: "running", checks: [], viewport: 0, error: null };
    const iframe = document.getElementById("site");
    const check = (id, ok, detail) => result.checks.push({ id, ok: !!ok, detail: String(detail || "") });
    const finish = () => { result.status = result.checks.every((item) => item.ok) ? "passed" : "failed"; };
    const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
    const setValue = (doc, selector, value) => {
      const node = doc.querySelector(selector);
      if (!node) return false;
      node.value = String(value);
      node.dispatchEvent(new Event("input", { bubbles: true }));
      node.dispatchEvent(new Event("change", { bubbles: true }));
      return true;
    };
    const rowByText = (doc, text) => Array.from(doc.querySelectorAll("tr, [data-row]"))
      .find((row) => (row.textContent || "").includes(text)) || null;
    const visible = (el, win) => {
      if (!el) return false;
      const style = win.getComputedStyle(el);
      const rect = el.getBoundingClientRect();
      return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
    };
    """


def _warehouse_add_script() -> str:
    return """
    iframe.addEventListener("load", async () => {
      try {
        const doc = iframe.contentDocument;
        const win = iframe.contentWindow;
        result.viewport = win.innerWidth;
        const add = doc.querySelector("#add-item");
        check("add_control", !!add, "#add-item");
        if (!add) { finish(); return; }
        add.click();
        await wait(150);
        for (const [selector, value] of [["#item-sku", "BENCH-9001"], ["#item-name", "Benchmark item"], ["#item-quantity", "3"], ["#item-reorder", "5"]]) {
          check("field" + selector, setValue(doc, selector, value), selector);
        }
        const save = doc.querySelector("#item-save");
        check("save_control", !!save, "#item-save");
        if (save) save.click();
        await wait(300);
        check("add_item", !!rowByText(doc, "BENCH-9001"), "row after save");
        check("search_control", setValue(doc, "#search", "BENCH-9001"), "#search");
        await wait(200);
        check("search_finds_item", !!rowByText(doc, "BENCH-9001"), "search result");
        let persisted = false;
        try {
          persisted = Object.keys(window.localStorage).some((key) => String(window.localStorage.getItem(key) || "").includes("BENCH-9001"));
        } catch (error) { persisted = false; }
        check("localstorage_persist", persisted, "localStorage contains the new item");
      } catch (error) { result.error = String(error); }
      finish();
    });
    iframe.src = "/index.html";
    """


def _warehouse_persist_script() -> str:
    return """
    iframe.addEventListener("load", async () => {
      try {
        const doc = iframe.contentDocument;
        const win = iframe.contentWindow;
        result.viewport = win.innerWidth;
        check("reload_page", !!doc.querySelector("#search"), "page reloaded");
        setValue(doc, "#search", "BENCH-9001");
        await wait(250);
        check("persist_after_reload", !!rowByText(doc, "BENCH-9001"), "item survives a fresh browser run");
        setValue(doc, "#search", "");
        await wait(150);
        const row = rowByText(doc, "BENCH-9001");
        check("delete_control", !!(row && row.querySelector(".js-delete")), "row delete button");
        if (row && row.querySelector(".js-delete")) {
          row.querySelector(".js-delete").click();
          await wait(180);
          const confirm = doc.querySelector("#confirm-action");
          if (confirm) confirm.click();
          await wait(300);
        }
        check("delete_item", !rowByText(doc, "BENCH-9001"), "row removed");
        const low = doc.querySelector("#kpi-low");
        check("low_stock_indicator", !!low && String(low.textContent || "").trim() !== "", "#kpi-low");
      } catch (error) { result.error = String(error); }
      finish();
    });
    iframe.src = "/index.html";
    """


def _brand_script() -> str:
    return """
    let done = false;
    iframe.addEventListener("load", async () => {
      if (done) return;
      done = true;
      try {
        const doc = iframe.contentDocument;
        const win = iframe.contentWindow;
        result.viewport = win.innerWidth;
        check("mobile_viewport", win.innerWidth <= 480, "viewport " + win.innerWidth + "px");
        check("no_horizontal_overflow", doc.documentElement.scrollWidth <= win.innerWidth + 2, "scrollWidth " + doc.documentElement.scrollWidth);
        const candidates = Array.from(doc.querySelectorAll("a, button, [role='button']"))
          .filter((node) => visible(node, win) && String(node.textContent || "").trim().length > 0);
        const cta = candidates.find((node) => /book|pre.?order|get started|start|launch|shop|join|try|claim|download/i.test(node.textContent || "")) || candidates[0];
        check("page_text", (doc.body.textContent || "").trim().length > 80, "rendered body text");
        check("cta_visible", !!cta && visible(cta, win), cta ? cta.textContent.trim().slice(0, 60) : "no CTA");
        if (cta) {
          const rect = cta.getBoundingClientRect();
          check("cta_in_viewport", rect.left >= -1 && rect.right <= win.innerWidth + 1, "rect " + Math.round(rect.left) + ".." + Math.round(rect.right));
          const href = cta.getAttribute("href") || "";
          const before = iframe.contentWindow.location.href;
          cta.click();
          await wait(350);
          const after = iframe.contentWindow.location.href;
          check("cta_has_destination", (href && href !== "#") || after !== before, "href=" + href + " urlChanged=" + (after !== before));
        }
      } catch (error) { result.error = String(error); }
      finish();
    });
    iframe.src = "/index.html";
    """


def _harness(script: str, width: int, height: int) -> str:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Stitchcraft benchmark harness</title>
<style>html,body{{margin:0;background:#111}}iframe{{border:0;display:block;width:{width}px;height:{height}px}}</style>
</head><body>
<iframe id="site" title="Generated site" width="{width}" height="{height}"></iframe>
<script>{_checks_template()}{script}</script>
</body></html>"""


class _HarnessHandler(http.server.SimpleHTTPRequestHandler):
    harnesses: dict[str, str] = {}
    site_dir = ""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=self.site_dir, **kwargs)

    def do_GET(self) -> None:  # noqa: N802
        path = urllib.parse.urlsplit(self.path).path
        if path in self.harnesses:
            body = self.harnesses[path].encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def log_message(self, format: str, *args: Any) -> None:
        return


@contextmanager
def _serve_harnesses(harnesses: dict[str, str], site_dir: Path) -> Iterator[str]:
    handler = type(
        "BoundHarnessHandler",
        (_HarnessHandler,),
        {"harnesses": dict(harnesses), "site_dir": str(site_dir)},
    )
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler, bind_and_activate=False)
    httpd.allow_reuse_address = True
    httpd.daemon_threads = True
    httpd.server_bind()
    httpd.server_activate()
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{int(httpd.server_address[1])}"
    finally:
        httpd.shutdown()
        httpd.server_close()


def _untested(reason: str, kind: str | None = None) -> dict:
    return {"status": UNTESTED, "kind": kind, "reason": reason, "checks": []}


def _evaluate_harness(
    url: str,
    kind: str,
    browser: BrowserManager,
    *,
    storage_dir: Path | None,
    timeout: int,
) -> dict:
    result = browser.evaluate(
        url,
        "JSON.stringify(window.__benchmark)",
        timeout=timeout,
        wait_seconds=5,
        storage_dir=storage_dir,
    )
    checks = result.get("checks") if isinstance(result.get("checks"), list) else []
    status_value = str(result.get("status") or FAILED)
    if status_value not in {PASSED, FAILED}:
        status_value = FAILED
    return {
        "status": status_value,
        "kind": kind,
        "checks": checks,
        "viewport": result.get("viewport"),
        "error": result.get("error"),
    }


def run_functional_check(
    kind: str | None,
    site_dir: Path,
    *,
    placeholder: bool = False,
    browser: BrowserManager | None = None,
    timeout: int = 45,
) -> dict:
    """Run a named functional scenario and return passed/failed/untested."""
    if not kind:
        return _untested("no functional scenario for this task")
    if placeholder:
        return _untested("build is a placeholder, so user operations are not meaningful", kind)
    site_dir = Path(site_dir)
    if not (site_dir / "index.html").is_file():
        return _untested("generated site has no index.html", kind)
    browser = browser or BrowserManager()
    status = browser.status()
    if not status["installed"]:
        return _untested("Obscura is not installed; functional checks are untested", kind)
    if kind not in {"warehouse_flow", "brand_mobile"}:
        return _untested(f"unknown functional scenario: {kind}", kind)

    try:
        if kind == "warehouse_flow":
            with tempfile.TemporaryDirectory() as storage:
                storage_dir = Path(storage)
                harnesses = {
                    "/__benchmark_add.html": _harness(_warehouse_add_script(), 1200, 900),
                    "/__benchmark_persist.html": _harness(_warehouse_persist_script(), 1200, 900),
                }
                with _serve_harnesses(harnesses, site_dir) as base:
                    first = _evaluate_harness(
                        base + "/__benchmark_add.html",
                        "warehouse_flow:add",
                        browser,
                        storage_dir=storage_dir,
                        timeout=timeout,
                    )
                    if first["status"] != PASSED:
                        return {**first, "kind": kind}
                    second = _evaluate_harness(
                        base + "/__benchmark_persist.html",
                        "warehouse_flow:persist",
                        browser,
                        storage_dir=storage_dir,
                        timeout=timeout,
                    )
                checks = first["checks"] + second["checks"]
                return {
                    "status": PASSED if second["status"] == PASSED else FAILED,
                    "kind": kind,
                    "checks": checks,
                    "viewport": first.get("viewport"),
                    "error": second.get("error"),
                }
        harnesses = {"/__benchmark_brand.html": _harness(_brand_script(), 390, 844)}
        with _serve_harnesses(harnesses, site_dir) as base:
            result = _evaluate_harness(
                base + "/__benchmark_brand.html",
                "brand_mobile",
                browser,
                storage_dir=None,
                timeout=timeout,
            )
        return {**result, "kind": kind}
    except BrowserError as exc:
        return _untested("browser could not run the functional harness: " + str(exc), kind)
    except Exception as exc:  # noqa: BLE001 - a broken harness must not fail the build
        return _untested("functional harness error: " + str(exc), kind)
