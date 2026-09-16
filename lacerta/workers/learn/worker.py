"""LearnWorker — recipe runner for learn_* JobTypes."""

from __future__ import annotations

from typing import Any

from lacerta.core.capabilities import CapabilityContext, run_recipe
from lacerta.core.jobs import JobResult, JobSpec

# Ensure capabilities/recipes register on import
from lacerta.workers.corpus import capabilities as _corpus_caps  # noqa: F401
from lacerta.workers.corpus import recipes as _corpus_recipes  # noqa: F401
from lacerta.workers.learn import capabilities as _capabilities  # noqa: F401
from lacerta.workers.learn import recipes as _recipes  # noqa: F401


def run(job: JobSpec, *, client: Any | None = None, surface: str = "learn") -> JobResult:
    inputs = dict(job.inputs or {})
    recipe_id = str(inputs.get("recipe_id") or "learn.syllabus_from_files")
    if job.job_type == "learn_syllabus_files":
        recipe_id = str(inputs.get("recipe_id") or "learn.syllabus_from_files")
    elif job.job_type == "learn_syllabus_web":
        recipe_id = str(inputs.get("recipe_id") or "learn.syllabus_from_web")
    elif job.job_type == "learn_tutor_turn":
        recipe_id = str(inputs.get("recipe_id") or "learn.tutor_turn")
    elif job.job_type == "learn_assessment":
        recipe_id = str(inputs.get("recipe_id") or "learn.assessment")
    elif job.job_type == "learn_mastery_check":
        recipe_id = str(inputs.get("recipe_id") or "learn.mastery_check")
    elif job.job_type == "learn_practice_quiz":
        recipe_id = str(inputs.get("recipe_id") or "learn.practice_quiz")
    elif job.job_type == "learn_archive_chat":
        recipe_id = str(inputs.get("recipe_id") or "learn.archive_chat")
    elif job.job_type == "learn_index_corpus":
        recipe_id = str(inputs.get("recipe_id") or "learn.index_corpus")

    data_root = str(inputs.get("data_root") or inputs.get("root") or ".")
    extra: dict[str, Any] = {
        "topic": inputs.get("topic") or job.objective,
        "data_root": data_root,
    }
    if inputs.get("node_id"):
        extra["node_id"] = inputs["node_id"]
    if inputs.get("target_tier") is not None:
        extra["target_tier"] = inputs["target_tier"]
    if inputs.get("corpus_root"):
        extra["corpus_root"] = inputs["corpus_root"]

    ctx = CapabilityContext(
        client=client,
        task_id=job.job_id,
        surface=surface,
        offline=True,
        user_request=job.objective,
        attachments=list(inputs.get("attachments") or []),
        attachment_text_chunks=list(inputs.get("attachment_text_chunks") or []),
        instance_id=str(inputs.get("instance_id") or "default"),
        course_id=str(inputs.get("course_id") or "course"),
        data_root=data_root,
        extra=extra,
    )
    return run_recipe(recipe_id, ctx, job)
