# Phase V1.5 — Chat continuity & v1 exit

**Status:** done  
**Depends on:** V1.1–V1.4 including **V1.35**; L8 chat path  
**Exit:** Multi-turn chat in GUI; v1 regression matrix green (incl. corpus retrieve gate); v1 declared done; MCP/Remote still deferred  

**Sources:** architecture-v1 §4.1–§4.3, §6; surfaces §9.

---

## Goal

Finish the local product loop: chat that remembers the session in the GUI, live-enough job log updates, and a documented v1 exit bar across surfaces.

---

## Checkboxes

- [x] Chat session: prior turns passed as context into `chat_answer` (client-sent history)
- [x] Optional light research still works with session context
- [x] Job log: polling while run in progress (stdlib `202` + `GET /api/runs/{id}`)
- [x] v1 regression matrix documented in README / architecture-v1:
  - [x] pytest green
  - [x] writing_short, research_local, learn_syllabus_files, habit_tracker (det), smoke (Ollama when up)
  - [x] learn_corpus_retrieve green — fixture book → index → cite
  - [x] GUI manual smoke checklist updated (incl. learn attach → index; multi-turn chat)
- [ ] Optional: chat may pass `corpus_id` for light grounded answers — **skipped** (learn/research cover corpus)
- [x] Mark architecture-v1 **v1 exit met** when matrix passes
- [x] Confirm L9–L12 remain deferred (no scope creep)

---

## Files (expected)

| Path | Action |
|------|--------|
| `lacerta/gui/*` | Session + polling |
| `lacerta/core/chat_local.py` | Multi-turn messages |
| `README.md` / `docs/architecture-v1.md` | Exit bar |
| `tests/test_gui_*.py` / `tests/test_chat_session.py` | Session + poll wiring |

---

## Tests

```bash
python -m pytest tests/ -q
LACERTA_HABIT_MODE=deterministic ./scripts/gate.sh habit_tracker --runs 1
./scripts/gate.sh writing_short --runs 1
./scripts/gate.sh research_local --runs 1
./scripts/gate.sh learn_syllabus_files --runs 1
./scripts/gate.sh learn_corpus_retrieve --runs 1
./scripts/gate.sh writing_from_sources --runs 1
./scripts/gate.sh research_corpus_bulk --runs 1
# if ollama healthy:
./scripts/gate.sh smoke_write_file --runs 1
```

---

## Architecture PR checklist

- [x] Chat still manager-local (no CodeWorker FS)
- [x] One manager
- [x] No MCP/Remote required for v1 exit

---

## Out of scope

Remote PWA chat stream (L11), MCP host tools (L9), chat corpus grounding.
