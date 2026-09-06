"""advance_when enforcement for writing finalize."""

from __future__ import annotations

from pathlib import Path

from lacerta.core.capabilities import CapabilityContext
from lacerta.workers.writing.brief import WritingBrief
from lacerta.workers.writing.capabilities import finalize_deliverable, FinalizeInput
from lacerta.workers.writing import storage


def _ctx(tmp: Path, brief: WritingBrief) -> CapabilityContext:
    return CapabilityContext(
        task_id="adv-test",
        surface="writing",
        data_root=str(tmp),
        extra={"brief": brief.model_dump(), "data_root": str(tmp)},
    )


def test_single_draft_blocks_empty(tmp_path: Path) -> None:
    brief = WritingBrief(advance_when="single_draft", target_document="out.md")
    storage.save_draft(tmp_path, "adv-test", storage.default_draft(title="Empty"))
    result = finalize_deliverable(_ctx(tmp_path, brief), FinalizeInput())
    assert not result.ok
    assert result.error_code == "advance_blocked"


def test_single_draft_allows_after_section(tmp_path: Path) -> None:
    brief = WritingBrief(advance_when="single_draft", target_document="out.md", title="Ready")
    draft = storage.default_draft(title="Ready")
    draft["sections"] = [
        {
            "header": "Body",
            "body": "x" * 100,
        }
    ]
    storage.save_draft(tmp_path, "adv-test", draft)
    result = finalize_deliverable(_ctx(tmp_path, brief), FinalizeInput(slug="out.md"))
    assert result.ok, result.error_message
    out = tmp_path / "tasks" / "adv-test" / "writing" / "out.md"
    assert out.is_file()
    text = out.read_text(encoding="utf-8")
    assert text.startswith("# Ready")
    assert len(text) >= 100
