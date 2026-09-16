# Phase V1.55 — Document extract (PDF / DOCX / HTML)

**Status:** done  
**Depends on:** V1.35 (corpus), V1.4 (research/writing ingest)  
**Exit:** Attachments in `.pdf` / `.docx` / `.html` / `.csv` extract to text for corpus index and research/writing/learn ingest; missing optional deps fail honestly  

---

## Goal

Stop treating non-markdown uploads as raw UTF-8 bytes. One shared extractor normalizes user files to text before notes / `corpus/sources/`.

---

## Checkboxes

- [x] Shared `lacerta/storage/extract.py`: `.md/.txt/.markdown`, `.html/.htm`, `.csv/.tsv` (stdlib); `.pdf` (pypdf); `.docx` (python-docx)
- [x] Legacy `.doc` honest reject (convert to `.docx`)
- [x] Corpus `extract` writes normalized `.md` under `sources/` (chunk/index unchanged)
- [x] Research / writing / learn ingest use the same helper
- [x] Optional extra: `pip install 'lacerta[extract]'` (also in `[dev]`)
- [x] Unit tests for HTML/plain + PDF/DOCX when deps present

## Tests

```bash
pip install -e ".[dev]"
pytest tests/test_extract.py tests/ -q -k corpus
```

## Out of scope

OCR for scanned PDFs, `.pptx`/`.xlsx`, paywall scrape, embedding cloud APIs.
