"""Paths, shared corpus (chunk/index/retrieve), embeddings, and learn registry.

See docs/architecture-v1.md §4.3 and docs/phases/phase-V1.35.md.
"""

from lacerta.storage import corpus as corpus_storage
from lacerta.storage import extract as extract_storage

__all__ = ["corpus_storage", "extract_storage"]
