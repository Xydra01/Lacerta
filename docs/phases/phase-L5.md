# Phase L5 — ResearchWorker

**Status:** planned  
**Depends on:** L4 exit (`habit_tracker` tracked)  
**Exit:** `research_local` green  

**Sources:** surfaces §7; port kit §8.1 `research_local`, §10; architecture §8 step 6.

---

## Goal

Ship Research as a recipe-runner surface: offline notes → synthesis → deliverable on disk, with SourceRegistry ready for web recipes and harness min-char acceptance.

---

## Checkboxes

- [ ] Artifacts under `tasks/<task_id>/research/` (`notes.md`, `report.md`)
- [ ] `SourceRegistry` / `SourceRecord` (surfaces §7.4)
- [ ] Research capabilities (surfaces §7.5)
  - [ ] `research.append_note`, `research.read_notes`
  - [ ] `research.ingest_offline` (fail if empty)
  - [ ] `research.synthesize_notes`
  - [ ] `research.compile_report` / `research.finalize_deliverable`
  - [ ] `research.gather_web_sources` (implement or stub; web scenario optional)
  - [ ] `research.light_web_context` stub OK for chat later
- [ ] Recipes: `research.offline` (required); `research.full_web`, `research.light` as available
- [ ] JobTypes: `research_local` (required); `research_web` / `research_light` wired when ready
- [ ] Manager template `tpl.research.offline`
- [ ] Surface allowlist: research JobTypes only on research surface
- [ ] Web primitives (`web_search`, `read_webpage`) **inside** gather capability only — never on manager
- [ ] Harness `research_local`: offline; deliverable ≥ 400 chars; no web
- [ ] Optional `research_web_mini` (≥ 800 chars) if web stack ready
- [ ] Evaluate: `min_deliverable_chars` on report path

---

## Files

| Path | Action |
|------|--------|
| `lacerta/workers/research/capabilities.py` | Handlers |
| `lacerta/workers/research/recipes.py` | RESEARCH_RECIPES |
| `lacerta/workers/research/sources.py` | SourceRegistry |
| `lacerta/workers/research/worker.py` | Recipe dispatch |
| `lacerta/core/routers/research.py` | Templates |
| `lacerta/harness/scenarios.py` | `research_local` (+ optional web) |
| `tests/test_research_offline.py` | Empty ingest fails; report length |
| `tests/fixtures/research/…` | Offline attachments |

---

## Tests

```bash
pytest tests/test_research_offline.py -q
./scripts/gate.sh research_local
```

---

## Harness command

```bash
./scripts/gate.sh research_local
```

**Pass criteria:** `report.md` (or configured deliverable) ≥ 400 characters; recipe ran offline; manager did not call web tools.

---

## Architecture PR checklist

- [ ] Research = recipes, not a forked engine
- [ ] Manager has no web_search
- [ ] Workers ephemeral; no worker↔worker chat
- [ ] Harness on disk deliverable
- [ ] Learn still ahead of writing in ship order (writing is L6)
- [ ] No MCP/Remote

---

## Out of scope

WritingWorker, GUI, MCP client for web (use native gather first).
