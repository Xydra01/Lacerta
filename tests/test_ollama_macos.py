from __future__ import annotations

import json
from unittest.mock import patch

from lacerta.core.ollama_client import (
    CAPABLE_MODELS,
    OllamaClient,
    check_worker_model,
    default_num_ctx,
    default_num_predict,
)


def test_default_num_ctx_macos_budget(monkeypatch) -> None:
    monkeypatch.delenv("OLLAMA_NUM_CTX", raising=False)
    assert default_num_ctx() == 8192
    monkeypatch.setenv("OLLAMA_NUM_CTX", "4096")
    assert default_num_ctx() == 4096


def test_default_num_predict(monkeypatch) -> None:
    monkeypatch.delenv("OLLAMA_NUM_PREDICT", raising=False)
    assert default_num_predict() == 1024


def test_capable_includes_qwen35_4b() -> None:
    assert "qwen3.5:4b" in CAPABLE_MODELS
    assert "lacerta:latest" in CAPABLE_MODELS


def test_check_worker_model_qwen4b(monkeypatch) -> None:
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3.5:4b")
    res = check_worker_model()
    assert res.ok and res.capable


def test_chat_sends_num_ctx_options(monkeypatch) -> None:
    monkeypatch.setenv("OLLAMA_NUM_CTX", "8192")
    monkeypatch.setenv("OLLAMA_NUM_PREDICT", "512")
    client = OllamaClient(model="lacerta:latest")
    captured: dict = {}

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({"message": {"content": "{}"}}).encode()

    def fake_urlopen(req, timeout=0):
        captured["payload"] = json.loads(req.data.decode())
        return _Resp()

    with patch("urllib.request.urlopen", fake_urlopen):
        client.chat([{"role": "user", "content": "hi"}], format={"type": "object"})

    opts = captured["payload"]["options"]
    assert opts["num_ctx"] == 8192
    assert opts["num_predict"] == 512
    assert captured["payload"]["think"] is False
    assert captured["payload"]["stream"] is False


def test_chat_stream_stitches_ndjson_and_on_delta() -> None:
    client = OllamaClient(model="lacerta:latest")
    lines = [
        json.dumps({"message": {"role": "assistant", "content": "Hi"}, "done": False}),
        json.dumps({"message": {"thinking": "secret"}, "done": False}),
        json.dumps({"message": {"content": " there"}, "done": True}),
    ]
    seen: list[str] = []

    class _Resp:
        def __init__(self) -> None:
            self._lines = [ln.encode() for ln in lines] + [b""]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def readline(self):
            return self._lines.pop(0)

    def fake_urlopen(req, timeout=0):
        payload = json.loads(req.data.decode())
        assert payload["stream"] is True
        return _Resp()

    with patch("urllib.request.urlopen", fake_urlopen):
        result = client.chat(
            [{"role": "user", "content": "hi"}],
            stream=True,
            on_delta=seen.append,
        )

    assert seen == ["Hi", "Hi there"]
    assert result["message"]["content"] == "Hi there"
    assert result["done"] is True
    assert "secret" not in result["message"]["content"]


def test_chat_stream_thinking_fallback_does_not_call_on_delta() -> None:
    client = OllamaClient(model="lacerta:latest")
    line = json.dumps(
        {"message": {"role": "assistant", "thinking": "only think"}, "done": True}
    )

    class _Resp:
        def __init__(self) -> None:
            self._lines = [line.encode(), b""]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def readline(self):
            return self._lines.pop(0)

    def boom(_text: str) -> None:
        raise RuntimeError("callback must not fail the chat")

    with patch("urllib.request.urlopen", lambda req, timeout=0: _Resp()):
        result = client.chat(
            [{"role": "user", "content": "hi"}],
            stream=True,
            on_delta=boom,
        )
    assert result["message"]["content"] == "only think"
