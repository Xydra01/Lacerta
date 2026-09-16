"""Learn Practice: quiz, flashcards, study guides (V2.4)."""

from __future__ import annotations

from pathlib import Path

from lacerta.core.capabilities import CapabilityContext, run_capability, run_recipe
from lacerta.core.jobs import JobSpec
from lacerta.gui.surfaces import LEARN_SCENARIOS, build_run_inputs, list_surfaces
from lacerta.workers.learn import capabilities as learn_caps
from lacerta.workers.learn import storage
from lacerta.workers.learn import capabilities as _caps  # noqa: F401
from lacerta.workers.learn import recipes as _recipes  # noqa: F401
from lacerta.workers.corpus import capabilities as _cc  # noqa: F401
from lacerta.workers.corpus import recipes as _cr  # noqa: F401


def _syllabus_course(tmp_path: Path, course_id: str = "prac") -> tuple[Path, str]:
    notes = tmp_path / "notes.md"
    notes.write_text("# Sorting\n\nComparison sorts and counting.\n", encoding="utf-8")
    ctx = CapabilityContext(
        instance_id="default",
        course_id=course_id,
        data_root=str(tmp_path),
        attachments=[str(notes)],
        extra={"data_root": str(tmp_path), "topic": "Sorting"},
        user_request="Build syllabus",
    )
    job = JobSpec(
        job_id="syl",
        job_type="learn_syllabus_files",
        objective="Build syllabus",
        inputs={
            "recipe_id": "learn.syllabus_from_files",
            "course_id": course_id,
            "instance_id": "default",
            "root": str(tmp_path),
            "data_root": str(tmp_path),
            "attachments": [str(notes)],
        },
        tools=[],
    )
    result = run_recipe("learn.syllabus_from_files", ctx, job)
    assert result.ok, result.error
    root = storage.course_dir(tmp_path, "default", course_id)
    syllabus = storage.read_json(storage.syllabus_path(root))
    assert syllabus and syllabus.get("nodes")
    nid = str(syllabus["nodes"][0]["id"])
    return root, nid


def test_validate_quiz_payload() -> None:
    assert storage.validate_quiz_payload({"questions": []}) is not None
    good = {
        "questions": [
            {
                "id": "q1",
                "prompt": "P?",
                "choices": ["a", "b"],
                "correct_index": 0,
            }
        ]
    }
    assert storage.validate_quiz_payload(good) is None
    bad = {
        "questions": [
            {"id": "q1", "prompt": "P?", "choices": ["a"], "correct_index": 0}
        ]
    }
    assert storage.validate_quiz_payload(bad) is not None


def test_practice_quiz_grade_pass_and_fail(tmp_path: Path) -> None:
    root, nid = _syllabus_course(tmp_path)
    ctx = CapabilityContext(
        instance_id="default",
        course_id="prac",
        data_root=str(tmp_path),
        extra={"data_root": str(tmp_path), "node_id": nid},
    )
    gen = run_capability("learn.generate_quiz", ctx, {"node_id": nid, "questions_count": 3})
    assert gen.ok, gen.error_message
    quiz = storage.read_json(storage.quiz_path(root, nid))
    assert quiz and storage.validate_quiz_payload(quiz) is None
    assert quiz.get("grounding") == "deterministic_quiz"

    right = [
        {"question_id": q["id"], "selected_index": q["correct_index"]}
        for q in quiz["questions"]
    ]
    out = learn_caps.grade_practice_quiz(root, nid, right)
    assert out["ok"] and out["passed"]
    assert out["score"] == out["total"]
    assert Path(out["attempt_path"]).is_file()
    # mastery unchanged
    assert storage.get_node_tier(root, nid) == 0

    wrong = [{"question_id": q["id"], "selected_index": 1} for q in quiz["questions"]]
    out_fail = learn_caps.grade_practice_quiz(root, nid, wrong)
    assert out_fail["ok"]
    assert not out_fail["passed"]
    assert out_fail["score"] < out_fail["need"]


def test_flashcards_and_study_guide(tmp_path: Path) -> None:
    root, nid = _syllabus_course(tmp_path, course_id="prac2")
    ctx = CapabilityContext(
        instance_id="default",
        course_id="prac2",
        data_root=str(tmp_path),
        extra={"data_root": str(tmp_path)},
    )
    fc = run_capability("learn.generate_flashcards", ctx, {"node_id": nid})
    assert fc.ok, fc.error_message
    deck = storage.read_json(storage.flashcards_path(root, nid))
    assert deck and len(deck.get("cards") or []) >= 2

    sg = run_capability("learn.generate_study_guide", ctx, {"node_id": nid})
    assert sg.ok, sg.error_message
    path = storage.study_guide_path(root, nid)
    assert path.is_file()
    assert "Study guide" in path.read_text(encoding="utf-8")


def test_study_guide_includes_stem_table_token(tmp_path: Path) -> None:
    root, nid = _syllabus_course(tmp_path, course_id="stem-prac")
    mini = Path(__file__).parent / "fixtures" / "learn" / "mini_stem.md"
    ctx = CapabilityContext(
        instance_id="default",
        course_id="stem-prac",
        data_root=str(tmp_path),
        attachments=[str(mini)],
        extra={"data_root": str(tmp_path)},
        user_request="index",
    )
    job = JobSpec(
        job_id="idx",
        job_type="learn_index_corpus",
        objective="index",
        inputs={},
        tools=[],
    )
    assert run_recipe("learn.index_corpus", ctx, job).ok
    sg = run_capability(
        "learn.generate_study_guide",
        ctx,
        {"node_id": nid},
    )
    # Retrieve query is node title — may or may not hit STEM token depending on title.
    # Force retrieve-friendly: regenerate with title that matches mini_stem keywords via quiz path
    from lacerta.storage import corpus as corpus_storage

    croot = storage.corpus_dir(root)
    ret = run_capability(
        "corpus.retrieve",
        ctx,
        {
            "query": "planted cell reference values Quantity",
            "corpus_root": str(croot),
            "top_k": 3,
            "max_chars": 4000,
        },
    )
    assert ret.ok
    blob = " ".join(str(c.get("text") or "") for c in (ret.data.get("chunks") or []))
    assert "LACERTA_TABLE_CELL_42" in blob
    # Study guide for a STEM-titled node: write syllabus node title that matches
    syllabus = storage.read_json(storage.syllabus_path(root))
    syllabus["nodes"].append(
        {"id": "stem-n", "title": "Constants table planted cell", "parent_id": None}
    )
    storage.write_json(storage.syllabus_path(root), syllabus)
    storage.ensure_mastery(root, syllabus)
    sg2 = run_capability(
        "learn.generate_study_guide",
        ctx,
        {"node_id": "stem-n"},
    )
    assert sg2.ok, sg2.error_message
    text = storage.study_guide_path(root, "stem-n").read_text(encoding="utf-8")
    assert "LACERTA_TABLE_CELL_42" in text or "[table]" in text


def test_gui_practice_scenario_listed() -> None:
    learn = next(s for s in list_surfaces() if s["id"] == "learn")
    ids = {s["id"] for s in learn["learn_scenarios"]}
    assert "practice" in ids
    prac = next(s for s in learn["learn_scenarios"] if s["id"] == "practice")
    assert prac["require_node_id"] is True
    assert LEARN_SCENARIOS["practice"]["template_id"] == "tpl.learn.practice"


def test_build_run_inputs_practice_requires_node(tmp_path: Path) -> None:
    try:
        build_run_inputs(
            "learn",
            "quiz",
            str(tmp_path),
            scenario="practice",
            course_id="c1",
        )
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    inputs = build_run_inputs(
        "learn",
        "quiz",
        str(tmp_path),
        scenario="practice",
        course_id="c1",
        node_id="n1",
    )
    assert inputs["template_id"] == "tpl.learn.practice"
    assert inputs["node_id"] == "n1"
