# Phase V1.2 — Code checks & scenarios in GUI

**Status:** done  
**Depends on:** V1.1  
**Exit:** GUI can run a **named code check / premade scenario** (not a smoke|habit “mode” toggle); acceptance pass/fail is visible in the job log  

**Sources:** architecture-v1 §4.1–§4.2; `tpl.code.smoke` / `tpl.code.habit` (harness ids stay CLI-facing); habit gate.

---

## Goal

Give the Code surface an obvious **Test / Run check** path with human-readable scenario labels. Wire those to existing templates under the hood. Disk remains SoT; CLI keeps developer scenario names (`smoke_write_file`, `habit_tracker`).

**Do not** label the UI “smoke” or “habit mode.”

| GUI label | Template / acceptance (internal) |
|-----------|----------------------------------|
| Quick file check | `tpl.code.smoke` |
| Habit tracker (scaffold + tests) | `tpl.code.habit` + `habit_tracker` |

---

## Checkboxes

- [x] Code surface: **Test / scenario** control with plain labels (not smoke|habit modes)
- [x] Wire `scenario` (or `check_id`) → `tpl.code.smoke` / `tpl.code.habit` in `build_run_inputs`
- [x] Habit-tracker scenario uses deterministic scaffold by default (`LACERTA_HABIT_MODE=deterministic` documented for CLI)
- [x] Job log shows plan steps (when multi-step) and final acceptance pass/fail reason
- [x] Do **not** make the canvas/editor SoT
- [x] Headless test: `build_run_inputs(..., scenario="habit_tracker")` sets `tpl.code.habit`
- [x] Regression: `./scripts/gate.sh habit_tracker --runs 1` (deterministic CLI)

---

## Files (expected)

| Path | Action |
|------|--------|
| `lacerta/gui/surfaces.py` | Scenario → template_id + acceptance |
| `lacerta/gui/static/*` | Test / scenario control + acceptance row |
| `lacerta/gui/server.py` | Pass `scenario`; structured acceptance in response |
| `tests/test_gui_surface_wiring.py` | Scenario wiring |
| `tests/test_gui_api.py` | API + acceptance fields |

---

## Tests

```bash
pytest tests/test_gui_surface_wiring.py tests/test_gui_api.py -q
LACERTA_HABIT_MODE=deterministic ./scripts/gate.sh habit_tracker --runs 1
```

---

## Architecture PR checklist

- [x] Still one CodeWorker tool loop
- [x] Manager has no FS tools
- [x] Habit acceptance remains disk/pytest honest
- [x] GUI copy does not require users to learn harness jargon

---

## Out of scope

Full IDE, arbitrary multi-root workspaces, MCP tools in code jobs, renaming CLI gate scenario ids.
