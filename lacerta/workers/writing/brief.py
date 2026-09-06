"""Writing brief model (surfaces §8.1)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

WritingScope = Literal["quick_edit", "short_form", "standard", "from_sources"]
WritingTone = Literal["neutral", "formal", "conversational", "technical", "custom"]
LengthMode = Literal["words", "paragraphs", "sections", "flexible"]
AdvanceWhen = Literal["scope_met", "single_draft", "manual"]


class WritingBrief(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scope: WritingScope = "short_form"
    tone: WritingTone = "neutral"
    tone_custom: str = ""
    length_mode: LengthMode = "paragraphs"
    target_words: int | None = None
    target_paragraphs: int | None = 2
    target_sections: int | None = None
    advance_when: AdvanceWhen = "single_draft"
    target_document: str | None = "short.md"
    has_attachments: bool = False
    title: str = "Untitled"


def brief_from_inputs(inputs: dict) -> WritingBrief:
    raw = dict(inputs.get("brief") or {})
    if inputs.get("title") and "title" not in raw:
        raw["title"] = inputs["title"]
    if inputs.get("scope"):
        raw.setdefault("scope", inputs["scope"])
    if inputs.get("advance_when"):
        raw.setdefault("advance_when", inputs["advance_when"])
    if inputs.get("target_document"):
        raw.setdefault("target_document", inputs["target_document"])
    return WritingBrief.model_validate(raw)
