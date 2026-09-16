# Phase V3.1 — Replies panel + formatting

**Status:** done  
**Shipped:** formatter is `lacerta/gui/format_reply.py` (`closed_prefix`, `render_html`); the browser inserts `reply_html` and typesets with vendored temml. Chat history stays in memory; Tutor/Archive history is the existing disk index via `GET /api/learn/turns`.  
**Depends on:** V3.0  
**Exit:** Chat, Tutor, and Archive replies appear in a dedicated conversation panel with history; newlines, `*italic*`, `**bold**`, and `$…$` / `$$…$$` math render; users do not have to open raw JSON artifacts to read an answer  

**Sources:** architecture-v3 §2–3; current GUI (`#preview` is a mono dump of artifact text; chat transcript is `white-space: pre-wrap` only).

---

## Goal

Today the only readable model output is an artifact click that shows raw JSON (`reply` buried in tutor/archive turn files) or an unformatted chat blob. Add a **Replies** section that keeps a visible Q/A history and renders lightweight markdown plus math.

Artifact list + Preview stay for disk debugging. They are not the conversation UI.

---

## Approach (locked)

- Still the thin static GUI. No React/Vue. No CDN.
- Panel id: `#replies` in [`lacerta/gui/static/index.html`](../../lacerta/gui/static/index.html), rendered from [`app.js`](../../lacerta/gui/static/app.js).
- One transcript per surface session in the page:
  - **Chat:** existing in-memory `chatMessages`, rendered here (existing `#chatTranscript` can fold into this panel or stay as the same list — do not keep two divergent histories).
  - **Tutor / Archive:** after a successful run, append `{role, text, ts}` from the job result `reply` (or the written turn JSON `reply` field). Prior turns for the open course can be loaded from `tutor/` / `archive/` history index via a thin read-only endpoint (reuse course root; do not invent a second transcript file).
  - **Code / Research / Writing:** show the latest assistant/user-facing summary in the same panel when the run finishes (deliverable title + short status is enough if there is no prose reply). Do not force those modes into a fake chat.
- Formatter (client-side, escape HTML first):
  - `\n` → line breaks
  - `**bold**` and `*italic*` (and `_italic_`)
  - inline `` `code` `` and fenced code blocks
  - `$…$` inline and `$$…$$` display math
- Math: vendor a small local renderer under `lacerta/gui/static/vendor/` (KaTeX or temml — pick one, ship the files, no network at runtime). Unparseable math stays as the source text, not a blank.
- Do not interpret artifact JSON as the message. Extract `reply` / chat `content` before render.

---

## Checkboxes

- [x] `#replies` section: scrollable history, user vs assistant labels, newest at bottom
- [x] Chat turns render in that panel (not only a pre-wrap dump)
- [x] Tutor and Archive successful runs append the synthesized (or paste) reply without clicking Artifacts
- [x] Safe HTML (escape first); newlines, bold, italic, code work
- [x] Math `$` / `$$` renders locally; failure falls back to source text
- [x] Preview/artifacts still work for raw JSON
- [x] Unit or static fixture test for the formatter (bold, italic, newline, math delimiters preserved or rendered) — extract a small pure function so pytest can cover it without a browser if practical; otherwise a documented manual check plus a JS-free Python twin of the escape rules is not required if the function lives in JS — prefer a tiny Python-free check in existing GUI tests only for payload shape (`reply` exposed on run result)

---

## Files (expected)

| Path | Action |
|------|--------|
| `lacerta/gui/static/index.html` | Replies section |
| `lacerta/gui/static/app.js` | History + formatter |
| `lacerta/gui/static/app.css` | Reply bubbles (theme tokens, not hardcoded greens) |
| `lacerta/gui/static/vendor/` | Local math assets |
| `lacerta/gui/server.py` | Expose `reply` on run payload if missing; optional list of recent tutor/archive turns |

---

## Tests

```bash
pytest tests/ -q -k 'gui or reply or tutor or archive'
```

Manual: Tutor question → answer visible in Replies with a line break and bold; a `$E=mc^2$` snippet renders; artifact JSON still opens from Artifacts.

---

## Architecture PR checklist

- [x] No second transcript store that diverges from disk turns
- [x] HTML escaped before markdown
- [x] Math assets local

---

## Out of scope

Activity and buffered typing (V3.2). Themes and draft-title leak (V3.3). The formatter must expose a closed-prefix split so V3.2 can paint incomplete replies without half-open `**` or `$`.
