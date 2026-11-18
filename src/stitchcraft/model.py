"""Core data types for the Stitchcraft stitch.

A repo is deliberately small: a project identity, the modules, the stages that
wire them together, and the artifact contracts those stages exchange.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

__all__ = ["Issue", "Module", "Project", "Repo", "Stage", "replace"]


@dataclass(frozen=True)
class Project:
    """Identity declared in `pipeline/pipeline.toml`."""

    name: str
    version: str
    artifact_dir: str
    default_profile: str


@dataclass(frozen=True)
class Stage:
    """One seam in the stitch: a module plus the stages it depends on."""

    id: str
    module: str
    depends_on: tuple[str, ...] = ()
    gate: bool = False
    description: str = ""


@dataclass(frozen=True)
class Module:
    """One specialised job, declared by `modules/<slug>/module.toml`."""

    id: str
    name: str
    stage: int
    summary: str
    skill: str
    consumes: tuple[str, ...]
    produces: tuple[str, ...]
    gate: bool
    path: Path

    @property
    def slug(self) -> str:
        return self.path.name

    @property
    def skill_path(self) -> Path:
        return self.path / self.skill


@dataclass(frozen=True)
class Repo:
    """Everything the validator and the CLI need, loaded from disk."""

    root: Path
    project: Project
    modules: tuple[Module, ...]
    stages: tuple[Stage, ...]
    contracts: tuple[str, ...]

    def module(self, module_id: str) -> Module | None:
        for module in self.modules:
            if module.id == module_id:
                return module
        return None

    def stage(self, stage_id: str) -> Stage | None:
        for stage in self.stages:
            if stage.id == stage_id:
                return stage
        return None


@dataclass(frozen=True)
class Issue:
    """A single validation finding."""

    level: str
    code: str
    message: str
    where: str = ""

    def __str__(self) -> str:
        location = f" [{self.where}]" if self.where else ""
        return f"{self.level.upper():<7} {self.code}{location}: {self.message}"
