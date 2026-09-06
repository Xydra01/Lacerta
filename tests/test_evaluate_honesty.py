from __future__ import annotations

from pathlib import Path

from lacerta.harness.evaluate import evaluate_run, session_successful


def test_disk_beats_failed_status(tmp_path: Path) -> None:
    (tmp_path / "harness_smoke.py").write_text("print('HARNESS_OK')\n", encoding="utf-8")
    ok, failures = evaluate_run(
        {
            "scenario": {
                "acceptance": {
                    "check_file_glob": "**/harness_smoke.py",
                    "file_contains": "HARNESS_OK",
                }
            },
            "project_root": str(tmp_path),
            "worker_metrics": {"completed": False},
            "run_status": "failed",
            "error": "finish_task not observed",
        }
    )
    assert ok is True
    assert failures == []


def test_session_successful_helpers() -> None:
    assert session_successful({"completed": True}, ["x"]) is True
    assert session_successful({}, []) is True
    assert session_successful({}, ["missing"]) is False
