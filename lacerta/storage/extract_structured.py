"""Structured extract surrogates for tables, math, and figures (V2.35).

Emits text-only markers into chunk bodies. Never stores image/PDF bytes in the
manager. Optional local describe is stubbed; MAX_DESCRIBE_CALLS defaults to 0.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any

MAX_TABLE_CHARS = 4000
MAX_FIGURES_PER_DOC = 20
MAX_DESCRIBE_CALLS = 0  # stub only; multimodal describe not required for exit

TABLE_OPEN = "[table]"
TABLE_CLOSE = "[/table]"
MATH_OPEN = "[math]"
MATH_CLOSE = "[/math]"

_PIPE_ROW = re.compile(r"^\s*\|.+\|\s*$")
_PIPE_SEP = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$")
_MD_IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_TEX_INLINE = re.compile(r"\$\$[^$]+\$\$|\$[^$\n]+\$")
_MATH_CHARS = set("=+-*/^_<>≤≥≈≠∑∫√∞παβγδθλμσφωΩΔΣΠ()[]{}|\\")


def truncate_table_body(body: str, *, max_chars: int = MAX_TABLE_CHARS) -> str:
    body = body.strip()
    if len(body) <= max_chars:
        return body
    return body[: max(0, max_chars - 1)].rstrip() + "…"


def wrap_table(body: str, *, max_chars: int = MAX_TABLE_CHARS) -> str:
    body = truncate_table_body(body, max_chars=max_chars)
    if not body:
        return "[table: extract failed]"
    return f"{TABLE_OPEN}\n{body}\n{TABLE_CLOSE}"


def wrap_math(body: str) -> str:
    body = body.strip()
    if not body:
        return f"{MATH_OPEN}\n{MATH_CLOSE}"
    if body.startswith(MATH_OPEN):
        return body
    return f"{MATH_OPEN}\n{body}\n{MATH_CLOSE}"


def describe_figure(
    *,
    caption: str = "",
    image_bytes: bytes | None = None,
    describe_budget: list[int] | None = None,
) -> str:
    """Return a figure surrogate. Never calls cloud APIs.

    ``describe_budget`` is a mutable ``[remaining]`` counter when callers want
    to spend optional local describe slots (default budget is 0 → stub only).
    ``image_bytes`` is accepted but not retained or uploaded.
    """
    _ = image_bytes  # intentionally unused — no manager-held binary path
    cap = (caption or "").strip() or "(none)"
    remaining = MAX_DESCRIBE_CALLS
    if describe_budget is not None:
        remaining = describe_budget[0]
    if remaining > 0 and describe_budget is not None:
        describe_budget[0] = remaining - 1
        # Future: local multimodal describe. Exit criteria use stub only.
        desc = "unreadable — no local describe"
    else:
        desc = "unreadable — no local describe"
    if not (caption or "").strip():
        return f"[figure: unreadable — caption: {cap}]"
    return f"[figure] caption: {cap}; description: {desc}"


def figure_surrogate(caption: str = "", *, description: str | None = None) -> str:
    if description is None:
        return describe_figure(caption=caption)
    cap = (caption or "").strip() or "(none)"
    return f"[figure] caption: {cap}; description: {description}"


def _is_dense_math_line(line: str) -> bool:
    s = line.strip()
    if len(s) < 3 or len(s) > 200:
        return False
    if s.startswith(("#", TABLE_OPEN, MATH_OPEN, "[figure", "[", "http")):
        return False
    if _TEX_INLINE.search(s):
        return True
    letters = sum(1 for c in s if c.isalpha())
    mathish = sum(1 for c in s if c in _MATH_CHARS or c.isdigit())
    if letters + mathish < 4:
        return False
    # Dense if math/digit chars dominate letters
    return mathish >= max(3, letters) and mathish / max(1, len(s)) >= 0.35


def _looks_like_table_line(line: str) -> bool:
    s = line.rstrip()
    if not s.strip():
        return False
    if "|" in s and s.count("|") >= 2:
        return True
    # Multi-column via 2+ spaces / tabs
    if "\t" in s and len(s.split("\t")) >= 2:
        return True
    if re.search(r"\S  +\S.*\S  +\S", s):
        return True
    return False


def _rows_to_markdown(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    norm = [r + [""] * (width - len(r)) for r in rows]
    lines = ["| " + " | ".join(c.strip() or " " for c in row) + " |" for row in norm]
    if len(lines) >= 1:
        sep = "| " + " | ".join("---" for _ in range(width)) + " |"
        lines.insert(1, sep)
    return "\n".join(lines)


def enrich_prose(text: str, *, max_figures: int = MAX_FIGURES_PER_DOC) -> str:
    """Post-process markdown/plain/PDF page text with table/math/figure markers."""
    text = text.replace("\r\n", "\n")
    # Markdown images → figure surrogates (cap)
    fig_count = 0

    def _img_repl(m: re.Match[str]) -> str:
        nonlocal fig_count
        if fig_count >= max_figures:
            return m.group(0)
        fig_count += 1
        return describe_figure(caption=m.group(1).strip())

    text = _MD_IMAGE.sub(_img_repl, text)

    lines = text.split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Already wrapped
        if line.strip() == TABLE_OPEN:
            out.append(line)
            i += 1
            while i < len(lines) and lines[i].strip() != TABLE_CLOSE:
                out.append(lines[i])
                i += 1
            if i < len(lines):
                out.append(lines[i])
                i += 1
            continue
        if line.strip() == MATH_OPEN:
            out.append(line)
            i += 1
            while i < len(lines) and lines[i].strip() != MATH_CLOSE:
                out.append(lines[i])
                i += 1
            if i < len(lines):
                out.append(lines[i])
                i += 1
            continue

        # Pipe markdown table block
        if _PIPE_ROW.match(line):
            block = [line]
            j = i + 1
            while j < len(lines) and (
                _PIPE_ROW.match(lines[j]) or _PIPE_SEP.match(lines[j])
            ):
                block.append(lines[j])
                j += 1
            if len(block) >= 2 or (len(block) == 1 and block[0].count("|") >= 3):
                body = "\n".join(block)
                out.append(wrap_table(body))
                i = j
                continue

        # Consecutive multi-column heuristic lines → table
        if _looks_like_table_line(line) and "|" not in line:
            block = [line]
            j = i + 1
            while j < len(lines) and _looks_like_table_line(lines[j]):
                block.append(lines[j])
                j += 1
            if len(block) >= 2:
                rows = []
                for bl in block:
                    if "\t" in bl:
                        rows.append([c.strip() for c in bl.split("\t")])
                    else:
                        rows.append(re.split(r"\s{2,}", bl.strip()))
                out.append(wrap_table(_rows_to_markdown(rows)))
                i = j
                continue

        # Math: preserve TeX; tag dense formula lines
        stripped = line.strip()
        if stripped.startswith("[figure"):
            out.append(line)
            i += 1
            continue
        if _TEX_INLINE.search(line) or _is_dense_math_line(line):
            # Don't double-wrap if already inside markers on same line
            if MATH_OPEN not in line:
                out.append(wrap_math(line.strip()))
            else:
                out.append(line)
            i += 1
            continue

        out.append(line)
        i += 1

    body = "\n".join(out)
    return re.sub(r"\n{3,}", "\n\n", body).strip()


class _HTMLStructured(HTMLParser):
    """HTML → prose + [table] / [figure] surrogates."""

    def __init__(self, *, max_figures: int = MAX_FIGURES_PER_DOC) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip = 0
        self._in_table = False
        self._table_rows: list[list[str]] = []
        self._row: list[str] = []
        self._cell: list[str] = []
        self._in_cell = False
        self._in_caption = False
        self._caption: list[str] = []
        self._fig_count = 0
        self._max_figures = max_figures
        self._in_fig = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        ad = {k: (v or "") for k, v in attrs}
        if tag in ("script", "style"):
            self._skip += 1
            return
        if self._skip:
            return
        if tag == "table":
            self._in_table = True
            self._table_rows = []
            return
        if self._in_table:
            if tag == "tr":
                self._row = []
            elif tag in ("td", "th"):
                self._in_cell = True
                self._cell = []
            return
        if tag == "figure":
            self._in_fig = True
            self._caption = []
            return
        if tag == "figcaption":
            self._in_caption = True
            self._caption = []
            return
        if tag == "img":
            if self._fig_count < self._max_figures:
                self._fig_count += 1
                alt = ad.get("alt") or ad.get("title") or ""
                if self._in_fig and self._caption:
                    alt = alt or " ".join(self._caption).strip()
                self._parts.append("\n" + describe_figure(caption=alt) + "\n")
            return
        if tag in ("p", "div", "br", "li", "h1", "h2", "h3"):
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style") and self._skip:
            self._skip -= 1
            return
        if self._skip:
            return
        if self._in_table:
            if tag in ("td", "th") and self._in_cell:
                self._row.append("".join(self._cell).strip())
                self._in_cell = False
                self._cell = []
            elif tag == "tr":
                if self._row:
                    self._table_rows.append(self._row)
                self._row = []
            elif tag == "table":
                self._in_table = False
                md = _rows_to_markdown(self._table_rows)
                self._parts.append("\n" + wrap_table(md) + "\n")
                self._table_rows = []
            return
        if tag == "figcaption":
            self._in_caption = False
            return
        if tag == "figure":
            # If figure had caption but no img handled, still emit slot
            if self._caption and self._fig_count < self._max_figures:
                # Only if we didn't already emit via img — check last part
                cap = " ".join(self._caption).strip()
                last = self._parts[-1] if self._parts else ""
                if "[figure" not in last and cap:
                    self._fig_count += 1
                    self._parts.append("\n" + describe_figure(caption=cap) + "\n")
            self._in_fig = False
            self._caption = []
            return
        if tag in ("p", "div", "li", "h1", "h2", "h3"):
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        if self._in_cell:
            self._cell.append(data)
            return
        if self._in_caption:
            self._caption.append(data.strip())
            return
        if self._in_table:
            return
        text = data.strip()
        if text:
            self._parts.append(text + " ")

    def text(self) -> str:
        raw = "".join(self._parts)
        raw = re.sub(r"[ \t]+\n", "\n", re.sub(r"\n{3,}", "\n\n", raw)).strip()
        return enrich_prose(raw, max_figures=max(0, self._max_figures - self._fig_count))


def extract_html_structured(html: str, *, max_figures: int = MAX_FIGURES_PER_DOC) -> str:
    parser = _HTMLStructured(max_figures=max_figures)
    parser.feed(html)
    parser.close()
    return parser.text()


def extract_csv_structured(rows: list[list[str]]) -> str:
    if not rows:
        return "[table: extract failed]"
    lines = [" | ".join(cell.strip() for cell in row if str(cell).strip()) for row in rows]
    body = "\n".join(r for r in lines if r)
    return wrap_table(body)


def extract_docx_parts(document: Any, *, max_figures: int = MAX_FIGURES_PER_DOC) -> str:
    """Build structured text from a python-docx Document."""
    parts: list[str] = []
    fig_budget = max_figures
    for para in document.paragraphs:
        text = (para.text or "").strip()
        if text:
            parts.append(text)
        # Inline shapes / drawings — emit placeholder when we can name them
        try:
            blips = para._element.findall(
                ".//{http://schemas.openxmlformats.org/drawingml/2006/main}blip"
            )
        except Exception:
            blips = []
        for _ in blips:
            if fig_budget <= 0:
                break
            fig_budget -= 1
            parts.append(describe_figure(caption="(embedded image)"))

    for table in document.tables:
        rows: list[list[str]] = []
        try:
            for row in table.rows:
                cells = [c.text.strip() for c in row.cells]
                rows.append(cells)
            parts.append(wrap_table(_rows_to_markdown(rows)))
        except Exception:
            parts.append("[table: extract failed]")

    body = "\n\n".join(parts).strip()
    return enrich_prose(body, max_figures=fig_budget)


def extract_pdf_page_structured(
    page_text: str,
    *,
    page_index: int,
    image_count: int = 0,
    max_figures_remaining: list[int] | None = None,
) -> str:
    """Enrich one PDF page's text layer and optional image slots."""
    enriched = enrich_prose(page_text)
    figs: list[str] = []
    remaining = MAX_FIGURES_PER_DOC if max_figures_remaining is None else max_figures_remaining[0]
    for n in range(image_count):
        if remaining <= 0:
            break
        remaining -= 1
        figs.append(
            describe_figure(caption=f"page {page_index} image {n + 1}")
        )
    if max_figures_remaining is not None:
        max_figures_remaining[0] = remaining
    if figs:
        enriched = (enriched + "\n\n" + "\n\n".join(figs)).strip()
    return enriched


def infer_chunk_kind(text: str) -> str:
    """Return prose | table | math | figure from chunk body markers."""
    t = text.strip()
    if not t:
        return "prose"
    # Dominated by a single marker type
    has_table = TABLE_OPEN in t
    has_math = MATH_OPEN in t
    has_fig = "[figure" in t
    kinds = sum([has_table, has_math, has_fig])
    if kinds == 1:
        if has_table:
            # Prefer table if most of the content is the wrapped block
            start = t.find(TABLE_OPEN)
            end = t.find(TABLE_CLOSE)
            if start >= 0 and end > start:
                inner = end + len(TABLE_CLOSE) - start
                if inner >= len(t) * 0.5:
                    return "table"
            return "table" if t.startswith(TABLE_OPEN) or t.count("\n") < 8 else "prose"
        if has_math:
            start = t.find(MATH_OPEN)
            end = t.find(MATH_CLOSE)
            if start >= 0 and end > start:
                inner = end + len(MATH_CLOSE) - start
                if inner >= len(t) * 0.4 or t.startswith(MATH_OPEN):
                    return "math"
            return "math" if len(t) < 400 else "prose"
        if has_fig:
            # Single figure line or figure-dominated
            if t.startswith("[figure") or t.count("[figure") == 1 and len(t) < 500:
                return "figure"
    if has_table and not has_math and not has_fig:
        return "table"
    if has_math and not has_table and not has_fig:
        return "math"
    if has_fig and not has_table and not has_math:
        return "figure"
    return "prose"


def prefer_marker_boundary(text: str, start: int, end: int, target: int) -> int:
    """Adjust soft-split end to avoid cutting inside [table]/[math] when possible."""
    window = text[start:end]
    for open_m, close_m in ((TABLE_OPEN, TABLE_CLOSE), (MATH_OPEN, MATH_CLOSE)):
        # If we open a marker without closing in this window, try to extend to close
        last_open = window.rfind(open_m)
        last_close = window.rfind(close_m)
        if last_open > last_close:
            # Look for close after end
            close_at = text.find(close_m, end)
            if close_at != -1:
                candidate = close_at + len(close_m)
                # Only extend if not huge
                if candidate - start <= target * 3:
                    return candidate
            # Else try to break before the open
            abs_open = start + last_open
            if abs_open - start > target // 3:
                return abs_open
    return end
