# Phase L8 — Thin GUI (surface tabs + job log)

**Status:** planned  
**Depends on:** L6 exit (L7 optional); core surfaces harness-green  
**Exit:** Thin GUI — surface tabs + job log; **no second OS**  

**Sources:** architecture §5 `gui/`, §8 step 8, §4.2 non-goals; surfaces §1, §9; port kit §12 L8.

---

## Goal

Ship a thin local UI that selects a task surface, launches goals through the **same manager**, and shows job activity / deliverable pointers — without forking orchestration into the frontend.

---

## Checkboxes

- [ ] `lacerta/gui/` thin app (stack choice documented; keep small)
- [ ] Surface switcher: chat | code | learn | research | writing
- [ ] Opening a surface sets `surface=…` + default MacroTemplate + allowlist (no new engine)
- [ ] Start run → manager; display job_id, JobType, ok/summary, artifacts
- [ ] Job log / activity stream (summaries only, not full worker transcripts by default)
- [ ] Chat: manager-local completion; optional spawn `research_light`
- [ ] Learn/research/writing: show deliverable paths (syllabus, report, draft)
- [ ] Code: status of last jobs; do not make canvas SoT for files (disk remains SoT)
- [ ] Shared generation lock stub if needed for later MCP/Remote (optional prep)
- [ ] No workflow GUI editor, persona calendar, or plan-review dialogs (v0 non-goals)
- [ ] Manual smoke: each surface can launch a template job against local Ollama

---

## Files

| Path | Action |
|------|--------|
| `lacerta/gui/` | App package / entry |
| `lacerta/gui/README.md` | How to run |
| Thin API or in-process calls into `manager.py` | Same process preferred for v0 |
| `tests/` smoke for GUI wiring if headless-testable | Optional |

---

## Tests

```bash
# Prefer headless unit tests for “surface → template id → allowlist” wiring
pytest tests/test_gui_surface_wiring.py -q   # if added
./scripts/gate.sh smoke_write_file --runs 1  # CLI/harness unchanged
```

---

## Harness command

Harness remains CLI-first. GUI exit is manual:

1. Launch GUI  
2. Run code smoke objective → file on disk  
3. Confirm job log shows manager spawn/finish  
4. Switch surface; confirm wrong JobTypes cannot be launched from UI

---

## Architecture PR checklist

- [ ] GUI is not a second orchestrator / LoopEngine
- [ ] Surfaces still templates + allowlists
- [ ] Manager has no FS tools
- [ ] Disk / syllabus.json remain SoT
- [ ] No MCP/Remote blocking or replacing this thin client
- [ ] Line budget: avoid dumping orchestration into UI modules

---

## Out of scope

MCP host/client, Remote PWA, workflow editors, multi-worker swarm UI.
