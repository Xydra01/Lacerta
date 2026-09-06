"""Filesystem tools for CodeWorker."""

from __future__ import annotations

import ast
import fnmatch
import os
import re
from contextvars import ContextVar
from pathlib import Path
from typing import Any

_PROJECT_ROOT: ContextVar[Path | None] = ContextVar("lacerta_project_root", default=None)

_SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "node_modules",
        ".eggs",
        "dist",
        "build",
        ".tox",
    }
)


def set_project_root(root: Path | str | None) -> None:
    if root is None:
        _PROJECT_ROOT.set(None)
        return
    _PROJECT_ROOT.set(Path(root).resolve())


def get_project_root() -> Path | None:
    return _PROJECT_ROOT.get()


def _max_write_chars() -> int:
    raw = os.getenv("LACERTA_MAX_WRITE_CHARS", "8000").strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 8000


def _require_project_root() -> Path | str:
    root = get_project_root()
    if not root:
        return "❌ OS BLOCK: No project root."
    return root


def resolve_under_root(path: str, *, for_write: bool = False) -> Path:
    """Resolve path under project root. Caller must still validate containment."""
    del for_write  # reserved for future read-vs-write policy
    root = get_project_root()
    if root is None:
        raise RuntimeError("No project root")
    raw = (path or "").strip().replace("\\", "/")
    if raw.startswith("/"):
        raw = raw.lstrip("/")
    return (root / raw).resolve()


def write_file(path: str, content: str) -> str:
    block = _require_project_root()
    if isinstance(block, str):
        return block
    text = str(content)
    max_chars = _max_write_chars()
    if len(text) > max_chars:
        return f"❌ OS BLOCK: content {len(text)} chars (max {max_chars})."
    try:
        target = resolve_under_root(path, for_write=True)
    except RuntimeError:
        return "❌ OS BLOCK: No project root."
    root = block.resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return f"❌ Cannot write outside project ({root})."
    target.parent.mkdir(parents=True, exist_ok=True)
    if not text.endswith("\n") and target.suffix == ".py":
        text = text + "\n"
    target.write_text(text, encoding="utf-8")
    if target.suffix == ".py":
        try:
            ast.parse(text)
        except SyntaxError as e:
            return (
                f"✅ Wrote {path}, syntax error: {e.msg} (line {e.lineno}). "
                "Fix with search_replace."
            )
    return f"✅ Successfully wrote {path}."


def search_replace(path: str, old_string: str, new_string: str) -> str:
    block = _require_project_root()
    if isinstance(block, str):
        return block
    try:
        target = resolve_under_root(path, for_write=True)
    except RuntimeError:
        return "❌ OS BLOCK: No project root."
    root = block.resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return f"❌ Cannot write outside project ({root})."
    if not target.is_file():
        return f"❌ File not found: {path}"
    text = target.read_text(encoding="utf-8", errors="replace")
    count = text.count(old_string)
    if count == 0:
        return f"❌ search_replace: old_string not found in {path}."
    if count > 1:
        return (
            f"❌ search_replace: old_string matched {count} times in {path}; "
            "require exactly one match."
        )
    target.write_text(text.replace(old_string, new_string, 1), encoding="utf-8")
    return f"✅ search_replace applied to {path}."


def read_file(path: str, start_line: int = 1, end_line: int = 0) -> str:
    block = _require_project_root()
    if isinstance(block, str):
        return block
    try:
        target = resolve_under_root(path)
    except RuntimeError:
        return "❌ OS BLOCK: No project root."
    root = block.resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return f"❌ Cannot read outside project ({root})."
    if not target.is_file():
        return f"❌ File not found: {path}"
    lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines:
        return f"[empty file] {path}"
    start = max(1, int(start_line or 1))
    if end_line and int(end_line) > 0:
        end = int(end_line)
    else:
        end = start + 199
    end = min(len(lines), end)
    if start > len(lines):
        return f"❌ start_line {start} past end of file ({len(lines)} lines)."
    numbered = [f"{i}|{lines[i - 1]}" for i in range(start, end + 1)]
    return "\n".join(numbered)


def list_dir(path: str = ".") -> str:
    block = _require_project_root()
    if isinstance(block, str):
        return block
    try:
        target = resolve_under_root(path or ".")
    except RuntimeError:
        return "❌ OS BLOCK: No project root."
    root = block.resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return f"❌ Cannot list outside project ({root})."
    if not target.exists():
        return f"❌ Path not found: {path}"
    if not target.is_dir():
        return f"❌ Not a directory: {path}"
    entries: list[str] = []
    for child in sorted(target.iterdir(), key=lambda p: p.name.lower()):
        if child.name in _SKIP_DIR_NAMES:
            continue
        rel = child.relative_to(root).as_posix()
        suffix = "/" if child.is_dir() else ""
        entries.append(f"{rel}{suffix}")
    if not entries:
        return f"[empty dir] {path}"
    return "\n".join(entries)


def _should_skip_dir(name: str) -> bool:
    return name in _SKIP_DIR_NAMES


def grep(pattern: str, path: str = ".", max_matches: int = 50) -> str:
    block = _require_project_root()
    if isinstance(block, str):
        return block
    try:
        target = resolve_under_root(path or ".")
    except RuntimeError:
        return "❌ OS BLOCK: No project root."
    root = block.resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return f"❌ Cannot grep outside project ({root})."
    try:
        regex = re.compile(pattern)
    except re.error as e:
        return f"❌ Invalid regex: {e}"
    cap = max(1, int(max_matches or 50))
    matches: list[str] = []

    def scan_file(fp: Path) -> None:
        nonlocal matches
        if len(matches) >= cap:
            return
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return
        rel = fp.relative_to(root).as_posix()
        for i, line in enumerate(text.splitlines(), start=1):
            if regex.search(line):
                matches.append(f"{rel}:{i}: {line.strip()[:200]}")
                if len(matches) >= cap:
                    return

    if target.is_file():
        scan_file(target)
    elif target.is_dir():
        for dirpath, dirnames, filenames in os.walk(target):
            dirnames[:] = [d for d in dirnames if not _should_skip_dir(d)]
            for name in filenames:
                scan_file(Path(dirpath) / name)
                if len(matches) >= cap:
                    break
            if len(matches) >= cap:
                break
    else:
        return f"❌ Path not found: {path}"

    body = "\n".join(matches)
    header = f"[OK] {len(matches)} match(es) for {pattern!r}"
    return f"{header}\n{body}" if body else header


def find_files(pattern: str = "*", path: str = ".", max_results: int = 100) -> str:
    block = _require_project_root()
    if isinstance(block, str):
        return block
    try:
        target = resolve_under_root(path or ".")
    except RuntimeError:
        return "❌ OS BLOCK: No project root."
    root = block.resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return f"❌ Cannot find outside project ({root})."
    if not target.exists():
        return f"❌ Path not found: {path}"
    cap = max(1, int(max_results or 100))
    found: list[str] = []
    if target.is_file():
        rel = target.relative_to(root).as_posix()
        if fnmatch.fnmatch(target.name, pattern) or fnmatch.fnmatch(rel, pattern):
            found.append(rel)
    else:
        for dirpath, dirnames, filenames in os.walk(target):
            dirnames[:] = [d for d in dirnames if not _should_skip_dir(d)]
            for name in filenames:
                fp = Path(dirpath) / name
                rel = fp.relative_to(root).as_posix()
                if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(rel, pattern):
                    found.append(rel)
                    if len(found) >= cap:
                        break
            if len(found) >= cap:
                break
    if not found:
        return f"[OK] 0 file(s) for {pattern!r}"
    return f"[OK] {len(found)} file(s) for {pattern!r}\n" + "\n".join(found)


def run_command(command: str) -> str:
    """Allowlisted shell: pytest / python -m pytest only, cwd=project root."""
    import shlex
    import subprocess

    block = _require_project_root()
    if isinstance(block, str):
        return block
    root = block.resolve()
    raw = (command or "").strip()
    if not raw:
        return "❌ OS BLOCK: empty command"
    try:
        parts = shlex.split(raw, posix=os.name != "nt")
    except ValueError as e:
        return f"❌ OS BLOCK: cannot parse command: {e}"
    if not parts:
        return "❌ OS BLOCK: empty command"

    allowed_prefixes = (
        ["pytest"],
        ["python", "-m", "pytest"],
        ["python3", "-m", "pytest"],
        ["py", "-m", "pytest"],
    )
    ok = False
    for prefix in allowed_prefixes:
        if parts[: len(prefix)] == prefix:
            ok = True
            break
    if not ok:
        return (
            "❌ OS BLOCK: command not allowlisted. "
            "Allowed: pytest / python -m pytest …"
        )
    try:
        proc = subprocess.run(
            parts,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return "❌ OS BLOCK: command timed out"
    except OSError as e:
        return f"❌ OS BLOCK: failed to run: {e}"
    out = (proc.stdout or "") + (proc.stderr or "")
    out = out[-4000:]
    status = "OK" if proc.returncode == 0 else "FAIL"
    return f"[{status}] exit={proc.returncode}\n{out}"


CODE_TOOL_REGISTRY: dict[str, dict[str, Any]] = {
    "read_file": {
        "func": read_file,
        "description": "Read a file slice with numbered lines.",
    },
    "write_file": {
        "func": write_file,
        "description": "Write a file under project root.",
    },
    "search_replace": {
        "func": search_replace,
        "description": "Replace exactly one occurrence in a file.",
    },
    "list_dir": {
        "func": list_dir,
        "description": "List directory entries under project root.",
    },
    "grep": {
        "func": grep,
        "description": "Search file contents; path:line: content output.",
    },
    "find_files": {
        "func": find_files,
        "description": "Find files by glob pattern under project root.",
    },
    "run_command": {
        "func": run_command,
        "description": "Allowlisted shell (stub in L1).",
    },
}


def get_active_tools(job_tools: list[str] | None = None) -> frozenset[str]:
    base = frozenset(CODE_TOOL_REGISTRY)
    if job_tools:
        return frozenset(t for t in job_tools if t in base)
    return base
