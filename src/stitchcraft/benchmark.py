"""Fixed acceptance tasks for measuring generated-site quality.

The benchmark is deliberately small and deterministic: each task names a theme,
a brief and the files a usable build must contain. A run records pass/fail,
latency, file count, warnings and retry/repair notes. It is not a substitute for
human review, but it answers the practical question: "after a brief, how often
did the first build produce a usable site?"
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import functional, generator
from .browser import BrowserManager
from .generator import GenerationRequest
from .settings import AppConfig

TASKS_DIR = Path("benchmarks") / "tasks"


class BenchmarkError(RuntimeError):
    """Raised when benchmark task definitions or a run are invalid."""


def load_tasks(root: Path, only: list[str] | None = None) -> list[dict]:
    """Load and validate the fixed JSON task files."""
    directory = Path(root) / TASKS_DIR
    if not directory.is_dir():
        raise BenchmarkError(f"benchmark tasks directory is missing: {TASKS_DIR.as_posix()}")
    tasks: list[dict] = []
    for path in sorted(directory.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise BenchmarkError(f"invalid benchmark task {path.name}: {exc}") from exc
        for field in ("id", "theme", "prompt"):
            if not isinstance(data.get(field), str) or not data[field].strip():
                raise BenchmarkError(f"{path.name} is missing a non-empty '{field}'")
        required = data.get("required_files", [])
        if not isinstance(required, list) or not required or not all(isinstance(item, str) for item in required):
            raise BenchmarkError(f"{path.name} needs a non-empty required_files array")
        if not isinstance(data.get("min_files", 1), int) or data.get("min_files", 1) < 1:
            raise BenchmarkError(f"{path.name} has an invalid min_files value")
        data["required_files"] = required
        data["min_files"] = int(data.get("min_files", 1))
        data["file"] = path.name
        tasks.append(data)
    wanted = [str(item) for item in only or []]
    if wanted:
        known = {task["id"] for task in tasks}
        missing = [task_id for task_id in wanted if task_id not in known]
        if missing:
            raise BenchmarkError("unknown benchmark task(s): " + ", ".join(missing))
        tasks = [task for task in tasks if task["id"] in wanted]
    if not tasks:
        raise BenchmarkError("no benchmark tasks selected")
    return tasks


def _critical_warnings(warnings: list[str]) -> list[str]:
    return [warning for warning in warnings if "missing local file" in warning.lower()]


def _summary(results: list[dict], tasks: list[dict]) -> dict:
    by_task: dict[str, list[dict]] = {}
    for item in results:
        by_task.setdefault(item["task"], []).append(item)
    total = len(results)
    build_passed = sum(1 for item in results if item["build_ok"])
    functional_passed = sum(1 for item in results if item["functional"].get("status") == "passed")
    functional_failed = sum(1 for item in results if item["functional"].get("status") == "failed")
    functional_untested = sum(1 for item in results if item["functional"].get("status") == "untested")
    no_retry = sum(1 for item in results if item["build_ok"] and item["retries"] == 0)
    recovered = sum(1 for item in results if item["build_ok"] and item["retries"] > 0)
    first_pass = 0
    retry_recovered = 0
    for attempts in by_task.values():
        ordered = sorted(attempts, key=lambda item: item["attempt"])
        first = ordered[0]
        if first["build_ok"] and first["retries"] == 0:
            first_pass += 1
        elif any(item["build_ok"] for item in ordered[1:]):
            retry_recovered += 1
    durations = [item["duration_ms"] for item in results if item["duration_ms"] > 0]
    return {
        "total": total,
        "tasks": len(tasks),
        "build_passed": build_passed,
        "build_failed": total - build_passed,
        "passed": build_passed,
        "pass_rate": round(build_passed / total, 3) if total else 0,
        "functional_passed": functional_passed,
        "functional_failed": functional_failed,
        "functional_untested": functional_untested,
        "placeholders": sum(1 for item in results if item["placeholder"]),
        "no_retry_passes": no_retry,
        "recovered_after_retry": recovered,
        "first_pass": first_pass,
        "first_pass_rate": round(first_pass / len(by_task), 3) if by_task else 0,
        "retry_recovered_tasks": retry_recovered,
        "average_duration_ms": int(sum(durations) / len(durations)) if durations else 0,
        "model_calls": sum(item["model_calls"] for item in results),
        "retries": sum(item["retries"] for item in results),
    }


def run_benchmarks(
    root: Path,
    config: AppConfig,
    tasks: list[dict],
    *,
    engine: str = "mock",
    repeat: int = 1,
    out_dir: Path | None = None,
    sleep=time.sleep,
    browser: BrowserManager | None = None,
) -> dict:
    """Run each fixed task and return a JSON-serialisable report."""
    root = Path(root)
    engine = "ai" if engine == "ai" else "mock"
    repeat = max(1, int(repeat))
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    base_dir = Path(out_dir) if out_dir is not None else root / ".stitch" / "benchmarks"
    base_dir.mkdir(parents=True, exist_ok=True)
    output_root = base_dir / f"run-{run_id}"
    # The run directory is always new: a user-supplied --out is a parent, never
    # the thing we write task folders into, and we never pass force=True.
    suffix = 1
    while output_root.exists():
        output_root = base_dir / f"run-{run_id}-{suffix}"
        suffix += 1
    output_root.mkdir(parents=True)
    started_run = time.perf_counter()
    results: list[dict] = []
    browser = browser or BrowserManager()
    for task in tasks:
        for attempt in range(1, repeat + 1):
            target = output_root / f"{task['id']}-{attempt}"
            started = time.perf_counter()
            record = {
                "task": task["id"],
                "title": task.get("title", task["id"]),
                "theme": task["theme"],
                "attempt": attempt,
                "engine": engine,
                "ok": False,
                "build_ok": False,
                "duration_ms": 0,
                "files": 0,
                "missing_files": [],
                "warnings": [],
                "placeholder": False,
                "model_calls": 0,
                "retries": 0,
                "no_retry_pass": False,
                "functional": {"status": "untested", "kind": task.get("functional"), "reason": "build did not run", "checks": []},
                "error": None,
            }
            try:
                result = generator.generate_site(
                    root,
                    config,
                    GenerationRequest(
                        theme_id=task["theme"],
                        prompt=task["prompt"],
                        title=task.get("title", ""),
                        engine=engine,
                        database={"mode": "local", "remote": {}},
                    ),
                    target,
                    sleep=sleep,
                )
                missing = [name for name in task["required_files"] if name not in result.files]
                warnings = list(result.warnings)
                critical = _critical_warnings(warnings)
                build_ok = not missing and len(result.files) >= task["min_files"] and not critical
                try:
                    functional_result = functional.run_functional_check(
                        task.get("functional"),
                        target,
                        placeholder=result.placeholder,
                        browser=browser,
                    )
                except Exception as exc:  # noqa: BLE001 - build success is still valid
                    functional_result = {
                        "status": "untested",
                        "kind": task.get("functional"),
                        "reason": "functional harness error: " + str(exc),
                        "checks": [],
                    }
                record.update(
                    ok=build_ok,
                    build_ok=build_ok,
                    duration_ms=result.duration_ms,
                    files=len(result.files),
                    missing_files=missing,
                    warnings=warnings,
                    placeholder=bool(result.placeholder),
                    model_calls=int(result.model_calls),
                    retries=int(result.retries),
                    no_retry_pass=bool(build_ok and result.retries == 0),
                    functional=functional_result,
                    summary=result.summary,
                )
            except Exception as exc:  # noqa: BLE001 - a failed task is benchmark data
                record["error"] = str(exc)
                record["duration_ms"] = int((time.perf_counter() - started) * 1000)
                record["functional"] = {
                    "status": "untested",
                    "kind": task.get("functional"),
                    "reason": "build failed before the functional check",
                    "checks": [],
                }
            record["provider"] = config.ai.provider if engine == "ai" else "mock"
            record["model"] = config.ai.model if engine == "ai" else "mock"
            results.append(record)

    summary = _summary(results, tasks)
    report = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "engine": engine,
        "provider": config.ai.provider if engine == "ai" else "mock",
        "model": config.ai.model if engine == "ai" else "mock",
        "total_seconds": round(time.perf_counter() - started_run, 2),
        "tasks": [
            {
                "id": task["id"],
                "title": task.get("title", task["id"]),
                "theme": task["theme"],
                "required_files": task["required_files"],
                "functional": task.get("functional"),
                "file": task.get("file"),
            }
            for task in tasks
        ],
        "results": results,
        "summary": summary,
    }
    (output_root / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output_root / "report.md").write_text(_markdown(report), encoding="utf-8")
    report["report_dir"] = str(output_root)
    return report


def _markdown(report: dict) -> str:
    summary = report["summary"]
    lines = [
        "# Stitchcraft acceptance benchmark",
        "",
        f"- Engine: **{report['engine']}** ({report.get('provider')}/{report.get('model')})",
        f"- Run: `{report['run_id']}`",
        f"- Build: **{summary['build_passed']}/{summary['total']} passed** "
        f"({summary['pass_rate'] * 100:.0f}%), no-retry first pass {summary['first_pass_rate'] * 100:.0f}%",
        f"- Functional: {summary['functional_passed']} passed, {summary['functional_failed']} failed, "
        f"{summary['functional_untested']} untested; placeholders: {summary['placeholders']}",
        f"- Retries: {summary['retries']} · model calls: {summary['model_calls']} · "
        f"average duration: {summary['average_duration_ms']} ms",
        "",
        "| Task | Attempt | Build | Functional | Retries | Calls | Duration | Files | Warnings |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in report["results"]:
        functional = item["functional"].get("status", "untested")
        build = "PASS" if item["build_ok"] else "FAIL"
        lines.append(
            f"| {item['task']} | {item['attempt']} | {build} | {functional} | {item['retries']} | "
            f"{item['model_calls']} | {item['duration_ms']} ms | {item['files']} | {len(item['warnings'])} |"
        )
    lines.append("")
    lines.append("> Build pass means the site was generated with its required files.")
    lines.append("> Functional status comes from the browser operation chain; `untested` is")
    lines.append("> explicit (browser missing, placeholder build, or no scenario), never a pass.")
    lines.append("> Placeholder builds are counted separately so they cannot inflate quality.")
    return "\n".join(lines) + "\n"
