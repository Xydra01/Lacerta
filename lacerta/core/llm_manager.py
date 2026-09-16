"""Optional LLM manager decompose — propose typed JobSpecs only."""

from __future__ import annotations

import json
import os
import uuid
from typing import TYPE_CHECKING, Any

from lacerta.core.allowlists import allowed_job_types
from lacerta.core.jobs import JobSpec

if TYPE_CHECKING:
    from lacerta.core.manager import MacroState

# Keep in sync with lacerta.core.jobs.JobType
_JOB_TYPE_ENUM: list[str] = [
    "code_edit",
    "code_test",
    "code_recon",
    "learn_syllabus_files",
    "learn_syllabus_web",
    "learn_assessment",
    "learn_mastery_check",
    "learn_practice_quiz",
    "learn_tutor_turn",
    "learn_archive_chat",
    "learn_index_corpus",
    "research_local",
    "research_web",
    "research_light",
    "write_draft",
    "write_finalize",
    "write_from_sources",
    "chat_answer",
]

JOB_PROPOSAL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "done": {"type": "boolean"},
        "job_type": {"type": "string", "enum": _JOB_TYPE_ENUM},
        "objective": {"type": "string"},
        "tools": {"type": "array", "items": {"type": "string"}},
        "inputs": {"type": "object"},
        "max_turns": {"type": "integer"},
    },
    "required": ["done"],
}

_PLUMBING_KEYS = (
    "root",
    "data_root",
    "task_id",
    "attachments",
    "instance_id",
    "course_id",
    "topic",
    "acceptance",
    "deliverable_path",
    "target_document",
)


def llm_decompose_enabled() -> bool:
    raw = os.getenv("LACERTA_LLM_DECOMPOSE", "0").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def llm_decompose_max() -> int:
    raw = os.getenv("LACERTA_LLM_DECOMPOSE_MAX", "3").strip()
    try:
        return max(1, min(20, int(raw)))
    except ValueError:
        return 3


def _merge_plumbing(state: MacroState, proposed: dict[str, Any]) -> dict[str, Any]:
    merged = dict(proposed or {})
    for key in _PLUMBING_KEYS:
        if key in state.inputs and state.inputs[key] is not None:
            # Prefer state plumbing for paths/roots; allow LLM extras otherwise.
            if key in ("root", "data_root", "task_id", "attachments", "acceptance"):
                merged[key] = state.inputs[key]
            elif key not in merged:
                merged[key] = state.inputs[key]
    if "root" in merged and "data_root" not in merged:
        merged["data_root"] = merged["root"]
    return merged


def _parse_proposal(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if not text:
        raise ValueError("empty LLM proposal")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM proposal JSON parse failed: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("LLM proposal must be a JSON object")
    return data


def _chat_once(client: Any, messages: list[dict[str, Any]]) -> dict[str, Any]:
    result = client.chat(messages, temperature=0.1, format=JOB_PROPOSAL_SCHEMA)
    content = str(result.get("message", {}).get("content") or "")
    return _parse_proposal(content)


def propose_job(state: MacroState, client: Any) -> JobSpec | None:
    """Ask the LLM for one JobSpec (or done). Raises ValueError on bad shape."""
    if client is None:
        raise ValueError("LLM decompose requires Ollama client")

    allowed = sorted(allowed_job_types(state.surface))
    prior = [
        {
            "job_id": r.get("job_id"),
            "ok": r.get("ok"),
            "summary": r.get("summary"),
            "error": r.get("error"),
        }
        for r in (state.results or [])
    ]
    system = (
        "You are Lacerta's manager decompose helper. "
        "Emit exactly one JSON object matching the schema. "
        "Propose at most one next typed JobSpec. "
        f"Surface={state.surface!r}; allowed job_types={allowed}. "
        "Set done=true when the goal is already satisfied or no further job is needed. "
        "When done=false, set job_type and objective. "
        "For code jobs, tools is a list of at most 4 names "
        "(read_file, write_file, list_dir, grep, search_replace, run_command). "
        "Do not invent narrative plans; JobSpec fields only."
    )
    user = (
        f"Goal: {state.goal}\n"
        f"Prior results: {json.dumps(prior, ensure_ascii=False)}\n"
        f"State plan so far: {state.plan}"
    )
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    try:
        data = _chat_once(client, messages)
    except ValueError as first:
        # One optional re-ask on JSON parse failure only.
        messages.append(
            {
                "role": "user",
                "content": f"Previous reply was invalid ({first}). Reply with valid JSON only.",
            }
        )
        data = _chat_once(client, messages)

    if bool(data.get("done")):
        return None

    job_type = data.get("job_type")
    if not job_type:
        raise ValueError("LLM proposal missing job_type (and done is false)")
    objective = str(data.get("objective") or state.goal).strip() or state.goal
    tools = list(data.get("tools") or [])
    if not isinstance(tools, list):
        tools = []
    tools = [str(t) for t in tools][:4]
    inputs = data.get("inputs") if isinstance(data.get("inputs"), dict) else {}
    merged = _merge_plumbing(state, inputs)

    max_turns = data.get("max_turns")
    try:
        mt = int(max_turns) if max_turns is not None else int(state.inputs.get("max_turns") or 5)
    except (TypeError, ValueError):
        mt = 5
    mt = max(1, min(20, mt))

    return JobSpec(
        job_id=f"llm-{uuid.uuid4().hex[:8]}",
        job_type=str(job_type),  # type: ignore[arg-type]
        objective=objective,
        inputs=merged,
        tools=tools,
        acceptance=dict(merged.get("acceptance") or state.inputs.get("acceptance") or {}),
        max_turns=mt,
    )


__all__ = [
    "JOB_PROPOSAL_SCHEMA",
    "llm_decompose_enabled",
    "llm_decompose_max",
    "propose_job",
]
