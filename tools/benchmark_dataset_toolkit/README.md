# Knowra Benchmark Dataset Toolkit

Developer utility for generating and validating **Apex National Bank** benchmark artefacts used to evaluate Knowra’s Knowledge Engine.

This toolkit is **not** part of the Knowra runtime (backend/frontend). It lives exclusively under:

```text
tools/benchmark_dataset_toolkit/
```

---

## Current capability

| Pipeline | Status |
|---|---|
| **Markdown → PDF** (Pandoc) | ✅ Implemented |
| Markdown → DOCX | 🔜 Planned |
| Scanned PDF generation | 🔜 Planned |
| OCR benchmark generation | 🔜 Planned |
| Image dataset generation | 🔜 Planned |
| Dataset validation / statistics | 🔜 Planned (PDF verification included) |

---

## Architecture

```text
tools/benchmark_dataset_toolkit/
├── convert_dataset.py          # CLI entry point
├── config.yaml                 # Defaults (paths, Pandoc, workers, reporting)
├── requirements.txt
├── README.md
├── assets/pandoc/header.tex    # Page numbers / table helpers
└── toolkit/
    ├── cli.py                  # Click CLI
    ├── config.py               # YAML load + path resolution
    ├── discovery.py            # Recursive Markdown discovery
    ├── pipeline.py             # Parallel orchestration + progress
    ├── reporting.py            # JSON reports + console summary
    ├── validation.py           # PDF existence / magic-byte checks
    ├── logging_setup.py
    ├── models.py
    ├── converters/
    │   ├── base.py             # Abstract BaseConverter (extension point)
    │   ├── registry.py         # Plug-in registry
    │   └── markdown_to_pdf.py  # Pandoc PDF converter
    ├── pdf_enhance.py          # Cover, bookmarks, stamps, metadata
    ├── manifest.py             # dataset_manifest.json
    └── utils/
        ├── paths.py            # Hierarchy-preserving path mapping
        └── pandoc.py           # Pandoc subprocess helpers
```

### Extension model

New formats register a `BaseConverter` subclass without changing the pipeline:

```python
# toolkit/converters/markdown_to_docx.py  (future)
class MarkdownToDocxConverter(BaseConverter):
    name = "markdown_to_docx"
    target_suffix = ".docx"
    def convert_one(self, job, context): ...

# toolkit/converters/registry.py
registry.register(MarkdownToDocxConverter())
```

Then:

```bash
python convert_dataset.py --converter markdown_to_docx
```

---

## Prerequisites

### 1. Python

Python **3.10+** (3.11/3.12 recommended).

### 2. Pandoc (required)

Install from https://pandoc.org/installing.html and confirm:

```bash
pandoc --version
```

### 3. PDF engine (required for PDF output)

Pandoc needs a PDF engine. Default is **Chrome/Edge headless** (`config.yaml → conversion.pdf_engine: chrome`).

| Engine | Notes |
|---|---|
| `chrome` / `edge` | Recommended on Windows — uses installed browser `--print-to-pdf` |
| `xelatex` | Requires a working MiKTeX / TeX Live |
| `weasyprint` | Pip package; often needs native libs |

Also install **PyMuPDF** (listed in `requirements.txt`) for cover page, bookmarks, stamps, and metadata.

---

## Installation

From the repository root:

```bash
cd tools/benchmark_dataset_toolkit
python -m pip install -r requirements.txt
```

No package install into the Knowra app environment is required; the entry script adds the toolkit home to `sys.path`.

---

## Dataset layout

```text
docs/apex_national_bank/
├── 00_foundation/
├── 01_enterprise_governance/
├── ...
└── 11_customer_cases/
```

### Output mapping

Hierarchy under `docs/apex_national_bank/` is preserved beneath `benchmark/pdf/`:

```text
docs/apex_national_bank/03_finance/001_EXPENSE_POLICY.md
        ↓
benchmark/pdf/03_finance/001_EXPENSE_POLICY.pdf
```

Filenames are preserved with a `.pdf` suffix.

---

## Usage

Run from **either** the toolkit directory or the repository root (paths resolve via `config.yaml`).

```bash
cd tools/benchmark_dataset_toolkit

# Default conversion (skip existing PDFs)
python convert_dataset.py

# Force reconvert everything
python convert_dataset.py --force

# Parallelism
python convert_dataset.py --workers 8

# Custom paths
python convert_dataset.py --input docs/apex_national_bank --output benchmark/pdf

# Plan only (no Pandoc invocation)
python convert_dataset.py --dry-run

# Debug logging
python convert_dataset.py --verbose
```

Equivalent module form (from the toolkit directory):

```bash
python -m toolkit --dry-run
```

### CLI reference

| Flag | Description |
|---|---|
| `--config PATH` | Alternate `config.yaml` |
| `--input DIR` | Markdown corpus root |
| `--output DIR` | PDF output root |
| `--workers N` | Thread pool size (default from config) |
| `--force` | Do not skip existing PDFs |
| `--dry-run` | Discover + plan only |
| `--verbose` | Debug logs |
| `--converter NAME` | Registered converter (default `markdown_to_pdf`) |

---

## Configuration

Edit `config.yaml` for defaults:

- Input / output directories
- Worker count
- Pandoc PDF engine, TOC, margins, fonts
- Report / log filenames
- PDF validation thresholds

Paths are resolved relative to the **repository root** unless absolute. Asset paths such as `assets/pandoc/header.tex` resolve relative to the toolkit folder.

---

## Reports & logs

Written under the output directory (default `benchmark/pdf/`):

| File | Contents |
|---|---|
| `conversion_report.json` | Totals, timings, per-file results, errors |
| `conversion_failures.json` | Failed conversions only |
| `conversion.log` | Full run log |

### Console summary

```text
---------------------------------------
Knowra Benchmark Dataset Toolkit
---------------------------------------
Markdown files discovered : 171
Converted                 : 171
Skipped                   : 0
Failed                    : 0
Verified OK               : 171
Elapsed                   : 0:01:42
Avg conversion time       : 0.598s
Output                    :
  .../benchmark/pdf
---------------------------------------
```

Progress during conversion:

```text
[ 72 / 171 ] OK   03_finance/001_EXPENSE_POLICY.md
```

---

## Behaviour notes

1. **Skip existing** — If the target PDF exists, it is skipped unless `--force`.
2. **Continue on errors** — One bad file does not abort the run; failures are collected in the report.
3. **PDF verification** — Every successful (and skipped) PDF is checked for existence, minimum size, and `%PDF` magic bytes.
4. **Exit codes** — `0` success (no failures), `1` one or more conversion failures, `2` fatal/config error.

---

## Enterprise PDF features

Applied after conversion (PyMuPDF post-process in `toolkit/pdf_enhance.py`):

| Feature | Config flag | Behaviour |
|---|---|---|
| Cover page | `cover_page` | Page 1 from markdown metadata table; no header/footer/page numbers |
| Page numbers | `page_numbers` | `Page N of M` on content pages only (starts after cover) |
| Header / footer | `header_enabled` / `footer_enabled` | Bank name + title; classification stamp |
| PDF metadata | `pdf_metadata` | Title, Author, Subject, Keywords, Creator, Producer, dates (Adobe Properties) |
| Bookmarks | `bookmarks` | Outline from markdown headings |
| TOC links | `toc_links` | Clickable TOC (from Pandoc HTML/LaTeX) |

Soft validation (`validation.enterprise_checks`) warns only — never fails a conversion.

---

## Roadmap

1. `markdown_to_docx` — Pandoc DOCX export with style reference
2. `scanned_pdf_generator` — Rasterize PDFs to image-only “scan” PDFs
3. `ocr_dataset_generator` — Pair scans with ground-truth text for OCR evals
4. `image_dataset_generator` — Page image corpora
5. Dataset statistics & quality gates (link integrity, ID coverage, cross-ref graph)

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Pandoc was not found on PATH` | Install Pandoc; restart the shell |
| `xelatex not found` / Pandoc PDF engine errors | Install TeX Live / MiKTeX; or change `pdf_engine` |
| Unicode / emoji failures with `pdflatex` | Prefer `xelatex` or `lualatex` |
| Missing fonts | Set `conversion.variables.mainfont` in `config.yaml` |
| Tables overflow page width | Tighten content or adjust `geometry` |

---

## License / ownership

Internal Knowra engineering tool. Do not ship inside the customer runtime image unless explicitly productized.
