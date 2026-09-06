# Phase L1 — CodeWorker + FS tools + schema

**Status:** done  
**Depends on:** L0 exit (`pytest` green)  
**Exit:** `smoke_write_file` **3/3**  

**Sources:** port kit §2–§8.1, §8.2, §8.4; architecture §3.4, §7, §8 step 2.

---

## Goal

Ship an ephemeral CodeWorker tool loop that can create a file on disk under project root, with Ollama JSON schema transforms, FS tool registry, and honest disk acceptance for the smoke scenario.

---

## Checkboxes

- [x] Implement FS tools in `lacerta/workers/code_tools.py` (port kit §3)
  - [x] `read_file`, `write_file`, `search_replace`, `list_dir`, `grep`, `find_files`
  - [x] Optional stub/`run_command` allowlist (full use in L4)
  - [x] Project-root guard + write size cap (`LACERTA_MAX_WRITE_CHARS`)
  - [x] `search_replace` requires exactly one match
  - [x] Grep output contract: `rel/path.py:12: content…` (port kit §4)
- [x] `CODE_TOOL_REGISTRY` + `get_active_tools` (≤4 tools per JobSpec)
- [x] Ollama schema prep: inline `$defs`, `additionalProperties: false`, optional strip descriptions (port kit §6)
- [x] `build_worker_json_schema` — flat tool-name enums, max 1 tool/turn
- [x] `run_worker_session` in `worker_runtime.py` (port kit §2)
  - [x] Fresh messages every job; purge caller-side after `JobResult`
  - [x] `max_turns` in Python (`LACERTA_WORKER_MAX_TURNS`, clamp 1–16)
  - [x] One tool per turn; truncate tool outputs
  - [x] Repeat-path OS block for `write_file` / `search_replace`
- [x] Worker prompt rules: JSON + reasoning + one tool; `final_report` when done
- [x] Session metrics → `logs/worker-sessions.jsonl` (port kit §7)
- [x] Scenario `smoke_write_file` in harness (port kit §8.1)
- [x] Disk `check_acceptance` for `check_file_glob` + `file_contains` (port kit §8.2)
- [x] Gate runs smoke with `--runs 3`; require 3/3 pass
- [x] Model tier stub optional (`check_worker_model`) — warn only if needed

---

## Files

| Path | Action |
|------|--------|
| `lacerta/workers/code_tools.py` | Implement |
| `lacerta/core/worker_runtime.py` | Implement tool loop |
| `lacerta/core/schema.py` (or under workers) | Ollama schema helpers |
| `lacerta/harness/scenarios.py` | Add `smoke_write_file` |
| `lacerta/harness/evaluate.py` | Disk acceptance + `session_successful` |
| `lacerta/harness/gate.py` | Run smoke N times |
| `scripts/gate.sh` | Export `LACERTA_DATA_ROOT`, invoke gate |
| `tests/test_code_tools.py` | Unit: root guard, write cap, search_replace uniqueness, grep shape |
| `tests/test_worker_schema.py` | Schema transforms / parse_tool_turn |

---

## Tests

```bash
pytest tests/test_code_tools.py tests/test_worker_schema.py -q
```

Manual/integration (needs Ollama + configured model):

```bash
./scripts/gate.sh smoke_write_file --runs 3
```

---

## Harness command

```bash
export LACERTA_DATA_ROOT="${LACERTA_DATA_ROOT:-$REPO_ROOT}"
export OLLAMA_MODEL="${OLLAMA_MODEL:-lacerta:latest}"
./scripts/gate.sh smoke_write_file --runs 3
```

**Pass criteria:** 3/3 runs create a file matching `**/harness_smoke.py` containing `HARNESS_OK`. Do not fail solely on missing `finish_task` log lines if disk acceptance passed.

**Verified:** 3/3 with `OLLAMA_MODEL=aquila:latest` (no `lacerta:latest` on this host).

---

## Architecture PR checklist

- [x] Code uses tool loop — **not** capability FSM / “dev recipes”
- [x] Manager still has no FS tools (manager may remain stub)
- [x] Worker context purged after job
- [x] `max_turns` enforced in Python
- [x] Disk acceptance is source of truth for smoke
- [x] No second orchestrator
- [x] No MCP/Remote

---

## Out of scope

Manager templates, Learn/Research/Writing, habit_tracker full gate, GUI.
