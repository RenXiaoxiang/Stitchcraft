"""Smoke tests for the stitch itself.

These run against the repository this file lives in: if the repo's own pipeline,
modules and contracts do not validate, the project is not shippable.
"""

from __future__ import annotations

import json
import sys
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from stitchcraft.loader import load_repo  # noqa: E402
from stitchcraft.render import mermaid_flow, stage_prompt  # noqa: E402
from stitchcraft.validate import summarize, validate_repo  # noqa: E402


class RepoHealthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = load_repo(ROOT)

    def test_repo_has_no_validation_errors(self) -> None:
        issues = validate_repo(self.repo)
        errors = [str(issue) for issue in issues if issue.level == "error"]
        self.assertEqual(errors, [], "the repository must validate cleanly")

    def test_every_contract_parses_as_schema_object(self) -> None:
        for artifact in self.repo.contracts:
            path = ROOT / "contracts" / f"{artifact}.schema.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data.get("type"), "object", artifact)
            self.assertIn("properties", data, artifact)
            self.assertIn("required", data, artifact)

    def test_every_module_has_a_skill(self) -> None:
        for module in self.repo.modules:
            self.assertTrue(module.skill_path.is_file(), module.id)

    def test_stage_prompt_names_skill_and_artifact(self) -> None:
        stage = self.repo.stages[0]
        prompt = stage_prompt(self.repo, stage, 1)
        self.assertIn("modules/01-brief/SKILL.md", prompt)
        self.assertIn(".stitch/01-brief/brief.json", prompt)
        self.assertIn("contracts/brief.schema.json", prompt)

    def test_mermaid_graph_contains_every_stage(self) -> None:
        chart = mermaid_flow(self.repo)
        for stage in self.repo.stages:
            self.assertIn(stage.id, chart)

    def test_unknown_dependency_is_reported(self) -> None:
        stages = list(self.repo.stages)
        stages[1] = replace(stages[1], depends_on=("does-not-exist",))
        broken = replace(self.repo, stages=tuple(stages))
        issues = validate_repo(broken)
        codes = {issue.code for issue in issues}
        self.assertIn("pipeline.unknown_dependency", codes)

    def test_duplicate_artifact_producer_is_reported(self) -> None:
        modules = list(self.repo.modules)
        first = modules[0]
        modules[1] = replace(modules[1], produces=modules[1].produces + first.produces)
        broken = replace(self.repo, modules=tuple(modules))
        issues = validate_repo(broken)
        codes = {issue.code for issue in issues}
        self.assertIn("seam.duplicate_producer", codes)

    def test_summary_counts_levels(self) -> None:
        errors, warnings = summarize(validate_repo(self.repo))
        self.assertEqual(errors, 0)
        self.assertGreaterEqual(warnings, 0)


if __name__ == "__main__":
    unittest.main()
