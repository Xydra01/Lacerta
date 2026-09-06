"""Thin local GUI HTTP server (stdlib only)."""

from __future__ import annotations

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from lacerta.core.gen_lock import GenerationBusy, acquire_generation, release_generation
from lacerta.core.manager import run_manager
from lacerta.core.ollama_client import OllamaClient
from lacerta.gui.surfaces import build_run_inputs, default_root, list_surfaces

STATIC_DIR = Path(__file__).resolve().parent / "static"


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


class LacertaHandler(BaseHTTPRequestHandler):
    server_version = "LacertaGUI/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        # Quiet default console spam; still show errors via print in handlers.
        return

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/surfaces":
            _json_response(
                self,
                200,
                {"surfaces": list_surfaces(), "default_root": default_root()},
            )
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
        if not surface or not goal:
            _json_response(self, 400, {"error": "surface and goal are required"})
            return
        try:
            inputs = build_run_inputs(
                surface,
                goal,
                root,
                light_research=light,
                attachments=list(data.get("attachments") or []),
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
            }
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
