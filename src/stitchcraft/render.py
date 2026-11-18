"""Render the stitch for humans: Mermaid graphs and Markdown tables."""

from __future__ import annotations

from .model import Module, Repo, Stage

__all__ = ["mermaid_flow", "module_table", "plan_table"]

EMPTY = "-"


def _node(stage_id: str) -> str:
    """Mermaid-safe node id for a stage id."""
    return "n_" + "".join(char if char.isalnum() else "_" for char in stage_id)


def mermaid_flow(repo: Repo) -> str:
    """Render the stage graph as a Mermaid flowchart."""
    modules = {module.id: module for module in repo.modules}
    lines = ["flowchart LR"]
    for stage in repo.stages:
        module = modules.get(stage.module)
        label = module.name if module is not None else stage.module
        lines.append(f'    {_node(stage.id)}["{stage.id}<br/>{label}"]')
    for stage in repo.stages:
        for dependency in stage.depends_on:
            lines.append(f"    {_node(dependency)} --> {_node(stage.id)}")
    return "\n".join(lines)


def plan_table(repo: Repo) -> str:
    """Render the stitch as a Markdown table in pipeline order."""
    modules = {module.id: module for module in repo.modules}
    rows = [
        "| # | Stage | Module | Depends on | Consumes | Produces | Gate |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for index, stage in enumerate(repo.stages, start=1):
        module = modules.get(stage.module)
        consumes = ", ".join(module.consumes) if module is not None and module.consumes else EMPTY
        produces = ", ".join(module.produces) if module is not None and module.produces else EMPTY
        depends = ", ".join(stage.depends_on) if stage.depends_on else EMPTY
        gate = "yes" if stage.gate else ""
        name = module.name if module is not None else stage.module
        rows.append(
            f"| {index} | `{stage.id}` | {name} | {depends} | {consumes} | {produces} | {gate} |"
        )
    return "\n".join(rows)


def module_table(repo: Repo) -> str:
    """Render modules only, for README-style inventories."""
    rows = [
        "| Stage | Module | Job | Consumes | Produces |",
        "| --- | --- | --- | --- | --- |",
    ]
    for module in sorted(repo.modules, key=lambda item: item.stage):
        consumes = ", ".join(module.consumes) if module.consumes else EMPTY
        produces = ", ".join(module.produces) if module.produces else EMPTY
        rows.append(
            f"| {module.stage} | `{module.id}` | {module.summary} | {consumes} | {produces} |"
        )
    return "\n".join(rows)


def stage_prompt(repo: Repo, stage: Stage, order: int) -> str:
    """Compose the dry-run prompt an agent executes for one stage.

    The prompt is intentionally plain text. It points at the skill, the seam and
    the artifact path instead of inlining instructions, so the SKILL.md stays the
    single source of truth for the job.
    """
    module = repo.module(stage.module)
    if module is None:
        raise ValueError(f"stage '{stage.id}' references unknown module '{stage.module}'")
    artifact_dir = repo.project.artifact_dir.rstrip("/")
    produced_paths = [f"{artifact_dir}/{order:02d}-{stage.id}/{artifact}.json" for artifact in module.produces]

    lines = [
        f"# Stage {order:02d} — {module.name}",
        "",
        f"- Stage: `{stage.id}`",
        f"- Module: `{module.id}`",
        f"- Skill: `{module.skill_path.relative_to(repo.root).as_posix()}`",
        f"- Job: {stage.description or module.summary}",
        "",
        "## Read",
        f"1. `{module.skill_path.relative_to(repo.root).as_posix()}` — the authoritative procedure for this job.",
        "2. The contracts for every artifact named below.",
        "3. The upstream artifacts this stage consumes.",
        "",
        "## Seam",
        f"- Consumes: {', '.join(f'`{artifact}`' for artifact in module.consumes) if module.consumes else 'nothing (entry stage)'}",
        f"- Produces: {', '.join(f'`{artifact}`' for artifact in module.produces)}",
    ]
    for artifact in module.consumes:
        lines.append(f"- Contract: `contracts/{artifact}.schema.json`")
    for artifact in module.produces:
        lines.append(f"- Contract: `contracts/{artifact}.schema.json`")
    lines.extend(["", "## Upstream files", ""])
    if not stage.depends_on:
        lines.append("This is the entry stage: there are no upstream artifacts.")
    else:
        for dependency in stage.depends_on:
            dependency_stage = repo.stage(dependency)
            dependency_module = repo.module(dependency_stage.module) if dependency_stage else None
            if dependency_module is None:
                continue
            dependent_order = _stage_order(repo, dependency)
            for artifact in dependency_module.produces:
                lines.append(
                    f"- `{artifact_dir}/{dependent_order:02d}-{dependency}/{artifact}.json`"
                )
    lines.extend(
        [
            "",
            "## Do",
            "",
            "- Execute only this module's job. Do not do another stage's work;",
            "  if the input is insufficient, record the gap in `open_questions`.",
            f"- Write the artifact as JSON to: {', '.join(f'`{path}`' for path in produced_paths)}.",
            "- Run `python -m stitchcraft validate` and fix anything this stage broke.",
            "- Stop when the quality bar in the skill is met; do not polish the whole site here.",
            "",
            "## Guardrails",
            "",
            "- Never edit another module's artifact; report the defect upstream instead.",
            "- Never weaken `contracts/` to make an artifact pass.",
            "- Keep the artifact machine-readable: JSON only, no prose wrappers.",
            "",
        ]
    )
    return "\n".join(lines)


def _stage_order(repo: Repo, stage_id: str) -> int:
    for index, stage in enumerate(repo.stages, start=1):
        if stage.id == stage_id:
            return index
    raise ValueError(f"unknown stage '{stage_id}'")
