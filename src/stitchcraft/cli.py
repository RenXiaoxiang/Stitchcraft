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

    app = sub.add_parser("app", help="launch the desktop studio (local UI in an app window)")
    app.add_argument("--port", type=int, default=8765, help="preferred local port (default 8765)")
    app.add_argument("--no-window", action="store_true", help="start the server without opening a window")
    app.add_argument("--smoke-test", action="store_true", help="run API checks headlessly and exit")

    theme_parser = sub.add_parser("themes", help="list, inspect or verify theme packages")
    theme_parser.add_argument("action", nargs="?", default="list", choices=["list", "show", "verify"])
    theme_parser.add_argument("theme_id", nargs="?", help="theme id for `themes show`")

    skill_parser = sub.add_parser("skills", help="list, inspect or verify bundled skills")
    skill_parser.add_argument("action", nargs="?", default="list", choices=["list", "show", "verify"])
    skill_parser.add_argument("skill_id", nargs="?", help="skill id for `skills show`")

    library_parser = sub.add_parser("libraries", help="list, inspect or verify bundled browser libraries")
    library_parser.add_argument("action", nargs="?", default="list", choices=["list", "show", "verify"])
    library_parser.add_argument("library_id", nargs="?", help="library id for `libraries show`")

    browser_parser = sub.add_parser("browser", help="install and drive the optional Obscura AI browser")
    browser_parser.add_argument(
        "action",
        nargs="?",
        default="status",
        choices=["status", "install", "remove", "check", "serve", "mcp"],
    )
    browser_parser.add_argument("--url", default="", help="page URL for `browser check`")
    browser_parser.add_argument("--out", type=Path, default=None, help="artifact directory for `browser check`")
    browser_parser.add_argument("--timeout", type=int, default=30, help="navigation timeout in seconds")
    browser_parser.add_argument("--no-screenshot", action="store_true", help="skip the PNG screenshot")
    browser_parser.add_argument("--port", type=int, default=9222, help="CDP port for `browser serve`")
    browser_parser.add_argument("--stealth", action="store_true", help="enable Obscura stealth mode")
    browser_parser.add_argument("--http", action="store_true", help="run the MCP server over HTTP")
    browser_parser.add_argument("--json", action="store_true", dest="as_json", help="machine-readable output")

    generate = sub.add_parser("generate", help="generate a site headlessly from a theme and a brief")
    generate.add_argument("--theme", required=True, help="theme id, e.g. warehouse-ops")
    generate.add_argument("--prompt", required=True, help="what the site should be")
    generate.add_argument("--title", default="", help="optional site title")
    generate.add_argument("--engine", choices=["mock", "ai"], default="mock", help="mock (demo) or ai (configured API)")
    generate.add_argument("--database", choices=["local", "remote"], default="local", help="generated data layer mode")
    generate.add_argument("--db-kind", default="supabase", choices=["supabase", "rest"], help="remote database flavour")
    generate.add_argument("--db-url", default="", help="remote database URL")
    generate.add_argument("--db-key", default="", help="remote public/anon key")
    generate.add_argument("--db-prefix", default="stitchcraft", help="remote table prefix")
    generate.add_argument("--out", type=Path, default=None, help="output directory (default: <repo>/.stitch/generated/<theme>)")
    generate.add_argument(
        "--force",
        action="store_true",
        help="allow cleaning a non-empty output directory that Stitchcraft did not create",
    )

    benchmark = sub.add_parser("benchmark", help="run the fixed acceptance tasks and report quality")
    benchmark.add_argument("--engine", choices=["mock", "ai"], default="mock", help="mock demo or configured AI engine")
    benchmark.add_argument("--task", action="append", default=None, help="run only this task id (repeatable)")
    benchmark.add_argument("--repeat", type=int, default=1, help="attempts per task (default 1)")
    benchmark.add_argument("--out", type=Path, default=None, help="output directory (default: <repo>/.stitch/benchmarks/<run>)")

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
        "app": cmd_app,
        "themes": cmd_themes,
        "skills": cmd_skills,
        "libraries": cmd_libraries,
        "browser": cmd_browser,
        "generate": cmd_generate,
        "benchmark": cmd_benchmark,
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

    from .browser import BrowserManager

    browser_status = BrowserManager().status()
    checks.append(
        (
            "ai browser",
            "ok" if browser_status["installed"] else "warn",
            f"Obscura {browser_status['version']}: {'installed' if browser_status['installed'] else 'not installed'}",
        )
    )

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


def cmd_app(repo: Repo, args: argparse.Namespace) -> int:
    from .desktop import run as run_desktop

    return run_desktop(
        root=repo.root,
        port=args.port,
        open_window_enabled=not args.no_window,
        smoke_test=args.smoke_test,
    )


def cmd_themes(repo: Repo, args: argparse.Namespace) -> int:
    from .themes import get_theme, load_themes, verify_themes

    if args.action == "verify":
        findings = verify_themes(repo.root)
        for finding in findings:
            print(f"ERROR   themes: {finding}")
        print(f"stitch themes verify: {'ok' if not findings else str(len(findings)) + ' problem(s)'}")
        return EXIT_FINDINGS if findings else EXIT_OK
    if args.action == "show":
        if not args.theme_id:
            print("stitch: `themes show` needs a theme id", file=sys.stderr)
            return EXIT_ERROR
        theme = get_theme(repo.root, args.theme_id)
        if theme is None:
            print(f"stitch: unknown theme '{args.theme_id}'", file=sys.stderr)
            print("available: " + ", ".join(item.id for item in load_themes(repo.root)), file=sys.stderr)
            return EXIT_ERROR
        print(f"{theme.id} - {theme.name}")
        print(f"  category: {theme.category}")
        print(f"  accent:   {theme.accent}")
        print(f"  summary:  {theme.summary}")
        print(f"  tags:     {', '.join(theme.tags) or '-'}")
        print(f"  blocks:   {', '.join(theme.blocks) or '-'}")
        print(f"  skills:   {', '.join(theme.skills) or '-'}")
        print(f"  sample:   {'yes' if theme.has_sample else 'no'}")
        print(f"  folder:   {theme.path}")
        return EXIT_OK
    for theme in load_themes(repo.root):
        sample = "  [sample]" if theme.has_sample else ""
        print(f"{theme.id:<20} {theme.category:<9} {theme.name}{sample}")
    return EXIT_OK


def cmd_skills(repo: Repo, args: argparse.Namespace) -> int:
    from .skills import get_skill, load_registry, verify_registry

    if args.action == "verify":
        findings = verify_registry(repo.root)
        for finding in findings:
            print(f"ERROR   skills: {finding}")
        print(f"stitch skills verify: {'ok' if not findings else str(len(findings)) + ' problem(s)'}")
        return EXIT_FINDINGS if findings else EXIT_OK
    if args.action == "show":
        if not args.skill_id:
            print("stitch: `skills show` needs a skill id", file=sys.stderr)
            return EXIT_ERROR
        skill = get_skill(repo.root, args.skill_id)
        if skill is None:
            print(f"stitch: unknown skill '{args.skill_id}'", file=sys.stderr)
            return EXIT_ERROR
        print(f"{skill.id} - {skill.name}")
        print(f"  category: {skill.category}")
        print(f"  source:   {skill.source}")
        print(f"  license:  {skill.license}")
        print(f"  stages:   {', '.join(skill.stages) or '-'}")
        print(f"  budget:   {skill.budget_chars} chars")
        print(f"  path:     {skill.path}")
        return EXIT_OK
    for skill in load_registry(repo.root):
        state = "on " if skill.enabled else "off"
        print(f"{state} {skill.id:<26} {skill.category:<14} {skill.license:<18} {skill.name}")
    return EXIT_OK


def cmd_libraries(repo: Repo, args: argparse.Namespace) -> int:
    from .libraries import get_library, load_libraries, verify_libraries

    if args.action == "verify":
        findings = verify_libraries(repo.root)
        for finding in findings:
            print(f"ERROR   libraries: {finding}")
        print(f"stitch libraries verify: {'ok' if not findings else str(len(findings)) + ' problem(s)'}")
        return EXIT_FINDINGS if findings else EXIT_OK
    if args.action == "show":
        if not args.library_id:
            print("stitch: `libraries show` needs a library id", file=sys.stderr)
            return EXIT_ERROR
        library = get_library(repo.root, args.library_id)
        if library is None:
            print(f"stitch: unknown library '{args.library_id}'", file=sys.stderr)
            print("available: " + ", ".join(item.id for item in load_libraries(repo.root)), file=sys.stderr)
            return EXIT_ERROR
        print(f"{library.id} - {library.name} {library.version}")
        print(f"  category:  {library.category}")
        print(f"  license:   {library.license}")
        print(f"  copyright: {library.copyright}")
        print(f"  script:    {library.site_script}")
        if library.site_css:
            print(f"  css:       {library.site_css}")
        print(f"  purpose:   {library.purpose}")
        print(f"  upstream:  {library.upstream}")
        print(f"  folder:    {library.path}")
        return EXIT_OK
    for library in load_libraries(repo.root):
        print(f"{library.id:<12} {library.version:<9} {library.license:<8} {library.category:<10} {library.name}")
    return EXIT_OK


def cmd_browser(repo: Repo, args: argparse.Namespace) -> int:
    """Install and drive the optional Obscura runtime (no import, no daemon)."""
    import subprocess

    from .browser import BrowserError, BrowserManager

    manager = BrowserManager()
    action = args.action
    try:
        if action == "status":
            status = manager.status()
            if args.as_json:
                print(json.dumps(status, indent=2, ensure_ascii=False))
                return EXIT_OK
            print(f"Obscura AI browser {status['version']} ({status['license']})")
            print(f"  platform:  {status['platform_label']}")
            print(f"  installed: {'yes' if status['installed'] else 'no'}")
            if status["installed"]:
                print(f"  binary:    {status['binary']}")
                print(f"  installed: {status['installed_at']}")
            else:
                print(f"  download:  {status['download_url'] or '-'}")
                if status["download_bytes"]:
                    print(f"  size:      {status['download_bytes'] / 1024 / 1024:.1f} MB")
                print("  install:   stitch browser install")
            if status["missing_reason"]:
                print(f"  note:      {status['missing_reason']}")
            return EXIT_OK

        if action == "install":
            status = manager.status()
            if not status["supported"]:
                print(f"stitch browser: {status['missing_reason']}", file=sys.stderr)
                return EXIT_ERROR
            print(f"Installing Obscura {status['version']} ({status['license']})")
            print(f"  download: {status['download_url']}")
            print(f"  size:     {status['download_bytes'] / 1024 / 1024:.1f} MB")
            last = [-1]

            def progress(done: int, total: int) -> None:
                percent = int((done / total) * 100) if total else 0
                if percent >= last[0] + 5 or percent == 100:
                    last[0] = percent
                    print(f"  downloading: {percent:3d}%  ({done / 1024 / 1024:5.1f} MB)")

            installed = manager.install(progress=progress)
            print(f"Installed: {installed['binary']}")
            print(f"License:   {installed['license']} — see LICENSE/NOTICE in the install directory.")
            return EXIT_OK

        if action == "remove":
            removed = manager.remove()
            print("Removed the local Obscura runtime." if removed else "No local Obscura runtime was installed.")
            return EXIT_OK

        if action == "check":
            if not args.url:
                print("stitch browser check: --url is required", file=sys.stderr)
                return EXIT_ERROR
            report = manager.check(
                args.url,
                args.out,
                timeout=args.timeout,
                screenshot=not args.no_screenshot,
            )
            if args.as_json:
                print(json.dumps(report, indent=2, ensure_ascii=False))
            else:
                state = "ok" if report["ok"] else "needs attention"
                print(f"Browser check: {state}")
                print(f"  title:    {report['title'] or '-'}")
                print(f"  language: {report['lang'] or '-'}")
                print(f"  h1:       {report['h1']}")
                print(f"  text:     {report['text_chars']} chars")
                if report["screenshot"]:
                    print(f"  shot:     {_display(Path(report['screenshot']), repo.root)}")
                for warning in report["warnings"]:
                    print(f"  warning:  {warning}")
            return EXIT_OK if report["ok"] else EXIT_FINDINGS

        if action in {"serve", "mcp"}:
            if action == "serve":
                command = manager.serve_command(
                    args.port,
                    allow_private_network=True,
                    stealth=args.stealth,
                )
            else:
                command = manager.mcp_command(http_port=args.port if args.http else None, stealth=args.stealth)
            print("Running: " + " ".join(command))
            return int(subprocess.call(command))
    except BrowserError as exc:
        print(f"stitch browser: {exc}", file=sys.stderr)
        return EXIT_ERROR
    return EXIT_ERROR


def cmd_benchmark(repo: Repo, args: argparse.Namespace) -> int:
    from . import settings as settings_module
    from .benchmark import BenchmarkError, load_tasks, run_benchmarks

    try:
        tasks = load_tasks(repo.root, args.task)
    except BenchmarkError as exc:
        print(f"stitch benchmark: {exc}", file=sys.stderr)
        return EXIT_ERROR
    out_dir = None
    if args.out is not None:
        out_dir = args.out if args.out.is_absolute() else repo.root / args.out
    config = settings_module.load_config()
    report = run_benchmarks(
        repo.root,
        config,
        tasks,
        engine=args.engine,
        repeat=max(1, int(args.repeat or 1)),
        out_dir=out_dir,
    )
    summary = report["summary"]
    print(f"Acceptance benchmark ({report['engine']}) — {summary['total']} attempt(s), {len(report['tasks'])} task(s)")
    print()
    for item in report["results"]:
        marker = "PASS" if item["ok"] else "FAIL"
        detail = f"{item['files']} files, {len(item['warnings'])} warning(s)"
        if item.get("missing_files"):
            detail += ", missing: " + ", ".join(item["missing_files"])
        if item.get("error"):
            detail += ", error: " + str(item["error"])[:120]
        print(f"  [{marker}] {item['task']:<22} {item['duration_ms']:>6} ms  {detail}")
    print()
    print(
        f"summary: {summary['passed']}/{summary['total']} passed · "
        f"first-pass {summary['first_pass_rate'] * 100:.0f}% · "
        f"average {summary['average_duration_ms']} ms · repairs {summary['repairs']}"
    )
    print(f"  report: {_display(Path(report['report_dir']), repo.root)}")
    return EXIT_OK if summary["failed"] == 0 else EXIT_FINDINGS


def cmd_generate(repo: Repo, args: argparse.Namespace) -> int:
    from . import settings as settings_module
    from .generator import GenerationError, GenerationRequest, generate_site
    from .themes import get_theme

    theme = get_theme(repo.root, args.theme)
    if theme is None:
        print(f"stitch: unknown theme '{args.theme}'", file=sys.stderr)
        return EXIT_ERROR
    if args.database == "remote" and not args.db_url:
        print("stitch: --database remote needs --db-url", file=sys.stderr)
        return EXIT_ERROR
    database = {"mode": args.database, "remote": {}}
    if args.database == "remote":
        database["remote"] = {
            "kind": args.db_kind,
            "url": args.db_url,
            "anon_key": args.db_key,
            "table_prefix": args.db_prefix,
        }
    out_dir = Path(args.out) if args.out else repo.root / ".stitch" / "generated" / args.theme
    request = GenerationRequest(
        theme_id=args.theme,
        prompt=args.prompt,
        title=args.title or theme.name,
        engine=args.engine,
        database=database,
    )

    def progress(index: int, status: str, message: str | None = None, level: str = "info") -> None:
        if status in {"active", "done"} and message:
            print(f"  [{index + 1}/9] {message}")

    try:
        result = generate_site(
            repo.root,
            settings_module.load_config(),
            request,
            out_dir,
            on_progress=progress,
            force=args.force,
        )
    except GenerationError as exc:
        print(f"stitch generate: {exc}", file=sys.stderr)
        return EXIT_ERROR
    print()
    print(f"Generated: {result.title} ({result.engine})")
    print(f"  output:  {_display(out_dir, repo.root)}")
    print(f"  files:   {len(result.files)}")
    print(f"  summary: {result.summary}")
    for warning in result.warnings:
        print(f"  warning: {warning}")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
