# Getting started

Lacerta runs on **Windows, Linux, and macOS**. Pick a model budget, not an operating-system branch.

| Profile | Copy | Model you build | When |
|---------|------|-----------------|------|
| **full** | `.env.example` | `lacerta:latest` from `qwen3.5:9b` (32k) | Hosts that can spare ~8GB+ for the model |
| **lite** | `.env.lite.example` | `lacerta:lite` from `qwen3.5:4b` (8k) | Windows, Linux, or macOS laptops, including 8GB machines |

`LACERTA_PROFILE=macos` is only an alias of **lite**. New setups on every OS use `lite`.

---

## 1. Install Python and Ollama

Python **3.11+** and [Ollama](https://ollama.com). Start the Ollama app (or `ollama serve`) before building a model.

- **Windows:** install Python from python.org (enable “Add python to PATH”) and the Ollama Windows app.
- **Linux:** your distro’s Python 3.11+ and the Ollama install script from ollama.com.
- **macOS:** Xcode Command Line Tools if `git` is missing (`xcode-select --install`). Homebrew is optional (`brew install python@3.12` and `brew install --cask ollama`). Details: [macos.md](macos.md).

## 2. Clone and install

```bash
git clone <this-repo> Lacerta
cd Lacerta
git checkout main
python -m venv .venv
```

Activate:

- Windows cmd: `.venv\Scripts\activate`
- Windows PowerShell: `.venv\Scripts\Activate.ps1`
- Linux / macOS: `source .venv/bin/activate`

```bash
pip install -e ".[dev]"
```

`[dev]` includes PDF/DOCX extract. The GUI does not need a browser framework.

## 3. Choose a profile and build the model

**Full**

```bash
cp .env.example .env          # Windows: copy .env.example .env
ollama pull qwen3.5:9b
ollama create lacerta -f Modelfile
```

**Lite** (does not replace `lacerta:latest`)

```bash
cp .env.lite.example .env     # Windows: copy .env.lite.example .env
```

Linux, macOS, or Git Bash:

```bash
./scripts/setup-lite.sh
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup-lite.ps1
```

Confirm `ollama list` shows `lacerta:lite` (lite) or `lacerta:latest` (full). `.env` is loaded automatically by the GUI and the harness.

## 4. Check the install

```bash
pytest tests/ -q
python -m lacerta.harness.gate --help
```

`scripts/gate.sh` is Bash. On Windows without Git Bash, call `python -m lacerta.harness.gate` with the same arguments.

## 5. GUI

```bash
python -m lacerta.gui
```

Open http://127.0.0.1:8765/

- **Replies** is where Chat, Tutor, and Archive answers appear (formatted, not raw JSON). While a run is going, a step line sits above the reply.
- **Draft title** only appears on Writing → Short draft.
- **Grove / Dusk / Ink** is a local theme. It is stored in the browser, not on the server.
- Artifacts and Preview still open files on disk.

First runs: Code → Quick file check (needs Ollama) or Habit tracker (deterministic, no model). Learn → Build syllabus, then Index sources, then Tutor or Archive. Workspace paths can be any folder you own (`C:\Users\you\lacerta-demo`, `/tmp/lacerta-demo`, and so on).

## 6. Day to day

Start Ollama, activate the venv, `python -m lacerta.gui`. Rebuild the lite model only if `Modelfile.lite` changed (`./scripts/setup-lite.sh` or the PowerShell script). Do not point a lite `.env` at the 9B Modelfile, and do not set `OLLAMA_NUM_CTX=32768` on an 8GB machine.

Deterministic recipes (syllabus, habit tracker, short writing) run without a loaded model. Chat, Tutor, Archive, and code file-check need the model named in `OLLAMA_MODEL`.
