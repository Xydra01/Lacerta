#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export LACERTA_DATA_ROOT="${LACERTA_DATA_ROOT:-$REPO_ROOT}"
# Prefer python3 on macOS when `python` is absent.
if command -v python >/dev/null 2>&1; then
  PY=python
elif command -v python3 >/dev/null 2>&1; then
  PY=python3
else
  echo "python/python3 not found" >&2
  exit 1
fi
exec "$PY" -m lacerta.harness.gate "$@"
