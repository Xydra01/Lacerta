"""ResearchWorker recipe runner."""

from __future__ import annotations

from typing import Any

from lacerta.core.capabilities import CapabilityContext, run_recipe
from lacerta.core.jobs import JobResult, JobSpec
from lacerta.storage import corpus as corpus_storage
from lacerta.workers.corpus import capabilities as _corpus_caps  # noqa: F401
from lacerta.workers.corpus import recipes as _corpus_recipes  # noqa: F401
from lacerta.workers.research import capabilities as _caps  # noqa: F401
from lacerta.workers.research import recipes as _recipes  # noqa: F401
from lacerta.workers.research.bulk import attachments_need_corpus
from lacerta.workers.research.sources import SourceRegistry


def _select_local_recipe(inputs: dict[str, Any], attachments: list[str]) -> str:
    explicit = inputs.get("recipe_id")
    if explicit in ("research.offline", "research.offline_corpus"):
        return str(explicit)
    if inputs.get("use_corpus") is True or attachments_need_corpus(attachments):
        return "research.offline_corpus"
    return "research.offline"


def run(job: JobSpec, *, client: Any | None = None, surface: str = "research") -> JobResult:
    inputs = dict(job.inputs or {})
    attachments = list(inputs.get("attachments") or [])
    recipe_id = str(inputs.get("recipe_id") or "research.offline")
    if job.job_type == "research_local":
        recipe_id = _select_local_recipe(inputs, attachments)
    elif job.job_type == "research_web":
        recipe_id = str(inputs.get("recipe_id") or "research.full_web")
    elif job.job_type == "research_light":
        recipe_id = "research.light"

    data_root = str(inputs.get("data_root") or inputs.get("root") or ".")
    task_id = str(inputs.get("task_id") or job.job_id)
    corpus_root = str(
        inputs.get("corpus_root")
        or corpus_storage.resolve_task_corpus_root(data_root, task_id, surface="research")
    )
    ctx = CapabilityContext(
        client=client,
        task_id=task_id,
        surface=surface,
        offline=True,
        user_request=job.objective,
        attachments=attachments,
        attachment_text_chunks=list(inputs.get("attachment_text_chunks") or []),
        instance_id=str(inputs.get("instance_id") or "default"),
        data_root=data_root,
        source_registry=SourceRegistry(),
        extra={
            "topic": inputs.get("topic") or job.objective,
            "data_root": data_root,
            "corpus_root": corpus_root,
        },
    )
    return run_recipe(recipe_id, ctx, job)
