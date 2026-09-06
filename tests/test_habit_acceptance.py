from __future__ import annotations

from pathlib import Path

from lacerta.harness.acceptance_habit import check_habit_tracker
from lacerta.harness.evaluate import evaluate_run
from lacerta.workers.habit_scaffold import write_habit_scaffold


def test_habit_acceptance_green(tmp_path: Path) -> None:
    write_habit_scaffold(tmp_path)
    assert check_habit_tracker(tmp_path) == []


def test_habit_acceptance_missing(tmp_path: Path) -> None:
    fails = check_habit_tracker(tmp_path)
    assert any("missing" in f for f in fails)


def test_evaluate_habit_flag(tmp_path: Path) -> None:
    write_habit_scaffold(tmp_path)
    ok, failures = evaluate_run(
        {
            "scenario": {"acceptance": {"habit_tracker": True}},
            "project_root": str(tmp_path),
            "worker_metrics": {"completed": True},
            "run_status": "ok",
        }
    )
    assert ok is True
    assert failures == []
