# Delete Pages

**Route:** `POST /pdf/delete-pages`
**Category:** PDF Tools
**Library:** pikepdf

---

## Overview

The Delete Pages tool removes one or more specified pages from an uploaded PDF file and returns a clean, repackaged PDF containing only the retained pages. It accepts a comma-separated list of 1-indexed page numbers, converts them to 0-indexed positions internally, and deletes them in reverse order to keep all remaining page indices valid throughout the operation. The output is saved to a UUID-named file to prevent collisions across concurrent requests.

---

## Features

1. **Arbitrary page selection** — remove any combination of pages in a single request; no need to send the file multiple times.
2. **1-indexed input** — page numbers match what users see in PDF viewers (page 1 is the first page), eliminating off-by-one confusion.
3. **Reverse-order deletion** — pages are removed from the highest index to the lowest so earlier indices stay stable during the loop.
4. **UUID output naming** — each processed file is written to a unique filename, making concurrent use safe with no overwrites.
5. **Full PDF fidelity** — pikepdf preserves fonts, images, annotations, and metadata on all retained pages.
6. **Duplicate input handling** — repeated page numbers in the input are deduplicated before processing to avoid index errors.
7. **Out-of-range validation** — page numbers exceeding the document's actual page count are rejected with a descriptive error before any modification is attempted.
8. **In-memory safe** — the original uploaded file is never modified; all changes are written to a separate output path.

---

## How It Works

1. The uploaded PDF is received via a multipart form `POST` request alongside a `pages` string such as `"1,3,5"`.
2. The pages string is split, stripped, and parsed into a list of integers.
3. Each integer is converted from 1-indexed (user-facing) to 0-indexed (internal) by subtracting 1.
4. Duplicates are removed and the list is sorted in descending order.
5. pikepdf opens the PDF and iterates the sorted index list, calling `del pdf.pages[i]` for each entry. Descending order guarantees that deleting index `n` does not shift the position of any lower index still pending removal.
6. The modified PDF is saved to `outputs/<uuid>.pdf`.
7. The output file path (or a download response) is returned to the caller.

---

## Input

| Field  | Type            | Required | Description                                                                 |
|--------|-----------------|----------|-----------------------------------------------------------------------------|
| `file` | `multipart/form-data` (PDF) | Yes | The source PDF file to process. |
| `pages` | `string` | Yes | Comma-separated 1-indexed page numbers to delete (e.g. `"2,4,7"`). Spaces around commas are ignored. |

**Example request (curl):**

```bash
curl -X POST http://localhost:5000/pdf/delete-pages \
  -F "file=@document.pdf" \
  -F "pages=1,3,5"
```

---

## Output

On success the endpoint returns the processed PDF as a file download with the following characteristics:

- **Content-Type:** `application/pdf`
- **Filename:** A UUID-based name (e.g. `f3a1bc72-...pdf`) to avoid caching conflicts.
- **Content:** The original PDF with all specified pages removed and remaining pages renumbered sequentially.

---

## Libraries

| Library  | Role                                                                 |
|----------|----------------------------------------------------------------------|
| `pikepdf` | Opens, modifies, and saves PDF files; provides direct page-list access via `pdf.pages`. |
| `uuid`    | Generates a unique filename for each output file.                   |
| `os` / `pathlib` | Resolves upload and output directory paths.               |

---

## Configuration

| Setting         | Default        | Description                                          |
|-----------------|----------------|------------------------------------------------------|
| `UPLOAD_FOLDER` | `uploads/`     | Temporary directory where the incoming file is saved before processing. |
| `OUTPUT_FOLDER` | `outputs/`     | Directory where the processed PDF is written.        |
| `MAX_CONTENT_LENGTH` | `50 MB`   | Maximum accepted upload size; configurable in Flask app config. |

---

## Tips

1. **Verify page count first** — use the `/pdf/info` endpoint (if available) to confirm total page count before submitting delete requests to avoid out-of-range errors.
2. **Delete ranges efficiently** — to remove pages 3 through 7, pass `"3,4,5,6,7"` rather than sending five separate requests.
3. **Keep a backup** — the tool does not alter the original file, but retain your source PDF in case you need to re-run with a corrected page list.
4. **Use 1-based numbering** — always count pages as they appear in your PDF reader; internally the tool handles the conversion to 0-based indices.
5. **Large files** — for PDFs with hundreds of pages, increasing `MAX_CONTENT_LENGTH` and adjusting the server timeout prevents premature request termination.

---

## Errors

| HTTP Status | Cause                                                              | Resolution                                             |
|-------------|--------------------------------------------------------------------|--------------------------------------------------------|
| `400 Bad Request` | `pages` field is missing or empty.                        | Include a non-empty `pages` value in the form data.    |
| `400 Bad Request` | A page number is not a valid integer (e.g. `"2,abc,4"`). | Ensure all values in the comma list are positive integers. |
| `400 Bad Request` | A page number is less than 1 or exceeds the PDF's page count. | Check document length and correct the page list.      |
| `415 Unsupported Media Type` | Uploaded file is not a valid PDF.             | Confirm the file has a `.pdf` extension and valid PDF structure. |
| `500 Internal Server Error` | pikepdf failed to open or write the file.   | Check server logs; the PDF may be encrypted or corrupted. |
