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

PRESETS: dict[str, dict[str, object]] = {
    # Free, no key required (community endpoint — rate limited, not for secrets).
    "pollinations": {
        "label": "Pollinations (free, no key)",
        "base_url": "https://text.pollinations.ai/openai",
        "model": "openai",
        "requires_key": False,
        "kind": "free-keyless",
        "compact": True,
        "note": "Free community endpoint, no API key. Free tier allows about one request per 30s per IP and short outputs — good for a first try, not for long sessions.",
        "key_url": "https://pollinations.ai",
    },
    # Free, runs on this machine (needs Ollama installed).
    "ollama": {
        "label": "Ollama (free, local)",
        "base_url": "http://127.0.0.1:11434/v1",
        "model": "llama3.1",
        "requires_key": False,
        "kind": "local",
        "compact": True,
        "note": "Runs on your machine. Install Ollama, run `ollama serve`, then `ollama pull llama3.1`.",
        "key_url": "https://ollama.com/download",
    },
    # Free tiers that need a free API key (China-friendly options included).
    "zhipu": {
        "label": "智谱 GLM-4-Flash (free, CN)",
        "base_url": "https://open.bigmodel.cn/api/paas/v4/",
        "model": "glm-4-flash",
        "requires_key": True,
        "kind": "free-key",
        "compact": True,
        "note": "国内可直连；glm-4-flash 永久免费，注册后创建免费 API Key。",
        "key_url": "https://open.bigmodel.cn/",
    },
    "siliconflow": {
        "label": "SiliconFlow 免费模型 (free, CN)",
        "base_url": "https://api.siliconflow.cn/v1",
        "model": "THUDM/GLM-Z1-9B-0414",
        "requires_key": True,
        "kind": "free-key",
        "compact": True,
        "note": "国内可直连；部分小模型 0 元，注册免费 Key，模型名以控制台为准。",
        "key_url": "https://cloud.siliconflow.cn/",
    },
    "groq": {
        "label": "Groq (free tier)",
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
        "requires_key": True,
        "kind": "free-key",
        "compact": False,
        "note": "Generous free tier with a free API key from console.groq.com.",
        "key_url": "https://console.groq.com/keys",
    },
    "gemini": {
        "label": "Google Gemini (free tier)",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model": "gemini-2.5-flash",
        "requires_key": True,
        "kind": "free-key",
        "compact": False,
        "note": "Free tier with a Google AI Studio key; check the current model names.",
        "key_url": "https://aistudio.google.com/apikey",
    },
    "openrouter": {
        "label": "OpenRouter (free models)",
        "base_url": "https://openrouter.ai/api/v1",
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "requires_key": True,
        "kind": "free-pool",
        "compact": False,
        "note": "Free models end with ':free' — type the exact id in the Model field.",
        "key_url": "https://openrouter.ai/keys",
    },
    "github": {
        "label": "GitHub Models (free with PAT)",
        "base_url": "https://models.github.ai/inference",
        "model": "openai/gpt-4o-mini",
        "requires_key": True,
        "kind": "free-key",
        "compact": False,
        "note": "Free quota with a GitHub account: create a PAT with the 'models: read' scope.",
        "key_url": "https://github.com/settings/tokens",
    },
    # Paid providers.
    "openai": {
        "label": "OpenAI (paid key)",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "requires_key": True,
        "kind": "paid",
        "note": "Requires a paid OpenAI API key.",
        "key_url": "https://platform.openai.com/api-keys",
    },
    "deepseek": {
        "label": "DeepSeek (paid key)",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "requires_key": True,
        "kind": "paid",
        "note": "DeepSeek's official API is paid (low cost); new accounts need a top-up. Use a free provider for zero-cost runs.",
        "key_url": "https://platform.deepseek.com/",
    },
    "custom": {
        "label": "Custom OpenAI-compatible",
        "base_url": "",
        "model": "",
        "requires_key": False,
        "kind": "custom",
        "note": "Any OpenAI-compatible endpoint. Leave the key blank for local or keyless servers.",
        "key_url": "",
    },
}

FREE_PROVIDER_IDS: tuple[str, ...] = (
    "pollinations",
    "ollama",
    "zhipu",
    "siliconflow",
    "groq",
    "gemini",
    "openrouter",
    "github",
)


def provider_requires_key(provider: str) -> bool:
    """Whether the provider cannot work without a user-supplied API key."""
    return bool(PRESETS.get(provider, {}).get("requires_key", True))


def provider_catalog() -> list[dict]:
    """Machine-readable provider list for the studio UI and docs."""
    return [
        {
            "id": provider_id,
            "label": str(preset.get("label", provider_id)),
            "base_url": str(preset.get("base_url", "")),
            "model": str(preset.get("model", "")),
            "requires_key": bool(preset.get("requires_key", True)),
            "kind": str(preset.get("kind", "custom")),
            "compact": bool(preset.get("compact", False)),
            "note": str(preset.get("note", "")),
            "key_url": str(preset.get("key_url", "")),
            "free": provider_id in FREE_PROVIDER_IDS,
        }
        for provider_id, preset in PRESETS.items()
    ]


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
    provider: str = "pollinations"
    base_url: str = str(PRESETS["pollinations"]["base_url"])
    model: str = str(PRESETS["pollinations"]["model"])
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
    demo_mode: bool = False

    def public_dict(self) -> dict:
        return {"theme": self.theme, "demo_mode": self.demo_mode}


@dataclass
class BrowserSettings:
    """Optional local Obscura runtime used for AI browser checks."""

    auto_check: bool = True
    allow_private_network: bool = True

    def public_dict(self) -> dict:
        return {
            "auto_check": self.auto_check,
            "allow_private_network": self.allow_private_network,
        }


@dataclass
class AppConfig:
    ai: AISettings = field(default_factory=AISettings)
    database: DatabaseSettings = field(default_factory=DatabaseSettings)
    ui: UISettings = field(default_factory=UISettings)
    browser: BrowserSettings = field(default_factory=BrowserSettings)

    def public_dict(self) -> dict:
        return {
            "ai": self.ai.public_dict(),
            "database": self.database.public_dict(),
            "ui": self.ui.public_dict(),
            "browser": self.browser.public_dict(),
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
            "browser": {
                "auto_check": self.browser.auto_check,
                "allow_private_network": self.browser.allow_private_network,
            },
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

        browser = payload.get("browser") or {}
        if "auto_check" in browser:
            self.browser.auto_check = bool(browser.get("auto_check"))
        if "allow_private_network" in browser:
            self.browser.allow_private_network = bool(browser.get("allow_private_network"))
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
