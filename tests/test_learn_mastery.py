"""V2.3 mastery 0–5 disk SoT + progress-aware Learn."""

from __future__ import annotations

from pathlib import Path

from lacerta.core.capabilities import CapabilityContext, run_capability
from lacerta.core.jobs import JobSpec
from lacerta.gui.surfaces import build_run_inputs, list_surfaces
from lacerta.workers.learn import capabilities as learn_caps  # noqa: F401
from lacerta.workers.learn import recipes as learn_recipes  # noqa: F401
from lacerta.workers.learn import storage
from lacerta.workers.learn.worker import run as learn_run


def _seed_course(tmp_path: Path, *, course_id: str = "mastery-course") -> Path:
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
    root = storage.course_dir(tmp_path, "default", course_id)
    assert storage.mastery_path(root).is_file()
    return root


def test_clamp_tier_bounds() -> None:
    assert storage.clamp_tier(-1) == 0
    assert storage.clamp_tier(0) == 0
    assert storage.clamp_tier(5) == 5
    assert storage.clamp_tier(99) == 5
    assert storage.clamp_tier("3") == 3
    assert storage.clamp_tier("x") == 0


def test_ensure_mastery_inits_zero(tmp_path: Path) -> None:
    root = _seed_course(tmp_path)
    doc = storage.load_mastery(root)
    assert doc["nodes"]
    for entry in doc["nodes"].values():
        assert entry["tier"] == 0


def test_set_node_tier_mirrors_syllabus(tmp_path: Path) -> None:
    root = _seed_course(tmp_path)
    syllabus = storage.read_json(storage.syllabus_path(root))
    assert syllabus
    nid = str(syllabus["nodes"][0]["id"])
    assert storage.set_node_tier(root, nid, 3) == 3
    assert storage.get_node_tier(root, nid) == 3
    syllabus2 = storage.read_json(storage.syllabus_path(root))
    node = next(n for n in syllabus2["nodes"] if str(n["id"]) == nid)
    assert node["mastery_tier"] == 3


def test_load_course_browse_uses_mastery_json(tmp_path: Path) -> None:
    root = _seed_course(tmp_path)
    syllabus = storage.read_json(storage.syllabus_path(root))
    nid = str(syllabus["nodes"][0]["id"])
    storage.set_node_tier(root, nid, 4)
    browse = storage.load_course_browse(tmp_path, "default", "mastery-course")
    node = next(n for n in browse["nodes"] if n["id"] == nid)
    assert node["mastery_tier"] == 4
    assert browse.get("mastery_path")


def test_assessment_prompts_tier_markers() -> None:
    low = learn_caps._assessment_prompts_for_tier("n1", "Sorting", 1)
    high = learn_caps._assessment_prompts_for_tier("n1", "Sorting", 5)
    low_blob = " ".join(q["prompt"] for q in low)
    high_blob = " ".join(q["prompt"] for q in high)
    assert learn_caps.HIGH_TIER_MARKER not in low_blob
    assert learn_caps.HIGH_TIER_MARKER in high_blob


def test_generate_assessments_respects_disk_mastery(tmp_path: Path) -> None:
    root = _seed_course(tmp_path)
    syllabus = storage.read_json(storage.syllabus_path(root))
    nid = str(syllabus["nodes"][0]["id"])
    storage.set_node_tier(root, nid, 1)
    ctx = CapabilityContext(
        instance_id="default",
        course_id="mastery-course",
        data_root=str(tmp_path),
        extra={"data_root": str(tmp_path)},
    )
    result = run_capability(
        "learn.generate_assessments",
        ctx,
        {"node_id": nid, "max_nodes": 1},
    )
    assert result.ok, result.error_message
    asm = storage.read_json(storage.assessments_dir(root) / "assessments.json")
    assert asm
    a0 = asm["assessments"][0]
    assert a0["target_tier"] == 1
    blob = " ".join(q["prompt"] for q in a0["questions"])
    assert learn_caps.HIGH_TIER_MARKER not in blob

    storage.set_node_tier(root, nid, 5)
    result2 = run_capability(
        "learn.generate_assessments",
        ctx,
        {"node_id": nid, "max_nodes": 1},
    )
    assert result2.ok, result2.error_message
    asm2 = storage.read_json(storage.assessments_dir(root) / "assessments.json")
    blob2 = " ".join(q["prompt"] for q in asm2["assessments"][0]["questions"])
    assert learn_caps.HIGH_TIER_MARKER in blob2


def test_mastery_check_grade_pass_and_fail(tmp_path: Path) -> None:
    root = _seed_course(tmp_path)
    syllabus = storage.read_json(storage.syllabus_path(root))
    nid = str(syllabus["nodes"][0]["id"])
    assert storage.get_node_tier(root, nid) == 0
    job = JobSpec(
        job_id="mc1",
        job_type="learn_mastery_check",
        objective="Mastery check",
        inputs={
            "recipe_id": "learn.mastery_check",
            "course_id": "mastery-course",
            "instance_id": "default",
            "root": str(tmp_path),
            "data_root": str(tmp_path),
            "node_id": nid,
        },
        tools=[],
    )
    result = learn_run(job)
    assert result.ok, result.error
    check = storage.read_json(storage.mastery_check_path(root, nid))
    assert check and check["questions"]

    # Fail: wrong answers → tier unchanged
    wrong = [
        {"question_id": q["id"], "selected_index": 1}
        for q in check["questions"]
    ]
    out_fail = learn_caps.grade_mastery_check(root, nid, wrong)
    assert out_fail["ok"] is True
    assert out_fail["passed"] is False
    assert out_fail["tier"] == 0

    # Pass: all correct → increment
    right = [
        {"question_id": q["id"], "selected_index": int(q["correct_index"])}
        for q in check["questions"]
    ]
    out_pass = learn_caps.grade_mastery_check(root, nid, right)
    assert out_pass["passed"] is True
    assert out_pass["tier"] == 1

    storage.set_node_tier(root, nid, 5)
    learn_run(job)
    check5 = storage.read_json(storage.mastery_check_path(root, nid))
    right5 = [
        {"question_id": q["id"], "selected_index": int(q["correct_index"])}
        for q in check5["questions"]
    ]
    out5 = learn_caps.grade_mastery_check(root, nid, right5)
    assert out5["passed"] is True
    assert out5["tier"] == 5


def test_tutor_includes_mastery_band(tmp_path: Path) -> None:
    root = _seed_course(tmp_path)
    syllabus = storage.read_json(storage.syllabus_path(root))
    nid = str(syllabus["nodes"][0]["id"])
    storage.set_node_tier(root, nid, 0)

    class Client:
        def __init__(self) -> None:
            self.messages = None

        def chat(self, messages, **kwargs):
            del kwargs
            self.messages = messages
            return {"message": {"content": "Intro-level reply about the unit."}}

    client = Client()
    ctx = CapabilityContext(
        client=client,
        instance_id="default",
        course_id="mastery-course",
        data_root=str(tmp_path),
        user_request="Explain this unit",
        extra={"data_root": str(tmp_path)},
    )
    result = run_capability(
        "learn.tutor_turn",
        ctx,
        {"question": "Explain this unit", "node_id": nid},
    )
    assert result.ok, result.error_message
    blob = " ".join(str(m.get("content") or "") for m in (client.messages or []))
    assert "MASTERY_BAND_INTRO" in blob
    assert "0/5" in blob

    storage.set_node_tier(root, nid, 5)
    client2 = Client()
    ctx.client = client2
    result2 = run_capability(
        "learn.tutor_turn",
        ctx,
        {"question": "Go deeper", "node_id": nid},
    )
    assert result2.ok, result2.error_message
    blob2 = " ".join(str(m.get("content") or "") for m in (client2.messages or []))
    assert "MASTERY_BAND_MASTER" in blob2


def test_gui_mastery_check_scenario_listed() -> None:
    learn = next(s for s in list_surfaces() if s["id"] == "learn")
    ids = {s["id"] for s in learn["learn_scenarios"]}
    assert "mastery_check" in ids
    mc = next(s for s in learn["learn_scenarios"] if s["id"] == "mastery_check")
    assert mc["require_node_id"] is True
    assert mc["show_node_id"] is True


def test_build_run_inputs_mastery_check_requires_node(tmp_path: Path) -> None:
    import pytest

    with pytest.raises(ValueError, match="Node id"):
        build_run_inputs(
            "learn",
            "check",
            str(tmp_path),
            scenario="mastery_check",
        )
    inputs = build_run_inputs(
        "learn",
        "check",
        str(tmp_path),
        scenario="mastery_check",
        node_id="n1",
    )
    assert inputs["template_id"] == "tpl.learn.mastery_check"
    assert inputs["node_id"] == "n1"
