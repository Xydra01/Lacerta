"""Shared corpus storage + retrieve caps (V1.35)."""

from __future__ import annotations

from pathlib import Path

from lacerta.core.capabilities import CapabilityContext, run_capability, run_recipe
from lacerta.core.jobs import JobSpec
from lacerta.storage import corpus as corpus_storage
from lacerta.workers.corpus import capabilities as _corpus_caps  # noqa: F401
from lacerta.workers.corpus import recipes as _corpus_recipes  # noqa: F401


def test_fingerprint_and_stale(tmp_path: Path) -> None:
    root = tmp_path / "corpus"
    corpus_storage.ensure_corpus_layout(root)
    src = corpus_storage.sources_dir(root) / "notes.md"
    src.write_text("hello world", encoding="utf-8")
    meta = corpus_storage.default_meta("c1")
    meta["source_fingerprints"] = {"notes.md": corpus_storage.fingerprint_file(src)}
    corpus_storage.save_meta(root, meta)
    assert corpus_storage.compute_stale(root, meta) is False
    src.write_text("hello world changed", encoding="utf-8")
    assert corpus_storage.compute_stale(root) is True


def test_chunk_ids_stable_and_retrieve_caps(tmp_path: Path) -> None:
    mini = Path(__file__).parent / "fixtures" / "learn" / "mini_book.md"
    ctx = CapabilityContext(
        instance_id="default",
        course_id="c-corpus",
        data_root=str(tmp_path),
        user_request="index",
        attachments=[str(mini)],
        extra={"data_root": str(tmp_path)},
    )
    job = JobSpec(
        job_id="j1",
        job_type="learn_index_corpus",
        objective="index",
        inputs={},
        tools=[],
    )
    result = run_recipe("corpus.index_sources", ctx, job)
    assert result.ok, result.error
    root = corpus_storage.resolve_course_corpus_root(tmp_path, "default", "c-corpus")
    meta = corpus_storage.load_meta(root)
    assert meta["status"] == "complete"
    assert meta["index_backend"] == "keyword"
    assert int(meta["chunk_count"]) >= 1
    ids = sorted(p.stem for p in corpus_storage.chunks_dir(root).glob("c*.json"))
    assert ids[0] == "c0001"

    ret = run_capability(
        "corpus.retrieve",
        ctx,
        {
            "query": "secret mascot animal",
            "corpus_root": str(root),
            "top_k": 2,
            "max_chars": 400,
        },
    )
    assert ret.ok, ret.error
    chunks = ret.data.get("chunks") or []
    assert 1 <= len(chunks) <= 2
    blob = " ".join(str(c.get("text") or "") for c in chunks)
    assert "LACERTA_PLANTED_FACT_QUOKKA" in blob
    total = sum(len(str(c.get("text") or "")) for c in chunks)
    assert total <= 400 or len(chunks) == 1


def test_keyword_backend_default(tmp_path: Path) -> None:
    src = tmp_path / "note.md"
    src.write_text("# Title\n\nalpha beta gamma planted_token_xyz\n", encoding="utf-8")
    ctx = CapabilityContext(
        instance_id="default",
        course_id="kw",
        data_root=str(tmp_path),
        attachments=[str(src)],
        extra={"data_root": str(tmp_path)},
    )
    job = JobSpec(job_id="k1", job_type="learn_index_corpus", objective="i", inputs={}, tools=[])
    assert run_recipe("corpus.index_sources", ctx, job).ok
    root = corpus_storage.resolve_course_corpus_root(tmp_path, "default", "kw")
    meta = corpus_storage.load_meta(root)
    assert meta["index_backend"] == "keyword"
    assert meta["status"] == "complete"
    assert corpus_storage.keyword_index_path(root).is_file()
    ret = run_capability(
        "corpus.retrieve",
        ctx,
        {"query": "planted_token_xyz", "corpus_root": str(root), "top_k": 1},
    )
    assert ret.ok
    assert "planted_token_xyz" in str((ret.data.get("chunks") or [{}])[0].get("text"))


def test_stem_structured_retrieve_planted_tokens(tmp_path: Path) -> None:
    mini = Path(__file__).parent / "fixtures" / "learn" / "mini_stem.md"
    ctx = CapabilityContext(
        instance_id="default",
        course_id="c-stem",
        data_root=str(tmp_path),
        user_request="index",
        attachments=[str(mini)],
        extra={"data_root": str(tmp_path)},
    )
    job = JobSpec(
        job_id="j-stem",
        job_type="learn_index_corpus",
        objective="index",
        inputs={},
        tools=[],
    )
    result = run_recipe("corpus.index_sources", ctx, job)
    assert result.ok, result.error
    root = corpus_storage.resolve_course_corpus_root(tmp_path, "default", "c-stem")
    kinds = {
        (corpus_storage.read_json(p) or {}).get("kind")
        for p in corpus_storage.chunks_dir(root).glob("c*.json")
    }
    assert kinds & {"table", "math", "figure"}

    table_ret = run_capability(
        "corpus.retrieve",
        ctx,
        {
            "query": "planted cell reference values Quantity",
            "corpus_root": str(root),
            "top_k": 3,
            "max_chars": 4000,
        },
    )
    assert table_ret.ok, table_ret.error
    table_blob = " ".join(str(c.get("text") or "") for c in (table_ret.data.get("chunks") or []))
    assert "LACERTA_TABLE_CELL_42" in table_blob

    math_ret = run_capability(
        "corpus.retrieve",
        ctx,
        {
            "query": "equation identity LACERTA_MATH_TOKEN",
            "corpus_root": str(root),
            "top_k": 3,
            "max_chars": 4000,
        },
    )
    assert math_ret.ok, math_ret.error
    math_blob = " ".join(str(c.get("text") or "") for c in (math_ret.data.get("chunks") or []))
    assert "LACERTA_MATH_TOKEN_π" in math_blob
    assert any(c.get("kind") for c in (math_ret.data.get("chunks") or []))
