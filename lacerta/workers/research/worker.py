"""ResearchWorker recipe runner."""

from __future__ import annotations

from typing import Any

from lacerta.core.capabilities import CapabilityContext, run_recipe
from lacerta.core.jobs import JobResult, JobSpec
from lacerta.workers.research import capabilities as _caps  # noqa: F401
from lacerta.workers.research import recipes as _recipes  # noqa: F401
from lacerta.workers.research.sources import SourceRegistry


def run(job: JobSpec, *, client: Any | None = None, surface: str = "research") -> JobResult:
    inputs = dict(job.inputs or {})
    recipe_id = str(inputs.get("recipe_id") or "research.offline")
    if job.job_type == "research_local":
        recipe_id = "research.offline"
    elif job.job_type == "research_web":
        recipe_id = str(inputs.get("recipe_id") or "research.full_web")
    elif job.job_type == "research_light":
        recipe_id = "research.light"

    data_root = str(inputs.get("data_root") or inputs.get("root") or ".")
    task_id = str(inputs.get("task_id") or job.job_id)
    ctx = CapabilityContext(
        client=client,
        task_id=task_id,
        surface=surface,
        offline=True,
        user_request=job.objective,
        attachments=list(inputs.get("attachments") or []),
        attachment_text_chunks=list(inputs.get("attachment_text_chunks") or []),
        instance_id=str(inputs.get("instance_id") or "default"),
        data_root=data_root,
        source_registry=SourceRegistry(),
        extra={"topic": inputs.get("topic") or job.objective},
    )
    return run_recipe(recipe_id, ctx, job)
