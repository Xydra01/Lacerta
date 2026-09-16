# Phase V3.2 — In-flight activity + buffered typing

**Status:** planned  
**Depends on:** V3.1 (Replies panel + formatter exist)  
**Exit:** While a run is going, the GUI shows step labels and the assistant reply grows in closed chunks (bold, italic, math only after their closers), so it looks like typing without flashing unfinished markdown  

**Sources:** architecture-v3; `OllamaClient.chat` today reads one JSON body (`stream` is sent but the response is not line-parsed); `pollRun` in [`app.js`](../../lacerta/gui/static/app.js).

---

## Goal

Runs can take a while. Show both what the job is doing and the reply as it forms. Do not break existing `client.chat()` callers.

---

## Approach (locked)

### Client (localized)

- `OllamaClient.chat` still **returns one dict** when the call finishes. `stream=False` stays the default (manager JSON, harness, `format=` calls unchanged).
- When `stream=True`, parse Ollama's newline-delimited JSON: accumulate `message.content`, invoke optional `on_delta(full_text_so_far)`, then return the same shape as a non-stream call.
- No other worker is required to pass `on_delta`. Tutor, Archive, and Chat wire it when a GUI run buffer is present. If the callback is absent, behavior matches today.

### Buffer

- GUI run holds `partial_reply: str` on the in-memory run record. `on_delta` writes it. `GET /api/runs/{id}` includes `partial_reply` while `status=running`.
- Disk turn files are still written only when the job finishes. The buffer is a view, not a second transcript store.

### Paint (delay on purpose)

- Poll remains the clock (about 300–500ms). No SSE.
- Renderer from V3.1 paints only a **closed prefix**:
  - complete lines
  - finished `**…**` and `*…*` / `_…_`
  - finished `$…$` / `$$…$$`
- An open marker stays in a raw tail and is shown as plain text, or hidden if it is an unclosed `$`. Never render half-written math.
- Step line above the reply: `Indexing sources`, `Retrieving`, `Generating reply`, `Grading`, else `Working`.
- On failure, drop the tail and show the error. On success, replace the growing row with the final rendered reply.

---

## Checkboxes

- [ ] `chat(stream=True)` parses NDJSON and still returns one dict; `stream=False` tests unchanged
- [ ] `on_delta` optional; callers that ignore it keep working
- [ ] Run poll exposes `partial_reply` during Tutor / Archive / Chat
- [ ] Replies panel grows on each poll using the closed-prefix rule
- [ ] Unclosed `$` or `**` does not render as a broken span
- [ ] Failure clears the generating row
- [ ] GUI README notes the typing behavior

---

## Files (expected)

| Path | Action |
|------|--------|
| `lacerta/core/ollama_client.py` | NDJSON parse + optional `on_delta` |
| `lacerta/gui/server.py` | Partial reply on the run record |
| `lacerta/workers/learn/capabilities.py` | Tutor/Archive pass `on_delta` when the run provides one |
| `lacerta/core/chat_local.py` | Same for chat |
| `lacerta/gui/static/app.js` | Poll paint of closed prefix |
| `tests/` | Stream parse without a live Ollama (feed lines) |

---

## Tests

```bash
pytest tests/ -q -k 'ollama or gui_api or tutor or archive or chat'
```

Manual: Tutor with Ollama — text appears in chunks; a `**bold**` phrase does not flash bold until the closer; `$E=mc^2$` appears only once both dollars are in.

---

## Architecture PR checklist

- [ ] `chat()` return type unchanged
- [ ] No SSE/WebSocket
- [ ] Partial text not written as the disk SoT until the job finishes
- [ ] Poll still single-flight (409 unchanged)

---

## Out of scope

True token-per-frame paint. Themes (V3.3). Changing non-GUI `chat()` call sites that do not need a live reply.
