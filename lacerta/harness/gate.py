"""Harness gate CLI entrypoint."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

from lacerta.core.manager import run_manager
from lacerta.core.ollama_client import OllamaClient, check_worker_model
from lacerta.harness.evaluate import evaluate_run
from lacerta.harness.scenarios import SCENARIOS


def _data_root() -> Path:
    raw = os.getenv("LACERTA_DATA_ROOT", "").strip()
    if raw:
        return Path(raw).resolve()
    return Path(__file__).resolve().parents[2]


def _prepare_attachments(scenario: dict, root: Path) -> list[str]:
    out: list[str] = []
    for src in scenario.get("attachments") or []:
        src_path = Path(src)
        if not src_path.is_file():
            continue
        dest_dir = root / "attachments"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / src_path.name
        shutil.copy2(src_path, dest)
        out.append(str(dest))
    return out


def run_scenario(name: str, *, runs: int = 1, client: OllamaClient | None = None) -> int:
    if name not in SCENARIOS:
        print(f"Unknown scenario: {name!r}. Known: {sorted(SCENARIOS)}")
        return 1
    scenario = SCENARIOS[name]
    check = check_worker_model()
    if check.unknown:
        print(f"model check: {check.message}")

    ollama = client or OllamaClient()
    # Learn deterministic recipes do not require Ollama; still prefer health when available.
    needs_ollama = str(scenario.get("surface") or "code") in ("code",) or scenario.get(
        "requires_ollama"
    )
    if needs_ollama:
        try:
            ollama.health()
        except ConnectionError as e:
            print(str(e))
            return 1
    else:
        try:
            ollama.health()
        except ConnectionError:
            ollama = None  # type: ignore[assignment]

    passed = 0
    for run_n in range(1, runs + 1):
        root = _data_root() / "harness" / "runs" / name / f"run_{run_n}"
        if root.exists():
            for p in sorted(root.rglob("*"), reverse=True):
                if p.is_file():
                    p.unlink(missing_ok=True)
                elif p.is_dir():
                    try:
                        p.rmdir()
                    except OSError:
                        pass
        root.mkdir(parents=True, exist_ok=True)
        attachments = _prepare_attachments(scenario, root)

        default_template = {
            "code": "tpl.code.smoke",
            "learn": "tpl.learn.syllabus_files",
            "research": "tpl.research.offline",
            "writing": "tpl.writing.short",
            "chat": "tpl.chat.plain",
        }.get(str(scenario.get("surface") or "code"), "tpl.code.smoke")

        task_id = str(scenario.get("task_id") or f"{name}-{run_n}")
        deliverable_path = scenario.get("deliverable_path")
        if isinstance(deliverable_path, str) and "<task_id>" in deliverable_path:
            deliverable_path = deliverable_path.replace("<task_id>", task_id)

        inputs = {
            "root": str(root),
            "tools": list(scenario.get("tools") or []),
            "acceptance": dict(scenario.get("acceptance") or {}),
            "template_id": scenario.get("template_id") or default_template,
            "job_type": scenario.get("job_type", "code_edit"),
            "max_turns": int(scenario.get("max_turns") or 5),
            "instance_id": scenario.get("instance_id") or "default",
            "course_id": scenario.get("course_id") or "harness-course",
            "topic": scenario.get("topic"),
            "attachments": attachments,
            "task_id": task_id,
            "deliverable_path": deliverable_path,
            "recipe_id": scenario.get("recipe_id"),
            "deterministic_habit": scenario.get("deterministic_habit"),
        }
        # Drop Nones
        inputs = {k: v for k, v in inputs.items() if v is not None}

        state = run_manager(
            scenario["objective"],
            surface=str(scenario.get("surface") or "code"),
            inputs=inputs,
            client=ollama,
        )
        last = state.results[-1] if state.results else {}
        report = {
            "scenario": scenario,
            "project_root": str(root),
            "instance_id": inputs.get("instance_id"),
            "course_id": inputs.get("course_id"),
            "deliverable_path": inputs.get("deliverable_path"),
            "worker_metrics": last.get("metrics") or {},
            "run_status": "ok" if state.status == "finished" else "failed",
            "error": state.error or last.get("error"),
            "summary": last.get("summary"),
            "manager": {
                "status": state.status,
                "steps": state.steps,
                "jobs": [r.get("job_id") for r in state.results],
            },
        }
        ok, failures = evaluate_run(report)
        jobs = ",".join(report["manager"]["jobs"]) or "-"
        print(
            f"manager status={state.status} steps={state.steps} jobs=[{jobs}]"
        )
        if ok:
            passed += 1
            print(f"[{run_n}/{runs}] PASS {name} root={root}")
        else:
            print(f"[{run_n}/{runs}] FAIL {name}: {failures}")
            if state.error:
                print(f"  error: {state.error}")
            if last.get("summary"):
                print(f"  summary: {last['summary']}")

    print(f"{passed}/{runs} passed for {name}")
    return 0 if passed == runs else 1


def main(argv: list[str] | None = None) -> int:
    from lacerta.core.envload import load_dotenv

    load_dotenv()
    parser = argparse.ArgumentParser(
        prog="lacerta.harness.gate",
        description="Lacerta harness gate.",
    )
    parser.add_argument(
        "scenario",
        nargs="?",
        default="smoke_write_file",
        help="Scenario name (default: smoke_write_file)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Number of runs (default: 1; use 3 for smoke gate)",
    )
    args = parser.parse_args(argv)
    return run_scenario(args.scenario, runs=max(1, args.runs))


if __name__ == "__main__":
    sys.exit(main())
