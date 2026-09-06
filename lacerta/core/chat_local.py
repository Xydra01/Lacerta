"""Manager-local chat completion (no FS tools)."""

from __future__ import annotations

from typing import Any

from lacerta.core.jobs import JobResult, JobSpec


def run_chat_answer(job: JobSpec, *, client: Any | None = None) -> JobResult:
    """Answer the user objective via Ollama with no tools."""
    if client is None:
        return JobResult(
            job_id=job.job_id,
            ok=False,
            summary="",
            error="chat_answer requires Ollama client",
        )
    context = str((job.inputs or {}).get("context") or "").strip()
    user = job.objective
    if context:
        user = f"Context:\n{context}\n\nQuestion:\n{job.objective}"
    try:
        result = client.chat(
            [
                {
                    "role": "system",
                    "content": (
                        "You are Lacerta chat. Answer clearly and briefly. "
                        "You have no file-system or shell tools."
                    ),
                },
                {"role": "user", "content": user},
            ],
            temperature=0.4,
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
        metrics={"chat_chars": len(reply)},
    )
