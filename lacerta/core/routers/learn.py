"""Learn surface MacroTemplates."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from lacerta.core.jobs import JobSpec

if TYPE_CHECKING:
    from lacerta.core.manager import MacroState


def _learn_roots(state: MacroState) -> tuple[str, str, str]:
    root = state.inputs.get("root") or state.inputs.get("data_root")
    if not root:
        raise ValueError("learn template requires inputs['root']")
    course_id = str(state.inputs.get("course_id") or "harness-course")
    instance_id = str(state.inputs.get("instance_id") or "default")
    return str(root), course_id, instance_id


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
        root, course_id, instance_id = _learn_roots(state)
        job = JobSpec(
            job_id=f"learn-files-{uuid.uuid4().hex[:8]}",
            job_type="learn_syllabus_files",
            objective=state.goal,
            inputs={
                "recipe_id": "learn.syllabus_from_files",
                "course_id": course_id,
                "instance_id": instance_id,
                "root": root,
                "data_root": root,
                "attachments": list(state.inputs.get("attachments") or []),
                "topic": state.inputs.get("topic") or state.goal,
            },
            tools=[],
            acceptance=dict(state.inputs.get("acceptance") or {}),
            max_turns=1,
        )
        state.plan.append("learn_syllabus_files")
        return job


class LearnTutorTemplate:
    template_id = "tpl.learn.tutor"

    def can_handle(self, state: MacroState) -> bool:
        if state.surface != "learn":
            return False
        tid = str(state.inputs.get("template_id") or "")
        return tid == self.template_id

    def next_job(self, state: MacroState) -> JobSpec | None:
        if state.plan:
            return None
        root, course_id, instance_id = _learn_roots(state)
        job = JobSpec(
            job_id=f"learn-tutor-{uuid.uuid4().hex[:8]}",
            job_type="learn_tutor_turn",
            objective=state.goal,
            inputs={
                "recipe_id": "learn.tutor_turn",
                "course_id": course_id,
                "instance_id": instance_id,
                "root": root,
                "data_root": root,
                "question": state.inputs.get("question") or state.goal,
                "node_id": state.inputs.get("node_id"),
                "topic": state.inputs.get("topic") or state.goal,
            },
            tools=[],
            acceptance=dict(state.inputs.get("acceptance") or {}),
            max_turns=1,
        )
        state.plan.append("learn_tutor_turn")
        return job


class LearnAssessmentTemplate:
    template_id = "tpl.learn.assessment"

    def can_handle(self, state: MacroState) -> bool:
        if state.surface != "learn":
            return False
        tid = str(state.inputs.get("template_id") or "")
        return tid == self.template_id

    def next_job(self, state: MacroState) -> JobSpec | None:
        if state.plan:
            return None
        root, course_id, instance_id = _learn_roots(state)
        job = JobSpec(
            job_id=f"learn-asm-{uuid.uuid4().hex[:8]}",
            job_type="learn_assessment",
            objective=state.goal,
            inputs={
                "recipe_id": "learn.assessment",
                "course_id": course_id,
                "instance_id": instance_id,
                "root": root,
                "data_root": root,
                "node_id": state.inputs.get("node_id"),
                "topic": state.inputs.get("topic") or state.goal,
                "max_nodes": state.inputs.get("max_nodes") or 5,
            },
            tools=[],
            acceptance=dict(state.inputs.get("acceptance") or {}),
            max_turns=1,
        )
        if state.inputs.get("target_tier") is not None:
            job.inputs["target_tier"] = state.inputs.get("target_tier")
        state.plan.append("learn_assessment")
        return job


class LearnMasteryCheckTemplate:
    template_id = "tpl.learn.mastery_check"

    def can_handle(self, state: MacroState) -> bool:
        if state.surface != "learn":
            return False
        tid = str(state.inputs.get("template_id") or "")
        return tid == self.template_id

    def next_job(self, state: MacroState) -> JobSpec | None:
        if state.plan:
            return None
        root, course_id, instance_id = _learn_roots(state)
        node_id = state.inputs.get("node_id")
        job = JobSpec(
            job_id=f"learn-mc-{uuid.uuid4().hex[:8]}",
            job_type="learn_mastery_check",
            objective=state.goal,
            inputs={
                "recipe_id": "learn.mastery_check",
                "course_id": course_id,
                "instance_id": instance_id,
                "root": root,
                "data_root": root,
                "node_id": node_id,
                "topic": state.inputs.get("topic") or state.goal,
            },
            tools=[],
            acceptance=dict(state.inputs.get("acceptance") or {}),
            max_turns=1,
        )
        state.plan.append("learn_mastery_check")
        return job


class LearnPracticeQuizTemplate:
    template_id = "tpl.learn.practice"

    def can_handle(self, state: MacroState) -> bool:
        if state.surface != "learn":
            return False
        tid = str(state.inputs.get("template_id") or "")
        return tid == self.template_id

    def next_job(self, state: MacroState) -> JobSpec | None:
        if state.plan:
            return None
        root, course_id, instance_id = _learn_roots(state)
        node_id = state.inputs.get("node_id")
        job = JobSpec(
            job_id=f"learn-quiz-{uuid.uuid4().hex[:8]}",
            job_type="learn_practice_quiz",
            objective=state.goal,
            inputs={
                "recipe_id": "learn.practice_quiz",
                "course_id": course_id,
                "instance_id": instance_id,
                "root": root,
                "data_root": root,
                "node_id": node_id,
                "topic": state.inputs.get("topic") or state.goal,
            },
            tools=[],
            acceptance=dict(state.inputs.get("acceptance") or {}),
            max_turns=1,
        )
        state.plan.append("learn_practice_quiz")
        return job


class LearnIndexCorpusTemplate:
    template_id = "tpl.learn.index_corpus"

    def can_handle(self, state: MacroState) -> bool:
        if state.surface != "learn":
            return False
        tid = str(state.inputs.get("template_id") or "")
        return tid == self.template_id

    def next_job(self, state: MacroState) -> JobSpec | None:
        if state.plan:
            return None
        root, course_id, instance_id = _learn_roots(state)
        job = JobSpec(
            job_id=f"learn-index-{uuid.uuid4().hex[:8]}",
            job_type="learn_index_corpus",
            objective=state.goal,
            inputs={
                "recipe_id": "learn.index_corpus",
                "course_id": course_id,
                "instance_id": instance_id,
                "root": root,
                "data_root": root,
                "attachments": list(state.inputs.get("attachments") or []),
                "topic": state.inputs.get("topic") or state.goal,
            },
            tools=[],
            acceptance=dict(state.inputs.get("acceptance") or {}),
            max_turns=1,
        )
        state.plan.append("learn_index_corpus")
        return job


class LearnArchiveChatTemplate:
    template_id = "tpl.learn.archive_chat"

    def can_handle(self, state: MacroState) -> bool:
        if state.surface != "learn":
            return False
        tid = str(state.inputs.get("template_id") or "")
        return tid == self.template_id

    def next_job(self, state: MacroState) -> JobSpec | None:
        if state.plan:
            return None
        root, course_id, instance_id = _learn_roots(state)
        job = JobSpec(
            job_id=f"learn-archive-{uuid.uuid4().hex[:8]}",
            job_type="learn_archive_chat",
            objective=state.goal,
            inputs={
                "recipe_id": "learn.archive_chat",
                "course_id": course_id,
                "instance_id": instance_id,
                "root": root,
                "data_root": root,
                "message": state.inputs.get("message") or state.goal,
                "topic": state.inputs.get("topic") or state.goal,
            },
            tools=[],
            acceptance=dict(state.inputs.get("acceptance") or {}),
            max_turns=1,
        )
        state.plan.append("learn_archive_chat")
        return job


LEARN_TEMPLATES: dict[str, Any] = {
    LearnSyllabusFilesTemplate.template_id: LearnSyllabusFilesTemplate(),
    LearnTutorTemplate.template_id: LearnTutorTemplate(),
    LearnAssessmentTemplate.template_id: LearnAssessmentTemplate(),
    LearnMasteryCheckTemplate.template_id: LearnMasteryCheckTemplate(),
    LearnPracticeQuizTemplate.template_id: LearnPracticeQuizTemplate(),
    LearnIndexCorpusTemplate.template_id: LearnIndexCorpusTemplate(),
    LearnArchiveChatTemplate.template_id: LearnArchiveChatTemplate(),
}
