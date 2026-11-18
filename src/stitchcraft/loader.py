"""Load a Stitchcraft repo from disk.

All configuration is data: `pipeline/pipeline.toml`, one `module.toml` per
module, and one JSON Schema per artifact. Nothing here imports site templates,
runner code or an LLM — loading must stay deterministic and offline.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

from .model import Module, Project, Repo, Stage

PIPELINE = Path("pipeline") / "pipeline.toml"

__all__ = [
    "LoadError",
    "find_root",
    "load_contracts",
    "load_modules",
    "load_repo",
    "load_schema",
    "load_stages",
]


class LoadError(RuntimeError):
    """Raised when the repo cannot be loaded at all."""


def find_root(start: Path | None = None) -> Path:
    """Walk upwards until a `pipeline/pipeline.toml` is found."""
    current = Path(start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / PIPELINE).is_file():
            return candidate
    raise LoadError(f"no pipeline/pipeline.toml found at or above {current}")


def _read_toml(path: Path) -> dict:
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except FileNotFoundError as exc:
        raise LoadError(f"missing file: {path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise LoadError(f"invalid TOML in {path}: {exc}") from exc


def _parse_project(data: dict, path: Path) -> Project:
    project = data.get("project")
    if not isinstance(project, dict):
        raise LoadError(f"{path}: missing [project] table")
    missing = [key for key in ("name",) if not str(project.get(key, "")).strip()]
    if missing:
        raise LoadError(f"{path}: missing project key(s): {', '.join(missing)}")
    return Project(
        name=str(project["name"]),
        version=str(project.get("version", "0.0.0")),
        artifact_dir=str(project.get("artifact_dir", ".stitch")),
        default_profile=str(project.get("default_profile", "solo")),
    )


def load_stages(root: Path) -> tuple[Stage, ...]:
    """Load `[[stages]]` from `pipeline/pipeline.toml`."""
    path = root / PIPELINE
    data = _read_toml(path)
    raw_stages = data.get("stages", [])
    if not isinstance(raw_stages, list):
        raise LoadError(f"{path}: [[stages]] must be a list of tables")
    stages: list[Stage] = []
    for index, raw in enumerate(raw_stages, start=1):
        if not isinstance(raw, dict):
            raise LoadError(f"{path}: stage #{index} is not a table")
        stages.append(
            Stage(
                id=str(raw.get("id", "")).strip(),
                module=str(raw.get("module", "")).strip(),
                depends_on=tuple(str(dep).strip() for dep in raw.get("depends_on", [])),
                gate=bool(raw.get("gate", False)),
                description=str(raw.get("description", "")).strip(),
            )
        )
    return tuple(stages)


def load_modules(root: Path) -> tuple[Module, ...]:
    """Load every `modules/*/module.toml`, sorted by path."""
    modules_dir = root / "modules"
    if not modules_dir.is_dir():
        raise LoadError(f"missing modules/ directory at {modules_dir}")
    manifests = sorted(modules_dir.glob("*/module.toml"))
    if not manifests:
        raise LoadError(f"no module manifests found under {modules_dir}")
    modules: list[Module] = []
    for manifest in manifests:
        data = _read_toml(manifest)
        raw = data.get("module")
        if not isinstance(raw, dict):
            raise LoadError(f"{manifest}: missing [module] table")
        missing = [key for key in ("id", "name") if not str(raw.get(key, "")).strip()]
        if missing:
            raise LoadError(f"{manifest}: missing module key(s): {', '.join(missing)}")
        modules.append(
            Module(
                id=str(raw["id"]).strip(),
                name=str(raw["name"]).strip(),
                stage=int(raw.get("stage", 0)),
                summary=str(raw.get("summary", "")).strip(),
                skill=str(raw.get("skill", "SKILL.md")).strip(),
                consumes=tuple(str(item).strip() for item in raw.get("consumes", [])),
                produces=tuple(str(item).strip() for item in raw.get("produces", [])),
                gate=bool(raw.get("gate", False)),
                path=manifest.parent,
            )
        )
    return tuple(modules)


def load_contracts(root: Path) -> tuple[str, ...]:
    """Return artifact names discovered from `contracts/*.schema.json`."""
    contracts_dir = root / "contracts"
    if not contracts_dir.is_dir():
        return ()
    suffix = ".schema.json"
    return tuple(
        path.name[: -len(suffix)]
        for path in sorted(contracts_dir.glob(f"*{suffix}"))
    )


def load_schema(root: Path, artifact: str) -> dict:
    """Load one artifact contract as a JSON object."""
    path = root / "contracts" / f"{artifact}.schema.json"
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise LoadError(f"missing contract for artifact '{artifact}': {path}") from exc
    except json.JSONDecodeError as exc:
        raise LoadError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise LoadError(f"{path}: contract must be a JSON object")
    return data


def load_repo(root: Path | None = None) -> Repo:
    """Load the complete stitch, ready for validation."""
    project_root = find_root(root)
    pipeline_path = project_root / PIPELINE
    data = _read_toml(pipeline_path)
    return Repo(
        root=project_root,
        project=_parse_project(data, pipeline_path),
        modules=load_modules(project_root),
        stages=load_stages(project_root),
        contracts=load_contracts(project_root),
    )
