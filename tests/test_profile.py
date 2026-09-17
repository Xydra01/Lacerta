"""Lite vs full host profile. Feature paths do not change."""

from __future__ import annotations

from lacerta.core.profile import (
    default_num_ctx,
    default_tool_output_chars,
    default_write_chars,
    is_lite,
    profile_name,
)


def test_full_is_default(monkeypatch) -> None:
    monkeypatch.delenv("LACERTA_PROFILE", raising=False)
    assert profile_name() == "full"
    assert is_lite() is False
    assert default_num_ctx() == 32768
    assert default_write_chars() == 8000
    assert default_tool_output_chars() == 6000


def test_lite_and_macos_alias(monkeypatch) -> None:
    monkeypatch.setenv("LACERTA_PROFILE", "lite")
    assert profile_name() == "lite"
    assert is_lite() is True
    assert default_num_ctx() == 8192
    assert default_write_chars() == 6000
    assert default_tool_output_chars() == 4000
    monkeypatch.setenv("LACERTA_PROFILE", "macos")
    assert profile_name() == "lite"
    assert default_num_ctx() == 8192
