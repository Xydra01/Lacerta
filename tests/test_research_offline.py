from __future__ import annotations

from pathlib import Path

import pytest

from lacerta.core.capabilities import CapabilityContext, run_capability
from lacerta.core.jobs import JobSpec
from lacerta.core.manager import validate_job
from lacerta.workers.research import capabilities as _caps  # noqa: F401
from lacerta.workers.research import recipes as _recipes  # noqa: F401
from lacerta.workers.research.worker import run as research_run


def test_empty_ingest_fails(tmp_path: Path) -> None:
    ctx = CapabilityContext(
        task_id="t1",
        data_root=str(tmp_path),
        surface="research",
        offline=True,
    )
    result = run_capability("research.ingest_offline", ctx, {"topic": ""})
    # topic alone may still produce content via empty topic — force no attachments
    ctx.user_request = ""
    result = run_capability("research.ingest_offline", ctx, {})
    assert result.ok is False
    assert result.error_code == "empty_ingest"


def test_research_recipe_happy_path(tmp_path: Path) -> None:
    fixture = Path(__file__).parent / "fixtures" / "research" / "source.md"
    job = JobSpec(
        job_id="r1",
        job_type="research_local",
        objective="Offline research from sources",
        inputs={
            "recipe_id": "research.offline",
            "root": str(tmp_path),
            "data_root": str(tmp_path),
            "task_id": "unit-research",
            "attachments": [str(fixture)],
            "topic": "Local-first AI agents",
        },
        tools=[],
        max_turns=1,
    )
    result = research_run(job)
    assert result.ok, result.error
    report = tmp_path / "tasks" / "unit-research" / "research" / "report.md"
    assert report.is_file()
    assert len(report.read_text(encoding="utf-8")) >= 400


def test_research_rejected_on_code_surface() -> None:
    job = JobSpec(
        job_id="x",
        job_type="research_local",
        objective="nope",
    )
    with pytest.raises(ValueError, match="not allowed"):
        validate_job(job, "code")
