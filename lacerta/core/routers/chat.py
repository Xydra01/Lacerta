"""Chat MacroTemplates (manager-local)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from lacerta.core.jobs import JobSpec

if TYPE_CHECKING:
    from lacerta.core.manager import MacroState


class ChatPlainTemplate:
    template_id = "tpl.chat.plain"

    def can_handle(self, state: MacroState) -> bool:
        if state.surface != "chat":
            return False
        tid = str(state.inputs.get("template_id") or self.template_id)
        return tid == self.template_id

    def next_job(self, state: MacroState) -> JobSpec | None:
        light = bool(state.inputs.get("light_research"))
        planned = set(state.plan)

        if light and "research_light" not in planned:
            root = state.inputs.get("root") or "."
            job = JobSpec(
                job_id=f"research-light-{uuid.uuid4().hex[:8]}",
                job_type="research_light",
                objective=state.goal,
                inputs={
                    "recipe_id": "research.light",
                    "root": str(root),
                    "data_root": str(root),
                    "task_id": str(state.inputs.get("task_id") or f"chat-{uuid.uuid4().hex[:8]}"),
                    "user_input": state.goal,
                },
                tools=[],
                max_turns=1,
            )
            state.plan.append("research_light")
            return job

        if "chat_answer" in planned:
            return None

        context = ""
        if light and state.results:
            # Pull light research summary into chat context
            last = state.results[-1]
            context = str(last.get("summary") or "")
            metrics = last.get("metrics") or {}
            if isinstance(metrics, dict) and metrics.get("context"):
                context = str(metrics["context"])

        job = JobSpec(
            job_id=f"chat-{uuid.uuid4().hex[:8]}",
            job_type="chat_answer",
            objective=state.goal,
            inputs={
                "context": context or str(state.inputs.get("context") or ""),
                "messages": list(state.inputs.get("messages") or []),
                "root": str(state.inputs.get("root") or "."),
            },
            tools=[],
            max_turns=1,
        )
        state.plan.append("chat_answer")
        return job


CHAT_TEMPLATES: dict[str, Any] = {
    ChatPlainTemplate.template_id: ChatPlainTemplate(),
}
