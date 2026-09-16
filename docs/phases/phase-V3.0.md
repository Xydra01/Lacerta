# Phase V3.0 — Charter (UI / UX polish)

**Status:** planned (docs)  
**Depends on:** v2 exit (V2.5)  
**Exit:** architecture-v3 + phase map agreed; no product code required  

**Sources:** product feedback (replies buried in artifact JSON; formatting; generating feedback; leaked mode fields; darker themes).

---

## Goal

Lock a short v3 track before UI work: readable replies, formatting (including math), visible in-flight activity, mode-only inputs, and a couple of darker color schemes — without a new frontend stack or a second orchestrator.

---

## Checkboxes

- [x] Publish [architecture-v3.md](../architecture-v3.md) and link from [phases/README.md](README.md)
- [x] Split implementation into V3.1 (replies + formatting), V3.2 (activity), V3.3 (fields + themes + exit)
- [x] Confirm invariants: disk artifacts remain SoT; Replies panel is a view; L9–L12 stay deferred; no SPA framework; no CDN required for exit

---

## Files (expected)

| Path | Action |
|------|--------|
| `docs/architecture-v3.md` | Charter |
| `docs/phases/phase-V3.*.md` | Phase map |
| `docs/phases/README.md` | Index v3 track |

---

## Tests

Docs-only phase — no harness gate.

---

## Architecture PR checklist

- [x] No second orchestrator
- [x] No new GUI framework
- [x] MCP/Remote not required for v3 exit

---

## Out of scope

Implementation (starts V3.1).
