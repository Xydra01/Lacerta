# Lacerta

Lacerta is a local-first AI agent framework: a stateful **manager** that plans, dispatches, and grades; ephemeral **workers** that execute one typed job with a tiny tool set or a Python recipe. Surfaces (chat, code, learn, research, writing) pick templates and allowlists.

## Blueprint

- [Architecture (Supervisor–Worker)](lacerta-supervisor-worker-viability.md)
- [Port kit (CodeWorker, IPC, harness)](lacerta-port-kit.md)
- [Surfaces & recipes](lacerta-surfaces-and-recipes.md)
- [Implementation phases](docs/phases/README.md)

## Setup

```bash
python -m venv .venv
# Windows Git Bash / WSL:
source .venv/Scripts/activate   # or: source .venv/bin/activate
pip install -e ".[dev]"
```

Copy [`.env.example`](.env.example) to `.env` when you need local overrides.

### Ollama model (`lacerta:latest`)

Requires a local [`qwen3.5:9b`](https://ollama.com) base, then:

```bash
ollama pull qwen3.5:9b   # if needed
ollama create lacerta -f Modelfile
```

That yields `lacerta:latest`, the default `OLLAMA_MODEL`.

## Verify (L0–L6)

```bash
pytest
python -m lacerta.harness.gate --help
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
