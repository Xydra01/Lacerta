"""Learn course storage paths and JSON helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def course_dir(data_root: Path | str, instance_id: str, course_id: str) -> Path:
    return (
        Path(data_root)
        / "instances"
        / instance_id
        / "learn"
        / "courses"
        / course_id
    )


def ensure_course_dirs(data_root: Path | str, instance_id: str, course_id: str) -> Path:
    root = course_dir(data_root, instance_id, course_id)
    (root / "sources").mkdir(parents=True, exist_ok=True)
    (root / "assessments").mkdir(parents=True, exist_ok=True)
    return root


def syllabus_path(course_root: Path) -> Path:
    return course_root / "syllabus.json"


def course_json_path(course_root: Path) -> Path:
    return course_root / "course.json"


def notes_path(course_root: Path) -> Path:
    return course_root / "sources" / "notes.md"


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def validate_syllabus_structure(
    syllabus: dict[str, Any],
    *,
    min_nodes: int = 8,
    min_subunits: int = 5,
) -> list[str]:
    failures: list[str] = []
    nodes = syllabus.get("nodes")
    if not isinstance(nodes, list):
        return ["syllabus.nodes must be a list"]
    if len(nodes) < min_nodes:
        failures.append(f"need ≥{min_nodes} nodes, got {len(nodes)}")
    subunits = 0
    for i, node in enumerate(nodes):
        if not isinstance(node, dict):
            failures.append(f"node[{i}] not an object")
            continue
        if not node.get("id") or not node.get("title"):
            failures.append(f"node[{i}] missing id/title")
        if node.get("parent_id"):
            subunits += 1
    if subunits < min_subunits:
        failures.append(f"need ≥{min_subunits} sub-units (parent_id set), got {subunits}")
    return failures
