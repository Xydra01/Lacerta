"""Research MacroTemplates."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from lacerta.core.jobs import JobSpec
from lacerta.workers.research.bulk import attachments_need_corpus

if TYPE_CHECKING:
    from lacerta.core.manager import MacroState


class ResearchOfflineTemplate:
    template_id = "tpl.research.offline"

    def can_handle(self, state: MacroState) -> bool:
        if state.surface != "research":
            return False
        tid = str(state.inputs.get("template_id") or self.template_id)
        return tid == self.template_id

    def next_job(self, state: MacroState) -> JobSpec | None:
        if state.plan:
            return None
        root = state.inputs.get("root")
        if not root:
            raise ValueError("tpl.research.offline requires root")
        task_id = str(state.inputs.get("task_id") or f"research-{uuid.uuid4().hex[:8]}")
        attachments = list(state.inputs.get("attachments") or [])
        use_corpus = bool(state.inputs.get("use_corpus")) or attachments_need_corpus(
            attachments
        )
        recipe_id = (
            str(state.inputs.get("recipe_id"))
            if state.inputs.get("recipe_id")
            in ("research.offline", "research.offline_corpus")
            else ("research.offline_corpus" if use_corpus else "research.offline")
        )
        job = JobSpec(
            job_id=f"research-local-{uuid.uuid4().hex[:8]}",
            job_type="research_local",
            objective=state.goal,
            inputs={
                "recipe_id": recipe_id,
                "use_corpus": use_corpus,
                "root": str(root),
                "data_root": str(root),
                "task_id": task_id,
                "attachments": attachments,
                "topic": state.inputs.get("topic") or state.goal,
            },
            tools=[],
            acceptance=dict(state.inputs.get("acceptance") or {}),
            max_turns=1,
        )
        state.plan.append("research_local")
        return job


class ResearchWebTemplate:
    """Light-web path — gather is honestly deferred (V1.4)."""

    template_id = "tpl.research.web"

    def can_handle(self, state: MacroState) -> bool:
        if state.surface != "research":
            return False
        tid = str(state.inputs.get("template_id") or "")
        return tid == self.template_id

    def next_job(self, state: MacroState) -> JobSpec | None:
        if state.plan:
            return None
        root = state.inputs.get("root")
        if not root:
            raise ValueError("tpl.research.web requires root")
        task_id = str(state.inputs.get("task_id") or f"research-{uuid.uuid4().hex[:8]}")
        job = JobSpec(
            job_id=f"research-web-{uuid.uuid4().hex[:8]}",
            job_type="research_web",
            objective=state.goal,
            inputs={
                "recipe_id": "research.full_web",
                "root": str(root),
                "data_root": str(root),
                "task_id": task_id,
                "attachments": list(state.inputs.get("attachments") or []),
                "topic": state.inputs.get("topic") or state.goal,
            },
            tools=[],
            acceptance=dict(state.inputs.get("acceptance") or {}),
            max_turns=1,
        )
        state.plan.append("research_web")
        return job


RESEARCH_TEMPLATES: dict[str, Any] = {
    ResearchOfflineTemplate.template_id: ResearchOfflineTemplate(),
    ResearchWebTemplate.template_id: ResearchWebTemplate(),
}
