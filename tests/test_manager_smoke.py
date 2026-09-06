from __future__ import annotations

from pathlib import Path

from lacerta.core.jobs import JobResult, JobSpec
from lacerta.core.manager import run_manager


def test_manager_smoke_finishes_with_disk(tmp_path: Path) -> None:
    def runner(job: JobSpec) -> JobResult:
        assert job.job_type == "code_edit"
        assert job.inputs.get("root") == str(tmp_path)
        (tmp_path / "harness_smoke.py").write_text(
            "print('HARNESS_OK')\n", encoding="utf-8"
        )
        return JobResult(
            job_id=job.job_id,
            ok=True,
            summary="wrote file",
            metrics={"completed": True, "turns": 1},
        )

    state = run_manager(
        "Create harness_smoke.py",
        surface="code",
        inputs={
            "root": str(tmp_path),
            "tools": ["write_file"],
            "acceptance": {
                "check_file_glob": "**/harness_smoke.py",
                "file_contains": "HARNESS_OK",
            },
            "template_id": "tpl.code.smoke",
            "job_type": "code_edit",
        },
        runner=runner,
    )
    assert state.status == "finished"
    assert len(state.results) == 1
    assert state.results[0]["ok"] is True
    assert state.plan == ["code_edit"]


def test_manager_smoke_disk_pass_without_worker_ok(tmp_path: Path) -> None:
    def runner(job: JobSpec) -> JobResult:
        (tmp_path / "harness_smoke.py").write_text(
            "print('HARNESS_OK')\n", encoding="utf-8"
        )
        return JobResult(
            job_id=job.job_id,
            ok=False,
            summary="no final_report",
            metrics={"completed": False},
        )

    state = run_manager(
        "Create harness_smoke.py",
        surface="code",
        inputs={
            "root": str(tmp_path),
            "acceptance": {
                "check_file_glob": "**/harness_smoke.py",
                "file_contains": "HARNESS_OK",
            },
            "template_id": "tpl.code.smoke",
        },
        runner=runner,
    )
    assert state.status == "finished"


def test_manager_hard_worker_failure(tmp_path: Path) -> None:
    def runner(job: JobSpec) -> JobResult:
        return JobResult(
            job_id=job.job_id,
            ok=False,
            summary="",
            error="Ollama unreachable",
        )

    state = run_manager(
        "Create harness_smoke.py",
        surface="code",
        inputs={
            "root": str(tmp_path),
            "acceptance": {
                "check_file_glob": "**/harness_smoke.py",
                "file_contains": "HARNESS_OK",
            },
            "template_id": "tpl.code.smoke",
        },
        runner=runner,
    )
    assert state.status == "failed"
    assert state.error == "Ollama unreachable"
    assert len(state.results) == 1


def test_manager_rejects_cross_surface_via_bad_job_type(tmp_path: Path) -> None:
    state = run_manager(
        "research something",
        surface="code",
        inputs={
            "root": str(tmp_path),
            "template_id": "tpl.code.smoke",
            "job_type": "research_local",
        },
        runner=lambda job: JobResult(job_id=job.job_id, ok=True, summary="nope"),
    )
    assert state.status == "failed"
    assert state.error and "not allowed" in state.error
