"""LearnWorker — recipe runner for learn_* JobTypes."""

from __future__ import annotations

from typing import Any

from lacerta.core.capabilities import CapabilityContext, run_recipe
from lacerta.core.jobs import JobResult, JobSpec

# Ensure capabilities/recipes register on import
from lacerta.workers.learn import capabilities as _capabilities  # noqa: F401
from lacerta.workers.learn import recipes as _recipes  # noqa: F401


def run(job: JobSpec, *, client: Any | None = None, surface: str = "learn") -> JobResult:
    inputs = dict(job.inputs or {})
    recipe_id = str(inputs.get("recipe_id") or "learn.syllabus_from_files")
    if job.job_type == "learn_syllabus_files":
        recipe_id = str(inputs.get("recipe_id") or "learn.syllabus_from_files")
    elif job.job_type == "learn_syllabus_web":
        recipe_id = str(inputs.get("recipe_id") or "learn.syllabus_from_web")
    elif job.job_type in (
        "learn_tutor_turn",
        "learn_archive_chat",
        "learn_assessment",
        "learn_index_corpus",
    ):
        return JobResult(
            job_id=job.job_id,
            ok=False,
            summary="",
            error=f"{job.job_type} not implemented yet (see V1.3 / V1.35)",
        )

    data_root = str(inputs.get("data_root") or inputs.get("root") or ".")
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
        extra={
            "topic": inputs.get("topic") or job.objective,
            "data_root": data_root,
        },
    )
    return run_recipe(recipe_id, ctx, job)
