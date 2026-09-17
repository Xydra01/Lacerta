#!/usr/bin/env bash
# macOS convenience wrapper. The low-RAM model is the cross-platform lite profile,
# not a separate macOS-only tag. Prefer scripts/setup-lite.sh and LACERTA_PROFILE=lite.
set -euo pipefail
echo "macOS uses the same lite model as Windows and Linux (LACERTA_PROFILE=lite)."
exec "$(cd "$(dirname "$0")" && pwd)/setup-lite.sh" "$@"
