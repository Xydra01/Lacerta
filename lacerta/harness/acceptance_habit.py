"""Habit-tracker disk acceptance for the code-reliability harness bar."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REQUIRED_FILES = (
    "habit.py",
    "tests/test_habit.py",
    "README.md",
)


def check_habit_tracker(project_root: Path) -> list[str]:
    """Return failure strings; empty list means files present and pytest green."""
    root = Path(project_root)
    failures: list[str] = []
    for rel in REQUIRED_FILES:
        path = root / rel
        if not path.is_file():
            failures.append(f"habit missing: {rel}")
    if failures:
        return failures

    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "tests/test_habit.py"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return [f"habit pytest failed to run: {e}"]

    if proc.returncode != 0:
        tail = ((proc.stdout or "") + (proc.stderr or ""))[-1500:]
        failures.append(f"habit pytest exit={proc.returncode}\n{tail}")
    return failures
