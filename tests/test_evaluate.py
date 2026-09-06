from __future__ import annotations

from pathlib import Path

from lacerta.harness.evaluate import check_acceptance, evaluate_run, session_successful
from lacerta.harness.scenarios import SCENARIOS


def test_check_acceptance_smoke(tmp_path: Path) -> None:
    scenario = SCENARIOS["smoke_write_file"]
    assert check_acceptance(scenario, tmp_path)
    (tmp_path / "harness_smoke.py").write_text("print('HARNESS_OK')\n", encoding="utf-8")
    assert check_acceptance(scenario, tmp_path) == []


def test_session_successful_disk_without_final_report() -> None:
    assert session_successful({}, []) is True
    assert session_successful({"completed": True}, ["x"]) is True
    assert session_successful({}, ["missing"]) is False


def test_evaluate_run_prefers_disk(tmp_path: Path) -> None:
    (tmp_path / "harness_smoke.py").write_text("print('HARNESS_OK')\n", encoding="utf-8")
    ok, failures = evaluate_run(
        {
            "scenario": SCENARIOS["smoke_write_file"],
            "project_root": str(tmp_path),
            "worker_metrics": {"completed": False},
            "run_status": "failed",
            "error": "model said failed",
        }
    )
    assert ok is True
    assert failures == []
