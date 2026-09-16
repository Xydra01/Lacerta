# Phase V3.3 — Mode fields + color schemes + v3 exit

**Status:** done  
**Depends on:** V3.1, V3.2  
**Exit:** Mode-only inputs stay hidden (Draft title only on Writing modes that use it); default green theme plus two selectable darker schemes persist locally; v3 regression note in architecture-v3  

**Sources:** architecture-v3; leak: Writing `show_title` is a **surface** flag ([`surfaces.py`](../../lacerta/gui/surfaces.py) writing defaults), and [`updateSurfaceFields`](../../lacerta/gui/static/app.js) hides `#titleWrap` from that flag only — not from the active scenario. Other chrome (`#nodeWrap`, course browser, attachments) must be re-checked the same way. CSS: if a rule sets `display` on `.field`, it can override the `hidden` attribute and show controls on every tab.

---

## Goal

Finish the short polish track: no Writing-only (or Learn-only) boxes on Chat, Code, Research, or the wrong Learn/Writing submode; offer darker palettes without dropping the current green.

---

## Approach (locked)

### Fields

- Visibility is **scenario-scoped**, not surface-scoped, for optional chrome:
  - Draft title: only Writing scenarios that need a title (short draft). Hidden on From sources if that mode does not use it, and hidden on every non-writing surface.
  - Re-apply hide on surface **and** scenario change (`applyScenarioModeFields`), not only when the tab first loads.
- CSS: `[hidden] { display: none !important; }` so grid/flex field rules cannot reveal hidden controls.
- Add per-scenario `show_title` (and audit `show_node_id`, `show_attachments`, course chrome) in `LEARN_SCENARIOS` / `WRITING_SCENARIOS`. Wiring tests assert Draft title is off for chat, learn, code, research.

### Themes

- CSS variables already in `:root` ([`app.css`](../../lacerta/gui/static/app.css)). Do not hardcode a second palette in component rules.
- Three schemes, selectable in the header (plain labels):
  - **Grove** — current light green (default)
  - **Dusk** — dark green
  - **Ink** — near-black with the same accent family
- Persist choice in `localStorage` (`lacerta-theme`). No account, no server setting.
- Contrast: body text readable on each scheme (ink on light, light text on dark). Replies panel, job log, and inputs all use the tokens.

### Exit

- Mark this phase done when the checks pass.
- Add a short v3 regression blurb to [architecture-v3.md](../architecture-v3.md): pytest green; prior v2 gates not required to be re-proven unless a GUI wiring test failed; manual: Replies readable, activity visible, draft title absent on Tutor, theme switch sticks after reload.
- L9–L12 remain deferred.

---

## Checkboxes

- [x] Draft title hidden unless the active Writing scenario sets `show_title`
- [x] `[hidden]` cannot be overridden by `.field` display rules
- [x] Scenario change and surface change both re-hide leaked fields (node id, attachments, course chrome, draft title)
- [x] Wiring test: chat/learn/code/research do not expose `show_title`
- [x] Theme switcher: Grove / Dusk / Ink; persists across reload
- [x] architecture-v3 status **v3 exit met**; phases README row updated
- [x] GUI README: replies, activity, themes, draft-title note

---

## Files (expected)

| Path | Action |
|------|--------|
| `lacerta/gui/surfaces.py` | Per-scenario `show_title` |
| `lacerta/gui/static/app.js` / `index.html` / `app.css` | Hide + themes |
| `tests/test_gui_surface_wiring.py` | Title flag |
| `docs/architecture-v3.md` | Exit met |
| `lacerta/gui/README.md` | Smoke |

---

## Tests

```bash
pytest tests/ -q -k 'gui_surface or gui_api'
```

Manual: switch Chat → Learn Tutor → Writing; Draft title only on the writing mode that needs it. Switch to Dusk, reload, still Dusk.

---

## Architecture PR checklist

- [x] No new backend theme store
- [x] L9–L12 still deferred
- [x] Prior reply/activity behavior from V3.1–V3.2 still works under all three themes

---

## Out of scope

Custom theme editor, system-font changes, MCP/Remote. Buffered typing stays as shipped in V3.2 (no SSE).
