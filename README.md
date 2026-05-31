# File Toolkit

A local Flask web app that consolidates 30+ file-processing tools into one clean interface. Handles PDFs, CSVs, and images — no cloud uploads, no user accounts, all processing happens on your machine.

## Features

### CSV / Data
| Tool | Description |
|------|-------------|
| **Split** | Upload a CSV/TSV, choose rows-per-file, download a ZIP of all parts. Tiny leftovers (< 10 rows) are appended to the last chunk instead of creating a micro-file. |
| **Merge** | Upload multiple CSV/TSV files, combine into a single CSV, TSV, or PDF. PDF output truncates at 500 rows for performance. |

### PDF Toolkit
| Tool | Description |
|------|-------------|
| **Merge** | Combine multiple PDFs into one |
| **Split** | Split by page count or custom page ranges |
| **Compress** | Reduce PDF file size |
| **Rotate** | Rotate all pages or specific pages |
| **Watermark** | Add a text watermark to every page |
| **Page Numbers** | Stamp page numbers (top/bottom, left/center/right) |
| **Header / Footer** | Add custom header and footer text |
| **Delete Pages** | Remove specific pages by number |
| **Extract Pages** | Pull out specific pages into a new PDF |
| **Reorder Pages** | Drag-and-drop page reordering |
| **Password Protect** | Encrypt a PDF with a password |
| **Unlock** | Remove password protection from a PDF |
| **Repair** | Attempt to fix a corrupted PDF |
| **Sign** | Add signer metadata to a PDF |
| **Compare** | Compare two PDFs by file size |
| **OCR** | Extract searchable text from scanned PDFs or images (Tesseract + ocrmypdf) |
| **Editor** | PDF text editing *(placeholder — in progress)* |

### Format Conversion
| From | To |
|------|----|
| PDF | DOCX, Excel, CSV, Images (PNG/JPG), PowerPoint |
| Images | PDF |
| Office (DOCX, XLSX, PPTX, ODT, ODS, ODP) | PDF |
| Scanned image / PDF | Searchable PDF (OCR) |

### Image Toolkit
| Tool | Description |
|------|-------------|
| **Compress** | Lossy or lossless compression with a quality slider; live before/after preview |
| **Resize** | Resize by percentage or custom dimensions, with optional aspect-ratio lock |
| **Convert** | Convert between PNG, JPG, and WebP |
| **Rotate / Flip** | Rotate by arbitrary degrees or flip horizontally/vertically |
| **Images → PDF** | Combine multiple images into a single PDF |

### Resume Builder
Three professional resume templates (Modern 1 / 2 / 3). Fill in the form, preview in real-time, and download as a PDF.

### AI Chat *(requires Ollama)*
Upload a PDF, CSV, or text file and ask questions about it. Powered by a local Ollama model — no data leaves your machine.

---

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+ · Flask 3.x |
| Data processing | pandas 2.x · openpyxl |
| PDF manipulation | PyMuPDF · pdf2docx · pdfplumber · PyPDF2 · pikepdf |
| PDF generation | reportlab · fpdf · WeasyPrint |
| Image processing | Pillow · pdf2image |
| OCR | pytesseract · ocrmypdf |
| Office conversion | python-pptx · python-docx |
| Frontend | Jinja2 · Tailwind CSS (CDN) · Font Awesome |
| AI | Ollama (HTTP, local) |

---

## Setup

```bash
git clone <repo-url>
cd splitting-and-merging

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt
python run.py                      # http://localhost:5000
```

### System dependencies

Some features need system-level libraries:

```bash
# Fedora
sudo dnf install tesseract tesseract-langpack-eng ocrmypdf cairo pango gdk-pixbuf2 libffi

# Ubuntu / Debian
sudo apt-get install tesseract-ocr ocrmypdf libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev

# Office → PDF conversion (all platforms)
# Requires LibreOffice to be installed and on PATH
```

### AI chat (optional)

Install [Ollama](https://ollama.com), pull a model, and make sure the server is running:

```bash
ollama pull llama3
ollama serve          # default: http://localhost:11434
```

---

## Project Layout

```
splitting-and-merging/
├── app/
│   ├── __init__.py              # App factory — registers all blueprints
│   ├── routes.py                # GET /, POST /split, POST /merge
│   ├── celery_app.py            # Celery factory (wired, not activated)
│   ├── pdf_toolkit/
│   │   └── __init__.py          # All /pdf/* routes
│   ├── image_toolkit/
│   │   └── __init__.py          # All /image/* routes
│   ├── resume/
│   │   └── __init__.py          # /resume/* routes
│   ├── tasks/
│   │   ├── conversion.py        # PDF ↔ DOCX/Excel/images/PPTX, Office → PDF
│   │   ├── pdf_ops.py           # Split, merge, rotate, watermark, etc.
│   │   ├── ocr.py               # Tesseract + ocrmypdf
│   │   ├── security.py          # Protect / unlock
│   │   ├── ai.py                # Ollama HTTP chat
│   │   ├── image.py             # Compress, resize, convert, rotate
│   │   └── editor.py            # PDF editor (placeholder)
│   └── templates/               # Jinja2 templates (36 files)
│       ├── base.html
│       ├── index.html
│       ├── resumes/
│       │   ├── modern_1.html
│       │   ├── modern_2.html
│       │   └── modern_3.html
│       └── ...
├── config.py                    # Upload folders, file limits, env config
├── run.py                       # Dev entry point
├── start.py                     # Launcher with auto browser-open
└── requirements.txt
```

---

## Configuration

Edit `config.py` or set environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | random | Flask session signing key |
| `PORT` | `5000` | Listening port (`start.py` only) |
| `DEFAULT_ROWS_PER_SPLIT` | `1000` | Rows per CSV split chunk |
| `MIN_ROWS_PER_FILE` | `10` | Min rows before merging leftovers into last chunk |
| `MAX_CONTENT_LENGTH` | `50 MB` | Max upload size |
| `ALLOWED_EXTENSIONS` | `csv, tsv` | Accepted types for CSV tools |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama server for AI chat |

---

## Notes

- **No database** — all processing is stateless and ephemeral. Uploaded files are stored temporarily in `uploads/`, `splits/`, and `merged/` and are not auto-cleaned.
- **Synchronous** — file operations block the request. Fine for local single-user use; swap to Celery + Redis for multi-user workloads (infrastructure is already wired in `celery_app.py`).
- **PDF compare** is file-size diff only — full content diff would require additional libraries.
# Toolkit
