"""Thin Ollama HTTP client (stdlib urllib)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from collections.abc import Callable
from typing import Any


def _base_url() -> str:
    return os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")


def _model() -> str:
    return os.getenv("OLLAMA_MODEL", "lacerta:latest").strip() or "lacerta:latest"


def default_num_ctx() -> int:
    """Context window for chat options. Mac 8GB profile defaults to 8k."""
    raw = os.getenv("OLLAMA_NUM_CTX", "").strip()
    if raw:
        try:
            return max(1024, min(131072, int(raw)))
        except ValueError:
            pass
    # devMacOS / 8GB Apple Silicon: keep KV cache modest by default.
    return 8192


def default_num_predict() -> int | None:
    raw = os.getenv("OLLAMA_NUM_PREDICT", "").strip()
    if not raw:
        # Cap generations so small models finish turns instead of rambling.
        return 1024
    try:
        return max(64, min(8192, int(raw)))
    except ValueError:
        return 1024


@dataclass
class ModelCheckResult:
    ok: bool
    model: str
    message: str
    capable: bool = False
    unknown: bool = True


# Harness-verified / intended Lacerta tags (including Mac 4B rebuild of lacerta:latest).
CAPABLE_MODELS = frozenset(
    {
        "lacerta",
        "lacerta:latest",
        "lacerta:macos",
        "qwen3.5:4b",
        "qwen3.5:4b-mlx",
    }
)
DEGRADED_MODELS = frozenset(
    {
        "qwen3.5:2b",
        "qwen3.5:0.8b",
        "llama3.2:3b",
        "llama3.2:1b",
    }
)


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
        num_ctx: int | None = None,
        num_predict: int | None = None,
        on_delta: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        options: dict[str, Any] = {"temperature": temperature}
        ctx = default_num_ctx() if num_ctx is None else num_ctx
        if ctx is not None:
            options["num_ctx"] = int(ctx)
        pred = default_num_predict() if num_predict is None else num_predict
        if pred is not None:
            options["num_predict"] = int(pred)

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": bool(stream),
            "options": options,
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
                if stream:
                    result = _read_ndjson_chat(resp, on_delta)
                else:
                    raw = resp.read().decode("utf-8")
                    result = json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Ollama chat HTTP {e.code}: {body}") from e
        except urllib.error.URLError as e:
            raise ConnectionError(
                f"Ollama unreachable at {self.base_url}: {e}. "
                "Start Ollama and set OLLAMA_BASE_URL / OLLAMA_MODEL."
            ) from e
        return _apply_thinking_fallback(result)


def _apply_thinking_fallback(result: Any) -> dict[str, Any]:
    """Empty content falls back to thinking on the returned dict only."""
    if not isinstance(result, dict):
        return {}
    msg = result.get("message")
    if isinstance(msg, dict):
        content = str(msg.get("content") or "").strip()
        if not content:
            thinking = str(msg.get("thinking") or "").strip()
            if thinking:
                msg["content"] = thinking
    return result


def _read_ndjson_chat(resp: Any, on_delta: Callable[[str], None] | None) -> dict[str, Any]:
    """Accumulate Ollama newline-delimited chat chunks into one dict."""
    parts: list[str] = []
    thinking: list[str] = []
    role = "assistant"
    done = False
    while True:
        line = resp.readline()
        if not line:
            break
        if isinstance(line, bytes):
            line = line.decode("utf-8", errors="replace")
        text = str(line).strip()
        if not text:
            continue
        try:
            chunk = json.loads(text)
        except json.JSONDecodeError:
            continue
        if not isinstance(chunk, dict):
            continue
        msg = chunk.get("message")
        if isinstance(msg, dict):
            if msg.get("role"):
                role = str(msg["role"])
            piece = msg.get("content")
            if piece:
                parts.append(str(piece))
                if on_delta is not None:
                    try:
                        on_delta("".join(parts))
                    except Exception:
                        pass
            think = msg.get("thinking")
            if think:
                thinking.append(str(think))
        if chunk.get("done"):
            done = True
            break
    message: dict[str, Any] = {"role": role, "content": "".join(parts)}
    if thinking:
        message["thinking"] = "".join(thinking)
    return {"message": message, "done": done}
