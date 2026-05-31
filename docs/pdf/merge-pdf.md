# Merge PDF

## Route

`POST /pdf/merge`

## Overview

The Merge PDF tool combines multiple PDF files into a single output PDF. Files are merged in the exact order they are uploaded. Each source file is opened with pikepdf, and its pages are appended sequentially to a new PDF document. The merged result is saved to disk with a UUID-based filename and returned to the caller as a downloadable file.

---

## Features

1. **Order-preserving merge** — pages appear in the output in the same sequence as the uploaded files.
2. **Unlimited file count** — any number of PDFs can be submitted in a single request via the `files[]` field.
3. **pikepdf page-level control** — each page is copied individually, preserving embedded fonts, images, and annotations.
4. **UUID output filenames** — collision-free naming for every merged result; no overwriting of previous outputs.
5. **In-memory intermediary** — source files are read from werkzeug's temporary storage without writing unnecessary copies to disk.
6. **Graceful error handling** — malformed or password-protected PDFs return a structured JSON error without crashing the service.
7. **Stateless processing** — no session state is stored; each request is fully self-contained.
8. **Flask-native file handling** — uses `request.files.getlist` for multi-file extraction, keeping the route handler minimal and readable.

---

## How It Works

1. The route handler reads all uploaded files via `request.files.getlist("files[]")`.
2. A new empty `pikepdf.Pdf` object is created as the output container.
3. For each uploaded file, `pikepdf.Pdf.open(file.stream)` opens the PDF directly from the in-memory stream.
4. Every page in the source PDF is appended to the output PDF using `output.pages.extend(source.pages)`.
5. After all source files are processed, the output PDF is saved to the configured output directory using a UUID filename (`uuid4().hex + ".pdf"`).
6. The saved file is returned to the client via Flask's `send_file` with `as_attachment=True`.

---

## Input

| Field     | Type              | Required | Description                                                      |
|-----------|-------------------|----------|------------------------------------------------------------------|
| `files[]` | `multipart/file`  | Yes      | Two or more PDF files. Submit as a multi-select file input. Files are merged in upload order. |

**Example curl request:**

```bash
curl -X POST http://localhost:5000/pdf/merge \
  -F "files[]=@doc1.pdf" \
  -F "files[]=@doc2.pdf" \
  -F "files[]=@doc3.pdf" \
  --output merged.pdf
```

---

## Output

| Property        | Value                                      |
|-----------------|--------------------------------------------|
| Content-Type    | `application/pdf`                          |
| Disposition     | `attachment; filename=<uuid>.pdf`          |
| Body            | Binary PDF — all source pages concatenated |

On error, a JSON response is returned instead:

```json
{ "error": "<description>" }
```

---

## Libraries

| Library      | Role                                                              |
|--------------|-------------------------------------------------------------------|
| `pikepdf`    | Opens source PDFs and appends pages to the output PDF document.  |
| `Flask`      | HTTP routing, request parsing, and file response via `send_file`. |
| `werkzeug`   | Multipart file handling; provides the `FileStorage` stream object.|

---

## Configuration

| Setting          | Default              | Description                                       |
|------------------|----------------------|---------------------------------------------------|
| Output directory | `outputs/pdf/`       | Directory where merged PDFs are saved to disk.    |
| Max content size | Flask default (16 MB)| Override with `MAX_CONTENT_LENGTH` in app config. |
| Filename pattern | `uuid4().hex + .pdf` | Ensures unique filenames across all merge jobs.   |

---

## Tips

1. **Upload order matters** — arrange files in the desired reading order before submitting; the merge respects upload sequence exactly.
2. **Increase size limits for large files** — set `app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024` for batches exceeding 16 MB.
3. **Avoid password-protected PDFs** — pikepdf will raise a `PasswordError`; decrypt files before uploading or handle the exception to return a user-friendly message.
4. **Check page count before merging** — submitting a zero-page or corrupt PDF causes an empty page range; validate each source after opening.
5. **Clean up output files** — UUID files accumulate on disk; implement a scheduled cleanup job or serve files and delete them immediately after download.

---

## Error Handling

| Scenario                        | HTTP Status | Response Body                              |
|---------------------------------|-------------|--------------------------------------------|
| No files provided               | `400`       | `{ "error": "No files uploaded" }`         |
| Fewer than two files            | `400`       | `{ "error": "At least two PDFs required" }`|
| File is not a valid PDF         | `400`       | `{ "error": "Invalid PDF: <filename>" }`   |
| Password-protected PDF          | `400`       | `{ "error": "PDF is encrypted: <filename>" }` |
| Unexpected server-side failure  | `500`       | `{ "error": "Merge failed: <detail>" }`    |

---

## Code Location

| Artifact            | Path                                      |
|---------------------|-------------------------------------------|
| Route handler       | `app/routes/pdf/merge_pdf.py`             |
| Blueprint register  | `app/routes/pdf/__init__.py`              |
| Output directory    | `outputs/pdf/`                            |
| This documentation  | `docs/pdf/merge-pdf.md`                   |
