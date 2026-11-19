"""Functional acceptance checks for benchmark tasks.

The checks run in the optional Obscura browser when it is installed. A generated
site is served on loopback and loaded inside a same-origin iframe; the harness
drives the page like a user would (add, filter, reload, delete, click a CTA) and
reports each step. When the browser is missing, or the build is a placeholder,
the result is explicitly ``untested`` instead of pretending to pass.

A pass requires all three: no harness exception, every expected step was
reached, and every recorded check succeeded. The Python status evaluator
re-checks this contract even if the browser returns a misleading status.
"""

from __future__ import annotations

import http.server
import json
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

WAREHOUSE_ADD_REQUIRED = (
    "add_control",
    "field_sku",
    "field_name",
    "field_quantity",
    "field_reorder",
    "save_control",
    "add_first",
    "add_second",
    "search_control",
    "search_target_visible",
    "search_other_filtered",
    "localstorage_persist",
)
WAREHOUSE_PERSIST_REQUIRED = (
    "reload_page",
    "persist_search_control",
    "persist_target_visible",
    "persist_other_filtered",
    "delete_control",
    "delete_item",
    "low_stock_indicator",
)
BRAND_REQUIRED = (
    "mobile_viewport",
    "no_horizontal_overflow",
    "page_text",
    "cta_visible",
    "cta_in_viewport",
    "cta_has_destination",
)


def _checks_template(required: tuple[str, ...] | list[str]) -> str:
    required_json = json.dumps(list(required))
    return """
    const result = window.__benchmark = {
      status: "running", checks: [], required: __REQUIRED__, viewport: 0,
      phase: "start", error: null, failedChecks: [], missingChecks: [], interruptedAt: null
    };
    const iframe = document.getElementById("site");
    const phase = (name) => { result.phase = name; };
    const check = (id, ok, detail) => result.checks.push({ id, ok: !!ok, detail: String(detail || "") });
    const finish = () => {
      const failed = result.checks.filter((item) => !item.ok).map((item) => item.id);
      const passed = new Set(result.checks.filter((item) => item.ok).map((item) => item.id));
      const missing = result.required.filter((id) => !passed.has(id));
      result.failedChecks = failed;
      result.missingChecks = missing;
      result.status = (!result.error && !failed.length && !missing.length) ? "passed" : "failed";
      result.interruptedAt = (result.error || result.status === "failed") ? result.phase : null;
    };
    const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
    const testId = (doc, id) => doc.querySelector('[data-testid="' + id + '"]');
    const text = (node) => String((node && node.textContent) || "").trim();
    const labelFor = (node) => {
      if (!node || !node.ownerDocument) return "";
      const id = node.getAttribute("id");
      const label = id ? node.ownerDocument.querySelector('label[for="' + id + '"]') : null;
      return text(label);
    };
    const nameOf = (node) => [
      node.getAttribute("aria-label") || "",
      node.getAttribute("name") || "",
      node.getAttribute("placeholder") || "",
      node.getAttribute("id") || "",
      labelFor(node),
      text(node)
    ].join(" ").toLowerCase();
    const visible = (el, win) => {
      if (!el) return false;
      const style = win.getComputedStyle(el);
      const rect = el.getBoundingClientRect();
      return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
    };
    const findButton = (doc, pattern, root) => Array.from((root || doc).querySelectorAll(
      'button, [role="button"], input[type="submit"], a'
    )).find((node) => !node.disabled && pattern.test(nameOf(node)));
    const findField = (doc, pattern, root) => Array.from((root || doc).querySelectorAll(
      "input, select, textarea"
    )).find((node) => !node.disabled && pattern.test(nameOf(node)));
    const findText = (doc, pattern) => Array.from(doc.querySelectorAll("p, span, dd, dt, li, strong, small"))
      .find((node) => pattern.test(text(node).toLowerCase()));
    const dialogButton = (doc, pattern) => {
      const dialog = doc.querySelector("dialog[open], [role='dialog']");
      return dialog ? findButton(doc, pattern, dialog) : null;
    };
    const setValue = (node, value) => {
      if (!node) return false;
      node.value = String(value);
      node.dispatchEvent(new Event("input", { bubbles: true }));
      node.dispatchEvent(new Event("change", { bubbles: true }));
      return true;
    };
    const rowByText = (doc, value) => Array.from(doc.querySelectorAll("tbody tr, [data-row], [data-testid='item-row']"))
      .find((row) => String(row.textContent || "").includes(value)) || null;
    const rowVisible = (doc, value) => {
      const row = rowByText(doc, value);
      if (!row) return false;
      const style = doc.defaultView.getComputedStyle(row);
      const rect = row.getBoundingClientRect();
      return style.display !== "none" && style.visibility !== "hidden" && rect.height > 0;
    };
    const rowButton = (row, pattern) => findButton(row.ownerDocument, pattern, row);
    const control = (doc, id, pattern, field) => (field ? testId(doc, id) : testId(doc, id)) ||
      (field ? findField(doc, pattern) : findButton(doc, pattern));
    """.replace("__REQUIRED__", required_json)


def _warehouse_add_script() -> str:
    return """
    iframe.addEventListener("load", async () => {
      try {
        const doc = iframe.contentDocument;
        const win = iframe.contentWindow;
        result.viewport = win.innerWidth;

        phase("add_control");
        const add = testId(doc, "add-item") || findButton(doc, /add|new|create/i);
        check("add_control", !!add, add ? nameOf(add) : "add control not found");
        if (!add) { result.error = "add control not found"; finish(); return; }

        const fields = () => ({
          sku: testId(doc, "item-sku") || findField(doc, /sku|code|reference/i),
          name: testId(doc, "item-name") || findField(doc, /name|title/i),
          quantity: testId(doc, "item-quantity") || findField(doc, /quantity|qty|stock|count/i),
          reorder: testId(doc, "item-reorder") || findField(doc, /reorder|threshold|minimum|min/i)
        });
        const save = () => testId(doc, "save-item") ||
          doc.querySelector("dialog button[type='submit'], [role='dialog'] button[type='submit'], form button[type='submit']") ||
          findButton(doc, /save|create|add item/i);

        add.click();
        await wait(180);
        let current = fields();
        check("field_sku", !!current.sku, current.sku ? nameOf(current.sku) : "sku field");
        check("field_name", !!current.name, current.name ? nameOf(current.name) : "name field");
        check("field_quantity", !!current.quantity, current.quantity ? nameOf(current.quantity) : "quantity field");
        check("field_reorder", !!current.reorder, current.reorder ? nameOf(current.reorder) : "reorder field");
        const saveFirst = save();
        check("save_control", !!saveFirst, saveFirst ? nameOf(saveFirst) : "save control");
        if (!current.sku || !current.name || !current.quantity || !current.reorder || !saveFirst) {
          result.error = "required add form controls not found";
          finish();
          return;
        }
        setValue(current.sku, "BENCH-9001");
        setValue(current.name, "Benchmark item one");
        setValue(current.quantity, "3");
        setValue(current.reorder, "5");
        saveFirst.click();
        await wait(350);
        check("add_first", rowVisible(doc, "BENCH-9001"), "first item row");

        phase("add_second");
        add.click();
        await wait(180);
        current = fields();
        const saveSecond = save();
        if (!current.sku || !current.name || !saveSecond) {
          result.error = "second add form controls not found";
          finish();
          return;
        }
        setValue(current.sku, "BENCH-9002");
        setValue(current.name, "Benchmark item two");
        setValue(current.quantity, "90");
        setValue(current.reorder, "10");
        saveSecond.click();
        await wait(350);
        check("add_second", rowVisible(doc, "BENCH-9002"), "second item row");

        phase("search");
        const search = testId(doc, "search") || doc.querySelector("input[type='search']") || findField(doc, /search|filter/i);
        check("search_control", !!search, search ? nameOf(search) : "search control");
        if (!search) { result.error = "search control not found"; finish(); return; }
        setValue(search, "BENCH-9001");
        await wait(300);
        check("search_target_visible", rowVisible(doc, "BENCH-9001"), "target row after filtering");
        check("search_other_filtered", !rowVisible(doc, "BENCH-9002"), "other row hidden after filtering");
        let persisted = false;
        try {
          persisted = Object.keys(window.localStorage).some((key) => {
            const value = String(window.localStorage.getItem(key) || "");
            return value.includes("BENCH-9001") && value.includes("BENCH-9002");
          });
        } catch (error) { persisted = false; }
        check("localstorage_persist", persisted, "both rows persisted in localStorage");
      } catch (error) {
        result.error = String(error);
      }
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

        phase("reload");
        check("reload_page", !!doc.body, "page reloaded");
        const search = testId(doc, "search") || doc.querySelector("input[type='search']") || findField(doc, /search|filter/i);
        check("persist_search_control", !!search, search ? nameOf(search) : "search control");
        if (!search) { result.error = "search control missing after reload"; finish(); return; }
        setValue(search, "BENCH-9001");
        await wait(300);
        check("persist_target_visible", rowVisible(doc, "BENCH-9001"), "target row after a fresh browser run");
        check("persist_other_filtered", !rowVisible(doc, "BENCH-9002"), "other row hidden after a fresh browser run");

        phase("delete");
        setValue(search, "");
        await wait(180);
        const row = rowByText(doc, "BENCH-9001");
        const deleteButton = row ? (testId(row, "delete-item") || rowButton(row, /delete|remove/i)) : null;
        check("delete_control", !!deleteButton, deleteButton ? nameOf(deleteButton) : "row delete control");
        if (deleteButton) {
          deleteButton.click();
          await wait(200);
          const confirm = testId(doc, "confirm-delete") || dialogButton(doc, /delete|confirm|yes/i) ||
            findButton(doc, /delete|confirm|yes/i);
          if (confirm) confirm.click();
          await wait(350);
        }
        check("delete_item", !rowVisible(doc, "BENCH-9001"), "target row after delete");
        const low = testId(doc, "low-stock") || doc.querySelector("#kpi-low") ||
          findText(doc, /low stock|low-stock|reorder/i);
        check("low_stock_indicator", !!low && text(low).length > 0, low ? text(low).slice(0, 40) : "low-stock indicator");
      } catch (error) {
        result.error = String(error);
      }
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

        phase("viewport");
        check("mobile_viewport", win.innerWidth <= 480, "viewport " + win.innerWidth + "px");
        check("no_horizontal_overflow", doc.documentElement.scrollWidth <= win.innerWidth + 2, "scrollWidth " + doc.documentElement.scrollWidth);
        check("page_text", (doc.body.textContent || "").trim().length > 80, "rendered body text");

        phase("cta");
        const candidates = Array.from(doc.querySelectorAll("a, button, [role='button']"))
          .filter((node) => visible(node, win) && text(node).length > 0);
        const cta = candidates.find((node) => /book|pre.?order|get started|start|launch|shop|join|try|claim|download|reserve/i.test(text(node))) || candidates[0];
        check("cta_visible", !!cta && visible(cta, win), cta ? text(cta).slice(0, 60) : "no CTA");
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
      } catch (error) {
        result.error = String(error);
      }
      finish();
    });
    iframe.src = "/index.html";
    """


def _harness(script: str, width: int, height: int, required: tuple[str, ...]) -> str:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Stitchcraft benchmark harness</title>
<style>html,body{{margin:0;background:#111}}iframe{{border:0;display:block;width:{width}px;height:{height}px}}</style>
</head><body>
<iframe id="site" title="Generated site" width="{width}" height="{height}"></iframe>
<script>{_checks_template(required)}{script}</script>
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
    return {"status": UNTESTED, "kind": kind, "reason": reason, "checks": [], "required": []}


def _functional_outcome(result: object, required: tuple[str, ...] | list[str]) -> dict:
    """Enforce the completion contract on a raw harness result.

    This is deliberately independent of the browser-reported status: a harness
    that throws before its first assertion returns an empty check list, which
    must not become a pass.
    """
    data = result if isinstance(result, dict) else {}
    checks = data.get("checks") if isinstance(data.get("checks"), list) else []
    valid = [item for item in checks if isinstance(item, dict) and isinstance(item.get("id"), str)]
    passed_ids = {item["id"] for item in valid if item.get("ok") is True}
    failed_checks = [item["id"] for item in valid if item.get("ok") is not True]
    missing_checks = [check_id for check_id in required if check_id not in passed_ids]
    error = data.get("error")
    interrupted_at = data.get("interruptedAt") or (data.get("phase") if error else None)
    reported_failed = data.get("status") == FAILED
    status = PASSED if not error and not failed_checks and not missing_checks and not reported_failed else FAILED
    return {
        "status": status,
        "kind": str(data.get("kind") or ""),
        "checks": valid,
        "required": list(required),
        "missing_checks": missing_checks,
        "failed_checks": failed_checks,
        "error": None if error in (None, "") else str(error),
        "interrupted_at": interrupted_at,
        "viewport": data.get("viewport"),
    }


def _evaluate_harness(
    url: str,
    kind: str,
    browser: BrowserManager,
    *,
    required: tuple[str, ...],
    storage_dir: Path | None,
    timeout: int,
) -> dict:
    raw = browser.evaluate(
        url,
        "JSON.stringify(window.__benchmark)",
        timeout=timeout,
        wait_seconds=5,
        storage_dir=storage_dir,
    )
    return _functional_outcome(raw, required) | {"kind": kind}


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
                    "/__benchmark_add.html": _harness(_warehouse_add_script(), 1200, 900, WAREHOUSE_ADD_REQUIRED),
                    "/__benchmark_persist.html": _harness(_warehouse_persist_script(), 1200, 900, WAREHOUSE_PERSIST_REQUIRED),
                }
                with _serve_harnesses(harnesses, site_dir) as base:
                    first = _evaluate_harness(
                        base + "/__benchmark_add.html",
                        "warehouse_flow:add",
                        browser,
                        required=WAREHOUSE_ADD_REQUIRED,
                        storage_dir=storage_dir,
                        timeout=timeout,
                    )
                    if first["status"] != PASSED:
                        return {**first, "kind": kind}
                    second = _evaluate_harness(
                        base + "/__benchmark_persist.html",
                        "warehouse_flow:persist",
                        browser,
                        required=WAREHOUSE_PERSIST_REQUIRED,
                        storage_dir=storage_dir,
                        timeout=timeout,
                    )
                checks = first["checks"] + second["checks"]
                return {
                    "status": PASSED if second["status"] == PASSED else FAILED,
                    "kind": kind,
                    "checks": checks,
                    "required": list(WAREHOUSE_ADD_REQUIRED) + list(WAREHOUSE_PERSIST_REQUIRED),
                    "missing_checks": second.get("missing_checks", []),
                    "failed_checks": second.get("failed_checks", []),
                    "error": second.get("error"),
                    "interrupted_at": second.get("interrupted_at"),
                    "viewport": first.get("viewport"),
                }
        harness = {"/__benchmark_brand.html": _harness(_brand_script(), 390, 844, BRAND_REQUIRED)}
        with _serve_harnesses(harness, site_dir) as base:
            result = _evaluate_harness(
                base + "/__benchmark_brand.html",
                "brand_mobile",
                browser,
                required=BRAND_REQUIRED,
                storage_dir=None,
                timeout=timeout,
            )
        return {**result, "kind": kind}
    except BrowserError as exc:
        return _untested("browser could not run the functional harness: " + str(exc), kind)
    except Exception as exc:  # noqa: BLE001 - a broken harness must not fail the build
        return _untested("functional harness error: " + str(exc), kind)
