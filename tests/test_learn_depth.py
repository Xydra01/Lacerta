"""Learn depth: tutor, assessment, corpus reservation."""

from __future__ import annotations

from pathlib import Path

from lacerta.core.capabilities import CapabilityContext, run_capability, run_recipe
from lacerta.core.jobs import JobSpec
from lacerta.core.manager import run_manager
from lacerta.gui.surfaces import build_run_inputs, list_surfaces
from lacerta.workers.learn import capabilities as learn_caps  # noqa: F401
from lacerta.workers.learn import recipes as learn_recipes  # noqa: F401
from lacerta.workers.learn import storage
from lacerta.workers.learn.worker import run as learn_run


def _seed_course(tmp_path: Path, *, course_id: str = "test-course") -> Path:
    ctx = CapabilityContext(
        instance_id="default",
        course_id=course_id,
        data_root=str(tmp_path),
        user_request="Algorithms",
        attachments=[],
        extra={"topic": "Algorithms", "data_root": str(tmp_path)},
    )
    fixture = Path(__file__).parent / "fixtures" / "learn" / "course_notes.md"
    ctx.attachments = [str(fixture)]
    assert run_capability("learn.ingest_course_materials", ctx, {"topic": "Algorithms"}).ok
    assert run_capability("learn.write_syllabus", ctx, {}).ok
    assert run_capability("learn.finalize_course", ctx, {}).ok
    return storage.course_dir(tmp_path, "default", course_id)


def test_ensure_course_meta_reserves_corpus(tmp_path: Path) -> None:
    course = storage.ensure_course_meta(tmp_path, "default", "c1")
    root = storage.course_dir(tmp_path, "default", "c1")
    assert (root / "corpus").is_dir()
    assert course.get("corpus_id")
    meta = storage.read_json(storage.corpus_meta_path(root))
    assert meta and meta.get("status") == "pending"


def test_tutor_turn_writes_artifact(tmp_path: Path) -> None:
    _seed_course(tmp_path)
    job = JobSpec(
        job_id="t1",
        job_type="learn_tutor_turn",
        objective="Explain the first unit",
        inputs={
            "recipe_id": "learn.tutor_turn",
            "course_id": "test-course",
            "instance_id": "default",
            "root": str(tmp_path),
            "data_root": str(tmp_path),
            "question": "Explain the first unit",
        },
        tools=[],
    )
    result = learn_run(job)
    assert result.ok, result.error
    assert result.artifacts
    turn_path = Path(result.artifacts[0])
    assert turn_path.is_file()
    data = storage.read_json(turn_path)
    assert data and data.get("reply")


def test_assessment_writes_artifact(tmp_path: Path) -> None:
    _seed_course(tmp_path)
    job = JobSpec(
        job_id="a1",
        job_type="learn_assessment",
        objective="Generate assessments",
        inputs={
            "recipe_id": "learn.assessment",
            "course_id": "test-course",
            "instance_id": "default",
            "root": str(tmp_path),
            "data_root": str(tmp_path),
            "max_nodes": 3,
        },
        tools=[],
    )
    result = learn_run(job)
    assert result.ok, result.error
    root = storage.course_dir(tmp_path, "default", "test-course")
    asm = storage.read_json(storage.assessments_dir(root) / "assessments.json")
    assert asm and len(asm.get("assessments") or []) >= 1


def test_archive_chat_requires_complete_corpus(tmp_path: Path) -> None:
    _seed_course(tmp_path)
    job = JobSpec(
        job_id="x1",
        job_type="learn_archive_chat",
        objective="What is sorting?",
        inputs={
            "root": str(tmp_path),
            "data_root": str(tmp_path),
            "course_id": "test-course",
            "instance_id": "default",
        },
        tools=[],
    )
    result = learn_run(job)
    assert result.ok is False
    assert "Index sources" in (result.error or "") or "corpus" in (
        result.error or ""
    ).lower()


def test_index_and_tutor_cites_chunk(tmp_path: Path) -> None:
    _seed_course(tmp_path)
    mini = Path(__file__).parent / "fixtures" / "learn" / "mini_book.md"
    index_job = JobSpec(
        job_id="idx1",
        job_type="learn_index_corpus",
        objective="Index mini-book",
        inputs={
            "recipe_id": "learn.index_corpus",
            "course_id": "test-course",
            "instance_id": "default",
            "root": str(tmp_path),
            "data_root": str(tmp_path),
            "attachments": [str(mini)],
        },
        tools=[],
    )
    idx = learn_run(index_job)
    assert idx.ok, idx.error
    meta = storage.read_json(
        storage.corpus_meta_path(storage.course_dir(tmp_path, "default", "test-course"))
    )
    assert meta and meta.get("status") == "complete"
    assert int(meta.get("chunk_count") or 0) >= 1

    tutor_job = JobSpec(
        job_id="t2",
        job_type="learn_tutor_turn",
        objective="What is the secret mascot animal?",
        inputs={
            "recipe_id": "learn.tutor_turn",
            "course_id": "test-course",
            "instance_id": "default",
            "root": str(tmp_path),
            "data_root": str(tmp_path),
            "question": "What is the secret mascot animal?",
        },
        tools=[],
    )
    result = learn_run(tutor_job)
    assert result.ok, result.error
    turn = storage.read_json(Path(result.artifacts[0]))
    assert turn
    assert "LACERTA_PLANTED_FACT_QUOKKA" in str(turn.get("reply") or "")
    assert turn.get("citations") or turn.get("grounding") in (
        "corpus_retrieve",
        "corpus_teach",
    )


def test_archive_chat_with_indexed_corpus(tmp_path: Path) -> None:
    _seed_course(tmp_path)
    mini = Path(__file__).parent / "fixtures" / "learn" / "mini_book.md"
    assert learn_run(
        JobSpec(
            job_id="idx2",
            job_type="learn_index_corpus",
            objective="Index",
            inputs={
                "course_id": "test-course",
                "instance_id": "default",
                "root": str(tmp_path),
                "data_root": str(tmp_path),
                "attachments": [str(mini)],
            },
            tools=[],
        )
    ).ok
    result = learn_run(
        JobSpec(
            job_id="a2",
            job_type="learn_archive_chat",
            objective="What is the secret mascot animal?",
            inputs={
                "course_id": "test-course",
                "instance_id": "default",
                "root": str(tmp_path),
                "data_root": str(tmp_path),
            },
            tools=[],
        )
    )
    assert result.ok, result.error
    data = storage.read_json(Path(result.artifacts[0]))
    assert data and "LACERTA_PLANTED_FACT_QUOKKA" in str(data.get("reply") or "")
    assert str(data.get("reply") or "").startswith("Archive (retrieve):")
    assert data.get("grounding") == "corpus_retrieve"


def test_learn_scenarios_plain_labels() -> None:
    learn = next(s for s in list_surfaces() if s["id"] == "learn")
    assert learn["show_learn_scenario"] is True
    ids = {s["id"] for s in learn["learn_scenarios"]}
    assert ids == {
        "build_syllabus",
        "tutor",
        "assessment",
        "mastery_check",
        "practice",
        "archive",
        "index_sources",
    }
    labels = " ".join(s["label"] for s in learn["learn_scenarios"]).lower()
    assert "tutor" in labels
    assert "practice" in labels
    assert "archive" in labels
    assert "index sources" in labels
    assert "learn_tutor_turn" not in labels


def test_build_run_inputs_learn_tutor(tmp_path: Path) -> None:
    inputs = build_run_inputs(
        "learn",
        "What is sorting?",
        str(tmp_path),
        scenario="tutor",
        course_id="gui-course",
    )
    assert inputs["template_id"] == "tpl.learn.tutor"
    assert inputs["scenario"] == "tutor"
    assert inputs["question"] == "What is sorting?"


def test_build_run_inputs_invalid_learn_scenario(tmp_path: Path) -> None:
    import pytest

    with pytest.raises(ValueError, match="unknown learn scenario"):
        build_run_inputs("learn", "x", str(tmp_path), scenario="not_real")


def test_manager_tutor_template(tmp_path: Path) -> None:
    ctx = CapabilityContext(
        instance_id="gui",
        course_id="gui-course",
        data_root=str(tmp_path),
        user_request="Algorithms",
        attachments=[str(Path(__file__).parent / "fixtures" / "learn" / "course_notes.md")],
        extra={"topic": "Algorithms", "data_root": str(tmp_path)},
    )
    assert run_capability("learn.ingest_course_materials", ctx, {"topic": "Algorithms"}).ok
    assert run_capability("learn.write_syllabus", ctx, {}).ok
    assert run_capability("learn.finalize_course", ctx, {}).ok

    inputs = build_run_inputs(
        "learn",
        "Help me with unit one",
        str(tmp_path),
        scenario="tutor",
        course_id="gui-course",
    )
    state = run_manager(
        "Help me with unit one",
        surface="learn",
        inputs=inputs,
        client=None,
    )
    assert state.status == "finished", state.error
    assert state.plan == ["learn_tutor_turn"]


def test_load_course_browse(tmp_path: Path) -> None:
    root = _seed_course(tmp_path)
    browse = storage.load_course_browse(tmp_path, "default", "test-course")
    assert browse["exists"] is True
    assert browse["node_count"] >= 8
    assert browse["syllabus_path"]
    assert (root / "corpus").is_dir()
