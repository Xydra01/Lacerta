from __future__ import annotations

from pathlib import Path

from lacerta.core.capabilities import CapabilityContext, run_capability, run_recipe
from lacerta.core.jobs import JobSpec
from lacerta.workers.learn import capabilities as learn_caps  # noqa: F401
from lacerta.workers.learn import recipes as learn_recipes  # noqa: F401
from lacerta.workers.learn import storage
from lacerta.workers.learn.worker import run as learn_run


def _ctx(tmp_path: Path, **extra) -> CapabilityContext:
    return CapabilityContext(
        instance_id="default",
        course_id="test-course",
        data_root=str(tmp_path),
        user_request="Algorithms",
        attachments=extra.get("attachments") or [],
        extra={"topic": "Algorithms", "data_root": str(tmp_path)},
    )


def test_shallow_syllabus_rejected(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    shallow = {
        "status": "building",
        "nodes": [
            {"id": "u1", "title": "A", "parent_id": None, "mastery_tier": 0},
            {"id": "u2", "title": "B", "parent_id": None, "mastery_tier": 0},
            {"id": "u3", "title": "C", "parent_id": None, "mastery_tier": 0},
        ],
        "assessments": [],
    }
    import json

    result = run_capability(
        "learn.write_syllabus",
        ctx,
        {"content": json.dumps(shallow)},
    )
    assert result.ok is False
    assert result.error_code == "shallow_syllabus"


def test_deep_write_and_finalize(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    # ingest first
    notes = tmp_path / "notes.md"
    notes.write_text("# Unit One\n# Unit Two\n", encoding="utf-8")
    ctx.attachments = [str(notes)]
    ing = run_capability("learn.ingest_course_materials", ctx, {"topic": "Algorithms"})
    assert ing.ok
    written = run_capability("learn.write_syllabus", ctx, {})
    assert written.ok, written.error_message
    fin = run_capability("learn.finalize_course", ctx, {})
    assert fin.ok
    root = storage.course_dir(tmp_path, "default", "test-course")
    syllabus = storage.read_json(storage.syllabus_path(root))
    assert syllabus and syllabus["status"] == "active"
    assert len(syllabus["nodes"]) >= 8


def test_recipe_happy_path(tmp_path: Path) -> None:
    fixture = Path(__file__).parent / "fixtures" / "learn" / "course_notes.md"
    job = JobSpec(
        job_id="j1",
        job_type="learn_syllabus_files",
        objective="Build syllabus",
        inputs={
            "recipe_id": "learn.syllabus_from_files",
            "course_id": "calc",
            "instance_id": "default",
            "root": str(tmp_path),
            "data_root": str(tmp_path),
            "attachments": [str(fixture)],
            "topic": "Algorithms",
        },
        tools=[],
        max_turns=1,
    )
    result = learn_run(job)
    assert result.ok, result.error
    root = storage.course_dir(tmp_path, "default", "calc")
    syllabus = storage.read_json(storage.syllabus_path(root))
    assert syllabus and syllabus["status"] == "active"
    course = storage.read_json(storage.course_json_path(root))
    assert course and course.get("build_complete") is True
