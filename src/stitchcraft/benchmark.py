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

from . import generator
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


def _repair_count(warnings: list[str]) -> int:
    return sum(1 for warning in warnings if "retry" in warning.lower())


def run_benchmarks(
    root: Path,
    config: AppConfig,
    tasks: list[dict],
    *,
    engine: str = "mock",
    repeat: int = 1,
    out_dir: Path | None = None,
    sleep=time.sleep,
) -> dict:
    """Run each fixed task and return a JSON-serialisable report."""
    root = Path(root)
    engine = "ai" if engine == "ai" else "mock"
    repeat = max(1, int(repeat))
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    output_root = Path(out_dir) if out_dir is not None else root / ".stitch" / "benchmarks" / run_id
    output_root.mkdir(parents=True, exist_ok=True)
    started_run = time.perf_counter()
    results: list[dict] = []
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
                "duration_ms": 0,
                "files": 0,
                "missing_files": [],
                "warnings": [],
                "repairs": 0,
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
                    force=True,
                    sleep=sleep,
                )
                missing = [name for name in task["required_files"] if name not in result.files]
                warnings = list(result.warnings)
                critical = _critical_warnings(warnings)
                record.update(
                    ok=not missing and len(result.files) >= task["min_files"] and not critical,
                    duration_ms=result.duration_ms,
                    files=len(result.files),
                    missing_files=missing,
                    warnings=warnings,
                    repairs=_repair_count(warnings),
                    summary=result.summary,
                )
            except Exception as exc:  # noqa: BLE001 - a failed task is benchmark data
                record["error"] = str(exc)
                record["duration_ms"] = int((time.perf_counter() - started) * 1000)
            results.append(record)

    total = len(results)
    passed = sum(1 for item in results if item["ok"])
    by_task: dict[str, list[dict]] = {}
    for item in results:
        by_task.setdefault(item["task"], []).append(item)
    first_pass = sum(
        1
        for attempts in by_task.values()
        if sorted(attempts, key=lambda item: item["attempt"])[0]["ok"]
    )
    durations = [item["duration_ms"] for item in results if item["duration_ms"] > 0]
    report = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "engine": engine,
        "total_seconds": round(time.perf_counter() - started_run, 2),
        "tasks": [
            {
                "id": task["id"],
                "title": task.get("title", task["id"]),
                "theme": task["theme"],
                "required_files": task["required_files"],
                "file": task.get("file"),
            }
            for task in tasks
        ],
        "results": results,
        "summary": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": round(passed / total, 3) if total else 0,
            "first_pass": first_pass,
            "first_pass_rate": round(first_pass / len(by_task), 3) if by_task else 0,
            "average_duration_ms": int(sum(durations) / len(durations)) if durations else 0,
            "repairs": sum(item["repairs"] for item in results),
        },
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
        f"- Engine: **{report['engine']}**",
        f"- Run: `{report['run_id']}`",
        f"- Result: **{summary['passed']}/{summary['total']} passed** "
        f"({summary['pass_rate'] * 100:.0f}%), first-pass {summary['first_pass_rate'] * 100:.0f}%",
        f"- Average duration: {summary['average_duration_ms']} ms; repairs: {summary['repairs']}",
        "",
        "| Task | Attempt | Status | Duration | Files | Missing | Warnings |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in report["results"]:
        status = "PASS" if item["ok"] else "FAIL"
        missing = ", ".join(item["missing_files"]) or "-"
        lines.append(
            f"| {item['task']} | {item['attempt']} | {status} | {item['duration_ms']} ms | "
            f"{item['files']} | {missing} | {len(item['warnings'])} |"
        )
    lines.append("")
    lines.append("> A pass means the build completed and the required files exist.")
    lines.append("> Warnings and missing references are recorded for human review.")
    return "\n".join(lines) + "\n"
