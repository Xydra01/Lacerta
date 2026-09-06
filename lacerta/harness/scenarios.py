"""Harness scenario catalog."""

from __future__ import annotations

from pathlib import Path
from typing import Any

_FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures"

SCENARIOS: dict[str, dict[str, Any]] = {
    "smoke_write_file": {
        "description": "Create harness_smoke.py",
        "surface": "code",
        "template_id": "tpl.code.smoke",
        "job_type": "code_edit",
        "objective": (
            "Create harness_smoke.py with print('HARNESS_OK') using write_file. "
            "Then set final_report when done."
        ),
        "tools": ["read_file", "write_file", "list_dir", "grep"],
        "acceptance": {
            "check_file_glob": "**/harness_smoke.py",
            "file_contains": "HARNESS_OK",
        },
    },
    "learn_syllabus_files": {
        "description": "Build deep syllabus from course materials",
        "surface": "learn",
        "template_id": "tpl.learn.syllabus_files",
        "job_type": "learn_syllabus_files",
        "objective": "Build a deep syllabus from attached course materials.",
        "instance_id": "default",
        "course_id": "harness-course",
        "topic": "Introduction to Algorithms",
        "attachments": [str(_FIXTURES / "learn" / "course_notes.md")],
        "max_turns": 1,
        "acceptance": {
            "syllabus_min_nodes": 8,
            "syllabus_min_subunits": 5,
            "course_active": True,
        },
    },
    "habit_tracker": {
        "description": "Build CLI habit tracker with tests",
        "surface": "code",
        "template_id": "tpl.code.habit",
        "objective": (
            "Build CLI habit tracker: habit.py, tests/test_habit.py, README.md. "
            "Support add/tick/list commands."
        ),
        "deterministic_habit": True,
        "max_turns": 5,
        "acceptance": {"habit_tracker": True},
    },
    "research_local": {
        "description": "Offline research report from attachments",
        "surface": "research",
        "template_id": "tpl.research.offline",
        "job_type": "research_local",
        "objective": "Offline research note from attached sources (no web).",
        "topic": "Local-first AI agents",
        "attachments": [str(_FIXTURES / "research" / "source.md")],
        "task_id": "research-harness",
        "deliverable_path": "tasks/research-harness/research/report.md",
        "max_turns": 1,
        "acceptance": {"min_deliverable_chars": 400},
    },
    "writing_short": {
        "description": "Short markdown draft with title",
        "surface": "writing",
        "template_id": "tpl.writing.short",
        "job_type": "write_draft",
        "objective": "Two-paragraph markdown draft with a clear # title.",
        "task_id": "writing-harness",
        "deliverable_path": "tasks/writing-harness/writing/short.md",
        "max_turns": 1,
        "acceptance": {"min_deliverable_chars": 300, "require_title": True},
    },
}
