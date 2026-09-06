# Lacerta

Lacerta is a local-first AI agent framework: a stateful **manager** that plans, dispatches, and grades; ephemeral **workers** that execute one typed job with a tiny tool set or a Python recipe. Surfaces (chat, code, learn, research, writing) pick templates and allowlists — they never fork the runtime.

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

## Verify (L0)

```bash
pytest
python -m lacerta.harness.gate --help
# optional:
./scripts/gate.sh --help
```
