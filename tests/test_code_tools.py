from __future__ import annotations

import os
from pathlib import Path

import pytest

from lacerta.workers import code_tools as ct


@pytest.fixture()
def project_root(tmp_path: Path):
    ct.set_project_root(tmp_path)
    yield tmp_path
    ct.set_project_root(None)


def test_write_and_read_file(project_root: Path) -> None:
    msg = ct.write_file("hello.py", "print('hi')")
    assert msg.startswith("✅")
    assert (project_root / "hello.py").read_text(encoding="utf-8").endswith("\n")
    body = ct.read_file("hello.py")
    assert "1|print('hi')" in body


def test_write_cap(project_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LACERTA_MAX_WRITE_CHARS", "10")
    msg = ct.write_file("big.txt", "x" * 20)
    assert "OS BLOCK" in msg
    assert not (project_root / "big.txt").exists()


def test_path_escape_blocked(project_root: Path) -> None:
    msg = ct.write_file("../outside.txt", "nope")
    # resolve_under_root may land outside → blocked
    assert "outside" in msg.lower() or "Cannot write" in msg or "OS BLOCK" in msg
    assert not (project_root.parent / "outside.txt").exists() or "Cannot write" in msg


def test_search_replace_uniqueness(project_root: Path) -> None:
    ct.write_file("a.txt", "foo\nfoo\n")
    msg = ct.search_replace("a.txt", "foo", "bar")
    assert "matched 2 times" in msg
    ct.write_file("b.txt", "only once foo here\n")
    msg2 = ct.search_replace("b.txt", "foo", "bar")
    assert msg2.startswith("✅")
    assert "bar" in (project_root / "b.txt").read_text(encoding="utf-8")


def test_grep_shape(project_root: Path) -> None:
    ct.write_file("pkg/mod.py", "alpha\nbeta HARNESS_OK\n")
    out = ct.grep("HARNESS_OK")
    assert out.startswith("[OK]")
    assert "pkg/mod.py:2:" in out.replace("\\", "/")
    assert "HARNESS_OK" in out


def test_no_root_blocks() -> None:
    ct.set_project_root(None)
    assert "No project root" in ct.write_file("x.py", "y")


def test_get_active_tools() -> None:
    assert "write_file" in ct.get_active_tools(None)
    active = ct.get_active_tools(["write_file", "nope"])
    assert active == frozenset({"write_file"})
