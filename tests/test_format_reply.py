"""Reply formatter: escape-first markdown and closed-prefix split."""

from __future__ import annotations

from lacerta.gui.format_reply import closed_prefix, render_html


def test_bold_italic_newline_and_script_escape() -> None:
    html = render_html("**bold** and *italic* and _also_\n<script>alert(1)</script>")
    assert "<strong>bold</strong>" in html
    assert "<em>italic</em>" in html
    assert "<em>also</em>" in html
    assert "<br>" in html
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_closed_prefix_hides_unclosed_math_and_bold() -> None:
    safe, tail = closed_prefix("done $E=mc")
    assert "$" not in safe
    assert tail.startswith("$")
    rendered = render_html("done $E=mc")
    assert "math-inline" not in rendered
    assert "$E=mc" in rendered

    safe_b, tail_b = closed_prefix("hello **bo")
    assert "**" not in safe_b
    assert tail_b.startswith("**")
    rendered_b = render_html("hello **bo")
    assert "<strong>" not in rendered_b
    assert "**bo" in rendered_b


def test_hide_unclosed_math_in_partial_html() -> None:
    shown = render_html("See $E=mc", hide_unclosed_math=True)
    assert "math-inline" not in shown
    assert "$" not in shown
    assert "See" in shown
    bold = render_html("hello **bo", hide_unclosed_math=True)
    assert "<strong>" not in bold
    assert "**bo" in bold
    finished = render_html("done $E=mc")
    assert "$E=mc" in finished


def test_finished_inline_math_becomes_span() -> None:
    html = render_html("Energy is $E=mc^2$ today.")
    assert 'class="math-inline"' in html
    assert 'data-tex="E=mc^2"' in html
    assert "$E=mc^2$" not in html
