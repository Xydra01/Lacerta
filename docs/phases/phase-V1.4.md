# Phase V1.4 — Research & writing depth

**Status:** planned  
**Depends on:** V1.1 (attachments UX); L5/L6 green  
**Exit:** `writing.from_sources` and research-with-attachments are first-class in GUI; bounded web gather is either real or honestly stubbed with a clear gate  

**Sources:** architecture-v1 §4.2; `writing.from_sources`; `research.gather_web_sources`.

---

## Goal

Deepen research/writing beyond single offline/short paths: sources in, deliverables out, optional bounded web—without manager-held web tools.

---

## Checkboxes

- [ ] GUI: writing mode `short` vs `from_sources` (`tpl` or recipe_id via `write_from_sources`)
- [ ] Research: attachments required warning when list empty; preview report.md
- [ ] Implement or replace `gather_web_sources` stub with **bounded** fetch (domain allowlist / max pages)—worker-side only
- [ ] Template or flag for research offline vs light-web (keep `research_local` default)
- [ ] Harness: writing_from_sources or extend writing_short; research with fixture attachments still green
- [ ] Document advance_when / multi-section pattern for longer docs (Python-enforced)

---

## Files (expected)

| Path | Action |
|------|--------|
| `lacerta/workers/research/capabilities.py` | Bounded gather |
| `lacerta/workers/writing/*` | from_sources polish |
| `lacerta/core/routers/*` | Templates if needed |
| `lacerta/gui/*` | Modes + attachments |
| `lacerta/harness/scenarios.py` | New/extended scenarios |

---

## Tests

```bash
./scripts/gate.sh research_local --runs 1
./scripts/gate.sh writing_short --runs 1
pytest tests/test_writing_*.py tests/test_research_*.py -q
```

---

## Architecture PR checklist

- [ ] Manager still cannot call web_search
- [ ] Caps in Python (max pages/bytes)
- [ ] Recipes remain primary for these surfaces

---

## Out of scope

Full browser agent, unrestricted crawl, MCP external search servers (L10 deferred).
