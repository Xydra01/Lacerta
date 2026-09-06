"""Learn surface capability handlers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from lacerta.core.capabilities import (
    CapabilityContext,
    CapabilityResult,
    CapabilitySpec,
    register_capability,
)
from lacerta.workers.learn import storage
from lacerta.workers.learn.propose import propose_syllabus


class EmptyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class IngestInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    topic: str | None = None
    content: str | None = None


class WriteSyllabusInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str | None = None
    nodes: list[dict[str, Any]] | None = None
    title: str | None = None
    status: str | None = None


class GatherInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    topic: str
    max_searches: int = 2
    max_pages: int = 3


class GenerateAssessmentsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    node_id: str
    target_tier: int = Field(ge=1, le=5)
    questions_json: str = "[]"
    passing_score: int = 70


def _course_root(ctx: CapabilityContext) -> Path:
    data_root = ctx.data_root or ctx.extra.get("data_root") or "."
    return storage.ensure_course_dirs(data_root, ctx.instance_id or "default", ctx.course_id or "course")


def ingest_course_materials(ctx: CapabilityContext, inp: IngestInput) -> CapabilityResult:
    root = _course_root(ctx)
    chunks: list[str] = []
    if inp.topic:
        chunks.append(f"# Topic\n{inp.topic}\n")
    if inp.content:
        chunks.append(inp.content)
    if ctx.journal_text:
        chunks.append(ctx.journal_text)
    for c in ctx.attachment_text_chunks:
        chunks.append(c)
    for path in ctx.attachments:
        p = Path(path)
        if p.is_file():
            chunks.append(f"## Source: {p.name}\n{p.read_text(encoding='utf-8', errors='replace')}\n")
    text = "\n\n".join(x for x in chunks if x and str(x).strip())
    if not text.strip():
        return CapabilityResult.failure("empty_ingest", "No course materials to ingest")
    notes = storage.notes_path(root)
    notes.write_text(text, encoding="utf-8")
    course = storage.read_json(storage.course_json_path(root)) or {
        "course_id": ctx.course_id,
        "instance_id": ctx.instance_id,
        "build_complete": False,
    }
    course["status"] = "building"
    storage.write_json(storage.course_json_path(root), course)
    return CapabilityResult.success("Ingested course materials", notes_path=str(notes), path=str(notes))


def write_syllabus(ctx: CapabilityContext, inp: WriteSyllabusInput) -> CapabilityResult:
    root = _course_root(ctx)
    spath = storage.syllabus_path(root)
    existing = storage.read_json(spath)
    if existing and existing.get("status") in ("building", "active", "complete") and existing.get("nodes"):
        # One write per build — reject rewrite once nodes exist
        if ctx.extra.get("allow_syllabus_rewrite"):
            pass
        else:
            return CapabilityResult.failure(
                "syllabus_already_written",
                "syllabus.json already written for this build",
            )

    syllabus: dict[str, Any] | None = None
    if inp.nodes is not None:
        syllabus = {
            "status": inp.status or "building",
            "nodes": inp.nodes,
            "assessments": [],
            "title": inp.title,
        }
    elif inp.content:
        raw = inp.content
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                return CapabilityResult.failure("invalid_json", "content is not valid JSON")
            if isinstance(parsed, dict):
                syllabus = parsed
        elif isinstance(raw, dict):
            syllabus = raw
    if syllabus is None:
        notes = ""
        np = storage.notes_path(root)
        if np.is_file():
            notes = np.read_text(encoding="utf-8", errors="replace")
        topic = (ctx.extra.get("topic") or ctx.user_request or ctx.course_id or "Course")
        syllabus = propose_syllabus(topic=str(topic), notes=notes, client=ctx.client)

    failures = storage.validate_syllabus_structure(syllabus)
    if failures:
        return CapabilityResult.failure("shallow_syllabus", "; ".join(failures))

    syllabus["status"] = "building"
    storage.write_json(spath, syllabus)
    return CapabilityResult.success(
        "Wrote syllabus.json",
        syllabus_path=str(spath),
        path=str(spath),
        node_count=len(syllabus.get("nodes") or []),
    )


def finalize_course(ctx: CapabilityContext, inp: EmptyInput) -> CapabilityResult:
    del inp
    root = _course_root(ctx)
    spath = storage.syllabus_path(root)
    syllabus = storage.read_json(spath)
    if not syllabus:
        return CapabilityResult.failure("missing_syllabus", "syllabus.json missing")
    failures = storage.validate_syllabus_structure(syllabus)
    if failures:
        return CapabilityResult.failure("invalid_syllabus", "; ".join(failures))
    syllabus["status"] = "active"
    storage.write_json(spath, syllabus)
    course = storage.read_json(storage.course_json_path(root)) or {
        "course_id": ctx.course_id,
        "instance_id": ctx.instance_id,
    }
    course["build_complete"] = True
    course["status"] = "active"
    cpath = storage.course_json_path(root)
    storage.write_json(cpath, course)
    return CapabilityResult.success(
        "Course finalized",
        course_path=str(cpath),
        syllabus_path=str(spath),
        path=str(cpath),
    )


def gather_topic_sources(ctx: CapabilityContext, inp: GatherInput) -> CapabilityResult:
    del ctx, inp
    return CapabilityResult.failure("not_implemented", "learn.gather_topic_sources deferred (web path)")


def generate_assessments(ctx: CapabilityContext, inp: GenerateAssessmentsInput) -> CapabilityResult:
    del ctx, inp
    return CapabilityResult.failure("not_implemented", "learn.generate_assessments deferred")


def register_learn_capabilities() -> None:
    specs = [
        CapabilitySpec(
            capability_id="learn.ingest_course_materials",
            title="Ingest course materials",
            description="Compose topic + attachments into notes",
            input_model=IngestInput,
            handler=ingest_course_materials,
            surfaces=frozenset({"learn"}),
        ),
        CapabilitySpec(
            capability_id="learn.write_syllabus",
            title="Write syllabus",
            description="Validate and write syllabus.json once",
            input_model=WriteSyllabusInput,
            handler=write_syllabus,
            surfaces=frozenset({"learn"}),
        ),
        CapabilitySpec(
            capability_id="learn.finalize_course",
            title="Finalize course",
            description="Activate course after valid syllabus",
            input_model=EmptyInput,
            handler=finalize_course,
            surfaces=frozenset({"learn"}),
        ),
        CapabilitySpec(
            capability_id="learn.gather_topic_sources",
            title="Gather topic sources",
            description="Web gather (stub)",
            input_model=GatherInput,
            handler=gather_topic_sources,
            surfaces=frozenset({"learn"}),
        ),
        CapabilitySpec(
            capability_id="learn.generate_assessments",
            title="Generate assessments",
            description="Assessment writer (stub)",
            input_model=GenerateAssessmentsInput,
            handler=generate_assessments,
            surfaces=frozenset({"learn"}),
        ),
    ]
    for spec in specs:
        register_capability(spec)


register_learn_capabilities()
