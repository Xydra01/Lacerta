# Lacerta v2 Architecture

**Status:** **v2 exit met**  
**Depends on:** v1 exit met (V1.0–V1.55)  
**Does not replace:** Supervisor–Worker blueprint; shared corpus (§4.3 still SoT)

| Doc | Role |
|-----|------|
| [Architecture v1](architecture-v1.md) | v1 exit baseline |
| [phases/README.md](phases/README.md) | Phase index including **v2** |
| Attachment | *V2 Improved thin UI, improved UX, and Full LLM-style tutoring* |

---

## 1. Version story

| Version | Meaning | Exit |
|---------|---------|------|
| **v1** | Local product shell + corpus + multi-turn chat | **Met** |
| **v2** | Usable Learn UX + LLM-grounded tutoring/assessment/archive; decluttered thin GUI | **Met** (V2.5) |
| **Later** | MCP / Remote (L9–L12) | Still deferred unless explicitly resumed |

**v2 is not a second orchestrator.** Surfaces still pick templates; workers stay ephemeral; disk (`syllabus.json`, `corpus.json`, mastery files) remains SoT.

---

## 2. North star (v2 adds)

> Mode-specific UI that only shows fields for the active Learn (or other) mode — no mashed dropdown-only control surface.

> Tutor that **teaches**: ephemeral workers retrieve top-k from the shared corpus; the manager-local or worker LLM synthesizes a short teaching reply with **lite compressed history** (Mac / low `num_ctx`).

> **Progress-aware** Learn: mastery 0–5 per syllabus node; assessments and examples match current mastery; interactive MC quizzes preferred for honest grading.

> Separate **Archive** Learn submode: corpus-grounded LLM chat (humanized Q&A), distinct from teaching Tutor.

> **STEM-aware ingest (V2.35):** tables, equations, and figures become **text surrogates** inside corpus chunks so tutor/practice/archive can reason about them without the manager holding images.

---

## 3. Runtime shape (unchanged spine)

```text
GUI (decluttered modes)
  → run_manager (templates / allowlists / gen_lock)
      → learn / corpus workers (retrieve top-k only)
      → optional LLM synthesize (worker or manager-local chat path)
Disk: syllabus.json · corpus/ · mastery.json · tutor turns · quiz artifacts
```

**Hard rules**

- Manager never holds full chunk bodies / embeddings in prompts — only `corpus_id`, node ids, mastery summaries, compressed history digests.
- Retrieve caps stay in Python (`top_k`, `max_chars`).
- One shared corpus subsystem (no LearnRAG fork).
- No CodeWorker FS toolkit on learn jobs.

---

## 4. Phase map

| Phase | Focus |
|-------|--------|
| [V2.0](phases/phase-V2.0.md) | Charter + UX/Learn contracts |
| [V2.1](phases/phase-V2.1.md) | Thin UI declutter (mode-scoped fields) |
| [V2.2](phases/phase-V2.2.md) | LLM tutor + ephemeral retrieve + compressed history |
| [V2.3](phases/phase-V2.3.md) | Mastery 0–5 + progress-aware prompting |
| [V2.35](phases/phase-V2.35.md) | Structured corpus ingest (tables, math, figure surrogates) |
| [V2.4](phases/phase-V2.4.md) | Interactive MC quizzes, practice, flashcards, study guides |
| [V2.5](phases/phase-V2.5.md) | Archive LLM chat submode + v2 exit bar |

---

## 5. Learn submodes (plain labels)

| Submode | Job |
|---------|-----|
| Build syllabus | Existing structure recipes |
| Index sources | Shared corpus multi-pass index |
| Tutor | Retrieve → LLM **teach** + compressed history |
| Assessment | Mastery check (MC preferred) matching tier 0–5 |
| Practice | Generated MC quizzes, flashcards, study guides |
| Archive | Corpus-grounded LLM Q&A (not teaching path) |

Exact GUI labels may refine in V2.1; Tutor vs Archive stay distinct roles.

## 6. Disk contracts (sketch)

| Artifact | Role |
|----------|------|
| `syllabus.json` | Nodes SoT |
| `corpus/` + `corpus.json` | Shared index (v1 §4.3); chunk text may include `[table]` / `[math]` / `[figure]` surrogates (V2.35) |
| `mastery.json` | Per-node tier `0..5` SoT (syllabus `mastery_tier` mirrored); fail leaves tier unchanged |
| `tutor/turn_*.json` | Per-turn Q/A + citations + grounding |
| `tutor/history_digest.json` | Lite compressed session digest (≤1500 chars; Mac/`num_ctx=8192`) |
| `tutor/tutor_history.json` | Index of recent turns (paths only) |
| `archive/turn_*.json` | Archive Q&A + citations + grounding (`corpus_archive` or labeled retrieve paste) |
| `archive/history_digest.json` | Lite compressed archive session (separate from tutor) |
| `archive/history_index.json` | Index of recent archive turns |
| `assessments/mastery_check_{node}.json` | Short MC mastery check (Python-graded) |
| `assessments/` · `practice/` | Quiz JSON, flashcards, study guides |

## 7. Out of scope for v2

- MCP host/client, Remote PWA (L9–L12)
- Unrestricted web crawl as default tutor data path
- Cloud embedding / cloud vision APIs / surprise model downloads
- Perfect OCR of every scanned textbook page (V2.35: best-effort surrogates + honest placeholders)
- Second “coach OS” or heal-tower outside recipes

## 8. v2 regression matrix

**v2 exit met.** L9–L12 (MCP host/client, Remote) remain **deferred** — not required for this exit.

```bash
python -m pytest tests/ -q
./scripts/gate.sh learn_syllabus_files --runs 1
./scripts/gate.sh learn_corpus_retrieve --runs 1
./scripts/gate.sh learn_corpus_structured --runs 1
./scripts/gate.sh learn_tutor_grounded --runs 1
./scripts/gate.sh learn_quiz_roundtrip --runs 1
./scripts/gate.sh learn_archive_chat --runs 1
./scripts/gate.sh writing_short --runs 1
./scripts/gate.sh writing_from_sources --runs 1
./scripts/gate.sh research_local --runs 1
./scripts/gate.sh research_corpus_bulk --runs 1
```

GUI manual (Learn): decluttered modes; tutor teach; mastery visible; MC practice; archive chat (Index sources first; STEM tables/math as text surrogates after re-index).
