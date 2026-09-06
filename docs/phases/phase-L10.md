# Phase L10 — MCP client (`mcp__*` allowlisted)

**Status:** planned  
**Depends on:** L9 exit; CodeWorker tools exist; L1–L6 still green  
**Exit:** One external server callable from a research job  

**Sources:** architecture §9.1 Client, §9.3; surfaces §13; port kit §12 L10, env `LACERTA_MCP_ALLOWED_SURFACES`.

---

## Goal

Allow Lacerta to call user-configured external MCP servers as allowlisted worker tools named `mcp__{server}__{tool}`, merged only when JobSpec/surface policy permits — default off for code/learn templates.

---

## Checkboxes

- [ ] `lacerta/integrations/mcp_client.py` — connect to configured servers (stdio; SSE later/with Remote)
- [ ] Config: user-enabled server list; optional per-instance overrides
- [ ] Tool naming: `mcp__{server}__{tool}`
- [ ] Merge into worker registries only when allowlist says so
- [ ] Default: MCP client tools **off** for code/learn template jobs
- [ ] Enable for research (and optionally writing/chat) via `LACERTA_MCP_ALLOWED_SURFACES` (default `research,writing,chat`)
- [ ] JobSpec.tools may include specific `mcp__*` names (still ≤4 for tool-loop jobs; recipe jobs call via capability if designed that way)
- [ ] Harness or integration test: one external mock/real server invoked from a research job
- [ ] Fail closed if server missing / tool not allowlisted
- [ ] Do not give manager direct MCP tool access

---

## Files

| Path | Action |
|------|--------|
| `lacerta/integrations/mcp_client.py` | Implement |
| Config schema (yaml/json/env) | Document |
| `lacerta/workers/research/…` | Optional capability wrapping MCP tools |
| `tests/test_mcp_client_allowlist.py` | Surface/JobSpec gating |
| `tests/fixtures/mcp_mock_server/` | Optional mock |

---

## Tests

```bash
pytest tests/test_mcp_client_allowlist.py -q
# Integration: research job with mcp__* tool → JobResult ok
```

---

## Harness command

```bash
# Prefer a dedicated scenario once stable, e.g. research_mcp_mini
./scripts/gate.sh research_local   # regression: still offline without MCP
```

**Pass criteria:** One external MCP server successfully used from a research job; code/learn default templates remain MCP-free.

---

## Architecture PR checklist

- [ ] Allowlisted only — not global tool dump
- [ ] Off for code/learn templates by default
- [ ] Same manager; no remote-mode engine
- [ ] Manager has no MCP tools
- [ ] Harness honesty unchanged for non-MCP scenarios

---

## Out of scope

Remote PWA, SSE host mount (L12), exposing all MCP tools in GUI without allowlist.
