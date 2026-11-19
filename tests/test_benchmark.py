"""Tests for the fixed acceptance benchmark (offline mock engine)."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from stitchcraft import benchmark  # noqa: E402
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
            )
            self.assertEqual(report["summary"]["total"], 1)
            self.assertEqual(report["summary"]["passed"], 1)
            self.assertTrue(report["results"][0]["ok"])
            self.assertTrue((Path(report["report_dir"]) / "report.json").is_file())
            self.assertTrue((Path(report["report_dir"]) / "report.md").is_file())


if __name__ == "__main__":
    unittest.main()
