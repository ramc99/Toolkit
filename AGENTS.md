# CSV & PDF Toolkit — Architecture

## What this is
A local Flask web app for working with CSV and PDF files. No user accounts, no database, no cloud storage — files live on disk temporarily per-request.

## Stack
| Layer | Tech |
|-------|------|
| Backend | Python 3.11+ / Flask 3.x |
| Data processing | pandas 2.x |
| PDF manipulation | PyMuPDF, pdfplumber, pdf2docx, PyPDF2, pikepdf |
| OCR | pytesseract, ocrmypdf |
| Image handling | Pillow, pdf2image |
| PDF generation | reportlab, fpdf |
| Frontend | Jinja2 templates + Tailwind CSS (Play CDN) + Font Awesome |

## Project layout
```
app/
  __init__.py          # app factory — registers both blueprints
  routes.py            # /split and /merge endpoints (Blueprint: main)
  celery_app.py        # optional Celery factory (unused unless Redis available)
  pdf_toolkit/
    __init__.py        # all /pdf/* routes (Blueprint: pdf_toolkit)
  tasks/
    conversion.py      # pdf↔docx/excel/csv/image (plain functions)
    editor.py          # pdf text editing (placeholder)
    ocr.py             # pytesseract + ocrmypdf
    security.py        # PyPDF2 protect/unlock
    ai.py              # Ollama HTTP chat
  templates/           # Jinja2 templates extending base.html
config.py              # upload/split/merge folders, limits, optional Celery URLs
run.py                 # dev entry point  (python run.py)
start.py               # launcher with auto browser-open
requirements.txt
```

## Key design decisions
- **No Celery required** — tasks in `app/tasks/` are plain Python functions called directly from routes. Celery infra (`celery_app.py`, `CELERY_*` config) is wired up for future use but not activated.
- **Synchronous processing** — all file ops block the request. Acceptable for a local tool; switch to background tasks + polling if multi-user.
- **Uploads are ephemeral** — `uploads/`, `splits/`, `merged/` are not cleaned up automatically. Add a scheduled cleanup if disk usage matters.
- **PDF compare is file-size diff only** — full text/content diff requires additional libraries (e.g. python-pdftotext + difflib).

## Running locally
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python run.py        # http://localhost:5000
```

## Environment variables
| Variable | Default | Purpose |
|----------|---------|---------|
| `SECRET_KEY` | random | Flask session signing |
| `PORT` | 5000 | Listening port (start.py only) |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama server for AI chat |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Future Celery broker |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/0` | Future Celery backend |

## Implemented endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Home — CSV split + merge forms + PDF tool grid |
| POST | `/split` | Split CSV → ZIP |
| POST | `/merge` | Merge CSVs/TSVs → CSV/TSV/PDF |
| GET | `/pdf/` | PDF tools landing page |
| GET/POST | `/pdf/conversion` | Conversion form |
| POST | `/pdf/conversion/<target>` | Run conversion (docx/excel/csv/image/pdf_from_images) |
| GET/POST | `/pdf/editor` | PDF editor (placeholder copy) |
| GET/POST | `/pdf/ocr` | OCR image or PDF |
| GET/POST | `/pdf/security` | Protect / unlock PDF |
| GET/POST | `/pdf/ai` | Ollama chat |
| GET/POST | `/pdf/compare` | Compare two PDFs (size diff) |
| GET | `/pdf/organization` | Coming soon |
| GET | `/pdf/batch` | Coming soon |
