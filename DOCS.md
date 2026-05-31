# File Toolkit — Technical Documentation

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Setup & Configuration](#setup--configuration)
4. [Application Factory](#application-factory)
5. [Blueprint: CSV (main)](#blueprint-csv-main)
6. [Blueprint: PDF Toolkit](#blueprint-pdf-toolkit)
7. [Blueprint: Image Toolkit](#blueprint-image-toolkit)
8. [Blueprint: Resume Builder](#blueprint-resume-builder)
9. [Task Functions](#task-functions)
   - [PDF Operations](#pdf-operations-pdf_opspy)
   - [Format Conversion](#format-conversion-conversionpy)
   - [OCR](#ocr-ocrpy)
   - [Security](#security-securitypy)
   - [Image Processing](#image-processing-imagepy)
   - [AI Chat](#ai-chat-aipy)
10. [Error Handling](#error-handling)
11. [File Storage](#file-storage)

---

## Overview

File Toolkit is a local Flask web application that bundles 30+ file-processing tools into one interface. All processing happens on your machine — no cloud uploads, no user accounts, no database.

**Four tool categories:**

| Category | Tools |
|----------|-------|
| CSV / Data | Split by rows, merge multiple files |
| PDF | Merge, split, compress, rotate, watermark, convert, OCR, sign, secure, repair, and more |
| Images | Compress, resize, convert formats, rotate/flip, combine to PDF |
| Resume | Form-driven builder with PDF export |

---

## Architecture

### Blueprint layout

```
app/
├── __init__.py          create_app() factory
├── routes.py            Blueprint: main        →  /  /split  /merge
├── pdf_toolkit/
│   └── __init__.py      Blueprint: pdf_toolkit →  /pdf/*
├── image_toolkit/
│   └── __init__.py      Blueprint: image_toolkit → /image/*
├── resume/
│   └── __init__.py      Blueprint: resume_bp   →  /resume/*
└── tasks/               Plain Python functions (no Celery)
    ├── pdf_ops.py        pikepdf + PyMuPDF operations
    ├── conversion.py     pdf2docx, pdfplumber, pdf2image, LibreOffice
    ├── ocr.py            pytesseract, ocrmypdf
    ├── security.py       PyPDF2 encrypt/decrypt
    ├── image.py          Pillow operations
    ├── ai.py             Ollama HTTP chat
    └── editor.py         PDF text editor (placeholder)
```

### Request lifecycle

1. `before_request` — records `g.t0 = time.perf_counter()`, skips `/static/*`
2. Route handler — validates upload, calls task function, returns file or JSON
3. `after_request` — logs `METHOD /path → STATUS in Xms`
4. `teardown_request` — catches and logs any unhandled exceptions

### Processing model

All task functions are **synchronous** — they block the request until the file operation completes. This is intentional for a local single-user tool. Celery infrastructure (`celery_app.py`, `CELERY_*` config keys) is wired but not activated; enable it if you need async processing for larger files.

---

## Setup & Configuration

### Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python run.py          # http://localhost:5000
```

### System dependencies

| Feature | Fedora | Ubuntu/Debian |
|---------|--------|---------------|
| OCR | `sudo dnf install tesseract tesseract-langpack-eng ocrmypdf` | `sudo apt install tesseract-ocr ocrmypdf` |
| WeasyPrint (PDF) | `sudo dnf install cairo pango gdk-pixbuf2 libffi` | `sudo apt install libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev` |
| Office → PDF | LibreOffice on PATH | LibreOffice on PATH |

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | random 64-char hex | Flask session signing key |
| `PORT` | `5000` | Listening port (`start.py` only) |
| `OLLAMA_API_KEY` | *(see ai.py)* | Override default Ollama API key |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Future Celery broker |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/0` | Future Celery backend |

### config.py constants

| Constant | Default | Description |
|----------|---------|-------------|
| `UPLOAD_FOLDER` | `./uploads` | All uploaded and generated files |
| `SPLIT_FOLDER` | `./splits` | CSV split output |
| `MERGE_FOLDER` | `./merged` | CSV merge output |
| `MAX_CONTENT_LENGTH` | `50 MB` | Max upload size |
| `ALLOWED_EXTENSIONS` | `{csv, tsv}` | Accepted types for CSV routes |
| `DEFAULT_ROWS_PER_SPLIT` | `1000` | Default chunk size for CSV split |
| `MIN_ROWS_PER_FILE` | `10` | Min rows before merging leftover chunk |

---

## Application Factory

**File:** `app/__init__.py`

```python
create_app() → Flask
```

- Applies `config.py` values onto the Flask app
- Sets up two log handlers: file (`DEBUG`, `logs/app.log`) and console (`INFO`)
- Creates `UPLOAD_FOLDER`, `SPLIT_FOLDER`, `MERGE_FOLDER` if missing
- Registers four blueprints: `main`, `pdf_toolkit`, `image_toolkit`, `resume_bp`
- Hooks:
  - `before_request` → stores `g.t0` timestamp; skips static files
  - `after_request` → logs method + path + status + elapsed ms
  - `teardown_request` → logs unhandled exceptions with traceback

**Log format:** `YYYY-MM-DD HH:MM:SS  LEVEL  message`

---

## Blueprint: CSV (main)

**File:** `app/routes.py`  
**URL prefix:** `/`

### Helper

```python
allowed_file(filename: str) → bool
```
Returns `True` if the file extension is in `ALLOWED_EXTENSIONS` (`csv`, `tsv`).

---

### `GET /`

Renders the home page (`index.html`) — shows links to all tool categories.

---

### `GET /split`

Renders `csv_split.html` with a file upload form and a row-count input.

---

### `POST /split`

Splits a CSV/TSV file into multiple smaller files and returns them as a ZIP.

**Form fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `file` | File | required | CSV or TSV to split |
| `row_count` | int | `DEFAULT_ROWS_PER_SPLIT` (1000) | Rows per output file |

**Processing steps:**

1. Validate file is present and has an allowed extension.
2. Parse `row_count`; enforce minimum of `MIN_ROWS_PER_FILE` (10).
3. Read CSV with `pandas.read_csv()` preserving header.
4. Slice rows into chunks of `row_count`.
5. Leftover chunk logic:
   - If leftover rows **< `MIN_ROWS_PER_FILE`** → append to the previous part.
   - Otherwise → save as its own part file.
6. Write part files as `{basename}_part_1.csv`, `_part_2.csv`, …
7. Bundle all parts into `{basename}_splits.zip`.

**Returns:** ZIP file download.

**Logs:** filename, rows_per_split, total_rows, output zip path.

---

### `GET /merge`

Renders `csv_merge.html` with a multi-file upload form and format selector.

---

### `POST /merge`

Merges multiple CSV/TSV files into a single output file.

**Form fields:**

| Field | Type | Options | Description |
|-------|------|---------|-------------|
| `files` | File[] | required | Two or more CSV/TSV files |
| `format` | string | `csv` \| `tsv` \| `pdf` | Output format |

**Processing steps:**

1. Validate at least one file is present; validate format.
2. For each file, infer separator from extension (`,` for CSV, `\t` for TSV).
3. Read with `pandas.read_csv(sep=sep)`.
4. Concatenate all DataFrames with `axis=0, ignore_index=True, sort=False` (union of all columns).
5. Output:
   - **CSV/TSV** — `merged_output.csv` or `merged_output.tsv` with appropriate separator.
   - **PDF** — FPDF table, truncated to **500 rows** for performance. Use CSV/TSV for full data.

**Returns:** Merged file download.

**Logs:** output path, format, number of source files.

---

## Blueprint: PDF Toolkit

**File:** `app/pdf_toolkit/__init__.py`  
**URL prefix:** `/pdf`

### Internal helpers

```python
_file_context(f: FileStorage) → str
```

Extracts readable context from an uploaded file for the AI prompt. Returns a formatted string:

- **CSV/TSV** — shape, column names, dtypes, missing-value counts, first 5 rows
- **PDF** — first ~4000 characters of text (via pdfminer)
- **TXT / MD / JSON / LOG** — raw text (first 4000 chars)
- **Binary / unknown** — filename only

---

### Routes

#### `GET /pdf/`
Renders `pdf_home.html` — landing page listing all PDF tools.

---

#### `GET/POST /pdf/compare`

Compares two PDFs by file size and displays a summary.

**Form fields:** `file1` (PDF), `file2` (PDF)

**Returns:** Renders `compare.html` with size comparison results.

---

#### `GET /pdf/conversion`

Renders `conversion.html` — menu for selecting the target format.

---

#### `POST /pdf/conversion/<target>`

Runs a format conversion on an uploaded file.

**URL parameter:** `target` — one of `docx`, `excel`, `csv`, `image`, `pdf_from_images`, `pptx`

**Form fields:** `file` (PDF or image depending on target)

| Target | Input | Output | Task function |
|--------|-------|--------|--------------|
| `docx` | PDF | DOCX | `pdf_to_docx()` |
| `excel` | PDF | XLSX | `pdf_to_excel()` |
| `csv` | PDF | CSV | `pdf_to_csv()` |
| `image` | PDF | PNG images (ZIP if multi-page) | `pdf_to_image()` |
| `pdf_from_images` | Images | PDF | `image_to_pdf()` |
| `pptx` | PDF | PPTX | `pdf_to_pptx()` |

Returns `400` for unsupported targets.

---

#### `GET/POST /pdf/editor`

PDF text editor (placeholder — copies the file unchanged).

**Form fields:** `file` (PDF), `edits` (string — edit instructions, unused)

---

#### `GET /pdf/organization`

Placeholder — renders `coming_soon.html`.

---

#### `GET/POST /pdf/ocr`

Performs OCR on an uploaded image or PDF.

**Form fields:** `file` (PNG, JPG, JPEG, TIF, TIFF, or PDF)

| Input | Behaviour | Returns |
|-------|-----------|---------|
| Image | `ocr_image()` → extracted text string | Renders `ocr_result.html` with text |
| PDF | `ocr_pdf()` → searchable PDF | PDF download |

---

#### `GET/POST /pdf/security`

Encrypts or decrypts a PDF.

**Form fields:**

| Field | Values | Description |
|-------|--------|-------------|
| `file` | PDF | File to protect or unlock |
| `action` | `protect` \| `unlock` | Operation |
| `password` | string | Password to apply or remove |

- `protect` → calls `protect_pdf(path, password)` → returns `protected.pdf`
- `unlock` → calls `unlock_pdf(path, password)` → returns `unlocked.pdf`

---

#### `POST /pdf/ai/ask` (AJAX endpoint)

Chat with an AI about an uploaded file.

**Accepts:** JSON body or multipart form.

**Parameters:**

| Field | Required | Description |
|-------|----------|-------------|
| `prompt` | yes | The user's question |
| `context` | no | Additional context string |
| `file` | no | File to extract context from |

**Flow:**
1. If a file is provided, call `_file_context(file)` to extract text.
2. Build a system prompt from the extracted context.
3. Call `ollama_chat(prompt, system=system_prompt)`.
4. Return `{"reply": "<text>"}`.

**Error responses:**
- `429` — `OllamaRateLimitError` (all API keys exhausted)
- `500` — any other exception

---

#### `GET/POST /pdf/ai`

Full-page AI chat form.

- **GET:** Renders `ai.html`; accepts optional `?prompt=` query param to pre-fill.
- **POST:** Submits prompt, returns response in `ai.html`.

---

#### `GET /pdf/batch`

Placeholder — renders `coming_soon.html`.

---

#### `GET/POST /pdf/merge`

Merges multiple PDFs into one.

**Form fields:** `files[]` — two or more PDFs.

Calls `merge_pdfs(paths)` → returns `merged.pdf`.

---

#### `GET/POST /pdf/split`

Splits a PDF by page count or custom ranges.

**Form fields:**

| Field | Values | Description |
|-------|--------|-------------|
| `file` | PDF | Source PDF |
| `mode` | `every` \| `ranges` | Split mode |
| `every` | int (default 1) | Pages per output file (mode=every) |
| `ranges` | string | Comma-separated ranges, e.g. `1-3,5,8-10` (mode=ranges) |

**Range format:** `1-3` = pages 1 through 3; `5` = page 5 only. Pages are 1-indexed.

Calls `split_pdf(path, every=..., ranges=...)` → returns `split_pages.zip`.

---

#### `GET/POST /pdf/compress`

Reduces PDF file size.

**Form fields:** `file` (PDF)

Calls `compress_pdf(path)` → returns `compressed.pdf`.

---

#### `GET/POST /pdf/rotate`

Rotates all or specific pages in a PDF.

**Form fields:**

| Field | Values | Default | Description |
|-------|--------|---------|-------------|
| `file` | PDF | required | Source PDF |
| `angle` | int | `90` | Degrees to rotate (clockwise) |
| `page_mode` | `all` \| `specific` | `all` | Which pages to rotate |
| `pages` | string | — | Comma-separated page numbers (1-indexed) when mode=specific |

Calls `rotate_pdf(path, angle, pages)` → returns `rotated.pdf`.

---

#### `GET/POST /pdf/delete-pages`

Removes specific pages from a PDF.

**Form fields:** `file` (PDF), `pages` (required, comma-separated 1-indexed page numbers)

Calls `delete_pages(path, page_nums)` → returns `pages_deleted.pdf`.

---

#### `GET/POST /pdf/extract-pages`

Extracts specific pages into a new PDF.

**Form fields:** `file` (PDF), `pages` (required, supports ranges: `1-3,5`)

Calls `extract_pages(path, page_nums)` → returns `extracted.pdf`.

---

#### `GET/POST /pdf/reorder`

Reorders pages in a PDF.

**Form fields:** `file` (PDF), `order` (required, comma-separated new page sequence, 1-indexed — e.g. `3,1,2` moves page 3 first)

Calls `reorder_pdf(path, order)` → returns `reordered.pdf`.

---

#### `GET/POST /pdf/watermark`

Adds a text watermark to every page.

**Form fields:** `file` (PDF), `text` (required, watermark string)

Watermark is rendered at **45° angle**, centered on each page, semi-transparent grey (RGB 0.75, 0.75, 0.75), font size 52.

Calls `watermark_pdf(path, text)` → returns `watermarked.pdf`.

---

#### `GET/POST /pdf/number-pages`

Stamps page numbers onto every page.

**Form fields:**

| Field | Values | Default | Description |
|-------|--------|---------|-------------|
| `file` | PDF | required | Source PDF |
| `position` | `bottom-center` \| `bottom-right` \| `bottom-left` \| `top-center` \| `top-right` \| `top-left` | `bottom-center` | Where to place the number |
| `start` | int | `1` | Starting page number |

Calls `number_pages(path, position, start)` → returns `numbered.pdf`.

---

#### `GET/POST /pdf/header-footer`

Adds a header, footer, or both to every page.

**Form fields:** `file` (PDF), `header` (optional string), `footer` (optional string). At least one must be provided.

Text is centered, font size 9, grey (0.3, 0.3, 0.3).

Calls `add_header_footer(path, header, footer)` → returns `header_footer.pdf`.

---

#### `GET/POST /pdf/repair`

Attempts to fix a corrupted PDF by re-parsing and re-saving it.

**Form fields:** `file` (PDF)

Calls `repair_pdf(path)` → returns `repaired.pdf`.

---

#### `GET/POST /pdf/sign`

Adds a visual signature box to the last page.

**Form fields:**

| Field | Required | Description |
|-------|----------|-------------|
| `file` | yes | PDF to sign |
| `name` | yes | Signer name |
| `date` | no | Signature date |
| `reason` | no | Reason for signing |

Signature box: bottom-right corner, 210px wide × 70px tall. Border in blue (0.2, 0.35, 0.75), text in dark blue (0.1, 0.1, 0.5), font size 8.

Calls `sign_pdf(path, name, date, reason)` → returns `signed.pdf`.

---

#### `GET/POST /pdf/to-pptx`

Converts a PDF to a PowerPoint presentation (one slide per page).

**Form fields:** `file` (PDF)

Calls `pdf_to_pptx(path)` → returns `presentation.pptx`.

---

#### `GET/POST /pdf/office-to-pdf`

Converts a Microsoft Office or OpenDocument file to PDF via LibreOffice.

**Accepted formats:** `.docx`, `.doc`, `.xlsx`, `.xls`, `.pptx`, `.ppt`, `.odt`, `.ods`, `.odp`

**Form fields:** `file` (Office document)

Calls `office_to_pdf(path)` → returns `converted.pdf`.

Requires LibreOffice installed and on `PATH`. Returns `500` if LibreOffice is missing.

---

## Blueprint: Image Toolkit

**File:** `app/image_toolkit/__init__.py`  
**URL prefix:** `/image`

### Internal helpers

| Helper | Description |
|--------|-------------|
| `_allowed(filename)` | Returns `True` if extension is in `{png, jpg, jpeg, webp, bmp, tiff, gif}` |
| `_save_upload(file)` | Saves file to `UPLOAD_FOLDER` with `secure_filename`, returns path |
| `_fmt_size(n)` | Formats bytes → human-readable string (B / KB / MB) |
| `_image_info(path)` | Returns `{size, size_fmt, width, height, format}` dict |
| `_preview_url(path)` | Returns `/image/preview/{filename}` URL |
| `_is_ajax()` | Checks `X-Requested-With: XMLHttpRequest` header |
| `_comparison(upload_path, result, download_name)` | Builds before/after comparison JSON |
| `_compressed_folder()` | Returns (creating if needed) `{UPLOAD_FOLDER}/compressed` |
| `_process_image(input_path, output_path, settings)` | Full processing pipeline (see below) |

#### `_process_image` settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `quality` | int | 80 | JPEG/WebP quality (1–100) |
| `format` | string | source ext | Output format |
| `resize_mode` | `none` \| `percentage` \| `custom` | `none` | How to resize |
| `resize_value` | int | — | Percentage (1–200) if mode=percentage |
| `width` / `height` | int | — | Target dimensions if mode=custom |
| `keep_aspect` | bool | `True` | Lock aspect ratio on custom resize |
| `brightness` | float | `1.0` | 1.0 = no change |
| `contrast` | float | `1.0` | 1.0 = no change |
| `sharpness` | float | `1.0` | 1.0 = no change |
| `blur` | float | `0.0` | 0.0 = no blur |

**Optimization rules:**
- `quality=100`, no enhancements, same format → copy original unchanged
- JPEG → progressive encoding for large images; fall back to original if re-encoding is larger
- PNG → `compress_level=9`, `optimize=True`
- WebP → `method=4`

**Color space:**
- JPEG / WebP → force `RGB`
- PNG → preserve `RGBA` if present; else `RGB`

---

### Routes

#### `GET /image/`
Renders `image_home.html` — lists all image tools.

---

#### `GET /image/preview/<filename>`
Serves an image from `UPLOAD_FOLDER` (or the `compressed/` subfolder). Returns `404` if not found.

---

#### `GET /image/download/<filename>`
Downloads an image as an attachment.

---

#### `GET /image/serve-orig/<filename>`
Serves the original uploaded image (used by the interactive compressor UI).

---

#### `GET /image/serve-comp/<filename>`
Serves the current compressed preview from `UPLOAD_FOLDER/compressed/`.

---

#### `GET /image/dl-comp/<filename>`
Downloads the compressed image as an attachment.

---

#### `GET/POST /image/compress`

Simple one-shot compression.

**Form fields:** `file` (image), `quality` (int, default 60)

Calls `compress_image(path, quality)`.

- **AJAX request** → returns comparison JSON (before/after size, dimensions, download URL)
- **Regular request** → direct file download

---

#### `POST /image/compress-upload` (Step 1 of interactive compressor)

Accepts an image upload, applies default compression (quality=60), and returns stats for the live preview UI.

**Form fields:** `file` (image)

**Returns JSON:**

```json
{
  "file_id": "a3f8c2d1e9b0",
  "orig_ext": "jpg",
  "original_size": 204800,
  "original_size_str": "200.0 KB",
  "compressed_size_str": "87.3 KB",
  "reduction_percent": 57.3,
  "orig_url": "/image/serve-orig/a3f8c2d1e9b0_orig.jpg",
  "comp_url": "/image/serve-comp/a3f8c2d1e9b0_comp.jpg",
  "download_url": "/image/dl-comp/a3f8c2d1e9b0_comp.jpg",
  "orig_width": 1920,
  "orig_height": 1080
}
```

Files stored as: `{file_id}_orig.{ext}` (original) and `{file_id}_comp.{ext}` (compressed).

---

#### `POST /image/compress-process` (Step 2 — slider update)

Re-processes the previously uploaded image with new settings from the slider.

**JSON body:**

| Field | Type | Description |
|-------|------|-------------|
| `file_id` | string | ID from compress-upload |
| `format` | string | Output format |
| `quality` | int | New quality value (1–100) |
| `resize_mode` | string | none / percentage / custom |
| `resize_value` | int | Percentage if mode=percentage |
| `width` / `height` | int | Dimensions if mode=custom |
| `keep_aspect` | bool | Lock aspect ratio |
| `brightness` / `contrast` / `sharpness` | float | Enhancement values |
| `blur` | float | Gaussian blur radius |

Deletes the previous compressed file, writes a new one, returns updated stats JSON.

---

#### `GET/POST /image/resize`

Resizes an image to exact or percentage dimensions.

**Form fields:**

| Field | Default | Description |
|-------|---------|-------------|
| `file` | required | Image to resize |
| `width` | `800` | Target width in pixels |
| `height` | `600` | Target height in pixels |
| `keep_aspect` | `true` | `true` → use thumbnail(); `false` → force exact size |

Calls `resize_image(path, width, height, keep_aspect)` → download.

---

#### `GET/POST /image/convert`

Converts an image to a different format.

**Form fields:** `file` (image), `target_fmt` (`png` / `jpg` / `webp` / `bmp` / `tiff` / `gif`)

- AJAX → comparison JSON
- Regular → download

---

#### `GET/POST /image/rotate`

Rotates or flips an image.

**Form fields:**

| Field | Values | Default | Description |
|-------|--------|---------|-------------|
| `file` | image | required | Source image |
| `direction` | `rotate` \| `flip_h` \| `flip_v` | `rotate` | Operation |
| `degrees` | int | `90` | Degrees (used when direction=rotate) |

- `rotate` → calls `rotate_image(path, degrees)` (canvas expands to fit)
- `flip_h` → calls `flip_image(path, 'horizontal')`
- `flip_v` → calls `flip_image(path, 'vertical')`

Returns the transformed image as a download.

---

#### `GET/POST /image/to-pdf`

Combines multiple images into a single PDF.

**Form fields:** `files[]` (multiple images)

Calls `images_to_pdf(paths)` → returns `images.pdf`.

---

## Blueprint: Resume Builder

**File:** `app/resume/__init__.py`  
**URL prefix:** `/resume`

### Data models

```python
@dataclass
Skill(name: str, level: int = 3)          # level 1–5

@dataclass
ContactInfo(
    name: str, email: str, phone: str, location: str,
    linkedin: str = "", website: str = ""
)

@dataclass
WorkExperience(
    company: str, role: str,
    start_date: str, end_date: str,
    bullets: list[str]
)

@dataclass
Education(
    institution: str, degree: str, field: str,
    start_date: str, end_date: str,
    gpa: str = ""
)

@dataclass
ResumeData(
    contact: ContactInfo,
    summary: str,
    experience: list[WorkExperience],
    education: list[Education],
    skills: list[Skill],
    template: str = "modern_1"
)
```

### Template registry

| Key | Template file |
|-----|--------------|
| `modern_1` | `templates/resumes/modern_1.html` |
| `modern_2` | `templates/resumes/modern_2.html` |
| `modern_3` | `templates/resumes/modern_3.html` |

### Internal functions

```python
_to_ctx(data: ResumeData) → dict
```
Converts the `ResumeData` dataclass to a plain dict for Jinja2 template rendering.

```python
render_resume_html(data: ResumeData) → str
```
Renders the selected template with `_to_ctx(data)`, returns the HTML string.

```python
generate_pdf(html: str) → bytes
```
Passes the HTML string through WeasyPrint and returns raw PDF bytes.

```python
_parse_form(form: ImmutableMultiDict) → ResumeData
```

Parses a form submission into a `ResumeData` object:

- **Work experience** — reads parallel lists: `company[]`, `role[]`, `exp_start[]`, `exp_end[]`, `bullets[]`. Empty `company` entries are skipped.
- **Education** — reads: `institution[]`, `degree[]`, `field[]`, `edu_start[]`, `edu_end[]`, `gpa[]`. Empty `institution` entries are skipped.
- **Skills** — reads `skill_name[]` and `skill_level[]`; clamps level to 1–5.
- Raises `ValueError` on any parsing error (caught by route → `422`).

---

### Routes

#### `GET /resume/`

Renders `resume_index.html` with:
- `templates` — list of available template keys
- `sample_html` — pre-rendered sample resume for the preview pane

---

#### `POST /resume/preview`

Parses the submitted form, renders the resume HTML, and returns it directly as an HTML response (embedded in the preview iframe).

Returns `422` if `_parse_form` raises a `ValueError`.

---

#### `POST /resume/download`

Parses the submitted form, generates a PDF with WeasyPrint, and streams it back.

- `Content-Type: application/pdf`
- `Content-Disposition: attachment; filename="{name}_resume.pdf"`

Returns `422` on form parse error.

---

## Task Functions

### PDF Operations (`pdf_ops.py`)

All functions write output to `UPLOAD_FOLDER` with a UUID filename. Each function returns the output file path.

#### Helpers

```python
_out(ext: str) → str
```
Returns `{UPLOAD_FOLDER}/{uuid4}.{ext}`.

```python
_parse_page_list(s: str, total: int) → list[int]
```
Parses a page-number string into a 0-indexed list.

| Input | Output (0-indexed) |
|-------|--------------------|
| `"1,3-5,8"` | `[0, 2, 3, 4, 7]` |
| `"2"` | `[1]` |
| `"1-3"` | `[0, 1, 2]` |

---

#### `merge_pdfs(input_paths: list[str]) → str`

Uses **pikepdf**. Opens all source PDFs, creates a new PDF, and extends it with pages from each source in order.

---

#### `split_pdf(input_path: str, every: int = None, ranges: list[tuple] = None) → str`

Uses **pikepdf**. Two modes:

- **`every`** — chunk the pages every N: `[0..N-1]`, `[N..2N-1]`, …
- **`ranges`** — use the provided list of `(start, end)` tuples (0-indexed, end exclusive)

Writes `part_1.pdf`, `part_2.pdf`, … then ZIPs them. Returns the ZIP path.

---

#### `compress_pdf(input_path: str) → str`

Uses **pikepdf** with `compress_streams=True` and object stream generation.

---

#### `rotate_pdf(input_path: str, angle: int, pages: str = 'all') → str`

Uses **pikepdf**. For each target page, adds `angle` to the existing `/Rotate` value (mod 360).

`pages` is a comma-separated string of 1-indexed page numbers, or `"all"`.

---

#### `delete_pages(input_path: str, page_nums: str) → str`

Uses **pikepdf**. Parses page numbers (1-indexed), sorts descending, and deletes in reverse order to preserve indices.

---

#### `extract_pages(input_path: str, page_nums: str) → str`

Uses **pikepdf**. Parses page numbers (supports ranges), copies matching pages to a new PDF.

---

#### `reorder_pdf(input_path: str, order: str) → str`

Uses **pikepdf**. Parses the new page order (1-indexed) and appends pages to a new PDF in that sequence.

---

#### `watermark_pdf(input_path: str, text: str) → str`

Uses **PyMuPDF (fitz)**. On each page, inserts `text` at:
- Position: 22% of width, 62% of height
- Angle: 45°
- Font size: 52
- Color: RGB (0.75, 0.75, 0.75) — semi-transparent grey

---

#### `number_pages(input_path: str, position: str = 'bottom-center', start: int = 1) → str`

Uses **PyMuPDF**. Inserts the page number on each page at the specified position with 18px margin, font size 10.

Supported positions: `bottom-center`, `bottom-right`, `bottom-left`, `top-center`, `top-right`, `top-left`.

---

#### `add_header_footer(input_path: str, header: str = '', footer: str = '') → str`

Uses **PyMuPDF**. Inserts header and/or footer text on every page, centered, font size 9, color (0.3, 0.3, 0.3).

---

#### `repair_pdf(input_path: str) → str`

Uses **pikepdf** with `suppress_warnings=True`. Opens and re-saves the PDF, which fixes many common corruption issues.

---

#### `sign_pdf(input_path: str, name: str, date: str = '', reason: str = '') → str`

Uses **PyMuPDF**. Adds a signature box on the **last page** at the bottom-right:

- Dimensions: 210px wide × 70px tall
- Border color: (0.2, 0.35, 0.75) — blue
- Text color: (0.1, 0.1, 0.5) — dark blue
- Font size: 8
- Content: `"Signed by: {name}"` + optional date and reason lines

---

### Format Conversion (`conversion.py`)

#### `pdf_to_docx(input_path: str) → str`

Uses **pdf2docx**. Opens the PDF, runs the converter, saves as DOCX.

---

#### `pdf_to_excel(input_path: str) → str`

Uses **pdfplumber** to extract tables from all pages → concatenates DataFrames → writes XLSX via **openpyxl**.

---

#### `pdf_to_csv(input_path: str) → str`

Same pipeline as `pdf_to_excel` but writes CSV instead.

---

#### `pdf_to_image(input_path: str, fmt: str = 'png') → str`

Uses **pdf2image**. Converts each page to an image. If multiple pages, ZIPs all images and returns the ZIP path; otherwise returns the single image path.

---

#### `image_to_pdf(image_paths: str) → str`

Input: comma-separated file paths. Uses **PIL**. Opens all images as RGB, saves the first with `append_images` for the rest. Returns PDF path.

---

#### `pdf_to_pptx(input_path: str) → str`

Uses **pdf2image** (dpi=150) and **python-pptx**. Creates a blank presentation, adds one slide per page, inserts the page image filling the slide.

---

#### `office_to_pdf(input_path: str) → str`

Uses **LibreOffice CLI**:

```bash
libreoffice --headless --convert-to pdf --outdir <upload_folder> <input_file>
```

Timeout: 60 seconds. Returns `RuntimeError` if LibreOffice is not installed or conversion fails.

---

### OCR (`ocr.py`)

#### `ocr_image(image_path: str, lang: str = 'eng') → str`

Uses **pytesseract**. Opens image with PIL, runs `image_to_string(img, lang=lang)`. Returns extracted text string.

---

#### `ocr_pdf(pdf_path: str, lang: str = 'eng') → str`

Uses **ocrmypdf CLI** via subprocess:

```bash
ocrmypdf --language eng <input> <output>
```

Returns the output searchable PDF path.

---

### Security (`security.py`)

#### `protect_pdf(pdf_path: str, password: str) → str`

Uses **PyPDF2**. Reads all pages, creates a `PdfWriter`, adds all pages, encrypts with `user_pwd=password`, `owner_pwd=None`, 128-bit encryption. Returns output path.

---

#### `unlock_pdf(pdf_path: str, password: str) → str`

Uses **PyPDF2**. Reads PDF, calls `.decrypt(password)` if encrypted, copies all pages to a new unencrypted PDF. Returns output path.

---

### Image Processing (`image.py`)

#### `convert_image(input_path: str, target_fmt: str) → str`

Opens with PIL, converts color space (`RGB` for JPEG/WebP, `RGBA` for PNG otherwise `RGB`), saves in target format.

---

#### `compress_image(input_path: str, quality: int = 60) → str`

Opens with PIL, saves at reduced quality. Format-specific:
- JPEG / WebP — `quality=quality`
- PNG — `optimize=True`

---

#### `resize_image(input_path: str, width: int, height: int, keep_aspect: bool = True) → str`

- `keep_aspect=True` → `thumbnail((width, height))` — fits within bounds, preserves ratio
- `keep_aspect=False` → `resize((width, height))` — exact dimensions

---

#### `images_to_pdf(image_paths: str) → str`

Comma-separated paths. Opens all as RGB, saves the first image as a PDF with `append_images` for the remaining pages.

---

#### `rotate_image(input_path: str, degrees: int = 90) → str`

`image.rotate(-degrees, expand=True)` — negative to match clockwise UI expectation; `expand=True` resizes canvas to fit.

---

#### `flip_image(input_path: str, direction: str = 'horizontal') → str`

- `horizontal` → `FLIP_LEFT_RIGHT`
- `vertical` → `FLIP_TOP_BOTTOM`

---

### AI Chat (`ai.py`)

#### `ollama_chat(prompt: str, model: str = 'gpt-oss:120b-cloud', system: str = None) → str`

Calls the Ollama cloud API with automatic key rotation and retry logic.

**API keys** — tried in order:
1. `OLLAMA_API_KEY` environment variable
2. Three built-in fallback keys

**Retry strategy per key:**
- Attempt up to **3 times**
- `429 Too Many Requests` → sleep 1s, then 2s, then move to next key
- Other HTTP error → immediately try next key

**Raises:** `OllamaRateLimitError` if all keys are exhausted.

**Message structure sent to API:**

```json
[
  { "role": "system", "content": "<system prompt>" },
  { "role": "user",   "content": "<prompt>" }
]
```

System message is omitted if `system=None`.

---

## Error Handling

| Scenario | HTTP status | Where |
|----------|-------------|-------|
| No file uploaded | 400 | All upload routes |
| Invalid file extension | 400 | All upload routes |
| Invalid/missing form fields | 400 | Split, merge, PDF routes |
| Unsupported conversion target | 400 | `/pdf/conversion/<target>` |
| Form parse error in resume builder | 422 | `/resume/preview`, `/resume/download` |
| LibreOffice not found | 500 | `/pdf/office-to-pdf` |
| All Ollama API keys exhausted | 429 | `/pdf/ai/ask` |
| Unhandled exception | 500 | Any route (logged via `teardown_request`) |

---

## File Storage

All uploaded and generated files go to `UPLOAD_FOLDER` (`./uploads`) with UUID-based names. Sub-folders:

| Path | Contents |
|------|----------|
| `uploads/` | All uploads and generated outputs |
| `uploads/compressed/` | Interactive compressor previews |
| `splits/` | CSV split output ZIPs |
| `merged/` | CSV merge output files |

**There is no automatic cleanup.** Files accumulate until removed manually. To add cleanup, schedule a job that deletes files older than N hours from these directories.
