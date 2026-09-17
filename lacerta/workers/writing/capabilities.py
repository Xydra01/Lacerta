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


def _scratch_excerpt(draft: dict[str, Any], *, limit: int = 280) -> str:
    scratch = str(draft.get("scratch") or "").strip()
    if not scratch:
        return ""
    return " ".join(scratch.split())[:limit]


def _deterministic_sections(ctx: CapabilityContext, brief: WritingBrief) -> list[dict[str, str]]:
    topic = str(ctx.extra.get("topic") or ctx.user_request or brief.title or "Topic")
    data_root, task_id = _roots(ctx)
    draft = storage.load_draft(data_root, task_id) or {}
    excerpt = _scratch_excerpt(draft)
    p1 = (
        f"This short draft introduces {topic}. Local-first agents keep inference "
        f"and tools on the user's machine so acceptance can be judged against disk "
        f"artifacts rather than log theater. Privacy and latency both improve when "
        f"the filesystem remains the source of truth for edits."
    )
    if excerpt:
        p1 = f"{p1} Source excerpt: {excerpt}"
    p2 = (
        f"Lacerta's writing surface uses a Python recipe runner: draft sections into "
        f"a buffer, compile a single markdown title with section headings, then "
        f"finalize a deliverable. Advance rules such as single_draft are enforced in "
        f"code before the file is written, matching the Supervisor–Worker design. "
        f"When scope is from_sources, ingest runs first so scratch notes inform the draft. "
        f"Keep the deliverable long enough for harness honesty checks."
    )
    return [
        {"header": "Introduction", "body": p1},
        {"header": "Approach", "body": p2},
    ]


def _llm_sections(
    ctx: CapabilityContext,
    brief: WritingBrief,
    draft: dict[str, Any],
) -> list[dict[str, str]] | None:
    """Ask the model for sections. Returns None on failure so the caller can fall back."""
    if ctx.client is None:
        return None
    topic = str(ctx.extra.get("topic") or ctx.user_request or brief.title or "Topic")
    # Larger excerpt for LLM than the deterministic paste; still bounded for 8k ctx.
    sources = _scratch_excerpt(draft, limit=3500)
    user_bits = [
        f"Goal / topic: {topic}",
        f"Working title: {brief.title or draft.get('title') or 'Draft'}",
    ]
    if sources:
        user_bits.append(
            "Write a clear markdown draft grounded in these sources. "
            "Do not invent facts that are not supported by the sources.\n\n"
            f"SOURCES:\n{sources}"
        )
    else:
        user_bits.append("Write a clear short markdown draft for the goal above.")
    try:
        result = ctx.client.chat(
            [
                {
                    "role": "system",
                    "content": (
                        "You are Lacerta's writing worker. Return JSON only with "
                        "title and two or three sections (header + body). "
                        "Bodies are plain paragraphs, no markdown headings inside body. "
                        "When SOURCES are present, rewrite for technical depth, flow, "
                        "and grammar using those sources."
                    ),
                },
                {"role": "user", "content": "\n\n".join(user_bits)},
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
        if not isinstance(data, dict) or not data.get("sections"):
            return None
        sections = [
            {
                "header": storage.strip_heading_marks(str(s.get("header") or "Section")),
                "body": storage.strip_heading_marks(str(s.get("body") or "")),
            }
            for s in data["sections"]
            if isinstance(s, dict)
        ]
        if not sections:
            return None
        title = storage.strip_heading_marks(
            str(data.get("title") or draft.get("title") or brief.title or "Draft")
        )
        draft["title"] = title
        return sections
    except Exception:
        return None


def ingest_sources(ctx: CapabilityContext, inp: IngestInput) -> CapabilityResult:
    from lacerta.storage.extract import ExtractError, extract_text

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
        if not p.is_file():
            continue
        try:
            chunks.append(extract_text(p))
        except ExtractError as e:
            return CapabilityResult.failure(e.code, e.message)
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
    elif not draft.get("sections"):
        draft["title"] = storage.strip_heading_marks(
            brief.title or ctx.user_request or "Writing Draft"
        )
        use_llm = _writing_mode() == "llm" and ctx.client is not None
        sections: list[dict[str, str]] | None = None
        if use_llm:
            sections = _llm_sections(ctx, brief, draft)
        if not sections:
            sections = _deterministic_sections(ctx, brief)
        draft["sections"] = sections

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
