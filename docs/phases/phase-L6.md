# Phase L6 — WritingWorker

**Status:** done  
**Depends on:** L5 exit (`research_local` green)  
**Exit:** `writing_short` green  

**Sources:** surfaces §8; port kit §8.1 `writing_short`; architecture §8 step 6; surfaces §13 phase gate note.

---

## Goal

Ship Writing as a recipe-runner surface with WritingBrief, draft buffer → compiled markdown deliverable, Python-enforced `advance_when`, and harness acceptance (min chars + `#` title).

---

## Checkboxes

- [x] `WritingBrief` model (surfaces §8.1) — scope, tone, length_mode, `advance_when`
- [x] Artifacts: `tasks/<id>/writing/active_draft.json` + deliverable `.md`
- [x] Capabilities: ingest / init / draft_sections / read_outline / compile / finalize
- [x] Recipes: `writing.dynamic`, `writing.from_sources`
- [x] JobTypes: `write_draft`, `write_finalize`, `write_from_sources`
- [x] Compile rules: one `# Title`; sections as `## …`; strip duplicate `#` from bodies
- [x] `advance_when` enforced in **Python** (manager template or worker), not prompt milestones
- [x] Manager template `tpl.writing.short` → draft → finalize (or single recipe path)
- [x] Prefer multi-job section drafts for long docs (document pattern; short path for harness)
- [x] Surface allowlist for writing JobTypes
- [x] Harness `writing_short`: ≥ 300 chars; `#` title present
- [ ] Chat stub: manager-local `chat_answer` optional; no CodeWorker FS for chat — deferred (not required for exit)

---

## Files

| Path | Action |
|------|--------|
| `lacerta/workers/writing/brief.py` | WritingBrief |
| `lacerta/workers/writing/capabilities.py` | Handlers |
| `lacerta/workers/writing/recipes.py` | WRITING_RECIPES |
| `lacerta/workers/writing/worker.py` | Dispatch |
| `lacerta/core/routers/writing.py` | `tpl.writing.short` |
| `lacerta/core/routers/chat.py` | Optional `tpl.chat.plain` |
| `lacerta/harness/scenarios.py` | `writing_short` |
| `tests/test_writing_compile.py` | Title/section compile rules |
| `tests/test_writing_advance.py` | `advance_when` Python gate |

---

## Tests

```bash
pytest tests/test_writing_compile.py tests/test_writing_advance.py -q
./scripts/gate.sh writing_short
```

---

## Harness command

```bash
./scripts/gate.sh writing_short
```

**Pass criteria:** Deliverable ≥ 300 characters with a clear `#` title. L1–L5 scenarios still green.

**Phase gate:** Core surfaces L1–L6 are harness-honest. L7+ is separate; **no cascade CreatePlan for L7**. L9+ still blocked until L1–L6 remain green.

---

## Architecture PR checklist

- [x] Writing = recipes; one manager
- [x] Limits / advance rules in Python
- [x] No dual orchestrator
- [x] Harness scenario present
- [x] Do not start MCP/Remote until this phase (and L1–L5) stay green
- [x] Code still tool-loop; writing not using CodeWorker FS as primary path

---

## Out of scope

LLM decompose (L7), GUI (L8), MCP, Remote. Chat stub deferred.
