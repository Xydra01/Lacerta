# Phase V2.5 — Archive LLM chat + v2 exit

**Status:** done  
**Depends on:** V2.1 UI shell; V2.2 synthesize/retrieve; V2.35 structured ingest (STEM surrogates in corpus); V1.35 corpus  
**Exit:** Learn **Archive** submode: corpus-grounded LLM chat (humanized Q&A); v2 regression matrix green (incl. structured-corpus gate when present); architecture-v2 marked exit met; L9–L12 still deferred  

**Sources:** architecture-v2; attachment (Archive submode — chat with corpus via LLM, distinct from teaching Tutor).

---

## Goal

Ship a separate **Archive** Learn submode: user chats with the LLM about corpus content for their query — similar to today’s retrieve paste, but with LLM personalization. Tutor remains the **teaching** path; Archive is **exploratory Q&A**. Close v2 when UI declutter + tutor teach + mastery + practice + archive are harness-honest.

Archive/tutor answers about graphs/tables/equations rely on **V2.35 text surrogates** already in chunks — Archive does not re-run vision; it retrieves and synthesizes like Tutor.

---

## Checkboxes

### Archive mode

- [x] GUI Learn mode **Archive** (plain label): multi-turn messages + corpus retrieve → LLM reply + citations
- [x] Recipe / JobType reuse or thin `learn_archive_chat` upgrade (already typed in v1): must call retrieve then synthesize (not stub, not raw dump alone when Ollama up)
- [x] Compressed history same pattern as tutor (shared helper) with archive-specific system prompt (“answer from sources; cite; don’t invent”; use `[table]`/`[math]`/`[figure]` blocks when retrieved)
- [x] Without corpus complete: honest failure (“Index sources first”)
- [x] Deterministic fallback when Ollama down: retrieve paste labeled as such

### v2 exit bar

- [x] Document regression matrix in README / architecture-v2:
  - [x] pytest green
  - [x] prior v1 gates still green (`learn_syllabus_files`, `learn_corpus_retrieve`, writing/research as applicable)
  - [x] `learn_corpus_structured` (V2.35) green when extract extras installed
  - [x] new: grounded tutor / quiz / archive scenarios as landed in V2.2–V2.4
  - [x] GUI manual: decluttered Learn modes; tutor teach; mastery visible; MC practice; archive chat; STEM index note (tables/math)
- [x] Mark [architecture-v2.md](../architecture-v2.md) **v2 exit met**
- [x] Confirm L9–L12 remain deferred

---

## Files (expected)

| Path | Action |
|------|--------|
| `lacerta/workers/learn/capabilities.py` | Archive synthesize |
| `lacerta/gui/*` | Archive mode UX |
| `docs/architecture-v2.md` / `README.md` | Exit bar |
| `tests/` / harness | Archive + matrix |

---

## Tests

```bash
python -m pytest tests/ -q
./scripts/gate.sh learn_corpus_retrieve --runs 1
./scripts/gate.sh learn_syllabus_files --runs 1
# ./scripts/gate.sh learn_corpus_structured --runs 1
# ./scripts/gate.sh learn_archive_chat --runs 1
# plus V2.2–V2.4 gates once present
```

---

## Architecture PR checklist

- [x] Archive ≠ second OS; still recipe + allowlist
- [x] Tutor vs Archive prompts/roles clearly separated
- [x] Shared corpus only (structured surrogates stay in chunk text)
- [x] No MCP/Remote required for v2 exit

---

## Out of scope

Remote archive sync, multi-user courses, unrestricted web as archive backend. New figure-OCR pipelines after V2.35 — polish only if exit risk.
