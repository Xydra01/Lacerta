# Lacerta

Lacerta is a local-first AI agent framework: a stateful **manager** that plans, dispatches, and grades; ephemeral **workers** that execute one typed job with a tiny tool set or a Python recipe. Surfaces (chat, code, learn, research, writing) pick templates and allowlists.

**Version:** **v0 complete** (L0–L8). **v1 in progress** — deepen the GUI and surface capabilities. MCP/Remote (former L9–L12) are **deferred** until after v1.

**This branch (`devMacOS`):** Apple Silicon profile for a **2023 MacBook Air M2 / 8GB** — Ollama base **`qwen3.5:4b`**, 8k context.

## Start here

**[Getting started (full Mac setup)](docs/getting-started.md)** — install tools, clone, model, GUI, first runs, troubleshooting.

## Docs

- [Getting started](docs/getting-started.md) — **full start-to-finish setup**
- [macOS / M2 8GB profile](docs/macos.md) — memory/model rationale
- [Architecture v1](docs/architecture-v1.md) — active product architecture
- [Architecture (Supervisor–Worker blueprint)](lacerta-supervisor-worker-viability.md)
- [Port kit (CodeWorker, IPC, harness)](lacerta-port-kit.md)
- [Surfaces & recipes](lacerta-surfaces-and-recipes.md)
- [Implementation phases](docs/phases/README.md)

## Quick setup (macOS)

```bash
git checkout devMacOS
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
./scripts/setup-macos.sh   # pulls qwen3.5:4b and builds lacerta:latest
python3 -m lacerta.gui     # http://127.0.0.1:8765/
```

Requires [Ollama](https://ollama.com) (App or `brew install --cask ollama`). Details, gates, and troubleshooting: [docs/getting-started.md](docs/getting-started.md).

### Larger hosts (not this branch’s default)

Mainline historically used `qwen3.5:9b` + 32k context. Do **not** use that Modelfile on 8GB Macs.

## Verify (v0 bar — keep green)

```bash
pytest
./scripts/gate.sh --help
python3 -m lacerta.gui
# Code smoke (needs Ollama):
./scripts/gate.sh smoke_write_file --runs 3
# Deterministic surfaces:
./scripts/gate.sh learn_syllabus_files --runs 1
./scripts/gate.sh habit_tracker --runs 3
./scripts/gate.sh research_local --runs 1
./scripts/gate.sh writing_short --runs 1
```

Templates remain the default path. Optional LLM manager decompose is off unless
`LACERTA_LLM_DECOMPOSE=1` (keep narrow for local models; see `.env.example`).

## What’s next (v1)

See [docs/architecture-v1.md](docs/architecture-v1.md) and phases **V1.1–V1.5**. **Do not start L9–L12 until V1.5.**

On `devMacOS`, when syncing from `main`, re-validate the Mac memory/model profile before merging feature work.
