"""Learn course storage paths and JSON helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

NOTES_CHAR_CAP = 4000
TUTOR_NOTES_CHAR_CAP = 2000
TUTOR_DIGEST_MAX_CHARS = 1500
TUTOR_LAST_RAW_TURNS = 4
TUTOR_HISTORY_INDEX_MAX = 50


def course_dir(data_root: Path | str, instance_id: str, course_id: str) -> Path:
    return (
        Path(data_root)
        / "instances"
        / instance_id
        / "learn"
        / "courses"
        / course_id
    )


def ensure_course_dirs(data_root: Path | str, instance_id: str, course_id: str) -> Path:
    root = course_dir(data_root, instance_id, course_id)
    (root / "sources").mkdir(parents=True, exist_ok=True)
    (root / "assessments").mkdir(parents=True, exist_ok=True)
    (root / "assessments" / "attempts").mkdir(parents=True, exist_ok=True)
    (root / "practice").mkdir(parents=True, exist_ok=True)
    (root / "corpus").mkdir(parents=True, exist_ok=True)
    (root / "tutor").mkdir(parents=True, exist_ok=True)
    (root / "archive").mkdir(parents=True, exist_ok=True)
    from lacerta.storage import corpus as corpus_storage

    corpus_storage.ensure_corpus_layout(root / "corpus")
    return root


def syllabus_path(course_root: Path) -> Path:
    return course_root / "syllabus.json"


def course_json_path(course_root: Path) -> Path:
    return course_root / "course.json"


def notes_path(course_root: Path) -> Path:
    return course_root / "sources" / "notes.md"


def corpus_dir(course_root: Path) -> Path:
    return course_root / "corpus"


def corpus_meta_path(course_root: Path) -> Path:
    return course_root / "corpus" / "corpus.json"


def assessments_dir(course_root: Path) -> Path:
    return course_root / "assessments"


def mastery_path(course_root: Path) -> Path:
    return course_root / "mastery.json"


def mastery_check_path(course_root: Path, node_id: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in node_id) or "node"
    return assessments_dir(course_root) / f"mastery_check_{safe}.json"


def _safe_node(node_id: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in node_id) or "node"


def practice_dir(course_root: Path) -> Path:
    d = course_root / "practice"
    d.mkdir(parents=True, exist_ok=True)
    return d


def attempts_dir(course_root: Path) -> Path:
    d = assessments_dir(course_root) / "attempts"
    d.mkdir(parents=True, exist_ok=True)
    return d


def quiz_path(course_root: Path, node_id: str) -> Path:
    return assessments_dir(course_root) / f"quiz_{_safe_node(node_id)}.json"


def attempt_path(course_root: Path, node_id: str, ts: int | None = None) -> Path:
    import time

    stamp = int(ts if ts is not None else time.time())
    return attempts_dir(course_root) / f"attempt_{stamp}_{_safe_node(node_id)}.json"


def flashcards_path(course_root: Path, node_id: str) -> Path:
    return practice_dir(course_root) / f"flashcards_{_safe_node(node_id)}.json"


def study_guide_path(course_root: Path, node_id: str) -> Path:
    return practice_dir(course_root) / f"study_guide_{_safe_node(node_id)}.md"


def validate_quiz_payload(doc: dict[str, Any]) -> str | None:
    """Return error message if quiz JSON is malformed; else None."""
    if not isinstance(doc, dict):
        return "quiz must be an object"
    questions = doc.get("questions")
    if not isinstance(questions, list) or not questions:
        return "quiz questions must be a non-empty list"
    for i, q in enumerate(questions):
        if not isinstance(q, dict):
            return f"question {i} must be an object"
        if not str(q.get("id") or "").strip():
            return f"question {i} missing id"
        if not str(q.get("prompt") or "").strip():
            return f"question {i} missing prompt"
        choices = q.get("choices")
        if not isinstance(choices, list) or len(choices) < 2:
            return f"question {i} needs at least 2 choices"
        try:
            ci = int(q.get("correct_index"))
        except (TypeError, ValueError):
            return f"question {i} missing correct_index"
        if ci < 0 or ci >= len(choices):
            return f"question {i} correct_index out of range"
    return None


def clamp_tier(value: Any) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        n = 0
    return max(0, min(5, n))


def load_mastery(course_root: Path) -> dict[str, Any]:
    doc = read_json(mastery_path(course_root)) or {}
    nodes = doc.get("nodes")
    if not isinstance(nodes, dict):
        nodes = {}
    return {"nodes": nodes}


def ensure_mastery(course_root: Path, syllabus: dict[str, Any] | None) -> dict[str, Any]:
    """Ensure every syllabus node has a mastery entry (default tier 0)."""
    import time

    doc = load_mastery(course_root)
    nodes_map: dict[str, Any] = dict(doc.get("nodes") or {})
    changed = False
    syllabus_nodes = (syllabus or {}).get("nodes") or []
    if isinstance(syllabus_nodes, list):
        for node in syllabus_nodes:
            if not isinstance(node, dict):
                continue
            nid = str(node.get("id") or "").strip()
            if not nid:
                continue
            if nid not in nodes_map or not isinstance(nodes_map[nid], dict):
                nodes_map[nid] = {
                    "tier": 0,
                    "updated_ts": int(time.time()),
                }
                changed = True
            else:
                entry = dict(nodes_map[nid])
                tier = clamp_tier(entry.get("tier", 0))
                if entry.get("tier") != tier:
                    entry["tier"] = tier
                    changed = True
                nodes_map[nid] = entry
    if changed or not mastery_path(course_root).is_file():
        write_json(mastery_path(course_root), {"nodes": nodes_map})
    return {"nodes": nodes_map}


def get_node_tier(course_root: Path, node_id: str | None) -> int:
    nid = (node_id or "").strip()
    if not nid:
        return 0
    doc = load_mastery(course_root)
    entry = (doc.get("nodes") or {}).get(nid)
    if isinstance(entry, dict):
        return clamp_tier(entry.get("tier", 0))
    return 0


def set_node_tier(course_root: Path, node_id: str, tier: int) -> int:
    """Set mastery tier (clamped 0..5), write mastery.json, mirror onto syllabus."""
    import time

    nid = (node_id or "").strip()
    if not nid:
        raise ValueError("node_id required")
    new_tier = clamp_tier(tier)
    doc = load_mastery(course_root)
    nodes_map: dict[str, Any] = dict(doc.get("nodes") or {})
    nodes_map[nid] = {"tier": new_tier, "updated_ts": int(time.time())}
    write_json(mastery_path(course_root), {"nodes": nodes_map})

    spath = syllabus_path(course_root)
    syllabus = read_json(spath)
    if syllabus and isinstance(syllabus.get("nodes"), list):
        for node in syllabus["nodes"]:
            if isinstance(node, dict) and str(node.get("id") or "") == nid:
                node["mastery_tier"] = new_tier
        write_json(spath, syllabus)
    return new_tier


def tutor_dir(course_root: Path) -> Path:
    return course_root / "tutor"


def tutor_digest_path(course_root: Path) -> Path:
    return tutor_dir(course_root) / "history_digest.json"


def tutor_history_path(course_root: Path) -> Path:
    return tutor_dir(course_root) / "tutor_history.json"


def compress_tutor_history(
    prior_digest: str,
    new_question: str,
    new_reply: str,
    *,
    max_chars: int = TUTOR_DIGEST_MAX_CHARS,
) -> str:
    """Deterministic rolling digest: append Q/A, trim from the front to fit max_chars."""
    q = " ".join((new_question or "").split())
    a = " ".join((new_reply or "").split())
    if len(q) > 200:
        q = q[:197] + "…"
    if len(a) > 400:
        a = a[:397] + "…"
    piece = f"Q: {q} / A: {a}".strip()
    if len(piece) > max_chars:
        piece = piece[: max(0, max_chars - 1)] + ("…" if max_chars > 0 else "")
    prior = (prior_digest or "").strip()
    combined = f"{prior}\n{piece}".strip() if prior else piece
    if len(combined) <= max_chars:
        return combined
    # Trim oldest segments (newline-separated) from the front; keep newest piece.
    parts = [p for p in combined.split("\n") if p.strip()]
    while len(parts) > 1 and sum(len(p) for p in parts) + max(0, len(parts) - 1) > max_chars:
        parts.pop(0)
    out = "\n".join(parts)
    if len(out) > max_chars:
        out = out[-max_chars:]
    return out


def load_tutor_context(
    course_root: Path,
    *,
    last_k: int = TUTOR_LAST_RAW_TURNS,
) -> tuple[str, list[dict[str, str]]]:
    """Load compressed digest + last K raw Q/A turns from disk."""
    digest_doc = read_json(tutor_digest_path(course_root)) or {}
    digest = str(digest_doc.get("digest") or "")
    history = read_json(tutor_history_path(course_root)) or {}
    entries = list(history.get("turns") or [])
    last_turns: list[dict[str, str]] = []
    for entry in entries[-max(0, last_k) :]:
        if not isinstance(entry, dict):
            continue
        path_str = str(entry.get("path") or "")
        if not path_str:
            continue
        turn = read_json(Path(path_str))
        if not turn:
            continue
        q = str(turn.get("question") or "").strip()
        a = str(turn.get("reply") or "").strip()
        if q and a:
            last_turns.append({"question": q, "reply": a})
    return digest, last_turns


def save_tutor_digest(
    course_root: Path,
    digest: str,
    *,
    turn_count: int | None = None,
) -> None:
    import time

    prev = read_json(tutor_digest_path(course_root)) or {}
    count = turn_count
    if count is None:
        count = int(prev.get("turn_count") or 0) + 1
    write_json(
        tutor_digest_path(course_root),
        {
            "digest": digest,
            "updated_ts": int(time.time()),
            "turn_count": count,
        },
    )


def clear_tutor_session(course_root: Path) -> dict[str, Any]:
    """Wipe digest + truncate history index. Turn JSON files remain as artifacts."""
    tdir = tutor_dir(course_root)
    tdir.mkdir(parents=True, exist_ok=True)
    write_json(
        tutor_digest_path(course_root),
        {"digest": "", "updated_ts": 0, "turn_count": 0},
    )
    write_json(tutor_history_path(course_root), {"turns": []})
    return {"ok": True, "tutor_dir": str(tdir)}


def archive_dir(course_root: Path) -> Path:
    d = course_root / "archive"
    d.mkdir(parents=True, exist_ok=True)
    return d


def archive_digest_path(course_root: Path) -> Path:
    return archive_dir(course_root) / "history_digest.json"


def archive_history_path(course_root: Path) -> Path:
    return archive_dir(course_root) / "history_index.json"


def load_archive_context(
    course_root: Path,
    *,
    last_k: int = TUTOR_LAST_RAW_TURNS,
) -> tuple[str, list[dict[str, str]]]:
    """Load archive digest + last K turns (message/reply)."""
    digest_doc = read_json(archive_digest_path(course_root)) or {}
    digest = str(digest_doc.get("digest") or "")
    history = read_json(archive_history_path(course_root)) or {}
    entries = list(history.get("turns") or [])
    last_turns: list[dict[str, str]] = []
    for entry in entries[-max(0, last_k) :]:
        if not isinstance(entry, dict):
            continue
        path_str = str(entry.get("path") or "")
        if not path_str:
            continue
        turn = read_json(Path(path_str))
        if not turn:
            continue
        q = str(turn.get("message") or turn.get("question") or "").strip()
        a = str(turn.get("reply") or "").strip()
        if q and a:
            last_turns.append({"question": q, "reply": a})
    return digest, last_turns


def save_archive_digest(
    course_root: Path,
    digest: str,
    *,
    turn_count: int | None = None,
) -> None:
    import time

    prev = read_json(archive_digest_path(course_root)) or {}
    count = turn_count
    if count is None:
        count = int(prev.get("turn_count") or 0) + 1
    write_json(
        archive_digest_path(course_root),
        {
            "digest": digest,
            "updated_ts": int(time.time()),
            "turn_count": count,
        },
    )


def clear_archive_session(course_root: Path) -> dict[str, Any]:
    """Wipe archive digest + history index. Does not touch tutor session."""
    adir = archive_dir(course_root)
    write_json(
        archive_digest_path(course_root),
        {"digest": "", "updated_ts": 0, "turn_count": 0},
    )
    write_json(archive_history_path(course_root), {"turns": []})
    return {"ok": True, "archive_dir": str(adir)}


def default_corpus_id(instance_id: str, course_id: str) -> str:
    return f"{instance_id}:{course_id}"


def ensure_course_meta(
    data_root: Path | str,
    instance_id: str,
    course_id: str,
    *,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Ensure course dirs + course.json with corpus reservation (pending)."""
    from lacerta.storage import corpus as corpus_storage

    root = ensure_course_dirs(data_root, instance_id, course_id)
    cpath = course_json_path(root)
    course = read_json(cpath) or {
        "course_id": course_id,
        "instance_id": instance_id,
        "build_complete": False,
        "status": "pending",
    }
    cid = str(course.get("corpus_id") or default_corpus_id(instance_id, course_id))
    course["corpus_id"] = cid
    croot = corpus_dir(root)
    corpus_meta = corpus_storage.load_meta(croot)
    corpus_meta["corpus_id"] = cid
    if corpus_meta.get("status") in (None, ""):
        corpus_meta["status"] = "pending"
    corpus_storage.save_meta(croot, corpus_meta)
    if extra:
        course.update(extra)
    write_json(cpath, course)
    return course


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_notes_bounded(course_root: Path, *, max_chars: int = NOTES_CHAR_CAP) -> str:
    np = notes_path(course_root)
    if not np.is_file():
        return ""
    text = np.read_text(encoding="utf-8", errors="replace")
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n…[truncated]"


def syllabus_node_summaries(syllabus: dict[str, Any]) -> list[dict[str, Any]]:
    """Read-only node list for GUI (id, title, parent_id, mastery_tier)."""
    nodes = syllabus.get("nodes") or []
    out: list[dict[str, Any]] = []
    if not isinstance(nodes, list):
        return out
    for node in nodes:
        if not isinstance(node, dict):
            continue
        out.append(
            {
                "id": str(node.get("id") or ""),
                "title": str(node.get("title") or ""),
                "parent_id": node.get("parent_id"),
                "mastery_tier": node.get("mastery_tier"),
            }
        )
    return out


def load_course_browse(
    data_root: Path | str,
    instance_id: str,
    course_id: str,
) -> dict[str, Any]:
    """Course snapshot for GUI. May init mastery.json once from syllabus nodes."""
    root = course_dir(data_root, instance_id, course_id)
    syllabus = read_json(syllabus_path(root)) if root.is_dir() else None
    course = read_json(course_json_path(root)) if root.is_dir() else None
    corpus = read_json(corpus_meta_path(root)) if (root / "corpus").is_dir() else None
    if syllabus and root.is_dir():
        ensure_mastery(root, syllabus)
    nodes = syllabus_node_summaries(syllabus) if syllabus else []
    # Authoritative tiers from mastery.json
    if root.is_dir() and nodes:
        for n in nodes:
            nid = str(n.get("id") or "")
            if nid:
                n["mastery_tier"] = get_node_tier(root, nid)
    return {
        "course_id": course_id,
        "instance_id": instance_id,
        "course_root": str(root) if root.exists() else None,
        "syllabus_path": str(syllabus_path(root)) if syllabus else None,
        "course_path": str(course_json_path(root)) if course else None,
        "corpus_path": str(corpus_meta_path(root)) if corpus else None,
        "mastery_path": str(mastery_path(root)) if root.is_dir() else None,
        "course": course,
        "corpus": corpus,
        "syllabus_status": (syllabus or {}).get("status"),
        "nodes": nodes,
        "node_count": len(nodes),
        "exists": root.is_dir() and (syllabus is not None or course is not None),
    }


def validate_syllabus_structure(
    syllabus: dict[str, Any],
    *,
    min_nodes: int = 8,
    min_subunits: int = 5,
) -> list[str]:
    failures: list[str] = []
    nodes = syllabus.get("nodes")
    if not isinstance(nodes, list):
        return ["syllabus.nodes must be a list"]
    if len(nodes) < min_nodes:
        failures.append(f"need ≥{min_nodes} nodes, got {len(nodes)}")
    subunits = 0
    for i, node in enumerate(nodes):
        if not isinstance(node, dict):
            failures.append(f"node[{i}] not an object")
            continue
        if not node.get("id") or not node.get("title"):
            failures.append(f"node[{i}] missing id/title")
        if node.get("parent_id"):
            subunits += 1
    if subunits < min_subunits:
        failures.append(f"need ≥{min_subunits} sub-units (parent_id set), got {subunits}")
    return failures
