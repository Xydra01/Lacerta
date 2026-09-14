from __future__ import annotations

import os
from pathlib import Path

from lacerta.core.envload import find_dotenv, load_dotenv


def test_load_dotenv_sets_missing_keys(tmp_path: Path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# comment\n"
        "OLLAMA_MODEL=lacerta:latest\n"
        "export OLLAMA_NUM_CTX=8192\n"
        "QUOTED='hello world'\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    monkeypatch.delenv("OLLAMA_NUM_CTX", raising=False)
    monkeypatch.delenv("QUOTED", raising=False)
    monkeypatch.setenv("ALREADY", "keep-me")

    loaded = load_dotenv(env_file)
    assert loaded == env_file.resolve()
    assert os.environ["OLLAMA_MODEL"] == "lacerta:latest"
    assert os.environ["OLLAMA_NUM_CTX"] == "8192"
    assert os.environ["QUOTED"] == "hello world"


def test_load_dotenv_does_not_override_by_default(tmp_path: Path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("OLLAMA_MODEL=from-file\n", encoding="utf-8")
    monkeypatch.setenv("OLLAMA_MODEL", "from-shell")
    load_dotenv(env_file)
    assert os.environ["OLLAMA_MODEL"] == "from-shell"
    load_dotenv(env_file, override=True)
    assert os.environ["OLLAMA_MODEL"] == "from-file"


def test_find_dotenv_walks_parents(tmp_path: Path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("X=1\n", encoding="utf-8")
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)
    found = find_dotenv()
    assert found == env_file.resolve()
