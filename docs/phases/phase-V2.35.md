# Phase V2.35 — Structured corpus ingest (tables, math, figures)

**Status:** done  
**Depends on:** V1.55 extract; V1.35 corpus index; V2.3 done (practice/tutor already consume retrieve)  
**Exit:** Indexing PDFs/notes that contain tables, equations, or figures yields **text surrogates** in corpus chunks that tutor/practice/archive can retrieve and an LLM can use; harness proves a planted table cell and math token survive retrieve  

**Sources:** product need (math / STEM tutoring); architecture-v2 §3 (manager never holds binaries); shared corpus only.

---

## Goal

Plain `pypdf` extract drops or mangles tables, graphs, and math. STEM tutoring needs those structures as **bounded text in chunks** — not raw images in the manager. Extend extract → chunk so figures become captions/descriptions, tables become markdown/TSV, and math becomes TeX-like or tagged plain lines.

---

## Approach (locked)

- Still **one** corpus subsystem; no vision tower in the manager.
- Store **text surrogates** only in chunk bodies (and optional `kind` metadata: `prose` | `table` | `math` | `figure`).
- Prefer **offline / local** paths: PDF text layer + table heuristics first; optional local LLM/vision describe for embedded images (flagged, capped pages).
- Honest labels when transcription fails: `[figure: unreadable — caption: …]` / `[table: extract failed]`.
- Caps in Python (max figures per doc, max table chars, max describe calls).

```text
PDF/DOCX → extract_structured
  → prose + [table] markdown + [math] lines + [figure] descriptions
  → existing chunk → map → embed → retrieve
```

---

## Checkboxes

### Extract enrichment (`lacerta/storage/extract.py` + helpers)

- [x] Tables: detect grid-ish PDF/HTML/CSV regions → emit markdown table or TSV block wrapped with `[table]` … `[/table]` (or equivalent stable markers)
- [x] Math: preserve TeX-like `$...$` / `$$...$$` when present in text layer; Unicode operators kept; tag dense formula lines `[math]`
- [x] Figures: pull caption text from PDF when available; optional **local** describe step (Ollama multimodal *or* stub) → `[figure] caption: …; description: …`
- [x] When image bytes exist but no describe client: still emit caption/placeholder — never silently drop the figure slot
- [x] Optional deps documented (`[extract]` grows only if needed; Mac-friendly; no surprise cloud APIs)

### Corpus pipeline

- [x] `corpus.extract` / chunk path accepts structured text without breaking existing mini-book gate
- [x] Chunk metadata may include `kind` for retrieve boost later (optional; prose default)
- [x] Re-index is explicit (user re-runs Index sources) — no silent background rewrite of old corpora required for exit

### Honesty

- [x] Fixture PDF or markdown with planted `LACERTA_TABLE_CELL_42` in a table and `LACERTA_MATH_TOKEN_π` in an equation line
- [x] Harness/unit: index → retrieve query about the table/math → chunk text contains planted tokens
- [x] Unit: extract on fixture does not require network
- [x] Document limits: scanned page with only a bitmap graph may need local describe; without it, tutor sees placeholder only

---

## Files (expected)

| Path | Action |
|------|--------|
| `lacerta/storage/extract.py` (+ `extract_structured.py` if large) | Table/math/figure surrogates |
| `lacerta/workers/corpus/capabilities.py` | Pass-through / meta |
| `tests/fixtures/learn/` | `mini_stem.md` or small PDF fixture |
| `tests/test_extract_structured.py` / harness | Planted token retrieve |
| `docs/getting-started.md` / GUI README | STEM index notes |

---

## Tests

```bash
pytest tests/ -q -k 'extract or structured or stem or table or math'
./scripts/gate.sh learn_corpus_structured --runs 1
./scripts/gate.sh learn_corpus_retrieve --runs 1
```

---

## Architecture PR checklist

- [x] No manager-held image bytes / full PDF pages
- [x] Caps on describe calls and table size in Python
- [x] One corpus subsystem (learn + research consumers)
- [x] Cloud vision APIs not required for exit

---

## Out of scope

Full OCR of every scanned page as default; Guaranteed perfect graph digitization; Separate “MathRAG” engine; Practice UI (V2.4); Archive productization (V2.5 — consumes this automatically via retrieve).
