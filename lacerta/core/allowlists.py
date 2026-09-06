"""Surface → JobType allowlists."""

from __future__ import annotations

from typing import Mapping

from lacerta.core.jobs import JobType, Surface

SURFACE_JOB_TYPES: dict[Surface, frozenset[str]] = {
    "chat": frozenset({"chat_answer", "research_light"}),
    "code": frozenset({"code_recon", "code_edit", "code_test"}),
    "learn": frozenset(
        {
            "learn_syllabus_files",
            "learn_syllabus_web",
            "learn_assessment",
            "learn_tutor_turn",
            "learn_archive_chat",
        }
    ),
    "research": frozenset({"research_local", "research_web"}),
    "writing": frozenset({"write_draft", "write_finalize", "write_from_sources"}),
}


def allowed_job_types(surface: Surface | str) -> frozenset[str]:
    return SURFACE_JOB_TYPES.get(surface, frozenset())  # type: ignore[arg-type]


def is_allowed(surface: Surface | str, job_type: JobType | str) -> bool:
    return str(job_type) in allowed_job_types(surface)


def all_surfaces() -> tuple[str, ...]:
    return tuple(SURFACE_JOB_TYPES.keys())


def as_mapping() -> Mapping[str, frozenset[str]]:
    return dict(SURFACE_JOB_TYPES)
