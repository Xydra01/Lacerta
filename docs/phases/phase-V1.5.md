# Phase V1.5 — Chat continuity & v1 exit

**Status:** planned  
**Depends on:** V1.1–V1.4 (or V1.1 + parallel depth as available); L8 chat path  
**Exit:** Multi-turn chat in GUI; v1 regression matrix green; v1 declared done; MCP/Remote still deferred  

**Sources:** architecture-v1 §4.1–§4.2, §6; surfaces §9.

---

## Goal

Finish the local product loop: chat that remembers the session in the GUI, live-enough job log updates, and a documented v1 exit bar across surfaces.

---

## Checkboxes

- [ ] Chat session: prior turns passed as context into `chat_answer` (server-side session or client-sent history)
- [ ] Optional light research still works with session context
- [ ] Job log: polling or chunked status while run in progress (stdlib-friendly)
- [ ] v1 regression matrix documented in README / architecture-v1:
  - [ ] pytest green
  - [ ] writing_short, research_local, learn_syllabus_files, habit_tracker (det), smoke (Ollama)
  - [ ] GUI manual smoke checklist updated
- [ ] Mark architecture-v1 **v1 exit met** when matrix passes
- [ ] Confirm L9–L12 remain deferred (no scope creep)

---

## Files (expected)

| Path | Action |
|------|--------|
| `lacerta/gui/*` | Session + polling |
| `lacerta/core/chat_local.py` | Multi-turn messages |
| `README.md` / `docs/architecture-v1.md` | Exit bar |
| `tests/test_gui_*.py` | Session wiring |

---

## Tests

```bash
python -m pytest tests/ -q
LACERTA_HABIT_MODE=deterministic ./scripts/gate.sh habit_tracker --runs 1
./scripts/gate.sh writing_short --runs 1
./scripts/gate.sh research_local --runs 1
./scripts/gate.sh learn_syllabus_files --runs 1
# smoke if Ollama up
```

---

## Architecture PR checklist

- [ ] Chat still manager-local (no CodeWorker FS)
- [ ] One manager
- [ ] No MCP/Remote required for v1 exit

---

## Out of scope

Remote PWA chat stream (L11), MCP host tools (L9).
