"""Thin local GUI HTTP server (stdlib only)."""

from __future__ import annotations

import json
import mimetypes
import threading
import time
import uuid
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from lacerta.core.gen_lock import GenerationBusy, acquire_generation, release_generation
from lacerta.core.manager import MacroState, run_manager
from lacerta.core.ollama_client import OllamaClient
from lacerta.gui.surfaces import (
    build_run_inputs,
    code_scenario_needs_ollama,
    default_root,
    learn_scenario_needs_ollama,
    list_surfaces,
)
from lacerta.workers.learn import storage as learn_storage


STATIC_DIR = Path(__file__).resolve().parent / "static"

PREVIEW_MAX_BYTES = 64 * 1024
HISTORY_MAX = 20
ACTIVE_RUNS_MAX = 40

# In-process recent runs (newest appended; exposed newest-first).
_run_history: deque[dict[str, Any]] = deque(maxlen=HISTORY_MAX)
_active_runs: dict[str, dict[str, Any]] = {}
_partial_replies: dict[str, str] = {}
_active_lock = threading.Lock()


def clear_run_history() -> None:
    """Test helper: reset in-process history."""
    _run_history.clear()


def clear_active_runs() -> None:
    """Test helper: reset in-process active run registry."""
    with _active_lock:
        _active_runs.clear()
        _partial_replies.clear()


def get_run_history() -> list[dict[str, Any]]:
    """Newest-first snapshot of recent runs."""
    return list(reversed(_run_history))


def get_active_run(run_id: str) -> dict[str, Any] | None:
    with _active_lock:
        rec = _active_runs.get(run_id)
        return dict(rec) if rec else None


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


def _normalize_messages(raw: Any) -> list[dict[str, str]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError("messages must be a list of {role, content}")
    out: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "").strip().lower()
        if role not in ("user", "assistant"):
            continue
        content = str(item.get("content") or "").strip()
        if content:
            out.append({"role": role, "content": content})
    return out


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


def _acceptance_payload(state: MacroState) -> dict[str, Any] | None:
    if state.acceptance_ok is True:
        return {"ok": True, "failures": []}
    if state.acceptance_ok is False:
        return {"ok": False, "failures": list(state.acceptance_failures or [])}
    return None


def _collect_artifacts(state: MacroState, inputs: dict[str, Any], root: str) -> list[str]:
    artifacts: list[str] = []
    for r in state.results:
        for a in r.get("artifacts") or []:
            artifacts.append(str(a))
    if dp := inputs.get("deliverable_path"):
        p = Path(str(dp))
        if not p.is_absolute():
            p = Path(root) / p
        artifacts.append(str(p))
    seen: set[str] = set()
    uniq: list[str] = []
    for a in artifacts:
        if a not in seen:
            seen.add(a)
            uniq.append(a)
    return uniq


def _extract_reply(
    state: MacroState,
    inputs: dict[str, Any],
    *,
    surface: str,
) -> str:
    """Plain user-facing reply. Never the raw artifact JSON blob."""
    for r in reversed(list(state.results or [])):
        for raw in reversed(list(r.get("artifacts") or [])):
            path = Path(str(raw))
            if path.suffix.lower() != ".json" or not path.is_file():
                continue
            try:
                doc = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(doc, dict) and str(doc.get("reply") or "").strip():
                return str(doc["reply"])
    if surface == "chat":
        for r in reversed(list(state.results or [])):
            if r.get("ok") and str(r.get("summary") or "").strip():
                return str(r["summary"])
    if state.status == "failed":
        return str(state.error or "Failed")
    if state.status != "finished":
        return ""
    bits = ["Finished"]
    if inputs.get("deliverable_path"):
        bits.append(str(inputs["deliverable_path"]))
    return " · ".join(bits)


_TURN_CAP = 20


def _learn_turns(course_root: Path, kind: str) -> list[dict[str, Any]]:
    """Last turns as user/assistant rows. Text is question or reply, not JSON."""
    from lacerta.gui.format_reply import render_html

    if kind == "archive":
        index = learn_storage.archive_history_path(course_root)
    else:
        index = learn_storage.tutor_history_path(course_root)
    history = learn_storage.read_json(index) or {}
    entries = list(history.get("turns") or [])[-_TURN_CAP:]
    out: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        path_str = str(entry.get("path") or "")
        if not path_str:
            continue
        turn = learn_storage.read_json(Path(path_str))
        if not isinstance(turn, dict):
            continue
        ts = turn.get("ts") if turn.get("ts") is not None else entry.get("ts")
        question = str(turn.get("question") or turn.get("message") or "").strip()
        reply = str(turn.get("reply") or "").strip()
        if question:
            out.append(
                {
                    "role": "user",
                    "text": question,
                    "ts": ts,
                    "text_html": render_html(question),
                }
            )
        if reply:
            out.append(
                {
                    "role": "assistant",
                    "text": reply,
                    "ts": ts,
                    "text_html": render_html(reply),
                }
            )
    return out


def _snapshot_state(
    run_id: str,
    *,
    surface: str,
    goal: str,
    root: str,
    attachments: list[str],
    inputs: dict[str, Any],
    state: MacroState,
) -> dict[str, Any]:
    acceptance = _acceptance_payload(state)
    from lacerta.gui.format_reply import render_html

    reply = _extract_reply(state, inputs, surface=surface)
    payload = {
        "run_id": run_id,
        "status": state.status if state.status != "running" else "running",
        "error": state.error,
        "plan": list(state.plan),
        "results": list(state.results),
        "artifacts": _collect_artifacts(state, inputs, root),
        "steps": state.steps,
        "surface": surface,
        "template_id": inputs.get("template_id"),
        "task_id": inputs.get("task_id"),
        "root": root,
        "goal": goal,
        "attachments": attachments,
        "course_id": inputs.get("course_id"),
        "title": inputs.get("title"),
        "scenario": inputs.get("scenario"),
        "acceptance": acceptance,
        "reply": reply,
        "reply_html": render_html(reply) if reply else "",
    }
    return payload


def _activity_label(plan: list[Any], partial: str) -> str:
    """One step label for the Replies panel while a run is in flight."""
    last = str(plan[-1]) if plan else ""
    if last.startswith("llm:"):
        last = last[4:]
    if partial and last in ("learn_tutor_turn", "learn_archive_chat", "chat_answer"):
        return "Generating reply"
    if last == "learn_index_corpus":
        return "Indexing sources"
    if last in ("learn_mastery_check", "learn_assessment", "learn_practice_quiz"):
        return "Grading"
    if last in ("research_light", "learn_tutor_turn", "learn_archive_chat"):
        return "Retrieving"
    return "Working"


def _apply_partial(run_id: str, payload: dict[str, Any]) -> None:
    """Merge the in-memory reply buffer. Finished/failed runs drop it."""
    from lacerta.gui.format_reply import render_html

    if payload.get("status") != "running":
        _partial_replies.pop(run_id, None)
        payload["partial_reply"] = ""
        payload["partial_reply_html"] = ""
        payload["activity"] = ""
        return
    partial = _partial_replies.get(run_id, "")
    payload["partial_reply"] = partial
    payload["partial_reply_html"] = (
        render_html(partial, hide_unclosed_math=True) if partial else ""
    )
    payload["activity"] = _activity_label(list(payload.get("plan") or []), partial)


def _set_partial_reply(run_id: str, text: str) -> None:
    from lacerta.gui.format_reply import render_html

    with _active_lock:
        _partial_replies[run_id] = text
        rec = _active_runs.get(run_id)
        if rec is None or rec.get("status") != "running":
            return
        rec["partial_reply"] = text
        rec["partial_reply_html"] = render_html(text, hide_unclosed_math=True)
        rec["activity"] = _activity_label(list(rec.get("plan") or []), text)


def _update_active(run_id: str, payload: dict[str, Any]) -> None:
    with _active_lock:
        _apply_partial(run_id, payload)
        _active_runs[run_id] = payload
        # Bound memory: drop oldest finished entries beyond cap.
        if len(_active_runs) > ACTIVE_RUNS_MAX:
            finished = [
                rid
                for rid, rec in _active_runs.items()
                if rec.get("status") in ("finished", "failed")
            ]
            for rid in finished[: max(0, len(_active_runs) - ACTIVE_RUNS_MAX)]:
                _active_runs.pop(rid, None)
                _partial_replies.pop(rid, None)


def _execute_run(
    run_id: str,
    *,
    surface: str,
    goal: str,
    root: str,
    attachments: list[str],
    inputs: dict[str, Any],
    client: OllamaClient | None,
) -> None:
    def on_progress(state: MacroState) -> None:
        _update_active(
            run_id,
            _snapshot_state(
                run_id,
                surface=surface,
                goal=goal,
                root=root,
                attachments=attachments,
                inputs=inputs,
                state=state,
            ),
        )

    if client is not None:
        client.on_delta = lambda text: _set_partial_reply(run_id, text)  # type: ignore[attr-defined]

    try:
        state = run_manager(
            goal,
            surface=surface,
            inputs=inputs,
            client=client,
            on_progress=on_progress,
        )
        payload = _snapshot_state(
            run_id,
            surface=surface,
            goal=goal,
            root=root,
            attachments=attachments,
            inputs=inputs,
            state=state,
        )
        _update_active(run_id, payload)
        _record_history(
            {
                "ts": time.time(),
                "run_id": run_id,
                "status": state.status,
                "surface": surface,
                "goal_snippet": goal[:120],
                "goal": goal,
                "root": root,
                "template_id": inputs.get("template_id"),
                "artifacts": payload["artifacts"],
                "attachments": attachments,
                "course_id": inputs.get("course_id"),
                "title": inputs.get("title"),
                "scenario": inputs.get("scenario"),
                "acceptance": payload.get("acceptance"),
                "error": state.error,
            }
        )
    except Exception as e:
        _update_active(
            run_id,
            {
                "run_id": run_id,
                "status": "failed",
                "error": str(e),
                "plan": [],
                "results": [],
                "artifacts": [],
                "steps": 0,
                "surface": surface,
                "goal": goal,
                "root": root,
                "attachments": attachments,
                "acceptance": None,
            },
        )
        _record_history(
            {
                "ts": time.time(),
                "run_id": run_id,
                "status": "failed",
                "surface": surface,
                "goal_snippet": goal[:120],
                "goal": goal,
                "root": root,
                "error": str(e),
                "artifacts": [],
                "attachments": attachments,
            }
        )
    finally:
        release_generation()


class LacertaHandler(BaseHTTPRequestHandler):
    server_version = "LacertaGUI/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:
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
        if path.startswith("/api/runs/"):
            run_id = path[len("/api/runs/") :].strip("/")
            if not run_id or "/" in run_id:
                _json_response(self, 404, {"error": "not found"})
                return
            rec = get_active_run(run_id)
            if rec is None:
                _json_response(self, 404, {"error": "unknown run_id"})
                return
            _json_response(self, 200, rec)
            return
        if path == "/api/learn/course":
            root = (qs.get("root") or [default_root()])[0]
            course_id = (qs.get("course_id") or ["gui-course"])[0].strip() or "gui-course"
            instance_id = (qs.get("instance_id") or ["gui"])[0].strip() or "gui"
            payload = learn_storage.load_course_browse(root, instance_id, course_id)
            _json_response(self, 200, payload)
            return
        if path == "/api/learn/turns":
            root = (qs.get("root") or [default_root()])[0]
            course_id = (qs.get("course_id") or ["gui-course"])[0].strip() or "gui-course"
            instance_id = (qs.get("instance_id") or ["gui"])[0].strip() or "gui"
            kind = (qs.get("kind") or ["tutor"])[0].strip().lower()
            if kind not in ("tutor", "archive"):
                _json_response(self, 400, {"error": "kind must be tutor or archive"})
                return
            course_root = learn_storage.course_dir(root, instance_id, course_id)
            _json_response(self, 200, {"kind": kind, "turns": _learn_turns(course_root, kind)})
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
        name = path.lstrip("/")
        candidate = STATIC_DIR / name
        if candidate.is_file():
            self._serve_file(candidate)
            return
        _json_response(self, 404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/learn/tutor/clear":
            try:
                data = _read_json(self)
            except ValueError as e:
                _json_response(self, 400, {"error": str(e)})
                return
            root = str(data.get("root") or default_root()).strip() or default_root()
            course_id = str(data.get("course_id") or "").strip() or "gui-course"
            instance_id = str(data.get("instance_id") or "").strip() or "gui"
            course_root = learn_storage.ensure_course_dirs(root, instance_id, course_id)
            payload = learn_storage.clear_tutor_session(course_root)
            _json_response(self, 200, payload)
            return
        if path == "/api/learn/archive/clear":
            try:
                data = _read_json(self)
            except ValueError as e:
                _json_response(self, 400, {"error": str(e)})
                return
            root = str(data.get("root") or default_root()).strip() or default_root()
            course_id = str(data.get("course_id") or "").strip() or "gui-course"
            instance_id = str(data.get("instance_id") or "").strip() or "gui"
            course_root = learn_storage.ensure_course_dirs(root, instance_id, course_id)
            payload = learn_storage.clear_archive_session(course_root)
            _json_response(self, 200, payload)
            return
        if path == "/api/learn/mastery/grade":
            try:
                data = _read_json(self)
            except ValueError as e:
                _json_response(self, 400, {"error": str(e)})
                return
            root = str(data.get("root") or default_root()).strip() or default_root()
            course_id = str(data.get("course_id") or "").strip() or "gui-course"
            instance_id = str(data.get("instance_id") or "").strip() or "gui"
            node_id = str(data.get("node_id") or "").strip()
            answers = data.get("answers")
            if not node_id:
                _json_response(self, 400, {"error": "node_id is required"})
                return
            if not isinstance(answers, list):
                _json_response(self, 400, {"error": "answers must be a list"})
                return
            from lacerta.workers.learn import capabilities as learn_caps

            course_root = learn_storage.ensure_course_dirs(root, instance_id, course_id)
            payload = learn_caps.grade_mastery_check(course_root, node_id, answers)
            status = 200 if payload.get("ok") else 400
            _json_response(self, status, payload)
            return
        if path == "/api/learn/mastery/check":
            # Return latest generated mastery check JSON for GUI MC rendering
            try:
                data = _read_json(self)
            except ValueError as e:
                _json_response(self, 400, {"error": str(e)})
                return
            root = str(data.get("root") or default_root()).strip() or default_root()
            course_id = str(data.get("course_id") or "").strip() or "gui-course"
            instance_id = str(data.get("instance_id") or "").strip() or "gui"
            node_id = str(data.get("node_id") or "").strip()
            if not node_id:
                _json_response(self, 400, {"error": "node_id is required"})
                return
            course_root = learn_storage.course_dir(root, instance_id, course_id)
            path_check = learn_storage.mastery_check_path(course_root, node_id)
            doc = learn_storage.read_json(path_check)
            if not doc:
                _json_response(self, 404, {"error": "mastery check not found"})
                return
            # Strip correct_index from client payload? Keep for thin local GUI honesty —
            # grade is still server-side. Hide answers from response for slightly less spoiler:
            safe_qs = []
            for q in doc.get("questions") or []:
                if not isinstance(q, dict):
                    continue
                safe_qs.append(
                    {
                        "id": q.get("id"),
                        "prompt": q.get("prompt"),
                        "choices": q.get("choices"),
                        "node_id": q.get("node_id"),
                        "target_tier": q.get("target_tier"),
                    }
                )
            _json_response(
                self,
                200,
                {
                    "node_id": doc.get("node_id"),
                    "title": doc.get("title"),
                    "current_tier": doc.get("current_tier"),
                    "target_tier": doc.get("target_tier"),
                    "questions": safe_qs,
                },
            )
            return
        if path == "/api/learn/practice/quiz":
            try:
                data = _read_json(self)
            except ValueError as e:
                _json_response(self, 400, {"error": str(e)})
                return
            root = str(data.get("root") or default_root()).strip() or default_root()
            course_id = str(data.get("course_id") or "").strip() or "gui-course"
            instance_id = str(data.get("instance_id") or "").strip() or "gui"
            node_id = str(data.get("node_id") or "").strip()
            if not node_id:
                _json_response(self, 400, {"error": "node_id is required"})
                return
            course_root = learn_storage.course_dir(root, instance_id, course_id)
            path_quiz = learn_storage.quiz_path(course_root, node_id)
            doc = learn_storage.read_json(path_quiz)
            if not doc:
                _json_response(self, 404, {"error": "practice quiz not found"})
                return
            safe_qs = []
            for q in doc.get("questions") or []:
                if not isinstance(q, dict):
                    continue
                safe_qs.append(
                    {
                        "id": q.get("id"),
                        "prompt": q.get("prompt"),
                        "choices": q.get("choices"),
                        "node_id": q.get("node_id"),
                        "target_tier": q.get("target_tier"),
                    }
                )
            _json_response(
                self,
                200,
                {
                    "node_id": doc.get("node_id"),
                    "title": doc.get("title"),
                    "current_tier": doc.get("current_tier"),
                    "target_tier": doc.get("target_tier"),
                    "questions": safe_qs,
                },
            )
            return
        if path == "/api/learn/practice/grade":
            try:
                data = _read_json(self)
            except ValueError as e:
                _json_response(self, 400, {"error": str(e)})
                return
            root = str(data.get("root") or default_root()).strip() or default_root()
            course_id = str(data.get("course_id") or "").strip() or "gui-course"
            instance_id = str(data.get("instance_id") or "").strip() or "gui"
            node_id = str(data.get("node_id") or "").strip()
            answers = data.get("answers")
            if not node_id:
                _json_response(self, 400, {"error": "node_id is required"})
                return
            if not isinstance(answers, list):
                _json_response(self, 400, {"error": "answers must be a list"})
                return
            from lacerta.workers.learn import capabilities as learn_caps

            course_root = learn_storage.ensure_course_dirs(root, instance_id, course_id)
            payload = learn_caps.grade_practice_quiz(course_root, node_id, answers)
            status = 200 if payload.get("ok") else 400
            _json_response(self, status, payload)
            return
        if path == "/api/learn/practice/flashcards":
            try:
                data = _read_json(self)
            except ValueError as e:
                _json_response(self, 400, {"error": str(e)})
                return
            root = str(data.get("root") or default_root()).strip() or default_root()
            course_id = str(data.get("course_id") or "").strip() or "gui-course"
            instance_id = str(data.get("instance_id") or "").strip() or "gui"
            node_id = str(data.get("node_id") or "").strip()
            if not node_id:
                _json_response(self, 400, {"error": "node_id is required"})
                return
            from lacerta.core.capabilities import CapabilityContext, run_capability
            from lacerta.workers.learn import capabilities as _lc  # noqa: F401

            ctx = CapabilityContext(
                data_root=root,
                instance_id=instance_id,
                course_id=course_id,
                extra={"data_root": root, "node_id": node_id},
            )
            result = run_capability(
                "learn.generate_flashcards",
                ctx,
                {"node_id": node_id},
            )
            if not result.ok:
                _json_response(
                    self,
                    400,
                    {"error": result.error_message or result.error_code},
                )
                return
            course_root = learn_storage.course_dir(root, instance_id, course_id)
            doc = learn_storage.read_json(learn_storage.flashcards_path(course_root, node_id)) or {}
            _json_response(
                self,
                200,
                {
                    "path": result.data.get("path"),
                    "cards": doc.get("cards") or [],
                    "node_id": node_id,
                },
            )
            return
        if path == "/api/learn/practice/study_guide":
            try:
                data = _read_json(self)
            except ValueError as e:
                _json_response(self, 400, {"error": str(e)})
                return
            root = str(data.get("root") or default_root()).strip() or default_root()
            course_id = str(data.get("course_id") or "").strip() or "gui-course"
            instance_id = str(data.get("instance_id") or "").strip() or "gui"
            node_id = str(data.get("node_id") or "").strip()
            if not node_id:
                _json_response(self, 400, {"error": "node_id is required"})
                return
            from lacerta.core.capabilities import CapabilityContext, run_capability
            from lacerta.workers.learn import capabilities as _lc  # noqa: F401

            ctx = CapabilityContext(
                data_root=root,
                instance_id=instance_id,
                course_id=course_id,
                extra={"data_root": root, "node_id": node_id},
            )
            result = run_capability(
                "learn.generate_study_guide",
                ctx,
                {"node_id": node_id},
            )
            if not result.ok:
                _json_response(
                    self,
                    400,
                    {"error": result.error_message or result.error_code},
                )
                return
            _json_response(
                self,
                200,
                {
                    "path": result.data.get("path"),
                    "node_id": node_id,
                },
            )
            return
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
        scenario = str(data.get("scenario") or "").strip() or None
        node_id = str(data.get("node_id") or "").strip() or None
        if not surface or not goal:
            _json_response(self, 400, {"error": "surface and goal are required"})
            return
        try:
            attachments = _normalize_attachments(data.get("attachments"))
            messages = _normalize_messages(data.get("messages")) if surface == "chat" else []
            inputs = build_run_inputs(
                surface,
                goal,
                root,
                light_research=light,
                attachments=attachments,
                course_id=course_id,
                title=title,
                scenario=scenario,
                messages=messages or None,
                node_id=node_id,
            )
        except ValueError as e:
            _json_response(self, 400, {"error": str(e)})
            return

        try:
            acquire_generation(blocking=False)
        except GenerationBusy as e:
            _json_response(self, 409, {"error": str(e)})
            return

        client: OllamaClient | None = None
        try:
            client = OllamaClient()
            try:
                client.health()
            except ConnectionError:
                client = None
            needs_ollama = surface == "chat"
            if surface == "code":
                needs_ollama = code_scenario_needs_ollama(
                    str(inputs.get("scenario") or scenario)
                )
            elif surface == "learn":
                needs_ollama = learn_scenario_needs_ollama(
                    str(inputs.get("scenario") or scenario)
                )
            if needs_ollama and client is None:
                release_generation()
                _json_response(
                    self,
                    503,
                    {"error": "Ollama unreachable — required for this run"},
                )
                return

            run_id = uuid.uuid4().hex[:12]
            _update_active(
                run_id,
                {
                    "run_id": run_id,
                    "status": "running",
                    "error": None,
                    "plan": [],
                    "results": [],
                    "artifacts": [],
                    "steps": 0,
                    "surface": surface,
                    "goal": goal,
                    "root": root,
                    "attachments": attachments,
                    "template_id": inputs.get("template_id"),
                    "task_id": inputs.get("task_id"),
                    "scenario": inputs.get("scenario"),
                    "acceptance": None,
                    "partial_reply": "",
                    "partial_reply_html": "",
                    "activity": "Working",
                },
            )
            thread = threading.Thread(
                target=_execute_run,
                kwargs={
                    "run_id": run_id,
                    "surface": surface,
                    "goal": goal,
                    "root": root,
                    "attachments": attachments,
                    "inputs": inputs,
                    "client": client,
                },
                daemon=True,
            )
            thread.start()
            _json_response(
                self,
                202,
                {"run_id": run_id, "status": "running"},
            )
        except Exception as e:
            release_generation()
            _json_response(self, 500, {"error": str(e)})

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
