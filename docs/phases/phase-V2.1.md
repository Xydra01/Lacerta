# Phase V2.1 — Thin UI declutter (mode-scoped fields)

**Status:** done  
**Depends on:** V2.0  
**Exit:** Learn (and sibling surfaces as needed) show only fields relevant to the active mode; mode purpose is obvious without hunting dropdowns; headless surface wiring tests green  

**Sources:** architecture-v2 §2; attachment (thin UI mash / mode-specific fields).

---

## Goal

The thin GUI today piles options into one page and opaque dropdowns. Move **mode-specific** controls so they appear only for the active mode, reducing clutter while keeping stdlib HTTP + static UI (no second OS).

---

## Checkboxes

- [x] Inventory per-surface mode fields (Learn first: course id, attachments, refresh course, goal semantics, title, etc.)
- [x] Learn: panel / section that switches with Learn mode (Build syllabus · Index sources · Tutor · Assessment · … as landed)
- [x] Hide attachments unless mode `require_attachments` / `show_attachments`
- [x] Hide course browser controls when not Learn; clear empty states (“no syllabus yet”, “corpus pending|complete”)
- [x] Goal placeholder and primary CTA label reflect the active mode (plain language — no JobType jargon)
- [x] Code / Research / Writing already mode-scoped fields stay consistent with the same pattern
- [x] Chat transcript + Clear chat remain chat-only
- [x] CSS: one composition per mode panel — avoid dashboard card sprawl
- [x] `tests/test_gui_surface_wiring.py` / `test_gui_api.py`: scenario metadata drives visibility flags
- [x] Update GUI README manual smoke for decluttered Learn

---

## Files (expected)

| Path | Action |
|------|--------|
| `lacerta/gui/surfaces.py` | Richer per-scenario field flags |
| `lacerta/gui/static/index.html` / `app.js` / `app.css` | Mode panels |
| `lacerta/gui/README.md` | Manual smoke |
| `tests/test_gui_*.py` | Wiring |

---

## Tests

```bash
pytest tests/test_gui_surface_wiring.py tests/test_gui_api.py -q
```

---

## Architecture PR checklist

- [x] Still one manager / no SPA framework requirement
- [x] Surfaces still template-driven
- [x] No free JobType picker

---

## Out of scope

LLM tutor behavior (V2.2), mastery UI (V2.3), interactive quiz widgets (V2.4), Archive mode behavior (V2.5) — UI shells for future modes may be stubbed hidden until those phases.
