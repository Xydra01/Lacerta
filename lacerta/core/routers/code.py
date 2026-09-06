"""Code surface MacroTemplates."""

from __future__ import annotations

import os
import uuid
from typing import TYPE_CHECKING, Any

from lacerta.core.jobs import JobSpec

if TYPE_CHECKING:
    from lacerta.core.manager import MacroState


class CodeSmokeTemplate:
    template_id = "tpl.code.smoke"

    def can_handle(self, state: MacroState) -> bool:
        if state.surface != "code":
            return False
        tid = str(state.inputs.get("template_id") or self.template_id)
        return tid == self.template_id

    def next_job(self, state: MacroState) -> JobSpec | None:
        if state.plan:
            return None
        tools = list(state.inputs.get("tools") or [])
        if not tools:
            tools = ["read_file", "write_file", "list_dir", "grep"]
        root = state.inputs.get("root")
        if not root:
            raise ValueError("tpl.code.smoke requires inputs['root']")
        job_type = str(state.inputs.get("job_type") or "code_edit")
        max_turns = int(state.inputs.get("max_turns") or 5)
        job = JobSpec(
            job_id=f"smoke-{uuid.uuid4().hex[:8]}",
            job_type=job_type,  # type: ignore[arg-type]
            objective=state.goal,
            inputs={"root": str(root)},
            tools=tools[:4],
            acceptance=dict(state.inputs.get("acceptance") or {}),
            max_turns=max_turns,
        )
        state.plan.append("code_edit")
        return job


class CodeHabitTemplate:
    template_id = "tpl.code.habit"

    _STEPS = ("code_recon", "code_edit", "code_test")

    def can_handle(self, state: MacroState) -> bool:
        if state.surface != "code":
            return False
        tid = str(state.inputs.get("template_id") or "")
        return tid == self.template_id

    def next_job(self, state: MacroState) -> JobSpec | None:
        root = state.inputs.get("root")
        if not root:
            raise ValueError("tpl.code.habit requires inputs['root']")
        mode = os.getenv("LACERTA_HABIT_MODE", "deterministic").strip().lower()
        deterministic = mode == "deterministic" or bool(
            state.inputs.get("deterministic_habit")
        )
        # Always recon → edit → test (blueprint). Deterministic steps skip Ollama.
        done = set(state.plan)
        for step in self._STEPS:
            if step in done:
                continue
            if step == "code_recon":
                tools = ["list_dir", "grep", "read_file", "find_files"]
                objective = (
                    "Recon the project root. List files. "
                    "Then set final_report summarizing what exists."
                )
                inputs: dict[str, Any] = {"root": str(root)}
                if deterministic:
                    inputs["deterministic_scaffold"] = "habit_recon"
            elif step == "code_edit":
                tools = ["read_file", "write_file", "search_replace", "list_dir"]
                objective = state.goal
                inputs = {"root": str(root)}
                if deterministic:
                    inputs["deterministic_scaffold"] = "habit"
            else:
                tools = ["run_command", "read_file", "list_dir", "grep"]
                objective = (
                    "Run pytest for the habit tracker using run_command "
                    "with `python -m pytest -q`. Then set final_report."
                )
                inputs = {"root": str(root)}
                if deterministic:
                    inputs["deterministic_scaffold"] = "habit_test"
            job = JobSpec(
                job_id=f"habit-{step}-{uuid.uuid4().hex[:8]}",
                job_type=step,  # type: ignore[arg-type]
                objective=objective,
                inputs=inputs,
                tools=tools,
                acceptance=dict(state.inputs.get("acceptance") or {}),
                max_turns=int(state.inputs.get("max_turns") or 5),
            )
            state.plan.append(step)
            return job
        return None


CODE_TEMPLATES: dict[str, Any] = {
    CodeSmokeTemplate.template_id: CodeSmokeTemplate(),
    CodeHabitTemplate.template_id: CodeHabitTemplate(),
}
