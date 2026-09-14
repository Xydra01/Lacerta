#!/usr/bin/env bash
# Build Lacerta's macOS Ollama model (Qwen3.5 4B, 8k ctx) for M2 / 8GB class machines.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

if ! command -v ollama >/dev/null 2>&1; then
  echo "ollama not found. Install from https://ollama.com or: brew install --cask ollama" >&2
  exit 1
fi

# Ensure the daemon is reachable (Ollama.app or `ollama serve`).
if ! ollama list >/dev/null 2>&1; then
  echo "Ollama is installed but not responding. Open Ollama.app, then re-run." >&2
  exit 1
fi

BASE="${LACERTA_OLLAMA_BASE:-qwen3.5:4b}"
TAG="${OLLAMA_MODEL:-lacerta:latest}"
# Strip :tag for create name (ollama create lacerta -f … → lacerta:latest)
CREATE_NAME="${TAG%%:*}"
CREATE_NAME="${CREATE_NAME:-lacerta}"

echo "Pulling base model: ${BASE}"
ollama pull "${BASE}"

echo "Creating ${CREATE_NAME} from Modelfile (Apple Silicon / 8GB profile)"
ollama create "${CREATE_NAME}" -f "${REPO_ROOT}/Modelfile"

echo
echo "Done. Use:"
echo "  export OLLAMA_MODEL=${TAG}"
echo "  export OLLAMA_NUM_CTX=\${OLLAMA_NUM_CTX:-8192}"
echo "  python3 -m lacerta.gui"
echo
ollama list | head -20
