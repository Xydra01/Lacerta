#!/usr/bin/env bash
# Build Lacerta's lite Ollama model (Qwen3.5 4B, 8k context).
# Linux, macOS, and Windows Git Bash. PowerShell: scripts/setup-lite.ps1
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

if ! command -v ollama >/dev/null 2>&1; then
  echo "ollama not found. Install from https://ollama.com and start the app, then re-run." >&2
  exit 1
fi

if ! ollama list >/dev/null 2>&1; then
  echo "Ollama is installed but not responding. Start Ollama, then re-run." >&2
  exit 1
fi

BASE="${LACERTA_OLLAMA_BASE:-qwen3.5:4b}"
# Full tag so this does not replace lacerta:latest (the 9B full profile).
TAG="${LACERTA_LITE_TAG:-lacerta:lite}"

echo "Pulling base model: ${BASE}"
ollama pull "${BASE}"

echo "Creating ${TAG} from Modelfile.lite (lite / 4B / 8k, all platforms)"
ollama create "${TAG}" -f "${REPO_ROOT}/Modelfile.lite"

echo
echo "Done. Point .env at the lite profile:"
echo "  cp .env.lite.example .env"
echo "  # OLLAMA_MODEL=${TAG}"
echo "  # LACERTA_PROFILE=lite"
echo "  python -m lacerta.gui"
echo
ollama list | head -20
