---
name: office-documents
description: "Create, read, edit Office docs: .docx, .xlsx, .pdf, .pptx + OCR/document extraction."
version: 1.0.0
author: Nous Research
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [word, docx, excel, xlsx, pdf, powerpoint, pptx, office, documents, ocr, spreadsheets, presentations]
    category: productivity
    related_skills: [action-items]
---

# Office Documents

Create, read, edit, and convert the four Office formats — Word (.docx),
Excel (.xlsx), PDF, PowerPoint (.pptx) — plus OCR/text extraction from
scanned documents. Each format keeps its own script CLI; read the matching
reference file before a task in that format.

Consolidates the former `docx`, `xlsx`, `pdf`, `powerpoint`, and
`ocr-and-documents` skills (archived under `.archive/productivity/`).

## When to Use

- Generate or edit a Word document → `references/docx.md`.
- Build/read/edit an Excel workbook or CSV → `references/xlsx.md`.
- Create, merge, fill, OCR, or edit a PDF → `references/pdf.md`.
- Build/read/edit a PowerPoint deck → `references/powerpoint.md`.
- Extract text from a PDF/scan, or process Arxiv papers → `references/ocr-and-documents.md`.

## Format → Reference + Script Prefix

| Format | Reference | Script prefix | Deps |
|---|---|---|---|
| Word .docx | `references/docx.md` | `scripts/docx_*.py` | python-docx |
| Excel .xlsx | `references/xlsx.md` | `scripts/xlsx_*.py`, `csv_to_xlsx.py` | openpyxl |
| PDF | `references/pdf.md` | `scripts/pdf_*.py` | pypdf, reportlab, pdfplumber |
| PowerPoint .pptx | `references/powerpoint.md` | `scripts/pptx_*.py` | python-pptx |
| OCR / extraction | `references/ocr-and-documents.md` | `scripts/ocr/*.py` | pymupdf, marker-pdf |

All scripts are argparse CLIs: run with `terminal`, every one supports
`--help`, prints JSON to stdout, exits non-zero on failure.

## Cross-format notes

- Convert .docx/.xlsx/.pptx → PDF via LibreOffice: `soffice --headless --convert-to pdf f.docx`.
- Legacy formats (.doc/.xls/.ppt) are NOT handled natively — convert first with LibreOffice.
- PDF text extraction for text-based PDFs uses pymupdf; scanned/OCR needs marker-pdf (see `references/ocr-and-documents.md` for the pymupdf-vs-marker decision table).

## References

- `references/docx.md`, `references/xlsx.md`, `references/pdf.md`, `references/powerpoint.md` — per-format guides.
- `references/ocr-and-documents.md` — OCR/scanned-document extraction + Arxiv + nano-pdf editing.
- `references/revisions-and-comments.md` (docx), `references/restructuring.md` (xlsx), `references/forms.md` / `references/nano-pdf-editing.md` / `references/ocr-extraction.md` (pdf) — deep dives.
