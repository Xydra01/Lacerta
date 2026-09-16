"""Research bulk / corpus path tests (V1.4)."""

from __future__ import annotations

from pathlib import Path

from lacerta.core.jobs import JobSpec
from lacerta.gui.surfaces import build_run_inputs, list_surfaces
from lacerta.storage import corpus as corpus_storage
from lacerta.workers.research.bulk import attachments_need_corpus
from lacerta.workers.research.worker import run as research_run


def test_attachments_need_corpus_by_count(tmp_path: Path) -> None:
    paths = []
    for i in range(4):
        p = tmp_path / f"f{i}.md"
        p.write_text("x\n", encoding="utf-8")
        paths.append(str(p))
    assert attachments_need_corpus(paths) is True
    assert attachments_need_corpus(paths[:2]) is False


def test_attachments_need_corpus_by_bytes(tmp_path: Path) -> None:
    p = tmp_path / "big.md"
    p.write_text("a" * 80_001, encoding="utf-8")
    assert attachments_need_corpus([str(p)]) is True


def test_resolve_task_corpus_root(tmp_path: Path) -> None:
    root = corpus_storage.resolve_task_corpus_root(tmp_path, "tid", surface="research")
    assert root == tmp_path / "tasks" / "tid" / "research" / "corpus"


def test_research_offline_corpus_recipe(tmp_path: Path) -> None:
    bulk = Path(__file__).parent / "fixtures" / "research" / "bulk"
    attachments = [str(bulk / name) for name in ("part_a.md", "part_b.md", "part_c.md", "part_d.md")]
    job = JobSpec(
        job_id="rb1",
        job_type="research_local",
        objective="What is the secret research token?",
        inputs={
            "recipe_id": "research.offline_corpus",
            "use_corpus": True,
            "root": str(tmp_path),
            "data_root": str(tmp_path),
            "task_id": "bulk-unit",
            "attachments": attachments,
            "topic": "secret research token",
        },
        tools=[],
    )
    result = research_run(job)
    assert result.ok, result.error
    croot = corpus_storage.resolve_task_corpus_root(tmp_path, "bulk-unit")
    meta = corpus_storage.load_meta(croot)
    assert meta["status"] == "complete"
    assert meta["index_backend"] == "keyword"
    report = tmp_path / "tasks" / "bulk-unit" / "research" / "report.md"
    assert report.is_file()
    text = report.read_text(encoding="utf-8")
    assert "LACERTA_RESEARCH_PLANTED_ZEBRA" in text


def test_research_and_writing_scenario_labels() -> None:
    surfaces = {s["id"]: s for s in list_surfaces()}
    research = surfaces["research"]
    writing = surfaces["writing"]
    assert research["show_research_scenario"] is True
    assert {s["id"] for s in research["research_scenarios"]} == {
        "offline_sources",
        "light_web",
    }
    assert writing["show_writing_scenario"] is True
    assert {s["id"] for s in writing["writing_scenarios"]} == {
        "short_draft",
        "from_sources",
    }
    labels = " ".join(s["label"] for s in research["research_scenarios"]).lower()
    assert "deferred" in labels
    assert "research_web" not in labels


def test_build_run_inputs_writing_from_sources(tmp_path: Path) -> None:
    inputs = build_run_inputs(
        "writing",
        "Draft from notes",
        str(tmp_path),
        scenario="from_sources",
        attachments=["/tmp/a.md"],
        title="My Title",
    )
    assert inputs["template_id"] == "tpl.writing.from_sources"
    assert inputs["attachments"] == ["/tmp/a.md"]
    assert inputs["title"] == "My Title"
