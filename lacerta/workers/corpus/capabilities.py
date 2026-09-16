"""Corpus multi-pass capabilities (worker-side only)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from lacerta.core.capabilities import (
    CapabilityContext,
    CapabilityResult,
    CapabilitySpec,
    register_capability,
)
from lacerta.storage import corpus as corpus_storage


class CorpusRootInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    corpus_root: str | None = None


class RetrieveInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    corpus_root: str | None = None
    query: str = ""
    top_k: int = Field(default=corpus_storage.DEFAULT_TOP_K, ge=1, le=20)
    max_chars: int = Field(default=corpus_storage.DEFAULT_MAX_CHARS, ge=200, le=20000)


def _corpus_root(ctx: CapabilityContext, explicit: str | None = None) -> Path:
    if explicit:
        return Path(explicit)
    if ctx.extra.get("corpus_root"):
        return Path(str(ctx.extra["corpus_root"]))
    data_root = ctx.data_root or ctx.extra.get("data_root") or "."
    instance_id = ctx.instance_id or "default"
    course_id = ctx.course_id or "course"
    return corpus_storage.resolve_course_corpus_root(data_root, instance_id, course_id)


def _source_paths(ctx: CapabilityContext) -> list[Path]:
    paths: list[Path] = []
    for a in ctx.attachments:
        p = Path(a)
        if p.is_file():
            paths.append(p)
    for raw in ctx.extra.get("source_paths") or []:
        p = Path(str(raw))
        if p.is_file():
            paths.append(p)
    if not paths and ctx.data_root and ctx.course_id:
        from lacerta.workers.learn import storage as learn_storage

        notes = learn_storage.notes_path(
            learn_storage.course_dir(
                ctx.data_root, ctx.instance_id or "default", ctx.course_id
            )
        )
        if notes.is_file():
            paths.append(notes)
    return paths


def extract_sources(ctx: CapabilityContext, inp: CorpusRootInput) -> CapabilityResult:
    from lacerta.storage.extract import ExtractError, extract_text, normalized_source_name

    root = _corpus_root(ctx, inp.corpus_root)
    corpus_storage.ensure_corpus_layout(root)
    meta = corpus_storage.load_meta(root)
    meta["status"] = "indexing"
    meta["error"] = None
    if not meta.get("corpus_id"):
        meta["corpus_id"] = (
            f"{ctx.instance_id or 'default'}:{ctx.course_id or 'course'}"
        )
    corpus_storage.save_meta(root, meta)

    sources = _source_paths(ctx)
    if not sources:
        meta["status"] = "error"
        meta["error"] = "no_sources"
        corpus_storage.save_meta(root, meta)
        return CapabilityResult.failure(
            "no_sources",
            "No attachments or course notes to index "
            "(.md/.txt/.pdf/.docx/.html/.csv)",
        )

    fingerprints: dict[str, str] = {}
    copied: list[str] = []
    src_dir = corpus_storage.sources_dir(root)
    for old in list(src_dir.iterdir()):
        if old.is_file():
            old.unlink()

    used_names: set[str] = set()
    for src in sources:
        if not corpus_storage.is_supported_source(src):
            return CapabilityResult.failure(
                "unsupported_source",
                f"Unsupported source type {src.suffix!r} — use "
                f".md/.txt/.pdf/.docx/.html/.csv (legacy .doc not supported)",
            )
        try:
            text = extract_text(src)
        except ExtractError as e:
            meta["status"] = "error"
            meta["error"] = e.code
            corpus_storage.save_meta(root, meta)
            return CapabilityResult.failure(e.code, e.message)

        dest_name = normalized_source_name(src)
        if dest_name in used_names:
            dest_name = f"{src.stem}-{len(used_names)}.md"
        used_names.add(dest_name)
        dest = src_dir / dest_name
        header = f"# Source: {src.name}\n\n"
        dest.write_text(header + text + "\n", encoding="utf-8")
        fingerprints[dest.name] = corpus_storage.fingerprint_file(dest)
        copied.append(str(dest))

    meta["source_fingerprints"] = fingerprints
    meta["stale"] = False
    corpus_storage.save_meta(root, meta)
    return CapabilityResult.success(
        f"Extracted {len(copied)} source(s)",
        corpus_root=str(root),
        path=str(root),
        sources=copied,
    )


def _split_sections(text: str, source_name: str) -> list[dict[str, Any]]:
    lines = text.replace("\r\n", "\n").split("\n")
    sections: list[dict[str, Any]] = []
    current_heading = source_name
    buf: list[str] = []

    def flush() -> None:
        body = "\n".join(buf).strip()
        if body:
            sections.append({"heading": current_heading, "text": body})

    for line in lines:
        if re.match(r"^#{1,3}\s+", line):
            flush()
            buf = []
            current_heading = re.sub(r"^#{1,3}\s+", "", line).strip() or current_heading
        else:
            buf.append(line)
    flush()
    if not sections and text.strip():
        sections.append({"heading": source_name, "text": text.strip()})
    return sections


def _chunk_text(text: str, *, target: int = corpus_storage.CHUNK_TARGET_CHARS) -> list[str]:
    from lacerta.storage.extract_structured import prefer_marker_boundary

    text = text.strip()
    if not text:
        return []
    if len(text) <= target:
        return [text]
    parts: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + target)
        if end < len(text):
            window = text[start:end]
            br = max(window.rfind("\n\n"), window.rfind("\n"))
            if br > target // 3:
                end = start + br
            end = prefer_marker_boundary(text, start, end, target)
        parts.append(text[start:end].strip())
        start = end
    return [p for p in parts if p]


def chunk_sources(ctx: CapabilityContext, inp: CorpusRootInput) -> CapabilityResult:
    from lacerta.storage.extract_structured import infer_chunk_kind

    root = _corpus_root(ctx, inp.corpus_root)
    corpus_storage.ensure_corpus_layout(root)
    src_dir = corpus_storage.sources_dir(root)
    chunk_dir = corpus_storage.chunks_dir(root)
    for old in list(chunk_dir.iterdir()):
        if old.is_file():
            old.unlink()

    chunks: list[dict[str, Any]] = []
    idx = 0
    for src in sorted(src_dir.iterdir()):
        if not src.is_file() or not corpus_storage.is_normalized_source(src):
            continue
        text = src.read_text(encoding="utf-8", errors="replace")
        for section in _split_sections(text, src.stem):
            for piece in _chunk_text(section["text"]):
                idx += 1
                cid = f"c{idx:04d}"
                rec = {
                    "chunk_id": cid,
                    "source": src.name,
                    "heading": section["heading"],
                    "text": piece,
                    "kind": infer_chunk_kind(piece),
                }
                corpus_storage.write_json(chunk_dir / f"{cid}.json", rec)
                chunks.append(rec)

    if not chunks:
        return CapabilityResult.failure("no_chunks", "No chunks produced from sources")

    meta = corpus_storage.load_meta(root)
    meta["chunk_count"] = len(chunks)
    corpus_storage.save_meta(root, meta)
    return CapabilityResult.success(
        f"Wrote {len(chunks)} chunk(s)",
        corpus_root=str(root),
        path=str(chunk_dir),
        chunk_count=len(chunks),
    )


def map_corpus(ctx: CapabilityContext, inp: CorpusRootInput) -> CapabilityResult:
    root = _corpus_root(ctx, inp.corpus_root)
    chunk_dir = corpus_storage.chunks_dir(root)
    entries: list[dict[str, Any]] = []
    for path in sorted(chunk_dir.glob("c*.json")):
        rec = corpus_storage.read_json(path)
        if not rec:
            continue
        entry = {
            "chunk_id": rec.get("chunk_id"),
            "source": rec.get("source"),
            "heading": rec.get("heading"),
            "preview": str(rec.get("text") or "")[:120],
        }
        if rec.get("kind"):
            entry["kind"] = rec.get("kind")
        entries.append(entry)
    toc: dict[str, list[str]] = {}
    for e in entries:
        h = str(e.get("heading") or "Untitled")
        toc.setdefault(h, []).append(str(e.get("chunk_id")))
    payload = {
        "toc": [{"heading": k, "chunk_ids": v} for k, v in toc.items()],
        "entries": entries,
    }
    corpus_storage.write_json(corpus_storage.map_path(root), payload)
    return CapabilityResult.success(
        f"Mapped {len(entries)} chunk(s)",
        corpus_root=str(root),
        path=str(corpus_storage.map_path(root)),
    )


def embed_or_keyword(ctx: CapabilityContext, inp: CorpusRootInput) -> CapabilityResult:
    """Build keyword index; never download embedding models."""
    root = _corpus_root(ctx, inp.corpus_root)
    chunk_dir = corpus_storage.chunks_dir(root)
    posting: dict[str, list[str]] = {}
    chunk_count = 0
    for path in sorted(chunk_dir.glob("c*.json")):
        rec = corpus_storage.read_json(path)
        if not rec:
            continue
        chunk_count += 1
        cid = str(rec.get("chunk_id"))
        tokens = set(corpus_storage.tokenize(str(rec.get("text") or "")))
        tokens.update(corpus_storage.tokenize(str(rec.get("heading") or "")))
        for tok in tokens:
            posting.setdefault(tok, []).append(cid)

    corpus_storage.write_json(
        corpus_storage.keyword_index_path(root),
        {"posting": posting, "chunk_count": chunk_count},
    )
    meta = corpus_storage.load_meta(root)
    meta["index_backend"] = "keyword"
    meta["chunk_count"] = chunk_count
    meta["status"] = "complete"
    meta["stale"] = False
    meta["error"] = None
    fps: dict[str, str] = {}
    for src in corpus_storage.sources_dir(root).iterdir():
        if src.is_file() and corpus_storage.is_normalized_source(src):
            fps[src.name] = corpus_storage.fingerprint_file(src)
    meta["source_fingerprints"] = fps
    if not meta.get("corpus_id"):
        meta["corpus_id"] = f"{ctx.instance_id or 'default'}:{ctx.course_id or 'course'}"
    corpus_storage.save_meta(root, meta)
    return CapabilityResult.success(
        f"Keyword index complete ({chunk_count} chunks)",
        corpus_root=str(root),
        path=str(corpus_storage.keyword_index_path(root)),
        index_backend="keyword",
        chunk_count=chunk_count,
    )


def retrieve(ctx: CapabilityContext, inp: RetrieveInput) -> CapabilityResult:
    root = _corpus_root(ctx, inp.corpus_root)
    meta = corpus_storage.load_meta(root)
    if meta.get("status") != "complete":
        return CapabilityResult.failure(
            "corpus_not_ready",
            f"corpus status is {meta.get('status')!r}; index sources first",
        )
    query = (inp.query or ctx.user_request or "").strip()
    if not query:
        return CapabilityResult.failure("empty_query", "retrieve requires a query")

    index = corpus_storage.read_json(corpus_storage.keyword_index_path(root)) or {}
    posting: dict[str, list[str]] = dict(index.get("posting") or {})
    scores: dict[str, int] = {}
    for tok in corpus_storage.tokenize(query):
        for cid in posting.get(tok) or []:
            scores[cid] = scores.get(cid, 0) + 1

    ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
    if not ranked:
        for path in sorted(corpus_storage.chunks_dir(root).glob("c*.json"))[: inp.top_k]:
            rec = corpus_storage.read_json(path)
            if rec:
                ranked.append((str(rec.get("chunk_id")), 0))

    selected: list[dict[str, Any]] = []
    total_chars = 0
    for cid, score in ranked[: inp.top_k]:
        path = corpus_storage.chunks_dir(root) / f"{cid}.json"
        rec = corpus_storage.read_json(path)
        if not rec:
            continue
        text = str(rec.get("text") or "")
        if total_chars + len(text) > inp.max_chars and selected:
            break
        item: dict[str, Any] = {
            "chunk_id": cid,
            "score": score,
            "source": rec.get("source"),
            "heading": rec.get("heading"),
            "text": text,
        }
        if rec.get("kind"):
            item["kind"] = rec.get("kind")
        selected.append(item)
        total_chars += len(text)

    return CapabilityResult.success(
        f"Retrieved {len(selected)} chunk(s)",
        chunks=selected,
        citations=[
            {
                "chunk_id": c["chunk_id"],
                "source": c.get("source"),
                "heading": c.get("heading"),
            }
            for c in selected
        ],
        query=query,
        corpus_root=str(root),
    )


def register_corpus_capabilities() -> None:
    specs = [
        CapabilitySpec(
            capability_id="corpus.extract",
            title="Extract corpus sources",
            description="Copy text sources into corpus/sources",
            input_model=CorpusRootInput,
            handler=extract_sources,
            surfaces=frozenset({"learn", "research"}),
        ),
        CapabilitySpec(
            capability_id="corpus.chunk",
            title="Chunk corpus sources",
            description="Write stable chunk JSON under corpus/chunks",
            input_model=CorpusRootInput,
            handler=chunk_sources,
            surfaces=frozenset({"learn", "research"}),
        ),
        CapabilitySpec(
            capability_id="corpus.map",
            title="Map corpus TOC",
            description="Deterministic heading map",
            input_model=CorpusRootInput,
            handler=map_corpus,
            surfaces=frozenset({"learn", "research"}),
        ),
        CapabilitySpec(
            capability_id="corpus.embed",
            title="Index corpus (keyword)",
            description="Keyword backend; no embedding downloads",
            input_model=CorpusRootInput,
            handler=embed_or_keyword,
            surfaces=frozenset({"learn", "research"}),
        ),
        CapabilitySpec(
            capability_id="corpus.retrieve",
            title="Retrieve corpus chunks",
            description="Top-k keyword retrieve with Python caps",
            input_model=RetrieveInput,
            handler=retrieve,
            surfaces=frozenset({"learn", "research"}),
        ),
    ]
    for spec in specs:
        register_capability(spec)


register_corpus_capabilities()
