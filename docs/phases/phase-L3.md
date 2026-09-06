# Phase L3 — LearnWorker + syllabus recipes + structure gate

**Status:** done  
**Depends on:** L2 exit (manager spawns CodeWorker)  
**Exit:** `learn_syllabus_files` green  

**Sources:** surfaces §6 (full); port kit §8.1 learn scenario, §10; architecture §4.1 #9, §8 step 4.

---

## Goal

Ship Learn as the **second** surface: capability registry + recipe runner, syllabus-from-files recipe, Python structure gate (≥8 nodes, ≥5 sub-units), and disk-honest harness acceptance (`syllabus.json` + active course).

---

## Checkboxes

- [x] Capability primitives (port kit §10 + surfaces §10)
- [x] Learn storage layout under `instances/{instance_id}/learn/courses/{course_id}/`
- [x] Implement learn capabilities (ingest, write_syllabus, finalize; gather/assessments stubbed)
- [x] Recipes: `learn.syllabus_from_files`; web recipe registered (gather stub)
- [x] LearnWorker via recipe runner
- [x] Manager template `tpl.learn.syllabus_files`
- [x] Harness scenario `learn_syllabus_files` + shallow reject unit test

**Verified:** pytest green; `learn_syllabus_files` 1/1; smoke regression 1/1.

---

## Out of scope

Full placement diagnostic UI, cross-course analytics, slides, research/writing surfaces, habit_tracker.
