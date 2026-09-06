"""Stateful manager — spawn_worker / finish_task / fail_task only."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal

from lacerta.core.allowlists import is_allowed
from lacerta.core.jobs import JobResult, JobSpec, Surface
from lacerta.core.routers import select_template
from lacerta.core import worker_runtime
from lacerta.harness.evaluate import check_acceptance

WorkerRunner = Callable[[JobSpec], JobResult]


def _manager_max_steps() -> int:
    raw = os.getenv("LACERTA_MANAGER_MAX_STEPS", "20").strip()
    try:
        return max(1, min(100, int(raw)))
    except ValueError:
        return 20


@dataclass
class MacroState:
    surface: Surface | str
    goal: str
    plan: list[str] = field(default_factory=list)
    results: list[dict[str, Any]] = field(default_factory=list)
    inputs: dict[str, Any] = field(default_factory=dict)
    status: Literal["running", "finished", "failed"] = "running"
    error: str | None = None
    steps: int = 0


def validate_job(job: JobSpec, surface: Surface | str) -> None:
    """Raise ValueError if job_type is not allowed for surface."""
    if not is_allowed(surface, job.job_type):
        raise ValueError(
            f"JobType {job.job_type!r} not allowed on surface {surface!r}"
        )


def spawn_worker(
    job: JobSpec,
    *,
    surface: str = "code",
    client: Any | None = None,
    runner: WorkerRunner | None = None,
) -> JobResult:
    """Dispatch typed jobs. Manager never calls FS/web tools itself."""
    if runner is not None:
        return runner(job)
    if str(job.job_type).startswith("code_"):
        return worker_runtime.run(job, client=client, surface=surface)
    if str(job.job_type).startswith("learn_"):
        from lacerta.workers.learn.worker import run as learn_run

        return learn_run(job, client=client, surface=surface)
    if str(job.job_type).startswith("research_"):
        from lacerta.workers.research.worker import run as research_run

        return research_run(job, client=client, surface=surface)
    if str(job.job_type).startswith("write_"):
        from lacerta.workers.writing.worker import run as writing_run

        return writing_run(job, client=client, surface=surface)
    return JobResult(
        job_id=job.job_id,
        ok=False,
        summary="",
        error=f"worker not implemented for {job.job_type!r} (L7+)",
    )


def finish_task(state: MacroState) -> None:
    state.status = "finished"
    state.error = None


def fail_task(state: MacroState, message: str) -> None:
    state.status = "failed"
    state.error = message


def _summarize_result(result: JobResult) -> dict[str, Any]:
    return {
        "job_id": result.job_id,
        "ok": result.ok,
        "summary": result.summary,
        "error": result.error,
        "metrics": dict(result.metrics or {}),
    }


def run_manager(
    goal: str,
    *,
    surface: Surface | str,
    inputs: dict[str, Any] | None = None,
    client: Any | None = None,
    runner: WorkerRunner | None = None,
    fail_fast: bool = True,
) -> MacroState:
    state = MacroState(
        surface=surface,
        goal=goal,
        inputs=dict(inputs or {}),
    )
    router = select_template(state)
    if router is None:
        fail_task(state, "no template matched (LLM decompose disabled until L7)")
        return state

    limit = _manager_max_steps()
    while state.status == "running" and state.steps < limit:
        state.steps += 1
        try:
            job = router.next_job(state)
        except NotImplementedError as e:
            fail_task(state, str(e))
            break
        except ValueError as e:
            fail_task(state, str(e))
            break

        if job is None:
            # Plan exhausted — grade disk acceptance if configured.
            root = state.inputs.get("root")
            acceptance = state.inputs.get("acceptance") or {}
            if root and acceptance:
                scenario = {
                    "acceptance": acceptance,
                    "instance_id": state.inputs.get("instance_id"),
                    "course_id": state.inputs.get("course_id"),
                    "task_id": state.inputs.get("task_id"),
                    "deliverable_path": state.inputs.get("deliverable_path"),
                }
                failures = check_acceptance(scenario, Path(str(root)))
                if failures:
                    fail_task(state, "; ".join(failures))
                else:
                    finish_task(state)
            elif state.results and all(r.get("ok") for r in state.results):
                finish_task(state)
            elif state.results:
                fail_task(state, "template plan exhausted with failed jobs")
            else:
                fail_task(state, "no template job")
            break

        try:
            validate_job(job, state.surface)
        except ValueError as e:
            fail_task(state, str(e))
            break

        result = spawn_worker(
            job,
            surface=str(state.surface),
            client=client,
            runner=runner,
        )
        state.results.append(_summarize_result(result))

        # Hard fail only on explicit worker errors. Soft ok=False still allows
        # plan exhaustion + disk acceptance (honest harness).
        if result.error:
            fail_task(state, result.error)
            break
        if fail_fast and not result.ok and not (state.inputs.get("acceptance")):
            fail_task(state, result.summary or "worker returned ok=False")
            break

    if state.status == "running":
        fail_task(state, f"manager step limit reached ({limit})")
    return state
