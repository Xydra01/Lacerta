"""Shared capability registry and recipe runner."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Type

from pydantic import BaseModel

from lacerta.core.jobs import JobResult, JobSpec

CapabilityHandler = Callable[["CapabilityContext", BaseModel], "CapabilityResult"]

_REGISTRY: dict[str, "CapabilitySpec"] = {}
_RECIPES: dict[str, "Recipe"] = {}


@dataclass
class CapabilityContext:
    client: Any = None
    task_id: str = ""
    surface: str = "learn"
    offline: bool = False
    user_request: str = ""
    attachments: list[str] = field(default_factory=list)
    attachment_text_chunks: list[str] = field(default_factory=list)
    journal_text: str = ""
    source_registry: Any = None
    instance_id: str = ""
    course_id: str = ""
    data_root: str = ""
    extra: dict[str, Any] = field(default_factory=dict)
    cancel_check: Callable[[], bool] | None = None


@dataclass
class CapabilityResult:
    ok: bool
    data: dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    error_code: str | None = None
    error_message: str | None = None

    @classmethod
    def success(cls, summary: str = "", **data: Any) -> CapabilityResult:
        return cls(ok=True, summary=summary, data=dict(data))

    @classmethod
    def failure(cls, code: str, message: str) -> CapabilityResult:
        return cls(
            ok=False,
            summary=message,
            error_code=code,
            error_message=message,
        )


@dataclass(frozen=True)
class CapabilitySpec:
    capability_id: str
    title: str
    description: str
    input_model: Type[BaseModel]
    handler: CapabilityHandler
    surfaces: frozenset[str] = frozenset({"learn"})


@dataclass(frozen=True)
class Recipe:
    recipe_id: str
    title: str
    description: str
    capability_ids: tuple[str, ...]


def register_capability(spec: CapabilitySpec) -> None:
    _REGISTRY[spec.capability_id] = spec


def get_capability(capability_id: str) -> CapabilitySpec | None:
    return _REGISTRY.get(capability_id)


def register_recipe(recipe: Recipe) -> None:
    _RECIPES[recipe.recipe_id] = recipe


def get_recipe(recipe_id: str) -> Recipe | None:
    return _RECIPES.get(recipe_id)


def run_capability(
    capability_id: str,
    ctx: CapabilityContext,
    arguments: dict[str, Any] | None = None,
) -> CapabilityResult:
    spec = get_capability(capability_id)
    if spec is None:
        return CapabilityResult.failure("unknown_capability", capability_id)
    try:
        validated = spec.input_model.model_validate(arguments or {})
    except Exception as exc:
        return CapabilityResult.failure("invalid_input", str(exc))
    try:
        return spec.handler(ctx, validated)
    except Exception as exc:
        return CapabilityResult.failure("runtime_error", str(exc))


def args_for(cap_id: str, job: JobSpec, ctx: CapabilityContext) -> dict[str, Any]:
    """Default arg mapping from JobSpec/context into capability inputs."""
    inputs = dict(job.inputs or {})
    base: dict[str, Any] = {}
    if cap_id.endswith("ingest_course_materials"):
        if inputs.get("topic") or job.objective:
            base["topic"] = inputs.get("topic") or job.objective
        if inputs.get("content"):
            base["content"] = inputs["content"]
    elif cap_id.endswith("ingest_offline"):
        if inputs.get("topic") or job.objective:
            base["topic"] = inputs.get("topic") or job.objective
    elif cap_id.endswith("synthesize_notes"):
        if inputs.get("topic") or job.objective:
            base["topic"] = inputs.get("topic") or job.objective
        if "use_llm" in inputs:
            base["use_llm"] = inputs["use_llm"]
    elif cap_id.endswith("write_syllabus"):
        if "proposed_syllabus" in inputs:
            base["content"] = inputs["proposed_syllabus"]
        elif "syllabus" in inputs:
            base["content"] = inputs["syllabus"]
        elif "nodes" in inputs:
            base["nodes"] = inputs["nodes"]
            if "title" in inputs:
                base["title"] = inputs["title"]
        # else empty → handler proposes from notes
    elif cap_id.endswith("gather_topic_sources") or cap_id.endswith("gather_web_sources"):
        gather = dict(inputs.get("gather") or {})
        base["topic"] = inputs.get("topic") or job.objective
        base["max_searches"] = gather.get("max_searches", 2)
        base["max_pages"] = gather.get("max_pages", 3)
    elif cap_id.endswith("generate_assessments"):
        for k in ("node_id", "target_tier", "questions_json", "passing_score"):
            if k in inputs:
                base[k] = inputs[k]
    elif cap_id.endswith("light_web_context"):
        base["user_input"] = str(inputs.get("user_input") or job.objective)
    elif cap_id.endswith("append_note"):
        if inputs.get("content"):
            base["content"] = inputs["content"]
    elif cap_id.endswith("finalize_deliverable"):
        if inputs.get("report_body"):
            base["report_body"] = inputs["report_body"]
        if "compile_if_missing" in inputs:
            base["compile_if_missing"] = inputs["compile_if_missing"]
        brief = inputs.get("brief") or {}
        if isinstance(brief, dict) and brief.get("target_document"):
            base["slug"] = brief["target_document"]
        if inputs.get("target_document"):
            base["slug"] = inputs["target_document"]
        if inputs.get("slug"):
            base["slug"] = inputs["slug"]
    elif cap_id.endswith("draft_sections"):
        for k in ("section_header", "section_body", "title"):
            if k in inputs:
                base[k] = inputs[k]
        brief = inputs.get("brief") or {}
        if isinstance(brief, dict) and brief.get("title") and "title" not in base:
            base["title"] = brief["title"]
    elif cap_id.endswith("init_document"):
        if inputs.get("title"):
            base["title"] = inputs["title"]
        brief = inputs.get("brief") or {}
        if isinstance(brief, dict) and brief.get("title") and "title" not in base:
            base["title"] = brief["title"]
    elif cap_id.endswith("ingest_sources"):
        if inputs.get("content"):
            base["content"] = inputs["content"]
    # Merge any per-capability args dict if present
    per = inputs.get("capability_args") or {}
    if isinstance(per, dict) and cap_id in per and isinstance(per[cap_id], dict):
        base.update(per[cap_id])
    return {k: v for k, v in base.items() if v is not None}


def run_recipe(
    recipe_id: str,
    ctx: CapabilityContext,
    job: JobSpec,
) -> JobResult:
    recipe = get_recipe(recipe_id)
    if recipe is None:
        return JobResult(
            job_id=job.job_id,
            ok=False,
            summary="",
            error=f"unknown recipe {recipe_id!r}",
        )
    artifacts: list[str] = []
    for cap_id in recipe.capability_ids:
        result = run_capability(cap_id, ctx, args_for(cap_id, job, ctx))
        if not result.ok:
            return JobResult(
                job_id=job.job_id,
                ok=False,
                summary=result.summary or "",
                error=result.error_message,
                metrics={"failed_capability": cap_id},
            )
        if path := result.data.get("path"):
            artifacts.append(str(path))
        for key in ("syllabus_path", "course_path", "notes_path", "report_path"):
            if p := result.data.get(key):
                artifacts.append(str(p))
    return JobResult(
        job_id=job.job_id,
        ok=True,
        summary="Recipe complete.",
        artifacts=artifacts,
        metrics={"recipe_id": recipe_id},
    )
