# Lacerta thin GUI

Local stdlib HTTP UI (`http.server`) that calls `run_manager` in-process. Not a second orchestrator.

## Run

```bash
python -m lacerta.gui
# optional:
python -m lacerta.gui --host 127.0.0.1 --port 8765
```

Open http://127.0.0.1:8765/

Stack choice: **stdlib only** (no Gradio/Streamlit/FastAPI) so runtime deps stay pydantic-only.

## Manual smoke

1. Start Ollama with `lacerta:latest` (needed for **code** / **chat**).
2. Launch GUI; leave surface on **Code**; goal: create `harness_smoke.py` that prints `HARNESS_OK`.
3. Confirm job log shows a spawn/finish and the file exists under the workspace root.
4. Switch to **Writing** or **Learn** (deterministic OK without Ollama for those recipes); confirm job log / artifact paths.
5. Confirm there is no free JobType picker — only surface tabs (wrong JobTypes cannot be launched from the UI).

## API

- `GET /api/surfaces` — surface defaults + allowlists
- `POST /api/run` — `{surface, goal, root?, light_research?}` → manager status / plan / results / artifacts
