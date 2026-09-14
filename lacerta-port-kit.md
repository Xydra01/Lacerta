# Lacerta Port Kit — Code & Shared Kernels

**Purpose:** Implementation contracts for Lacerta.  
**Pair with:**
- [lacerta-supervisor-worker-viability.md](lacerta-supervisor-worker-viability.md) — architecture + do/don't  
- [lacerta-surfaces-and-recipes.md](lacerta-surfaces-and-recipes.md) — surfaces & recipes (**code → learn → research → writing**)

**How to use**

1. Read architecture (Supervisor–Worker + surfaces-as-UX).  
2. Read surfaces-and-recipes (learn/research/writing/chat contracts).  
3. Use **this** doc for CodeWorker, IPC, schema, harness honesty, capability registry.  
4. Create phase docs (§12) in the Lacerta repo and implement.

---

## 0. Do / don't (runtime)

| Do | Don't |
|----|-------|
| One manager; spawn/finish/fail only | Manager FS / web / shell tools |
| Surfaces = templates + allowlists | Forked orchestrator per surface |
| CodeWorker = tool loop | Code via capability FSM |
| Learn/research/writing = recipe runners | Worker↔worker chat |
| `max_turns` + syllabus gates in Python | Prompt-only “please stop” |
| Disk / syllabus.json acceptance in harness | Pass on log theater alone |
| Workers fresh + purged after JobResult | Shared forever worker context |
| Ship code then **learn** | Defer learn behind research/writing |
| Plan MCP + Remote as late phases | Block core on integrations; or rebuild a second brain for them |

---

## 0.5 Shape (summary)

| Layer | Role |
|-------|------|
| **Surface** (`chat` \| `code` \| `learn` \| `research` \| `writing`) | UX + MacroTemplate + JobType allowlist |
| **Manager** | `spawn_worker`, `finish_task`, `fail_task` only |
| **CodeWorker** | Tool loop (§2–§6) |
| **Learn / Research / Writing workers** | Recipe runners — surfaces doc |
| **Chat** | Manager-local; optional `research_light` |

**Modes choose the first JobSpec template; they never choose a different engine.**

---

## 1. IPC types (write first)

Put in `lacerta/core/jobs.py`:

```python
from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

Surface = Literal["chat", "code", "learn", "research", "writing"]

JobType = Literal[
    "code_edit",
    "code_test",
    "code_recon",
    "learn_syllabus_files",
    "learn_syllabus_web",
    "learn_assessment",
    "learn_tutor_turn",
    "learn_archive_chat",
    "learn_index_corpus",
    "research_local",
    "research_web",
    "research_light",
    "write_draft",
    "write_finalize",
    "write_from_sources",
    "chat_answer",
]

class JobSpec(BaseModel):
    job_id: str
    job_type: JobType
    objective: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    # CodeWorker: 2–4 tool names. Recipe workers: usually [].
    tools: list[str] = Field(default_factory=list)
    acceptance: dict[str, Any] = Field(default_factory=dict)
    max_turns: int = 5

class JobResult(BaseModel):
    job_id: str
    ok: bool
    summary: str
    artifacts: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
```

**Manager tools (only):** `spawn_worker(JobSpec)`, `finish_task`, `fail_task`.  
**Manager must:** reject JobTypes not allowed for the current `Surface` (surfaces doc §3).

---

## 2. Worker loop skeleton (CodeWorker)

**Lacerta home:** `lacerta/core/worker_runtime.py`  
**Applies to:** `code_*` JobTypes. Research/writing use recipe runners (surfaces doc §4–§6), not this loop.

Port the *shape*. Keep: max turns in Python, one tool/turn, metrics, truncate outputs, repeat-path guard with **tool names**. Drop capability→tool heal hacks.

```python
# Conceptual port — rename env vars to LACERTA_*

def _max_turns() -> int:
    raw = os.getenv("LACERTA_WORKER_MAX_TURNS", "5").strip()
    try:
        return max(1, min(16, int(raw)))
    except ValueError:
        return 5


def _block_tool_path_repeat(tool_name: str, path: str, prior_attempts: int) -> str | None:
    if tool_name not in ("write_file", "search_replace"):
        return None
    norm = (path or "").strip().replace("\\", "/")
    if not norm or prior_attempts < 2:
        return None
    if tool_name == "write_file":
        return (
            f"❌ OS BLOCK: `write_file` on `{norm}` repeated {prior_attempts + 1} times. "
            "Use `read_file`, `search_replace`, or set `final_report` if done."
        )
    return (
        f"❌ OS BLOCK: `{tool_name}` on `{norm}` repeated {prior_attempts + 1} times. "
        "Read with read_file, then unique search_replace."
    )


def run_worker_session(
    client,
    *,
    objective: str,
    tools_allowed: frozenset[str],
    registry: dict[str, dict],
    schema: dict,
    system_prompt: str,
    max_turns: int | None = None,
    cancel_check=None,
) -> tuple[str, dict]:
    """Fresh messages every job. Return (summary, metrics_dict). Purge caller-side."""
    metrics = {
        "turns": 0,
        "parse_failures": 0,
        "completed": False,
        "wall_s": 0.0,
    }
    started = time.monotonic()
    limit = max_turns or _max_turns()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": objective},
    ]
    tool_path_attempts: dict[str, int] = {}
    last_summary = ""
    completed = False

    for turn in range(1, limit + 1):
        metrics["turns"] = turn
        if cancel_check and cancel_check():
            break
        result = client.chat(
            messages,
            temperature=0.2,
            format=schema,
            stream=False,
            force_think_disabled=True,
        )
        raw = (
            str(result.get("message", {}).get("content", "") or "")
            if isinstance(result, dict)
            else str(result or "")
        )
        parsed = parse_tool_turn(raw, tools_allowed)  # implement with flat JSON schema
        if not parsed:
            metrics["parse_failures"] += 1
            messages.append({"role": "assistant", "content": raw or "{}"})
            messages.append({
                "role": "user",
                "content": (
                    "Tool Outputs:\n❌ Invalid JSON. Reply with reasoning + "
                    "one tool in tools[] or final_report."
                ),
            })
            continue

        messages.append({"role": "assistant", "content": json.dumps(parsed)})
        final_report = str(parsed.get("final_report") or "").strip()
        tools = parsed.get("tools") or []
        if not tools:
            if final_report:
                last_summary = final_report
                completed = True
                break
            messages.append({
                "role": "user",
                "content": "Tool Outputs:\n💡 Call a tool or set final_report.",
            })
            continue

        call = tools[0]
        name = str(call.get("name") or "").strip()
        args = dict(call.get("arguments") or {})
        path = str(args.get("path") or "").strip()
        path_key = f"{name}|{path}"
        prior = tool_path_attempts.get(path_key, 0) if path else 0
        if path:
            tool_path_attempts[path_key] = prior + 1
        block = _block_tool_path_repeat(name, path, prior)
        if block:
            tool_out = block
        elif name not in tools_allowed:
            tool_out = f"❌ Unknown/disallowed tool `{name}`."
        else:
            func = registry[name]["func"]
            tool_out = str(func(**{k: v for k, v in args.items() if k in inspect.signature(func).parameters}))

        tool_out = truncate_text(tool_out, tool_output_max_chars())
        messages.append({"role": "user", "content": f"Tool Outputs:\n{tool_out}"})

    metrics["completed"] = completed
    metrics["wall_s"] = round(time.monotonic() - started, 2)
    return last_summary or "Worker finished.", metrics
```

**Worker prompt rules:**

```text
Each turn: JSON with reasoning + exactly one tools[] entry (name + arguments).
When done: final_report and no tools.
Paths relative to PROJECT_ROOT. Read before edit. No multi-step plans. No capability IDs.
```

---

## 3. Filesystem tools (CodeWorker)

**Lacerta home:** `lacerta/workers/code_tools.py`  
**Port:** project-root guard, write size cap, direct disk write (no linter SYSTEM HINT novels), search_replace uniqueness, grep wrapper, find_files, list_dir.

```python
def _max_write_chars() -> int:
    raw = os.getenv("LACERTA_MAX_WRITE_CHARS", "8000").strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 8000


def _require_project_root() -> Path | str:
    root = get_project_root()  # Lacerta: resolve from JobSpec.inputs["root"]
    if not root:
        return "❌ OS BLOCK: No project root."
    return root


def write_file(path: str, content: str) -> str:
    block = _require_project_root()
    if isinstance(block, str):
        return block
    text = str(content)
    max_chars = _max_write_chars()
    if len(text) > max_chars:
        return f"❌ OS BLOCK: content {len(text)} chars (max {max_chars})."
    target = resolve_under_root(path, for_write=True)
    root = block.resolve()
    try:
        target.resolve().relative_to(root)
    except ValueError:
        return f"❌ Cannot write outside project ({root})."
    target.parent.mkdir(parents=True, exist_ok=True)
    if not text.endswith("\n") and target.suffix == ".py":
        text = text + "\n"
    target.write_text(text, encoding="utf-8")
    if target.suffix == ".py":
        import ast
        try:
            ast.parse(text)
        except SyntaxError as e:
            return f"✅ Wrote {path}, syntax error: {e.msg} (line {e.lineno}). Fix with search_replace."
    return f"✅ Successfully wrote {path}."


def search_replace(path: str, old_string: str, new_string: str) -> str:
    # Require exactly one match of old_string; else return clear error.
    ...


def read_file(path: str, start_line: int = 1, end_line: int = 0) -> str:
    # Return "N|line" numbered slice; default window ~200 lines if end_line<=0.
    ...
```

**Registry pattern:**

```python
CODE_TOOL_REGISTRY: dict[str, dict] = {
    "read_file": {"func": read_file, "description": "..."},
    "write_file": {"func": write_file, "description": "..."},
    "search_replace": {"func": search_replace, "description": "..."},
    "list_dir": {"func": list_dir, "description": "..."},
    "grep": {"func": grep, "description": "..."},
    "find_files": {"func": find_files, "description": "..."},
    "run_command": {"func": run_command, "description": "..."},  # allowlisted
}
```

JobSpec.tools must be a subset of this registry (≤4 names).

---

## 4. Grep output contract

```python
# Match lines: "rel/path.py:12: content..."
# Wrapped as: [OK] N match(es) for 'pat'\n<body>
# Cap matches (default 50). Skip should_skip_dir + optional root .gitignore dir names.
matches.append(f"{rel}:{i}: {line.strip()[:200]}")
```

Lacerta workers (and optional auto-context) depend on this `path:line: content` shape.

---

## 5. Tool catalog + schema (CodeWorker)

```python
def get_active_tools(job_tools: list[str] | None = None) -> frozenset[str]:
    base = frozenset(CODE_TOOL_REGISTRY)
    if job_tools:
        return frozenset(t for t in job_tools if t in base)
    return base


def build_worker_json_schema(tool_names: frozenset[str]) -> dict:
    registry = {k: CODE_TOOL_REGISTRY[k] for k in tool_names}
    return build_agent_action_json_schema(
        tool_names,
        registry,
        simplify=True,
        max_tools_per_turn=1,
        require_final_report=False,
    )
```

---

## 6. Ollama JSON schema rules

**Critical for local Ollama — implement these transforms:**

```python
def _prepare_ollama_schema(schema: dict, *, simplify: bool) -> dict:
    out = _inline_defs(schema)                 # expand $ref / $defs
    out = _enforce_additional_properties_false(out)  # every object
    if simplify:
        out = _strip_descriptions(out)         # smaller payloads
    if out.get("type") != "object":
        out = {"type": "object", **out}
    return out
```

**Worker action shape (conceptual):**

```json
{
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "reasoning": {"type": "string"},
    "tools": {
      "type": "array",
      "maxItems": 1,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "properties": {
          "name": {"type": "string", "enum": ["read_file", "write_file", "..."]},
          "arguments": {"type": "object"}
        },
        "required": ["name", "arguments"]
      }
    },
    "final_report": {"type": "string"}
  },
  "required": ["reasoning", "tools", "final_report"]
}
```

Avoid nested/complex `anyOf` for weak models when possible. Flat enums for tool names.

---

## 7. Session metrics

```python
@dataclass
class WorkerSessionMetrics:
    turns: int = 0
    wall_s: float = 0.0
    parse_failures: int = 0
    completed: bool = False
    model_id: str = ""
    job_id: str = ""
    job_type: str = ""
    surface: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
```

Append JSONL under `logs/worker-sessions.jsonl`.

---

## 8. Honest harness evaluation

**Implement thin; keep these contracts.**

### 8.1 Scenario shape

```python
SCENARIOS = {
    "smoke_write_file": {
        "description": "Create harness_smoke.py",
        "surface": "code",
        "job_type": "code_edit",
        "objective": (
            "Create harness_smoke.py with print('HARNESS_OK') using write_file. "
            "Then set final_report when done."
        ),
        "acceptance": {
            "check_file_glob": "**/harness_smoke.py",
            "file_contains": "HARNESS_OK",
        },
    },
    "learn_syllabus_files": {
        "surface": "learn",
        "job_type": "learn_syllabus_files",
        "objective": "Build a deep syllabus from attached course materials.",
        "inputs": {"recipe_id": "learn.syllabus_from_files", "attachments": ["..."]},
        "acceptance": {
            "syllabus_min_nodes": 8,
            "syllabus_min_subunits": 5,
            "course_active": True,
        },
    },
    "habit_tracker": {
        "surface": "code",
        "objective": "Build CLI habit tracker: habit.py, tests/test_habit.py, README.md",
        "acceptance": {"habit_tracker": True},
    },
    "research_local": {
        "surface": "research",
        "job_type": "research_local",
        "objective": "Offline research note from attached sources (no web).",
        "inputs": {"recipe_id": "research.offline", "attachments": ["..."]},
        "acceptance": {"min_deliverable_chars": 400},
    },
    "writing_short": {
        "surface": "writing",
        "objective": "Two-paragraph markdown draft with a clear # title.",
        "acceptance": {"min_deliverable_chars": 300},
    },
}
```

Learn / research / writing acceptance details: surfaces doc.

### 8.2 Disk acceptance

```python
def check_acceptance(scenario: dict, project_root: Path) -> list[str]:
    failures = []
    acc = scenario.get("acceptance") or {}
    needle = acc.get("file_contains")
    check_glob = acc.get("check_file_glob")
    if check_glob:
        matches = sorted(project_root.glob(check_glob), key=lambda p: p.stat().st_mtime, reverse=True)
        # Also search under data root if projects live outside cwd
        if not matches:
            failures.append(f"expected file missing (glob {check_glob!r})")
        elif needle and needle not in matches[0].read_text(encoding="utf-8", errors="replace"):
            failures.append(f"{matches[0]} does not contain {needle!r}")
    return failures
```

### 8.3 Code success honesty

```python
def session_successful(metrics: dict, acceptance_failures: list[str]) -> bool:
    if metrics.get("completed") or metrics.get("synced"):
        return True
    return not acceptance_failures  # disk acceptance can pass without final_report


def evaluate_run(report: dict) -> tuple[bool, list[str]]:
    failures = []
    acceptance_failures = check_acceptance(...)
    code_ok = session_successful(report.get("worker_metrics") or {}, acceptance_failures) and not acceptance_failures
    # Do NOT fail solely because status=failed if disk acceptance passed
    if report.get("run_status") == "failed" and not code_ok:
        failures.append("run_status=failed")
    # Drop scorecard noise like "finish_task not observed" when code_ok
    failures.extend(acceptance_failures)
    return (not failures), failures
```

### 8.4 Gate script shape

```bash
#!/usr/bin/env bash
# lacerta/harness/gate.sh
set -euo pipefail
export LACERTA_DATA_ROOT="${LACERTA_DATA_ROOT:-$REPO_ROOT}"
python -m lacerta.harness.gate "$@"
# Default: smoke scenario, --runs 3
```

---

## 9. Model tiers

```python
CAPABLE_MODELS = frozenset({"lacerta", "lacerta:latest"})  # harness-verified tags
DEGRADED_MODELS = frozenset()

def check_worker_model(*, surface: str = "cli", strict: bool = False) -> ModelCheckResult:
    # capable → ok
    # degraded → block in GUI; warn in CLI unless override env
    # unknown → warn; allow unless strict
    ...
```

Gate **workers** (optionally a stronger model for manager later).

---

## 10. Capability registry (Learn / Research / Writing workers)

**Use inside recipe workers, not as the manager loop.**  
Full catalogs: **[lacerta-surfaces-and-recipes.md](lacerta-surfaces-and-recipes.md)**.

```python
@dataclass
class CapabilityContext:
    client: Any = None
    task_id: str = ""
    surface: str = "learn"  # chat | code | learn | research | writing
    offline: bool = False
    user_request: str = ""
    attachments: list[str] = field(default_factory=list)
    source_registry: Any = None
    instance_id: str = ""
    # Keep small — do not dump manager chat here


@dataclass
class CapabilityResult:
    ok: bool
    data: dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    error_code: str | None = None
    error_message: str | None = None

    @classmethod
    def success(cls, summary: str = "", **data: Any) -> CapabilityResult: ...
    @classmethod
    def failure(cls, code: str, message: str) -> CapabilityResult: ...


@dataclass(frozen=True)
class CapabilitySpec:
    capability_id: str
    title: str
    description: str
    input_model: Type[BaseModel]
    handler: CapabilityHandler
    surfaces: frozenset[str] = frozenset({"learn"})


def run_capability(
    capability_id: str,
    ctx: CapabilityContext,
    arguments: dict | None = None,
) -> CapabilityResult:
    spec = get_capability(capability_id)
    if spec is None:
        return CapabilityResult.failure("unknown_capability", capability_id)
    try:
        validated = spec.input_model.model_validate(arguments or {})
    except Exception as exc:
        return CapabilityResult.failure("invalid_input", str(exc))
    try:
        return spec.handler(ctx, validated)
    except Exception as exc:
        return CapabilityResult.failure("runtime_error", str(exc))
```

**Recipe runner:**

```python
def run_recipe(recipe_id: str, ctx: CapabilityContext, job: JobSpec) -> JobResult:
    recipe = get_recipe(recipe_id)
    artifacts: list[str] = []
    for cap_id in recipe.capability_ids:
        result = run_capability(cap_id, ctx, args_for(cap_id, job))
        if not result.ok:
            return JobResult(
                job_id=job.job_id, ok=False, summary=result.summary or "",
                error=result.error_message, metrics={},
            )
        if path := result.data.get("path"):
            artifacts.append(str(path))
    return JobResult(
        job_id=job.job_id, ok=True, summary="Recipe complete.",
        artifacts=artifacts, metrics={},
    )
```

**Embeddings (optional):** prefer offline hash/ONNX; never download unless `LACERTA_ALLOW_EMBEDDING_DOWNLOAD=1`.

---

## 11. Learn / research / writing contracts

All product contracts (syllabus gates, recipes, writing brief, research notes):

→ **[lacerta-surfaces-and-recipes.md](lacerta-surfaces-and-recipes.md)**

If a detail is missing, define a minimal contract + harness scenario in-repo.

---

## 12. Phase docs (create in Lacerta repo)

| Phase | Title | Exit |
|-------|-------|------|
| **L0** | Bootstrap + JobSpec/JobResult/Surface + gate stub | `pytest` green |
| **L1** | CodeWorker + FS tools + schema | `smoke_write_file` 3/3 |
| **L2** | Manager + surface allowlists + code templates | Manager spawns CodeWorker |
| **L3** | **LearnWorker** + syllabus recipes + structure gate | `learn_syllabus_files` green |
| **L4** | Honest evaluate + habit acceptance | `habit_tracker` tracked |
| **L5** | ResearchWorker | `research_local` green |
| **L6** | WritingWorker | `writing_short` green |
| **L7** | Optional LLM manager decompose (flagged) | Templates still default |
| **L8** | Thin GUI (surface tabs + job log) | No second OS |
| **L9** | MCP **host** (stdio meta-tools → manager) | Cursor runs smoke via `lacerta_run_scenario` |
| **L10** | MCP **client** (`mcp__*` allowlisted) | One external server from a research job |
| **L11** | Remote companion (pair + PWA + surface launch) | Phone completes learn or research job |
| **L12** | Remote MCP SSE mount + generation lock polish | Same host tools over mesh + token |

MCP/Remote contracts: architecture doc §9 and surfaces doc §13. **Do not start L9 before L1–L6 are green.**

Each phase: goal, checkboxes, files, tests, harness command, architecture PR checklist.

---

## 13. Repo bootstrap checklist

```text
lacerta/
  README.md
  docs/
    architecture.md
    port-kit.md
    surfaces-and-recipes.md
    phases/
  lacerta/
    core/jobs.py
    core/worker_runtime.py
    core/manager.py
    core/routers/
    workers/code_tools.py
    workers/learn/
    workers/research/
    workers/writing/
    harness/{scenarios,evaluate,gate}.py
    storage/
  scripts/gate.sh
  tests/
```

**Implementation order**

1. `jobs.py`  
2. `code_tools.py` + `worker_runtime.py`  
3. `smoke_write_file`  
4. `manager.py` + code templates  
5. **Learn** recipes (surfaces doc §6)  
6. Habit + research + writing  
7. GUI  
8. **MCP host → MCP client → Remote** (architecture §9)  

---

## 14. Env defaults

```env
LACERTA_WORKER_MAX_TURNS=5
LACERTA_MANAGER_MAX_STEPS=20
LACERTA_MAX_WRITE_CHARS=8000
LACERTA_TOOL_OUTPUT_CHAR_CAP=6000
LACERTA_MODEL_GATE=1
LACERTA_LEARN_TUTOR_TEMP=0.7
LACERTA_MCP_ALLOWED_SURFACES=research,writing,chat
LACERTA_REMOTE_PORT=8800
OLLAMA_MODEL=lacerta:latest
OLLAMA_BASE_URL=http://127.0.0.1:11434
```

---

## 15. Reminder

- Architecture = Supervisor–Worker; surfaces ≠ engines.  
- Surfaces doc = learn / research / writing / chat (**learn is 2nd**).  
- This kit = CodeWorker + IPC + schema + harness + registry.  
- MCP host/client + Remote = **last**, same manager, small tool surface.  
- One manager; workers by JobType; harness honesty on disk.
