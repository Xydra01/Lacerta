"""GUI surface wiring and chat manager path."""

from __future__ import annotations

from pathlib import Path

import pytest

from lacerta.core.allowlists import is_allowed
from lacerta.core.gen_lock import (
    GenerationBusy,
    acquire_generation,
    generation_held,
    release_generation,
)
from lacerta.core.manager import run_manager
from lacerta.gui.surfaces import SURFACE_DEFAULTS, build_run_inputs, list_surfaces


@pytest.fixture(autouse=True)
def _release_lock() -> None:
    release_generation()
    yield
    release_generation()


def test_each_surface_has_template_and_allowed_defaults() -> None:
    expected = {
        "chat": "tpl.chat.plain",
        "code": "tpl.code.smoke",
        "learn": "tpl.learn.syllabus_files",
        "research": "tpl.research.offline",
        "writing": "tpl.writing.short",
    }
    listed = {s["id"]: s for s in list_surfaces()}
    assert set(listed) == set(expected)
    for sid, tid in expected.items():
        assert listed[sid]["template_id"] == tid
        for jt in SURFACE_DEFAULTS[sid]["job_types"]:
            assert is_allowed(sid, jt)


def test_build_run_inputs_stays_on_allowlist(tmp_path: Path) -> None:
    for sid in SURFACE_DEFAULTS:
        inputs = build_run_inputs(sid, "goal text", str(tmp_path))
        assert inputs["template_id"] == SURFACE_DEFAULTS[sid]["template_id"]
        assert inputs["root"] == str(tmp_path)
        # no free-form job_type outside defaults (code sets code_edit explicitly)
        if "job_type" in inputs:
            assert is_allowed(sid, inputs["job_type"])


def test_chat_template_finishes_with_mock_client(tmp_path: Path) -> None:
    class Client:
        def chat(self, messages, **kwargs):
            del messages, kwargs
            return {"message": {"content": "Hello from Lacerta chat."}}

    state = run_manager(
        "What is Lacerta?",
        surface="chat",
        inputs=build_run_inputs("chat", "What is Lacerta?", str(tmp_path)),
        client=Client(),
    )
    assert state.status == "finished", state.error
    assert state.plan == ["chat_answer"]
    assert state.results[0]["ok"] is True
    assert "Hello from Lacerta chat." in state.results[0]["summary"]


def test_chat_light_research_then_answer(tmp_path: Path) -> None:
    class Client:
        def chat(self, messages, **kwargs):
            del kwargs
            user = messages[-1]["content"]
            return {"message": {"content": f"answered:{user[:40]}"}}

    inputs = build_run_inputs(
        "chat", "Explain agents", str(tmp_path), light_research=True
    )
    state = run_manager(
        "Explain agents",
        surface="chat",
        inputs=inputs,
        client=Client(),
    )
    assert state.status == "finished", state.error
    assert state.plan == ["research_light", "chat_answer"]


def test_gen_lock_already_held() -> None:
    assert generation_held() is False
    acquire_generation(blocking=False)
    assert generation_held() is True
    with pytest.raises(GenerationBusy):
        acquire_generation(blocking=False)
    release_generation()
    assert generation_held() is False
