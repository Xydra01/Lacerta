# Lacerta

Lacerta is a local-first AI agent framework: a stateful **manager** that plans, dispatches, and grades; ephemeral **workers** that execute one typed job with a tiny tool set or a Python recipe. Surfaces (chat, code, learn, research, writing) pick templates and allowlists. The same code runs on **Windows, Linux, and macOS**.

**Version:** **v0 complete** (L0–L8). **v1 exit met**. **v2 exit met**. **v3 exit met** (replies, activity, themes). MCP/Remote (L9–L12) remain **deferred**.

## Profiles

| Profile | Who | Model | Context |
|---------|-----|--------|---------|
| **full** (default) | Machines that can hold a 9B model | `qwen3.5:9b` → `lacerta:latest` | 32768 |
| **lite** | Windows, Linux, or macOS with less RAM (including an 8GB laptop) | `qwen3.5:4b` → `lacerta:lite` | 8192 |

Lite is not a macOS-only switch. Set `LACERTA_PROFILE=lite`. An older `LACERTA_PROFILE=macos` value is accepted as an alias so an existing Mac `.env` still uses the small budget.

## Start here

**[Getting started](docs/getting-started.md)** — Windows, Linux, and macOS install, full vs lite, GUI, first runs.

## Docs

- [Getting started](docs/getting-started.md)
- [macOS hardware notes](docs/macos.md) — 8GB Apple Silicon uses the **lite** profile
- [Architecture v1](docs/architecture-v1.md) · [v2](docs/architecture-v2.md) · [v3](docs/architecture-v3.md)
- [Phases](docs/phases/README.md)
- [GUI](lacerta/gui/README.md)

## Quick setup

Install [Ollama](https://ollama.com) and Python 3.11+, then:

```bash
python -m venv .venv
```

- **Windows (cmd):** `.venv\Scripts\activate`
- **Windows (PowerShell):** `.venv\Scripts\Activate.ps1`
- **Linux / macOS:** `source .venv/bin/activate`

```bash
pip install -e ".[dev]"
```

**Full profile**

```bash
# Windows: copy .env.example .env
cp .env.example .env
ollama pull qwen3.5:9b
ollama create lacerta -f Modelfile
python -m lacerta.gui
```

**Lite profile** (4B, 8k — Windows, Linux, or macOS)

```bash
# Windows: copy .env.lite.example .env
cp .env.lite.example .env
# Linux / macOS / Git Bash:
./scripts/setup-lite.sh
# Windows PowerShell:
# powershell -ExecutionPolicy Bypass -File scripts/setup-lite.ps1
python -m lacerta.gui
```

Open http://127.0.0.1:8765/

## Verify

```bash
pytest tests/ -q
```

Harness gates (Git Bash or Linux/macOS). On Windows without Bash, the same entry point is `python -m lacerta.harness.gate`.

```bash
./scripts/gate.sh habit_tracker --runs 1
./scripts/gate.sh writing_short --runs 1
./scripts/gate.sh learn_syllabus_files --runs 1
```
