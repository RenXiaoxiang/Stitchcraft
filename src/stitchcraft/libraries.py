"""Aggregated open-source browser libraries ("tool packs") for generated sites.

Third-party browser libraries live under `vendor/` and are vendored unmodified
with their LICENSE and UPSTREAM notes. Themes declare the packs they may use;
the generator injects usage guidance into the AI prompt and copies only the
libraries a generated site actually references into `site/vendor/<id>/`.
No CDN is ever required at runtime.
"""

from __future__ import annotations

import shutil
import tomllib
from dataclasses import dataclass
from pathlib import Path

REGISTRY = Path("vendor") / "registry.toml"

__all__ = [
    "Library",
    "build_prompt_context",
    "copy_library",
    "copy_used",
    "get_library",
    "libraries_for_theme",
    "load_libraries",
    "verify_libraries",
]


@dataclass(frozen=True)
class Library:
    id: str
    name: str
    category: str
    version: str
    license: str
    copyright: str
    upstream: str
    path: str
    dist: str
    css: str
    size_bytes: int
    purpose: str
    usage: str
    root: Path

    @property
    def folder(self) -> Path:
        return self.root / self.path

    @property
    def dist_path(self) -> Path:
        return self.folder / self.dist

    @property
    def css_path(self) -> Path | None:
        return self.folder / self.css if self.css else None

    @property
    def license_path(self) -> Path | None:
        for name in ("LICENSE", "LICENSE.md", "LICENSE.txt"):
            candidate = self.folder / name
            if candidate.is_file():
                return candidate
        return None

    @property
    def upstream_path(self) -> Path | None:
        candidate = self.folder / "UPSTREAM.md"
        return candidate if candidate.is_file() else None

    @property
    def readme_path(self) -> Path | None:
        candidate = self.folder / "README.md"
        return candidate if candidate.is_file() else None

    @property
    def site_script(self) -> str:
        return f"{self.path}/{self.dist}"

    @property
    def site_css(self) -> str:
        return f"{self.path}/{self.css}" if self.css else ""

    def public_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "version": self.version,
            "license": self.license,
            "copyright": self.copyright,
            "upstream": self.upstream,
            "purpose": self.purpose,
            "usage": self.usage,
            "script": self.site_script,
            "css": self.site_css,
            "size_bytes": self.size_bytes,
        }


def load_libraries(root: Path) -> tuple[Library, ...]:
    path = Path(root) / REGISTRY
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, tomllib.TOMLDecodeError):
        return ()
    libraries: list[Library] = []
    for entry in data.get("libraries") or data.get("library") or []:
        if not isinstance(entry, dict):
            continue
        library_id = str(entry.get("id", "")).strip()
        if not library_id:
            continue
        libraries.append(
            Library(
                id=library_id,
                name=str(entry.get("name", library_id)),
                category=str(entry.get("category", "utility")),
                version=str(entry.get("version", "")),
                license=str(entry.get("license", "")),
                copyright=str(entry.get("copyright", "")),
                upstream=str(entry.get("upstream", "")),
                path=str(entry.get("path", f"vendor/{library_id}")),
                dist=str(entry.get("dist", "")),
                css=str(entry.get("css", "")),
                size_bytes=int(entry.get("size_bytes", 0)),
                purpose=str(entry.get("purpose", "")),
                usage=str(entry.get("usage", "")),
                root=Path(root),
            )
        )
    return tuple(libraries)


def get_library(root: Path, library_id: str) -> Library | None:
    for library in load_libraries(root):
        if library.id == library_id:
            return library
    return None


def libraries_for_theme(root: Path, theme) -> list[Library]:
    """Resolve the library ids a theme declares; unknown ids are ignored."""
    known = {library.id: library for library in load_libraries(root)}
    return [known[library_id] for library_id in getattr(theme, "libraries", ()) if library_id in known]


def build_prompt_context(libraries: list[Library]) -> str:
    """Render the vendored-library section injected into the generation prompt."""
    if not libraries:
        return ""
    lines = [
        "The following browser libraries are bundled offline with this generator. "
        "Reference them with the exact relative paths below (the generator copies the "
        "files into the generated site). Never use a CDN or an external URL.",
        "",
    ]
    for library in libraries:
        lines.append(f"### {library.name} {library.version} ({library.license}) — {library.purpose}")
        lines.append(f"- Script: `<script src=\"{library.site_script}\"></script>`")
        if library.site_css:
            lines.append(f"- Stylesheet: `<link rel=\"stylesheet\" href=\"{library.site_css}\">`")
        if library.usage:
            lines.append(f"- Usage: {library.usage}")
        lines.append("")
    return "\n".join(lines).strip()


def copy_library(library: Library, out_dir: Path) -> list[str]:
    """Copy a library's distributed files + license into a generated site."""
    out_dir = Path(out_dir)
    target = out_dir / library.path
    target.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for source in (library.dist_path, library.css_path, library.license_path, library.upstream_path):
        if source is None or not Path(source).is_file():
            continue
        destination = target / Path(source).name
        shutil.copy2(source, destination)
        copied.append(destination.relative_to(out_dir).as_posix())
    # Bundler-generated sidecars such as `gridstack-all.js.LICENSE.txt` must
    # travel with the dist file so the banner's license pointer resolves.
    for extra in sorted(library.folder.glob("*LICENSE*")):
        if extra.is_file() and extra.name != "LICENSE":
            destination = target / extra.name
            if destination.is_file():
                continue
            shutil.copy2(extra, destination)
            copied.append(destination.relative_to(out_dir).as_posix())
    return copied


def copy_used(libraries: list[Library], out_dir: Path) -> tuple[list[str], list[Library]]:
    """Copy only libraries referenced by the generated site's text files."""
    out_dir = Path(out_dir)
    haystack = ""
    for path in out_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".html", ".css", ".js", ".json", ".svg", ".md", ".txt"}:
            try:
                haystack += path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
    copied: list[str] = []
    used: list[Library] = []
    for library in libraries:
        markers = [library.site_script, f"{library.path}/", library.dist]
        if library.site_css:
            markers.append(library.site_css)
        if any(marker and marker in haystack for marker in markers):
            copied.extend(copy_library(library, out_dir))
            used.append(library)
    return copied, used


def verify_libraries(root: Path) -> list[str]:
    """Return human-readable findings; empty list means healthy."""
    root = Path(root)
    findings: list[str] = []
    path = root / REGISTRY
    if not path.is_file():
        return [f"missing library registry: {REGISTRY.as_posix()}"]
    try:
        tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        return [f"invalid TOML in {REGISTRY.as_posix()}: {exc}"]
    libraries = load_libraries(root)
    if not libraries:
        findings.append("vendor/registry.toml declares no libraries")
    seen: set[str] = set()
    for library in libraries:
        if library.id in seen:
            findings.append(f"duplicate library id: {library.id}")
        seen.add(library.id)
        if not library.dist:
            findings.append(f"library '{library.id}' has no dist file")
            continue
        if not library.folder.is_dir():
            findings.append(f"library '{library.id}' folder does not exist: {library.path}")
            continue
        if not library.dist_path.is_file():
            findings.append(f"library '{library.id}' dist is missing: {library.site_script}")
            continue
        actual_size = library.dist_path.stat().st_size
        if library.size_bytes and actual_size != library.size_bytes:
            findings.append(
                f"library '{library.id}' size mismatch (registry {library.size_bytes}, file {actual_size})"
            )
        if library.css and not (library.css_path and library.css_path.is_file()):
            findings.append(f"library '{library.id}' css is missing: {library.site_css}")
        if library.license_path is None:
            findings.append(f"library '{library.id}' is missing its LICENSE file")
        if library.upstream_path is None:
            findings.append(f"library '{library.id}' is missing UPSTREAM.md")
        if library.readme_path is None:
            findings.append(f"library '{library.id}' is missing README.md")
    return findings
