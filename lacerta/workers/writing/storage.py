"""Writing draft storage and compile helpers."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def writing_dir(data_root: Path | str, task_id: str) -> Path:
    path = Path(data_root) / "tasks" / task_id / "writing"
    path.mkdir(parents=True, exist_ok=True)
    return path


def draft_path(data_root: Path | str, task_id: str) -> Path:
    return writing_dir(data_root, task_id) / "active_draft.json"


def deliverable_path(data_root: Path | str, task_id: str, slug: str = "short.md") -> Path:
    name = slug if slug.endswith(".md") else f"{slug}.md"
    return writing_dir(data_root, task_id) / name


def default_draft(*, title: str = "Untitled") -> dict[str, Any]:
    return {
        "title": title,
        "scratch": "",
        "sections": [],  # list[{"header": str, "body": str}]
    }


def load_draft(data_root: Path | str, task_id: str) -> dict[str, Any] | None:
    path = draft_path(data_root, task_id)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_draft(data_root: Path | str, task_id: str, draft: dict[str, Any]) -> Path:
    path = draft_path(data_root, task_id)
    path.write_text(json.dumps(draft, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def strip_heading_marks(text: str) -> str:
    lines = []
    for line in (text or "").splitlines():
        lines.append(re.sub(r"^#{1,6}\s*", "", line))
    return "\n".join(lines).strip()


def compile_markdown(draft: dict[str, Any]) -> str:
    title = str(draft.get("title") or "Untitled").strip() or "Untitled"
    title = strip_heading_marks(title)
    parts = [f"# {title}", ""]
    for sec in draft.get("sections") or []:
        if not isinstance(sec, dict):
            continue
        header = strip_heading_marks(str(sec.get("header") or "Section"))
        body = strip_heading_marks(str(sec.get("body") or ""))
        parts.append(f"## {header}")
        parts.append("")
        if body:
            parts.append(body)
            parts.append("")
    text = "\n".join(parts).rstrip() + "\n"
    # Ensure exactly one H1 at start
    lines = text.splitlines()
    h1 = [i for i, ln in enumerate(lines) if ln.startswith("# ") and not ln.startswith("## ")]
    if not h1:
        lines.insert(0, f"# {title}")
    elif h1[0] != 0:
        # move first h1 to top conceptually — keep simple: prefix if missing at 0
        if not lines[0].startswith("# "):
            lines.insert(0, f"# {title}")
    # Downgrade any extra H1 after first to H2
    seen = False
    fixed: list[str] = []
    for ln in lines:
        if ln.startswith("# ") and not ln.startswith("## "):
            if not seen:
                fixed.append(ln)
                seen = True
            else:
                fixed.append("#" + ln)  # ## 
        else:
            fixed.append(ln)
    return "\n".join(fixed).rstrip() + "\n"


def section_body_chars(draft: dict[str, Any]) -> int:
    total = 0
    for sec in draft.get("sections") or []:
        if isinstance(sec, dict):
            total += len(str(sec.get("body") or "").strip())
    return total
