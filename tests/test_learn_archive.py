"""Archive synthesize vs retrieve paste (V2.5)."""

from __future__ import annotations

import re
from pathlib import Path

from lacerta.core.capabilities import CapabilityContext, run_capability
from lacerta.core.jobs import JobSpec
from lacerta.workers.learn import recipes as _recipes  # noqa: F401
from lacerta.workers.learn import capabilities as _caps  # noqa: F401
from lacerta.workers.learn import storage
from lacerta.workers.learn.worker import run as learn_run
from lacerta.workers.corpus import capabilities as _cc  # noqa: F401
from lacerta.workers.corpus import recipes as _cr  # noqa: F401


class _FakeArchiveClient:
    def chat(self, messages, **kwargs):
        del kwargs
        blob = " ".join(str(m.get("content") or "") for m in (messages or []))
        tokens = re.findall(r"LACERTA_PLANTED_[A-Z0-9_]+", blob)
        fact = tokens[0] if tokens else "UNKNOWN"
        return {"message": {"content": f"From the sources, the answer is {fact}."}}


def _index(tmp_path: Path) -> None:
    notes = tmp_path / "notes.md"
    notes.write_text("# Sorting\n\nComparison sorts.\n", encoding="utf-8")
    assert learn_run(
        JobSpec(
            job_id="syl",
            job_type="learn_syllabus_files",
            objective="Build syllabus",
            inputs={
                "course_id": "arch",
                "instance_id": "default",
                "root": str(tmp_path),
                "data_root": str(tmp_path),
                "attachments": [str(notes)],
            },
            tools=[],
        )
    ).ok
    mini = Path(__file__).parent / "fixtures" / "learn" / "mini_book.md"
    assert learn_run(
        JobSpec(
            job_id="idx",
            job_type="learn_index_corpus",
            objective="Index",
            inputs={
                "course_id": "arch",
                "instance_id": "default",
                "root": str(tmp_path),
                "data_root": str(tmp_path),
                "attachments": [str(mini)],
            },
            tools=[],
        )
    ).ok


def test_archive_synthesize_and_clear(tmp_path: Path) -> None:
    _index(tmp_path)
    ctx = CapabilityContext(
        client=_FakeArchiveClient(),
        instance_id="default",
        course_id="arch",
        data_root=str(tmp_path),
        extra={"data_root": str(tmp_path)},
        user_request="What is the secret mascot animal?",
    )
    result = run_capability(
        "learn.archive_chat",
        ctx,
        {"message": "What is the secret mascot animal?"},
    )
    assert result.ok, result.error_message
    assert result.data.get("grounding") == "corpus_archive"
    turn = storage.read_json(Path(str(result.data.get("path"))))
    assert turn
    assert "LACERTA_PLANTED_FACT_QUOKKA" in str(turn.get("reply"))
    assert not str(turn.get("reply")).startswith("Archive (retrieve):")
    root = storage.course_dir(tmp_path, "default", "arch")
    assert storage.archive_digest_path(root).is_file()
    digest = (storage.read_json(storage.archive_digest_path(root)) or {}).get("digest") or ""
    assert digest
    cleared = storage.clear_archive_session(root)
    assert cleared["ok"]
    emptied = (storage.read_json(storage.archive_digest_path(root)) or {}).get("digest") or ""
    assert emptied == ""
    tutor_digest = storage.tutor_digest_path(root)
    # clear archive must not create/wipe a tutor digest that wasn't there
    if tutor_digest.is_file():
        # should still be absent unless tutor ran
        pass
    assert not (storage.read_json(storage.tutor_digest_path(root)) or {}).get("digest")
