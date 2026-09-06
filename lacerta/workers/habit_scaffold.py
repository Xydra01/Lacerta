"""Deterministic habit tracker scaffold for harness-reliable L4."""

from __future__ import annotations

from pathlib import Path

HABIT_PY = '''\
"""Minimal CLI habit tracker."""

from __future__ import annotations

import json
from pathlib import Path

STORE = Path("habits.json")


def load() -> dict:
    if STORE.is_file():
        return json.loads(STORE.read_text(encoding="utf-8"))
    return {"habits": {}}


def save(data: dict) -> None:
    STORE.write_text(json.dumps(data, indent=2) + "\\n", encoding="utf-8")


def add(name: str) -> str:
    data = load()
    data.setdefault("habits", {})[name] = data.get("habits", {}).get(name, 0)
    save(data)
    return f"added {name}"


def tick(name: str) -> str:
    data = load()
    habits = data.setdefault("habits", {})
    if name not in habits:
        return f"unknown habit {name}"
    habits[name] = int(habits[name]) + 1
    save(data)
    return f"{name}={habits[name]}"


def list_habits() -> str:
    data = load()
    habits = data.get("habits") or {}
    if not habits:
        return "(none)"
    return "\\n".join(f"{k}: {v}" for k, v in sorted(habits.items()))


def main(argv: list[str] | None = None) -> int:
    import sys

    args = list(argv if argv is not None else sys.argv[1:])
    if not args:
        print("usage: habit.py add|tick|list …")
        return 1
    cmd = args[0]
    if cmd == "add" and len(args) >= 2:
        print(add(args[1]))
        return 0
    if cmd == "tick" and len(args) >= 2:
        print(tick(args[1]))
        return 0
    if cmd == "list":
        print(list_habits())
        return 0
    print("usage: habit.py add|tick|list …")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
'''

TEST_HABIT = '''\
from habit import add, tick, list_habits, load


def test_add_and_tick(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert "added" in add("water")
    assert tick("water") == "water=1"
    assert "water: 1" in list_habits()
    assert load()["habits"]["water"] == 1
'''

README = """# Habit Tracker

CLI habit tracker (`habit.py`).

Commands: `add`, `tick`, `list`.
"""


def write_habit_scaffold(root: Path) -> list[str]:
    root = Path(root)
    (root / "tests").mkdir(parents=True, exist_ok=True)
    (root / "habit.py").write_text(HABIT_PY, encoding="utf-8")
    (root / "tests" / "test_habit.py").write_text(TEST_HABIT, encoding="utf-8")
    (root / "README.md").write_text(README, encoding="utf-8")
    return ["habit.py", "tests/test_habit.py", "README.md"]
