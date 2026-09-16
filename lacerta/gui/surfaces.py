"""Surface → default MacroTemplate wiring for the thin GUI."""

from __future__ import annotations

import os
import uuid
from typing import Any

from lacerta.core.allowlists import allowed_job_types, is_allowed
from lacerta.workers.research.bulk import attachments_need_corpus

# Code checks: GUI labels only — harness ids stay CLI-facing.
CODE_SCENARIOS: dict[str, dict[str, Any]] = {
    "quick_file_check": {
        "label": "Quick file check",
        "template_id": "tpl.code.smoke",
        "placeholder": "Create harness_smoke.py that prints HARNESS_OK",
        "needs_ollama": True,
        "job_types": ("code_edit",),
        "tools": ["read_file", "write_file", "list_dir", "grep"],
        "acceptance": {
            "check_file_glob": "**/harness_smoke.py",
            "file_contains": "HARNESS_OK",
        },
        "cta_label": "Run check",
        "goal_label": "Goal",
        "hint": "Create a small file the harness can verify.",
        "show_course_browser": False,
        "show_workspace_root": True,
        "show_attachments": False,
        "require_attachments": False,
    },
    "habit_tracker": {
        "label": "Habit tracker (scaffold + tests)",
        "template_id": "tpl.code.habit",
        "placeholder": "Build a small habit tracker with tests under the workspace root",
        "needs_ollama": False,
        "job_types": ("code_recon", "code_edit", "code_test"),
        "tools": ["read_file", "write_file", "list_dir", "grep"],
        "acceptance": {"habit_tracker": True},
        "deterministic_habit": True,
        "cta_label": "Build habit tracker",
        "goal_label": "Goal",
        "hint": "Scaffold a habit tracker with tests (no Ollama required).",
        "show_course_browser": False,
        "show_workspace_root": True,
        "show_attachments": False,
        "require_attachments": False,
    },
}

# Learn modes: plain labels → templates / JobTypes.
LEARN_SCENARIOS: dict[str, dict[str, Any]] = {
    "build_syllabus": {
        "label": "Build syllabus",
        "template_id": "tpl.learn.syllabus_files",
        "placeholder": "Build a short syllabus from local notes",
        "needs_ollama": False,
        "job_types": ("learn_syllabus_files",),
        "show_attachments": True,
        "require_attachments": True,
        "cta_label": "Build syllabus",
        "goal_label": "Goal",
        "hint": "Structure a course syllabus from attached notes.",
        "show_course_browser": True,
        "show_workspace_root": True,
        "show_node_id": False,
    },
    "tutor": {
        "label": "Tutor",
        "template_id": "tpl.learn.tutor",
        "placeholder": "Ask a question about a syllabus unit…",
        "needs_ollama": False,
        "job_types": ("learn_tutor_turn",),
        "show_attachments": False,
        "require_attachments": False,
        "cta_label": "Ask tutor",
        "goal_label": "Question",
        "hint": "Ask a topical question (not “tutor me on C++”). Matches syllabus node mastery 0–5. Session history is compressed on disk; Clear tutor session resets it. Ollama improves teaching tone.",
        "show_course_browser": True,
        "show_workspace_root": True,
        "show_node_id": True,
    },
    "assessment": {
        "label": "Assessment",
        "template_id": "tpl.learn.assessment",
        "placeholder": "Generate practice checks for the current course",
        "needs_ollama": False,
        "job_types": ("learn_assessment",),
        "show_attachments": False,
        "require_attachments": False,
        "cta_label": "Generate assessment",
        "goal_label": "Focus (optional)",
        "hint": "Generate practice checks. Difficulty follows node mastery when Node id is set.",
        "show_course_browser": True,
        "show_workspace_root": True,
        "show_node_id": True,
    },
    "mastery_check": {
        "label": "Mastery check",
        "template_id": "tpl.learn.mastery_check",
        "placeholder": "Run a mastery check for a syllabus node (set Node id)",
        "needs_ollama": False,
        "job_types": ("learn_mastery_check",),
        "show_attachments": False,
        "require_attachments": False,
        "cta_label": "Generate mastery check",
        "goal_label": "Focus",
        "hint": "Requires Node id. Generates short MC; answer below and Submit to advance mastery on pass (fail leaves tier unchanged).",
        "show_course_browser": True,
        "show_workspace_root": True,
        "show_node_id": True,
        "require_node_id": True,
    },
    "practice": {
        "label": "Practice",
        "template_id": "tpl.learn.practice",
        "placeholder": "Generate a practice quiz for a syllabus node (set Node id)",
        "needs_ollama": False,
        "job_types": ("learn_practice_quiz",),
        "show_attachments": False,
        "require_attachments": False,
        "cta_label": "Generate practice quiz",
        "goal_label": "Focus",
        "hint": "Requires Node id. Interactive MC practice (Python-graded; does not change mastery). Use Flashcards / Study guide below after setting Node id. Grounds on corpus when indexed (tables/math/figures as text).",
        "show_course_browser": True,
        "show_workspace_root": True,
        "show_node_id": True,
        "require_node_id": True,
    },
    "archive": {
        "label": "Archive",
        "template_id": "tpl.learn.archive_chat",
        "placeholder": "Ask about indexed course sources…",
        "needs_ollama": False,
        "job_types": ("learn_archive_chat",),
        "show_attachments": False,
        "require_attachments": False,
        "cta_label": "Ask archive",
        "goal_label": "Question",
        "hint": "Index sources first. Exploratory Q&A from the corpus (not tutoring). Ollama personalizes the answer; otherwise you get a labeled retrieve paste. Clear archive session resets history only.",
        "show_course_browser": True,
        "show_workspace_root": True,
        "show_node_id": False,
    },
    "index_sources": {
        "label": "Index sources",
        "template_id": "tpl.learn.index_corpus",
        "placeholder": "Index attached textbook/notes into the course corpus",
        "needs_ollama": False,
        "job_types": ("learn_index_corpus",),
        "show_attachments": True,
        "require_attachments": True,
        "cta_label": "Index sources",
        "goal_label": "Index notes",
        "hint": "Chunk and index attached sources into the shared course corpus.",
        "show_course_browser": True,
        "show_workspace_root": True,
        "show_node_id": False,
    },
}

RESEARCH_SCENARIOS: dict[str, dict[str, Any]] = {
    "offline_sources": {
        "label": "Offline sources",
        "template_id": "tpl.research.offline",
        "placeholder": "Offline research note from attached sources",
        "needs_ollama": False,
        "job_types": ("research_local",),
        "show_attachments": True,
        "require_attachments": True,
        "cta_label": "Research offline",
        "goal_label": "Goal",
        "hint": "Write a research note from attached local sources.",
        "show_course_browser": False,
        "show_workspace_root": True,
    },
    "light_web": {
        "label": "Light web (deferred)",
        "template_id": "tpl.research.web",
        "placeholder": "Web gather is deferred — use Offline sources",
        "needs_ollama": False,
        "job_types": ("research_web",),
        "show_attachments": False,
        "require_attachments": False,
        "cta_label": "Research web",
        "goal_label": "Goal",
        "hint": "Web gather is deferred — use Offline sources instead.",
        "show_course_browser": False,
        "show_workspace_root": True,
    },
}

WRITING_SCENARIOS: dict[str, dict[str, Any]] = {
    "short_draft": {
        "label": "Short draft",
        "template_id": "tpl.writing.short",
        "placeholder": "Two-paragraph markdown draft with a clear # title.",
        "needs_ollama": False,
        "job_types": ("write_draft",),
        "show_attachments": False,
        "require_attachments": False,
        "target_document": "short.md",
        "cta_label": "Write draft",
        "goal_label": "Goal",
        "hint": "Draft a short markdown document with a clear title.",
        "show_course_browser": False,
        "show_workspace_root": True,
    },
    "from_sources": {
        "label": "From sources",
        "template_id": "tpl.writing.from_sources",
        "placeholder": "Draft from attached notes/sources",
        "needs_ollama": False,
        "job_types": ("write_from_sources",),
        "show_attachments": True,
        "require_attachments": True,
        "target_document": "from_sources.md",
        "cta_label": "Write from sources",
        "goal_label": "Goal",
        "hint": "Draft from attached notes or sources.",
        "show_course_browser": False,
        "show_workspace_root": True,
    },
}

SURFACE_DEFAULTS: dict[str, dict[str, Any]] = {
    "chat": {
        "template_id": "tpl.chat.plain",
        "job_types": ("chat_answer",),
        "label": "Chat",
        "placeholder": "Ask a question…",
        "cta_label": "Send",
        "goal_label": "Message",
        "hint": "Multi-turn local chat; prior turns stay in this session.",
        "show_attachments": False,
        "show_course_id": False,
        "show_title": False,
        "show_code_scenario": False,
        "show_learn_scenario": False,
        "show_research_scenario": False,
        "show_writing_scenario": False,
        "show_workspace_root": False,
        "show_course_browser": False,
    },
    "code": {
        "template_id": "tpl.code.smoke",
        "job_types": ("code_edit",),
        "label": "Code",
        "placeholder": "Create harness_smoke.py that prints HARNESS_OK",
        "tools": ["read_file", "write_file", "list_dir", "grep"],
        "cta_label": "Run check",
        "goal_label": "Goal",
        "hint": "",
        "show_attachments": False,
        "show_course_id": False,
        "show_title": False,
        "show_code_scenario": True,
        "show_learn_scenario": False,
        "show_research_scenario": False,
        "show_writing_scenario": False,
        "show_workspace_root": True,
        "show_course_browser": False,
        "default_scenario": "quick_file_check",
    },
    "learn": {
        "template_id": "tpl.learn.syllabus_files",
        "job_types": ("learn_syllabus_files",),
        "label": "Learn",
        "placeholder": "Build a short syllabus from local notes",
        "cta_label": "Build syllabus",
        "goal_label": "Goal",
        "hint": "",
        "show_attachments": True,
        "show_course_id": True,
        "show_title": False,
        "show_code_scenario": False,
        "show_learn_scenario": True,
        "show_research_scenario": False,
        "show_writing_scenario": False,
        "show_workspace_root": True,
        "show_course_browser": True,
        "default_scenario": "build_syllabus",
    },
    "research": {
        "template_id": "tpl.research.offline",
        "job_types": ("research_local",),
        "label": "Research",
        "placeholder": "Offline research note from attached sources",
        "cta_label": "Research offline",
        "goal_label": "Goal",
        "hint": "",
        "show_attachments": True,
        "show_course_id": False,
        "show_title": False,
        "show_code_scenario": False,
        "show_learn_scenario": False,
        "show_research_scenario": True,
        "show_writing_scenario": False,
        "show_workspace_root": True,
        "show_course_browser": False,
        "default_scenario": "offline_sources",
    },
    "writing": {
        "template_id": "tpl.writing.short",
        "job_types": ("write_draft",),
        "label": "Writing",
        "placeholder": "Two-paragraph markdown draft with a clear # title.",
        "cta_label": "Write draft",
        "goal_label": "Goal",
        "hint": "",
        "show_attachments": False,
        "show_course_id": False,
        "show_title": True,
        "show_code_scenario": False,
        "show_learn_scenario": False,
        "show_research_scenario": False,
        "show_writing_scenario": True,
        "show_workspace_root": True,
        "show_course_browser": False,
        "default_scenario": "short_draft",
    },
}

def _scenario_ui_fields(meta: dict[str, Any]) -> dict[str, Any]:
    return {
        "cta_label": str(meta.get("cta_label") or "Run"),
        "goal_label": str(meta.get("goal_label") or "Goal"),
        "hint": str(meta.get("hint") or ""),
        "show_attachments": bool(meta.get("show_attachments")),
        "require_attachments": bool(meta.get("require_attachments")),
        "show_course_browser": bool(meta.get("show_course_browser")),
        "show_workspace_root": bool(meta.get("show_workspace_root", True)),
        "show_node_id": bool(meta.get("show_node_id")),
        "require_node_id": bool(meta.get("require_node_id")),
    }


def _scenario_list(catalog: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": sid,
            "label": meta["label"],
            "placeholder": meta.get("placeholder") or "",
            "needs_ollama": bool(meta.get("needs_ollama")),
            **_scenario_ui_fields(meta),
        }
        for sid, meta in catalog.items()
    ]


def list_code_scenarios() -> list[dict[str, Any]]:
    return _scenario_list(CODE_SCENARIOS)


def list_learn_scenarios() -> list[dict[str, Any]]:
    return _scenario_list(LEARN_SCENARIOS)


def list_research_scenarios() -> list[dict[str, Any]]:
    return _scenario_list(RESEARCH_SCENARIOS)


def list_writing_scenarios() -> list[dict[str, Any]]:
    return _scenario_list(WRITING_SCENARIOS)


def list_surfaces() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for sid, meta in SURFACE_DEFAULTS.items():
        entry: dict[str, Any] = {
            "id": sid,
            "label": meta["label"],
            "template_id": meta["template_id"],
            "job_types": list(meta["job_types"]),
            "allowed_job_types": sorted(allowed_job_types(sid)),
            "placeholder": meta.get("placeholder") or "",
            "cta_label": str(meta.get("cta_label") or "Run"),
            "goal_label": str(meta.get("goal_label") or "Goal"),
            "hint": str(meta.get("hint") or ""),
            "show_attachments": bool(meta.get("show_attachments")),
            "show_course_id": bool(meta.get("show_course_id")),
            "show_title": bool(meta.get("show_title")),
            "show_code_scenario": bool(meta.get("show_code_scenario")),
            "show_learn_scenario": bool(meta.get("show_learn_scenario")),
            "show_research_scenario": bool(meta.get("show_research_scenario")),
            "show_writing_scenario": bool(meta.get("show_writing_scenario")),
            "show_workspace_root": bool(meta.get("show_workspace_root", True)),
            "show_course_browser": bool(meta.get("show_course_browser")),
        }
        if sid == "code":
            entry["code_scenarios"] = list_code_scenarios()
            entry["default_scenario"] = str(meta.get("default_scenario") or "quick_file_check")
        if sid == "learn":
            entry["learn_scenarios"] = list_learn_scenarios()
            entry["default_scenario"] = str(meta.get("default_scenario") or "build_syllabus")
        if sid == "research":
            entry["research_scenarios"] = list_research_scenarios()
            entry["default_scenario"] = str(meta.get("default_scenario") or "offline_sources")
        if sid == "writing":
            entry["writing_scenarios"] = list_writing_scenarios()
            entry["default_scenario"] = str(meta.get("default_scenario") or "short_draft")
        out.append(entry)
    return out


def build_run_inputs(
    surface: str,
    goal: str,
    root: str,
    *,
    light_research: bool = False,
    attachments: list[str] | None = None,
    course_id: str | None = None,
    title: str | None = None,
    scenario: str | None = None,
    messages: list[dict[str, Any]] | None = None,
    node_id: str | None = None,
) -> dict[str, Any]:
    """Build manager inputs for a GUI run. Never invents disallowed job types."""
    if surface not in SURFACE_DEFAULTS:
        raise ValueError(f"unknown surface {surface!r}")
    meta = SURFACE_DEFAULTS[surface]

    scenario_id: str | None = None
    scenario_meta: dict[str, Any] | None = None
    if surface == "code":
        scenario_id = (scenario or "").strip() or str(
            meta.get("default_scenario") or "quick_file_check"
        )
        scenario_meta = CODE_SCENARIOS.get(scenario_id)
        if scenario_meta is None:
            raise ValueError(f"unknown code scenario {scenario_id!r}")
        template_id = str(scenario_meta["template_id"])
        job_types = tuple(scenario_meta["job_types"])
    elif surface == "learn":
        scenario_id = (scenario or "").strip() or str(
            meta.get("default_scenario") or "build_syllabus"
        )
        scenario_meta = LEARN_SCENARIOS.get(scenario_id)
        if scenario_meta is None:
            raise ValueError(f"unknown learn scenario {scenario_id!r}")
        template_id = str(scenario_meta["template_id"])
        job_types = tuple(scenario_meta["job_types"])
    elif surface == "research":
        scenario_id = (scenario or "").strip() or str(
            meta.get("default_scenario") or "offline_sources"
        )
        scenario_meta = RESEARCH_SCENARIOS.get(scenario_id)
        if scenario_meta is None:
            raise ValueError(f"unknown research scenario {scenario_id!r}")
        template_id = str(scenario_meta["template_id"])
        job_types = tuple(scenario_meta["job_types"])
    elif surface == "writing":
        scenario_id = (scenario or "").strip() or str(
            meta.get("default_scenario") or "short_draft"
        )
        scenario_meta = WRITING_SCENARIOS.get(scenario_id)
        if scenario_meta is None:
            raise ValueError(f"unknown writing scenario {scenario_id!r}")
        template_id = str(scenario_meta["template_id"])
        job_types = tuple(scenario_meta["job_types"])
    else:
        template_id = str(meta["template_id"])
        job_types = tuple(meta["job_types"])

    for jt in job_types:
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
    if meta.get("tools") or (scenario_meta and scenario_meta.get("tools")):
        tools = (scenario_meta or meta).get("tools") or meta.get("tools")
        if tools:
            inputs["tools"] = list(tools)
    if surface == "chat":
        inputs["light_research"] = bool(light_research)
        if messages:
            inputs["messages"] = list(messages)
    if surface == "code" and scenario_meta is not None:
        inputs["scenario"] = scenario_id
        inputs["acceptance"] = dict(scenario_meta.get("acceptance") or {})
        if scenario_meta.get("deterministic_habit"):
            inputs["deterministic_habit"] = True
        if scenario_id == "quick_file_check":
            inputs["job_type"] = "code_edit"
    if surface == "learn" and scenario_meta is not None:
        inputs["scenario"] = scenario_id
        inputs["instance_id"] = "gui"
        cid = (course_id or "").strip() or "gui-course"
        inputs["course_id"] = cid
        if scenario_meta.get("show_attachments"):
            inputs["attachments"] = list(attachments or [])
        else:
            inputs["attachments"] = []
        if scenario_id == "build_syllabus":
            inputs["acceptance"] = {
                "syllabus_min_nodes": 8,
                "syllabus_min_subunits": 5,
                "course_active": True,
            }
        if scenario_id == "tutor":
            inputs["question"] = goal
        if scenario_id == "archive":
            inputs["message"] = goal
        if scenario_id == "index_sources":
            inputs["acceptance"] = {"corpus_complete": True}
        nid = (node_id or "").strip()
        if nid:
            inputs["node_id"] = nid
        elif scenario_meta.get("require_node_id"):
            raise ValueError("Node id is required for this Learn mode")
    if surface == "research" and scenario_meta is not None:
        inputs["scenario"] = scenario_id
        att = list(attachments or [])
        inputs["attachments"] = att if scenario_meta.get("show_attachments") else []
        inputs["deliverable_path"] = f"tasks/{task_id}/research/report.md"
        if scenario_id == "offline_sources":
            if attachments_need_corpus(att):
                inputs["use_corpus"] = True
                inputs["recipe_id"] = "research.offline_corpus"
            inputs["acceptance"] = {"min_deliverable_chars": 400}
    if surface == "writing" and scenario_meta is not None:
        inputs["scenario"] = scenario_id
        target = str(scenario_meta.get("target_document") or "short.md")
        inputs["target_document"] = target
        inputs["deliverable_path"] = f"tasks/{task_id}/writing/{target}"
        if scenario_meta.get("show_attachments"):
            inputs["attachments"] = list(attachments or [])
        else:
            inputs["attachments"] = []
        t = (title or "").strip()
        if t:
            inputs["title"] = t[:120]
        inputs["acceptance"] = {
            "min_deliverable_chars": 300,
            "require_title": True,
        }
    return inputs


def code_scenario_needs_ollama(scenario: str | None) -> bool:
    sid = (scenario or "").strip() or "quick_file_check"
    meta = CODE_SCENARIOS.get(sid)
    if meta is None:
        return True
    return bool(meta.get("needs_ollama", True))


def learn_scenario_needs_ollama(scenario: str | None) -> bool:
    sid = (scenario or "").strip() or "build_syllabus"
    meta = LEARN_SCENARIOS.get(sid)
    if meta is None:
        return False
    return bool(meta.get("needs_ollama", False))


def default_root() -> str:
    raw = os.getenv("LACERTA_DATA_ROOT", "").strip()
    if raw:
        return raw
    return os.getcwd()
