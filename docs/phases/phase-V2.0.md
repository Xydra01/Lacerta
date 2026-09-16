# Phase V2.0 — Charter + Learn UX contracts

**Status:** done (docs charter landed with phase map)  
**Depends on:** v1 exit (V1.5) + V1.55 document extract  
**Exit:** v2 architecture doc + phase map agreed; Learn mode inventory and disk contracts sketched; no product code required  

**Sources:** [architecture-v2.md](../architecture-v2.md); attachment *V2 Improved thin UI…*; [architecture-v1.md](../architecture-v1.md) §4.3.

---

## Goal

Lock the v2 product story before UI/tutor code: decluttered thin GUI, LLM-style tutoring on shared corpus, mastery-aware Learn, interactive assessments, Archive chat — without forking a second orchestrator.

---

## Checkboxes

- [x] Publish [architecture-v2.md](../architecture-v2.md) and link from [phases/README.md](README.md)
- [x] Document Learn **submodes** (plain labels): Build syllabus · Index sources · Tutor · Assessment · Practice · Archive (exact labels may refine in V2.1)
- [x] Disk contracts (sketch only):
  - [x] `syllabus.json` remains SoT for nodes
  - [x] `mastery.json` (or per-node fields) for tiers `0..5`
  - [x] tutor session: turns + **compressed history digest** (char-capped)
  - [x] quiz / flashcard / study-guide artifact paths under course tree
- [x] Confirm architecture invariants: manager never holds chunk bodies; retrieve via ephemeral workers; Python caps; Mac/low-ctx history compression
- [x] Confirm L9–L12 remain deferred for v2 exit
- [x] Point V2.1–V2.5 at this charter

---

## Files (expected)

| Path | Action |
|------|--------|
| `docs/architecture-v2.md` | Charter |
| `docs/phases/phase-V2.*.md` | Phase map |
| `docs/phases/README.md` | Index v2 track |

---

## Tests

Docs-only phase — no harness gate. Optional: link-check phase files exist.

---

## Architecture PR checklist

- [ ] No second orchestrator invented in the charter
- [ ] Shared corpus remains one subsystem
- [ ] MCP/Remote not required for v2 exit

---

## Out of scope

Implementation (starts V2.1). Full quiz UI, LLM tutor, mastery engine.
