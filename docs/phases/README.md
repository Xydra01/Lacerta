# Lacerta Implementation Phases

Numbered phase docs for building Lacerta from the blueprint trio:

| Doc | Role |
|-----|------|
| [lacerta-supervisor-worker-viability.md](../../lacerta-supervisor-worker-viability.md) | Architecture, do/don't, MCP/Remote late plan |
| [lacerta-port-kit.md](../../lacerta-port-kit.md) | CodeWorker, IPC, schema, harness, registry |
| [lacerta-surfaces-and-recipes.md](../../lacerta-surfaces-and-recipes.md) | Surfaces, recipes, learn/research/writing |

**Ship order:** code → learn → research → writing → chat/GUI polish → MCP → Remote.

**Hard gate:** do not start **L9+** until **L1–L6** are harness-honest.

| Phase | Title | Exit |
|-------|-------|------|
| [L0](phase-L0.md) | Bootstrap + JobSpec/JobResult/Surface + gate stub | `pytest` green |
| [L1](phase-L1.md) | CodeWorker + FS tools + schema | `smoke_write_file` 3/3 |
| [L2](phase-L2.md) | Manager + surface allowlists + code templates | Manager spawns CodeWorker |
| [L3](phase-L3.md) | LearnWorker + syllabus recipes + structure gate | `learn_syllabus_files` green |
| [L4](phase-L4.md) | Honest evaluate + habit acceptance | `habit_tracker` tracked |
| [L5](phase-L5.md) | ResearchWorker | `research_local` green (done) |
| [L6](phase-L6.md) | WritingWorker | `writing_short` green |
| [L7](phase-L7.md) | Optional LLM manager decompose (flagged) | Templates still default |
| [L8](phase-L8.md) | Thin GUI (surface tabs + job log) | No second OS |
| [L9](phase-L9.md) | MCP host (stdio → manager) | Cursor runs smoke via `lacerta_run_scenario` |
| [L10](phase-L10.md) | MCP client (`mcp__*` allowlisted) | One external server from a research job |
| [L11](phase-L11.md) | Remote companion (pair + PWA + surface launch) | Phone completes learn or research job |
| [L12](phase-L12.md) | Remote MCP SSE + generation lock polish | Same host tools over mesh + token |

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
- [ ] MCP/Remote blocking core surface ship order?
