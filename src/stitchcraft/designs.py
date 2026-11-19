"""Design references (DESIGN.md) for the generator.

Themes can point at a vendored DESIGN.md document (Google Stitch format) with
`design_reference = "<id>"` in `theme.toml`. The generator injects an excerpt of
that document into the build prompt so a data dashboard or a brand landing page
can follow a coherent visual language.

All designs are vendored MIT material under `designs/vendor/<pack>/`; this module
only reads them and never edits them.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

REGISTRY = Path("designs") / "registry.toml"
VENDOR_ROOT = Path("designs") / "vendor"

__all__ = [
    "Design",
    "DesignError",
    "build_prompt_context",
    "get_design",
    "load_designs",
    "verify_designs",
]


class DesignError(RuntimeError):
    """Raised when a design reference cannot be loaded or verified."""


@dataclass(frozen=True)
class Design:
    id: str
    name: str
    brand: str
    source: str
    license: str
    path: str
    summary: str
    upstream: str
    root: Path

    @property
    def folder(self) -> Path:
        return self.root / self.path

    @property
    def design_path(self) -> Path | None:
        candidate = self.folder / "DESIGN.md"
        return candidate if candidate.is_file() else None

    @property
    def license_path(self) -> Path | None:
        for base in (self.folder, *self.folder.parents):
            for name in ("LICENSE", "LICENSE.md", "LICENSE.txt"):
                candidate = base / name
                if candidate.is_file():
                    return candidate
            if base == self.root / VENDOR_ROOT:
                break
        return None

    @property
    def upstream_path(self) -> Path | None:
        for base in (self.folder, *self.folder.parents):
            candidate = base / "UPSTREAM.md"
            if candidate.is_file():
                return candidate
            if base == self.root / VENDOR_ROOT:
                break
        return None

    def public_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "brand": self.brand,
            "source": self.source,
            "license": self.license,
            "summary": self.summary,
            "upstream": self.upstream,
        }


def load_designs(root: Path) -> tuple[Design, ...]:
    path = Path(root) / REGISTRY
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, tomllib.TOMLDecodeError):
        return ()
    entries = data.get("designs") or []
    designs: list[Design] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        design_id = str(entry.get("id", "")).strip()
        design_path = str(entry.get("path", "")).strip()
        if not design_id or not design_path:
            continue
        designs.append(
            Design(
                id=design_id,
                name=str(entry.get("name", design_id)),
                brand=str(entry.get("brand", "")),
                source=str(entry.get("source", "")),
                license=str(entry.get("license", "")),
                path=design_path,
                summary=str(entry.get("summary", "")),
                upstream=str(entry.get("upstream", "")),
                root=Path(root),
            )
        )
    return tuple(designs)


def get_design(root: Path, design_id: str) -> Design | None:
    for design in load_designs(root):
        if design.id == design_id:
            return design
    return None


def build_prompt_context(root: Path, design_id: str, max_chars: int = 8000) -> str:
    design = get_design(root, design_id)
    if design is None:
        raise DesignError(f"Unknown design reference '{design_id}'.")
    if design.design_path is None:
        raise DesignError(f"Design '{design_id}' has no DESIGN.md.")
    try:
        text = design.design_path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError as exc:
        raise DesignError(f"Could not read DESIGN.md for '{design_id}': {exc}") from exc
    if max_chars and len(text) > max_chars:
        text = text[:max_chars].rstrip() + "\n\n[... design reference truncated to fit the prompt budget ...]"
    return (
        f"### DESIGN.md reference: {design.name} ({design.license}; {design.source})\n\n"
        "Use this as visual guidance for palette, type scale, components, spacing, "
        "elevation and responsive behaviour. Write an original composition; do not "
        "copy brand assets, logos or proprietary copy.\n\n"
        + text
    )


def verify_designs(root: Path) -> list[str]:
    findings: list[str] = []
    path = Path(root) / REGISTRY
    if not path.is_file():
        return [f"missing design registry: {REGISTRY.as_posix()}"]
    try:
        tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        return [f"invalid TOML in {REGISTRY.as_posix()}: {exc}"]
    designs = load_designs(root)
    if not designs:
        findings.append(f"{REGISTRY.as_posix()} declares no designs")
    seen: set[str] = set()
    for design in designs:
        if design.id in seen:
            findings.append(f"duplicate design id: {design.id}")
        seen.add(design.id)
        if not design.path.startswith("designs/vendor/"):
            findings.append(f"design '{design.id}' is outside designs/vendor/: {design.path}")
        if not design.folder.is_dir():
            findings.append(f"design '{design.id}' path does not exist: {design.path}")
            continue
        if design.design_path is None:
            findings.append(f"design '{design.id}' has no DESIGN.md under {design.path}")
        if design.license_path is None:
            findings.append(f"design '{design.id}' is missing LICENSE evidence")
        if design.upstream_path is None:
            findings.append(f"design '{design.id}' is missing UPSTREAM.md evidence")
        if not design.license.strip():
            findings.append(f"design '{design.id}' has no license field")
        if not design.source.strip():
            findings.append(f"design '{design.id}' has no source field")
    return findings
