"""WritingWorker recipe runner."""

from __future__ import annotations

from typing import Any

from lacerta.core.capabilities import CapabilityContext, run_capability, run_recipe
from lacerta.core.jobs import JobResult, JobSpec
from lacerta.workers.writing import capabilities as _caps  # noqa: F401
from lacerta.workers.writing import recipes as _recipes  # noqa: F401
from lacerta.workers.writing.brief import brief_from_inputs


def run(job: JobSpec, *, client: Any | None = None, surface: str = "writing") -> JobResult:
    inputs = dict(job.inputs or {})
    recipe_id = str(inputs.get("recipe_id") or "writing.dynamic")
    if job.job_type == "write_from_sources":
        recipe_id = str(inputs.get("recipe_id") or "writing.from_sources")
    elif job.job_type == "write_finalize":
        # Single capability path
        data_root = str(inputs.get("data_root") or inputs.get("root") or ".")
        task_id = str(inputs.get("task_id") or job.job_id)
        brief = brief_from_inputs(inputs)
        ctx = CapabilityContext(
            client=client,
            task_id=task_id,
            surface=surface,
            user_request=job.objective,
            attachments=list(inputs.get("attachments") or []),
            data_root=data_root,
            extra={
                "brief": brief.model_dump(),
                "title": brief.title,
                "topic": inputs.get("topic") or job.objective,
                "data_root": data_root,
            },
        )
        result = run_capability(
            "writing.finalize_deliverable",
            ctx,
            {"slug": brief.target_document or "short.md"},
        )
        if not result.ok:
            return JobResult(
                job_id=job.job_id,
                ok=False,
                summary=result.summary or "",
                error=result.error_message,
            )
        artifacts = []
        if p := result.data.get("path"):
            artifacts.append(str(p))
        return JobResult(
            job_id=job.job_id,
            ok=True,
            summary=result.summary or "Finalized",
            artifacts=artifacts,
        )
    elif job.job_type == "write_draft":
        recipe_id = str(inputs.get("recipe_id") or "writing.dynamic")

    data_root = str(inputs.get("data_root") or inputs.get("root") or ".")
    task_id = str(inputs.get("task_id") or job.job_id)
    brief = brief_from_inputs(inputs)
    # Default short harness brief
    if job.job_type == "write_draft" and "brief" not in inputs:
        brief.scope = "short_form"
        brief.advance_when = "single_draft"
        brief.target_document = str(inputs.get("target_document") or "short.md")
        if not brief.title or brief.title == "Untitled":
            brief.title = "Lacerta Writing Draft"

    ctx = CapabilityContext(
        client=client,
        task_id=task_id,
        surface=surface,
        user_request=job.objective,
        attachments=list(inputs.get("attachments") or []),
        attachment_text_chunks=list(inputs.get("attachment_text_chunks") or []),
        data_root=data_root,
        extra={
            "brief": brief.model_dump(),
            "title": brief.title,
            "topic": inputs.get("topic") or job.objective,
            "data_root": data_root,
        },
    )
    return run_recipe(recipe_id, ctx, job)
