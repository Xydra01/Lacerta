"""LLM decompose flag: templates first; flagged fallback only."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from lacerta.core.jobs import JobResult, JobSpec
from lacerta.core.manager import run_manager


@pytest.fixture(autouse=True)
def _clear_decompose_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LACERTA_LLM_DECOMPOSE", raising=False)
    monkeypatch.delenv("LACERTA_LLM_DECOMPOSE_MAX", raising=False)


class TrackingClient:
    def __init__(self, replies: list[dict[str, Any]]) -> None:
        self.replies = list(replies)
        self.calls = 0

    def chat(self, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        del messages, kwargs
        self.calls += 1
        if not self.replies:
            payload = {"done": True}
        else:
            payload = self.replies.pop(0)
        return {"message": {"content": json.dumps(payload)}}


def test_flag_default_off_no_template_fails_without_chat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("LACERTA_LLM_DECOMPOSE", raising=False)
    client = TrackingClient([{"done": False, "job_type": "code_edit", "objective": "x"}])

    state = run_manager(
        "do something freeform",
        surface="code",
        inputs={"root": str(tmp_path), "template_id": "tpl.none"},
        client=client,
    )
    assert state.status == "failed"
    assert state.error and "LACERTA_LLM_DECOMPOSE=1" in state.error
    assert client.calls == 0


def test_flag_off_template_still_wins(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LACERTA_LLM_DECOMPOSE", "0")
    client = TrackingClient(
        [{"done": False, "job_type": "code_edit", "objective": "should not run"}]
    )

    def runner(job: JobSpec) -> JobResult:
        (tmp_path / "harness_smoke.py").write_text(
            "print('HARNESS_OK')\n", encoding="utf-8"
        )
        return JobResult(job_id=job.job_id, ok=True, summary="ok")

    state = run_manager(
        "Create harness_smoke.py",
        surface="code",
        inputs={
            "root": str(tmp_path),
            "template_id": "tpl.code.smoke",
            "tools": ["write_file"],
            "acceptance": {
                "check_file_glob": "**/harness_smoke.py",
                "file_contains": "HARNESS_OK",
            },
        },
        client=client,
        runner=runner,
    )
    assert state.status == "finished"
    assert client.calls == 0
    assert state.plan == ["code_edit"]


def test_flag_on_proposes_valid_job_and_finishes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LACERTA_LLM_DECOMPOSE", "1")
    client = TrackingClient(
        [
            {
                "done": False,
                "job_type": "code_edit",
                "objective": "Create harness_smoke.py",
                "tools": ["write_file"],
                "inputs": {},
            }
        ]
    )

    def runner(job: JobSpec) -> JobResult:
        assert job.job_type == "code_edit"
        assert job.inputs.get("root") == str(tmp_path)
        (tmp_path / "harness_smoke.py").write_text(
            "print('HARNESS_OK')\n", encoding="utf-8"
        )
        return JobResult(job_id=job.job_id, ok=True, summary="wrote")

    state = run_manager(
        "Create harness_smoke.py with HARNESS_OK",
        surface="code",
        inputs={
            "root": str(tmp_path),
            "template_id": "tpl.none",
            "acceptance": {
                "check_file_glob": "**/harness_smoke.py",
                "file_contains": "HARNESS_OK",
            },
        },
        client=client,
        runner=runner,
    )
    assert state.status == "finished", state.error
    assert client.calls >= 1
    assert state.plan == ["llm:code_edit"]
    assert state.results[0]["ok"] is True


def test_flag_on_disallowed_job_type_fails_before_spawn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LACERTA_LLM_DECOMPOSE", "1")
    client = TrackingClient(
        [
            {
                "done": False,
                "job_type": "research_local",
                "objective": "research",
            }
        ]
    )
    spawned = {"n": 0}

    def runner(job: JobSpec) -> JobResult:
        spawned["n"] += 1
        return JobResult(job_id=job.job_id, ok=True, summary="should not run")

    state = run_manager(
        "freeform",
        surface="code",
        inputs={"root": str(tmp_path), "template_id": "tpl.none"},
        client=client,
        runner=runner,
    )
    assert state.status == "failed"
    assert state.error and "not allowed" in state.error
    assert spawned["n"] == 0


def test_propose_cap_stops_unbounded_replan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LACERTA_LLM_DECOMPOSE", "1")
    monkeypatch.setenv("LACERTA_LLM_DECOMPOSE_MAX", "2")

    class AlwaysPropose:
        calls = 0

        def chat(self, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
            del messages, kwargs
            self.calls += 1
            return {
                "message": {
                    "content": json.dumps(
                        {
                            "done": False,
                            "job_type": "code_edit",
                            "objective": f"step {self.calls}",
                            "tools": ["write_file"],
                        }
                    )
                }
            }

    client = AlwaysPropose()

    def runner(job: JobSpec) -> JobResult:
        return JobResult(job_id=job.job_id, ok=True, summary="noop")

    state = run_manager(
        "never done",
        surface="code",
        inputs={"root": str(tmp_path), "template_id": "tpl.none"},
        client=client,
        runner=runner,
    )
    assert state.status == "failed"
    assert state.error and "propose cap" in state.error
    assert len(state.plan) == 2
    assert all(p.startswith("llm:") for p in state.plan)


def test_flag_on_without_client_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LACERTA_LLM_DECOMPOSE", "true")
    state = run_manager(
        "x",
        surface="code",
        inputs={"root": str(tmp_path), "template_id": "tpl.none"},
        client=None,
    )
    assert state.status == "failed"
    assert state.error and "Ollama client" in state.error
