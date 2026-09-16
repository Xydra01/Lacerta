"""V2.2 tutor teach + compressed history."""

from __future__ import annotations

import re
from pathlib import Path

from lacerta.core.capabilities import CapabilityContext, run_capability
from lacerta.core.jobs import JobSpec
from lacerta.workers.learn import capabilities as learn_caps  # noqa: F401
from lacerta.workers.learn import recipes as learn_recipes  # noqa: F401
from lacerta.workers.learn import storage
from lacerta.workers.learn.worker import run as learn_run


def _seed_and_index(tmp_path: Path, *, course_id: str = "tutor-v22") -> Path:
    from lacerta.workers.corpus import capabilities as _cc  # noqa: F401

    ctx = CapabilityContext(
        instance_id="default",
        course_id=course_id,
        data_root=str(tmp_path),
        user_request="Algorithms",
        attachments=[],
        extra={"topic": "Algorithms", "data_root": str(tmp_path)},
    )
    fixture = Path(__file__).parent / "fixtures" / "learn" / "course_notes.md"
    ctx.attachments = [str(fixture)]
    assert run_capability("learn.ingest_course_materials", ctx, {"topic": "Algorithms"}).ok
    assert run_capability("learn.write_syllabus", ctx, {}).ok
    assert run_capability("learn.finalize_course", ctx, {}).ok
    mini = Path(__file__).parent / "fixtures" / "learn" / "mini_book.md"
    idx = learn_run(
        JobSpec(
            job_id="idx-v22",
            job_type="learn_index_corpus",
            objective="Index",
            inputs={
                "course_id": course_id,
                "instance_id": "default",
                "root": str(tmp_path),
                "data_root": str(tmp_path),
                "attachments": [str(mini)],
            },
            tools=[],
        )
    )
    assert idx.ok, idx.error
    return storage.course_dir(tmp_path, "default", course_id)


class _TeachClient:
    """Echo planted tokens from the user prompt as a teaching reply."""

    def __init__(self) -> None:
        self.calls: list[list[dict[str, str]]] = []

    def chat(self, messages, **kwargs):
        del kwargs
        self.calls.append(list(messages or []))
        blob = " ".join(str(m.get("content") or "") for m in (messages or []))
        tokens = re.findall(r"LACERTA_PLANTED_[A-Z0-9_]+", blob)
        fact = tokens[0] if tokens else "unknown"
        return {
            "message": {
                "content": (
                    f"From the course sources: the secret is {fact}. "
                    "Try restating that in one sentence."
                )
            }
        }


def test_compress_tutor_history_enforces_caps() -> None:
    dig = ""
    for i in range(20):
        dig = storage.compress_tutor_history(
            dig,
            f"question number {i} " + ("x" * 80),
            f"answer number {i} " + ("y" * 200),
            max_chars=200,
        )
        assert len(dig) <= 200
    assert dig
    assert "Q:" in dig


def test_clear_tutor_session(tmp_path: Path) -> None:
    root = _seed_and_index(tmp_path)
    storage.save_tutor_digest(root, "prior digest text", turn_count=3)
    storage.write_json(
        storage.tutor_history_path(root),
        {"turns": [{"ts": 1, "path": "x", "question": "q"}]},
    )
    out = storage.clear_tutor_session(root)
    assert out["ok"] is True
    dig = storage.read_json(storage.tutor_digest_path(root))
    assert dig and dig.get("digest") == ""
    hist = storage.read_json(storage.tutor_history_path(root))
    assert hist and hist.get("turns") == []


def test_tutor_synthesize_from_corpus_with_mock(tmp_path: Path) -> None:
    root = _seed_and_index(tmp_path)
    client = _TeachClient()
    ctx = CapabilityContext(
        client=client,
        instance_id="default",
        course_id="tutor-v22",
        data_root=str(tmp_path),
        user_request="What is the secret mascot animal?",
        extra={"data_root": str(tmp_path)},
    )
    result = run_capability(
        "learn.tutor_turn",
        ctx,
        {"question": "What is the secret mascot animal?"},
    )
    assert result.ok, result.error_message
    turn = storage.read_json(Path(result.data["path"]))
    assert turn
    assert turn.get("grounding") == "corpus_teach"
    reply = str(turn.get("reply") or "")
    assert "LACERTA_PLANTED_FACT_QUOKKA" in reply
    assert not reply.startswith("Tutor (corpus retrieve):")
    assert turn.get("citations")
    assert client.calls
    digest = storage.read_json(storage.tutor_digest_path(root))
    assert digest and "Q:" in str(digest.get("digest") or "")


def test_tutor_corpus_retrieve_fallback_without_client(tmp_path: Path) -> None:
    _seed_and_index(tmp_path, course_id="tutor-fallback")
    ctx = CapabilityContext(
        client=None,
        instance_id="default",
        course_id="tutor-fallback",
        data_root=str(tmp_path),
        user_request="What is the secret mascot animal?",
        extra={"data_root": str(tmp_path)},
    )
    result = run_capability(
        "learn.tutor_turn",
        ctx,
        {"question": "What is the secret mascot animal?"},
    )
    assert result.ok, result.error_message
    turn = storage.read_json(Path(result.data["path"]))
    assert turn
    assert turn.get("grounding") == "corpus_retrieve"
    reply = str(turn.get("reply") or "")
    assert reply.startswith("Tutor (corpus retrieve):")
    assert "LACERTA_PLANTED_FACT_QUOKKA" in reply


def test_tutor_second_turn_includes_digest(tmp_path: Path) -> None:
    root = _seed_and_index(tmp_path, course_id="tutor-hist")
    client = _TeachClient()
    ctx = CapabilityContext(
        client=client,
        instance_id="default",
        course_id="tutor-hist",
        data_root=str(tmp_path),
        user_request="What is the secret mascot animal?",
        extra={"data_root": str(tmp_path)},
    )
    r1 = run_capability(
        "learn.tutor_turn",
        ctx,
        {"question": "What is the secret mascot animal?"},
    )
    assert r1.ok, r1.error_message
    r2 = run_capability(
        "learn.tutor_turn",
        ctx,
        {"question": "Remind me what we just covered"},
    )
    assert r2.ok, r2.error_message
    assert len(client.calls) >= 2
    second_user = client.calls[-1][-1]["content"]
    assert "Compressed prior session" in second_user or "Prior Q:" in second_user
    digest = storage.read_json(storage.tutor_digest_path(root))
    assert digest and int(digest.get("turn_count") or 0) >= 2
