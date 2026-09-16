"""Attachment size/count thresholds for research corpus bulk path (V1.4)."""

from __future__ import annotations

from pathlib import Path

# Bulk if more than this many files OR total readable bytes exceed this.
CORPUS_ATTACHMENT_COUNT = 3
CORPUS_ATTACHMENT_BYTES = 80_000


def attachment_byte_total(paths: list[str | Path]) -> int:
    total = 0
    for raw in paths:
        p = Path(raw)
        if p.is_file():
            try:
                total += p.stat().st_size
            except OSError:
                continue
    return total


def attachments_need_corpus(
    paths: list[str | Path],
    *,
    count_threshold: int = CORPUS_ATTACHMENT_COUNT,
    bytes_threshold: int = CORPUS_ATTACHMENT_BYTES,
) -> bool:
    """True when attachments should use shared corpus instead of full-text concat."""
    files = [Path(p) for p in paths if Path(p).is_file()]
    if len(files) > count_threshold:
        return True
    return attachment_byte_total(files) > bytes_threshold
