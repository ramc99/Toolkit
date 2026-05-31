# Extract Pages

**Route:** `POST /pdf/extract-pages`

---

## Overview

The Extract Pages tool lets you save a specific subset of pages from an existing PDF as a
standalone PDF file. Supply a source PDF and a comma-separated list of page numbers; the
tool opens the source with pikepdf, appends only the requested pages to a new PDF object,
and streams the resulting file back to the caller. No temporary files are written to disk
beyond the upload itself.

---

## Features

1. **Selective extraction** — choose any combination of pages in any order; duplicates are allowed.
2. **Original fidelity** — pikepdf copies pages at the object level, preserving fonts, images, and annotations exactly.
3. **Non-destructive** — the source PDF is never modified; extraction always produces a new file.
4. **Order control** — output pages appear in the exact sequence you specify, not source order.
5. **Large-file support** — pikepdf streams pages lazily, keeping memory usage flat regardless of source size.
6. **Single-page output** — extracting one page produces a valid single-page PDF, not a wrapper.
7. **Mixed range input** — accepts individual page numbers and comma-separated lists in one request.
8. **Instant download** — the extracted PDF is returned directly in the HTTP response with appropriate headers.

---

## How It Works

1. The uploaded PDF is saved to a temporary location on the server.
2. pikepdf opens the source file in read mode (`pikepdf.open`).
3. A new, empty `pikepdf.Pdf` object is created.
4. For each page number in the parsed `pages` list, the corresponding page is appended to
   the new PDF via `new_pdf.pages.append(source.pages[n - 1])` (1-based indexing).
5. The new PDF is saved to an in-memory `BytesIO` buffer.
6. The buffer is returned as a `application/pdf` response with a descriptive filename.
7. The temporary upload file is removed from disk after the response is sent.

---

## Input

| Field  | Type             | Required | Description                                                                 |
|--------|------------------|----------|-----------------------------------------------------------------------------|
| `file` | `multipart/form-data` | Yes | The source PDF file to extract pages from.                             |
| `pages` | `string`        | Yes      | Comma-separated 1-based page numbers, e.g. `1,3,5` or `2,2,4`.            |

### Example Request (curl)

```bash
curl -X POST http://localhost:5000/pdf/extract-pages \
  -F "file=@/path/to/source.pdf" \
  -F "pages=1,3,5" \
  --output extracted.pdf
```

---

## Output

| Property        | Value                                      |
|-----------------|--------------------------------------------|
| Content-Type    | `application/pdf`                          |
| Disposition     | `attachment; filename="extracted_pages.pdf"` |
| Body            | Binary PDF containing only the specified pages |

On success the response is the raw PDF binary. Save it directly to a file.

---

## Libraries

| Library   | Role                                                                 |
|-----------|----------------------------------------------------------------------|
| `pikepdf` | Opens source PDFs, copies page objects, writes the new PDF to buffer |
| `flask`   | HTTP routing, file upload handling, response streaming               |

Install: `pip install pikepdf flask`

---

## Configuration

No dedicated configuration keys are required. The following global Toolkit settings apply:

| Setting              | Default | Effect                                      |
|----------------------|---------|---------------------------------------------|
| `MAX_CONTENT_LENGTH` | 50 MB   | Maximum upload size enforced by Flask.      |
| `UPLOAD_FOLDER`      | `uploads/` | Temporary storage for the incoming file. |

---

## Tips

1. **Page order matters** — passing `pages=3,1,2` produces a PDF with pages in that exact
   sequence; use this to reorder a document without a separate reorder step.
2. **Repeat pages** — specifying `pages=1,1,1` creates a three-page PDF where the first
   page appears three times, useful for printing duplicates.
3. **Validate before sending** — if your client knows the page count, reject out-of-range
   numbers before the request to get a cleaner error message.
4. **Large PDFs** — pikepdf does not load the entire file into memory at open time; only
   the pages you request are fully decoded, so extraction from a 500-page PDF is fast.
5. **Preserve bookmarks** — if the source PDF has a bookmark that points to an extracted
   page, copy the outline manually after extraction; pikepdf does not carry bookmarks
   across automatically.

---

## Errors

| HTTP Status | Condition                                         | Resolution                                     |
|-------------|---------------------------------------------------|------------------------------------------------|
| `400`       | `file` field missing from request                 | Include the PDF as a `multipart/form-data` field named `file`. |
| `400`       | `pages` field missing or empty                    | Provide at least one page number.              |
| `400`       | `pages` contains non-integer values               | Use only positive integers separated by commas. |
| `400`       | A requested page number is out of range           | Check the source PDF page count and adjust.   |
| `500`       | pikepdf raises `PdfError` (corrupt or encrypted)  | Ensure the source PDF is valid and not password-protected. |
