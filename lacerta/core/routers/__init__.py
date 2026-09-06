"""Deterministic MacroTemplates per surface."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from lacerta.core.routers.chat import CHAT_TEMPLATES, ChatPlainTemplate
from lacerta.core.routers.code import CODE_TEMPLATES, CodeHabitTemplate, CodeSmokeTemplate
from lacerta.core.routers.learn import LEARN_TEMPLATES, LearnSyllabusFilesTemplate
from lacerta.core.routers.research import RESEARCH_TEMPLATES, ResearchOfflineTemplate
from lacerta.core.routers.writing import WRITING_TEMPLATES, WritingShortTemplate

if TYPE_CHECKING:
    from lacerta.core.jobs import JobSpec
    from lacerta.core.manager import MacroState


class TemplateRouter(Protocol):
    template_id: str

    def can_handle(self, state: MacroState) -> bool: ...

    def next_job(self, state: MacroState) -> JobSpec | None: ...


TEMPLATES: dict[str, TemplateRouter] = {
    **CODE_TEMPLATES,
    **LEARN_TEMPLATES,
    **RESEARCH_TEMPLATES,
    **WRITING_TEMPLATES,
    **CHAT_TEMPLATES,
}


def select_template(state: MacroState) -> TemplateRouter | None:
    tid = str(state.inputs.get("template_id") or "").strip()
    if tid and tid in TEMPLATES:
        router = TEMPLATES[tid]
        if router.can_handle(state):
            return router
        if tid == CodeHabitTemplate.template_id:
            return router
        return None
    for router in TEMPLATES.values():
        if router.can_handle(state):
            return router
    return None


def list_template_ids() -> list[str]:
    return sorted(TEMPLATES)


__all__ = [
    "CHAT_TEMPLATES",
    "CODE_TEMPLATES",
    "LEARN_TEMPLATES",
    "RESEARCH_TEMPLATES",
    "WRITING_TEMPLATES",
    "ChatPlainTemplate",
    "CodeHabitTemplate",
    "CodeSmokeTemplate",
    "LearnSyllabusFilesTemplate",
    "ResearchOfflineTemplate",
    "WritingShortTemplate",
    "TEMPLATES",
    "TemplateRouter",
    "list_template_ids",
    "select_template",
]
