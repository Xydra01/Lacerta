"""File → plain text extractors for ingest / corpus (V1.55 + V2.35 structured).

Plain text and HTML use the stdlib. PDF (pypdf) and DOCX (python-docx) need
`pip install 'lacerta[extract]'` (also pulled in by `[dev]`).

Structured surrogates ([table]/[math]/[figure]) are text-only; no manager-held
image bytes. See lacerta.storage.extract_structured.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Callable

from lacerta.storage.extract_structured import (
    enrich_prose,
    extract_csv_structured,
    extract_docx_parts,
    extract_html_structured,
    extract_pdf_page_structured,
)

# Always available (stdlib).
PLAIN_SUFFIXES = {".md", ".txt", ".markdown", ".csv", ".tsv", ".html", ".htm"}
# Optional libraries.
PDF_SUFFIXES = {".pdf"}
DOCX_SUFFIXES = {".docx"}
# .doc (legacy binary) is not supported — convert to .docx first.

SUPPORTED_SUFFIXES = PLAIN_SUFFIXES | PDF_SUFFIXES | DOCX_SUFFIXES


class ExtractError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def is_extractable(path: Path | str) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_SUFFIXES


def missing_optional_deps(path: Path | str) -> str | None:
    """Return install hint if suffix needs a missing optional package."""
    suffix = Path(path).suffix.lower()
    if suffix in PDF_SUFFIXES:
        try:
            import pypdf  # noqa: F401
        except ImportError:
            return "PDF requires pypdf — pip install 'lacerta[extract]'"
    if suffix in DOCX_SUFFIXES:
        try:
            import docx  # noqa: F401
        except ImportError:
            return "DOCX requires python-docx — pip install 'lacerta[extract]'"
    return None


def _extract_plain(path: Path) -> str:
    return enrich_prose(path.read_text(encoding="utf-8", errors="replace").strip())


def _extract_html(path: Path) -> str:
    return extract_html_structured(
        path.read_text(encoding="utf-8", errors="replace")
    )


def _extract_csv(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    dialect = csv.excel_tab if path.suffix.lower() == ".tsv" else csv.excel
    reader = csv.reader(io.StringIO(raw), dialect=dialect)
    rows = [list(row) for row in reader]
    return extract_csv_structured(rows)


def _pdf_page_image_count(page: object) -> int:
    """Best-effort image count without retaining bytes."""
    try:
        images = getattr(page, "images", None)
        if images is not None:
            return len(list(images))
    except Exception:
        pass
    try:
        resources = page.get("/Resources") if hasattr(page, "get") else None  # type: ignore[union-attr]
        if resources is None:
            return 0
        resolved = resources.get_object() if hasattr(resources, "get_object") else resources
        xobj = resolved.get("/XObject") if resolved is not None else None
        if xobj is None:
            return 0
        xobj = xobj.get_object() if hasattr(xobj, "get_object") else xobj
        count = 0
        for key in xobj:
            try:
                obj = xobj[key]
                obj = obj.get_object() if hasattr(obj, "get_object") else obj
                if obj.get("/Subtype") == "/Image":
                    count += 1
            except Exception:
                continue
        return count
    except Exception:
        return 0


def _extract_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise ExtractError(
            "missing_dep",
            "PDF requires pypdf — pip install 'lacerta[extract]'",
        ) from e
    from lacerta.storage.extract_structured import MAX_FIGURES_PER_DOC

    reader = PdfReader(str(path))
    parts: list[str] = []
    fig_remaining = [MAX_FIGURES_PER_DOC]
    for i, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        text = text.strip()
        img_n = _pdf_page_image_count(page)
        if text or img_n:
            body = extract_pdf_page_structured(
                text,
                page_index=i,
                image_count=img_n,
                max_figures_remaining=fig_remaining,
            )
            if body:
                parts.append(f"## Page {i}\n\n{body}")
            elif text:
                parts.append(f"## Page {i}\n\n{text}")
    body = "\n\n".join(parts).strip()
    if not body:
        raise ExtractError("empty_pdf", f"No extractable text in PDF {path.name}")
    return body


def _extract_docx(path: Path) -> str:
    try:
        import docx
    except ImportError as e:
        raise ExtractError(
            "missing_dep",
            "DOCX requires python-docx — pip install 'lacerta[extract]'",
        ) from e
    document = docx.Document(str(path))
    body = extract_docx_parts(document).strip()
    if not body:
        raise ExtractError("empty_docx", f"No extractable text in DOCX {path.name}")
    return body


_EXTRACTORS: dict[str, Callable[[Path], str]] = {
    ".md": _extract_plain,
    ".txt": _extract_plain,
    ".markdown": _extract_plain,
    ".html": _extract_html,
    ".htm": _extract_html,
    ".csv": _extract_csv,
    ".tsv": _extract_csv,
    ".pdf": _extract_pdf,
    ".docx": _extract_docx,
}


def extract_text(path: Path | str) -> str:
    """Return normalized plain text for an attachment. Raises ExtractError."""
    p = Path(path)
    if not p.is_file():
        raise ExtractError("missing_file", f"Not a file: {p}")
    suffix = p.suffix.lower()
    if suffix == ".doc":
        raise ExtractError(
            "unsupported_source",
            "Legacy .doc is not supported — save as .docx or export to .md/.txt",
        )
    handler = _EXTRACTORS.get(suffix)
    if handler is None:
        raise ExtractError(
            "unsupported_source",
            f"Unsupported source type {suffix!r} — use "
            f"{', '.join(sorted(SUPPORTED_SUFFIXES))}",
        )
    text = handler(p).strip()
    if not text:
        raise ExtractError("empty_extract", f"No text extracted from {p.name}")
    return text


def normalized_source_name(path: Path | str) -> str:
    """Stable .md name for corpus/sources after extract."""
    p = Path(path)
    stem = p.stem.strip() or "source"
    return f"{stem}.md"
