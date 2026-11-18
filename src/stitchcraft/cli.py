"""`stitch` — the Stitchcraft command line.

The CLI only loads, checks, renders and stages the stitch. It never calls a
model: the agent (Kiro, Claude, Codex, ...) does the module work by following
each stage's SKILL.md and writing the contract-checked artifact.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from . import __version__
from .loader import LoadError, load_repo
from .model import Repo
from .render import mermaid_flow, plan_table, stage_prompt
from .validate import summarize, validate_repo

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_ERROR = 2

__all__ = ["build_parser", "main"]


def _display(path: Path, root: Path) -> str:
    """Render a path relative to the repo when possible, absolute otherwise."""
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stitch",
        description="Stitch specialised AI modules into one site-building pipeline.",
        epilog="Typical flow: stitch validate -> stitch plan -> stitch run --dry-run.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        help="repo root (default: nearest pipeline/pipeline.toml upward)",
    )
    parser.add_argument("--version", action="version", version=f"stitch {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="list stages and modules")
    show = sub.add_parser("show", help="show one module manifest and its skill")
    show.add_argument("module", help="module id, e.g. brief")

    validate = sub.add_parser("validate", help="validate wiring, seams, contracts and hooks")
    validate.add_argument("--strict", action="store_true", help="treat warnings as failures")
    validate.add_argument("--json", action="store_true", dest="as_json", help="machine-readable findings")

    plan = sub.add_parser("plan", help="render the stitch as Mermaid and a table")
    plan.add_argument("--mermaid-only", action="store_true", help="print only the Mermaid graph")

    sub.add_parser("doctor", help="check the local toolchain and repo health")

    run = sub.add_parser("run", help="prepare the stitch for an agent")
    run.add_argument("--dry-run", action="store_true", help="write one PROMPT.md per stage; no model calls")
    run.add_argument("--out", type=Path, help="output directory (default: <repo>/.stitch)")
    run.add_argument("--stage", help="only prepare one stage id")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        repo = load_repo(args.root)
    except LoadError as exc:
        print(f"stitch: {exc}", file=sys.stderr)
        return EXIT_ERROR
    handlers = {
        "list": cmd_list,
        "show": cmd_show,
        "validate": cmd_validate,
        "plan": cmd_plan,
        "doctor": cmd_doctor,
        "run": cmd_run,
    }
    return handlers[args.command](repo, args)


def cmd_list(repo: Repo, args: argparse.Namespace) -> int:
    print(f"{repo.project.name} {repo.project.version}: {len(repo.stages)} stages, {len(repo.modules)} modules")
    print()
    header = f"{'#':>2}  {'STAGE':<12} {'MODULE':<16} {'PRODUCES':<20} DEPENDS ON"
    print(header)
    print("-" * len(header))
    for index, stage in enumerate(repo.stages, start=1):
        module = repo.module(stage.module)
        produces = ", ".join(module.produces) if module is not None else "?"
        depends = ", ".join(stage.depends_on) or "-"
        gate = "  [gate]" if stage.gate else ""
        print(f"{index:>2}  {stage.id:<12} {stage.module:<16} {produces:<20} {depends}{gate}")
    print()
    print("Next: stitch show <module>, stitch validate, stitch plan")
    return EXIT_OK


def cmd_show(repo: Repo, args: argparse.Namespace) -> int:
    module = repo.module(args.module)
    if module is None:
        print(f"stitch: unknown module '{args.module}'", file=sys.stderr)
        print("available modules: " + ", ".join(item.id for item in repo.modules), file=sys.stderr)
        return EXIT_ERROR
    skill = module.skill_path.relative_to(repo.root).as_posix()
    print(f"{module.id} - {module.name}")
    print(f"  stage:    {module.stage}")
    print(f"  folder:   {module.path.relative_to(repo.root).as_posix()}")
    print(f"  skill:    {skill}")
    print(f"  consumes: {', '.join(module.consumes) or 'nothing (entry stage)'}")
    print(f"  produces: {', '.join(module.produces)}")
    print(f"  gate:     {'yes' if module.gate else 'no'}")
    print(f"  job:      {module.summary}")
    return EXIT_OK


def cmd_validate(repo: Repo, args: argparse.Namespace) -> int:
    issues = validate_repo(repo)
    errors, warnings = summarize(issues)
    failed = errors > 0 or (args.strict and warnings > 0)
    if args.as_json:
        payload = {
            "ok": not failed,
            "errors": errors,
            "warnings": warnings,
            "issues": [asdict(issue) for issue in issues],
        }
        print(json.dumps(payload, indent=2))
    else:
        for issue in issues:
            print(issue)
        if issues:
            print()
        state = "FAIL" if failed else "ok"
        print(f"stitch validate: {state} - {errors} error(s), {warnings} warning(s)")
    return EXIT_FINDINGS if failed else EXIT_OK


def cmd_plan(repo: Repo, args: argparse.Namespace) -> int:
    print("```mermaid")
    print(mermaid_flow(repo))
    print("```")
    if not args.mermaid_only:
        print()
        print(plan_table(repo))
    else:
        print()
    print()
    print(f"Artifacts land in {repo.project.artifact_dir}/<NN-stage>/<artifact>.json")
    return EXIT_OK


def cmd_doctor(repo: Repo, args: argparse.Namespace) -> int:
    checks: list[tuple[str, str, str]] = []

    ok = sys.version_info >= (3, 11)
    checks.append(("python", "ok" if ok else "fail", sys.version.split()[0]))

    git_dir = repo.root / ".git"
    checks.append(("git repo", "ok" if git_dir.exists() else "warn", str(repo.root)))
    checks.append(("pipeline", "ok" if repo.stages else "fail", f"{len(repo.stages)} stages"))

    produced = {artifact for module in repo.modules for artifact in module.produces}
    missing = sorted(produced - set(repo.contracts))
    checks.append(
        (
            "contracts",
            "ok" if not missing else "fail",
            f"{len(repo.contracts)} contracts" + (f", missing: {', '.join(missing)}" if missing else ""),
        )
    )

    hooks = sorted((repo.root / ".kiro" / "hooks").glob("*.kiro.hook"))
    steering = sorted((repo.root / ".kiro" / "steering").glob("*.md"))
    specs = sorted((repo.root / ".kiro" / "specs").glob("*/requirements.md"))
    checks.append(("steering", "ok" if steering else "warn", f"{len(steering)} file(s)"))
    checks.append(("hooks", "ok" if hooks else "warn", f"{len(hooks)} hook(s)"))
    checks.append(("specs", "ok" if specs else "warn", f"{len(specs)} spec(s)"))

    tests = repo.root / "tests"
    checks.append(("tests", "ok" if tests.is_dir() else "warn", str(tests.relative_to(repo.root))))

    for label, status, detail in checks:
        marker = {"ok": "[ ok ]", "warn": "[warn]", "fail": "[FAIL]"}[status]
        print(f"{marker} {label:<12} {detail}")

    failures = [item for item in checks if item[1] == "fail"]
    print()
    print("stitch doctor: " + ("healthy" if not failures else f"{len(failures)} blocking issue(s)"))
    return EXIT_FINDINGS if failures else EXIT_OK


def cmd_run(repo: Repo, args: argparse.Namespace) -> int:
    if not args.dry_run:
        print(
            "stitch: `stitch run` is agent-driven; this release ships the dry-run planner only.\n"
            "Use `stitch run --dry-run` to stage one PROMPT.md per stage, then execute the\n"
            "skills inside Kiro (or any agent) and validate the artifacts.",
            file=sys.stderr,
        )
        return EXIT_ERROR

    out_dir = args.out if args.out is not None else Path(repo.project.artifact_dir)
    if not out_dir.is_absolute():
        out_dir = repo.root / out_dir

    stages = list(repo.stages)
    if args.stage:
        matching = [stage for stage in stages if stage.id == args.stage]
        if not matching:
            print(f"stitch: unknown stage '{args.stage}'", file=sys.stderr)
            print("available stages: " + ", ".join(stage.id for stage in stages), file=sys.stderr)
            return EXIT_ERROR
        stages = matching

    written: list[Path] = []
    for index, stage in enumerate(repo.stages, start=1):
        if stage not in stages:
            continue
        stage_dir = out_dir / f"{index:02d}-{stage.id}"
        stage_dir.mkdir(parents=True, exist_ok=True)
        prompt_path = stage_dir / "PROMPT.md"
        prompt_path.write_text(stage_prompt(repo, stage, index), encoding="utf-8")
        written.append(prompt_path)

    print(f"stitch run --dry-run: prepared {len(written)} stage prompt(s), no model calls were made.")
    for path in written:
        print(f"  {_display(path, repo.root)}")
    print()
    print("Next: open the first PROMPT.md in Kiro (or any agent) and execute the skill it points to.")
    print("After a stage is done: `python -m stitchcraft validate` to prove the seam still holds.")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
