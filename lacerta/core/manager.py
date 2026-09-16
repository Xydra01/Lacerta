"""Stateful manager — spawn_worker / finish_task / fail_task only."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal

from lacerta.core.allowlists import is_allowed
from lacerta.core.jobs import JobResult, JobSpec, Surface
from lacerta.core.llm_manager import (
    llm_decompose_enabled,
    llm_decompose_max,
    propose_job,
)
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
    acceptance_ok: bool | None = None
    acceptance_failures: list[str] = field(default_factory=list)


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
    if job.job_type == "chat_answer":
        from lacerta.core.chat_local import run_chat_answer

        return run_chat_answer(job, client=client)
    return JobResult(
        job_id=job.job_id,
        ok=False,
        summary="",
        error=f"worker not implemented for {job.job_type!r} (L9+)",
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
        "artifacts": list(result.artifacts or []),
    }


def _finish_or_grade(state: MacroState, *, empty_msg: str) -> None:
    """Plan exhausted — grade disk acceptance if configured."""
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
            state.acceptance_ok = False
            state.acceptance_failures = list(failures)
            fail_task(state, "; ".join(failures))
        else:
            state.acceptance_ok = True
            state.acceptance_failures = []
            finish_task(state)
    elif state.results and all(r.get("ok") for r in state.results):
        state.acceptance_ok = None
        finish_task(state)
    elif state.results:
        state.acceptance_ok = False
        state.acceptance_failures = ["plan exhausted with failed jobs"]
        fail_task(state, "plan exhausted with failed jobs")
    else:
        state.acceptance_ok = False
        state.acceptance_failures = [empty_msg]
        fail_task(state, empty_msg)


def _run_job(
    state: MacroState,
    job: JobSpec,
    *,
    client: Any | None,
    runner: WorkerRunner | None,
    fail_fast: bool,
) -> bool:
    """Validate + spawn. Returns False if manager should stop."""
    try:
        validate_job(job, state.surface)
    except ValueError as e:
        fail_task(state, str(e))
        return False

    result = spawn_worker(
        job,
        surface=str(state.surface),
        client=client,
        runner=runner,
    )
    state.results.append(_summarize_result(result))

    if result.error:
        fail_task(state, result.error)
        return False
    if fail_fast and not result.ok and not (state.inputs.get("acceptance")):
        fail_task(state, result.summary or "worker returned ok=False")
        return False
    return True


def run_manager(
    goal: str,
    *,
    surface: Surface | str,
    inputs: dict[str, Any] | None = None,
    client: Any | None = None,
    runner: WorkerRunner | None = None,
    fail_fast: bool = True,
    on_progress: Callable[[MacroState], None] | None = None,
) -> MacroState:
    state = MacroState(
        surface=surface,
        goal=goal,
        inputs=dict(inputs or {}),
    )
    router = select_template(state)
    if router is None:
        if not llm_decompose_enabled():
            fail_task(
                state,
                "no template matched (set LACERTA_LLM_DECOMPOSE=1 to enable LLM decompose)",
            )
            return state
        if client is None:
            fail_task(state, "LLM decompose requires Ollama client")
            return state
        return _run_llm_loop(
            state,
            client=client,
            runner=runner,
            fail_fast=fail_fast,
            on_progress=on_progress,
        )

    return _run_template_loop(
        state,
        router,
        client=client,
        runner=runner,
        fail_fast=fail_fast,
        on_progress=on_progress,
    )


def _notify(on_progress: Callable[[MacroState], None] | None, state: MacroState) -> None:
    if on_progress is None:
        return
    try:
        on_progress(state)
    except Exception:
        pass


def _run_template_loop(
    state: MacroState,
    router: Any,
    *,
    client: Any | None,
    runner: WorkerRunner | None,
    fail_fast: bool,
    on_progress: Callable[[MacroState], None] | None = None,
) -> MacroState:
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
            _finish_or_grade(state, empty_msg="no template job")
            break

        _notify(on_progress, state)
        if not _run_job(state, job, client=client, runner=runner, fail_fast=fail_fast):
            break
        _notify(on_progress, state)

    if state.status == "running":
        fail_task(state, f"manager step limit reached ({limit})")
    _notify(on_progress, state)
    return state


def _run_llm_loop(
    state: MacroState,
    *,
    client: Any,
    runner: WorkerRunner | None,
    fail_fast: bool,
    on_progress: Callable[[MacroState], None] | None = None,
) -> MacroState:
    limit = _manager_max_steps()
    propose_cap = llm_decompose_max()
    llm_proposes = 0

    while state.status == "running" and state.steps < limit:
        state.steps += 1
        if llm_proposes >= propose_cap:
            fail_task(
                state,
                f"LLM decompose propose cap reached ({propose_cap})",
            )
            break
        try:
            job = propose_job(state, client)
        except ValueError as e:
            fail_task(state, str(e))
            break

        if job is None:
            _finish_or_grade(state, empty_msg="LLM decompose returned done with no jobs")
            break

        llm_proposes += 1
        state.plan.append(f"llm:{job.job_type}")
        _notify(on_progress, state)
        if not _run_job(state, job, client=client, runner=runner, fail_fast=fail_fast):
            break
        _notify(on_progress, state)

        # After a successful job, if acceptance is already met, stop early.
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
            if not failures:
                state.acceptance_ok = True
                state.acceptance_failures = []
                finish_task(state)
                break

    if state.status == "running":
        fail_task(state, f"manager step limit reached ({limit})")
    _notify(on_progress, state)
    return state
