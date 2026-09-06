from __future__ import annotations

import typing

import pytest
from pydantic import ValidationError

from lacerta.core.jobs import JobResult, JobSpec, JobType, Surface
from lacerta.core import manager, worker_runtime
from lacerta.harness import gate, scenarios
from lacerta.workers.code_tools import CODE_TOOL_REGISTRY


ALL_JOB_TYPES: tuple[str, ...] = typing.get_args(JobType)
ALL_SURFACES: tuple[str, ...] = typing.get_args(Surface)


def test_job_spec_defaults() -> None:
    spec = JobSpec(
        job_id="j1",
        job_type="code_edit",
        objective="Create a file",
    )
    assert spec.tools == []
    assert spec.acceptance == {}
    assert spec.inputs == {}
    assert spec.max_turns == 5


def test_job_result_round_trip() -> None:
    result = JobResult(
        job_id="j1",
        ok=False,
        summary="failed",
        error="boom",
    )
    dumped = result.model_dump()
    restored = JobResult.model_validate(dumped)
    assert restored.ok is False
    assert restored.error == "boom"
    assert restored.artifacts == []
    assert restored.metrics == {}


@pytest.mark.parametrize("job_type", ALL_JOB_TYPES)
def test_all_job_types_accepted(job_type: str) -> None:
    spec = JobSpec(job_id="j", job_type=job_type, objective="x")  # type: ignore[arg-type]
    assert spec.job_type == job_type


def test_invalid_job_type_rejected() -> None:
    with pytest.raises(ValidationError):
        JobSpec(job_id="j", job_type="not_a_real_type", objective="x")  # type: ignore[arg-type]


def test_extra_field_forbidden_on_job_spec() -> None:
    with pytest.raises(ValidationError):
        JobSpec.model_validate(
            {
                "job_id": "j",
                "job_type": "code_edit",
                "objective": "x",
                "unknown_field": True,
            }
        )


def test_extra_field_forbidden_on_job_result() -> None:
    with pytest.raises(ValidationError):
        JobResult.model_validate(
            {
                "job_id": "j",
                "ok": True,
                "summary": "ok",
                "extra_noise": 1,
            }
        )


def test_surfaces_literal() -> None:
    assert set(ALL_SURFACES) == {"chat", "code", "learn", "research", "writing"}


def test_stub_imports() -> None:
    assert CODE_TOOL_REGISTRY == {}
    assert scenarios.SCENARIOS == {}
    assert callable(manager.run_manager)
    assert callable(worker_runtime.run)
    assert callable(gate.main)


def test_gate_main_exits_zero() -> None:
    assert gate.main([]) == 0
    assert gate.main(["smoke_write_file", "--runs", "3"]) == 0
