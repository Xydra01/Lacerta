# Phase V1.3 — Learn depth

**Status:** done  
**Depends on:** V1.1 (GUI shell); L3 syllabus green  
**Exit:** Tutor and assessment (and archive-chat stub) runnable via manager; GUI can browse course/syllabus artifacts; course tree reserves corpus paths for V1.35  

**Sources:** architecture-v1 §4.2–§4.3; surfaces learn JobTypes; port kit recipes.

---

## Goal

Move learn beyond syllabus-build-only: ship recipe paths for tutor / assessment / archive chat and surface them in the GUI without forking a learn engine. Prepare the **course ↔ corpus** binding so V1.35 can index textbooks without a layout rewrite.

---

## Checkboxes

- [x] Recipes + worker dispatch for `learn_tutor_turn`, `learn_assessment` (archive chat may be stubbed but typed)
- [x] Templates or GUI mode switch: syllabus_files · tutor · assessment
- [x] GUI: show syllabus/course paths after syllabus run; basic node list from `syllabus.json` (read-only)
- [x] **Corpus path reservation:** course layout documents `corpus/` (or `corpus_id` pointer); empty/`status=pending` OK — no full indexer required yet
- [x] Tutor/assessment may still use short notes/syllabus context; do **not** concat entire textbook attachments into the manager
- [x] Harness or unit: assessment/tutor produces structured artifact or honest failure
- [x] Allowlist unchanged unless new JobTypes already present
- [x] No CodeWorker FS toolkit on learn jobs

---

## Files (expected)

| Path | Action |
|------|--------|
| `lacerta/workers/learn/*` | Tutor / assessment capabilities |
| `lacerta/workers/learn/storage.py` | Course paths + optional corpus dir helpers |
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

- [x] Learn remains recipe runner
- [x] syllabus.json SoT
- [x] No dual orchestrator
- [x] No manager-held full-file ingest for large attachments

---

## Out of scope

Full placement diagnostic, cross-course analytics, web syllabus as default.  
**Multi-pass extract/chunk/embed/retrieve** → [V1.35](phase-V1.35.md).
