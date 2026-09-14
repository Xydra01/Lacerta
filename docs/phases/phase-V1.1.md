# Phase V1.1 — GUI product shell

**Status:** done  
**Depends on:** V1.0  
**Exit:** GUI supports attachments, deliverable viewing, and recent-run history without becoming a second orchestrator  

**Sources:** [architecture-v1.md](../architecture-v1.md) §4.1; phase-L8.md.

---

## Goal

Turn the L8 stub into a usable local shell: surface-appropriate inputs, visible artifacts, and a short run history—still calling only `run_manager`.

---

## Checkboxes

- [x] Research (and writing-from-sources prep): **attachment picker / path list** in UI; POST `/api/run` passes `attachments`
- [x] **Deliverable viewer**: list artifact paths; `GET` bounded file preview (size-capped text)
- [x] **Run history**: last N runs in-process (status, surface, goal snippet, artifacts)—no durable DB required
- [x] Surface-specific form hints (placeholders already present; add learn course ids, writing title if cheap)
- [x] Keep generation lock; reject concurrent runs with 409
- [x] Headless tests for `/api/surfaces`, `/api/run` wiring (mock runner/client where needed)
- [x] Update `lacerta/gui/README.md` manual smoke

---

## Files (expected)

| Path | Action |
|------|--------|
| `lacerta/gui/static/*` | Attachments UI, history, preview |
| `lacerta/gui/server.py` | Preview + history endpoints |
| `lacerta/gui/surfaces.py` | Input helpers |
| `tests/test_gui_api.py` | Headless API tests |

---

## Tests

```bash
pytest tests/test_gui_surface_wiring.py tests/test_gui_api.py -q
LACERTA_LLM_DECOMPOSE=0 ./scripts/gate.sh writing_short --runs 1
```

---

## Architecture PR checklist

- [x] GUI still only calls manager (no FS tools in UI process beyond reading deliverables for preview)
- [x] Preview is bounded (max bytes / text only)
- [x] No MCP/Remote
- [x] Disk remains SoT

---

## Out of scope

Habit mode UI (V1.2), learn tutor (V1.3), corpus index (V1.35), web gather (V1.4), multi-turn chat (V1.5).
