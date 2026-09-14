"""Load a simple KEY=VALUE .env file into os.environ (stdlib only).

Existing environment variables are not overwritten unless override=True.
"""

from __future__ import annotations

import os
from pathlib import Path


def _parse_line(line: str) -> tuple[str, str] | None:
    raw = line.strip()
    if not raw or raw.startswith("#"):
        return None
    if raw.startswith("export "):
        raw = raw[len("export ") :].strip()
    if "=" not in raw:
        return None
    key, _, value = raw.partition("=")
    key = key.strip()
    if not key:
        return None
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1]
    return key, value


def find_dotenv(start: Path | None = None) -> Path | None:
    """Walk up from start (or cwd) looking for .env; also try repo root next to package."""
    here = (start or Path.cwd()).resolve()
    for directory in [here, *here.parents]:
        candidate = directory / ".env"
        if candidate.is_file():
            return candidate
        # Stop at filesystem root
        if directory.parent == directory:
            break
    # lacerta/core/envload.py → parents[2] is repo root when installed editable
    repo_env = Path(__file__).resolve().parents[2] / ".env"
    if repo_env.is_file():
        return repo_env
    return None


def load_dotenv(path: Path | str | None = None, *, override: bool = False) -> Path | None:
    """Load .env into os.environ. Returns the path loaded, or None if nothing found."""
    env_path = Path(path).resolve() if path else find_dotenv()
    if env_path is None or not env_path.is_file():
        return None
    try:
        text = env_path.read_text(encoding="utf-8")
    except OSError:
        return None
    for line in text.splitlines():
        parsed = _parse_line(line)
        if parsed is None:
            continue
        key, value = parsed
        if override or key not in os.environ:
            os.environ[key] = value
    return env_path
