# Lacerta v3 Architecture (UI polish)

**Status:** v3 exit met  
**Depends on:** v2 exit met (V2.0–V2.5)  
**Does not replace:** Supervisor–Worker blueprint; shared corpus; Learn recipes

| Doc | Role |
|-----|------|
| [Architecture v2](architecture-v2.md) | v2 exit baseline |
| [phases/README.md](phases/README.md) | Phase index including **v3** |

---

## 1. Version story

| Version | Meaning | Exit |
|---------|---------|------|
| **v2** | Learn UX + LLM tutor / mastery / practice / Archive | **Met** |
| **v3** | Readable conversation UI, activity feedback, field hygiene, themes | V3.3 exit |
| **Later** | MCP / Remote (L9–L12) | Still deferred |

**v3 is not a new orchestrator and not a new frontend stack.** The thin stdlib GUI stays. Polish is static HTML/CSS/JS plus whatever reply text the existing run payload already has.

---

## 2. North star

> A **Replies** panel shows the user’s question and the model’s answer as a conversation, not as raw JSON behind an artifact click.

> Replies render **newlines, `*italic*`, `**bold**`, and math** (`$…$` / `$$…$$`) so Tutor and Archive are readable.

> While a run is in flight, the UI shows **what is happening** (queued, indexing, retrieving) and the reply **types out** in closed chunks — not a silent button, and not half-written `**` or `$`.

> Controls that belong to one mode (**Draft title**, and any other leaked field) stay hidden everywhere else.

> The current green palette remains the default. Two darker schemes are one click away and persist in the browser.

---

## 3. Runtime shape (unchanged spine)

```text
GUI
  → POST /api/run
  → worker chat(stream=True, on_delta=…) writes a partial reply buffer
  → poll GET /api/runs/{id}   (no SSE; poll is the paint clock)
  → Replies panel renders only the closed markdown/math prefix
Disk artifacts remain SoT; the panel is a view, not a second transcript store.
```

- Chat already keeps an in-memory transcript. Tutor / Archive already persist turns on disk. V3 **displays** those; it does not invent a parallel chat engine.
- Job log and artifact list stay for debugging. They are not the way a user reads a reply.

---

## 4. Phase map

| Phase | Focus |
|-------|--------|
| [V3.0](phases/phase-V3.0.md) | Charter |
| [V3.1](phases/phase-V3.1.md) | Replies panel + markdown / math formatting |
| [V3.2](phases/phase-V3.2.md) | Step labels + buffered typing (closed markdown only) |
| [V3.3](phases/phase-V3.3.md) | Mode-field hygiene + color schemes + v3 exit |

---

## 5. v3 regression

pytest green for the GUI wiring and API checks. Prior v2 harness gates are not re-proven unless a GUI wiring test failed. Manual: Replies readable, activity visible while a run is in flight, Draft title absent on Tutor, theme switch sticks after reload. L9–L12 remain deferred.

---

## 6. Out of scope

- MCP / Remote (L9–L12)
- Replacing the stdlib HTTP GUI with a SPA framework
- A new streaming transport (SSE/WebSocket). Partial text rides the existing run poll.
- Changing `chat()`'s return type. Callers still get one finished dict; streaming is an optional `on_delta`.
- Cloud CDNs for math rendering (vendor locally if a math library is used)
- Changing tutor/archive prompts or corpus ingest
