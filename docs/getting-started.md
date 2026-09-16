# Getting started with Lacerta (macOS)

End-to-end setup for **Lacerta on a 2023 MacBook Air M2 (8GB)** using the `devMacOS` branch. Follow the sections in order the first time; later days you can jump to [Day-to-day use](#8-day-to-day-use).

**What you will have at the end**

- Python project installed in a virtualenv  
- Ollama running with a **~4B** local model tagged `lacerta:latest`  
- The thin local GUI at [http://127.0.0.1:8765/](http://127.0.0.1:8765/)  
- Verified harness gates (unit tests + optional model smoke)

Related: [macOS profile notes](macos.md) · [Architecture v1](architecture-v1.md) · [Architecture v2](architecture-v2.md) (v2 exit met) · [Phases](phases/README.md)

---

## 0. What Lacerta is (30 seconds)

Lacerta is a **local-first** agent app:

| Piece | Role |
|-------|------|
| **Manager** | Plans, dispatches, and grades jobs (templates by default) |
| **Workers** | Run one typed job with a small tool set or a Python recipe |
| **Surfaces** | Chat, Code, Learn, Research, Writing — tabs in the GUI |
| **Ollama** | Serves the local LLM used for Code / Chat (and optional LLM paths) |

Nothing is sent to a cloud LLM by default. Disk files (workspace root, syllabus JSON, drafts) are the source of truth.

---

## 1. Hardware & software you need

| Item | Requirement |
|------|-------------|
| Mac | Apple Silicon recommended; this guide targets **M2 / 8GB** |
| OS | macOS 13+ (Ventura or newer) |
| Disk | ~5–8 GB free (Python venv + `qwen3.5:4b` ≈ 3.4 GB) |
| Network | Needed once to clone the repo and pull the model |
| Accounts | GitHub access to this repo; no API keys required for local use |

**You will install**

1. **Xcode Command Line Tools** (git, clang)  
2. **Homebrew** (optional but recommended)  
3. **Python 3.11+**  
4. **Ollama**  
5. This **Lacerta** repo (`devMacOS` branch)

---

## 2. Install system tools

### 2.1 Command Line Tools

Open **Terminal** (Applications → Utilities → Terminal) and run:

```bash
xcode-select --install
```

Accept the dialog and wait until it finishes. Confirm:

```bash
git --version
```

### 2.2 Homebrew (recommended)

If you do not already have Homebrew:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Follow the on-screen steps (Apple Silicon often asks you to add Homebrew to your `PATH`). Then:

```bash
brew --version
```

### 2.3 Python 3.11+

```bash
brew install python@3.12
python3 --version   # should print 3.11 or newer
```

If `python3` is already ≥ 3.11 from another install, you can skip Homebrew Python.

### 2.4 Ollama

**Option A — Homebrew**

```bash
brew install --cask ollama
```

**Option B — Installer**

Download and install from [https://ollama.com](https://ollama.com).

Then **open Ollama** from Applications (menu-bar icon). Confirm the API is up:

```bash
ollama list
```

If that fails with a connection error, open the Ollama app and retry. Leave it running whenever you use Code or Chat.

---

## 3. Get the Lacerta code

```bash
# Pick a folder you like, e.g. ~/Developer
mkdir -p ~/Developer && cd ~/Developer

git clone https://github.com/Xydra01/Lacerta.git
cd Lacerta
git checkout devMacOS
```

If you already cloned the repo:

```bash
cd /path/to/Lacerta
git fetch origin
git checkout devMacOS
git pull origin devMacOS
```

You should see `Modelfile`, `scripts/setup-macos.sh`, and `docs/getting-started.md` in the tree.

---

## 4. Create the Python environment

Still inside the repo root:

```bash
python3 -m venv .venv
source .venv/bin/activate

# Confirm the venv is active (prompt usually shows (.venv))
which python3
python3 --version

pip install --upgrade pip
pip install -e ".[dev]"
```

Copy the Mac-tuned env file:

```bash
cp .env.example .env
```

Lacerta loads `.env` automatically when you start the GUI or the harness gate (values already in your shell win). You normally do **not** need to `export` each variable by hand.

**Important defaults in `.env` (M2 8GB)**

| Variable | Default | Why |
|----------|---------|-----|
| `OLLAMA_MODEL` | `lacerta:latest` | Custom tag built from the Modelfile |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Local Ollama API |
| `OLLAMA_NUM_CTX` | `8192` | Fits 8GB unified memory; do not set 32k on this machine |
| `OLLAMA_NUM_PREDICT` | `1024` | Caps long rambling generations |
| `LACERTA_LLM_DECOMPOSE` | `0` | Templates stay the default (more reliable on 4B) |
| `LACERTA_HABIT_MODE` | `deterministic` | Reliable habit gate without relying on the LLM |

---

## 5. Build the local model (`lacerta:latest`)

With Ollama open and your venv activated:

```bash
./scripts/setup-macos.sh
```

This will:

1. `ollama pull qwen3.5:4b` (~3.4 GB download the first time)  
2. `ollama create lacerta -f Modelfile` → tag **`lacerta:latest`** with 8k context and Lacerta’s system prompt  

Manual equivalent:

```bash
ollama pull qwen3.5:4b
ollama create lacerta -f Modelfile
ollama list
```

You should see both `qwen3.5:4b` and `lacerta:latest`.

**Quick model smoke (optional)**

```bash
ollama run lacerta:latest "Reply with exactly: ok"
```

Type `/bye` to exit the Ollama chat.

---

## 6. Verify the install

With `.venv` activated and Ollama running:

```bash
# Unit tests (no model required)
pytest -q

# Harness help
./scripts/gate.sh --help
```

**Deterministic gates** (safe without stressing the LLM):

```bash
./scripts/gate.sh learn_syllabus_files --runs 1
./scripts/gate.sh writing_short --runs 1
./scripts/gate.sh research_local --runs 1
export LACERTA_HABIT_MODE=deterministic
./scripts/gate.sh habit_tracker --runs 1
```

**LLM code smoke** (needs `lacerta:latest`; quit heavy browser tabs first on 8GB):

```bash
./scripts/gate.sh smoke_write_file --runs 3
```

Expect 3/3 pass. If it fails, see [Troubleshooting](#10-troubleshooting).

---

## 7. Start the app (GUI)

```bash
source .venv/bin/activate   # if not already
python3 -m lacerta.gui
```

You should see:

```text
Lacerta GUI at http://127.0.0.1:8765/  (Ctrl+C to stop)
```

Open **http://127.0.0.1:8765/** in Safari or Chrome.

### First runs in the UI

1. **Code (needs Ollama for Quick file check)**  
   - Leave the **Code** tab selected.  
   - **Run check:** Quick file check (default) or Habit tracker (scaffold + tests).  
   - Workspace root: leave the default, or set a folder you own (e.g. `/tmp/lacerta-demo`).  
   - Goal example (quick check):  
     `Create harness_smoke.py that prints HARNESS_OK`  
   - Click **Run**. Watch the job log for plan steps and **Acceptance** pass/fail; confirm files under the workspace root.  
   - Habit tracker check can run without Ollama when `LACERTA_HABIT_MODE=deterministic` (default).

2. **Writing / Learn (no hot model required for default recipes)**  
   - Writing: **Writing mode** = Short draft | From sources; optional draft title; From sources needs attachment paths.  
   - Learn: **Learn mode** = Build syllabus | Tutor | Assessment | Index sources; course id + attachments for syllabus/index.  
   - After syllabus, **Refresh course** shows node list and `corpus: pending`. After **Index sources**, status becomes `complete` with chunk count (keyword index on Mac; no embedding downloads).  
   - STEM sources: Index emits `[table]` / `[math]` / `[figure]` text surrogates for retrieve. **Re-run Index sources** after upgrading so older corpora pick this up. Bitmap-only scanned pages get a figure placeholder unless a local describe path is enabled later.  
   - Check **Artifacts** for paths on disk; click a path to **Preview** (text, size-capped).

3. **Chat**  
   - Needs Ollama + `lacerta:latest`. Ask a short question; confirm a reply in the log and **Chat session** transcript.  
   - Ask a follow-up without clearing — prior turns are sent with the next Run. **Clear chat** resets the transcript.  
   - Optional **Light research before answer** still works with multi-turn.

4. **Research**  
   - **Research mode** = Offline sources (default) or Light web (deferred).  
   - Offline: paste absolute attachment paths (one per line); empty list is rejected in the GUI.  
   - Supported attachment types: `.md` / `.txt` / `.pdf` / `.docx` / `.html` / `.csv` (PDF/DOCX need `pip install -e ".[dev]"` or `.[extract]`). Legacy `.doc` is rejected — save as `.docx`.  
   - More than 3 files or >80KB total → keyword corpus under `tasks/.../research/corpus/` then top-k retrieve (not full concat).  
   - After Run, confirm `report.md` in artifacts and preview.

There is **no free “job type” picker** — only surface tabs. That is intentional (surfaces choose templates and allowlists).

Optional host/port:

```bash
python3 -m lacerta.gui --host 127.0.0.1 --port 8765
```

Stop the server with `Ctrl+C` in Terminal.

---

## 8. Day-to-day use

Each session:

```bash
cd ~/Developer/Lacerta          # your clone path
source .venv/bin/activate
# Ensure Ollama.app is running (menu bar)
python3 -m lacerta.gui
```

Update this Mac branch later:

```bash
git pull origin devMacOS
pip install -e ".[dev]"         # if dependencies changed (includes PDF/DOCX extract libs)
# Only if Modelfile changed:
./scripts/setup-macos.sh
```

When `main` moves and you ask an agent to sync Mac changes, re-check that `Modelfile` still uses `qwen3.5:4b` and `num_ctx 8192` before rebuilding.

---

## 9. Surfaces cheat sheet

| Surface | Needs Ollama? | Good first goal |
|---------|---------------|-----------------|
| **Code** | Quick file check: yes; Habit tracker: no (deterministic) | **Run check** scenarios + acceptance in job log |
| **Chat** | Yes | Multi-turn session + optional light research; Clear chat |
| **Learn** | No (deterministic default) | Build syllabus / Tutor / Assessment / Index sources; course view + corpus status |
| **Writing** | No (deterministic default) | Short draft or From sources; `#` title; `advance_when=single_draft` enforced in Python |
| **Research** | No for offline recipe | Offline sources (attachments); bulk → keyword corpus; Light web deferred |

### v1 regression matrix

```bash
python -m pytest tests/ -q
LACERTA_HABIT_MODE=deterministic ./scripts/gate.sh habit_tracker --runs 1
./scripts/gate.sh writing_short --runs 1
./scripts/gate.sh writing_from_sources --runs 1
./scripts/gate.sh research_local --runs 1
./scripts/gate.sh research_corpus_bulk --runs 1
./scripts/gate.sh learn_syllabus_files --runs 1
./scripts/gate.sh learn_corpus_retrieve --runs 1
./scripts/gate.sh learn_corpus_structured --runs 1
./scripts/gate.sh learn_quiz_roundtrip --runs 1
./scripts/gate.sh learn_tutor_grounded --runs 1
./scripts/gate.sh learn_archive_chat --runs 1
# when Ollama is up:
./scripts/gate.sh smoke_write_file --runs 1
```

CLI equivalents use `./scripts/gate.sh <scenario>` — scenarios: `smoke_write_file`, `learn_syllabus_files`, `learn_corpus_retrieve`, `learn_corpus_structured`, `learn_quiz_roundtrip`, `learn_tutor_grounded`, `learn_archive_chat`, `habit_tracker`, `research_local`, `research_corpus_bulk`, `writing_short`, `writing_from_sources`.

---

## 10. Troubleshooting

| Symptom | What to try |
|---------|-------------|
| `ollama list` fails | Open **Ollama.app**; wait a few seconds; retry |
| `ollama create` / pull is slow | Normal on first download (~3.4 GB); keep Wi‑Fi awake |
| GUI opens but Code hangs / Mac fans spin | Quit Chrome/Electron apps; confirm `OLLAMA_NUM_CTX=8192` in `.env`; run `ollama ps` — model should stay GPU-resident |
| `.env` seems ignored | Start via `python3 -m lacerta.gui` or `./scripts/gate.sh` from the repo (they auto-load `.env`). Shell `export`s still win over the file |
| `Unknown model` / wrong answers | `ollama list` must show `lacerta:latest`; rebuild with `./scripts/setup-macos.sh` |
| `python: command not found` | Use `python3` and the venv (`source .venv/bin/activate`) |
| `pytest` not found | Activate venv and `pip install -e ".[dev]"` |
| Gate smoke fails JSON / tools | Keep temperature low (Modelfile default); ensure you are on `devMacOS` (tolerant JSON parsing); retry once — 4B models can flake; 2/3 then 3/3 on retry is a RAM/context issue more often than code |
| Port 8765 in use | `python3 -m lacerta.gui --port 8766` |
| Permission errors writing files | Point **Workspace root** at a directory you own |

**Memory rule of thumb (8GB):** model weights (~3.4 GB) + 8k KV cache + macOS should leave a little headroom. A 9B model or 32k context on this machine is not supported on this branch.

---

## 11. Optional: MLX base model

If you close other apps and want Apple’s MLX build:

1. `ollama pull qwen3.5:4b-mlx` (if available in your Ollama version)  
2. Edit `Modelfile` `FROM` line to that tag  
3. Re-run `./scripts/setup-macos.sh`  

Default remains **`qwen3.5:4b`** for the widest compatibility and headroom.

---

## 12. What not to do on this Mac profile

- Do not switch the Modelfile back to `qwen3.5:9b` or `num_ctx 32768` on 8GB.  
- Do not enable `LACERTA_LLM_DECOMPOSE=1` until smoke gates are solid.  
- Do not start MCP / Remote phases (L9–L12) before v1 GUI depth is done.  
- Do not treat the GUI as a second orchestrator — it only calls the same manager.

---

## Checklist (first-time success)

- [ ] Xcode CLT / git works  
- [ ] Python ≥ 3.11 (`python3 --version`)  
- [ ] Ollama.app running (`ollama list`)  
- [ ] `devMacOS` checked out  
- [ ] `.venv` activated and `pip install -e ".[dev]"` done  
- [ ] `.env` copied from `.env.example`  
- [ ] `./scripts/setup-macos.sh` created `lacerta:latest`  
- [ ] `pytest -q` green  
- [ ] `python3 -m lacerta.gui` → browser at http://127.0.0.1:8765/  
- [ ] One Code run created a file on disk  

You are set up. For profile rationale and syncing from `main`, see [macos.md](macos.md).
