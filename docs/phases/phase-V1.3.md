# Phase V1.3 — Learn depth

**Status:** planned  
**Depends on:** V1.1 (GUI shell); L3 syllabus green  
**Exit:** Tutor and assessment (and archive-chat stub) runnable via manager; GUI can browse course/syllabus artifacts  

**Sources:** architecture-v1 §4.2; surfaces learn JobTypes; port kit recipes.

---

## Goal

Move learn beyond syllabus-build-only: ship recipe paths for tutor / assessment / archive chat and surface them in the GUI without forking a learn engine.

---

## Checkboxes

- [ ] Recipes + worker dispatch for `learn_tutor_turn`, `learn_assessment` (archive chat may be stubbed but typed)
- [ ] Templates or GUI mode switch: syllabus_files · tutor · assessment
- [ ] GUI: show syllabus/course paths after syllabus run; basic node list from `syllabus.json` (read-only)
- [ ] Harness or unit: assessment/tutor produces structured artifact or honest failure
- [ ] Allowlist unchanged unless new JobTypes already present
- [ ] No CodeWorker FS toolkit on learn jobs

---

## Files (expected)

| Path | Action |
|------|--------|
| `lacerta/workers/learn/*` | Tutor / assessment capabilities |
| `lacerta/core/routers/learn.py` | Additional templates |
| `lacerta/gui/*` | Learn mode + course view |
| `lacerta/harness/scenarios.py` | Optional new scenarios |
| `tests/` | Learn depth tests |

---

## Tests

```bash
pytest tests/test_learn_syllabus_gate.py tests/ -q -k learn
./scripts/gate.sh learn_syllabus_files --runs 1
```

---

## Architecture PR checklist

- [ ] Learn remains recipe runner
- [ ] syllabus.json SoT
- [ ] No dual orchestrator

---

## Out of scope

Full placement diagnostic, cross-course analytics, web syllabus as default.
