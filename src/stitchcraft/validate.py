"""Prove the stitch holds.

Validation is split into the same layers the repo is built from:

* ``validate_modules``  — every module manifest is well formed.
* ``validate_stages``   — every stage references exactly one real module.
* ``validate_graph``    — the dependency graph is acyclic and reachable.
* ``validate_seams``    — every artifact has one producer, a contract and an
  upstream source before a consumer asks for it.
* ``validate_contracts``— every schema is valid, parseable JSON Schema.
* ``validate_governance``— the Kiro steering, specs and hooks exist and are
  structurally valid.

Every finding is returned; nothing raises on content problems so the CLI can
report all of them at once.
"""

from __future__ import annotations

import json
from pathlib import Path

from .model import Issue, Module, Repo

TRIGGER_TYPES = {
    "agentStop",
    "fileCreated",
    "fileDeleted",
    "fileEdited",
    "postToolUse",
    "preToolUse",
    "promptSubmit",
    "userTriggered",
}
ACTION_TYPES = {"askAgent", "runCommand"}
REQUIRED_HOOK_KEYS = ("version", "enabled", "name", "when", "then")

__all__ = ["summarize", "validate_repo"]


def summarize(issues: list[Issue]) -> tuple[int, int]:
    """Return ``(errors, warnings)`` for a list of findings."""
    errors = sum(1 for issue in issues if issue.level == "error")
    warnings = sum(1 for issue in issues if issue.level == "warning")
    return errors, warnings


def validate_repo(repo: Repo) -> list[Issue]:
    """Run every validation layer and return all findings."""
    issues: list[Issue] = []
    issues.extend(validate_modules(repo))
    issues.extend(validate_stages(repo))
    issues.extend(validate_graph(repo))
    issues.extend(validate_seams(repo))
    issues.extend(validate_contracts(repo))
    issues.extend(validate_skills(repo))
    issues.extend(validate_libraries(repo))
    issues.extend(validate_themes(repo))
    issues.extend(validate_governance(repo))
    return issues


def validate_modules(repo: Repo) -> list[Issue]:
    """A module declares one job, one skill file and at least one artifact."""
    issues: list[Issue] = []
    seen: dict[str, Module] = {}
    for module in repo.modules:
        where = str(module.path)
        if not module.id:
            issues.append(Issue("error", "module.id.missing", "module id is empty", where))
            continue
        if module.id in seen:
            issues.append(
                Issue(
                    "error",
                    "module.id.duplicate",
                    f"module id '{module.id}' is declared twice "
                    f"({seen[module.id].path.name} and {module.path.name})",
                    where,
                )
            )
        seen[module.id] = module
        if not module.name:
            issues.append(Issue("warning", "module.name.missing", "module name is empty", where))
        if module.stage < 1:
            issues.append(Issue("error", "module.stage.invalid", "module stage must be >= 1", where))
        expected_slug = f"{module.stage:02d}-{module.id}"
        if module.slug != expected_slug:
            issues.append(
                Issue(
                    "warning",
                    "module.slug.mismatch",
                    f"folder '{module.slug}' should be '{expected_slug}' to mirror the stage",
                    where,
                )
            )
        if not module.produces:
            issues.append(Issue("error", "module.produces.empty", "module produces no artifact", where))
        overlap = set(module.consumes) & set(module.produces)
        if overlap:
            issues.append(
                Issue(
                    "error",
                    "module.consumes_own_output",
                    f"module consumes its own output: {', '.join(sorted(overlap))}",
                    where,
                )
            )
        if not module.skill_path.is_file():
            issues.append(
                Issue(
                    "error",
                    "module.skill.missing",
                    f"skill file '{module.skill}' does not exist",
                    where,
                )
            )
    return issues


def validate_stages(repo: Repo) -> list[Issue]:
    """Every stage wires exactly one known module, and every module is wired."""
    issues: list[Issue] = []
    seen: dict[str, str] = {}
    usage: dict[str, list[str]] = {}
    module_ids = {module.id for module in repo.modules}
    where = "pipeline/pipeline.toml"

    for stage in repo.stages:
        if not stage.id:
            issues.append(Issue("error", "stage.id.missing", "stage id is empty", where))
            continue
        if stage.id in seen:
            issues.append(Issue("error", "stage.id.duplicate", f"stage id '{stage.id}' is declared twice", where))
        seen[stage.id] = stage.id
        if not stage.module:
            issues.append(Issue("error", "stage.module.missing", f"stage '{stage.id}' names no module", where))
            continue
        if stage.module not in module_ids:
            issues.append(
                Issue(
                    "error",
                    "stage.module.unknown",
                    f"stage '{stage.id}' references unknown module '{stage.module}'",
                    where,
                )
            )
        usage.setdefault(stage.module, []).append(stage.id)

    for module in repo.modules:
        stages = usage.get(module.id, [])
        if not stages:
            issues.append(
                Issue(
                    "warning",
                    "module.unwired",
                    f"module '{module.id}' is not wired into any stage",
                    str(module.path),
                )
            )
        elif len(stages) > 1:
            issues.append(
                Issue(
                    "error",
                    "module.duplicate_stage",
                    f"module '{module.id}' is wired into stages {', '.join(stages)}",
                    where,
                )
            )
    return issues


def validate_graph(repo: Repo) -> list[Issue]:
    """Dependency references, cycles and reachability."""
    issues: list[Issue] = []
    where = "pipeline/pipeline.toml"
    stages = {stage.id: stage for stage in repo.stages}

    for stage in repo.stages:
        for dependency in stage.depends_on:
            if dependency == stage.id:
                issues.append(
                    Issue("error", "pipeline.self_dependency", f"stage '{stage.id}' depends on itself", where)
                )
            elif dependency not in stages:
                issues.append(
                    Issue(
                        "error",
                        "pipeline.unknown_dependency",
                        f"stage '{stage.id}' depends on unknown stage '{dependency}'",
                        where,
                    )
                )

    roots = [stage for stage in repo.stages if not stage.depends_on]
    if not roots:
        issues.append(Issue("error", "pipeline.no_entry", "the pipeline has no entry stage", where))
    elif len(roots) > 1:
        issues.append(
            Issue(
                "warning",
                "pipeline.multiple_entry",
                f"expected one entry stage, found {len(roots)}: {', '.join(s.id for s in roots)}",
                where,
            )
        )

    state: dict[str, int] = {}

    def visit(stage_id: str, stack: list[str]) -> None:
        current = state.get(stage_id, 0)
        if current == 1:
            cycle = " -> ".join([*stack, stage_id])
            issues.append(Issue("error", "pipeline.cycle", f"dependency cycle: {cycle}", where))
            return
        if current == 2:
            return
        state[stage_id] = 1
        for dependency in stages[stage_id].depends_on:
            if dependency in stages:
                visit(dependency, [*stack, stage_id])
        state[stage_id] = 2

    for stage in repo.stages:
        visit(stage.id, [])

    dependents: dict[str, list[str]] = {stage_id: [] for stage_id in stages}
    for stage in repo.stages:
        for dependency in stage.depends_on:
            if dependency in dependents:
                dependents[dependency].append(stage.id)
    reachable: set[str] = set()
    queue = [root.id for root in roots]
    while queue:
        current = queue.pop()
        if current in reachable:
            continue
        reachable.add(current)
        queue.extend(dependents[current])
    for stage in repo.stages:
        if stage.id not in reachable:
            issues.append(
                Issue(
                    "warning",
                    "pipeline.unreachable",
                    f"stage '{stage.id}' is unreachable from an entry stage",
                    where,
                )
            )
    return issues


def validate_seams(repo: Repo) -> list[Issue]:
    """Every hand-off is complete: one producer, one contract, real upstream."""
    issues: list[Issue] = []
    contracts = set(repo.contracts)
    producers: dict[str, Module] = {}
    modules = {module.id: module for module in repo.modules}
    stages = {stage.id: stage for stage in repo.stages}
    where = "pipeline/pipeline.toml"

    for module in repo.modules:
        for artifact in module.produces:
            if artifact in producers:
                issues.append(
                    Issue(
                        "error",
                        "seam.duplicate_producer",
                        f"artifact '{artifact}' is produced by both "
                        f"'{producers[artifact].id}' and '{module.id}'",
                        str(module.path),
                    )
                )
            else:
                producers[artifact] = module
            if artifact not in contracts:
                issues.append(
                    Issue(
                        "error",
                        "seam.missing_contract",
                        f"no contract 'contracts/{artifact}.schema.json' for produced artifact",
                        str(module.path),
                    )
                )

    def ancestors(stage_id: str, memo: dict[str, set[str]]) -> set[str]:
        if stage_id in memo:
            return memo[stage_id]
        result: set[str] = set()
        stage = stages.get(stage_id)
        if stage is not None:
            for dependency in stage.depends_on:
                if dependency in stages:
                    result.add(dependency)
                    result |= ancestors(dependency, memo)
        memo[stage_id] = result
        return result

    memo: dict[str, set[str]] = {}
    for stage in repo.stages:
        module = modules.get(stage.module)
        if module is None:
            continue
        available: set[str] = set()
        for dependency in ancestors(stage.id, memo):
            dependency_module = modules.get(stages[dependency].module)
            if dependency_module is not None:
                available |= set(dependency_module.produces)
        for artifact in module.consumes:
            if artifact not in contracts:
                issues.append(
                    Issue(
                        "error",
                        "seam.missing_contract",
                        f"no contract 'contracts/{artifact}.schema.json' for consumed artifact",
                        str(module.path),
                    )
                )
            if artifact not in available:
                issues.append(
                    Issue(
                        "error",
                        "seam.unavailable_input",
                        f"stage '{stage.id}' consumes '{artifact}' but no upstream stage produces it",
                        where,
                    )
                )

    for artifact in repo.contracts:
        if artifact not in producers:
            issues.append(
                Issue(
                    "warning",
                    "seam.no_producer",
                    f"contract 'contracts/{artifact}.schema.json' has no producing module",
                    "contracts/",
                )
            )
    return issues


def validate_skills(repo: Repo) -> list[Issue]:
    """The skill registry and every vendored pack must be resolvable."""
    from .skills import verify_registry

    return [
        Issue("error", "skills.registry", finding, "skills/")
        for finding in verify_registry(repo.root)
    ]


def validate_libraries(repo: Repo) -> list[Issue]:
    """The vendored browser-library registry must be complete and licensed."""
    from .libraries import load_libraries, verify_libraries
    from .themes import load_themes

    issues = [
        Issue("error", "libraries.registry", finding, "vendor/")
        for finding in verify_libraries(repo.root)
    ]
    known = {library.id for library in load_libraries(repo.root)}
    for theme in load_themes(repo.root):
        for library_id in getattr(theme, "libraries", ()):  # noqa: B009
            if library_id not in known:
                issues.append(
                    Issue(
                        "error",
                        "themes.library.unknown",
                        f"theme '{theme.id}' references unknown bundled library '{library_id}'",
                        theme.path,
                    )
                )
    return issues


def validate_themes(repo: Repo) -> list[Issue]:
    """Theme packages must be complete: manifest, skill, data model, samples."""
    from .themes import verify_themes

    return [
        Issue("error", "themes.registry", finding, "themes/")
        for finding in verify_themes(repo.root)
    ]


def validate_contracts(repo: Repo) -> list[Issue]:
    """Contracts must be valid JSON Schema objects, not stubs."""
    issues: list[Issue] = []
    for artifact in repo.contracts:
        path = repo.root / "contracts" / f"{artifact}.schema.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            issues.append(
                Issue("error", "contract.invalid_json", f"invalid JSON: {exc}", str(path))
            )
            continue
        if not isinstance(data, dict):
            issues.append(Issue("error", "contract.not_object", "schema must be a JSON object", str(path)))
            continue
        for key in ("$schema", "title", "type"):
            if key not in data:
                issues.append(
                    Issue("warning", "contract.missing_key", f"schema has no '{key}' key", str(path))
                )
        if data.get("type") == "object" and not isinstance(data.get("properties"), dict):
            issues.append(
                Issue("error", "contract.no_properties", "object schema declares no properties", str(path))
            )
    return issues


def validate_governance(repo: Repo) -> list[Issue]:
    """Kiro steering, specs and hooks are part of the stitch, so they are checked."""
    issues: list[Issue] = []
    root = repo.root

    steering_dir = root / ".kiro" / "steering"
    if not steering_dir.is_dir() or not list(steering_dir.glob("*.md")):
        issues.append(
            Issue("warning", "governance.steering_missing", "no .kiro/steering/*.md files found", ".kiro/")
        )

    specs_dir = root / ".kiro" / "specs"
    if not specs_dir.is_dir() or not list(specs_dir.glob("*/requirements.md")):
        issues.append(
            Issue(
                "warning",
                "governance.specs_missing",
                "no .kiro/specs/*/requirements.md found",
                ".kiro/",
            )
        )

    hooks_dir = root / ".kiro" / "hooks"
    if not hooks_dir.is_dir():
        issues.append(Issue("warning", "governance.hooks_missing", "no .kiro/hooks directory", ".kiro/"))
        return issues
    hook_files = sorted(hooks_dir.glob("*.kiro.hook"))
    if not hook_files:
        issues.append(Issue("warning", "governance.hooks_empty", "no *.kiro.hook files", str(hooks_dir)))
    for path in hook_files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            issues.append(Issue("error", "hook.invalid_json", f"invalid JSON: {exc}", str(path)))
            continue
        if not isinstance(data, dict):
            issues.append(Issue("error", "hook.not_object", "hook must be a JSON object", str(path)))
            continue
        missing = [key for key in REQUIRED_HOOK_KEYS if key not in data]
        if missing:
            issues.append(
                Issue("error", "hook.missing_keys", f"missing keys: {', '.join(missing)}", str(path))
            )
            continue
        when = data.get("when")
        then = data.get("then")
        if not isinstance(when, dict) or when.get("type") not in TRIGGER_TYPES:
            issues.append(Issue("error", "hook.trigger_invalid", "unknown or missing trigger type", str(path)))
        elif when.get("type") == "fileEdited" and not when.get("patterns"):
            issues.append(
                Issue("error", "hook.patterns_missing", "fileEdited hook declares no patterns", str(path))
            )
        if not isinstance(then, dict) or then.get("type") not in ACTION_TYPES:
            issues.append(Issue("error", "hook.action_invalid", "unknown or missing action type", str(path)))
        elif then.get("type") == "askAgent" and not str(then.get("prompt", "")).strip():
            issues.append(Issue("error", "hook.prompt_missing", "askAgent hook has an empty prompt", str(path)))
        elif then.get("type") == "runCommand" and not str(then.get("command", "")).strip():
            issues.append(Issue("error", "hook.command_missing", "runCommand hook has an empty command", str(path)))
    return issues
