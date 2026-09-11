# Phase V1.35 — Shared corpus & multi-pass index

**Status:** planned  
**Depends on:** V1.3 (course paths / learn JobTypes); V1.1 attachments UX helpful but not required for headless  
**Exit:** Shared corpus layout + multi-pass index recipe + retrieve capability; learn textbook fixture harness green; manager never holds chunk bodies  

**Sources:** [architecture-v1.md](../architecture-v1.md) §4.3; [lacerta-surfaces-and-recipes.md](../../lacerta-surfaces-and-recipes.md) §6.7 / §6.10; storage module sketch.

---

## Goal

Make material larger than the model context first-class: ingest → multi-pass digest → on-disk index → top-k retrieve by ephemeral workers. One corpus subsystem serves **learn** (textbook → tutor/syllabus) and prepares **research** (V1.4 bulk upload).

---

## Checkboxes

### Layout & contracts

- [ ] `storage/corpus` (or equivalent): paths for `corpus.json`, `sources/`, `chunks/`, `map`/`toc`, `index/`
- [ ] `corpus.json` fields: `corpus_id`, `status`, source fingerprints, chunk_count, index_backend (`none` | `keyword` | `embeddings`), stale flag
- [ ] Course binding: learn course may reference `corpus_id` (under course tree or shared corpora root)
- [ ] JobTypes / templates: e.g. `learn_index_corpus` (or recipe under existing learn allowlist); archive chat uses retrieve

### Multi-pass capabilities (worker-side only)

- [ ] `corpus.extract` — PDF/text → page/section units (Python; no LLM required)
- [ ] `corpus.chunk` — structure-aware or fixed chunks + stable ids + page/heading metadata
- [ ] `corpus.map` — multi-pass TOC / coarse chapter summaries (small windows; optional LLM)
- [ ] `corpus.embed` — offline embeddings preferred; honest skip → keyword backend
- [ ] `corpus.retrieve` — query → top-k chunks; caps in Python (`top_k`, `max_chars`)
- [ ] Recipe `corpus.index_sources`: extract → chunk → map → embed → mark complete
- [ ] Freshness: re-index when source hash changes

### Learn reality check

- [ ] GUI or CLI path: attach textbook/notes → run index job → `corpus.json` complete
- [ ] `learn_tutor_turn` and/or `learn_archive_chat` inject **retrieved** chunks only (not full book)
- [ ] Optional: syllabus propose may use map + sampled chunks instead of full ingest concat
- [ ] Citations in grounded replies (chunk id / page / source)

### Honesty

- [ ] Harness: fixture mini-book with a planted fact → index → retrieve returns that fact → job `ok`
- [ ] Manager checklist: no chunk text in manager prompts; only `corpus_id` + plan
- [ ] No second RAG orchestrator; no CodeWorker FS toolkit on corpus jobs

---

## Files (expected)

| Path | Action |
|------|--------|
| `lacerta/storage/corpus.py` (and/or package) | Paths, fingerprints, read/write `corpus.json` |
| `lacerta/workers/corpus/` or shared caps under learn | extract/chunk/map/embed/retrieve |
| `lacerta/workers/learn/*` | Bind course ↔ corpus; tutor/archive retrieve |
| `lacerta/core/jobs.py` / routers / allowlists | JobTypes + templates as needed |
| `lacerta/gui/*` | Upload → index affordance on learn (thin) |
| `lacerta/harness/scenarios.py` | `learn_corpus_retrieve` (name TBD) |
| `tests/` | Corpus unit + harness wiring |

---

## Tests

```bash
pytest tests/ -q -k corpus
./scripts/gate.sh learn_corpus_retrieve --runs 1   # once scenario lands
./scripts/gate.sh learn_syllabus_files --runs 1    # no regression
```

---

## Architecture PR checklist

- [ ] One shared corpus subsystem
- [ ] Manager does not hold chunk bodies / embeddings
- [ ] Limits in Python
- [ ] Disk (`corpus.json` + chunks) is SoT
- [ ] Offline embeddings default / no surprise downloads
- [ ] User-supplied files only (no paywall scrape)

---

## Out of scope

- Research bulk wire-up (V1.4 consumes this API)
- Cloud embedding providers as default
- Cross-course analytics, full quiz generator UI
- MCP-backed vector DBs
