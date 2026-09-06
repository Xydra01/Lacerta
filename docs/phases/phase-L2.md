# Phase L2 — Manager + surface allowlists + code templates

**Status:** done  
**Depends on:** L1 exit (`smoke_write_file` 3/3)  
**Exit:** Manager spawns CodeWorker (template path)  

**Sources:** architecture §3.1–§3.3, §3.5; surfaces §3, §5, §11; port kit §0.5, §1.

---

## Goal

Introduce the single stateful Manager that only `spawn_worker` / `finish_task` / `fail_task`, rejects JobTypes outside the current Surface allowlist, and drives code goals via Python MacroTemplates (not free LLM decompose).

---

## Checkboxes

- [x] Implement `lacerta/core/manager.py` deterministic loop (architecture §3.3)
  - [x] `MacroState(surface, goal, plan=[], results=[])`
  - [x] Cap steps with `LACERTA_MANAGER_MAX_STEPS` (default 20)
  - [x] Apply `JobResult` summaries only (not full transcripts)
- [x] Manager tools **only:** `spawn_worker(JobSpec)`, `finish_task`, `fail_task`
- [x] Surface → JobType allowlists (surfaces §3)
  - [x] chat: `chat_answer`, `research_light`
  - [x] code: `code_recon`, `code_edit`, `code_test`
  - [x] learn / research / writing enums registered; reject cross-surface jobs
- [x] Python routers under `lacerta/core/routers/`
  - [x] `tpl.code.smoke` → one `code_edit` JobSpec
  - [x] Optional stub templates for other surfaces (no-op or NotImplemented until their phase)
- [x] `validate(job)`: Pydantic + surface allowlist before spawn
- [x] Wire `worker_runtime.run(job)` for `code_*` JobTypes; dispatch stub for others
- [x] Fast path: one worker for whole smoke goal (avoid unnecessary multi-job)
- [x] Scenario/path: gate smoke goes **through manager** (not calling worker directly)
- [x] Unit test: manager rejects e.g. `research_local` while `surface=code`
- [x] Unit test: manager finishes when acceptance met / fails cleanly on hard worker failure

---

## Files

| Path | Action |
|------|--------|
| `lacerta/core/manager.py` | Implement |
| `lacerta/core/routers/code.py` | `tpl.code.smoke` (+ stub habit) |
| `lacerta/core/routers/__init__.py` | Registry of templates by surface |
| `lacerta/core/allowlists.py` | Surface → JobType map |
| `tests/test_manager_allowlist.py` | Create |
| `tests/test_manager_smoke.py` | Manager → CodeWorker path |
| `lacerta/harness/scenarios.py` | Ensure smoke uses surface `code` + manager |

---

## Tests

```bash
pytest tests/test_manager_allowlist.py tests/test_manager_smoke.py -q
./scripts/gate.sh smoke_write_file --runs 3   # still 3/3 via manager
```

---

## Harness command

```bash
./scripts/gate.sh smoke_write_file --runs 3
```

**Pass criteria:** Smoke still 3/3; job log / metrics show manager spawn of CodeWorker. Scenario `manager_grades_failure` (optional this phase): worker fails; manager stops cleanly.

**Verified:** 3/3 via manager with `OLLAMA_MODEL=lacerta:latest` (logs show `manager status=finished steps=2 jobs=[smoke-…]`).

---

## Architecture PR checklist

- [x] One manager for all surfaces (no per-surface OS)
- [x] Manager cannot call FS / shell / web tools
- [x] Templates before free LLM decompose (LLM path off or stubbed)
- [x] Surfaces = UX + templates + allowlists only
- [x] Workers remain ephemeral
- [x] No MCP/Remote

---

## Out of scope

LLM manager decompose (L7), LearnWorker (L3), habit full acceptance (L4), GUI.
