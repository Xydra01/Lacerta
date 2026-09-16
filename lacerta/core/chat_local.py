"""Manager-local chat completion (no FS tools)."""

from __future__ import annotations

from typing import Any

from lacerta.core.jobs import JobResult, JobSpec

CHAT_MAX_PRIOR_TURNS = 12  # user+assistant messages (≈6 pairs)
CHAT_MAX_PRIOR_CHARS = 12_000
_ALLOWED_ROLES = frozenset({"user", "assistant"})


def trim_prior_messages(
    raw: Any,
    *,
    max_turns: int = CHAT_MAX_PRIOR_TURNS,
    max_chars: int = CHAT_MAX_PRIOR_CHARS,
) -> list[dict[str, str]]:
    """Normalize and trim prior chat turns (user/assistant only)."""
    if not isinstance(raw, list):
        return []
    cleaned: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "").strip().lower()
        if role not in _ALLOWED_ROLES:
            continue
        content = str(item.get("content") or "").strip()
        if not content:
            continue
        cleaned.append({"role": role, "content": content})

    # Keep newest turns within caps (trim from the oldest).
    while len(cleaned) > max_turns:
        cleaned.pop(0)
    total = sum(len(m["content"]) for m in cleaned)
    while cleaned and total > max_chars:
        dropped = cleaned.pop(0)
        total -= len(dropped["content"])
    return cleaned


def build_chat_messages(
    *,
    objective: str,
    prior: list[dict[str, str]] | None = None,
    context: str = "",
) -> list[dict[str, str]]:
    """system → prior turns → final user (optional light-research context)."""
    messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": (
                "You are Lacerta chat. Answer clearly and briefly. "
                "You have no file-system or shell tools."
            ),
        }
    ]
    for m in prior or []:
        messages.append({"role": m["role"], "content": m["content"]})
    user = objective
    ctx = (context or "").strip()
    if ctx:
        user = f"Context:\n{ctx}\n\nQuestion:\n{objective}"
    messages.append({"role": "user", "content": user})
    return messages


def run_chat_answer(job: JobSpec, *, client: Any | None = None) -> JobResult:
    """Answer the user objective via Ollama with no tools."""
    if client is None:
        return JobResult(
            job_id=job.job_id,
            ok=False,
            summary="",
            error="chat_answer requires Ollama client",
        )
    inputs = dict(job.inputs or {})
    context = str(inputs.get("context") or "").strip()
    prior = trim_prior_messages(inputs.get("messages"))
    payload = build_chat_messages(
        objective=job.objective,
        prior=prior,
        context=context,
    )
    try:
        delta = getattr(client, "on_delta", None)
        result = client.chat(
            payload,
            temperature=0.4,
            stream=delta is not None,
            on_delta=delta,
        )
    except Exception as e:
        return JobResult(
            job_id=job.job_id,
            ok=False,
            summary="",
            error=str(e),
        )
    reply = str(result.get("message", {}).get("content") or "").strip()
    if not reply:
        return JobResult(
            job_id=job.job_id,
            ok=False,
            summary="",
            error="empty chat reply",
        )
    return JobResult(
        job_id=job.job_id,
        ok=True,
        summary=reply,
        metrics={
            "chat_chars": len(reply),
            "prior_turns": len(prior),
            "message_count": len(payload),
        },
    )
