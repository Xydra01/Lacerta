"""Writing MacroTemplates."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from lacerta.core.jobs import JobSpec

if TYPE_CHECKING:
    from lacerta.core.manager import MacroState


class WritingShortTemplate:
    template_id = "tpl.writing.short"

    def can_handle(self, state: MacroState) -> bool:
        if state.surface != "writing":
            return False
        tid = str(state.inputs.get("template_id") or self.template_id)
        return tid == self.template_id

    def next_job(self, state: MacroState) -> JobSpec | None:
        if state.plan:
            return None
        root = state.inputs.get("root")
        if not root:
            raise ValueError("tpl.writing.short requires root")
        task_id = str(state.inputs.get("task_id") or f"writing-{uuid.uuid4().hex[:8]}")
        target = str(state.inputs.get("target_document") or "short.md")
        job = JobSpec(
            job_id=f"write-draft-{uuid.uuid4().hex[:8]}",
            job_type="write_draft",
            objective=state.goal,
            inputs={
                "recipe_id": "writing.dynamic",
                "root": str(root),
                "data_root": str(root),
                "task_id": task_id,
                "target_document": target,
                "topic": state.inputs.get("topic") or state.goal,
                "brief": {
                    "scope": "short_form",
                    "advance_when": "single_draft",
                    "target_document": target,
                    "title": str(state.inputs.get("title") or "Lacerta Writing Draft"),
                    "target_paragraphs": 2,
                },
            },
            tools=[],
            acceptance=dict(state.inputs.get("acceptance") or {}),
            max_turns=1,
        )
        state.plan.append("write_draft")
        return job


WRITING_TEMPLATES: dict[str, Any] = {
    WritingShortTemplate.template_id: WritingShortTemplate(),
}
