# Phase L9 — MCP host (stdio meta-tools → manager)

**Status:** planned  
**Depends on:** **L1–L6 harness-green** (hard gate); L8 recommended  
**Exit:** Cursor runs smoke via `lacerta_run_scenario`  

**Sources:** architecture §9.1, §9.3–§9.4; surfaces §13; port kit §12 L9.

---

## Goal

Expose Lacerta as an MCP **host** with a small meta-tool catalog that calls the **same manager** and harness evaluate path — so Cursor (or any MCP client) can run surfaces and scenarios without importing every FS tool.

---

## Checkboxes

- [ ] Confirm L1–L6 gates still green before starting
- [ ] `lacerta/integrations/mcp_host.py` (stdio transport)
- [ ] Meta-tool catalog (~8–12 tools) — roles from architecture §9.1:
  - [ ] `lacerta_health`
  - [ ] `lacerta_list_instances`
  - [ ] `lacerta_run_surface`
  - [ ] `lacerta_get_job_status`
  - [ ] `lacerta_get_run_metrics`
  - [ ] `lacerta_read_deliverable` (bounded)
  - [ ] `lacerta_list_scenarios` / `lacerta_run_scenario` / `lacerta_evaluate_run`
  - [ ] `lacerta_release_generation_lock`
- [ ] Host tools call same manager as GUI/CLI — **no** reimplemented LoopEngine
- [ ] `lacerta_run_scenario` / evaluate use **same** `evaluate_run` as harness
- [ ] Do **not** expose raw CodeWorker FS tools to Cursor
- [ ] Document Cursor MCP config snippet for Lacerta stdio server
- [ ] Generation lock shared with GUI if both can run
- [ ] Manual: from Cursor, `lacerta_run_scenario` smoke → disk acceptance pass

---

## Files

| Path | Action |
|------|--------|
| `lacerta/integrations/mcp_host.py` | Implement |
| `lacerta/integrations/__init__.py` | Package |
| `docs/` MCP host setup notes | Create or README section |
| `tests/test_mcp_host_tools.py` | Tool routing → manager mocks |

---

## Tests

```bash
pytest tests/test_mcp_host_tools.py -q
./scripts/gate.sh smoke_write_file --runs 1
# Manual: MCP client invokes lacerta_run_scenario smoke_write_file
```

---

## Harness command

```bash
./scripts/gate.sh smoke_write_file --runs 1
# Plus MCP-path run of the same scenario; acceptance must match CLI
```

**Pass criteria:** Cursor (or mcp inspector) runs smoke via `lacerta_run_scenario` and evaluate matches harness honesty.

---

## Architecture PR checklist

- [ ] Not inventing a parallel brain
- [ ] Not blocking core ship order (core already shipped)
- [ ] Small host catalog — no FS tool dump
- [ ] Same evaluate_run for MCP runs
- [ ] Manager still tool-less regarding project FS
- [ ] No public Remote yet (that’s L11+)

---

## Out of scope

MCP client bridge (L10), Remote companion (L11), SSE mount (L12).
