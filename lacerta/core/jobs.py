from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Surface = Literal["chat", "code", "learn", "research", "writing"]

JobType = Literal[
    "code_edit",
    "code_test",
    "code_recon",
    "learn_syllabus_files",
    "learn_syllabus_web",
    "learn_assessment",
    "learn_tutor_turn",
    "learn_archive_chat",
    "research_local",
    "research_web",
    "research_light",
    "write_draft",
    "write_finalize",
    "write_from_sources",
    "chat_answer",
]


class JobSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str
    job_type: JobType
    objective: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    # CodeWorker: 2–4 tool names. Recipe workers: usually [].
    tools: list[str] = Field(default_factory=list)
    acceptance: dict[str, Any] = Field(default_factory=dict)
    max_turns: int = 5


class JobResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str
    ok: bool
    summary: str
    artifacts: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
