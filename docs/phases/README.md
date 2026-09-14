# Lacerta Implementation Phases

Numbered phase docs for building Lacerta from the blueprint trio, plus the **v1 product track**.

| Doc | Role |
|-----|------|
| [Architecture v1](../architecture-v1.md) | **Active** product architecture (GUI + surface depth; MCP deferred) |
| [lacerta-supervisor-worker-viability.md](../../lacerta-supervisor-worker-viability.md) | Supervisor–Worker rules, do/don't |
| [lacerta-port-kit.md](../../lacerta-port-kit.md) | CodeWorker, IPC, schema, harness |
| [lacerta-surfaces-and-recipes.md](../../lacerta-surfaces-and-recipes.md) | Surfaces, recipes, learn/research/writing |

**Ship order (current):**

1. **v0 complete:** code → learn → research → writing → chat/thin GUI (L0–L8)  
2. **v1 active:** deepen GUI + surface capabilities (V1.0–V1.5), including **shared corpus index (V1.35)**  
3. **Deferred:** MCP → Remote (L9–L12) — resume only after **V1.5**

**Hard gate:** do not start **L9+** until **v1 exit (V1.5)** and **L1–L6** remain harness-honest.

---

## v0 — Core (done)

| Phase | Title | Exit |
|-------|-------|------|
| [L0](phase-L0.md) | Bootstrap + JobSpec/JobResult/Surface + gate stub | `pytest` green |
| [L1](phase-L1.md) | CodeWorker + FS tools + schema | `smoke_write_file` 3/3 |
| [L2](phase-L2.md) | Manager + surface allowlists + code templates | Manager spawns CodeWorker |
| [L3](phase-L3.md) | LearnWorker + syllabus recipes + structure gate | `learn_syllabus_files` green |
| [L4](phase-L4.md) | Honest evaluate + habit acceptance | `habit_tracker` tracked |
| [L5](phase-L5.md) | ResearchWorker | `research_local` green |
| [L6](phase-L6.md) | WritingWorker | `writing_short` green |
| [L7](phase-L7.md) | Optional LLM manager decompose (flagged) | Templates still default |
| [L8](phase-L8.md) | Thin GUI (surface tabs + job log) | No second OS |

---

## v1 — Productize GUI & capabilities (active)

| Phase | Title | Exit |
|-------|-------|------|
| [V1.0](phase-V1.0.md) | Charter + architecture | Docs landed; L9–L12 deferred |
| [V1.1](phase-V1.1.md) | GUI product shell | Attachments, deliverable viewer, run history |
| [V1.2](phase-V1.2.md) | Code depth in GUI | Smoke **or** habit selectable; acceptance visible |
| [V1.3](phase-V1.3.md) | Learn depth | Tutor/assessment/archive stub + course UI; corpus paths reserved |
| [V1.35](phase-V1.35.md) | Shared corpus & multi-pass index | Extract→chunk→map→embed→retrieve; learn textbook harness |
| [V1.4](phase-V1.4.md) | Research & writing depth | from_sources + bounded gather; research bulk via corpus |
| [V1.5](phase-V1.5.md) | Chat continuity & v1 exit | Multi-turn chat + regression bar (incl. corpus gate) |

---

## Deferred integrations (former L9–L12)

| Phase | Title | Status |
|-------|-------|--------|
| [L9](phase-L9.md) | MCP host (stdio → manager) | **Deferred** after v1 |
| [L10](phase-L10.md) | MCP client (`mcp__*` allowlisted) | **Deferred** |
| [L11](phase-L11.md) | Remote companion (pair + PWA) | **Deferred** |
| [L12](phase-L12.md) | Remote MCP SSE + generation lock polish | **Deferred** |

---

## How to use a phase doc

1. Confirm prior phase exit is met.
2. Implement checkboxes in order.
3. Run the listed tests / harness command.
4. Fill the architecture PR checklist before merging.

## Global architecture PR checklist (every phase)

- [ ] Second orchestrator path?
- [ ] Surface forked an engine instead of a template?
- [ ] Manager can write files or call web_search?
- [ ] Worker context unbounded?
- [ ] `max_turns` / syllabus gates in Python?
- [ ] Harness scenario for this feature?
- [ ] Heal layer instead of fixing schema/acceptance?
- [ ] Learn deferred without cause?
- [ ] MCP/Remote inventing a parallel brain?
- [ ] MCP/Remote blocking core / v1 surface ship order?
- [ ] Manager holding corpus chunk text?
- [ ] Separate per-surface RAG engines instead of shared corpus?
