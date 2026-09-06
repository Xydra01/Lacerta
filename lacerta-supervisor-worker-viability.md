# Lacerta Architecture: Supervisor–Worker

**Status:** Architecture blueprint for the Lacerta repo  
**Date:** 2026-09-06  
**Companion docs:**
- [lacerta-port-kit.md](lacerta-port-kit.md) — CodeWorker, IPC, schema, harness  
- [lacerta-surfaces-and-recipes.md](lacerta-surfaces-and-recipes.md) — surfaces, recipes (incl. **learn**)  
- [docs/architecture-v1.md](docs/architecture-v1.md) — **v1 product track** (GUI/capabilities; MCP deferred)

---

## 1. North star

> A stateful **manager** that only plans, dispatches, and grades; ephemeral **workers** that execute one typed job with 2–4 tools *or* a Python recipe and a purged context—gated by harness pass/fail. **Surfaces pick templates; they never fork the OS.**

| Question | Answer |
|----------|--------|
| Why Supervisor–Worker? | Local mid-size models fail as full OS kernels; they succeed as specialists with tiny contexts |
| Multi-surface product? | **Yes** — chat, code, learn, research, writing |
| Multi-engine runtime? | **No** — one manager; workers differ by JobType |
| Ship order | **v0 done** (→ thin GUI). **v1 next** (GUI + surface depth). **MCP → Remote deferred** after v1 — see [docs/architecture-v1.md](docs/architecture-v1.md) |

---

## 2. Design rules (do / don't)

### 2.1 Do

| Do | Why |
|----|-----|
| Harness before features | No silent regressions; disk acceptance > log theater |
| One manager for all surfaces | Single orchestration story |
| Surfaces = UX + templates + JobType allowlists | Product modes without forked engines |
| Workers ephemeral (fresh + purge) | Predictable KV / cost / failure attribution |
| Limits in Python (`max_turns`, quality gates) | Soft “please stop” prompts fail |
| Templates before free LLM decompose | Bad plans waste workers |
| Code = FS tool loop | Direct disk is source of truth |
| Learn / research / writing = recipe runners | Batched Python sequences beat turn-by-turn cap picking for templates |
| Typed `JobSpec` / `JobResult` | Debuggable IPC; no worker↔worker chat |
| Line budgets on orchestration core (&lt; ~1.5k) | Prevent god modules |
| Local Ollama + optional local embeddings | Privacy-first runtime |

### 2.2 Don't

| Don't | Why |
|-------|-----|
| Separate loop engine per surface | Dual architectures and months of freeze work |
| Manager calling FS / shell / web tools | Role collapse; manager becomes the overloaded agent |
| Conversational multi-agent / worker↔worker channels | Fragile ownership; hard to debug |
| Prompt-as-OS (coaches, heal towers, milestone novels) | Fragility; hide real failures |
| Canvas / buffer as agent source of truth for code | Dual truth with disk |
| Code via capability FSM / “dev recipes” | Confuses models; tools are enough |
| Features without harness scenarios | Unmetered complexity |
| 96k default worker context | Prefill blow-up |
| Ship learn/research/writing engines before code smoke | No honest foundation |
| Defer learn behind research/writing | Learn is **2nd** surface after code |

---

## 3. Architecture

### 3.1 Shape

```
┌──────────────────────────────────────────────────────────────┐
│  Task surface (UX): chat | code | learn | research | writing │
│  → MacroTemplate + JobType allowlist only                    │
└────────────────────────────┬─────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────┐
│  Manager (stateful)                                          │
│  - goal, macro-plan, acceptance                              │
│  - spawn_worker | finish_task | fail_task ONLY               │
│  - IPC: JobSpec / JobResult                                  │
└────────────────────────────┬─────────────────────────────────┘
                             │
     ┌───────────┬───────────┼───────────┬───────────┐
     ▼           ▼           ▼           ▼           ▼
 CodeWorker  LearnWorker ResearchWorker WritingWorker  chat (manager-local)
 tool loop   recipes     recipes        recipes
```

### 3.2 Core types

```python
Surface = Literal["chat", "code", "learn", "research", "writing"]

class JobSpec(BaseModel):
    job_id: str
    job_type: str          # see surfaces doc
    objective: str
    inputs: dict[str, Any] = {}
    tools: list[str] = []  # CodeWorker ≤4; recipes usually []
    acceptance: dict[str, Any] = {}
    max_turns: int = 5

class JobResult(BaseModel):
    job_id: str
    ok: bool
    summary: str
    artifacts: list[str] = []
    metrics: dict[str, Any] = {}
    error: str | None = None
```

Manager keeps JobResult **summaries**, not full worker transcripts.

### 3.3 Manager loop (deterministic shell)

```
state = MacroState(surface, goal, plan=[], results=[])
while not done and steps < MAX_MANAGER_STEPS:
    if python_router.can_handle(state):
        job = python_router.next_job(state)   # templates first
    else:
        job = llm_manager.propose_job(state)  # typed JobSpec only
    validate(job)  # Pydantic + surface allowlist
    result = worker_runtime.run(job)
    state.apply(result)
    if acceptance_met(state): finish()
    if result.failed_hard: fail_or_replan()
```

### 3.4 Worker runtime

1. System: role + tools/recipe only  
2. User: objective + inputs (+ tiny snapshot if code)  
3. Loop ≤ `max_turns` **or** one recipe pass  
4. Return `JobResult`; delete message list  

Tool-loop details: port kit. Recipe catalogs: surfaces doc.

### 3.5 Risks & mitigations

| Risk | Mitigation |
|------|------------|
| Manager overload | Manager **cannot** call worker tools |
| Decomposition tax | Fixed Python templates first; LLM decompose behind flag |
| Latency on tiny tasks | Fast path: one worker for whole smoke goal |
| Invalid JobSpecs | Pydantic reject before spawn |
| False confidence | Harness bar before “reliable” claims |
| Scope creep | v0 surfaces only; persona/calendar later |

### 3.6 Fit with local models

- Manager: classify, pick template, grade short summaries  
- Workers: narrow tools or one recipe  
- Dynamic decompose: rare; emit JobSpecs, not narrative plans  

The thin AgentLoop lives **inside workers**, not as the whole product. The manager is the missing hard boundary.

---

## 4. Product charter

### 4.1 Hard rules

1. Harness before features  
2. Orchestration core line budget  
3. Disk is SoT for code; syllabus.json is SoT for learn courses  
4. Manager has no FS/web tools  
5. Workers ephemeral  
6. Limits in Python  
7. Templates before free planning  
8. No heal towers as strategy — structured errors + optional respawn  
9. No dual orchestrator paths  
10. Ship vertical slices: **code smoke → learn syllabus → code habit → research → writing**

### 4.2 Non-goals for v0 (core)

- Multi-worker parallelism / swarm chat  
- Workflow GUI editor  
- Persona / calendar / email  
- Plan-review dialogs for code  
- TDD step-kind FSMs / slot-fill planners  
- Coach personas and long “OS HINT” tool output  
- Full learn placement diagnostic / cross-course analytics (post-v0)  
- **MCP host/client and Remote companion** — **planned, not abandoned**; see §9 (ship last)

### 4.3 Day-one metrics

| Metric | Gate |
|--------|------|
| `smoke_write_file` | 3/3 |
| `learn_syllabus_files` | structure gate + active course |
| `habit_tracker` | 3/3 before “code reliable” |
| Worker tokens ≪ manager tokens | Logged |
| Parse failure rate | &lt; 5% per worker session |

---

## 5. What to build (modules)

| Module | Role |
|--------|------|
| `core/jobs.py` | Surface, JobSpec, JobResult |
| `core/manager.py` | Stateful orchestrator |
| `core/worker_runtime.py` | Tool-loop AgentLoop (CodeWorker) |
| `core/routers/` | Deterministic templates per surface |
| `workers/code_tools.py` | FS + grep + allowlisted shell |
| `workers/learn/` | Syllabus/tutor/archive caps + recipes |
| `workers/research/` | Notes/web/report recipes |
| `workers/writing/` | Draft/finalize recipes |
| `harness/` | Scenarios, evaluate, gate |
| `storage/` | Paths, embeddings, learn registry |
| `gui/` | Thin later — surface tabs + job log |
| `integrations/mcp_host.py` | Late: Cursor meta-tools → manager |
| `integrations/mcp_client.py` | Late: external `mcp__*` into allowlisted jobs |
| `remote/` | Late: companion API + PWA + pair/revoke |

Contracts live in the companion docs—not in tribal memory.

---

## 6. Repo layout

```
lacerta/
  core/
    manager.py
    worker_runtime.py
    jobs.py
    routers/
  workers/
    code_tools.py
    learn/
    research/
    writing/
  harness/
    scenarios.py
    evaluate.py
    gate.sh
  storage/
  gui/                  # thin later
  integrations/         # late: mcp_host, mcp_client
  remote/               # late: companion API + PWA
  docs/
    architecture.md     # this file
    port-kit.md
    surfaces-and-recipes.md
    phases/
```

---

## 7. First scenarios

| Scenario | Surface | Acceptance |
|----------|---------|------------|
| `smoke_write_file` | code | File contains marker |
| `learn_syllabus_files` | learn | ≥8 nodes, ≥5 sub-units, course active |
| `habit_tracker` | code | Files + pytest green |
| `research_local` | research | Min deliverable chars |
| `writing_short` | writing | Min deliverable chars |
| `manager_grades_failure` | any | Worker fails; manager stops cleanly |

---

## 8. Recommended build sequence

1. Bootstrap repo + JobSpec/JobResult/Surface + gate stub  
2. CodeWorker + `smoke_write_file` 3/3  
3. Manager + code templates  
4. **LearnWorker** + `learn_syllabus_files` (+ shallow-reject unit test)  
5. Habit template + honest evaluate  
6. ResearchWorker → WritingWorker  
7. LLM manager decompose behind flag  
8. Thin GUI (surface tabs + job activity)  
9. **v1 track** — GUI product shell + surface depth (see [docs/architecture-v1.md](docs/architecture-v1.md), phases V1.1–V1.5)  
10. **MCP host + client** (integrations) — **deferred until after v1**  
11. **Remote companion** (phone/PWA over private mesh) — **deferred until after v1**

---

## 9. Integrations (deferred — do not abandon)

MCP and Remote are **first-class Lacerta advantages**, but they ship **after v1 product depth**—not immediately after the thin GUI. They wrap the same manager; they must not invent a second brain. Active plan: [docs/architecture-v1.md](docs/architecture-v1.md).

### 9.1 MCP (two directions)

| Direction | Role | When |
|-----------|------|------|
| **Host** | Cursor (or any MCP client) calls Lacerta via a small meta-tool set | After manager + ≥1 surface stable |
| **Client** | Lacerta calls external MCP servers as allowlisted tools | After CodeWorker tools exist; keep off learn/code templates by default |

**Host meta-tools (target catalog — rename freely, keep roles):**

| Tool | Behavior |
|------|----------|
| `lacerta_health` | Ollama reachability, model, instance, generation lock |
| `lacerta_list_instances` | Instance profiles |
| `lacerta_run_surface` | Headless run: `surface` + objective + inputs → manager/templates → JobResults |
| `lacerta_get_job_status` | Status for a task / job_id |
| `lacerta_get_run_metrics` | Throughput / wall / turns from session logs |
| `lacerta_read_deliverable` | Bounded read of report / syllabus / draft |
| `lacerta_list_scenarios` / `lacerta_run_scenario` / `lacerta_evaluate_run` | Harness from MCP |
| `lacerta_release_generation_lock` | Clear stale lock |

**Do:** Host tools call the **same manager** as GUI/CLI.  
**Don't:** Host tools reimplement LoopEngine or bypass harness acceptance.

**Client:**

- Config: user-enabled server list (stdio / SSE); per-instance overrides optional  
- Tool names: `mcp__{server}__{tool}`  
- Merge into worker registries only when the JobSpec/surface allowlist says so  
- Default: MCP client tools **off** for code/learn template jobs; enable for research/writing/chat if useful  

**Transports:** stdio for local Cursor; SSE (+ auth) when Remote is up.

### 9.2 Remote companion

Phone / laptop PWA → private mesh (e.g. Tailscale) → small host API → **same manager**.

| Piece | Contract |
|-------|----------|
| Network | Private mesh first; no public port-forward by default |
| Auth | Host ID + one-time pair code → long-lived device token (store hash only); revoke CLI |
| API | Chat stream, surface launch, job status, deliverable download, Ollama start/stop |
| UI | Thin: surface switcher (chat / code status / learn / research / writing)—not a second OS |
| MCP mount | Same host meta-tools at `/api/mcp/host/sse` with Bearer token |
| Lock | Shared generation lock so GUI, MCP, and Remote never double-generate |

**Do:** Remote is a **thin client** over manager + storage.  
**Don't:** Put orchestration logic in the PWA or a separate remote agent.

### 9.3 Integration do / don't

| Do | Don't |
|----|-------|
| Ship after core surfaces + harness | Block L0–L8 on MCP/Remote |
| Reuse manager + JobSpec | Fork a “remote mode engine” |
| Keep MCP host catalog small (~8–12 tools) | Expose every FS tool to Cursor |
| Pair + revoke devices | Trust open LAN alone |
| Gate `lacerta_run_scenario` with same evaluate_run | Different acceptance for MCP runs |

### 9.4 Suggested late phases

| Phase | Title | Exit |
|-------|-------|------|
| **L9** | MCP host (stdio) + health/run_surface/read_deliverable | Cursor can run smoke via MCP |
| **L10** | MCP client bridge (allowlisted `mcp__*`) | One external server callable from research job |
| **L11** | Remote companion (pair + chat + learn/research launch) | Phone PWA completes a learn or research job |
| **L12** | Remote mounts MCP host SSE + generation lock polish | Same tools over Tailscale with token |

---

## 10. Closing

Lacerta succeeds if workers stay tiny and typed, the manager never does worker work, limits live in Python, surfaces never fork the runtime, the harness remains the product’s conscience, **learn** ships early for real school use, and **MCP + Remote** return as thin integrations—not a second product—once the core is honest.

---

## Appendix — PR checklist

- [ ] Second orchestrator path?  
- [ ] Surface forked an engine instead of a template?  
- [ ] Manager can write files or call web_search?  
- [ ] Worker context unbounded?  
- [ ] `max_turns` / syllabus gates in Python?  
- [ ] Harness scenario for this feature?  
- [ ] Heal layer instead of fixing schema/acceptance?  
- [ ] Learn deferred without cause?  
- [ ] MCP/Remote inventing a parallel brain?  
- [ ] MCP/Remote blocking core surface ship order?  
