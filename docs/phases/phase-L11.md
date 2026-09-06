# Phase L11 — Remote companion (pair + PWA + surface launch)

**Status:** planned  
**Depends on:** L9 (host concepts) + core L1–L6 green; L10 optional  
**Exit:** Phone/PWA completes a learn or research job  

**Sources:** architecture §9.2–§9.4; surfaces §13; port kit §12 L11, `LACERTA_REMOTE_PORT`.

---

## Goal

Ship a thin Remote companion: private mesh → small host API → **same manager**, with pair/revoke auth, surface launch, job status, and deliverable download — not a second agent OS on the phone.

---

## Checkboxes

- [ ] `lacerta/remote/` host API (default port `LACERTA_REMOTE_PORT=8800`)
- [ ] Network: private mesh first (e.g. Tailscale); **no** public port-forward by default
- [ ] Auth: host ID + one-time pair code → long-lived device token (**store hash only**); revoke CLI
- [ ] API: chat stream, surface launch, job status, deliverable download, Ollama start/stop (as needed)
- [ ] Thin PWA: surface switcher (chat / code status / learn / research / writing)
- [ ] PWA launches learn or research template jobs through manager
- [ ] Shared generation lock with GUI/MCP so clients never double-generate
- [ ] No orchestration logic in the PWA
- [ ] Manual exit: phone on mesh completes learn **or** research job; deliverable downloadable

---

## Files

| Path | Action |
|------|--------|
| `lacerta/remote/api.py` | Host API |
| `lacerta/remote/auth.py` | Pair / token hash / revoke |
| `lacerta/remote/pwa/` | Thin frontend |
| `lacerta/remote/cli_revoke.py` or scripts | Revoke device |
| `tests/test_remote_auth.py` | Pair + revoke |
| Docs: mesh setup notes | README section |

---

## Tests

```bash
pytest tests/test_remote_auth.py -q
# Manual mesh + PWA run for learn or research
```

---

## Harness command

```bash
./scripts/gate.sh learn_syllabus_files   # or research_local — regression
# Exit demo: PWA completes equivalent job against same evaluate contracts
```

**Pass criteria:** Phone PWA completes a learn or research job over private mesh with paired token; revoke works.

---

## Architecture PR checklist

- [ ] Remote is thin client over manager + storage
- [ ] No parallel remote agent / second brain
- [ ] Pair + revoke — do not trust open LAN alone
- [ ] Generation lock shared
- [ ] Surfaces still templates, not forked engines
- [ ] MCP SSE mount can wait for L12

---

## Out of scope

Public internet exposure by default; full MCP SSE polish (L12); workflow editors on mobile.
