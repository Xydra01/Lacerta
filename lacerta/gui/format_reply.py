"""Escape-first reply formatting for the GUI Replies panel (V3.1).

Produces HTML the browser may insert. Never interpolates raw model text.
Math is wrapped for local temml; this module does not render TeX itself.
"""

from __future__ import annotations

import html
import re

_FENCE = re.compile(r"```(?:[^\n`]*)\n(.*?)```", re.DOTALL)
_INLINE_CODE = re.compile(r"`([^`\n]+)`")
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_STAR = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")
_ITALIC_UNDER = re.compile(r"(?<!_)_(?!_)(.+?)(?<!_)_(?!_)")
_DISPLAY_MATH = re.compile(r"\$\$(.+?)\$\$", re.DOTALL)
_INLINE_MATH = re.compile(r"(?<!\$)\$(?!\$)([^$\n]+?)\$(?!\$)")


def closed_prefix(text: str) -> tuple[str, str]:
    """Split text into a closed prefix and an open tail.

    Finished `**`, `*` / `_`, `$` / `$$`, and fenced code are closed.
    An unclosed opener and everything after it stay in the tail.
    Plain text before that opener is safe (including a partial last line).
    """
    if not text:
        return "", ""
    i = 0
    n = len(text)
    safe_end = 0
    while i < n:
        if text.startswith("```", i):
            end = text.find("```", i + 3)
            if end == -1:
                return text[:safe_end], text[safe_end:]
            i = end + 3
            safe_end = i
            continue
        if text.startswith("$$", i):
            end = text.find("$$", i + 2)
            if end == -1:
                return text[:safe_end], text[safe_end:]
            i = end + 2
            safe_end = i
            continue
        if text[i] == "$":
            end = text.find("$", i + 1)
            if end == -1 or "\n" in text[i + 1 : end]:
                return text[:safe_end], text[safe_end:]
            i = end + 1
            safe_end = i
            continue
        if text.startswith("**", i):
            end = text.find("**", i + 2)
            if end == -1:
                return text[:safe_end], text[safe_end:]
            i = end + 2
            safe_end = i
            continue
        if text[i] in "*_":
            closer = text[i]
            end = text.find(closer, i + 1)
            if end == -1:
                return text[:safe_end], text[safe_end:]
            i = end + 1
            safe_end = i
            continue
        i += 1
        safe_end = i
    return text, ""


def _math_span(tex: str, *, display: bool) -> str:
    kind = "math-display" if display else "math-inline"
    esc = html.escape(tex.strip(), quote=True)
    return f'<span class="{kind}" data-tex="{esc}">{esc}</span>'


def _apply_markup(raw: str) -> str:
    """Style a closed prefix. Every model character is escaped before it enters HTML."""
    placeholders: list[str] = []

    def _hold(html_chunk: str) -> str:
        placeholders.append(html_chunk)
        return f"\x00PH{len(placeholders) - 1}\x00"

    def _fence(match: re.Match[str]) -> str:
        body = html.escape(match.group(1), quote=True)
        return _hold(f"<pre><code>{body}</code></pre>")

    def _code(match: re.Match[str]) -> str:
        return _hold(f"<code>{html.escape(match.group(1), quote=True)}</code>")

    out = _FENCE.sub(_fence, raw)
    out = _INLINE_CODE.sub(_code, out)
    out = _DISPLAY_MATH.sub(lambda m: _hold(_math_span(m.group(1), display=True)), out)
    out = _INLINE_MATH.sub(lambda m: _hold(_math_span(m.group(1), display=False)), out)

    parts = re.split(r"(\x00PH\d+\x00)", out)
    escaped: list[str] = []
    for part in parts:
        if part.startswith("\x00PH"):
            escaped.append(part)
        else:
            escaped.append(html.escape(part, quote=True))
    out = "".join(escaped)
    out = _BOLD.sub(r"<strong>\1</strong>", out)
    out = _ITALIC_STAR.sub(r"<em>\1</em>", out)
    out = _ITALIC_UNDER.sub(r"<em>\1</em>", out)
    out = out.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>\n")

    def _restore(match: re.Match[str]) -> str:
        return placeholders[int(match.group(1))]

    return re.sub(r"\x00PH(\d+)\x00", _restore, out)


def render_html(text: str, *, hide_unclosed_math: bool = False) -> str:
    """Escape, style the closed prefix, and leave an open tail unstyled.

    When hide_unclosed_math is set, a tail that starts with `$` is omitted
    so in-flight polls never typeset half-written math.
    """
    raw = text or ""
    # Literal backslash-n from some model strings, not already-decoded newlines.
    raw = raw.replace("\\n", "\n")
    safe, tail = closed_prefix(raw)
    parts: list[str] = []
    if safe:
        parts.append(_apply_markup(safe))
    if tail and not (hide_unclosed_math and tail.lstrip().startswith("$")):
        parts.append(html.escape(tail, quote=True).replace("\n", "<br>\n"))
    return "".join(parts)
