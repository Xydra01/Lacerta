"""Thin local GUI HTTP server (stdlib only)."""

from __future__ import annotations

import json
import mimetypes
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from lacerta.core.gen_lock import GenerationBusy, acquire_generation, release_generation
from lacerta.core.manager import run_manager
from lacerta.core.ollama_client import OllamaClient
from lacerta.gui.surfaces import build_run_inputs, default_root, list_surfaces

STATIC_DIR = Path(__file__).resolve().parent / "static"

PREVIEW_MAX_BYTES = 64 * 1024
HISTORY_MAX = 20

# In-process recent runs (newest appended; exposed newest-first).
_run_history: deque[dict[str, Any]] = deque(maxlen=HISTORY_MAX)


def clear_run_history() -> None:
    """Test helper: reset in-process history."""
    _run_history.clear()


def get_run_history() -> list[dict[str, Any]]:
    """Newest-first snapshot of recent runs."""
    return list(reversed(_run_history))


def _json_response(handler: BaseHTTPRequestHandler, code: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _read_json(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length") or 0)
    raw = handler.rfile.read(length) if length else b"{}"
    try:
        data = json.loads(raw.decode("utf-8") or "{}")
    except json.JSONDecodeError as e:
        raise ValueError(f"invalid JSON: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("JSON body must be an object")
    return data


def _normalize_attachments(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        parts = [p.strip() for p in raw.replace("\r\n", "\n").split("\n")]
        return [p for p in parts if p]
    if isinstance(raw, list):
        out: list[str] = []
        for item in raw:
            s = str(item).strip()
            if s:
                out.append(s)
        return out
    raise ValueError("attachments must be a list of paths or newline-separated text")


def preview_file(*, path: str, root: str, max_bytes: int = PREVIEW_MAX_BYTES) -> dict[str, Any]:
    """Read a text file under root, size-capped. Raises ValueError on bad input."""
    if not path or not str(path).strip():
        raise ValueError("path is required")
    root_raw = (root or "").strip() or default_root()
    root_resolved = Path(root_raw).expanduser().resolve()
    if not root_resolved.is_dir():
        raise ValueError(f"root is not a directory: {root_resolved}")

    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = root_resolved / candidate
    try:
        resolved = candidate.resolve()
    except OSError as e:
        raise ValueError(f"cannot resolve path: {e}") from e

    try:
        resolved.relative_to(root_resolved)
    except ValueError as e:
        raise ValueError("path must be under workspace root") from e

    if not resolved.is_file():
        raise ValueError("path is not a file")

    size = resolved.stat().st_size
    to_read = min(size, max_bytes)
    raw = resolved.read_bytes()[:to_read]
    if b"\x00" in raw:
        raise ValueError("binary files are not previewable (text only)")
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ValueError("file is not valid UTF-8 text") from e

    return {
        "path": str(resolved),
        "root": str(root_resolved),
        "bytes_read": len(raw),
        "truncated": size > max_bytes,
        "content": content,
    }


def _record_history(entry: dict[str, Any]) -> None:
    _run_history.append(entry)


class LacertaHandler(BaseHTTPRequestHandler):
    server_version = "LacertaGUI/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        # Quiet default console spam; still show errors via print in handlers.
        return

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path == "/api/surfaces":
            _json_response(
                self,
                200,
                {"surfaces": list_surfaces(), "default_root": default_root()},
            )
            return
        if path == "/api/history":
            _json_response(self, 200, {"runs": get_run_history()})
            return
        if path == "/api/preview":
            file_path = (qs.get("path") or [""])[0]
            root = (qs.get("root") or [default_root()])[0]
            try:
                payload = preview_file(path=file_path, root=root)
            except ValueError as e:
                _json_response(self, 400, {"error": str(e)})
                return
            except OSError as e:
                _json_response(self, 400, {"error": str(e)})
                return
            _json_response(self, 200, payload)
            return
        if path in ("/", "/index.html"):
            self._serve_file(STATIC_DIR / "index.html")
            return
        if path.startswith("/static/"):
            rel = path[len("/static/") :]
            self._serve_file(STATIC_DIR / rel)
            return
        # Convenience: /app.css → static
        name = path.lstrip("/")
        candidate = STATIC_DIR / name
        if candidate.is_file():
            self._serve_file(candidate)
            return
        _json_response(self, 404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path != "/api/run":
            _json_response(self, 404, {"error": "not found"})
            return
        try:
            data = _read_json(self)
        except ValueError as e:
            _json_response(self, 400, {"error": str(e)})
            return

        surface = str(data.get("surface") or "").strip()
        goal = str(data.get("goal") or "").strip()
        root = str(data.get("root") or default_root()).strip() or default_root()
        light = bool(data.get("light_research"))
        course_id = str(data.get("course_id") or "").strip() or None
        title = str(data.get("title") or "").strip() or None
        if not surface or not goal:
            _json_response(self, 400, {"error": "surface and goal are required"})
            return
        try:
            attachments = _normalize_attachments(data.get("attachments"))
            inputs = build_run_inputs(
                surface,
                goal,
                root,
                light_research=light,
                attachments=attachments,
                course_id=course_id,
                title=title,
            )
        except ValueError as e:
            _json_response(self, 400, {"error": str(e)})
            return

        try:
            acquire_generation(blocking=False)
        except GenerationBusy as e:
            _json_response(self, 409, {"error": str(e)})
            return

        client: OllamaClient | None
        try:
            client = OllamaClient()
            try:
                client.health()
            except ConnectionError:
                client = None
            # Code and chat need Ollama; recipe surfaces can run deterministic without it.
            if surface in ("code", "chat") and client is None:
                _json_response(
                    self,
                    503,
                    {"error": "Ollama unreachable — required for code/chat surfaces"},
                )
                return

            state = run_manager(
                goal,
                surface=surface,
                inputs=inputs,
                client=client,
            )
            artifacts: list[str] = []
            for r in state.results:
                for a in r.get("artifacts") or []:
                    artifacts.append(str(a))
            if dp := inputs.get("deliverable_path"):
                p = Path(str(dp))
                if not p.is_absolute():
                    p = Path(root) / p
                artifacts.append(str(p))
            # de-dupe preserve order
            seen: set[str] = set()
            uniq: list[str] = []
            for a in artifacts:
                if a not in seen:
                    seen.add(a)
                    uniq.append(a)

            payload = {
                "status": state.status,
                "error": state.error,
                "plan": list(state.plan),
                "results": list(state.results),
                "artifacts": uniq,
                "steps": state.steps,
                "surface": surface,
                "template_id": inputs.get("template_id"),
                "task_id": inputs.get("task_id"),
                "root": root,
                "goal": goal,
                "attachments": attachments,
                "course_id": inputs.get("course_id"),
                "title": inputs.get("title"),
            }
            _record_history(
                {
                    "ts": time.time(),
                    "status": state.status,
                    "surface": surface,
                    "goal_snippet": goal[:120],
                    "goal": goal,
                    "root": root,
                    "template_id": inputs.get("template_id"),
                    "artifacts": uniq,
                    "attachments": attachments,
                    "course_id": inputs.get("course_id"),
                    "title": inputs.get("title"),
                    "error": state.error,
                }
            )
            _json_response(self, 200, payload)
        except Exception as e:
            _json_response(self, 500, {"error": str(e)})
        finally:
            release_generation()

    def _serve_file(self, path: Path) -> None:
        if not path.is_file():
            _json_response(self, 404, {"error": "not found"})
            return
        data = path.read_bytes()
        ctype, _ = mimetypes.guess_type(str(path))
        self.send_response(200)
        self.send_header("Content-Type", ctype or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    httpd = ThreadingHTTPServer((host, port), LacertaHandler)
    print(f"Lacerta GUI at http://{host}:{port}/  (Ctrl+C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        httpd.server_close()
