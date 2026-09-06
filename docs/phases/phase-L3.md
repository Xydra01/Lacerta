# Phase L3 — LearnWorker + syllabus recipes + structure gate

**Status:** planned  
**Depends on:** L2 exit (manager spawns CodeWorker)  
**Exit:** `learn_syllabus_files` green  

**Sources:** surfaces §6 (full); port kit §8.1 learn scenario, §10; architecture §4.1 #9, §8 step 4.

---

## Goal

Ship Learn as the **second** surface: capability registry + recipe runner, syllabus-from-files recipe, Python structure gate (≥8 nodes, ≥5 sub-units), and disk-honest harness acceptance (`syllabus.json` + active course).

---

## Checkboxes

- [ ] Capability primitives (port kit §10 + surfaces §10)
  - [ ] `CapabilityContext`, `CapabilityResult`, `CapabilitySpec`, `run_capability`
  - [ ] `Recipe` + `run_recipe` loop (fail-fast on first bad capability)
- [ ] Learn storage layout under `instances/{instance_id}/learn/courses/{course_id}/` (surfaces §6.2)
- [ ] Implement learn capabilities (surfaces §6.5)
  - [ ] `learn.ingest_course_materials`
  - [ ] `learn.write_syllabus` — **Python** gate ≥8 nodes / ≥5 with `parent_id`; one write per build
  - [ ] `learn.finalize_course` — require valid syllabus; set `status=active`
  - [ ] Stub or defer `learn.gather_topic_sources` / `learn.generate_assessments` if not needed for files path
- [ ] Recipes: `learn.syllabus_from_files` (required); `learn.syllabus_from_web` optional stub
- [ ] LearnWorker: JobTypes `learn_syllabus_files` (+ optional others) via recipe runner — **not** CodeWorker tool loop
- [ ] Manager template `tpl.learn.syllabus_files` → one `learn_syllabus_files` job
- [ ] Surface allowlist enforces learn JobTypes only on learn surface
- [ ] Internal LLM may *propose* syllabus JSON; validation stays in Python
- [ ] Harness scenario `learn_syllabus_files` + acceptance keys (surfaces §6.8)
- [ ] Unit/harness `learn_syllabus_shallow_reject`: shallow outline → `ok=False`
- [ ] Tutor / archive JobTypes: stub OK (full tutor/archive can land later within learn polish)

---

## Files

| Path | Action |
|------|--------|
| `lacerta/core/capabilities.py` | Shared registry + runners |
| `lacerta/workers/learn/capabilities.py` | Learn handlers |
| `lacerta/workers/learn/recipes.py` | LEARN_RECIPES |
| `lacerta/workers/learn/storage.py` | Paths for courses/syllabus |
| `lacerta/workers/learn/worker.py` | Recipe dispatch for learn JobTypes |
| `lacerta/core/routers/learn.py` | `tpl.learn.syllabus_files` |
| `lacerta/harness/scenarios.py` | `learn_syllabus_files`, shallow reject |
| `lacerta/harness/evaluate.py` | Syllabus structure + `course_active` |
| `tests/test_learn_syllabus_gate.py` | Shallow reject + structure |
| `tests/fixtures/…` | Minimal course materials for harness |

---

## Tests

```bash
pytest tests/test_learn_syllabus_gate.py -q
./scripts/gate.sh learn_syllabus_files --runs 1
```

---

## Harness command

```bash
./scripts/gate.sh learn_syllabus_files
```

**Pass criteria:**

- `syllabus.json` exists with ≥8 nodes and ≥5 with `parent_id`
- Course / syllabus status active (`course_active: True`)
- Shallow JSON rejected in unit or harness scenario
- Acceptance from **disk**, not “finalize observed in logs”

---

## Architecture PR checklist

- [ ] Learn is recipe runner — no separate Learn LoopEngine
- [ ] Learn not deferred behind research/writing
- [ ] Syllabus gates in Python
- [ ] Manager still has no FS/web tools (web gather only inside worker capability)
- [ ] No CodeWorker FS toolkit on tutor/archive
- [ ] One write of syllabus per build
- [ ] Harness scenario present
- [ ] No MCP/Remote

---

## Out of scope

Full placement diagnostic UI, cross-course analytics, slides, research/writing surfaces, habit_tracker.
