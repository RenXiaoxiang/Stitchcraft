"""Dependency-free OpenAI-compatible chat client.

Supports any endpoint that speaks the OpenAI chat-completions protocol: OpenAI,
DeepSeek, OpenRouter, Ollama's `/v1` shim and custom gateways. Nothing here
imports an SDK; the desktop studio must stay runnable with the standard library
alone.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

__all__ = [
    "AIConfig",
    "AIError",
    "chat",
    "extract_json",
    "test_connection",
]


class AIError(RuntimeError):
    """Raised when the configured AI endpoint cannot fulfil a request."""


@dataclass(frozen=True)
class AIConfig:
    provider: str = "openai"
    base_url: str = ""
    model: str = ""
    api_key: str = ""
    temperature: float = 0.7


def _url(base_url: str, path: str) -> str:
    return base_url.rstrip("/") + "/" + path.lstrip("/")


def _headers(config: AIConfig) -> dict[str, str]:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"
    if config.provider == "openrouter":
        headers["HTTP-Referer"] = "https://github.com/RenXiaoxiang/Stitchcraft"
        headers["X-Title"] = "Stitchcraft"
    return headers


def _extract_text(body: dict) -> str:
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        raise AIError("AI response did not contain any choices.")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, list):  # some gateways return content parts
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    if not isinstance(content, str) or not content.strip():
        raise AIError("AI response was empty.")
    return content


def chat(
    config: AIConfig,
    messages: list[dict],
    *,
    json_mode: bool = False,
    timeout: float = 240.0,
    retries: int = 1,
) -> str:
    """Send a chat-completions request and return the assistant text."""
    if not config.base_url:
        raise AIError("No AI base URL is configured.")
    if not config.model:
        raise AIError("No AI model is configured.")
    payload: dict = {
        "model": config.model,
        "messages": messages,
        "temperature": config.temperature,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    last_error: str = ""
    for attempt in range(retries + 1):
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            _url(config.base_url, "chat/completions"),
            data=data,
            headers=_headers(config),
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = json.loads(response.read().decode("utf-8", "replace"))
            return _extract_text(body)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:400]
            last_error = f"AI endpoint returned HTTP {exc.code}: {detail}"
            # Retry once without json_mode when an endpoint rejects it.
            if json_mode and attempt == 0 and exc.code in (400, 404, 415, 422):
                payload.pop("response_format", None)
                continue
            raise AIError(last_error) from exc
        except urllib.error.URLError as exc:
            raise AIError(f"cannot reach the AI endpoint: {exc.reason}") from exc
        except TimeoutError as exc:
            raise AIError("the AI endpoint timed out") from exc
    raise AIError(last_error or "AI request failed")


def test_connection(config: AIConfig, timeout: float = 20.0) -> dict:
    """Probe the endpoint; returns a JSON-friendly result for the settings UI."""
    started = time.perf_counter()

    def elapsed() -> int:
        return int((time.perf_counter() - started) * 1000)

    if not config.base_url:
        return {"ok": False, "message": "Base URL is empty.", "latency_ms": 0}
    try:
        request = urllib.request.Request(_url(config.base_url, "models"), headers=_headers(config))
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            if response.status < 400 and raw:
                return {
                    "ok": True,
                    "message": "Connection OK — the models endpoint answered.",
                    "latency_ms": elapsed(),
                }
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        pass  # fall back to a tiny chat round-trip
    try:
        text = chat(
            config,
            [{"role": "user", "content": "Reply with exactly the word: pong"}],
            timeout=timeout,
            retries=0,
        )
        return {
            "ok": True,
            "message": f"Connection OK — model replied: {text.strip()[:60]}",
            "latency_ms": elapsed(),
        }
    except AIError as exc:
        return {"ok": False, "message": str(exc), "latency_ms": elapsed()}


def extract_json(text: str) -> dict:
    """Parse the JSON object an AI returned, tolerating fences or stray prose."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end <= start:
            raise AIError("AI response did not contain a JSON object.")
        try:
            data = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError as exc:
            raise AIError(f"AI response was not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise AIError("AI response was not a JSON object.")
    return data
