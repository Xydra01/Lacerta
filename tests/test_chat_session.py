"""Multi-turn chat_local helpers (V1.5)."""

from __future__ import annotations

from lacerta.core.chat_local import (
    CHAT_MAX_PRIOR_TURNS,
    build_chat_messages,
    run_chat_answer,
    trim_prior_messages,
)
from lacerta.core.jobs import JobSpec
from lacerta.core.manager import run_manager
from lacerta.gui.surfaces import build_run_inputs


def test_trim_prior_messages_filters_and_caps() -> None:
    raw = (
        [{"role": "system", "content": "nope"}]
        + [{"role": "user", "content": f"u{i}"} for i in range(20)]
        + [{"role": "assistant", "content": "a"}]
    )
    out = trim_prior_messages(raw, max_turns=4, max_chars=10_000)
    assert len(out) <= 4
    assert all(m["role"] in ("user", "assistant") for m in out)
    assert "system" not in {m["role"] for m in out}


def test_trim_prior_messages_char_budget() -> None:
    raw = [
        {"role": "user", "content": "a" * 100},
        {"role": "assistant", "content": "b" * 100},
        {"role": "user", "content": "c" * 100},
    ]
    out = trim_prior_messages(raw, max_turns=12, max_chars=150)
    assert sum(len(m["content"]) for m in out) <= 150
    assert out[-1]["content"].startswith("c")


def test_build_chat_messages_order_and_context() -> None:
    msgs = build_chat_messages(
        objective="Q2",
        prior=[
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
        ],
        context="light bits",
    )
    assert msgs[0]["role"] == "system"
    assert msgs[1] == {"role": "user", "content": "Q1"}
    assert msgs[2] == {"role": "assistant", "content": "A1"}
    assert msgs[3]["role"] == "user"
    assert "light bits" in msgs[3]["content"]
    assert "Q2" in msgs[3]["content"]


def test_run_chat_answer_passes_multi_turn_payload() -> None:
    seen: list[list[dict[str, str]]] = []

    class Client:
        def chat(self, messages, **kwargs):
            del kwargs
            seen.append(list(messages))
            return {"message": {"content": "ok"}}

    job = JobSpec(
        job_id="c1",
        job_type="chat_answer",
        objective="next",
        inputs={
            "messages": [
                {"role": "user", "content": "hi"},
                {"role": "assistant", "content": "hello"},
            ]
        },
    )
    result = run_chat_answer(job, client=Client())
    assert result.ok
    assert len(seen[0]) >= 3
    assert seen[0][0]["role"] == "system"
    assert result.metrics.get("prior_turns") == 2


def test_run_chat_answer_streams_only_when_buffer_set() -> None:
    seen: list[dict] = []

    class Client:
        def chat(self, messages, **kwargs):
            del messages
            seen.append(kwargs)
            return {"message": {"content": "ok"}}

    job = JobSpec(job_id="c2", job_type="chat_answer", objective="next", inputs={})
    run_chat_answer(job, client=Client())
    assert seen[0].get("stream") is not True

    def on_delta(_text: str) -> None:
        return None

    buffered = Client()
    buffered.on_delta = on_delta
    run_chat_answer(job, client=buffered)
    assert seen[1]["stream"] is True
    assert seen[1]["on_delta"] is on_delta


def test_manager_multi_turn_chat(tmp_path) -> None:
    class Client:
        def chat(self, messages, **kwargs):
            del kwargs
            assert len(messages) >= 3
            assert messages[0]["role"] == "system"
            return {"message": {"content": "continued"}}

    inputs = build_run_inputs(
        "chat",
        "follow up",
        str(tmp_path),
        messages=[
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "reply"},
        ],
    )
    assert inputs.get("messages")
    state = run_manager(
        "follow up",
        surface="chat",
        inputs=inputs,
        client=Client(),
    )
    assert state.status == "finished", state.error
    assert "continued" in state.results[0]["summary"]


def test_chat_max_prior_constant() -> None:
    assert CHAT_MAX_PRIOR_TURNS == 12
