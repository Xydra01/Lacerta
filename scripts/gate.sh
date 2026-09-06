#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export LACERTA_DATA_ROOT="${LACERTA_DATA_ROOT:-$REPO_ROOT}"
exec python -m lacerta.harness.gate "$@"
