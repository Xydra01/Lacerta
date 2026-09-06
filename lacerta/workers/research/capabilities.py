"""Research capability handlers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from lacerta.core.capabilities import (
    CapabilityContext,
    CapabilityResult,
    CapabilitySpec,
    register_capability,
)
from lacerta.workers.research.sources import SourceRegistry


class EmptyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NoteInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str


class ReadNotesInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    max_chars: int | None = None
    tail: bool = True


class IngestOfflineInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    topic: str | None = None


class SynthesizeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    topic: str | None = None
    max_input_chars: int = 12000
    use_llm: bool = False


class CompileInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    max_chars: int = 24000


class FinalizeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    report_body: str | None = None
    compile_if_missing: bool = True


class GatherWebInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    topic: str
    max_searches: int = 2
    max_pages: int = 3


class LightWebInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_input: str


def _task_dir(ctx: CapabilityContext) -> Path:
    root = Path(ctx.data_root or ".")
    task_id = ctx.task_id or "task"
    path = root / "tasks" / task_id / "research"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _notes_file(ctx: CapabilityContext) -> Path:
    return _task_dir(ctx) / "notes.md"


def _report_file(ctx: CapabilityContext) -> Path:
    return _task_dir(ctx) / "report.md"


def append_note(ctx: CapabilityContext, inp: NoteInput) -> CapabilityResult:
    content = (inp.content or "").strip()
    if not content:
        return CapabilityResult.failure("empty_note", "empty note content")
    path = _notes_file(ctx)
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    if content in existing:
        return CapabilityResult.success("Note already present (dedup)", path=str(path))
    with path.open("a", encoding="utf-8") as f:
        if existing and not existing.endswith("\n"):
            f.write("\n")
        f.write(content.rstrip() + "\n\n")
    return CapabilityResult.success("Appended note", path=str(path), notes_path=str(path))


def read_notes(ctx: CapabilityContext, inp: ReadNotesInput) -> CapabilityResult:
    path = _notes_file(ctx)
    if not path.is_file():
        return CapabilityResult.failure("no_notes", "notes.md missing")
    text = path.read_text(encoding="utf-8", errors="replace")
    if inp.max_chars and len(text) > inp.max_chars:
        text = text[-inp.max_chars :] if inp.tail else text[: inp.max_chars]
    return CapabilityResult.success("Read notes", text=text, path=str(path))


def ingest_offline(ctx: CapabilityContext, inp: IngestOfflineInput) -> CapabilityResult:
    chunks: list[str] = []
    if inp.topic:
        chunks.append(f"# Topic\n{inp.topic}\n")
    if ctx.user_request:
        chunks.append(f"## Request\n{ctx.user_request}\n")
    if ctx.journal_text:
        chunks.append(ctx.journal_text)
    for c in ctx.attachment_text_chunks:
        chunks.append(c)
    for a in ctx.attachments:
        p = Path(a)
        if p.is_file():
            chunks.append(f"## Source: {p.name}\n{p.read_text(encoding='utf-8', errors='replace')}\n")
    text = "\n\n".join(x for x in chunks if x and str(x).strip())
    if not text.strip():
        return CapabilityResult.failure("empty_ingest", "No offline sources")
    return append_note(ctx, NoteInput(content=text))


def synthesize_notes(ctx: CapabilityContext, inp: SynthesizeInput) -> CapabilityResult:
    path = _notes_file(ctx)
    if not path.is_file():
        return CapabilityResult.failure("no_notes", "no notes to synthesize")
    raw = path.read_text(encoding="utf-8", errors="replace")
    if not raw.strip():
        return CapabilityResult.failure("no_notes", "notes empty")
    clipped = raw[: inp.max_input_chars]
    topic = inp.topic or ctx.user_request or "Research"
    # Deterministic synthesis (no LLM required for harness)
    lines = [ln.strip() for ln in clipped.splitlines() if ln.strip()]
    bullets = [f"- {ln[:200]}" for ln in lines[:40] if not ln.startswith("#")]
    body = f"## Synthesis: {topic}\n\n" + "\n".join(bullets[:25]) + "\n"
    return append_note(ctx, NoteInput(content=body))


def compile_report(ctx: CapabilityContext, inp: CompileInput) -> CapabilityResult:
    path = _notes_file(ctx)
    if not path.is_file():
        return CapabilityResult.failure("no_notes", "notes missing")
    body = path.read_text(encoding="utf-8", errors="replace")[: inp.max_chars]
    if len(body.strip()) < 200:
        return CapabilityResult.failure("short_notes", "notes too short to compile")
    registry: SourceRegistry = ctx.source_registry or SourceRegistry()
    bib = registry.format_bibliography_markdown()
    report = f"# Research Report\n\n{body.strip()}\n\n{bib}".strip() + "\n"
    return CapabilityResult.success("Compiled report", report_body=report)


def finalize_deliverable(ctx: CapabilityContext, inp: FinalizeInput) -> CapabilityResult:
    body = inp.report_body
    if not body and inp.compile_if_missing:
        compiled = compile_report(ctx, CompileInput())
        if not compiled.ok:
            return compiled
        body = str(compiled.data.get("report_body") or "")
    if not body or not str(body).strip():
        return CapabilityResult.failure("empty_report", "empty deliverable")
    path = _report_file(ctx)
    path.write_text(str(body).strip() + "\n", encoding="utf-8")
    return CapabilityResult.success(
        "Wrote report.md",
        path=str(path),
        report_path=str(path),
    )


def gather_web_sources(ctx: CapabilityContext, inp: GatherWebInput) -> CapabilityResult:
    del ctx, inp
    return CapabilityResult.failure("not_implemented", "research.gather_web_sources deferred")


def light_web_context(ctx: CapabilityContext, inp: LightWebInput) -> CapabilityResult:
    del ctx
    return CapabilityResult.success("light stub", context=f"(no web) {inp.user_input[:200]}")


def register_research_capabilities() -> None:
    for spec in (
        CapabilitySpec("research.append_note", "Append note", "", NoteInput, append_note, frozenset({"research", "learn"})),
        CapabilitySpec("research.read_notes", "Read notes", "", ReadNotesInput, read_notes, frozenset({"research"})),
        CapabilitySpec("research.ingest_offline", "Ingest offline", "", IngestOfflineInput, ingest_offline, frozenset({"research"})),
        CapabilitySpec("research.synthesize_notes", "Synthesize", "", SynthesizeInput, synthesize_notes, frozenset({"research"})),
        CapabilitySpec("research.compile_report", "Compile", "", CompileInput, compile_report, frozenset({"research"})),
        CapabilitySpec("research.finalize_deliverable", "Finalize", "", FinalizeInput, finalize_deliverable, frozenset({"research"})),
        CapabilitySpec("research.gather_web_sources", "Gather web", "", GatherWebInput, gather_web_sources, frozenset({"research"})),
        CapabilitySpec("research.light_web_context", "Light web", "", LightWebInput, light_web_context, frozenset({"research", "chat"})),
    ):
        register_capability(spec)


register_research_capabilities()
