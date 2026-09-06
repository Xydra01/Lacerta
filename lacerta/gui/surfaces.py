"""Surface → default MacroTemplate wiring for the thin GUI."""

from __future__ import annotations

import os
import uuid
from typing import Any

from lacerta.core.allowlists import allowed_job_types, is_allowed

SURFACE_DEFAULTS: dict[str, dict[str, Any]] = {
    "chat": {
        "template_id": "tpl.chat.plain",
        "job_types": ("chat_answer",),
        "label": "Chat",
        "placeholder": "Ask a question…",
    },
    "code": {
        "template_id": "tpl.code.smoke",
        "job_types": ("code_edit",),
        "label": "Code",
        "placeholder": "Create harness_smoke.py that prints HARNESS_OK",
        "tools": ["read_file", "write_file", "list_dir", "grep"],
    },
    "learn": {
        "template_id": "tpl.learn.syllabus_files",
        "job_types": ("learn_syllabus_files",),
        "label": "Learn",
        "placeholder": "Build a short syllabus from local notes",
    },
    "research": {
        "template_id": "tpl.research.offline",
        "job_types": ("research_local",),
        "label": "Research",
        "placeholder": "Offline research note from attached sources",
    },
    "writing": {
        "template_id": "tpl.writing.short",
        "job_types": ("write_draft",),
        "label": "Writing",
        "placeholder": "Two-paragraph markdown draft with a clear # title.",
    },
}


def list_surfaces() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for sid, meta in SURFACE_DEFAULTS.items():
        out.append(
            {
                "id": sid,
                "label": meta["label"],
                "template_id": meta["template_id"],
                "job_types": list(meta["job_types"]),
                "allowed_job_types": sorted(allowed_job_types(sid)),
                "placeholder": meta.get("placeholder") or "",
            }
        )
    return out


def build_run_inputs(
    surface: str,
    goal: str,
    root: str,
    *,
    light_research: bool = False,
    attachments: list[str] | None = None,
) -> dict[str, Any]:
    """Build manager inputs for a GUI run. Never invents disallowed job types."""
    if surface not in SURFACE_DEFAULTS:
        raise ValueError(f"unknown surface {surface!r}")
    meta = SURFACE_DEFAULTS[surface]
    template_id = str(meta["template_id"])
    for jt in meta["job_types"]:
        if not is_allowed(surface, jt):
            raise ValueError(f"default job_type {jt!r} not allowed on {surface!r}")

    task_id = f"gui-{surface}-{uuid.uuid4().hex[:8]}"
    inputs: dict[str, Any] = {
        "root": str(root),
        "data_root": str(root),
        "template_id": template_id,
        "task_id": task_id,
        "topic": goal,
        "max_turns": 5,
    }
    if meta.get("tools"):
        inputs["tools"] = list(meta["tools"])
    if surface == "chat":
        inputs["light_research"] = bool(light_research)
    if surface == "code":
        inputs["job_type"] = "code_edit"
        inputs["acceptance"] = {
            "check_file_glob": "**/harness_smoke.py",
            "file_contains": "HARNESS_OK",
        }
    if surface == "learn":
        inputs["instance_id"] = "gui"
        inputs["course_id"] = "gui-course"
    if surface == "research":
        inputs["attachments"] = list(attachments or [])
        inputs["deliverable_path"] = f"tasks/{task_id}/research/report.md"
    if surface == "writing":
        inputs["target_document"] = "short.md"
        inputs["deliverable_path"] = f"tasks/{task_id}/writing/short.md"
        inputs["acceptance"] = {
            "min_deliverable_chars": 300,
            "require_title": True,
        }
    return inputs


def default_root() -> str:
    raw = os.getenv("LACERTA_DATA_ROOT", "").strip()
    if raw:
        return raw
    return os.getcwd()
