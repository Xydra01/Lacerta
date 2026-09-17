"""Host sizing profiles. Surfaces and recipes do not change; only the model budget does.

``full`` is the default (9B-class host, 32k context). ``lite`` is the 4B / 8k budget
for Windows, Linux, and low-RAM machines. ``macos`` is an alias of ``lite`` so an
existing Mac ``.env`` still applies the small budget — new setups should set
``LACERTA_PROFILE=lite``.
"""

from __future__ import annotations

import os

FULL = "full"
LITE = "lite"

_LITE_ALIASES = frozenset({"lite", "macos", "mac", "devmacos"})


def profile_name() -> str:
    raw = os.getenv("LACERTA_PROFILE", FULL).strip().lower() or FULL
    if raw in _LITE_ALIASES:
        return LITE
    return FULL


def is_lite() -> bool:
    return profile_name() == LITE


def default_num_ctx() -> int:
    return 8192 if is_lite() else 32768


def default_num_predict() -> int:
    """Both profiles cap a turn so small models finish. Override with OLLAMA_NUM_PREDICT."""
    return 1024


def default_write_chars() -> int:
    return 6000 if is_lite() else 8000


def default_tool_output_chars() -> int:
    return 4000 if is_lite() else 6000
