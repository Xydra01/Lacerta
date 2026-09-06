"""Thin Ollama HTTP client (stdlib urllib)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


def _base_url() -> str:
    return os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")


def _model() -> str:
    return os.getenv("OLLAMA_MODEL", "lacerta:latest").strip() or "lacerta:latest"


@dataclass
class ModelCheckResult:
    ok: bool
    model: str
    message: str
    capable: bool = False
    unknown: bool = True


CAPABLE_MODELS = frozenset({"lacerta", "lacerta:latest"})
DEGRADED_MODELS = frozenset()


def check_worker_model(*, surface: str = "cli", strict: bool = False) -> ModelCheckResult:
    del surface
    model = _model()
    base = model.split(":")[0]
    if model in CAPABLE_MODELS or base in CAPABLE_MODELS:
        return ModelCheckResult(ok=True, model=model, message="capable", capable=True, unknown=False)
    if model in DEGRADED_MODELS or base in DEGRADED_MODELS:
        msg = f"degraded model {model!r}"
        return ModelCheckResult(ok=not strict, model=model, message=msg, capable=False, unknown=False)
    msg = f"unknown model {model!r}; allowing in L1"
    return ModelCheckResult(ok=True, model=model, message=msg, capable=False, unknown=True)


class OllamaClient:
    def __init__(self, base_url: str | None = None, model: str | None = None) -> None:
        self.base_url = (base_url or _base_url()).rstrip("/")
        self.model = model or _model()

    def health(self) -> dict[str, Any]:
        url = f"{self.base_url}/api/tags"
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
        except urllib.error.URLError as e:
            raise ConnectionError(
                f"Ollama unreachable at {self.base_url}: {e}. "
                "Start Ollama and set OLLAMA_BASE_URL / OLLAMA_MODEL."
            ) from e

    def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        temperature: float = 0.2,
        format: dict[str, Any] | str | None = None,
        stream: bool = False,
        force_think_disabled: bool = True,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": bool(stream),
            "options": {"temperature": temperature},
        }
        if force_think_disabled:
            payload["think"] = False
        if format is not None:
            payload["format"] = format
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Ollama chat HTTP {e.code}: {body}") from e
        except urllib.error.URLError as e:
            raise ConnectionError(
                f"Ollama unreachable at {self.base_url}: {e}. "
                "Start Ollama and set OLLAMA_BASE_URL / OLLAMA_MODEL."
            ) from e
        result = json.loads(raw) if raw else {}
        # Some thinking models leave content empty; fall back to thinking text.
        if isinstance(result, dict):
            msg = result.get("message")
            if isinstance(msg, dict):
                content = str(msg.get("content") or "").strip()
                if not content:
                    thinking = str(msg.get("thinking") or "").strip()
                    if thinking:
                        msg["content"] = thinking
        return result
