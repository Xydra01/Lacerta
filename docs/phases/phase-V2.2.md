# Phase V2.2 — LLM tutor + ephemeral retrieve + compressed history

**Status:** done  
**Depends on:** V2.0; V1.35 corpus retrieve; V1.5 multi-turn patterns; Ollama available for tutor LLM path  
**Exit:** Tutor synthesizes a teaching reply from retrieved chunks (not raw dump alone); history is lite-compressed for Mac/low context; harness proves grounded teaching on mini-book fixture  

**Sources:** architecture-v2; attachment (interactive tutor / ephemeral agents / compressed history).

---

## Goal

Corpus retrieve is raw data gathering. Tutor must **teach**: send ephemeral retrieve (existing `corpus.retrieve`), synthesize with LLM, engage the learner. Manager stays expert only for the moment — optional **compressed history digest**, not unbounded transcript.

---

## Checkboxes

### Retrieve → teach

- [x] Tutor recipe: `corpus.retrieve` (worker) → synthesize teaching reply (worker-local or manager-local LLM) using **retrieved text only** + syllabus node focus if present
- [x] Deterministic fallback when Ollama down: keep current retrieve paste **or** short template reply — honest, labeled
- [x] Citations remain in artifact (`chunk_id` / source / heading)
- [x] Manager prompts still must not include full corpus — only digests / top-k already retrieved by worker

### Session / history (Mac)

- [x] Tutor session turns on disk under course `tutor/`
- [x] Build **compressed history**: rolling summary ≤ N chars / M turns (Python caps; default fit `num_ctx=8192` Mac profile)
- [x] Client or server passes prior compressed digest + last K raw turns into next tutor job
- [x] Clear / new tutor session control in GUI (after V2.1 panel)

### Honesty

- [x] Harness or unit: mini-book indexed → tutor question about planted fact → reply mentions fact **and** reads as a tutor turn (not only chunk dump) when LLM mock/client present
- [x] Unit: history compressor enforces caps
- [x] Vague goals (“tutor me on C++”) may still retrieve poorly — document that users should ask topical questions; optional: rewrite query via tiny LLM step (same job, capped) — **deferred**; documented in tutor hint / README

---

## Files (expected)

| Path | Action |
|------|--------|
| `lacerta/workers/learn/capabilities.py` | Synthesize path + history |
| `lacerta/workers/learn/storage.py` | Session / digest paths |
| `lacerta/core/routers/learn.py` | Template inputs |
| `lacerta/gui/*` | Tutor session UX |
| `tests/test_learn_*.py` / harness | Grounded tutor gate |

---

## Tests

```bash
pytest tests/ -q -k 'tutor or learn_depth or corpus or history_digest or tutor_v22'
./scripts/gate.sh learn_tutor_grounded --runs 1
./scripts/gate.sh learn_corpus_retrieve --runs 1
```

---

## Architecture PR checklist

- [x] Ephemeral retrieve only — no manager-held book
- [x] History caps in Python
- [x] Recipes remain primary
- [x] No second LearnRAG stack

---

## Out of scope

Mastery gating of examples (V2.3), interactive MC UI (V2.4), Archive-as-chat productization (V2.5 — may share synthesize helper).
