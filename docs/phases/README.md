# Lacerta Implementation Phases

Numbered phase docs for building Lacerta from the blueprint trio, plus the **v1 product track**.

| Doc | Role |
|-----|------|
| [Architecture v1](../architecture-v1.md) | **v1 exit met** (GUI + surface depth; MCP deferred) |
| [Architecture v2](../architecture-v2.md) | **v2 exit met** — Learn UX, LLM tutor, mastery, practice, Archive |
| [Architecture v3](../architecture-v3.md) | **v3 planned** — replies, formatting, activity, themes |
| [lacerta-supervisor-worker-viability.md](../../lacerta-supervisor-worker-viability.md) | Supervisor–Worker rules, do/don't |
| [lacerta-port-kit.md](../../lacerta-port-kit.md) | CodeWorker, IPC, schema, harness |
| [lacerta-surfaces-and-recipes.md](../../lacerta-surfaces-and-recipes.md) | Surfaces, recipes, learn/research/writing |

**Ship order (current):**

1. **v0 complete:** code → learn → research → writing → chat/thin GUI (L0–L8)  
2. **v1 complete:** deepen GUI + surface capabilities (V1.0–V1.55) — **exit met**  
3. **v2 complete:** decluttered UI + LLM tutoring / mastery / practice / Archive (V2.0–V2.5) — **exit met**  
4. **v3 planned:** reply panel, formatting, activity, field hygiene, themes (V3.0–V3.3)  
5. **Deferred:** MCP → Remote (L9–L12) — resume only after deliberate decision (not blocked on v3)

**Hard gate:** do not start **L9+** until **v1 exit (V1.5)** remains harness-honest; v2 does not invent a second orchestrator.

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

## v1 — Productize GUI & capabilities (done)

| Phase | Title | Exit |
|-------|-------|------|
| [V1.0](phase-V1.0.md) | Charter + architecture | Docs landed; L9–L12 deferred |
| [V1.1](phase-V1.1.md) | GUI product shell | Attachments, deliverable viewer, run history |
| [V1.2](phase-V1.2.md) | Code checks & scenarios in GUI | Test / premade scenarios; acceptance visible |
| [V1.3](phase-V1.3.md) | Learn depth | Tutor/assessment/archive stub + course UI; corpus paths reserved |
| [V1.35](phase-V1.35.md) | Shared corpus & multi-pass index | Extract→chunk→map→embed→retrieve; learn textbook harness |
| [V1.4](phase-V1.4.md) | Research & writing depth | from_sources + bounded gather; research bulk via corpus |
| [V1.5](phase-V1.5.md) | Chat continuity & v1 exit | Multi-turn chat + regression bar (incl. corpus gate) |
| [V1.55](phase-V1.55.md) | Document extract | PDF/DOCX/HTML/CSV → text for corpus & ingest |

---

## v2 — Learn UX & LLM tutoring (**v2 exit met**)

| Phase | Title | Exit |
|-------|-------|------|
| [V2.0](phase-V2.0.md) | Charter + Learn UX contracts | architecture-v2 + phase map |
| [V2.1](phase-V2.1.md) | Thin UI declutter | Mode-scoped fields; wiring tests — **done** |
| [V2.2](phase-V2.2.md) | LLM tutor + retrieve + history | Teach from corpus; compressed history — **done** |
| [V2.3](phase-V2.3.md) | Mastery 0–5 | Progress-aware tutor/assessment — **done** |
| [V2.35](phase-V2.35.md) | Structured corpus ingest | Tables/math/figures → text surrogates — **done** |
| [V2.4](phase-V2.4.md) | Interactive practice | MC quizzes, flashcards, study guides — **done** |
| [V2.5](phase-V2.5.md) | Archive chat + v2 exit | Corpus LLM Archive; matrix green — **done** |

---

## v3 — UI / UX polish (planned)

| Phase | Title | Exit |
|-------|-------|------|
| [V3.0](phase-V3.0.md) | Charter | architecture-v3 + phase map — **docs** |
| [V3.1](phase-V3.1.md) | Replies + formatting | Conversation panel; newlines, bold, italic, math |
| [V3.2](phase-V3.2.md) | Activity + buffered typing | Step trace; reply grows in closed markdown chunks |
| [V3.3](phase-V3.3.md) | Fields + themes + exit | Draft title scoped; Grove / Dusk / Ink |

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
