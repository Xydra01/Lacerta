# Phase L0 — Bootstrap + JobSpec/JobResult/Surface + gate stub

**Status:** done  
**Depends on:** none  
**Exit:** `pytest` green  

**Sources:** port kit §1, §12–§14; architecture §5–§6, §8 step 1.

---

## Goal

Stand up the Lacerta package skeleton, typed IPC contracts (`Surface`, `JobType`, `JobSpec`, `JobResult`), env defaults, and a no-op harness/gate stub so later phases have a place to land.

---

## Checkboxes

- [x] Create repo layout under `lacerta/` (package) + top-level `tests/`, `scripts/`, `docs/`
- [x] Add `pyproject.toml` / packaging so `python -m lacerta…` and `pytest` resolve
- [x] Implement `lacerta/core/jobs.py` with Pydantic models from port kit §1
- [x] Export `Surface` and `JobType` Literals exactly as enumerated
- [x] Add empty/stub modules: `manager.py`, `worker_runtime.py`, `routers/`, worker dirs, `harness/`, `storage/`
- [x] Add `lacerta/harness/gate.py` stub + `scripts/gate.sh` that invokes it
- [x] Wire `.env.example` with LACERTA_* / OLLAMA_* defaults (port kit §14)
- [x] Add README pointing at architecture + phase index
- [x] Unit tests for JobSpec/JobResult round-trip and JobType enum membership
- [x] `pytest` passes with zero failing tests

---

## Files

| Path | Action |
|------|--------|
| `pyproject.toml` | Create |
| `README.md` | Create |
| `.env.example` | Create |
| `lacerta/__init__.py` | Create |
| `lacerta/core/jobs.py` | Create — IPC types |
| `lacerta/core/manager.py` | Stub |
| `lacerta/core/worker_runtime.py` | Stub |
| `lacerta/core/routers/__init__.py` | Stub |
| `lacerta/workers/code_tools.py` | Stub |
| `lacerta/workers/learn/`, `research/`, `writing/` | Package stubs |
| `lacerta/harness/scenarios.py` | Stub dict or empty |
| `lacerta/harness/evaluate.py` | Stub |
| `lacerta/harness/gate.py` | Stub CLI entry |
| `lacerta/storage/` | Stub package |
| `scripts/gate.sh` | Create |
| `tests/test_jobs.py` | Create |

**Target layout (port kit §13):**

```text
lacerta/
  README.md
  docs/phases/
  lacerta/
    core/jobs.py
    core/worker_runtime.py
    core/manager.py
    core/routers/
    workers/…
    harness/{scenarios,evaluate,gate}.py
    storage/
  scripts/gate.sh
  tests/
```

---

## Tests

```bash
pytest tests/test_jobs.py -q
```

Cover at minimum:

- JobSpec defaults (`tools=[]`, `acceptance={}`, `max_turns=5`)
- JobResult `ok` / `error` fields
- Invalid / unknown fields rejected by Pydantic where configured

---

## Harness command

```bash
./scripts/gate.sh --help   # or: python -m lacerta.harness.gate --help
```

Gate may exit 0 with a “not implemented” message; it must not crash on import.

---

## Architecture PR checklist

- [x] No second orchestrator introduced
- [x] Manager has no FS/web/shell tools
- [x] Surfaces not forked into separate engines
- [x] No heal towers / coach personas
- [x] No MCP/Remote work in this phase
- [x] Contracts match port kit §1 (do not invent alternate JobType names)

---

## Out of scope

CodeWorker loop, Ollama calls, real scenarios, Learn recipes, GUI, MCP, Remote.
