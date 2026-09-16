"""Learn surface capability handlers."""

from __future__ import annotations

import json
import time
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
    node_id: str | None = None
    target_tier: int = Field(default=2, ge=1, le=5)
    questions_json: str = "[]"
    passing_score: int = 70
    max_nodes: int = Field(default=5, ge=1, le=20)


class TutorTurnInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str | None = None
    node_id: str | None = None
    history_digest: str | None = None
    prior_turns: list[dict[str, Any]] | None = None


class ArchiveChatInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str | None = None


def _course_root(ctx: CapabilityContext) -> Path:
    data_root = ctx.data_root or ctx.extra.get("data_root") or "."
    instance_id = ctx.instance_id or "default"
    course_id = ctx.course_id or "course"
    storage.ensure_course_meta(data_root, instance_id, course_id)
    return storage.ensure_course_dirs(data_root, instance_id, course_id)


def ingest_course_materials(ctx: CapabilityContext, inp: IngestInput) -> CapabilityResult:
    from lacerta.storage.extract import ExtractError, extract_text

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
        if not p.is_file():
            continue
        try:
            body = extract_text(p)
        except ExtractError as e:
            return CapabilityResult.failure(e.code, e.message)
        chunks.append(f"## Source: {p.name}\n{body}\n")
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
    course.setdefault(
        "corpus_id",
        storage.default_corpus_id(ctx.instance_id or "default", ctx.course_id or "course"),
    )
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
        notes = storage.read_notes_bounded(root, max_chars=storage.NOTES_CHAR_CAP)
        topic = ctx.extra.get("topic") or ctx.user_request or ctx.course_id or "Course"
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
    storage.ensure_mastery(root, syllabus)
    course = storage.ensure_course_meta(
        ctx.data_root or ".",
        ctx.instance_id or "default",
        ctx.course_id or "course",
        extra={"build_complete": True, "status": "active"},
    )
    cpath = storage.course_json_path(root)
    storage.write_json(cpath, course)
    return CapabilityResult.success(
        "Course finalized",
        course_path=str(cpath),
        syllabus_path=str(spath),
        path=str(cpath),
        corpus_id=course.get("corpus_id"),
    )


def gather_topic_sources(ctx: CapabilityContext, inp: GatherInput) -> CapabilityResult:
    del ctx, inp
    return CapabilityResult.failure("not_implemented", "learn.gather_topic_sources deferred (web path)")


def _mastery_band_instruction(tier: int) -> str:
    t = storage.clamp_tier(tier)
    if t <= 1:
        return (
            "MASTERY_BAND_INTRO: learner mastery 0–1 — use intro/basics only; "
            "define terms; avoid advanced edge cases."
        )
    if t <= 3:
        return (
            "MASTERY_BAND_WORKING: learner mastery 2–3 — use working examples; "
            "moderate difficulty; skip pure beginner fluff."
        )
    if t == 4:
        return (
            "MASTERY_BAND_ADVANCED: learner mastery 4 — use advanced comparisons "
            "and edge cases; do not re-teach basics unless asked."
        )
    return (
        "MASTERY_BAND_MASTER: learner mastery 5 — assume section known; "
        "deepen only if asked; do not re-teach basics unless the user asks."
    )


def _deterministic_tutor_reply(
    *,
    question: str,
    nodes: list[dict[str, Any]],
    notes_excerpt: str,
    node_id: str | None,
    mastery_tier: int = 0,
) -> str:
    focus = None
    if node_id:
        focus = next((n for n in nodes if str(n.get("id")) == node_id), None)
    if focus is None and nodes:
        focus = nodes[0]
    title = str((focus or {}).get("title") or "this unit")
    nid = str((focus or {}).get("id") or "n/a")
    outline = ", ".join(
        str(n.get("title") or n.get("id")) for n in nodes[:6] if isinstance(n, dict)
    )
    note_line = notes_excerpt.strip().splitlines()[0] if notes_excerpt.strip() else "(no notes yet)"
    band = _mastery_band_instruction(mastery_tier)
    return (
        f"Tutor (deterministic): Focusing on «{title}» (`{nid}`). "
        f"Learner mastery: {storage.clamp_tier(mastery_tier)}/5.\n\n"
        f"{band}\n\n"
        f"Your question: {question}\n\n"
        f"Syllabus context (first units): {outline or '—'}.\n"
        f"Notes excerpt: {note_line}\n\n"
        f"Next step: restate the idea in your own words, then try one practice item "
        f"tied to «{title}». This turn uses syllabus.json + bounded notes "
        f"(index sources for corpus retrieve)."
    )


def _corpus_retrieve_paste(
    *,
    question: str,
    retrieved_bits: list[str],
    citations: list[dict[str, Any]],
) -> str:
    cite_line = "; ".join(
        f"{c.get('chunk_id')} ({c.get('source')})" for c in citations[:5]
    )
    body = "\n\n".join(retrieved_bits[:5])
    return (
        f"Tutor (corpus retrieve): {question}\n\n"
        f"{body}\n\n"
        f"Citations: {cite_line or '—'}"
    )


def _teach_from_sources(
    client: Any,
    *,
    question: str,
    source_block: str,
    syllabus_titles: str = "",
    history_digest: str = "",
    prior_turns: list[dict[str, str]] | None = None,
    system_prompt: str | None = None,
    mastery_tier: int = 0,
    focus_title: str = "",
) -> str | None:
    """Worker-local LLM teach/Q&A from bounded sources. Returns None on failure."""
    if client is None:
        return None
    hist_lines: list[str] = []
    if history_digest.strip():
        hist_lines.append(f"Compressed prior session:\n{history_digest.strip()[:1500]}")
    for t in prior_turns or []:
        q = str(t.get("question") or "").strip()
        a = str(t.get("reply") or "").strip()
        if q and a:
            hist_lines.append(f"Prior Q: {q[:300]}\nPrior A: {a[:500]}")
    history_block = "\n\n".join(hist_lines) if hist_lines else "(no prior turns)"
    titles = syllabus_titles.strip() or "(none)"
    tier = storage.clamp_tier(mastery_tier)
    title = focus_title.strip() or "this unit"
    band = _mastery_band_instruction(tier)
    sys = system_prompt or (
        "You are a concise course tutor. Teach using ONLY the provided source "
        "excerpts and session history. Do not invent facts or sources. "
        "Explain briefly, then invite one small next step. Reply in ≤150 words. "
        f"Learner mastery for «{title}»: {tier}/5 — match difficulty. {band}"
    )
    try:
        result = client.chat(
            [
                {"role": "system", "content": sys},
                {
                    "role": "user",
                    "content": (
                        f"Syllabus units: {titles}\n"
                        f"Learner mastery for «{title}»: {tier}/5\n"
                        f"{band}\n\n"
                        f"Sources:\n{source_block[:4000]}\n\n"
                        f"Session history:\n{history_block}\n\n"
                        f"Learner question: {question}\n"
                        "Teach from the sources above at the learner's mastery level."
                    ),
                },
            ],
            temperature=0.3,
        )
        content = str(result.get("message", {}).get("content") or "").strip()
        return content or None
    except Exception:
        return None


def tutor_turn(ctx: CapabilityContext, inp: TutorTurnInput) -> CapabilityResult:
    from lacerta.core.capabilities import run_capability
    from lacerta.storage import corpus as corpus_storage

    root = _course_root(ctx)
    question = (inp.question or ctx.user_request or "").strip()
    if not question:
        return CapabilityResult.failure("empty_question", "tutor turn requires a question/goal")

    syllabus = storage.read_json(storage.syllabus_path(root))
    if syllabus:
        storage.ensure_mastery(root, syllabus)
    nodes = (
        [n for n in (syllabus or {}).get("nodes") or [] if isinstance(n, dict)]
        if syllabus
        else []
    )
    titles = ", ".join(str(n.get("title") or "") for n in nodes[:8])
    focus = None
    if inp.node_id:
        focus = next((n for n in nodes if str(n.get("id")) == inp.node_id), None)
    if focus is None and nodes:
        focus = nodes[0]
    focus_id = str((focus or {}).get("id") or inp.node_id or "") or None
    focus_title = str((focus or {}).get("title") or "this unit")
    mastery_tier = storage.get_node_tier(root, focus_id)

    if inp.history_digest is not None or inp.prior_turns is not None:
        digest = str(inp.history_digest or "")
        prior_raw = list(inp.prior_turns or [])
        prior_turns: list[dict[str, str]] = []
        for t in prior_raw:
            if not isinstance(t, dict):
                continue
            q = str(t.get("question") or "").strip()
            a = str(t.get("reply") or "").strip()
            if q and a:
                prior_turns.append({"question": q, "reply": a})
    else:
        digest, prior_turns = storage.load_tutor_context(root)

    croot = storage.corpus_dir(root)
    meta = corpus_storage.load_meta(croot) if croot.is_dir() else {}
    grounding = "syllabus+bounded_notes"
    citations: list[dict[str, Any]] = []
    retrieved_bits: list[str] = []

    if meta.get("status") == "complete":
        ret = run_capability(
            "corpus.retrieve",
            ctx,
            {"query": question, "corpus_root": str(croot)},
        )
        if ret.ok:
            grounding = "corpus_retrieve"
            citations = list(ret.data.get("citations") or [])
            for ch in ret.data.get("chunks") or []:
                cid = ch.get("chunk_id")
                src = ch.get("source")
                text = str(ch.get("text") or "")
                retrieved_bits.append(f"[{cid} | {src}] {text}")

    notes = storage.read_notes_bounded(root, max_chars=storage.TUTOR_NOTES_CHAR_CAP)
    if grounding == "corpus_retrieve" and retrieved_bits:
        source_block = "\n\n".join(retrieved_bits[:5])
        taught = _teach_from_sources(
            ctx.client,
            question=question,
            source_block=source_block,
            syllabus_titles=titles,
            history_digest=digest,
            prior_turns=prior_turns,
            mastery_tier=mastery_tier,
            focus_title=focus_title,
        )
        if taught:
            reply = taught
            grounding = "corpus_teach"
        else:
            reply = _corpus_retrieve_paste(
                question=question,
                retrieved_bits=retrieved_bits,
                citations=citations,
            )
    elif nodes:
        reply = _deterministic_tutor_reply(
            question=question,
            nodes=nodes,
            notes_excerpt=notes,
            node_id=focus_id,
            mastery_tier=mastery_tier,
        )
        taught = _teach_from_sources(
            ctx.client,
            question=question,
            source_block=f"Notes excerpt:\n{notes[:1500]}",
            syllabus_titles=titles,
            history_digest=digest,
            prior_turns=prior_turns,
            mastery_tier=mastery_tier,
            focus_title=focus_title,
            system_prompt=(
                "You are a concise course tutor. Use only the provided "
                "syllabus titles and notes excerpt. Do not invent sources. "
                f"Learner mastery for «{focus_title}»: {mastery_tier}/5 — match difficulty. "
                f"{_mastery_band_instruction(mastery_tier)} "
                "Reply in ≤120 words."
            ),
        )
        if taught:
            reply = taught
            grounding = "syllabus_teach"
    else:
        return CapabilityResult.failure(
            "missing_context",
            "Need an active syllabus or a complete corpus index before tutoring",
        )

    ts = int(time.time())
    turn = {
        "ts": ts,
        "question": question,
        "node_id": focus_id,
        "mastery_tier": mastery_tier,
        "reply": reply,
        "grounding": grounding,
        "citations": citations,
    }
    out_path = storage.tutor_dir(root) / f"turn_{ts}.json"
    storage.write_json(out_path, turn)
    history_path = storage.tutor_history_path(root)
    history = storage.read_json(history_path) or {"turns": []}
    turns = list(history.get("turns") or [])
    turns.append({"ts": ts, "path": str(out_path), "question": question[:120]})
    history["turns"] = turns[-storage.TUTOR_HISTORY_INDEX_MAX :]
    storage.write_json(history_path, history)

    new_digest = storage.compress_tutor_history(
        digest,
        question,
        reply,
        max_chars=storage.TUTOR_DIGEST_MAX_CHARS,
    )
    storage.save_tutor_digest(root, new_digest)

    return CapabilityResult.success(
        "Tutor turn written",
        path=str(out_path),
        tutor_path=str(out_path),
        history_path=str(history_path),
        digest_path=str(storage.tutor_digest_path(root)),
        grounding=grounding,
        citations=citations,
    )


HIGH_TIER_MARKER = "MASTERY_5_EDGE_CASE"
MAX_QUESTIONS_PER_NODE = 4


def _assessment_prompts_for_tier(nid: str, title: str, target_tier: int) -> list[dict[str, Any]]:
    tier = storage.clamp_tier(target_tier)
    if tier <= 1:
        return [
            {
                "id": f"q-{nid}-1",
                "prompt": f"Define or identify: {title}",
                "type": "short_answer",
            },
            {
                "id": f"q-{nid}-2",
                "prompt": f"In one simple sentence, what is {title}?",
                "type": "short_answer",
            },
        ][:MAX_QUESTIONS_PER_NODE]
    if tier <= 3:
        return [
            {
                "id": f"q-{nid}-1",
                "prompt": f"In one sentence, explain: {title}",
                "type": "short_answer",
            },
            {
                "id": f"q-{nid}-2",
                "prompt": f"Give one working example related to {title}",
                "type": "short_answer",
            },
        ][:MAX_QUESTIONS_PER_NODE]
    # tier 4–5
    return [
        {
            "id": f"q-{nid}-1",
            "prompt": f"{HIGH_TIER_MARKER}: compare edge cases for {title}",
            "type": "short_answer",
        },
        {
            "id": f"q-{nid}-2",
            "prompt": f"{HIGH_TIER_MARKER}: critique a subtle mistake about {title}",
            "type": "short_answer",
        },
    ][:MAX_QUESTIONS_PER_NODE]


def generate_assessments(ctx: CapabilityContext, inp: GenerateAssessmentsInput) -> CapabilityResult:
    root = _course_root(ctx)
    syllabus = storage.read_json(storage.syllabus_path(root))
    if not syllabus or not isinstance(syllabus.get("nodes"), list):
        return CapabilityResult.failure(
            "missing_syllabus",
            "syllabus.json missing — run Build syllabus first",
        )
    storage.ensure_mastery(root, syllabus)
    nodes = [n for n in syllabus["nodes"] if isinstance(n, dict)]
    if not nodes:
        return CapabilityResult.failure("empty_syllabus", "syllabus has no nodes")

    selected: list[dict[str, Any]]
    if inp.node_id:
        selected = [n for n in nodes if str(n.get("id")) == inp.node_id]
        if not selected:
            return CapabilityResult.failure("unknown_node", f"node_id {inp.node_id!r} not in syllabus")
    else:
        # Prefer child nodes (sub-units); fall back to first N nodes.
        children = [n for n in nodes if n.get("parent_id")]
        pool = children or nodes
        selected = pool[: inp.max_nodes]

    custom_questions: list[Any] = []
    if inp.questions_json and inp.questions_json.strip() not in ("", "[]"):
        try:
            parsed = json.loads(inp.questions_json)
            if isinstance(parsed, list):
                custom_questions = parsed[:MAX_QUESTIONS_PER_NODE]
        except json.JSONDecodeError:
            return CapabilityResult.failure("invalid_questions_json", "questions_json must be JSON array")

    assessments: list[dict[str, Any]] = []
    for node in selected:
        nid = str(node.get("id") or "node")
        title = str(node.get("title") or nid)
        if inp.node_id:
            target_tier = storage.get_node_tier(root, nid)
        else:
            target_tier = storage.clamp_tier(inp.target_tier)
        # Explicit job override (tests / tooling)
        if ctx.extra.get("target_tier") is not None:
            target_tier = storage.clamp_tier(ctx.extra.get("target_tier"))
        questions = (
            list(custom_questions)
            if custom_questions
            else _assessment_prompts_for_tier(nid, title, target_tier)
        )
        assessments.append(
            {
                "assessment_id": f"asm-{nid}",
                "node_id": nid,
                "title": f"Check: {title}",
                "target_tier": target_tier,
                "passing_score": inp.passing_score,
                "questions": questions[:MAX_QUESTIONS_PER_NODE],
            }
        )

    if not assessments:
        return CapabilityResult.failure("no_assessments", "no assessments generated")

    payload = {
        "course_id": ctx.course_id,
        "status": "ready",
        "assessments": assessments,
    }
    out_path = storage.assessments_dir(root) / "assessments.json"
    storage.write_json(out_path, payload)

    # Mirror ids onto syllabus for discoverability (disk SoT remains assessments.json).
    syllabus_asm = list(syllabus.get("assessments") or [])
    for a in assessments:
        syllabus_asm.append({"assessment_id": a["assessment_id"], "node_id": a["node_id"]})
    syllabus["assessments"] = syllabus_asm
    storage.write_json(storage.syllabus_path(root), syllabus)

    return CapabilityResult.success(
        f"Wrote {len(assessments)} assessment(s)",
        path=str(out_path),
        assessments_path=str(out_path),
        count=len(assessments),
    )


class MasteryCheckInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    node_id: str
    questions_count: int = Field(default=3, ge=2, le=4)


def _deterministic_mc_questions(
    *,
    nid: str,
    title: str,
    check_tier: int,
    count: int,
) -> list[dict[str, Any]]:
    tier = storage.clamp_tier(check_tier)
    band = "intro" if tier <= 1 else "working" if tier <= 3 else "advanced"
    questions: list[dict[str, Any]] = []
    stems = [
        f"Which best describes {title} at a {band} level?",
        f"What is a correct statement about {title}?",
        f"Which option matches {title} for mastery check tier {tier}?",
        f"Pick the accurate claim regarding {title}.",
    ]
    for i in range(min(count, MAX_QUESTIONS_PER_NODE)):
        correct = f"Correct: {title} ({band})"
        choices = [
            correct,
            f"Unrelated distractor A for {title}",
            f"Unrelated distractor B for {title}",
            f"Unrelated distractor C for {title}",
        ]
        if tier >= 4:
            stems[i] = f"{HIGH_TIER_MARKER}: which edge-case claim about {title} is right?"
        questions.append(
            {
                "id": f"mc-{nid}-{i + 1}",
                "prompt": stems[i],
                "choices": choices,
                "correct_index": 0,
                "node_id": nid,
                "target_tier": tier,
            }
        )
    return questions


def generate_mastery_check(ctx: CapabilityContext, inp: MasteryCheckInput) -> CapabilityResult:
    root = _course_root(ctx)
    syllabus = storage.read_json(storage.syllabus_path(root))
    if not syllabus or not isinstance(syllabus.get("nodes"), list):
        return CapabilityResult.failure(
            "missing_syllabus",
            "syllabus.json missing — run Build syllabus first",
        )
    storage.ensure_mastery(root, syllabus)
    nid = (inp.node_id or "").strip()
    if not nid:
        return CapabilityResult.failure("missing_node", "mastery check requires node_id")
    node = next((n for n in syllabus["nodes"] if isinstance(n, dict) and str(n.get("id")) == nid), None)
    if node is None:
        return CapabilityResult.failure("unknown_node", f"node_id {nid!r} not in syllabus")
    title = str(node.get("title") or nid)
    current = storage.get_node_tier(root, nid)
    check_tier = min(5, current + 1) if current < 5 else 5
    questions = _deterministic_mc_questions(
        nid=nid,
        title=title,
        check_tier=check_tier,
        count=inp.questions_count,
    )
    payload = {
        "course_id": ctx.course_id,
        "node_id": nid,
        "title": title,
        "current_tier": current,
        "target_tier": check_tier,
        "status": "ready",
        "questions": questions,
        "passing_ratio": 0.7,
    }
    out_path = storage.mastery_check_path(root, nid)
    storage.write_json(out_path, payload)
    return CapabilityResult.success(
        f"Mastery check for {nid} (tier {current}→{check_tier})",
        path=str(out_path),
        mastery_check_path=str(out_path),
        node_id=nid,
        current_tier=current,
        target_tier=check_tier,
        question_count=len(questions),
    )


def grade_mastery_check(
    course_root: Path,
    node_id: str,
    answers: list[dict[str, Any]],
) -> dict[str, Any]:
    """Python grade mastery check. On pass, increment tier (cap 5); on fail, leave tier."""
    import math

    nid = (node_id or "").strip()
    path = storage.mastery_check_path(course_root, nid)
    doc = storage.read_json(path)
    if not doc:
        return {"ok": False, "error": "mastery check not found — generate one first"}
    questions = list(doc.get("questions") or [])
    if not questions:
        return {"ok": False, "error": "mastery check has no questions"}
    by_id = {str(q.get("id")): q for q in questions if isinstance(q, dict)}
    correct = 0
    for ans in answers:
        if not isinstance(ans, dict):
            continue
        qid = str(ans.get("question_id") or "")
        q = by_id.get(qid)
        if not q:
            continue
        try:
            selected = int(ans.get("selected_index"))
        except (TypeError, ValueError):
            continue
        if selected == int(q.get("correct_index", -1)):
            correct += 1
    n = len(questions)
    need = max(1, math.ceil(0.7 * n))
    passed = correct >= need
    current = storage.get_node_tier(course_root, nid)
    new_tier = current
    if passed and current < 5:
        new_tier = storage.set_node_tier(course_root, nid, current + 1)
    elif passed and current >= 5:
        new_tier = 5
    return {
        "ok": True,
        "score": correct,
        "total": n,
        "need": need,
        "passed": passed,
        "tier": new_tier,
        "previous_tier": current,
        "node_id": nid,
    }


PRACTICE_RETRIEVE_TOP_K = 4
PRACTICE_RETRIEVE_MAX_CHARS = 2400
_STRUCTURED_MARKERS = ("[table]", "[math]", "[figure]")


class PracticeQuizInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    node_id: str
    questions_count: int = Field(default=3, ge=2, le=4)


class PracticeNodeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    node_id: str


def _chunk_has_structured(chunk: dict[str, Any]) -> bool:
    kind = str(chunk.get("kind") or "")
    if kind in ("table", "math", "figure"):
        return True
    text = str(chunk.get("text") or "")
    return any(m in text for m in _STRUCTURED_MARKERS)


def _prefer_structured(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(chunks, key=lambda c: (0 if _chunk_has_structured(c) else 1))


def _retrieve_for_node(
    ctx: CapabilityContext, root: Path, title: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    from lacerta.core.capabilities import run_capability
    from lacerta.storage import corpus as corpus_storage

    croot = storage.corpus_dir(root)
    meta = corpus_storage.load_meta(croot) if croot.is_dir() else {}
    if meta.get("status") != "complete":
        return [], []
    ret = run_capability(
        "corpus.retrieve",
        ctx,
        {
            "query": title,
            "corpus_root": str(croot),
            "top_k": PRACTICE_RETRIEVE_TOP_K,
            "max_chars": PRACTICE_RETRIEVE_MAX_CHARS,
        },
    )
    if not ret.ok:
        return [], []
    chunks = _prefer_structured(list(ret.data.get("chunks") or []))
    citations = list(ret.data.get("citations") or [])
    return chunks, citations


def _grounded_deterministic_questions(
    *,
    nid: str,
    title: str,
    target_tier: int,
    count: int,
    chunks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    questions = _deterministic_mc_questions(
        nid=nid, title=title, check_tier=target_tier, count=count
    )
    # Prefer grounding first question from structured / first retrieved snippet
    grounded = next((c for c in chunks if _chunk_has_structured(c)), None)
    if grounded is None and chunks:
        grounded = chunks[0]
    if grounded and questions:
        snippet = str(grounded.get("text") or "").strip()
        # Keep stem bounded; never invent tokens beyond retrieve
        short = snippet[:280].replace("\n", " ")
        if short:
            questions[0] = {
                **questions[0],
                "id": f"mc-{nid}-g1",
                "prompt": f"Based on course sources about {title}, which claim fits?",
                "choices": [
                    short[:120] if len(short) > 20 else f"From sources: {title}",
                    f"Unrelated distractor A for {title}",
                    f"Unrelated distractor B for {title}",
                    f"Unrelated distractor C for {title}",
                ],
                "correct_index": 0,
                "citations": [
                    {
                        "chunk_id": grounded.get("chunk_id"),
                        "source": grounded.get("source"),
                        "heading": grounded.get("heading"),
                    }
                ],
            }
    return questions


def _try_llm_quiz(
    ctx: CapabilityContext,
    *,
    nid: str,
    title: str,
    target_tier: int,
    count: int,
    chunks: list[dict[str, Any]],
) -> list[dict[str, Any]] | None:
    if ctx.client is None:
        return None
    sources = "\n\n".join(
        f"[{c.get('chunk_id')}] {c.get('text')}" for c in chunks[:4]
    ) or f"(no corpus chunks; use title only: {title})"
    system = (
        "Generate a multiple-choice quiz as JSON only. Schema: "
        '{"questions":[{"id":"q1","prompt":"...","choices":["a","b","c","d"],'
        '"correct_index":0}]}. Use only facts present in SOURCES. '
        "Never invent table numbers or math tokens not in SOURCES. "
        f"Exactly {count} questions. Difficulty band for mastery tier {target_tier}."
    )
    user = f"Topic: {title}\nNode: {nid}\n\nSOURCES:\n{sources}"
    try:
        raw = ctx.client.chat(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ]
        )
        content = ""
        if isinstance(raw, dict):
            content = str((raw.get("message") or {}).get("content") or raw.get("content") or "")
        else:
            content = str(raw)
        start = content.find("{")
        end = content.rfind("}")
        if start < 0 or end <= start:
            return None
        parsed = json.loads(content[start : end + 1])
        questions = parsed.get("questions") if isinstance(parsed, dict) else None
        if not isinstance(questions, list):
            return None
        out: list[dict[str, Any]] = []
        for i, q in enumerate(questions[:count]):
            if not isinstance(q, dict):
                return None
            choices = q.get("choices")
            if not isinstance(choices, list) or len(choices) < 2:
                return None
            try:
                ci = int(q.get("correct_index"))
            except (TypeError, ValueError):
                return None
            if ci < 0 or ci >= len(choices):
                return None
            out.append(
                {
                    "id": str(q.get("id") or f"mc-{nid}-{i + 1}"),
                    "prompt": str(q.get("prompt") or "").strip(),
                    "choices": [str(c) for c in choices],
                    "correct_index": ci,
                    "node_id": nid,
                    "target_tier": target_tier,
                }
            )
            if not out[-1]["prompt"]:
                return None
        return out if len(out) >= 2 else None
    except Exception:
        return None


def generate_practice_quiz(ctx: CapabilityContext, inp: PracticeQuizInput) -> CapabilityResult:
    root = _course_root(ctx)
    syllabus = storage.read_json(storage.syllabus_path(root))
    if not syllabus or not isinstance(syllabus.get("nodes"), list):
        return CapabilityResult.failure(
            "missing_syllabus",
            "syllabus.json missing — run Build syllabus first",
        )
    storage.ensure_mastery(root, syllabus)
    nid = (inp.node_id or ctx.extra.get("node_id") or "").strip()
    if not nid:
        return CapabilityResult.failure("missing_node", "practice quiz requires node_id")
    node = next(
        (n for n in syllabus["nodes"] if isinstance(n, dict) and str(n.get("id")) == nid),
        None,
    )
    if node is None:
        return CapabilityResult.failure("unknown_node", f"node_id {nid!r} not in syllabus")
    title = str(node.get("title") or nid)
    current = storage.get_node_tier(root, nid)
    target_tier = current if current > 0 else 1
    chunks, citations = _retrieve_for_node(ctx, root, title)
    questions = _try_llm_quiz(
        ctx,
        nid=nid,
        title=title,
        target_tier=target_tier,
        count=inp.questions_count,
        chunks=chunks,
    )
    grounding = "llm_quiz" if questions else "deterministic_quiz"
    if not questions:
        questions = _grounded_deterministic_questions(
            nid=nid,
            title=title,
            target_tier=target_tier,
            count=inp.questions_count,
            chunks=chunks,
        )
    payload = {
        "course_id": ctx.course_id,
        "node_id": nid,
        "title": title,
        "current_tier": current,
        "target_tier": target_tier,
        "status": "ready",
        "questions": questions,
        "passing_ratio": 0.7,
        "citations": citations[:8],
        "grounding": grounding,
    }
    err = storage.validate_quiz_payload(payload)
    if err:
        return CapabilityResult.failure("invalid_quiz", err)
    out_path = storage.quiz_path(root, nid)
    storage.write_json(out_path, payload)
    return CapabilityResult.success(
        f"Practice quiz for {nid} ({len(questions)} questions)",
        path=str(out_path),
        quiz_path=str(out_path),
        node_id=nid,
        current_tier=current,
        target_tier=target_tier,
        question_count=len(questions),
        grounding=grounding,
    )


def grade_practice_quiz(
    course_root: Path,
    node_id: str,
    answers: list[dict[str, Any]],
) -> dict[str, Any]:
    """Python grade practice quiz. Writes attempt record; does not bump mastery."""
    import math
    import time

    nid = (node_id or "").strip()
    path = storage.quiz_path(course_root, nid)
    doc = storage.read_json(path)
    if not doc:
        return {"ok": False, "error": "practice quiz not found — generate one first"}
    err = storage.validate_quiz_payload(doc)
    if err:
        return {"ok": False, "error": err}
    questions = list(doc.get("questions") or [])
    by_id = {str(q.get("id")): q for q in questions if isinstance(q, dict)}
    correct = 0
    detail: list[dict[str, Any]] = []
    for ans in answers:
        if not isinstance(ans, dict):
            continue
        qid = str(ans.get("question_id") or "")
        q = by_id.get(qid)
        if not q:
            continue
        try:
            selected = int(ans.get("selected_index"))
        except (TypeError, ValueError):
            continue
        ok = selected == int(q.get("correct_index", -1))
        if ok:
            correct += 1
        detail.append({"question_id": qid, "selected_index": selected, "correct": ok})
    n = len(questions)
    need = max(1, math.ceil(0.7 * n))
    passed = correct >= need
    ratio = (correct / n) if n else 0.0
    ts = int(time.time())
    attempt = {
        "ts": ts,
        "node_id": nid,
        "score": correct,
        "total": n,
        "need": need,
        "passed": passed,
        "ratio": ratio,
        "answers": detail,
        "quiz_path": str(path),
    }
    apath = storage.attempt_path(course_root, nid, ts)
    storage.write_json(apath, attempt)
    return {
        "ok": True,
        "score": correct,
        "total": n,
        "need": need,
        "passed": passed,
        "ratio": ratio,
        "node_id": nid,
        "attempt_path": str(apath),
    }


def generate_flashcards(ctx: CapabilityContext, inp: PracticeNodeInput) -> CapabilityResult:
    root = _course_root(ctx)
    syllabus = storage.read_json(storage.syllabus_path(root))
    if not syllabus or not isinstance(syllabus.get("nodes"), list):
        return CapabilityResult.failure(
            "missing_syllabus",
            "syllabus.json missing — run Build syllabus first",
        )
    nid = (inp.node_id or "").strip()
    if not nid:
        return CapabilityResult.failure("missing_node", "flashcards require node_id")
    node = next(
        (n for n in syllabus["nodes"] if isinstance(n, dict) and str(n.get("id")) == nid),
        None,
    )
    if node is None:
        return CapabilityResult.failure("unknown_node", f"node_id {nid!r} not in syllabus")
    title = str(node.get("title") or nid)
    chunks, _ = _retrieve_for_node(ctx, root, title)
    cards: list[dict[str, str]] = [
        {"front": title, "back": f"Syllabus topic: {title}"},
    ]
    for c in chunks[:6]:
        text = str(c.get("text") or "").strip()
        if not text:
            continue
        heading = str(c.get("heading") or c.get("source") or "Source")
        cards.append(
            {
                "front": heading[:120],
                "back": text[:500],
            }
        )
    if len(cards) < 2:
        cards.append(
            {
                "front": f"Key idea: {title}",
                "back": f"Review the materials for {title}.",
            }
        )
    payload = {
        "course_id": ctx.course_id,
        "node_id": nid,
        "title": title,
        "cards": cards,
    }
    out_path = storage.flashcards_path(root, nid)
    storage.write_json(out_path, payload)
    return CapabilityResult.success(
        f"Flashcards for {nid} ({len(cards)} cards)",
        path=str(out_path),
        flashcards_path=str(out_path),
        node_id=nid,
        card_count=len(cards),
    )


def generate_study_guide(ctx: CapabilityContext, inp: PracticeNodeInput) -> CapabilityResult:
    root = _course_root(ctx)
    syllabus = storage.read_json(storage.syllabus_path(root))
    if not syllabus or not isinstance(syllabus.get("nodes"), list):
        return CapabilityResult.failure(
            "missing_syllabus",
            "syllabus.json missing — run Build syllabus first",
        )
    nid = (inp.node_id or "").strip()
    if not nid:
        return CapabilityResult.failure("missing_node", "study guide requires node_id")
    node = next(
        (n for n in syllabus["nodes"] if isinstance(n, dict) and str(n.get("id")) == nid),
        None,
    )
    if node is None:
        return CapabilityResult.failure("unknown_node", f"node_id {nid!r} not in syllabus")
    title = str(node.get("title") or nid)
    tier = storage.get_node_tier(root, nid)
    chunks, citations = _retrieve_for_node(ctx, root, title)
    lines = [
        f"# Study guide: {title}",
        "",
        f"Node: `{nid}` · mastery {tier}/5",
        "",
        "## Overview",
        "",
        f"Focus this session on **{title}**.",
        "",
    ]
    if chunks:
        lines.extend(["## Sources", ""])
        for c in chunks:
            text = str(c.get("text") or "").strip()
            if not text:
                continue
            cid = c.get("chunk_id") or "?"
            src = c.get("source") or ""
            lines.append(f"### {cid} ({src})")
            lines.append("")
            lines.append(text)
            lines.append("")
    else:
        lines.extend(
            [
                "## Sources",
                "",
                "_No corpus chunks retrieved — Index sources for grounded guides._",
                "",
            ]
        )
    if citations:
        lines.append("## Citations")
        lines.append("")
        for c in citations[:8]:
            lines.append(
                f"- {c.get('chunk_id')} · {c.get('source')} · {c.get('heading')}"
            )
        lines.append("")
    body = "\n".join(lines).rstrip() + "\n"
    out_path = storage.study_guide_path(root, nid)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(body, encoding="utf-8")
    return CapabilityResult.success(
        f"Study guide for {nid}",
        path=str(out_path),
        study_guide_path=str(out_path),
        node_id=nid,
    )


ARCHIVE_SYSTEM_PROMPT = (
    "You are a course archive assistant, not a tutor. Answer the user's question "
    "from the provided source excerpts only. Cite chunk ids. Do not invent facts, "
    "table numbers, or math tokens that are not in the excerpts. When excerpts "
    "contain [table], [math], or [figure] blocks, use them. Do not teach a lesson "
    "or assign practice. Reply in ≤150 words."
)


def archive_chat(ctx: CapabilityContext, inp: ArchiveChatInput) -> CapabilityResult:
    from lacerta.core.capabilities import run_capability
    from lacerta.storage import corpus as corpus_storage

    root = _course_root(ctx)
    message = (inp.message or ctx.user_request or "").strip()
    if not message:
        return CapabilityResult.failure("empty_message", "archive chat requires a message")
    croot = storage.corpus_dir(root)
    meta = corpus_storage.load_meta(croot) if croot.is_dir() else {}
    if meta.get("status") != "complete":
        return CapabilityResult.failure(
            "corpus_not_ready",
            "Index sources first so archive chat can retrieve chunks",
        )
    ret = run_capability(
        "corpus.retrieve",
        ctx,
        {"query": message, "corpus_root": str(croot)},
    )
    if not ret.ok:
        return ret
    citations = list(ret.data.get("citations") or [])
    chunks = list(ret.data.get("chunks") or [])
    retrieved_bits = [
        f"[{c.get('chunk_id')} | {c.get('source')}] {c.get('text')}" for c in chunks[:5]
    ]
    digest, prior_turns = storage.load_archive_context(root)
    source_block = "\n\n".join(retrieved_bits) or "(no chunks)"
    taught = _teach_from_sources(
        ctx.client,
        question=message,
        source_block=source_block,
        history_digest=digest,
        prior_turns=prior_turns,
        system_prompt=ARCHIVE_SYSTEM_PROMPT,
        mastery_tier=0,
        focus_title="archive",
    )
    if taught:
        reply = taught
        grounding = "corpus_archive"
    else:
        cite_line = "; ".join(
            f"{c.get('chunk_id')} ({c.get('source')})" for c in citations[:5]
        )
        body = "\n\n".join(retrieved_bits)
        reply = f"Archive (retrieve): {message}\n\n{body}\n\nCitations: {cite_line or '—'}"
        grounding = "corpus_retrieve"
    ts = int(time.time())
    turn = {
        "ts": ts,
        "message": message,
        "reply": reply,
        "citations": citations,
        "grounding": grounding,
    }
    out_path = storage.archive_dir(root) / f"turn_{ts}.json"
    storage.write_json(out_path, turn)
    history_path = storage.archive_history_path(root)
    history = storage.read_json(history_path) or {"turns": []}
    turns = list(history.get("turns") or [])
    turns.append({"ts": ts, "path": str(out_path), "message": message[:120]})
    history["turns"] = turns[-storage.TUTOR_HISTORY_INDEX_MAX :]
    storage.write_json(history_path, history)
    new_digest = storage.compress_tutor_history(
        digest,
        message,
        reply,
        max_chars=storage.TUTOR_DIGEST_MAX_CHARS,
    )
    storage.save_archive_digest(root, new_digest)
    return CapabilityResult.success(
        "Archive chat reply written",
        path=str(out_path),
        archive_path=str(out_path),
        history_path=str(history_path),
        digest_path=str(storage.archive_digest_path(root)),
        grounding=grounding,
        citations=citations,
    )


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
            description="Write structured assessments from syllabus nodes",
            input_model=GenerateAssessmentsInput,
            handler=generate_assessments,
            surfaces=frozenset({"learn"}),
        ),
        CapabilitySpec(
            capability_id="learn.mastery_check",
            title="Mastery check",
            description="Generate short MC mastery check for a syllabus node",
            input_model=MasteryCheckInput,
            handler=generate_mastery_check,
            surfaces=frozenset({"learn"}),
        ),
        CapabilitySpec(
            capability_id="learn.generate_quiz",
            title="Practice quiz",
            description="Generate MC practice quiz for a syllabus node (± corpus retrieve)",
            input_model=PracticeQuizInput,
            handler=generate_practice_quiz,
            surfaces=frozenset({"learn"}),
        ),
        CapabilitySpec(
            capability_id="learn.generate_flashcards",
            title="Practice flashcards",
            description="Generate flashcard deck for a syllabus node",
            input_model=PracticeNodeInput,
            handler=generate_flashcards,
            surfaces=frozenset({"learn"}),
        ),
        CapabilitySpec(
            capability_id="learn.generate_study_guide",
            title="Practice study guide",
            description="Write study guide markdown for a syllabus node",
            input_model=PracticeNodeInput,
            handler=generate_study_guide,
            surfaces=frozenset({"learn"}),
        ),
        CapabilitySpec(
            capability_id="learn.tutor_turn",
            title="Tutor turn",
            description="One tutor reply grounded on syllabus + bounded notes",
            input_model=TutorTurnInput,
            handler=tutor_turn,
            surfaces=frozenset({"learn"}),
        ),
        CapabilitySpec(
            capability_id="learn.archive_chat",
            title="Archive chat",
            description="Retrieve-grounded archive reply from indexed corpus",
            input_model=ArchiveChatInput,
            handler=archive_chat,
            surfaces=frozenset({"learn"}),
        ),
    ]
    for spec in specs:
        register_capability(spec)


register_learn_capabilities()
