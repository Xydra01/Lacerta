# Phase V1.2 — Code depth in GUI

**Status:** planned  
**Depends on:** V1.1  
**Exit:** GUI can run **smoke** or **habit** code templates; acceptance outcome visible in the job log  

**Sources:** architecture-v1 §4.2; `tpl.code.smoke` / `tpl.code.habit`; habit gate.

---

## Goal

Expose the real code reliability path (habit) alongside smoke, with honest acceptance feedback in the UI—disk still SoT.

---

## Checkboxes

- [ ] Code surface mode selector: `smoke` → `tpl.code.smoke` · `habit` → `tpl.code.habit`
- [ ] Habit runs use deterministic scaffold path by default (`LACERTA_HABIT_MODE=deterministic` documented)
- [ ] Job log shows plan steps (recon → edit → test) and final acceptance pass/fail reason
- [ ] Do **not** make the canvas/editor SoT; optional “open root in explorer” is OS-level only if added
- [ ] Headless test: `build_run_inputs(..., mode="habit")` sets `tpl.code.habit`
- [ ] Regression: `./scripts/gate.sh habit_tracker --runs 1` (deterministic)

---

## Files (expected)

| Path | Action |
|------|--------|
| `lacerta/gui/surfaces.py` | Code mode → template_id |
| `lacerta/gui/static/*` | Mode control |
| `tests/test_gui_surface_wiring.py` | Habit wiring |

---

## Tests

```bash
pytest tests/test_gui_surface_wiring.py -q
LACERTA_HABIT_MODE=deterministic ./scripts/gate.sh habit_tracker --runs 1
```

---

## Architecture PR checklist

- [ ] Still one CodeWorker tool loop
- [ ] Manager has no FS tools
- [ ] Habit acceptance remains disk/pytest honest

---

## Out of scope

Full IDE, arbitrary multi-root workspaces, MCP tools in code jobs.
