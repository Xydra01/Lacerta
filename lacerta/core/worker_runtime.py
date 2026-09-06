"""Worker runtime / CodeWorker tool loop."""

from __future__ import annotations

import inspect
import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

from lacerta.core.jobs import JobResult, JobSpec
from lacerta.core.ollama_client import OllamaClient
from lacerta.core.schema import build_worker_json_schema, parse_tool_turn
from lacerta.workers.code_tools import (
    CODE_TOOL_REGISTRY,
    get_active_tools,
    set_project_root,
)

WORKER_SYSTEM_PROMPT = """You are Lacerta CodeWorker.
Each turn reply with JSON only:
{"reasoning":"...","tools":[{"name":"TOOL","arguments":{...}}],"final_report":""}
Exactly one tools[] entry per turn (name + arguments object), OR tools=[] with a non-empty final_report when done.
Example write:
{"reasoning":"create smoke file","tools":[{"name":"write_file","arguments":{"path":"harness_smoke.py","content":"print('HARNESS_OK')\\n"}}],"final_report":""}
Example done:
{"reasoning":"done","tools":[],"final_report":"Created harness_smoke.py"}
Paths relative to PROJECT_ROOT. Read before edit. No multi-step plans. No capability IDs.
"""


def _max_turns() -> int:
    raw = os.getenv("LACERTA_WORKER_MAX_TURNS", "5").strip()
    try:
        return max(1, min(16, int(raw)))
    except ValueError:
        return 5


def tool_output_max_chars() -> int:
    raw = os.getenv("LACERTA_TOOL_OUTPUT_CHAR_CAP", "6000").strip()
    try:
        return max(256, int(raw))
    except ValueError:
        return 6000


def truncate_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 20] + "\n…[truncated]…"


def _block_tool_path_repeat(tool_name: str, path: str, prior_attempts: int) -> str | None:
    if tool_name not in ("write_file", "search_replace"):
        return None
    norm = (path or "").strip().replace("\\", "/")
    if not norm or prior_attempts < 2:
        return None
    if tool_name == "write_file":
        return (
            f"❌ OS BLOCK: `write_file` on `{norm}` repeated {prior_attempts + 1} times. "
            "Use `read_file`, `search_replace`, or set `final_report` if done."
        )
    return (
        f"❌ OS BLOCK: `{tool_name}` on `{norm}` repeated {prior_attempts + 1} times. "
        "Read with read_file, then unique search_replace."
    )


def _data_root() -> Path:
    raw = os.getenv("LACERTA_DATA_ROOT", "").strip()
    if raw:
        return Path(raw).resolve()
    # package lacerta/ -> repo root is parents[1]
    return Path(__file__).resolve().parents[2]


def _append_session_metrics(row: dict[str, Any]) -> None:
    log_dir = _data_root() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / "worker-sessions.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


@dataclass
class WorkerSessionMetrics:
    turns: int = 0
    wall_s: float = 0.0
    parse_failures: int = 0
    completed: bool = False
    model_id: str = ""
    job_id: str = ""
    job_type: str = ""
    surface: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_worker_session(
    client: Any,
    *,
    objective: str,
    tools_allowed: frozenset[str],
    registry: dict[str, dict[str, Any]],
    schema: dict[str, Any],
    system_prompt: str,
    max_turns: int | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Fresh messages every job. Return (summary, metrics_dict). Purge caller-side."""
    metrics: dict[str, Any] = {
        "turns": 0,
        "parse_failures": 0,
        "completed": False,
        "wall_s": 0.0,
    }
    started = time.monotonic()
    limit = max_turns or _max_turns()
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": objective},
    ]
    tool_path_attempts: dict[str, int] = {}
    last_summary = ""
    completed = False

    for turn in range(1, limit + 1):
        metrics["turns"] = turn
        if cancel_check and cancel_check():
            break
        result = client.chat(
            messages,
            temperature=0.2,
            format=schema,
            stream=False,
            force_think_disabled=True,
        )
        raw = (
            str(result.get("message", {}).get("content", "") or "")
            if isinstance(result, dict)
            else str(result or "")
        )
        parsed = parse_tool_turn(raw, tools_allowed)
        if not parsed:
            metrics["parse_failures"] += 1
            messages.append({"role": "assistant", "content": raw or "{}"})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Tool Outputs:\n❌ Invalid JSON. Reply with reasoning + "
                        "one tool in tools[] or final_report."
                    ),
                }
            )
            continue

        messages.append({"role": "assistant", "content": json.dumps(parsed)})
        final_report = str(parsed.get("final_report") or "").strip()
        tools = parsed.get("tools") or []
        if not tools:
            if final_report:
                last_summary = final_report
                completed = True
                break
            messages.append(
                {
                    "role": "user",
                    "content": "Tool Outputs:\n💡 Call a tool or set final_report.",
                }
            )
            continue

        call = tools[0]
        name = str(call.get("name") or "").strip()
        args = dict(call.get("arguments") or {})
        path = str(args.get("path") or "").strip()
        path_key = f"{name}|{path}"
        prior = tool_path_attempts.get(path_key, 0) if path else 0
        if path:
            tool_path_attempts[path_key] = prior + 1
        block = _block_tool_path_repeat(name, path, prior)
        if block:
            tool_out = block
        elif name not in tools_allowed:
            tool_out = f"❌ Unknown/disallowed tool `{name}`."
        else:
            func = registry[name]["func"]
            params = inspect.signature(func).parameters
            call_kwargs = {k: v for k, v in args.items() if k in params}
            missing = [
                p.name
                for p in params.values()
                if p.default is inspect.Parameter.empty
                and p.kind
                in (
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    inspect.Parameter.KEYWORD_ONLY,
                )
                and p.name not in call_kwargs
            ]
            if missing:
                tool_out = (
                    f"❌ Missing required arguments for `{name}`: {missing}. "
                    f"Got keys: {sorted(args.keys())}."
                )
            else:
                try:
                    tool_out = str(func(**call_kwargs))
                except TypeError as e:
                    tool_out = f"❌ Tool `{name}` TypeError: {e}"

        tool_out = truncate_text(tool_out, tool_output_max_chars())
        messages.append({"role": "user", "content": f"Tool Outputs:\n{tool_out}"})

    metrics["completed"] = completed
    metrics["wall_s"] = round(time.monotonic() - started, 2)
    # Drop message list — caller must not retain
    messages.clear()
    return last_summary or "Worker finished.", metrics


def run(job: JobSpec, *, client: Any | None = None, surface: str = "code") -> JobResult:
    root_raw = (job.inputs or {}).get("root")
    if not root_raw:
        return JobResult(
            job_id=job.job_id,
            ok=False,
            summary="",
            error="JobSpec.inputs['root'] is required for code jobs",
        )
    root = Path(str(root_raw)).resolve()
    root.mkdir(parents=True, exist_ok=True)

    # Deterministic habit scaffold (L4 harness-reliable path)
    scaffold = (job.inputs or {}).get("deterministic_scaffold")
    if scaffold == "habit_recon":
        set_project_root(root)
        try:
            listing = CODE_TOOL_REGISTRY["list_dir"]["func"](".")
        finally:
            set_project_root(None)
        summary = f"Recon complete.\n{listing}"
        row = {
            "turns": 1,
            "parse_failures": 0,
            "completed": True,
            "wall_s": 0.0,
            "model_id": "deterministic",
            "job_id": job.job_id,
            "job_type": job.job_type,
            "surface": surface,
        }
        try:
            _append_session_metrics(row)
        except OSError:
            pass
        return JobResult(
            job_id=job.job_id,
            ok=True,
            summary=summary[:500],
            metrics=row,
        )
    if scaffold == "habit":
        from lacerta.workers.habit_scaffold import write_habit_scaffold

        artifacts = write_habit_scaffold(root)
        row = {
            "turns": 0,
            "parse_failures": 0,
            "completed": True,
            "wall_s": 0.0,
            "model_id": "deterministic",
            "job_id": job.job_id,
            "job_type": job.job_type,
            "surface": surface,
        }
        try:
            _append_session_metrics(row)
        except OSError:
            pass
        return JobResult(
            job_id=job.job_id,
            ok=True,
            summary=f"Seeded habit scaffold: {', '.join(artifacts)}",
            artifacts=artifacts,
            metrics=row,
        )
    if scaffold == "habit_test":
        set_project_root(root)
        try:
            out = CODE_TOOL_REGISTRY["run_command"]["func"]("python -m pytest -q")
        finally:
            set_project_root(None)
        ok = out.startswith("[OK]")
        row = {
            "turns": 1,
            "parse_failures": 0,
            "completed": ok,
            "wall_s": 0.0,
            "model_id": "deterministic",
            "job_id": job.job_id,
            "job_type": job.job_type,
            "surface": surface,
        }
        try:
            _append_session_metrics(row)
        except OSError:
            pass
        return JobResult(
            job_id=job.job_id,
            ok=ok,
            summary=out[:500],
            metrics=row,
            error=None if ok else "pytest failed",
        )

    tools_allowed = get_active_tools(job.tools or None)
    if not tools_allowed:
        tools_allowed = get_active_tools(
            ["read_file", "write_file", "list_dir", "grep"]
        )
    # Cap at 4 tool names for CodeWorker
    if len(tools_allowed) > 4:
        preferred = ["read_file", "write_file", "list_dir", "grep", "search_replace"]
        capped = [t for t in preferred if t in tools_allowed][:4]
        if len(capped) < 4:
            for t in sorted(tools_allowed):
                if t not in capped:
                    capped.append(t)
                if len(capped) >= 4:
                    break
        tools_allowed = frozenset(capped)

    registry = {k: CODE_TOOL_REGISTRY[k] for k in tools_allowed}
    schema = build_worker_json_schema(tools_allowed)
    ollama = client or OllamaClient()
    set_project_root(root)
    try:
        summary, metrics = run_worker_session(
            ollama,
            objective=job.objective,
            tools_allowed=tools_allowed,
            registry=registry,
            schema=schema,
            system_prompt=WORKER_SYSTEM_PROMPT,
            max_turns=job.max_turns,
        )
    except (ConnectionError, RuntimeError, OSError) as e:
        set_project_root(None)
        return JobResult(
            job_id=job.job_id,
            ok=False,
            summary="",
            error=str(e),
            metrics={},
        )
    finally:
        set_project_root(None)

    model_id = getattr(ollama, "model", "") or ""
    row = {
        **metrics,
        "model_id": model_id,
        "job_id": job.job_id,
        "job_type": job.job_type,
        "surface": surface,
    }
    try:
        _append_session_metrics(row)
    except OSError:
        pass

    return JobResult(
        job_id=job.job_id,
        ok=bool(metrics.get("completed")),
        summary=summary,
        artifacts=[],
        metrics=row,
        error=None,
    )
