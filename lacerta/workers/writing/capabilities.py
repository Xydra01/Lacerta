"""Writing surface capability handlers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from lacerta.core.capabilities import (
    CapabilityContext,
    CapabilityResult,
    CapabilitySpec,
    register_capability,
)
from lacerta.workers.writing.brief import WritingBrief
from lacerta.workers.writing import storage


class EmptyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class IngestInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str | None = None


class InitInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = None


class DraftSectionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    section_header: str | None = None
    section_body: str | None = None
    title: str | None = None


class FinalizeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: str | None = None


def _roots(ctx: CapabilityContext) -> tuple[str, str]:
    data_root = ctx.data_root or ctx.extra.get("data_root") or "."
    task_id = ctx.task_id or "task"
    return str(data_root), str(task_id)


def _brief(ctx: CapabilityContext) -> WritingBrief:
    raw = dict(ctx.extra.get("brief") or {})
    if ctx.extra.get("title") and "title" not in raw:
        raw["title"] = ctx.extra["title"]
    return WritingBrief.model_validate(raw) if raw else WritingBrief(
        title=str(ctx.extra.get("title") or ctx.user_request or "Untitled")[:80]
    )


def _writing_mode() -> str:
    return os.getenv("LACERTA_WRITING_MODE", "deterministic").strip().lower() or "deterministic"


def _deterministic_sections(ctx: CapabilityContext, brief: WritingBrief) -> list[dict[str, str]]:
    topic = str(ctx.extra.get("topic") or ctx.user_request or brief.title or "Topic")
    p1 = (
        f"This short draft introduces {topic}. Local-first agents keep inference "
        f"and tools on the user's machine so acceptance can be judged against disk "
        f"artifacts rather than log theater. Privacy and latency both improve when "
        f"the filesystem remains the source of truth for edits."
    )
    p2 = (
        f"Lacerta's writing surface uses a Python recipe runner: draft sections into "
        f"a buffer, compile a single markdown title with section headings, then "
        f"finalize a deliverable. Advance rules such as single_draft are enforced in "
        f"code before the file is written, matching the Supervisor–Worker design."
    )
    return [
        {"header": "Introduction", "body": p1},
        {"header": "Approach", "body": p2},
    ]


def ingest_sources(ctx: CapabilityContext, inp: IngestInput) -> CapabilityResult:
    data_root, task_id = _roots(ctx)
    draft = storage.load_draft(data_root, task_id) or storage.default_draft(
        title=_brief(ctx).title
    )
    chunks: list[str] = []
    if inp.content:
        chunks.append(inp.content)
    for c in ctx.attachment_text_chunks:
        chunks.append(c)
    for a in ctx.attachments:
        p = Path(a)
        if p.is_file():
            chunks.append(p.read_text(encoding="utf-8", errors="replace"))
    text = "\n\n".join(x for x in chunks if x and str(x).strip())
    if not text.strip() and not draft.get("scratch"):
        return CapabilityResult.failure("empty_ingest", "No sources to ingest")
    if text.strip():
        scratch = str(draft.get("scratch") or "")
        draft["scratch"] = (scratch + "\n\n" + text).strip()
    path = storage.save_draft(data_root, task_id, draft)
    return CapabilityResult.success("Ingested sources", path=str(path))


def init_document(ctx: CapabilityContext, inp: InitInput) -> CapabilityResult:
    data_root, task_id = _roots(ctx)
    brief = _brief(ctx)
    title = (inp.title or brief.title or ctx.user_request or "Untitled").strip()
    draft = storage.default_draft(title=title[:120])
    path = storage.save_draft(data_root, task_id, draft)
    return CapabilityResult.success("Initialized draft", path=str(path), title=title)


def draft_sections(ctx: CapabilityContext, inp: DraftSectionInput) -> CapabilityResult:
    data_root, task_id = _roots(ctx)
    brief = _brief(ctx)
    draft = storage.load_draft(data_root, task_id)
    if draft is None:
        draft = storage.default_draft(title=inp.title or brief.title)
    if inp.title:
        draft["title"] = storage.strip_heading_marks(inp.title)

    if inp.section_header or inp.section_body:
        header = storage.strip_heading_marks(inp.section_header or "Section")
        body = storage.strip_heading_marks(inp.section_body or "")
        draft.setdefault("sections", []).append({"header": header, "body": body})
    elif _writing_mode() == "deterministic" or not ctx.client:
        if not draft.get("sections"):
            draft["title"] = storage.strip_heading_marks(
                brief.title or ctx.user_request or "Writing Draft"
            )
            draft["sections"] = _deterministic_sections(ctx, brief)
    else:
        # Optional LLM path: fall back to deterministic if anything fails
        try:
            result = ctx.client.chat(
                [
                    {
                        "role": "system",
                        "content": "Write two short markdown section bodies as JSON.",
                    },
                    {"role": "user", "content": ctx.user_request or brief.title},
                ],
                temperature=0.4,
                format={
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "sections": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "header": {"type": "string"},
                                    "body": {"type": "string"},
                                },
                            },
                        },
                    },
                },
            )
            import json

            raw = str(result.get("message", {}).get("content") or "")
            data = json.loads(raw)
            if isinstance(data, dict) and data.get("sections"):
                draft["title"] = storage.strip_heading_marks(
                    str(data.get("title") or draft.get("title") or "Draft")
                )
                draft["sections"] = [
                    {
                        "header": storage.strip_heading_marks(str(s.get("header") or "Section")),
                        "body": storage.strip_heading_marks(str(s.get("body") or "")),
                    }
                    for s in data["sections"]
                    if isinstance(s, dict)
                ]
            else:
                draft["sections"] = _deterministic_sections(ctx, brief)
        except Exception:
            draft["sections"] = _deterministic_sections(ctx, brief)

    path = storage.save_draft(data_root, task_id, draft)
    return CapabilityResult.success(
        "Drafted sections",
        path=str(path),
        section_count=len(draft.get("sections") or []),
    )


def read_outline(ctx: CapabilityContext, inp: EmptyInput) -> CapabilityResult:
    del inp
    data_root, task_id = _roots(ctx)
    draft = storage.load_draft(data_root, task_id)
    if not draft:
        return CapabilityResult.failure("no_draft", "active_draft.json missing")
    outline = [
        str(s.get("header") or "")
        for s in (draft.get("sections") or [])
        if isinstance(s, dict)
    ]
    return CapabilityResult.success("Outline", outline=outline, title=draft.get("title"))


def compile_document(ctx: CapabilityContext, inp: EmptyInput) -> CapabilityResult:
    del inp
    data_root, task_id = _roots(ctx)
    draft = storage.load_draft(data_root, task_id)
    if not draft:
        return CapabilityResult.failure("no_draft", "active_draft.json missing")
    md = storage.compile_markdown(draft)
    return CapabilityResult.success("Compiled", markdown=md)


def _advance_ok(brief: WritingBrief, draft: dict[str, Any]) -> str | None:
    """Return error message if advance_when not satisfied."""
    sections = draft.get("sections") or []
    chars = storage.section_body_chars(draft)
    if brief.advance_when == "manual":
        return None
    if brief.advance_when == "single_draft":
        if not sections or chars < 80:
            return "advance_when=single_draft requires at least one non-trivial section"
        return None
    if brief.advance_when == "scope_met":
        if brief.length_mode == "sections" and brief.target_sections:
            if len(sections) < int(brief.target_sections):
                return f"need ≥{brief.target_sections} sections"
        if brief.length_mode == "paragraphs" and brief.target_paragraphs:
            if len(sections) < int(brief.target_paragraphs):
                return f"need ≥{brief.target_paragraphs} sections/paragraphs"
        if chars < 80:
            return "scope_met requires substantial body text"
        return None
    return None


def finalize_deliverable(ctx: CapabilityContext, inp: FinalizeInput) -> CapabilityResult:
    data_root, task_id = _roots(ctx)
    brief = _brief(ctx)
    draft = storage.load_draft(data_root, task_id)
    if not draft:
        return CapabilityResult.failure("no_draft", "active_draft.json missing")
    err = _advance_ok(brief, draft)
    if err:
        return CapabilityResult.failure("advance_blocked", err)
    md = storage.compile_markdown(draft)
    if not any(ln.startswith("# ") and not ln.startswith("## ") for ln in md.splitlines()):
        return CapabilityResult.failure("missing_title", "compiled markdown missing # title")
    slug = inp.slug or brief.target_document or "short.md"
    out = storage.deliverable_path(data_root, task_id, slug)
    out.write_text(md, encoding="utf-8")
    # Clear buffer after success
    archive = storage.writing_dir(data_root, task_id) / "active_draft.archived.json"
    archive.write_text(
        storage.draft_path(data_root, task_id).read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    storage.draft_path(data_root, task_id).unlink(missing_ok=True)
    return CapabilityResult.success(
        "Finalized deliverable",
        path=str(out),
        report_path=str(out),
    )


def register_writing_capabilities() -> None:
    for spec in (
        CapabilitySpec(
            "writing.ingest_sources",
            "Ingest sources",
            "",
            IngestInput,
            ingest_sources,
            frozenset({"writing"}),
        ),
        CapabilitySpec(
            "writing.init_document",
            "Init document",
            "",
            InitInput,
            init_document,
            frozenset({"writing"}),
        ),
        CapabilitySpec(
            "writing.draft_sections",
            "Draft sections",
            "",
            DraftSectionInput,
            draft_sections,
            frozenset({"writing"}),
        ),
        CapabilitySpec(
            "writing.read_outline",
            "Read outline",
            "",
            EmptyInput,
            read_outline,
            frozenset({"writing"}),
        ),
        CapabilitySpec(
            "writing.compile_document",
            "Compile document",
            "",
            EmptyInput,
            compile_document,
            frozenset({"writing"}),
        ),
        CapabilitySpec(
            "writing.finalize_deliverable",
            "Finalize deliverable",
            "",
            FinalizeInput,
            finalize_deliverable,
            frozenset({"writing"}),
        ),
    ):
        register_capability(spec)


register_writing_capabilities()
