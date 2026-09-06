# Phase L7 — Optional LLM manager decompose (flagged)

**Status:** done  
**Depends on:** L6 exit (`writing_short` green); L1–L6 harness still green  
**Exit:** Templates still default; LLM decompose behind flag only  

**Sources:** architecture §3.3, §3.5–§3.6, §8 step 7; surfaces §11; port kit §0 do/don't.

---

## Goal

Add an optional LLM manager path that proposes typed `JobSpec`s when Python routers cannot handle a state — without replacing templates as the default, and without giving the manager worker tools.

---

## Checkboxes

- [x] Feature flag / env e.g. `LACERTA_LLM_DECOMPOSE=0` (default **off**)
- [x] `llm_manager.propose_job(state) -> JobSpec` only (typed; no narrative plan as SoT)
- [x] Still `validate(job)` + surface allowlist before spawn
- [x] Templates remain first: `if python_router.can_handle(state): … else: llm…`
- [x] Cap manager steps; refuse unbounded replan loops
- [x] Structured errors + optional respawn — no heal-tower prompt OS
- [x] Harness: with flag **off**, all existing scenarios unchanged
- [x] Harness or unit: with flag **on**, one non-template goal still produces valid JobSpecs and finishes or fails cleanly
- [x] Document that free decompose is rare and for mid-size local models must stay narrow

---

## Files

| Path | Action |
|------|--------|
| `lacerta/core/llm_manager.py` | Propose JobSpec only |
| `lacerta/core/manager.py` | Branch behind flag |
| `tests/test_llm_decompose_flag.py` | Default off; validate path |
| `docs/` or README note | Flag semantics |

---

## Tests

```bash
pytest tests/test_llm_decompose_flag.py -q
LACERTA_LLM_DECOMPOSE=0 ./scripts/gate.sh smoke_write_file --runs 1
# optional: LACERTA_LLM_DECOMPOSE=1 with a dedicated scenario
```

---

## Harness command

```bash
./scripts/gate.sh smoke_write_file --runs 1
./scripts/gate.sh learn_syllabus_files
# Templates must remain the path used by default scenarios
```

**Pass criteria:** Default gate behavior identical to L6. LLM path never becomes required for smoke/learn/research/writing templates.

**Note:** Free decompose is rare. For mid-size local models it must stay narrow (typed JobSpecs only, propose cap, templates first).

---

## Architecture PR checklist

- [x] Templates before free planning (default)
- [x] Manager still cannot call FS/web/shell
- [x] No second orchestrator path for “LLM mode”
- [x] No coach / heal towers
- [x] Workers still ephemeral
- [x] No MCP/Remote required for this phase

---

## Out of scope

GUI, MCP, Remote, changing recipe internals.
