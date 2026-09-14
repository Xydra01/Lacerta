# Phase V1.4 — Research & writing depth

**Status:** planned  
**Depends on:** V1.1 (attachments UX); L5/L6 green; **V1.35** for bulk-corpus path (small attachments may still use offline ingest)  
**Exit:** `writing.from_sources` and research-with-attachments are first-class in GUI; bounded web gather is either real or honestly stubbed; large attachment sets use shared corpus retrieve instead of full-text concat  

**Sources:** architecture-v1 §4.2–§4.3; `writing.from_sources`; `research.gather_web_sources`; phase-V1.35.

---

## Goal

Deepen research/writing beyond single offline/short paths: sources in, deliverables out, optional bounded web—without manager-held web tools. When uploads exceed a Python size/count threshold, research **indexes via shared corpus** and retrieves per section/query (same primitive as learn textbooks).

---

## Checkboxes

- [ ] GUI: writing mode `short` vs `from_sources` (`tpl` or recipe_id via `write_from_sources`)
- [ ] Research: attachments required warning when list empty; preview report.md
- [ ] Implement or replace `gather_web_sources` stub with **bounded** fetch (domain allowlist / max pages)—worker-side only
- [ ] Template or flag for research offline vs light-web (keep `research_local` default)
- [ ] **Bulk path:** if attachment bytes/count over threshold → `corpus.index_sources` then retrieve-for-outline / per-section synthesize (not `ingest_offline` full concat)
- [ ] Small fixtures may keep classic `research.ingest_offline` for back-compat
- [ ] Harness: writing_from_sources or extend writing_short; research with fixture attachments still green; optional `research_corpus_bulk` when ready
- [ ] Document advance_when / multi-section pattern for longer docs (Python-enforced)

---

## Files (expected)

| Path | Action |
|------|--------|
| `lacerta/workers/research/capabilities.py` | Bounded gather; corpus-aware synthesize |
| `lacerta/workers/writing/*` | from_sources polish |
| `lacerta/storage/corpus*` | Task-scoped or shared corpus root for research |
| `lacerta/core/routers/*` | Templates if needed |
| `lacerta/gui/*` | Modes + attachments |
| `lacerta/harness/scenarios.py` | New/extended scenarios |

---

## Tests

```bash
./scripts/gate.sh research_local --runs 1
./scripts/gate.sh writing_short --runs 1
pytest tests/test_writing_*.py tests/test_research_*.py -q
# if landed:
# ./scripts/gate.sh research_corpus_bulk --runs 1
```

---

## Architecture PR checklist

- [ ] Manager still cannot call web_search
- [ ] Caps in Python (max pages/bytes, top_k)
- [ ] Recipes remain primary for these surfaces
- [ ] No duplicate research-only vector stack — reuse shared corpus

---

## Out of scope

Full browser agent, unrestricted crawl, MCP external search servers (L10 deferred).
