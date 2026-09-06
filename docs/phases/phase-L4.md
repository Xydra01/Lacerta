# Phase L4 — Honest evaluate + habit acceptance

**Status:** planned  
**Depends on:** L3 exit (`learn_syllabus_files` green)  
**Exit:** `habit_tracker` tracked (3/3 before claiming “code reliable”)  

**Sources:** port kit §8.2–§8.3, §8.1 habit scenario; architecture §4.3, §7, §8 step 5; surfaces §5, §11 `tpl.code.habit`.

---

## Goal

Harden harness honesty (disk acceptance over log theater) and land the multi-job code path: recon → edit → test for a CLI habit tracker with pytest-green acceptance.

---

## Checkboxes

- [ ] Complete `evaluate_run` / `session_successful` per port kit §8.3
  - [ ] Disk acceptance can pass without `final_report`
  - [ ] Do **not** fail solely because `run_status=failed` if disk OK
  - [ ] Drop scorecard noise like “finish_task not observed” when `code_ok`
- [ ] Habit acceptance checker: expected files + pytest green
  - [ ] `habit.py`, `tests/test_habit.py`, `README.md`
  - [ ] Acceptance flag `habit_tracker: True` (or explicit file/pytest keys)
- [ ] Template `tpl.code.habit`: `code_recon` → `code_edit` → `code_test`
- [ ] `run_command` allowlisted for pytest (and only safe commands)
- [ ] Scenario `habit_tracker` in harness
- [ ] Gate tracks habit runs (report 3/3); document as code-reliability bar
- [ ] Metrics logging: worker tokens ≪ manager tokens; parse failure rate visible
- [ ] Optional: `manager_grades_failure` scenario green

---

## Files

| Path | Action |
|------|--------|
| `lacerta/harness/evaluate.py` | Honest evaluate contracts |
| `lacerta/harness/scenarios.py` | `habit_tracker` |
| `lacerta/harness/acceptance_habit.py` | Habit-specific checks |
| `lacerta/core/routers/code.py` | `tpl.code.habit` |
| `lacerta/workers/code_tools.py` | Harden `run_command` allowlist |
| `tests/test_evaluate_honesty.py` | Log theater must not override disk |
| `tests/test_habit_acceptance.py` | Synthetic project fixtures |

---

## Tests

```bash
pytest tests/test_evaluate_honesty.py tests/test_habit_acceptance.py -q
./scripts/gate.sh habit_tracker --runs 3
```

---

## Harness command

```bash
./scripts/gate.sh habit_tracker --runs 3
```

**Pass criteria:** 3/3 (or documented tracked rate) with files present and pytest green. Smoke + learn scenarios remain green (no regressions).

---

## Architecture PR checklist

- [ ] Harness before “reliable” claims
- [ ] Disk is SoT for code
- [ ] No heal towers as strategy
- [ ] Manager still tool-less
- [ ] Templates drive habit multi-job (no free decompose required)
- [ ] No MCP/Remote

---

## Out of scope

ResearchWorker, WritingWorker, GUI, LLM decompose.
