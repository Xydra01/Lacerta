"""Headless GUI API tests (stdlib HTTP server)."""

from __future__ import annotations

import json
import threading
from http.client import HTTPConnection
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from lacerta.core.gen_lock import acquire_generation, release_generation
from lacerta.gui import server as gui_server
from lacerta.gui.server import LacertaHandler, clear_run_history, preview_file, serve
from lacerta.gui.surfaces import build_run_inputs


@pytest.fixture(autouse=True)
def _reset_gui_state() -> None:
    release_generation()
    clear_run_history()
    yield
    release_generation()
    clear_run_history()


@pytest.fixture()
def gui_http(tmp_path: Path):
    """Start ThreadingHTTPServer on an ephemeral port; yield (host, port, root)."""
    host = "127.0.0.1"
    httpd = __import__("http.server", fromlist=["ThreadingHTTPServer"]).ThreadingHTTPServer(
        (host, 0), LacertaHandler
    )
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield host, port, tmp_path
    finally:
        httpd.shutdown()
        httpd.server_close()


def _request(
    host: str,
    port: int,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    conn = HTTPConnection(host, port, timeout=10)
    raw = None
    headers = {}
    if body is not None:
        raw = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
        headers["Content-Length"] = str(len(raw))
    conn.request(method, path, body=raw, headers=headers)
    res = conn.getresponse()
    data = res.read().decode("utf-8")
    conn.close()
    try:
        payload = json.loads(data) if data else {}
    except json.JSONDecodeError:
        payload = {"raw": data}
    return res.status, payload


def test_api_surfaces(gui_http) -> None:
    host, port, _ = gui_http
    status, data = _request(host, port, "GET", "/api/surfaces")
    assert status == 200
    ids = {s["id"] for s in data["surfaces"]}
    assert ids == {"chat", "code", "learn", "research", "writing"}
    research = next(s for s in data["surfaces"] if s["id"] == "research")
    assert research["show_attachments"] is True
    learn = next(s for s in data["surfaces"] if s["id"] == "learn")
    assert learn["show_course_id"] is True
    writing = next(s for s in data["surfaces"] if s["id"] == "writing")
    assert writing["show_title"] is True


def test_preview_under_root(tmp_path: Path) -> None:
    f = tmp_path / "note.md"
    f.write_text("# Hello\nworld\n", encoding="utf-8")
    out = preview_file(path=str(f), root=str(tmp_path))
    assert out["truncated"] is False
    assert "Hello" in out["content"]


def test_preview_rejects_escape(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"outside-{tmp_path.name}.txt"
    outside.write_text("secret", encoding="utf-8")
    with pytest.raises(ValueError, match="under workspace root"):
        preview_file(path=str(outside), root=str(tmp_path))


def test_preview_truncates(tmp_path: Path) -> None:
    f = tmp_path / "big.txt"
    f.write_bytes(b"a" * 1000)
    out = preview_file(path=str(f), root=str(tmp_path), max_bytes=100)
    assert out["truncated"] is True
    assert out["bytes_read"] == 100


def test_preview_rejects_binary(tmp_path: Path) -> None:
    f = tmp_path / "bin.dat"
    f.write_bytes(b"abc\x00def")
    with pytest.raises(ValueError, match="binary"):
        preview_file(path=str(f), root=str(tmp_path))


def test_api_preview(gui_http) -> None:
    host, port, root = gui_http
    f = root / "doc.md"
    f.write_text("preview me", encoding="utf-8")
    from urllib.parse import quote

    path = f"/api/preview?path={quote(str(f))}&root={quote(str(root))}"
    status, data = _request(host, port, "GET", path)
    assert status == 200
    assert data["content"] == "preview me"


def test_api_preview_escape(gui_http) -> None:
    host, port, root = gui_http
    from urllib.parse import quote

    path = f"/api/preview?path={quote('/etc/passwd')}&root={quote(str(root))}"
    status, data = _request(host, port, "GET", path)
    assert status == 400
    assert "root" in data["error"].lower()


def test_build_run_inputs_learn_attachments(tmp_path: Path) -> None:
    paths = [str(tmp_path / "a.md")]
    inputs = build_run_inputs(
        "learn",
        "syllabus",
        str(tmp_path),
        attachments=paths,
        course_id="mac-course",
    )
    assert inputs["attachments"] == paths
    assert inputs["course_id"] == "mac-course"


def test_build_run_inputs_writing_title(tmp_path: Path) -> None:
    inputs = build_run_inputs(
        "writing", "draft", str(tmp_path), title="Mac Notes"
    )
    assert inputs["title"] == "Mac Notes"


@patch("lacerta.gui.server.run_manager")
@patch("lacerta.gui.server.OllamaClient")
def test_api_run_attachments_and_history(
    mock_client_cls: MagicMock,
    mock_run: MagicMock,
    gui_http,
) -> None:
    host, port, root = gui_http
    mock_client = MagicMock()
    mock_client.health.side_effect = ConnectionError("no ollama")
    mock_client_cls.return_value = mock_client

    state = MagicMock()
    state.status = "finished"
    state.error = None
    state.plan = ["research_local"]
    state.results = [
        {"job_id": "j1", "ok": True, "summary": "ok", "artifacts": [str(root / "r.md")]}
    ]
    state.steps = 1
    mock_run.return_value = state

    status, data = _request(
        host,
        port,
        "POST",
        "/api/run",
        {
            "surface": "research",
            "goal": "Summarize notes",
            "root": str(root),
            "attachments": [str(root / "src.md")],
        },
    )
    assert status == 200
    assert data["status"] == "finished"
    assert data["attachments"] == [str(root / "src.md")]
    call_kwargs = mock_run.call_args.kwargs
    assert call_kwargs["inputs"]["attachments"] == [str(root / "src.md")]

    hstatus, hdata = _request(host, port, "GET", "/api/history")
    assert hstatus == 200
    assert len(hdata["runs"]) == 1
    assert hdata["runs"][0]["surface"] == "research"
    assert hdata["runs"][0]["goal_snippet"].startswith("Summarize")


@patch("lacerta.gui.server.OllamaClient")
def test_api_run_409_when_busy(mock_client_cls: MagicMock, gui_http) -> None:
    host, port, root = gui_http
    acquire_generation(blocking=False)
    try:
        status, data = _request(
            host,
            port,
            "POST",
            "/api/run",
            {"surface": "writing", "goal": "Write something long enough", "root": str(root)},
        )
        assert status == 409
        assert "generation" in data["error"].lower() or "progress" in data["error"].lower()
    finally:
        release_generation()


def test_serve_importable() -> None:
    assert callable(serve)
    assert gui_server.PREVIEW_MAX_BYTES == 64 * 1024
    assert gui_server.HISTORY_MAX == 20
