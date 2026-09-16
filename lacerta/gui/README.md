# Lacerta thin GUI

Local stdlib HTTP UI (`http.server`) that calls `run_manager` in-process. Not a second orchestrator.

## Run

```bash
python3 -m lacerta.gui
# optional:
python3 -m lacerta.gui --host 127.0.0.1 --port 8765
```

Open http://127.0.0.1:8765/

Stack choice: **stdlib only** (no Gradio/Streamlit/FastAPI) so runtime deps stay pydantic-only.

## Manual smoke (macOS)

1. Start Ollama with `lacerta:latest` (needed for **chat** and Code **Quick file check**).
2. Launch GUI; leave surface on **Code**; **Run check** = Quick file check; CTA reads **Run check**; goal: create `harness_smoke.py` that prints `HARNESS_OK`.
3. Confirm job log shows plan / jobs, **Acceptance: pass** when the file is on disk, and preview works.
4. Switch **Run check** to **Habit tracker (scaffold + tests)** (no Ollama required when deterministic). CTA becomes **Build habit tracker**. Confirm plan + acceptance.
5. Switch to **Learn**; **Learn mode** = Build syllabus — course chrome visible, attachments required, CTA **Build syllabus**. Attach notes path; run; **Refresh course** → syllabus nodes + `corpus: pending`.
6. Switch Learn mode to **Index sources** — attachments stay visible/required; CTA **Index sources**. Attach textbook/notes (`.md`/`.txt`/`.pdf`/`.docx`/`.html`/`.csv`); run; **Refresh course** → `corpus: complete` with chunk count. PDF/DOCX need `pip install -e ".[extract]"` (included in `[dev]`). After upgrading Lacerta, **re-run Index sources** so tables/math/figures become `[table]` / `[math]` / `[figure]` text surrogates in chunks (scanned bitmap-only pages stay placeholders unless you enable a local describe path later).
7. Switch Learn mode to **Tutor** — attachments hidden; CTA **Ask tutor**; ask a **topical** question after Index sources. With Ollama up, reply teaches from retrieved chunks at the node’s mastery band (0–5). **Clear tutor session** resets digest/history. Course list shows `mastery N/5` per node.
8. **Assessment** generates practice checks (difficulty follows Node id mastery). **Mastery check** mode requires Node id → generate MC → answer radios → **Submit mastery check** (pass increments tier; fail leaves unchanged). **Practice** mode: generate interactive MC (Python-graded, no mastery bump), **Flashcards** flip deck, **Study guide** markdown + preview; grounds on corpus when indexed (incl. `[table]`/`[math]`/`[figure]`).
9. **Archive** — exploratory Q&A after Index sources (not tutoring). With Ollama up, reply synthesizes from retrieved chunks; otherwise a labeled retrieve paste. **Clear archive session** resets archive history only.
10. Switch to **Research**; **Research mode** = Offline sources (attachments required); CTA **Research offline**. Large attachment sets auto-use keyword corpus bulk. **Light web (deferred)** fails honestly.
11. Switch to **Writing**; **Writing mode** = Short draft or From sources (attachments only for From sources); CTA updates per mode. **Draft title** appears only on Short draft.
12. Switch to **Chat** — workspace root hidden; **Clear chat**; CTA **Send**. Answers land in **Replies** (not a second transcript). Follow-up keeps prior turns in memory. Job log polls while running. Draft title is hidden.
13. Concurrent run → **409**. No free JobType picker — only surface tabs + plain-language modes. Mode hint text appears under the mode select.
14. Header **Grove / Dusk / Ink** switches the palette. The choice is stored in the browser (`lacerta-theme`) and sticks after reload. Grove is the default green.

**Replies** (above the job log) is the conversation view for Chat, Tutor, and Archive. Code / Research / Writing show a one-line finished status there, not a fake chat. While a Chat, Tutor, or Archive run is in flight, a step line (`Indexing sources`, `Retrieving`, `Generating reply`, `Grading`, or `Working`) sits above the panel and the assistant row grows from the poll buffer in closed chunks — unfinished `**` stays plain, and an unclosed `$` stays hidden until both dollars arrive. The buffer is not written to disk. Artifacts and Preview still open raw files. Formatting (newlines, bold, italic, code, `$…$` / `$$…$$`) is server HTML from `lacerta/gui/format_reply.py`; the page typesets math with vendored temml (`/vendor/`, no CDN). Themes only change CSS tokens; they do not change reply or activity behavior.

CLI gate names stay on the harness; the GUI uses human labels only. **v1 exit met**; **v2 exit met** (V2.1–V2.5). MCP/Remote still deferred.

## API

- `GET /api/surfaces` — surface defaults, allowlists, `code_scenarios`, `learn_scenarios`, `research_scenarios`, `writing_scenarios`
- `POST /api/run` — `{surface, goal, root?, light_research?, attachments?, course_id?, title?, scenario?, messages?}` → **202** `{run_id, status: running}`
- `GET /api/runs/{run_id}` — poll plan / results / artifacts / acceptance until finished|failed. Finished payloads include `reply` (plain text, not artifact JSON) and `reply_html`. While running, Chat / Tutor / Archive may include `partial_reply`, `partial_reply_html`, and `activity` (in-memory only).
- `GET /api/learn/turns?root=&course_id=&instance_id=&kind=tutor|archive` — last 20 disk turns as `{role, text, ts, text_html}`
- `GET /api/learn/course?root=&course_id=&instance_id=` — read-only syllabus nodes + corpus status/chunk_count
- `POST /api/learn/tutor/clear` — `{root?, course_id?, instance_id?}` wipe tutor digest + history index
- `POST /api/learn/archive/clear` — wipe archive digest + history index (not tutor)
- `POST /api/learn/mastery/check` — `{root?, course_id?, instance_id?, node_id}` load MC quiz (no correct answers)
- `POST /api/learn/mastery/grade` — `{…, answers:[{question_id, selected_index}]}` Python grade; pass increments mastery
- `POST /api/learn/practice/quiz` — load practice quiz (answers stripped)
- `POST /api/learn/practice/grade` — Python grade + attempt record (no mastery bump)
- `POST /api/learn/practice/flashcards` — generate deck JSON
- `POST /api/learn/practice/study_guide` — generate markdown study guide
- `GET /api/preview?path=&root=` — bounded text preview (max 64 KiB)
- `GET /api/history` — last N in-process runs
