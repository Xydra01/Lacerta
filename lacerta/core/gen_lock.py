"""Shared generation lock stub (prep for MCP/Remote)."""

from __future__ import annotations

import threading

_LOCK = threading.Lock()
_HELD = False


class GenerationBusy(RuntimeError):
    """Raised when a generation is already in progress."""


def acquire_generation(*, blocking: bool = False, timeout: float = 0.0) -> bool:
    """Acquire the process-wide generation lock. Non-blocking by default."""
    global _HELD
    if blocking:
        ok = _LOCK.acquire(timeout=timeout if timeout > 0 else -1)
    else:
        ok = _LOCK.acquire(blocking=False)
    if not ok:
        raise GenerationBusy("generation already in progress")
    _HELD = True
    return True


def release_generation() -> None:
    global _HELD
    if not _HELD:
        return
    _HELD = False
    try:
        _LOCK.release()
    except RuntimeError:
        pass


def generation_held() -> bool:
    return _HELD
