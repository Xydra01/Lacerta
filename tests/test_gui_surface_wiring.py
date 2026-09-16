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


def test_code_scenarios_listed_with_plain_labels() -> None:
    code = next(s for s in list_surfaces() if s["id"] == "code")
    assert code["show_code_scenario"] is True
    ids = {s["id"] for s in code["code_scenarios"]}
    assert ids == {"quick_file_check", "habit_tracker"}
    labels = {s["label"] for s in code["code_scenarios"]}
    assert "Quick file check" in labels
    assert "Habit tracker (scaffold + tests)" in labels
    # Harness jargon must not appear in GUI labels
    joined = " ".join(labels).lower()
    assert "smoke" not in joined
    assert "habit mode" not in joined


def test_build_run_inputs_habit_tracker_scenario(tmp_path: Path) -> None:
    inputs = build_run_inputs(
        "code",
        "Build habit tracker",
        str(tmp_path),
        scenario="habit_tracker",
    )
    assert inputs["template_id"] == "tpl.code.habit"
    assert inputs["acceptance"] == {"habit_tracker": True}
    assert inputs["deterministic_habit"] is True
    assert inputs["scenario"] == "habit_tracker"


def test_build_run_inputs_quick_file_check_default(tmp_path: Path) -> None:
    inputs = build_run_inputs("code", "smoke goal", str(tmp_path))
    assert inputs["template_id"] == "tpl.code.smoke"
    assert inputs["scenario"] == "quick_file_check"
    assert inputs["acceptance"]["file_contains"] == "HARNESS_OK"


def test_build_run_inputs_invalid_scenario(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unknown code scenario"):
        build_run_inputs("code", "x", str(tmp_path), scenario="not_a_real_check")


def test_scenario_ui_flags_and_plain_language() -> None:
    chat = next(s for s in list_surfaces() if s["id"] == "chat")
    assert chat["show_workspace_root"] is False
    assert chat["cta_label"] == "Send"
    assert chat["goal_label"] == "Message"
    assert chat["hint"]

    learn = next(s for s in list_surfaces() if s["id"] == "learn")
    for s in learn["learn_scenarios"]:
        assert s["show_course_browser"] is True
        assert s["cta_label"]
        assert s["goal_label"]
        assert s["show_workspace_root"] is True
        joined = " ".join(
            [s["label"], s["cta_label"], s["goal_label"], s.get("hint") or ""]
        ).lower()
        assert "learn_" not in joined
        assert "jobtype" not in joined
        assert "job_type" not in joined

    by_id = {s["id"]: s for s in learn["learn_scenarios"]}
    assert by_id["build_syllabus"]["require_attachments"] is True
    assert by_id["index_sources"]["require_attachments"] is True
    assert by_id["tutor"]["show_attachments"] is False
    assert by_id["assessment"]["show_attachments"] is False

    code = next(s for s in list_surfaces() if s["id"] == "code")
    for s in code["code_scenarios"]:
        assert s["cta_label"]
        assert s["show_course_browser"] is False
        assert "smoke" not in s["cta_label"].lower()
