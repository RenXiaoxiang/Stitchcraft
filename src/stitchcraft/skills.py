"""Skill registry: vendored agent skills that are injected into generations.

Skills are data, not code. The desktop generator selects the skills a theme
declares (or the user overrides) and serialises their `SKILL.md` guidance into
the AI prompt under a character budget, so a single generation can lean on
Chrome's Modern Web Guidance, the official GSAP skills and our house skills.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

REGISTRY = Path("skills") / "registry.toml"

__all__ = [
    "Skill",
    "build_skill_context",
    "get_skill",
    "load_registry",
    "read_skill_text",
    "verify_registry",
]


@dataclass(frozen=True)
class Skill:
    id: str
    name: str
    category: str
    source: str
    license: str
    path: str
    summary: str
    stages: tuple[str, ...]
    enabled: bool
    budget_chars: int
    kind: str
    root: Path

    @property
    def folder(self) -> Path:
        return self.root / self.path

    @property
    def skill_path(self) -> Path | None:
        direct = self.folder / "SKILL.md"
        if direct.is_file():
            return direct
        candidates = sorted(self.folder.rglob("SKILL.md"))
        return candidates[0] if candidates else None

    @property
    def license_path(self) -> Path | None:
        """Find the LICENSE near the skill (pack-root licenses are shared)."""
        vendor_root = self.root / "skills" / "vendor"
        for base in (self.folder, *self.folder.parents):
            for name in ("LICENSE", "LICENSE.md", "LICENSE.txt"):
                candidate = base / name
                if candidate.is_file():
                    return candidate
            if base == vendor_root or base == self.root:
                break
        return None

    @property
    def upstream_path(self) -> Path | None:
        vendor_root = self.root / "skills" / "vendor"
        for base in (self.folder, *self.folder.parents):
            candidate = base / "UPSTREAM.md"
            if candidate.is_file():
                return candidate
            if base == vendor_root or base == self.root:
                break
        return None


def load_registry(root: Path) -> tuple[Skill, ...]:
    path = Path(root) / REGISTRY
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, tomllib.TOMLDecodeError):
        return ()
    entries = data.get("skills") or data.get("skill") or []
    skills: list[Skill] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        skill_id = str(entry.get("id", "")).strip()
        if not skill_id:
            continue
        skills.append(
            Skill(
                id=skill_id,
                name=str(entry.get("name", skill_id)),
                category=str(entry.get("category", "general")),
                source=str(entry.get("source", "")),
                license=str(entry.get("license", "")),
                path=str(entry.get("path", "")),
                summary=str(entry.get("summary", "")),
                stages=tuple(str(stage) for stage in entry.get("stages", [])),
                enabled=bool(entry.get("enabled", True)),
                budget_chars=int(entry.get("budget_chars", 4000)),
                kind=str(entry.get("kind", "skill")),
                root=Path(root),
            )
        )
    return tuple(skills)


def get_skill(root: Path, skill_id: str) -> Skill | None:
    for skill in load_registry(root):
        if skill.id == skill_id:
            return skill
    return None


def read_skill_text(root: Path, skill: Skill, max_chars: int | None = None) -> str:
    path = skill.skill_path
    if path is None:
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    limit = max_chars if max_chars is not None else skill.budget_chars or 4000
    if limit and len(text) > limit:
        return text[:limit].rstrip() + "\n\n[... skill truncated to fit the prompt budget ...]"
    return text


def select_for_theme(root: Path, skill_ids: list[str] | tuple[str, ...] | None = None) -> list[Skill]:
    registry = load_registry(root)
    if not skill_ids:
        return [skill for skill in registry if skill.enabled and skill.kind == "skill"]
    wanted = [str(item) for item in skill_ids]
    selected: list[Skill] = []
    for skill in registry:
        if skill.id in wanted and skill.enabled and skill.kind == "skill":
            selected.append(skill)
    return selected


def build_skill_context(
    root: Path,
    skill_ids: list[str] | tuple[str, ...] | None,
    budget_chars: int = 24000,
) -> str:
    """Serialise the selected skills into one prompt section."""
    selected = select_for_theme(root, skill_ids)
    if not selected:
        return ""
    blocks: list[str] = []
    used = 0
    for skill in selected:
        remaining = max(600, budget_chars - used)
        text = read_skill_text(root, skill, min(skill.budget_chars or 4000, remaining))
        if not text:
            continue
        header = f"### {skill.name} ({skill.license}; {skill.source})"
        block = header + "\n\n" + text.strip()
        if used + len(block) > budget_chars and blocks:
            break
        blocks.append(block)
        used += len(block)
    if not blocks:
        return ""
    return (
        "The following skills are bundled with this generator and must inform the build. "
        "Apply them as guidance, not as text to copy.\n\n" + "\n\n---\n\n".join(blocks)
    )


def verify_registry(root: Path) -> list[str]:
    """Return human-readable findings; empty list means healthy."""
    findings: list[str] = []
    path = Path(root) / REGISTRY
    if not path.is_file():
        return [f"missing skill registry: {REGISTRY.as_posix()}"]
    try:
        tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        return [f"invalid TOML in {REGISTRY.as_posix()}: {exc}"]
    skills = load_registry(root)
    if not skills:
        findings.append(f"{REGISTRY.as_posix()} declares no skills")
    seen: set[str] = set()
    for skill in skills:
        if skill.id in seen:
            findings.append(f"duplicate skill id: {skill.id}")
        seen.add(skill.id)
        if not skill.path:
            findings.append(f"skill '{skill.id}' has no path")
            continue
        folder = skill.folder
        if not folder.is_dir():
            findings.append(f"skill '{skill.id}' path does not exist: {skill.path}")
            continue
        if skill.kind != "asset" and skill.skill_path is None:
            findings.append(f"skill '{skill.id}' has no SKILL.md under {skill.path}")
        if skill.kind == "asset" and not any(folder.iterdir()):
            findings.append(f"asset '{skill.id}' folder is empty: {skill.path}")
        if skill.path.startswith("skills/vendor/"):
            licensed = skill.license_path is not None
            if skill.kind == "asset":
                licensed = licensed or skill.upstream_path is not None
            if not licensed:
                findings.append(f"vendored skill '{skill.id}' is missing its LICENSE/UPSTREAM evidence")
    return findings
