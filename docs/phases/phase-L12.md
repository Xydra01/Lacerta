# Phase L12 — Remote MCP SSE mount + generation lock polish

**Status:** deferred (after v1)  
**Depends on:** L9 MCP host + L11 Remote companion  
**Exit:** Same host tools over mesh + token  

**Deferred:** See [architecture-v1.md](../architecture-v1.md). Resume after v1; not abandoned.
**Sources:** architecture §9.1 transports, §9.2 MCP mount, §9.4 L12; surfaces §13; port kit §12 L12.

---

## Goal

Mount the same MCP **host** meta-tools over SSE at the Remote API with Bearer device token, and polish the shared generation lock so GUI, stdio MCP, and Remote never double-generate.

---

## Checkboxes

- [ ] SSE endpoint e.g. `/api/mcp/host/sse` exposing the **same** host meta-tool catalog as L9
- [ ] Auth: Bearer device token (paired in L11); reject unauthenticated
- [ ] Behavior parity: `lacerta_run_scenario` / `lacerta_run_surface` / health / deliverable read match stdio host
- [ ] Generation lock: single-flight across GUI, MCP stdio, Remote, SSE
- [ ] `lacerta_release_generation_lock` clears stale locks safely
- [ ] Document Tailscale (or mesh) + token setup for remote MCP clients
- [ ] Integration test or scripted check: SSE client runs smoke; evaluate matches CLI
- [ ] Confirm still no raw FS tool exposure over MCP

---

## Files

| Path | Action |
|------|--------|
| `lacerta/remote/mcp_sse.py` | SSE mount |
| `lacerta/integrations/mcp_host.py` | Share tool handlers with SSE |
| `lacerta/core/generation_lock.py` | Polish lock primitive |
| `tests/test_mcp_sse_auth.py` | Auth + lock |
| Docs: remote MCP client config | Update |

---

## Tests

```bash
pytest tests/test_mcp_sse_auth.py -q
./scripts/gate.sh smoke_write_file --runs 1
# Manual/scripted: SSE + token → lacerta_run_scenario smoke
```

---

## Harness command

```bash
./scripts/gate.sh smoke_write_file --runs 1
# Plus mesh SSE path; acceptance identical to local harness
```

**Pass criteria:** Same host tools available over private mesh with device token; lock prevents concurrent generations; L1–L6 scenarios still green.

---

## Architecture PR checklist

- [ ] Same manager + same evaluate — no fork
- [ ] Small meta-tool surface only
- [ ] Auth required on SSE
- [ ] Lock shared across all entry points
- [ ] Not a second product brain
- [ ] Core surfaces remain harness-honest

---

## Out of scope

New product surfaces, swarm parallelism, public unauthenticated MCP, rewriting workers for remote-specific engines.

---

## After L12

Lacerta v0 integration story is complete: local-first Supervisor–Worker core, four recipe/tool surfaces, thin GUI, MCP host/client, and Remote companion. Further work is product polish and post-v0 learn features (placement diagnostic, analytics) per surfaces non-goals — each with new phase docs and harness scenarios before claims of reliability.
