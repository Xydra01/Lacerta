"""Shared on-disk corpus layout, fingerprints, and meta (V1.35)."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from lacerta.storage.extract import SUPPORTED_SUFFIXES, is_extractable

TEXT_SUFFIXES = {".md", ".txt", ".markdown"}
# V1.55: attachments may be PDF/DOCX/HTML/CSV; corpus sources/ stores normalized .md.
ATTACHMENT_SUFFIXES = SUPPORTED_SUFFIXES

DEFAULT_TOP_K = 5
DEFAULT_MAX_CHARS = 2400
CHUNK_TARGET_CHARS = 800


def fingerprint_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def fingerprint_file(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest()[:16]


def ensure_corpus_layout(corpus_root: Path | str) -> Path:
    root = Path(corpus_root)
    (root / "sources").mkdir(parents=True, exist_ok=True)
    (root / "chunks").mkdir(parents=True, exist_ok=True)
    (root / "index").mkdir(parents=True, exist_ok=True)
    return root


def corpus_json_path(corpus_root: Path) -> Path:
    return Path(corpus_root) / "corpus.json"


def sources_dir(corpus_root: Path) -> Path:
    return Path(corpus_root) / "sources"


def chunks_dir(corpus_root: Path) -> Path:
    return Path(corpus_root) / "chunks"


def map_path(corpus_root: Path) -> Path:
    return Path(corpus_root) / "map.json"


def keyword_index_path(corpus_root: Path) -> Path:
    return Path(corpus_root) / "index" / "keyword.json"


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def default_meta(corpus_id: str) -> dict[str, Any]:
    return {
        "corpus_id": corpus_id,
        "status": "pending",
        "index_backend": "none",
        "chunk_count": 0,
        "source_fingerprints": {},
        "stale": False,
        "error": None,
    }


def load_meta(corpus_root: Path) -> dict[str, Any]:
    ensure_corpus_layout(corpus_root)
    meta = read_json(corpus_json_path(corpus_root))
    if meta is None:
        meta = default_meta(Path(corpus_root).name)
        write_json(corpus_json_path(corpus_root), meta)
    return meta


def save_meta(corpus_root: Path, meta: dict[str, Any]) -> None:
    ensure_corpus_layout(corpus_root)
    write_json(corpus_json_path(corpus_root), meta)


def resolve_course_corpus_root(
    data_root: Path | str,
    instance_id: str,
    course_id: str,
) -> Path:
    """Course-bound corpus root (V1.3 layout)."""
    return (
        Path(data_root)
        / "instances"
        / instance_id
        / "learn"
        / "courses"
        / course_id
        / "corpus"
    )


def resolve_task_corpus_root(
    data_root: Path | str,
    task_id: str,
    *,
    surface: str = "research",
) -> Path:
    """Task-scoped corpus root (V1.4 research bulk)."""
    return Path(data_root) / "tasks" / task_id / surface / "corpus"


def is_supported_source(path: Path) -> bool:
    """True if path can be ingested (plain text or extractable binary)."""
    return is_extractable(path)


def is_normalized_source(path: Path) -> bool:
    """True if path is already plain text under corpus/sources."""
    return path.suffix.lower() in TEXT_SUFFIXES


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9_]+", text.lower()) if len(t) > 1]


def compute_stale(corpus_root: Path, meta: dict[str, Any] | None = None) -> bool:
    """True if on-disk source fingerprints differ from meta."""
    meta = meta or load_meta(corpus_root)
    recorded = dict(meta.get("source_fingerprints") or {})
    src_dir = sources_dir(corpus_root)
    if not src_dir.is_dir():
        return bool(recorded)
    current: dict[str, str] = {}
    for path in sorted(src_dir.iterdir()):
        if path.is_file() and is_normalized_source(path):
            current[path.name] = fingerprint_file(path)
    return current != recorded
