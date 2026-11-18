"""Local settings for the Stitchcraft desktop studio.

Settings — including AI API keys and remote-database credentials — live only in
the user's app-data directory. They are never committed to the repository and
never written into generated sites; only the remote database URL / public anon
key that the user explicitly configures is embedded into a generated site.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

PRESETS: dict[str, dict[str, str]] = {
    "openai": {
        "label": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
    },
    "deepseek": {
        "label": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
    },
    "openrouter": {
        "label": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "model": "openai/gpt-4o-mini",
    },
    "ollama": {
        "label": "Ollama (local)",
        "base_url": "http://127.0.0.1:11434/v1",
        "model": "llama3.1",
    },
    "custom": {"label": "Custom OpenAI-compatible", "base_url": "", "model": ""},
}


def app_dir() -> Path:
    """Directory that holds config, projects and logs for this user."""
    override = os.environ.get("STITCHCRAFT_HOME")
    if override:
        return Path(override).expanduser()
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "Stitchcraft"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Stitchcraft"
    return Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "stitchcraft"


def config_path() -> Path:
    return app_dir() / "config.json"


def _clamp_temperature(value: object, fallback: float = 0.7) -> float:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return fallback
    return max(0.0, min(2.0, number))


@dataclass
class AISettings:
    provider: str = "openai"
    base_url: str = PRESETS["openai"]["base_url"]
    model: str = PRESETS["openai"]["model"]
    temperature: float = 0.7
    api_key: str = ""

    def public_dict(self) -> dict:
        return {
            "provider": self.provider,
            "base_url": self.base_url,
            "model": self.model,
            "temperature": self.temperature,
            "has_key": bool(self.api_key),
            "key_hint": ("..." + self.api_key[-4:]) if len(self.api_key) >= 8 else "",
        }


@dataclass
class RemoteDatabaseSettings:
    kind: str = "supabase"
    url: str = ""
    anon_key: str = ""
    table_prefix: str = "stitchcraft"

    def public_dict(self) -> dict:
        return {
            "kind": self.kind,
            "url": self.url,
            "table_prefix": self.table_prefix,
            "has_key": bool(self.anon_key),
            "key_hint": ("..." + self.anon_key[-4:]) if len(self.anon_key) >= 8 else "",
        }


@dataclass
class DatabaseSettings:
    mode: str = "local"
    remote: RemoteDatabaseSettings = field(default_factory=RemoteDatabaseSettings)

    def public_dict(self) -> dict:
        return {"mode": self.mode, "remote": self.remote.public_dict()}


@dataclass
class UISettings:
    theme: str = "kiroween"
    demo_mode: bool = True

    def public_dict(self) -> dict:
        return {"theme": self.theme, "demo_mode": self.demo_mode}


@dataclass
class AppConfig:
    ai: AISettings = field(default_factory=AISettings)
    database: DatabaseSettings = field(default_factory=DatabaseSettings)
    ui: UISettings = field(default_factory=UISettings)

    def public_dict(self) -> dict:
        return {
            "ai": self.ai.public_dict(),
            "database": self.database.public_dict(),
            "ui": self.ui.public_dict(),
        }

    def to_dict(self) -> dict:
        return {
            "ai": {
                "provider": self.ai.provider,
                "base_url": self.ai.base_url,
                "model": self.ai.model,
                "temperature": self.ai.temperature,
                "api_key": self.ai.api_key,
            },
            "database": {
                "mode": self.database.mode,
                "remote": {
                    "kind": self.database.remote.kind,
                    "url": self.database.remote.url,
                    "anon_key": self.database.remote.anon_key,
                    "table_prefix": self.database.remote.table_prefix,
                },
            },
            "ui": {"theme": self.ui.theme, "demo_mode": self.ui.demo_mode},
        }

    def merge_patch(self, payload: dict) -> "AppConfig":
        """Apply a partially-filled settings payload; blank secrets are kept."""
        if not isinstance(payload, dict):
            return self
        ai = payload.get("ai") or {}
        provider = str(ai.get("provider", self.ai.provider)).strip() or self.ai.provider
        self.ai.provider = provider
        preset = PRESETS.get(provider, {})
        base_url = str(ai.get("base_url", self.ai.base_url)).strip()
        model = str(ai.get("model", self.ai.model)).strip()
        self.ai.base_url = base_url or preset.get("base_url", self.ai.base_url)
        self.ai.model = model or preset.get("model", self.ai.model)
        if "temperature" in ai:
            self.ai.temperature = _clamp_temperature(ai.get("temperature"), self.ai.temperature)
        api_key = ai.get("api_key")
        if isinstance(api_key, str) and api_key.strip():
            self.ai.api_key = api_key.strip()
        if ai.get("clear_api_key"):
            self.ai.api_key = ""

        database = payload.get("database") or {}
        mode = str(database.get("mode", self.database.mode)).strip()
        if mode in {"local", "remote"}:
            self.database.mode = mode
        remote = database.get("remote") or {}
        kind = str(remote.get("kind", self.database.remote.kind)).strip()
        if kind in {"supabase", "rest"}:
            self.database.remote.kind = kind
        if "url" in remote:
            self.database.remote.url = str(remote.get("url") or "").strip()
        if "table_prefix" in remote:
            prefix = str(remote.get("table_prefix") or "").strip()
            self.database.remote.table_prefix = prefix or "stitchcraft"
        anon_key = remote.get("anon_key")
        if isinstance(anon_key, str) and anon_key.strip():
            self.database.remote.anon_key = anon_key.strip()
        if remote.get("clear_anon_key"):
            self.database.remote.anon_key = ""

        ui = payload.get("ui") or {}
        if "theme" in ui:
            self.ui.theme = str(ui.get("theme") or "kiroween")
        if "demo_mode" in ui:
            self.ui.demo_mode = bool(ui.get("demo_mode"))
        return self


def _from_dict(data: dict) -> AppConfig:
    config = AppConfig()
    if not isinstance(data, dict):
        return config
    config.merge_patch(data)
    return config


def load_config(path: Path | None = None) -> AppConfig:
    target = Path(path) if path is not None else config_path()
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return AppConfig()
    return _from_dict(data)


def save_config(config: AppConfig, path: Path | None = None) -> Path:
    target = Path(path) if path is not None else config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(config.to_dict(), indent=2) + "\n", encoding="utf-8")
    try:  # best effort on Windows
        os.chmod(target, 0o600)
    except OSError:
        pass
    return target


def mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 6:
        return "***"
    return value[:2] + "***" + value[-2:]
