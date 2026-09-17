# macOS notes (8GB Apple Silicon)

The product is the same on Windows, Linux, and macOS. An 8GB Mac uses the **lite** profile — the same 4B / 8k budget as a small Windows or Linux machine. Do not set a separate macOS model.

Full install steps: [getting-started.md](getting-started.md).

| Setting | full | lite (use this on 8GB) |
|---------|------|------------------------|
| Base model | `qwen3.5:9b` | `qwen3.5:4b` |
| Ollama tag | `lacerta:latest` | `lacerta:lite` |
| `num_ctx` | 32768 | 8192 |
| Env file | `.env.example` | `.env.lite.example` |
| `LACERTA_PROFILE` | `full` | `lite` |

`LACERTA_PROFILE=macos` is accepted as an alias of `lite` so an older `.env` still applies the small budget. New Mac setups should say `lite`.

## Why 4B on 8GB

A 9B model plus a 32k KV cache contends with macOS and a browser on 8GB unified memory. Staying in the Qwen3.5 family keeps the same prompts and schemas.

Optional tighter RAM: `qwen3.5:2b` (more JSON retries). Optional spare RAM: `qwen3.5:4b-mlx` — change `FROM` in `Modelfile.lite` if you try it. Neither is the default.

## Memory tips

1. Quit unused browsers before long code runs.
2. Keep `OLLAMA_NUM_CTX=8192`.
3. Leave `LACERTA_LLM_DECOMPOSE=0`.
4. Use the venv interpreter (`python` or `python3`).
