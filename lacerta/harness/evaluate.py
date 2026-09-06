"""Honest harness evaluation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def check_acceptance(scenario: dict[str, Any], project_root: Path) -> list[str]:
    failures: list[str] = []
    acc = scenario.get("acceptance") or {}
    needle = acc.get("file_contains")
    check_glob = acc.get("check_file_glob")
    if check_glob:
        matches = sorted(
            project_root.glob(check_glob),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not matches:
            failures.append(f"expected file missing (glob {check_glob!r})")
        elif needle and needle not in matches[0].read_text(
            encoding="utf-8", errors="replace"
        ):
            failures.append(f"{matches[0]} does not contain {needle!r}")

    # Learn syllabus structure
    min_nodes = acc.get("syllabus_min_nodes")
    min_sub = acc.get("syllabus_min_subunits")
    course_active = acc.get("course_active")
    if min_nodes or min_sub or course_active:
        instance_id = str(scenario.get("instance_id") or "default")
        course_id = str(scenario.get("course_id") or "harness-course")
        course_root = (
            project_root / "instances" / instance_id / "learn" / "courses" / course_id
        )
        spath = course_root / "syllabus.json"
        cpath = course_root / "course.json"
        if not spath.is_file():
            failures.append("syllabus.json missing")
        else:
            try:
                syllabus = json.loads(spath.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                failures.append(f"syllabus.json invalid: {e}")
                syllabus = {}
            nodes = syllabus.get("nodes") if isinstance(syllabus, dict) else None
            if not isinstance(nodes, list):
                failures.append("syllabus.nodes missing")
            else:
                if min_nodes and len(nodes) < int(min_nodes):
                    failures.append(f"syllabus nodes {len(nodes)} < {min_nodes}")
                if min_sub:
                    sub = sum(1 for n in nodes if isinstance(n, dict) and n.get("parent_id"))
                    if sub < int(min_sub):
                        failures.append(f"syllabus sub-units {sub} < {min_sub}")
            if course_active:
                status = (syllabus or {}).get("status") if isinstance(syllabus, dict) else None
                course = {}
                if cpath.is_file():
                    try:
                        course = json.loads(cpath.read_text(encoding="utf-8"))
                    except json.JSONDecodeError:
                        course = {}
                if status != "active" and not course.get("build_complete"):
                    failures.append("course not active / build_complete")

    # Generic min deliverable chars (research/writing)
    min_chars = acc.get("min_deliverable_chars")
    if min_chars:
        rel = scenario.get("deliverable_path") or acc.get("deliverable_path")
        path: Path | None = None
        if rel:
            path = Path(rel)
            if not path.is_absolute():
                path = project_root / path
        if path is None or not path.is_file():
            # Prefer report.md under tasks/*/research/ before any markdown
            matches = sorted(
                project_root.glob("tasks/*/research/report.md"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if not matches:
                matches = sorted(
                    project_root.glob("**/report.md"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )
            path = matches[0] if matches else None
        if not path or not path.is_file():
            failures.append("deliverable missing")
        else:
            text = path.read_text(encoding="utf-8", errors="replace")
            if len(text) < int(min_chars):
                failures.append(f"deliverable chars {len(text)} < {min_chars}")
            if acc.get("require_title") and not any(
                line.startswith("# ") for line in text.splitlines()
            ):
                failures.append("deliverable missing # title")

    if acc.get("habit_tracker"):
        from lacerta.harness.acceptance_habit import check_habit_tracker

        failures.extend(check_habit_tracker(project_root))

    return failures


def session_successful(metrics: dict[str, Any], acceptance_failures: list[str]) -> bool:
    if metrics.get("completed") or metrics.get("synced"):
        return True
    return not acceptance_failures


def evaluate_run(report: dict[str, Any]) -> tuple[bool, list[str]]:
    failures: list[str] = []
    scenario = dict(report.get("scenario") or {})
    # Allow report to override ids used by learn acceptance
    for key in ("instance_id", "course_id", "deliverable_path", "task_id"):
        if key in report and key not in scenario:
            scenario[key] = report[key]
    project_root = Path(report["project_root"])
    acceptance_failures = check_acceptance(scenario, project_root)
    metrics = report.get("worker_metrics") or {}
    code_ok = session_successful(metrics, acceptance_failures) and not acceptance_failures
    if report.get("run_status") == "failed" and not code_ok:
        failures.append("run_status=failed")
    if report.get("error") and not code_ok:
        failures.append(str(report["error"]))
    failures.extend(acceptance_failures)
    return (not failures), failures
