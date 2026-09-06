# Phase L4 — Honest evaluate + habit acceptance

**Status:** done  
**Depends on:** L3 exit (`learn_syllabus_files` green)  
**Exit:** `habit_tracker` tracked (3/3 before claiming “code reliable”)

**Sources:** port kit §8.2–§8.3, §8.1 habit scenario; architecture §4.3, §7, §8 step 5; surfaces §5, §11 `tpl.code.habit`.

---

## Goal

Harden harness honesty (disk acceptance over log theater) and land the multi-job code path: recon → edit → test for a CLI habit tracker with pytest-green acceptance.

---

## Habit modes

| Mode | Env | Behavior |
|------|-----|----------|
| **deterministic** (default) | `LACERTA_HABIT_MODE=deterministic` or scenario `deterministic_habit` | Manager still emits **recon → edit → test**. Recon lists the project root without Ollama; edit seeds `habit.py` / tests / README; test runs allowlisted `python -m pytest -q`. |
| **llm** | `LACERTA_HABIT_MODE=llm` | Full CodeWorker tool loop for all three steps (needs Ollama). |

---

## Checkboxes

- [x] Complete `evaluate_run` / `session_successful` per port kit §8.3
  - [x] Disk acceptance can pass without `final_report`
  - [x] Do **not** fail solely because `run_status=failed` if disk OK
  - [x] Drop scorecard noise like “finish_task not observed” when `code_ok`
- [x] Habit acceptance checker: expected files + pytest green
  - [x] `habit.py`, `tests/test_habit.py`, `README.md`
  - [x] Acceptance flag `habit_tracker: True`
- [x] Template `tpl.code.habit`: recon → edit → test
- [x] `run_command` allowlisted for pytest (and only safe commands)
- [x] Scenario `habit_tracker` in harness
- [x] Gate tracks habit runs (report 3/3); document as code-reliability bar
- [x] Metrics logging: worker sessions JSONL (turns / completed); token accounting deferred
- [ ] Optional: `manager_grades_failure` scenario green (deferred)

---

## Files

| Path | Role |
|------|------|
| `lacerta/harness/evaluate.py` | Honest evaluate + habit / learn keys |
| `lacerta/harness/scenarios.py` | `habit_tracker` |
| `lacerta/harness/acceptance_habit.py` | Files + pytest |
| `lacerta/core/routers/code.py` | `tpl.code.habit` |
| `lacerta/workers/code_tools.py` | Allowlisted `run_command` |
| `lacerta/workers/habit_scaffold.py` | Deterministic scaffold |
| `tests/test_evaluate_honesty.py` | Disk beats log theater |
| `tests/test_habit_acceptance.py` | Habit acceptance |

---

## Tests / harness

```bash
pytest tests/test_evaluate_honesty.py tests/test_habit_acceptance.py -q
export LACERTA_HABIT_MODE=deterministic
./scripts/gate.sh habit_tracker --runs 3
```

**Pass criteria:** 3/3 with files present and pytest green. Smoke + learn remain green.

---

## Architecture PR checklist

- [x] Harness before “reliable” claims
- [x] Disk is SoT for code
- [x] No heal towers as strategy
- [x] Manager still tool-less
- [x] Templates drive habit multi-job (no free decompose required)
- [x] No MCP/Remote
- [x] No L5 cascade from this phase

---

## Out of scope

ResearchWorker (L5 — packages may exist but remain unregistered), WritingWorker, GUI, LLM decompose.
