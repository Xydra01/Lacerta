# Lacerta

Lacerta is a local-first AI agent framework: a stateful **manager** that plans, dispatches, and grades; ephemeral **workers** that execute one typed job with a tiny tool set or a Python recipe. Surfaces (chat, code, learn, research, writing) pick templates and allowlists.

**Version:** **v0 complete** (L0–L8). **v1 in progress** — deepen the GUI and surface capabilities. MCP/Remote (former L9–L12) are **deferred** until after v1.

**This branch (`devMacOS`):** Apple Silicon profile for a **2023 MacBook Air M2 / 8GB** — Ollama base **`qwen3.5:4b`**, 8k context, Mac setup docs. See [docs/macos.md](docs/macos.md).

## Docs

- [macOS / M2 8GB profile](docs/macos.md) — **start here on this branch**
- [Architecture v1](docs/architecture-v1.md) — active product architecture
- [Architecture (Supervisor–Worker blueprint)](lacerta-supervisor-worker-viability.md)
- [Port kit (CodeWorker, IPC, harness)](lacerta-port-kit.md)
- [Surfaces & recipes](lacerta-surfaces-and-recipes.md)
- [Implementation phases](docs/phases/README.md)

## Setup (macOS)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
./scripts/setup-macos.sh   # pulls qwen3.5:4b and builds lacerta:latest
```

Requires [Ollama](https://ollama.com) (App or `brew install --cask ollama`). That yields `lacerta:latest` from `qwen3.5:4b` with an 8k context Modelfile suited to 8GB unified memory.

### Larger hosts (not this branch’s default)

Mainline historically used `qwen3.5:9b` + 32k context. Do **not** use that Modelfile on 8GB Macs.

## Verify (v0 bar — keep green)

```bash
pytest
./scripts/gate.sh --help
# Thin GUI (same manager; stdlib HTTP):
python3 -m lacerta.gui
# Code smoke (needs Ollama):
export OLLAMA_MODEL=lacerta:latest
./scripts/gate.sh smoke_write_file --runs 3
# Learn syllabus (deterministic by default):
./scripts/gate.sh learn_syllabus_files --runs 1
# Habit tracker code-reliability bar (deterministic default):
export LACERTA_HABIT_MODE=deterministic
./scripts/gate.sh habit_tracker --runs 3
# Offline research:
./scripts/gate.sh research_local --runs 1
# Short writing draft (deterministic by default):
./scripts/gate.sh writing_short --runs 1
```

Templates remain the default path. Optional LLM manager decompose is off unless
`LACERTA_LLM_DECOMPOSE=1` (keep narrow for local models; see `.env.example`).

## What’s next (v1)

See [docs/architecture-v1.md](docs/architecture-v1.md) and phases **V1.1–V1.5**: GUI attachments / deliverables / history, code habit in UI, learn tutor & assessment, research/writing depth, multi-turn chat — then declare v1 exit. **Do not start L9–L12 until V1.5.**

On `devMacOS`, when syncing from `main`, re-validate the Mac memory/model profile before merging feature work.
