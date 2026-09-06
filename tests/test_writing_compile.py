"""Compile rules for writing drafts."""

from __future__ import annotations

from lacerta.workers.writing.storage import compile_markdown


def test_compile_one_h1_and_h2_sections() -> None:
    md = compile_markdown(
        {
            "title": "My Doc",
            "sections": [
                {"header": "First", "body": "Alpha paragraph."},
                {"header": "Second", "body": "Beta paragraph."},
            ],
        }
    )
    lines = md.splitlines()
    h1 = [ln for ln in lines if ln.startswith("# ") and not ln.startswith("## ")]
    h2 = [ln for ln in lines if ln.startswith("## ")]
    assert h1 == ["# My Doc"]
    assert h2 == ["## First", "## Second"]
    assert "Alpha paragraph." in md
    assert "Beta paragraph." in md


def test_compile_strips_heading_marks_from_bodies() -> None:
    md = compile_markdown(
        {
            "title": "# Already Marked",
            "sections": [
                {"header": "## Nested", "body": "# Bad title\n## also bad\nBody text."},
            ],
        }
    )
    lines = md.splitlines()
    h1 = [ln for ln in lines if ln.startswith("# ") and not ln.startswith("## ")]
    assert h1 == ["# Already Marked"]
    assert "## Nested" in md
    assert not any(ln == "# Bad title" for ln in lines)
    assert "Body text." in md
