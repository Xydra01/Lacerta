"""Syllabus proposal: deterministic (default) or LLM."""

from __future__ import annotations

import json
import os
import re
from typing import Any


def _mode() -> str:
    return os.getenv("LACERTA_LEARN_SYLLABUS_MODE", "deterministic").strip().lower() or "deterministic"


def build_deterministic_syllabus(topic: str, notes: str) -> dict[str, Any]:
    """Build a deep syllabus (≥8 nodes, ≥5 with parent_id) from topic/notes."""
    topic = (topic or "Course").strip() or "Course"
    # Extract candidate section titles from notes headings / lines
    titles: list[str] = []
    for line in (notes or "").splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^#{1,3}\s+(.+)$", line)
        if m:
            titles.append(m.group(1).strip()[:80])
            continue
        if line.startswith("- ") or line.startswith("* "):
            titles.append(line[2:].strip()[:80])
    # Ensure enough unique units
    defaults = [
        "Foundations",
        "Core Concepts",
        "Methods",
        "Applications",
        "Practice",
        "Assessment Prep",
        "Advanced Topics",
        "Review and Synthesis",
    ]
    while len(titles) < 4:
        titles.append(defaults[len(titles) % len(defaults)])

    nodes: list[dict[str, Any]] = []
    # 4 top-level units + 2 sub-units each = 12 nodes, 8 with parent_id
    top = titles[:4] if len(titles) >= 4 else (titles + defaults)[:4]
    for i, title in enumerate(top, start=1):
        uid = f"unit-{i}"
        nodes.append(
            {
                "id": uid,
                "title": f"{topic}: {title}" if i == 1 else title,
                "parent_id": None,
                "mastery_tier": 0,
                "required_assessment_id": None,
            }
        )
        for j, suffix in enumerate(("Overview", "Deep Dive"), start=1):
            nodes.append(
                {
                    "id": f"{uid}-s{j}",
                    "title": f"{title} — {suffix}",
                    "parent_id": uid,
                    "mastery_tier": 0,
                    "required_assessment_id": None,
                }
            )
    return {"status": "building", "nodes": nodes, "assessments": []}


def propose_syllabus(
    *,
    topic: str,
    notes: str,
    client: Any | None = None,
) -> dict[str, Any]:
    if _mode() != "llm" or client is None:
        return build_deterministic_syllabus(topic, notes)
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "status": {"type": "string"},
            "nodes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "id": {"type": "string"},
                        "title": {"type": "string"},
                        "parent_id": {"type": ["string", "null"]},
                        "mastery_tier": {"type": "integer"},
                        "required_assessment_id": {"type": ["string", "null"]},
                    },
                    "required": ["id", "title", "parent_id", "mastery_tier"],
                },
            },
            "assessments": {"type": "array"},
        },
        "required": ["nodes"],
    }
    prompt = (
        f"Build a deep course syllabus JSON for topic: {topic}\n"
        "Require at least 8 nodes and at least 5 child nodes with parent_id set.\n"
        f"Notes:\n{(notes or '')[:8000]}"
    )
    try:
        result = client.chat(
            [
                {"role": "system", "content": "Return only syllabus JSON matching the schema."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            format=schema,
            stream=False,
            force_think_disabled=True,
        )
        raw = str(result.get("message", {}).get("content", "") or "")
        data = json.loads(raw)
        if isinstance(data, dict) and isinstance(data.get("nodes"), list):
            data.setdefault("status", "building")
            data.setdefault("assessments", [])
            return data
    except Exception:
        pass
    return build_deterministic_syllabus(topic, notes)
