from __future__ import annotations

import pytest

from lacerta.core.allowlists import allowed_job_types, is_allowed
from lacerta.core.jobs import JobSpec
from lacerta.core.manager import validate_job


def test_code_allows_code_jobs() -> None:
    assert is_allowed("code", "code_edit")
    assert is_allowed("code", "code_recon")
    assert is_allowed("code", "code_test")
    assert not is_allowed("code", "research_local")


def test_research_local_rejected_on_code() -> None:
    job = JobSpec(
        job_id="j1",
        job_type="research_local",
        objective="x",
    )
    with pytest.raises(ValueError, match="not allowed"):
        validate_job(job, "code")


def test_write_draft_rejected_on_code() -> None:
    job = JobSpec(
        job_id="j2",
        job_type="write_draft",
        objective="x",
    )
    with pytest.raises(ValueError, match="not allowed"):
        validate_job(job, "code")


def test_each_surface_map() -> None:
    expected = {
        "chat": {"chat_answer", "research_light"},
        "code": {"code_recon", "code_edit", "code_test"},
        "learn": {
            "learn_syllabus_files",
            "learn_syllabus_web",
            "learn_assessment",
            "learn_tutor_turn",
            "learn_archive_chat",
        },
        "research": {"research_local", "research_web"},
        "writing": {"write_draft", "write_finalize", "write_from_sources"},
    }
    for surface, types in expected.items():
        assert set(allowed_job_types(surface)) == types
        for jt in types:
            assert is_allowed(surface, jt)


def test_validate_job_accepts_code_edit() -> None:
    job = JobSpec(job_id="j", job_type="code_edit", objective="ok")
    validate_job(job, "code")  # no raise
