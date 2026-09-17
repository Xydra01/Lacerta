"""Writing draft_sections: LLM vs deterministic."""

from __future__ import annotations

import json
from pathlib import Path

from lacerta.core.capabilities import CapabilityContext
from lacerta.workers.writing.brief import WritingBrief
from lacerta.workers.writing.capabilities import DraftSectionInput, draft_sections
from lacerta.workers.writing import storage


class _FakeClient:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.calls: list[list[dict]] = []

    def chat(self, messages, **kwargs):
        del kwargs
        self.calls.append(list(messages))
        return {"message": {"content": json.dumps(self.payload)}}


def _ctx(
    tmp_path: Path,
    *,
    client: object | None,
    topic: str = "Rewrite this source for technical depth",
) -> CapabilityContext:
    return CapabilityContext(
        surface="writing",
        user_request=topic,
        data_root=str(tmp_path),
        task_id="w1",
        client=client,
        extra={
            "brief": WritingBrief(
                title="Lacerta From Sources",
                scope="from_sources",
                advance_when="single_draft",
                target_document="from_sources.md",
            ).model_dump(),
        },
    )


def test_from_sources_uses_llm_when_mode_llm(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("LACERTA_WRITING_MODE", "llm")
    storage.save_draft(
        str(tmp_path),
        "w1",
        {
            "title": "Lacerta From Sources",
            "sections": [],
            "scratch": "Thin UI options are mashed into drop downs.",
        },
    )
    client = _FakeClient(
        {
            "title": "Thin UI Clarity",
            "sections": [
                {"header": "Problem", "body": "Drop downs hide what the thin UI is doing."},
                {"header": "Fix", "body": "Surface mode controls as clear choices instead."},
            ],
        }
    )
    result = draft_sections(_ctx(tmp_path, client=client), DraftSectionInput())
    assert result.ok
    draft = storage.load_draft(str(tmp_path), "w1")
    assert draft is not None
    assert draft["title"] == "Thin UI Clarity"
    assert draft["sections"][0]["header"] == "Problem"
    assert "Drop downs" in draft["sections"][0]["body"]
    assert "Local-first agents keep inference" not in draft["sections"][0]["body"]
    assert any("SOURCES" in m["content"] for turn in client.calls for m in turn if m["role"] == "user")


def test_from_sources_stays_deterministic_by_default(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("LACERTA_WRITING_MODE", raising=False)
    storage.save_draft(
        str(tmp_path),
        "w1",
        {
            "title": "Lacerta From Sources",
            "sections": [],
            "scratch": "Thin UI options are mashed into drop downs.",
        },
    )
    client = _FakeClient({"title": "Should Not Appear", "sections": [{"header": "X", "body": "Y"}]})
    result = draft_sections(_ctx(tmp_path, client=client), DraftSectionInput())
    assert result.ok
    draft = storage.load_draft(str(tmp_path), "w1")
    assert draft is not None
    assert "Local-first agents keep inference" in draft["sections"][0]["body"]
    assert client.calls == []
