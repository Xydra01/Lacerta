# Phase L8 — Thin GUI (surface tabs + job log)

**Status:** done  
**Depends on:** L6 exit (L7 optional); core surfaces harness-green  
**Exit:** Thin GUI — surface tabs + job log; **no second OS**  

**Sources:** architecture §5 `gui/`, §8 step 8, §4.2 non-goals; surfaces §1, §9; port kit §12 L8.

---

## Goal

Ship a thin local UI that selects a task surface, launches goals through the **same manager**, and shows job activity / deliverable pointers — without forking orchestration into the frontend.

---

## Checkboxes

- [x] `lacerta/gui/` thin app (stack choice documented; keep small)
- [x] Surface switcher: chat | code | learn | research | writing
- [x] Opening a surface sets `surface=…` + default MacroTemplate + allowlist (no new engine)
- [x] Start run → manager; display job_id, JobType, ok/summary, artifacts
- [x] Job log / activity stream (summaries only, not full worker transcripts by default)
- [x] Chat: manager-local completion; optional spawn `research_light`
- [x] Learn/research/writing: show deliverable paths (syllabus, report, draft)
- [x] Code: status of last jobs; do not make canvas SoT for files (disk remains SoT)
- [x] Shared generation lock stub if needed for later MCP/Remote (optional prep)
- [x] No workflow GUI editor, persona calendar, or plan-review dialogs (v0 non-goals)
- [x] Manual smoke: each surface can launch a template job against local Ollama (documented in `lacerta/gui/README.md`)

---

## Files

| Path | Action |
|------|--------|
| `lacerta/gui/` | App package / entry |
| `lacerta/gui/README.md` | How to run |
| Thin API or in-process calls into `manager.py` | Same process preferred for v0 |
| `tests/test_gui_surface_wiring.py` | Surface → template wiring |

---

## Tests

```bash
pytest tests/test_gui_surface_wiring.py -q
./scripts/gate.sh smoke_write_file --runs 1  # CLI/harness unchanged
```

---

## Harness command

Harness remains CLI-first. GUI exit is manual:

1. Launch GUI (`python -m lacerta.gui`)
2. Run code smoke objective → file on disk  
3. Confirm job log shows manager spawn/finish  
4. Switch surface; confirm wrong JobTypes cannot be launched from UI

---

## Architecture PR checklist

- [x] GUI is not a second orchestrator / LoopEngine
- [x] Surfaces still templates + allowlists
- [x] Manager has no FS tools
- [x] Disk / syllabus.json remain SoT
- [x] No MCP/Remote blocking or replacing this thin client
- [x] Line budget: avoid dumping orchestration into UI modules

---

## Out of scope

MCP host/client, Remote PWA, workflow editors, multi-worker swarm UI.
