"""Tests for the fixed acceptance benchmark (offline mock engine)."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from stitchcraft import benchmark  # noqa: E402
from stitchcraft import functional  # noqa: E402
from stitchcraft.browser import BrowserManager  # noqa: E402
from stitchcraft.settings import AppConfig  # noqa: E402


class BenchmarkTests(unittest.TestCase):
    def test_tasks_are_valid_and_cover_the_themes(self) -> None:
        tasks = benchmark.load_tasks(ROOT)
        self.assertGreaterEqual(len(tasks), 5)
        ids = {task["id"] for task in tasks}
        self.assertIn("warehouse-inventory", ids)
        self.assertIn("brand-launch", ids)
        themes = {task["theme"] for task in tasks}
        self.assertIn("warehouse-ops", themes)
        self.assertIn("personal-space", themes)

    def test_unknown_task_is_rejected(self) -> None:
        with self.assertRaises(benchmark.BenchmarkError):
            benchmark.load_tasks(ROOT, ["does-not-exist"])

    def test_mock_benchmark_passes_and_writes_reports(self) -> None:
        tasks = benchmark.load_tasks(ROOT, ["warehouse-inventory"])
        with tempfile.TemporaryDirectory() as tmp:
            report = benchmark.run_benchmarks(
                ROOT,
                AppConfig(),
                tasks,
                engine="mock",
                repeat=1,
                out_dir=Path(tmp) / "bench",
                browser=BrowserManager(base_dir=Path(tmp) / "browser"),
            )
            self.assertEqual(report["summary"]["total"], 1)
            self.assertEqual(report["summary"]["passed"], 1)
            self.assertTrue(report["results"][0]["ok"])
            self.assertEqual(report["results"][0]["model_calls"], 0)
            self.assertEqual(report["results"][0]["retries"], 0)
            self.assertIn(report["results"][0]["functional"]["status"], {"untested", "passed"})
            self.assertTrue((Path(report["report_dir"]) / "report.json").is_file())
            self.assertTrue((Path(report["report_dir"]) / "report.md").is_file())

    def test_mock_benchmark_flags_placeholder_builds(self) -> None:
        tasks = benchmark.load_tasks(ROOT, ["staff-directory"])
        with tempfile.TemporaryDirectory() as tmp:
            report = benchmark.run_benchmarks(
                ROOT,
                AppConfig(),
                tasks,
                engine="mock",
                repeat=1,
                out_dir=Path(tmp) / "bench",
                browser=BrowserManager(base_dir=Path(tmp) / "browser"),
            )
            result = report["results"][0]
            self.assertTrue(result["placeholder"])
            self.assertEqual(result["functional"]["status"], "untested")
            self.assertEqual(report["summary"]["placeholders"], 1)

    def test_brand_launch_has_a_real_demo_sample(self) -> None:
        tasks = benchmark.load_tasks(ROOT, ["brand-launch"])
        with tempfile.TemporaryDirectory() as tmp:
            report = benchmark.run_benchmarks(
                ROOT,
                AppConfig(),
                tasks,
                engine="mock",
                repeat=1,
                out_dir=Path(tmp) / "bench",
                browser=BrowserManager(base_dir=Path(tmp) / "browser"),
            )
            result = report["results"][0]
            self.assertFalse(result["placeholder"])
            self.assertTrue((ROOT / "themes" / "brand-launch" / "sample" / "index.html").is_file())
            self.assertEqual(report["summary"]["placeholders"], 0)

    def test_functional_outcome_fails_when_interrupted_before_first_check(self) -> None:
        required = ("add_control", "add_first", "search_control")
        outcome = functional._functional_outcome(
            {"status": "passed", "checks": [], "error": "boom before first assertion", "phase": "start"},
            required,
        )
        self.assertEqual(outcome["status"], "failed")
        self.assertEqual(outcome["interrupted_at"], "start")
        self.assertEqual(outcome["missing_checks"], list(required))
        self.assertIn("boom", outcome["error"])

    def test_functional_outcome_fails_when_interrupted_after_save(self) -> None:
        required = ("add_control", "save_control", "add_first", "search_control")
        outcome = functional._functional_outcome(
            {
                "status": "passed",
                "checks": [
                    {"id": "add_control", "ok": True},
                    {"id": "save_control", "ok": True},
                    {"id": "add_first", "ok": True},
                ],
                "error": "boom after save",
                "phase": "search",
            },
            required,
        )
        self.assertEqual(outcome["status"], "failed")
        self.assertEqual(outcome["interrupted_at"], "search")
        self.assertEqual(outcome["missing_checks"], ["search_control"])
        self.assertEqual(outcome["failed_checks"], [])

    def test_summary_marks_required_functional_incomplete(self) -> None:
        result = {
            "task": "warehouse-inventory",
            "attempt": 1,
            "build_ok": True,
            "functional": {"status": "untested"},
            "functional_required": True,
            "retries": 0,
            "duration_ms": 1,
            "placeholder": False,
            "model_calls": 0,
        }
        summary = benchmark._summary([result], [{"id": "warehouse-inventory"}])
        self.assertEqual(summary["functional_required"], 1)
        self.assertEqual(summary["functional_incomplete_required"], 1)
        self.assertFalse(summary["release_ready"])

    def test_warehouse_sample_exposes_stable_test_contract(self) -> None:
        html = (ROOT / "themes" / "warehouse-ops" / "sample" / "index.html").read_text(encoding="utf-8")
        for test_id in (
            "add-item", "item-sku", "item-name", "item-quantity", "item-reorder",
            "save-item", "search", "delete-item", "confirm-delete", "low-stock",
        ):
            self.assertIn(f'data-testid="{test_id}"', html)

    def test_functional_check_is_honest_without_a_browser(self) -> None:
        site = ROOT / "themes" / "warehouse-ops" / "sample"
        with tempfile.TemporaryDirectory() as tmp:
            result = functional.run_functional_check(
                "warehouse_flow",
                site,
                browser=BrowserManager(base_dir=Path(tmp) / "browser"),
            )
        self.assertEqual(result["status"], "untested")
        self.assertIn("not installed", result["reason"])

    def test_functional_check_does_not_score_placeholders(self) -> None:
        site = ROOT / "themes" / "warehouse-ops" / "sample"
        with tempfile.TemporaryDirectory() as tmp:
            result = functional.run_functional_check(
                "warehouse_flow",
                site,
                placeholder=True,
                browser=BrowserManager(base_dir=Path(tmp) / "browser"),
            )
        self.assertEqual(result["status"], "untested")
        self.assertIn("placeholder", result["reason"])

    def test_benchmark_uses_a_unique_run_directory_under_out(self) -> None:
        tasks = benchmark.load_tasks(ROOT, ["warehouse-inventory"])
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp) / "benchmarks"
            parent.mkdir()
            # Simulate a user directory that happens to share the task name.
            user_dir = parent / "warehouse-inventory-1"
            user_dir.mkdir()
            (user_dir / "notes.txt").write_text("keep me", encoding="utf-8")
            report = benchmark.run_benchmarks(
                ROOT,
                AppConfig(),
                tasks,
                engine="mock",
                repeat=1,
                out_dir=parent,
                browser=BrowserManager(base_dir=Path(tmp) / "browser"),
            )
            self.assertEqual((user_dir / "notes.txt").read_text(encoding="utf-8"), "keep me")
            run_dir = Path(report["report_dir"])
            self.assertNotEqual(run_dir, parent)
            self.assertTrue(run_dir.name.startswith("run-"))
            self.assertTrue((run_dir / "warehouse-inventory-1" / "index.html").is_file())


if __name__ == "__main__":
    unittest.main()
