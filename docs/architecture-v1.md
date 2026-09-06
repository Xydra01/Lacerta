# Lacerta v1 Architecture

**Status:** active product architecture (v1 track)  
**Date:** 2026-09-06  
**Supersedes for planning:** v0 “thin GUI then MCP/Remote” ship order  
**Does not replace:** the Supervisor–Worker blueprint trio (still normative for core rules)

| Doc | Role |
|-----|------|
| [lacerta-supervisor-worker-viability.md](../lacerta-supervisor-worker-viability.md) | Core Supervisor–Worker rules, do/don't |
| [lacerta-port-kit.md](../lacerta-port-kit.md) | CodeWorker, IPC, schema, harness |
| [lacerta-surfaces-and-recipes.md](../lacerta-surfaces-and-recipes.md) | Surface contracts & recipes |
| [docs/phases/README.md](phases/README.md) | Phase index (v0 complete, v1 active, MCP deferred) |

---

## 1. Version story

| Version | Meaning | Exit |
|---------|---------|------|
| **v0** | Harness-honest core: L0–L8 (manager, five surfaces, thin GUI stub, flagged LLM decompose) | Gates green; `python -m lacerta.gui` launches |
| **v1** | **Productize** existing surfaces + GUI so a human can usefully run chat/code/learn/research/writing locally | Phase V1.5 exit; still one manager; still no MCP/Remote required |
| **Later (deferred)** | Former L9–L12: MCP host/client, Remote companion, SSE mount | Resume only after v1 exit; same manager wrap |

**v1 is not a second orchestrator.** It deepens templates, recipes, GUI forms, and honesty around deliverables.

---

## 2. North star (unchanged)

> A stateful **manager** that only plans, dispatches, and grades; ephemeral **workers** that execute one typed job with a tiny tool set *or* a Python recipe—gated by harness pass/fail. **Surfaces pick templates; they never fork the OS.**

v1 adds:

> A **usable local product shell** (GUI + CLI/harness) where each surface has first-class inputs, visible artifacts, and honest failure—not only smoke scenarios.

---

## 3. Runtime shape (v1)

```text
┌─────────────────────────────────────────────────────────┐
│  Thin GUI  ·  harness gate  ·  (later: MCP / Remote)    │
│  → surface + goal + inputs → same run_manager()         │
└───────────────────────────┬─────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────┐
│  Manager: templates first · allowlists · gen_lock       │
│  Optional: LACERTA_LLM_DECOMPOSE (off by default)       │
└───────┬───────────┬───────────┬───────────┬─────────────┘
        │           │           │           │
   CodeWorker  LearnWorker ResearchWorker WritingWorker
   (tool loop) (recipes)   (recipes)      (recipes)
        │
   chat_answer (manager-local; no FS tools)
```

**Disk / syllabus.json remain sources of truth.** The GUI displays paths and summaries; it does not become the file SoT.

---

## 4. v1 product pillars

### 4.1 GUI depth

| Capability | v0 (L8) | v1 target |
|------------|---------|-----------|
| Surface tabs | Yes | Keep |
| Goal + root + Run | Yes | Keep |
| Job log (summaries) | Yes | Live/poll updates |
| Research attachments | API-only / empty | File picker + list |
| Deliverables | Path strings | Open/list viewer |
| Run history | None | Recent runs in-process |
| Code modes | Smoke only | Smoke **and** habit selectable |
| Chat | Single shot | Session continuity (multi-turn) |

Stack remains **stdlib HTTP + static UI** unless a later phase explicitly adopts a dependency (must stay thin; no second OS).

### 4.2 Surface depth

| Surface | v0 | v1 focus |
|---------|----|----------|
| **code** | smoke + habit (CLI) | Habit in GUI; clearer acceptance feedback |
| **learn** | syllabus_files | Tutor / assessment / archive chat recipes + GUI course view |
| **research** | offline local | Attachments UX; bounded web gather (honest, allowlisted) |
| **writing** | short dynamic | from_sources; multi-section pattern documented + GUI |
| **chat** | plain + optional light research | Multi-turn; context from prior turns |

### 4.3 Honesty & gates

- Templates remain default; LLM decompose stays flagged off.
- New GUI features get headless wiring tests; new recipes get harness scenarios where acceptance is disk-honest.
- Do not claim “reliable” for a surface without a green gate.

---

## 5. Deferred (explicit)

| Former phase | Topic | Status |
|--------------|-------|--------|
| L9 | MCP host | **Deferred** until after v1 |
| L10 | MCP client | **Deferred** |
| L11 | Remote companion / PWA | **Deferred** |
| L12 | Remote MCP SSE + lock polish | **Deferred** |

These remain first-class advantages in the blueprint; they wrap the same manager and must not invent a parallel brain. See [phases/README.md](phases/README.md).

---

## 6. v1 phase map

| Phase | Title | Exit (summary) |
|-------|-------|----------------|
| [V1.0](phases/phase-V1.0.md) | Charter + architecture | Docs landed; L9–L12 marked deferred |
| [V1.1](phases/phase-V1.1.md) | GUI product shell | Attachments, deliverable viewer, run history |
| [V1.2](phases/phase-V1.2.md) | Code depth in GUI | Habit mode selectable; acceptance visible |
| [V1.3](phases/phase-V1.3.md) | Learn depth | Tutor/assessment/archive + course UI |
| [V1.4](phases/phase-V1.4.md) | Research & writing depth | from_sources + bounded gather + GUI |
| [V1.5](phases/phase-V1.5.md) | Chat continuity & v1 exit | Multi-turn chat + full regression bar |

---

## 7. Architecture PR checklist (every v1 phase)

- [ ] Second orchestrator / LoopEngine in the GUI?
- [ ] Surface forked an engine instead of a template?
- [ ] Manager gained FS/web/shell tools?
- [ ] Worker context unbounded?
- [ ] Limits still in Python?
- [ ] Harness or headless test for the feature?
- [ ] Heal-tower / coach OS instead of schema fix?
- [ ] MCP/Remote sneak-in blocking v1 surface depth?
- [ ] Disk / syllabus still SoT?

---

## 8. Non-goals for v1

- MCP host/client productization  
- Remote phone PWA / mesh  
- Workflow GUI editor, persona calendar, plan-review dialogs  
- Multi-worker swarm / worker↔worker chat  
- Replacing Ollama with a cloud-only default  

---

## 9. Relationship to blueprint §8–§9

Blueprint build steps 1–8 are **done** (v0). Steps 9–10 (MCP/Remote) are **paused**. Insert the v1 phase map above before resuming integrations.
