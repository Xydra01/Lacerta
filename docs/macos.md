# Lacerta on macOS (Apple Silicon, 8GB)

**Branch profile:** `devMacOS`  
**Hardware target:** 2023 MacBook Air M2, 8GB unified memory  
**Model target:** Qwen3.5 **4B** via Ollama (`lacerta:latest`)

This profile keeps the same Supervisor–Worker contracts, flat tool JSON schema, and harness gates as mainline Lacerta. The changes are sizing and Mac ergonomics so the stack stays usable without swapping.

---

## Why 4B (not 9B)

| Setting | Mainline (larger hosts) | macOS 8GB profile |
|---------|-------------------------|-------------------|
| Base model | `qwen3.5:9b` (~6.6GB) | `qwen3.5:4b` (~3.4GB) |
| `num_ctx` | 32768 | **8192** |
| Tool output cap | 6000 | **4000** |
| Write char cap | 8000 | **6000** |

A 9B model plus a large KV cache will contend with macOS and Chrome on 8GB unified memory. Staying in the Qwen3.5 family preserves prompt/schema habits while fitting RAM. Structured output still goes through Ollama `format=` + the flat worker schema (see `lacerta/core/schema.py`).

**Optional (tighter RAM):** `qwen3.5:2b` — expect more JSON retries; not the default.  
**Optional (spare RAM / closed apps):** `qwen3.5:4b-mlx` — Apple MLX build; rebuild Modelfile `FROM` line if you try it.

---

## One-time setup

```bash
# 1. Python 3.11+ (Homebrew recommended)
brew install python@3.12
brew install --cask ollama   # or download from https://ollama.com

# 2. Clone / checkout this branch
git checkout devMacOS

# 3. Project env
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env

# 4. Model
./scripts/setup-macos.sh
# or manually:
#   ollama pull qwen3.5:4b
#   ollama create lacerta -f Modelfile
```

Confirm: `ollama list` shows `lacerta:latest` and `qwen3.5:4b`.

---

## Run

```bash
source .venv/bin/activate
pytest -q
python3 -m lacerta.gui          # http://127.0.0.1:8765/
./scripts/gate.sh smoke_write_file --runs 3   # needs Ollama + lacerta:latest
```

Deterministic surfaces (learn / writing / habit default) work without a hot model.

---

## Memory tips (M2 8GB)

1. Quit unused browsers / Electron apps before long code smokes.
2. Keep `OLLAMA_NUM_CTX=8192` unless you have headroom (`ollama ps` should stay GPU-resident).
3. Leave `LACERTA_LLM_DECOMPOSE=0` — templates are the default path.
4. Prefer `python3` / the venv interpreter; habit tests resolve via `sys.executable` on this branch.

---

## Syncing from `main`

When main moves, rebase or merge into `devMacOS`, then re-check:

- `Modelfile` still `FROM qwen3.5:4b` with `num_ctx 8192`
- `.env.example` Mac caps
- `docs/macos.md` still accurate

Do not silently reintroduce a 9B default on this branch.
