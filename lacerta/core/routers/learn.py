"""Learn surface MacroTemplates."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from lacerta.core.jobs import JobSpec

if TYPE_CHECKING:
    from lacerta.core.manager import MacroState


class LearnSyllabusFilesTemplate:
    template_id = "tpl.learn.syllabus_files"

    def can_handle(self, state: MacroState) -> bool:
        if state.surface != "learn":
            return False
        tid = str(state.inputs.get("template_id") or self.template_id)
        return tid == self.template_id

    def next_job(self, state: MacroState) -> JobSpec | None:
        if state.plan:
            return None
        root = state.inputs.get("root") or state.inputs.get("data_root")
        if not root:
            raise ValueError("tpl.learn.syllabus_files requires inputs['root']")
        course_id = str(state.inputs.get("course_id") or "harness-course")
        instance_id = str(state.inputs.get("instance_id") or "default")
        job = JobSpec(
            job_id=f"learn-files-{uuid.uuid4().hex[:8]}",
            job_type="learn_syllabus_files",
            objective=state.goal,
            inputs={
                "recipe_id": "learn.syllabus_from_files",
                "course_id": course_id,
                "instance_id": instance_id,
                "root": str(root),
                "data_root": str(root),
                "attachments": list(state.inputs.get("attachments") or []),
                "topic": state.inputs.get("topic") or state.goal,
            },
            tools=[],
            acceptance=dict(state.inputs.get("acceptance") or {}),
            max_turns=1,
        )
        state.plan.append("learn_syllabus_files")
        return job


LEARN_TEMPLATES: dict[str, Any] = {
    LearnSyllabusFilesTemplate.template_id: LearnSyllabusFilesTemplate(),
}
