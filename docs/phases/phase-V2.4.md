# Phase V2.4 — Interactive practice: MC quizzes, flashcards, study guides

**Status:** done  
**Depends on:** V2.3 mastery; V2.2 retrieve/synthesize helpers; **V2.35 structured corpus ingest** (STEM tables/math/figures as text surrogates); V1.35 corpus optional for grounding  
**Exit:** User can generate and take interactive multiple-choice practice; create flashcards and study-guide artifacts; results can update mastery; disk-honest grading; practice grounding can cite structured chunks when indexed  

**Sources:** architecture-v2; attachment (interactive MC, practice assessments, flashcards, study guides); V2.35 STEM ingest.

---

## Goal

Replace “assessment JSON only” with **usable practice**: multiple-choice quizzes (easy for AI + harness to grade), optional later re-take, interactive flashcards, and study-guide artifacts synthesized from syllabus section ± corpus retrieve.

When the course corpus was indexed after V2.35, retrieve may return `[table]` / `[math]` / `[figure]` surrogates — practice generation and study guides should prefer those chunks for STEM nodes instead of ignoring them.

---

## Checkboxes

### Artifacts (disk SoT)

- [x] Quiz schema: questions with `choices[]`, `correct_index` or `correct_id`, `node_id`, `target_tier`, citations optional
- [x] Paths under course: e.g. `assessments/quiz_*.json`, `practice/flashcards_*.json`, `practice/study_guide_*.md`
- [x] Generate from section + mastery (± `corpus.retrieve` for that node’s topic)
- [x] When retrieved chunks include structured markers (`[table]`, `[math]`, `[figure]`), quiz/study-guide prompts may use them; never invent table numbers not present in retrieve

### Interactive GUI (thin)

- [x] Learn mode **Practice** (or Assessment deepened): render MC one question at a time or list; submit → score
- [x] Grade in Python/server: compare selected choice to key; write attempt record
- [x] Optional: on mastery-check quizzes, call mastery increment (V2.3) — Mastery check mode retains tier bumps; Practice does not auto-bump
- [x] Flashcards: front/back flip in static UI; deck from generated JSON
- [x] Study guide: generate markdown artifact + preview (existing `/api/preview`); STEM guides may embed retrieved markdown tables

### Honesty

- [x] Harness: generate quiz for fixture course → attempt with correct answers → score 100%; wrong answers scored honestly
- [x] Unit: quiz JSON validation; reject malformed LLM output
- [x] Deterministic quiz generator fallback when Ollama down (template MC from node titles) so gates stay green
- [x] Optional gate: STEM fixture course — practice or study guide cite planted table/math token when V2.35 index present

---

## Files (expected)

| Path | Action |
|------|--------|
| `lacerta/workers/learn/*` | generate quiz / flashcards / study guide caps |
| `lacerta/gui/static/*` | MC + flashcard interaction |
| `lacerta/gui/server.py` | grade/attempt endpoints if needed (keep thin) |
| `lacerta/harness/scenarios.py` | `learn_quiz_roundtrip` |
| `tests/` | quiz + GUI wiring |

---

## Tests

```bash
pytest tests/ -q -k 'quiz or flashcard or study_guide or assessment or practice or mastery'
./scripts/gate.sh learn_quiz_roundtrip --runs 1
./scripts/gate.sh learn_corpus_structured --runs 1
```

---

## Architecture PR checklist

- [x] Grading in Python (not “LLM said you passed”)
- [x] Retrieve caps if corpus-grounded generation
- [x] No manager-held full textbook or figure binaries

---

## Out of scope

Free-response essay grading, adaptive IRT, Anki sync, mobile-native UI. New extract formats belong in V2.35 (this phase only *consumes* structured chunks).
