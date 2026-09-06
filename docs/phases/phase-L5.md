# Phase L5 — ResearchWorker

**Status:** done  
**Depends on:** L4 exit (`habit_tracker` tracked)  
**Exit:** `research_local` green  

**Sources:** surfaces §7; port kit §8.1 `research_local`, §10; architecture §8 step 6.

---

## Goal

Ship Research as a recipe-runner surface: offline notes → synthesis → deliverable on disk, with SourceRegistry ready for web recipes and harness min-char acceptance.

---

## Checkboxes

- [x] Artifacts under `tasks/<task_id>/research/` (`notes.md`, `report.md`)
- [x] `SourceRegistry` / `SourceRecord`
- [x] Research capabilities (ingest/synthesize/finalize; gather_web stubbed; light stub)
- [x] Recipes: `research.offline` (required); full_web / light registered
- [x] JobTypes: `research_local` wired; web/light via worker when selected
- [x] Manager template `tpl.research.offline` registered
- [x] Surface allowlist for research JobTypes
- [x] Web primitives only inside gather stub — never on manager
- [x] Harness `research_local`: offline; deliverable ≥ 400 chars
- [ ] Optional `research_web_mini` (deferred — gather stubbed)
- [x] Evaluate: `min_deliverable_chars` on report path

**Verified:** pytest green; `research_local` 1/1; learn/habit/smoke regressions.

---

## Out of scope

WritingWorker, GUI, MCP client for web.
