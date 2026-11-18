"""Theme packages: the module library a generated site starts from.

A theme is a data package, not code: `theme.toml` declares its identity, blocks
and skill picks; `SKILL.md` is the composition guide injected into the AI prompt;
`data-model.json` describes the collections a data theme needs; and an optional
`sample/` folder holds a complete, working demo site used by demo mode and the
GitHub Pages showcase.
"""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass
from pathlib import Path

REGISTRY = Path("themes") / "registry.toml"

__all__ = [
    "Theme",
    "get_theme",
    "load_data_model",
    "load_themes",
    "sample_dir",
    "theme_skill_text",
    "verify_themes",
]


@dataclass(frozen=True)
class Theme:
    id: str
    name: str
    category: str
    summary: str
    accent: str
    tags: tuple[str, ...]
    blocks: tuple[str, ...]
    skills: tuple[str, ...]
    libraries: tuple[str, ...]
    data_model: str
    sample: str
    path: str
    root: Path

    @property
    def folder(self) -> Path:
        return self.root / self.path

    @property
    def skill_path(self) -> Path:
        return self.folder / "SKILL.md"

    @property
    def data_model_path(self) -> Path | None:
        if not self.data_model:
            return None
        candidate = self.folder / self.data_model
        return candidate if candidate.is_file() else None

    @property
    def sample_path(self) -> Path | None:
        if not self.sample:
            return None
        candidate = self.folder / self.sample
        return candidate if candidate.is_dir() else None

    @property
    def has_sample(self) -> bool:
        return self.sample_path is not None and (self.sample_path / "index.html").is_file()

    def public_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "summary": self.summary,
            "accent": self.accent,
            "tags": list(self.tags),
            "blocks": list(self.blocks),
            "skills": list(self.skills),
            "libraries": list(self.libraries),
            "has_sample": self.has_sample,
            "path": self.path,
        }


def _parse_theme(root: Path, path: str, entry: dict) -> Theme | None:
    folder = root / path
    data: dict = {}
    if (folder / "theme.toml").is_file():
        try:
            data = tomllib.loads((folder / "theme.toml").read_text(encoding="utf-8")).get("theme", {})
        except tomllib.TOMLDecodeError:
            return None
    merged = {**entry, **data}
    theme_id = str(merged.get("id", "")).strip()
    if not theme_id:
        return None
    return Theme(
        id=theme_id,
        name=str(merged.get("name", theme_id)),
        category=str(merged.get("category", "data")),
        summary=str(merged.get("summary", "")),
        accent=str(merged.get("accent", "#ff8a3d")),
        tags=tuple(str(item) for item in merged.get("tags", [])),
        blocks=tuple(str(item) for item in merged.get("blocks", [])),
        skills=tuple(str(item) for item in merged.get("skills", [])),
        libraries=tuple(str(item) for item in merged.get("libraries", [])),
        data_model=str(merged.get("data_model", "")),
        sample=str(merged.get("sample", "")),
        path=path,
        root=root,
    )


def load_themes(root: Path) -> tuple[Theme, ...]:
    root = Path(root)
    registry_path = root / REGISTRY
    themes: list[Theme] = []
    if registry_path.is_file():
        try:
            data = tomllib.loads(registry_path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError:
            data = {}
        for entry in data.get("themes") or data.get("theme") or []:
            if not isinstance(entry, dict):
                continue
            path = str(entry.get("path", "")).strip()
            if not path:
                theme_id = str(entry.get("id", "")).strip()
                path = f"themes/{theme_id}" if theme_id else ""
            if not path:
                continue
            theme = _parse_theme(root, path, entry)
            if theme is not None:
                themes.append(theme)
    if not themes:
        for manifest in sorted((root / "themes").glob("*/theme.toml")):
            theme = _parse_theme(root, f"themes/{manifest.parent.name}", {})
            if theme is not None:
                themes.append(theme)
    return tuple(themes)


def get_theme(root: Path, theme_id: str) -> Theme | None:
    for theme in load_themes(root):
        if theme.id == theme_id:
            return theme
    return None


def theme_skill_text(root: Path, theme: Theme) -> str:
    try:
        return theme.skill_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def load_data_model(root: Path, theme: Theme) -> dict | None:
    path = theme.data_model_path
    if path is None:
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def sample_dir(root: Path, theme: Theme) -> Path | None:
    return theme.sample_path if theme.has_sample else None


def verify_themes(root: Path) -> list[str]:
    """Return human-readable findings; empty list means healthy."""
    root = Path(root)
    findings: list[str] = []
    registry_path = root / REGISTRY
    if not registry_path.is_file():
        findings.append(f"missing theme registry: {REGISTRY.as_posix()}")
    themes = load_themes(root)
    if not themes:
        findings.append("no themes discovered under themes/")
    seen: set[str] = set()
    for theme in themes:
        if theme.id in seen:
            findings.append(f"duplicate theme id: {theme.id}")
        seen.add(theme.id)
        if not theme.folder.is_dir():
            findings.append(f"theme '{theme.id}' folder does not exist: {theme.path}")
            continue
        if not theme.skill_path.is_file():
            findings.append(f"theme '{theme.id}' is missing SKILL.md")
        else:
            text = theme.skill_path.read_text(encoding="utf-8", errors="replace")
            for section in ("## Job", "## Layout blueprint", "## Quality bar", "## Output contract"):
                if section not in text:
                    findings.append(f"theme '{theme.id}' SKILL.md is missing '{section}'")
        if theme.data_model:
            if theme.data_model_path is None:
                findings.append(f"theme '{theme.id}' declares data_model '{theme.data_model}' but it does not exist")
            else:
                try:
                    json.loads(theme.data_model_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError as exc:
                    findings.append(f"theme '{theme.id}' data model is invalid JSON: {exc}")
        block_dir = root / "themes" / "_blocks"
        for block in theme.blocks:
            if not (block_dir / f"{block}.html").is_file():
                findings.append(f"theme '{theme.id}' references missing block '{block}.html'")
        if theme.sample and not theme.has_sample:
            findings.append(f"theme '{theme.id}' declares sample '{theme.sample}' but no sample/index.html exists")
    return findings
