"""Headless GUI API tests (stdlib HTTP server)."""

from __future__ import annotations

import json
import threading
import time
from http.client import HTTPConnection
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from lacerta.core.gen_lock import acquire_generation, release_generation
from lacerta.gui import server as gui_server
from lacerta.gui.server import (
    LacertaHandler,
    clear_active_runs,
    clear_run_history,
    preview_file,
    serve,
)
from lacerta.gui.surfaces import build_run_inputs


@pytest.fixture(autouse=True)
def _reset_gui_state() -> None:
    release_generation()
    clear_run_history()
    clear_active_runs()
    yield
    release_generation()
    clear_run_history()
    clear_active_runs()


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


def _poll_until_done(
    host: str, port: int, run_id: str, *, timeout_s: float = 5.0
) -> dict[str, Any]:
    deadline = time.time() + timeout_s
    last: dict[str, Any] = {}
    while time.time() < deadline:
        status, data = _request(host, port, "GET", f"/api/runs/{run_id}")
        assert status == 200, data
        last = data
        if data.get("status") in ("finished", "failed"):
            return data
        time.sleep(0.05)
    raise AssertionError(f"run {run_id} did not finish: {last}")


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
    chat = next(s for s in data["surfaces"] if s["id"] == "chat")
    assert chat["show_workspace_root"] is False
    assert chat["cta_label"] == "Send"
    assert chat["goal_label"] == "Message"


def test_api_surfaces_learn_visibility_matrix(gui_http) -> None:
    host, port, _ = gui_http
    status, data = _request(host, port, "GET", "/api/surfaces")
    assert status == 200
    learn = next(s for s in data["surfaces"] if s["id"] == "learn")
    by_id = {s["id"]: s for s in learn["learn_scenarios"]}
    for sid in ("build_syllabus", "tutor", "assessment", "mastery_check", "practice", "archive", "index_sources"):
        s = by_id[sid]
        assert s["show_course_browser"] is True
        assert s["cta_label"]
        assert s["goal_label"]
        assert "hint" in s
    assert by_id["tutor"]["show_attachments"] is False
    assert by_id["assessment"]["show_attachments"] is False
    assert by_id["build_syllabus"]["show_attachments"] is True
    assert by_id["build_syllabus"]["require_attachments"] is True
    assert by_id["index_sources"]["show_attachments"] is True
    assert by_id["index_sources"]["require_attachments"] is True
    assert by_id["tutor"]["cta_label"] == "Ask tutor"
    assert by_id["tutor"]["goal_label"] == "Question"


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
    state.acceptance_ok = None
    state.acceptance_failures = []
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
    assert status == 202
    assert data["status"] == "running"
    assert data.get("run_id")
    done = _poll_until_done(host, port, data["run_id"])
    assert done["status"] == "finished"
    assert done["attachments"] == [str(root / "src.md")]
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


def test_api_surfaces_include_code_scenarios(gui_http) -> None:
    host, port, _ = gui_http
    status, data = _request(host, port, "GET", "/api/surfaces")
    assert status == 200
    code = next(s for s in data["surfaces"] if s["id"] == "code")
    assert code["show_code_scenario"] is True
    assert {s["id"] for s in code["code_scenarios"]} == {
        "quick_file_check",
        "habit_tracker",
    }
    for s in code["code_scenarios"]:
        assert s["cta_label"]
        assert s["goal_label"]
        assert s["show_workspace_root"] is True
        assert s["show_course_browser"] is False
    learn = next(s for s in data["surfaces"] if s["id"] == "learn")
    assert learn["show_learn_scenario"] is True
    assert {s["id"] for s in learn["learn_scenarios"]} == {
        "build_syllabus",
        "tutor",
        "assessment",
        "mastery_check",
        "practice",
        "archive",
        "index_sources",
    }
    research = next(s for s in data["surfaces"] if s["id"] == "research")
    assert research["show_research_scenario"] is True
    assert {s["id"] for s in research["research_scenarios"]} == {
        "offline_sources",
        "light_web",
    }
    for s in research["research_scenarios"]:
        assert s["cta_label"]
        assert s["goal_label"]
    writing = next(s for s in data["surfaces"] if s["id"] == "writing")
    assert writing["show_writing_scenario"] is True
    assert {s["id"] for s in writing["writing_scenarios"]} == {
        "short_draft",
        "from_sources",
    }
    for s in writing["writing_scenarios"]:
        assert s["cta_label"]
        assert s["goal_label"]


@patch("lacerta.gui.server.run_manager")
@patch("lacerta.gui.server.OllamaClient")
def test_api_learn_course_browse(
    mock_client_cls: MagicMock,
    mock_run: MagicMock,
    gui_http,
) -> None:
    del mock_client_cls, mock_run
    host, port, root = gui_http
    from lacerta.workers.learn import storage as learn_storage

    course_root = learn_storage.ensure_course_dirs(root, "gui", "gui-course")
    learn_storage.ensure_course_meta(root, "gui", "gui-course")
    learn_storage.write_json(
        learn_storage.syllabus_path(course_root),
        {
            "status": "active",
            "nodes": [
                {"id": "n1", "title": "Intro", "parent_id": None, "mastery_tier": 0},
                {"id": "n2", "title": "Next", "parent_id": "n1", "mastery_tier": 0},
            ],
        },
    )
    learn_storage.ensure_mastery(
        course_root,
        learn_storage.read_json(learn_storage.syllabus_path(course_root)),
    )
    learn_storage.set_node_tier(course_root, "n1", 2)
    from urllib.parse import quote

    status, data = _request(
        host,
        port,
        "GET",
        f"/api/learn/course?root={quote(str(root))}&course_id=gui-course&instance_id=gui",
    )
    assert status == 200
    assert data["exists"] is True
    assert data["node_count"] == 2
    by_id = {n["id"]: n for n in data["nodes"]}
    assert by_id["n1"]["mastery_tier"] == 2
    assert data["corpus"]["status"] == "pending"


@patch("lacerta.gui.server.run_manager")
@patch("lacerta.gui.server.OllamaClient")
def test_api_mastery_grade(
    mock_client_cls: MagicMock,
    mock_run: MagicMock,
    gui_http,
) -> None:
    del mock_client_cls, mock_run
    host, port, root = gui_http
    from lacerta.workers.learn import storage as learn_storage

    course_root = learn_storage.ensure_course_dirs(root, "gui", "gui-course")
    learn_storage.write_json(
        learn_storage.syllabus_path(course_root),
        {
            "status": "active",
            "nodes": [{"id": "n1", "title": "Intro", "parent_id": None, "mastery_tier": 0}],
        },
    )
    learn_storage.ensure_mastery(
        course_root,
        learn_storage.read_json(learn_storage.syllabus_path(course_root)),
    )
    learn_storage.write_json(
        learn_storage.mastery_check_path(course_root, "n1"),
        {
            "node_id": "n1",
            "questions": [
                {
                    "id": "mc-n1-1",
                    "prompt": "q",
                    "choices": ["a", "b", "c", "d"],
                    "correct_index": 0,
                },
                {
                    "id": "mc-n1-2",
                    "prompt": "q2",
                    "choices": ["a", "b", "c", "d"],
                    "correct_index": 0,
                },
            ],
        },
    )
    status, data = _request(
        host,
        port,
        "POST",
        "/api/learn/mastery/grade",
        {
            "root": str(root),
            "course_id": "gui-course",
            "instance_id": "gui",
            "node_id": "n1",
            "answers": [
                {"question_id": "mc-n1-1", "selected_index": 0},
                {"question_id": "mc-n1-2", "selected_index": 0},
            ],
        },
    )
    assert status == 200
    assert data["passed"] is True
    assert data["tier"] == 1


@patch("lacerta.gui.server.run_manager")
@patch("lacerta.gui.server.OllamaClient")
def test_api_habit_tracker_without_ollama(
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
    state.plan = ["code_recon", "code_edit", "code_test"]
    state.results = [
        {"job_id": "h1", "ok": True, "summary": "recon", "artifacts": []},
        {"job_id": "h2", "ok": True, "summary": "edit", "artifacts": [str(root / "habit.py")]},
        {"job_id": "h3", "ok": True, "summary": "test", "artifacts": []},
    ]
    state.steps = 3
    state.acceptance_ok = True
    state.acceptance_failures = []
    mock_run.return_value = state

    status, data = _request(
        host,
        port,
        "POST",
        "/api/run",
        {
            "surface": "code",
            "goal": "Build habit tracker",
            "root": str(root),
            "scenario": "habit_tracker",
        },
    )
    assert status == 202
    done = _poll_until_done(host, port, data["run_id"])
    assert done["scenario"] == "habit_tracker"
    assert done["template_id"] == "tpl.code.habit"
    assert done["plan"] == ["code_recon", "code_edit", "code_test"]
    assert done["acceptance"] == {"ok": True, "failures": []}
    assert mock_run.call_args.kwargs["inputs"]["deterministic_habit"] is True


@patch("lacerta.gui.server.run_manager")
@patch("lacerta.gui.server.OllamaClient")
def test_api_chat_messages_passed_to_manager(
    mock_client_cls: MagicMock,
    mock_run: MagicMock,
    gui_http,
) -> None:
    host, port, root = gui_http
    mock_client = MagicMock()
    mock_client.health.return_value = True
    mock_client_cls.return_value = mock_client

    state = MagicMock()
    state.status = "finished"
    state.error = None
    state.plan = ["chat_answer"]
    state.results = [
        {"job_id": "c1", "ok": True, "summary": "hi again", "artifacts": []}
    ]
    state.steps = 1
    state.acceptance_ok = None
    state.acceptance_failures = []
    mock_run.return_value = state

    prior = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]
    status, data = _request(
        host,
        port,
        "POST",
        "/api/run",
        {
            "surface": "chat",
            "goal": "follow up",
            "root": str(root),
            "messages": prior,
        },
    )
    assert status == 202
    done = _poll_until_done(host, port, data["run_id"])
    assert done["status"] == "finished"
    assert mock_run.call_args.kwargs["inputs"]["messages"] == prior


@patch("lacerta.gui.server.OllamaClient")
def test_api_quick_file_check_requires_ollama(mock_client_cls: MagicMock, gui_http) -> None:
    host, port, root = gui_http
    mock_client = MagicMock()
    mock_client.health.side_effect = ConnectionError("no ollama")
    mock_client_cls.return_value = mock_client

    status, data = _request(
        host,
        port,
        "POST",
        "/api/run",
        {
            "surface": "code",
            "goal": "Create harness_smoke.py that prints HARNESS_OK",
            "root": str(root),
            "scenario": "quick_file_check",
        },
    )
    assert status == 503
    assert "ollama" in data["error"].lower()
