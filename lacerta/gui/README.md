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

1. Start Ollama with `lacerta:latest` (needed for **code** / **chat**).
2. Launch GUI; leave surface on **Code**; goal: create `harness_smoke.py` that prints `HARNESS_OK`.
3. Confirm job log shows a spawn/finish and the file exists under the workspace root.
4. Switch to **Research**; paste an absolute attachment path (e.g. `/Users/you/Documents/notes.md`), one per line; Run; confirm artifact paths appear.
5. Click an artifact → **Preview** shows size-capped UTF-8 text (or a clear error for binary / outside-root paths).
6. Confirm **Recent runs** lists the run; click it to restore goal / root / attachments (re-run still needs Run).
7. Switch to **Writing** or **Learn** (deterministic OK without Ollama for those recipes); Learn shows course id + attachments; Writing shows optional draft title.
8. While a run is in progress, a second Run should fail with HTTP **409** (generation lock).
9. Confirm there is no free JobType picker — only surface tabs.

## API

- `GET /api/surfaces` — surface defaults, allowlists, form hints (`show_attachments`, `show_course_id`, `show_title`)
- `POST /api/run` — `{surface, goal, root?, light_research?, attachments?, course_id?, title?}` → manager status / plan / results / artifacts (409 if busy)
- `GET /api/preview?path=&root=` — bounded text preview under workspace root (max 64 KiB)
- `GET /api/history` — last N in-process runs (newest first)
