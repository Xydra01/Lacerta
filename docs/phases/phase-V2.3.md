# Phase V2.3 — Mastery 0–5 + progress-aware Learn

**Status:** done  
**Depends on:** V2.0; V1.3 syllabus nodes; V2.2 tutor synthesize preferred  
**Exit:** Per-node mastery 0–5 on disk; tutor/assessment inputs respect mastery; user can take an on-the-spot mastery check for a section; early learners are not fed master-level items  

**Sources:** architecture-v2; attachment (progress-aware / mastery 0–5 / section mastery assessment).

---

## Goal

Learn must be **progress-aware**. If the user is early on a syllabus section (low mastery), do not present examples or assessments at higher mastery. Default new sections to mastery **0**; at **5**, treat the section as mastered for prompting and unlock assumptions.

---

## Checkboxes

### Disk SoT

- [x] `mastery.json` (or equivalent) under course: `{ nodes: { node_id: { tier: 0..5, updated_ts } } }`
- [x] Initialize missing nodes to `0` when syllabus activates / on first Learn open
- [x] Course browse API exposes mastery tiers with syllabus nodes
- [x] GUI course panel shows tier per node (plain text ok)

### Behavior

- [x] Tutor synthesize / deterministic prompts include **current node mastery** and instruction to match level (0–1 intro … 4–5 deep / edge cases)
- [x] Assessment generation selects difficulty from mastery (and optional target tier)
- [x] “Mastery check” action: generate short MC for a node at **current or next** tier; on pass, increment tier (cap 5); on fail, **leave tier unchanged**
- [x] At tier 5: tutor may assume section known; avoid re-teaching basics unless user asks

### Honesty

- [x] Unit: mastery read/write + bounds 0..5
- [x] Unit/harness: low-mastery path does not request “mastery 5” style items in generated assessment JSON when target is low
- [x] No silent mastery inflation without quiz / explicit user action

---

## Files (expected)

| Path | Action |
|------|--------|
| `lacerta/workers/learn/storage.py` | mastery paths |
| `lacerta/workers/learn/capabilities.py` | mastery-aware tutor/assessment |
| `lacerta/gui/server.py` / static | show tiers; mastery-check affordance |
| `tests/` | mastery unit + wiring |

---

## Tests

```bash
pytest tests/ -q -k mastery
pytest tests/test_learn_depth.py -q
```

---

## Architecture PR checklist

- [x] Mastery on disk is SoT (not only GUI memory)
- [x] Manager gets tier ints / node ids — not full quiz banks in manager prompts
- [x] Caps on assessment size in Python

---

## Out of scope

Full interactive quiz UX (V2.4 can consume mastery). Cross-course analytics. Spaced-repetition ML.
