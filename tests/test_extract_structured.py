"""Structured extract surrogates (V2.35) — tables, math, figures."""

from __future__ import annotations

from pathlib import Path

from lacerta.storage.extract import extract_text
from lacerta.storage.extract_structured import (
    MAX_TABLE_CHARS,
    describe_figure,
    enrich_prose,
    infer_chunk_kind,
    truncate_table_body,
    wrap_table,
)


FIXTURES = Path(__file__).parent / "fixtures" / "learn"


def test_extract_mini_stem_markers_and_tokens() -> None:
    text = extract_text(FIXTURES / "mini_stem.md")
    assert "[table]" in text and "[/table]" in text
    assert "LACERTA_TABLE_CELL_42" in text
    assert "[math]" in text and "[/math]" in text
    assert "LACERTA_MATH_TOKEN_π" in text
    assert "[figure]" in text
    assert "Oscilloscope" in text or "damped" in text.lower()
    assert "description:" in text or "unreadable" in text


def test_html_table_and_figure(tmp_path: Path) -> None:
    html = tmp_path / "stem.html"
    html.write_text(
        """
        <html><body>
        <p>Intro</p>
        <table>
          <tr><th>A</th><th>B</th></tr>
          <tr><td>LACERTA_HTML_TABLE_9</td><td>2</td></tr>
        </table>
        <figure>
          <img alt="Circuit schematic" src="c.png"/>
          <figcaption>Lab circuit</figcaption>
        </figure>
        <p>$E=mc^2$</p>
        </body></html>
        """,
        encoding="utf-8",
    )
    text = extract_text(html)
    assert "[table]" in text
    assert "LACERTA_HTML_TABLE_9" in text
    assert "[figure]" in text
    assert "Circuit schematic" in text or "Lab circuit" in text
    assert "[math]" in text
    assert "E=mc^2" in text.replace(" ", "")


def test_csv_wrapped_as_table(tmp_path: Path) -> None:
    csv_path = tmp_path / "vals.csv"
    csv_path.write_text("name,value\nalpha,1\nbeta,2\n", encoding="utf-8")
    text = extract_text(csv_path)
    assert text.startswith("[table]") or "\n[table]\n" in f"\n{text}"
    assert "[table]" in text and "[/table]" in text
    assert "alpha" in text and "beta" in text


def test_table_cap_truncates() -> None:
    huge = "x" * (MAX_TABLE_CHARS + 500)
    wrapped = wrap_table(huge)
    assert "…" in wrapped
    assert len(truncate_table_body(huge)) <= MAX_TABLE_CHARS


def test_figure_stub_no_network() -> None:
    s = describe_figure(caption="plot")
    assert "[figure]" in s
    assert "unreadable" in s
    assert "plot" in s
    empty = describe_figure(caption="")
    assert "unreadable" in empty


def test_infer_chunk_kind() -> None:
    assert infer_chunk_kind(wrap_table("| a | b |\n| --- | --- |\n| 1 | 2 |")) == "table"
    assert infer_chunk_kind("[math]\n$x=1$\n[/math]") == "math"
    assert infer_chunk_kind(describe_figure(caption="wave")) == "figure"
    assert infer_chunk_kind("plain prose about agents") == "prose"


def test_enrich_preserves_tex() -> None:
    out = enrich_prose("See $$a^2+b^2=c^2$$ on the board.")
    assert "[math]" in out
    assert "a^2+b^2=c^2" in out
