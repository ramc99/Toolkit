# Reorder Pages

**Route:** `POST /pdf/reorder`

---

## Overview

The Reorder Pages tool allows users to rearrange the pages of a PDF file into any custom sequence. By supplying a comma-separated list of page numbers, the tool builds a new PDF with pages assembled in the specified order. This is useful for reorganizing documents, correcting scan order, moving appendices, or producing alternate versions of a report without manual editing.

---

## Features

1. **Custom page ordering** — Specify any arbitrary sequence of page numbers to define the exact output order.
2. **Full page preservation** — All page content, annotations, fonts, and embedded media are carried over intact via pikepdf.
3. **Repeat and duplicate pages** — A page number can appear more than once in the order string, producing duplicate pages in the output.
4. **Subset selection** — Omitting page numbers from the order string produces a trimmed PDF containing only the listed pages.
5. **Large document support** — Streams pages individually so memory usage stays flat regardless of document size.
6. **Original file unchanged** — The uploaded file is never modified; the reordered document is returned as a new file.
7. **1-based page indexing** — Page numbers follow the familiar human convention (first page = 1), reducing off-by-one errors.
8. **Fast in-memory processing** — No intermediate files are written to disk; the result is assembled and returned in a single pass.

---

## How It Works

1. The client sends a `multipart/form-data` POST request containing the PDF file and the desired page order string.
2. The server parses the order string, splitting on commas and converting each token to a zero-based index for pikepdf.
3. pikepdf opens the uploaded PDF as a `pikepdf.Pdf` object.
4. A new empty `pikepdf.Pdf` is created.
5. For each page number in the parsed order, the corresponding page from the source document is appended to the new PDF.
6. The new PDF is saved to an in-memory buffer and returned to the client as a downloadable file.

---

## Input Parameters

| Parameter | Type              | Required | Description                                                                                  |
|-----------|-------------------|----------|----------------------------------------------------------------------------------------------|
| `file`    | File (PDF)        | Yes      | The PDF file whose pages will be reordered. Must be a valid, non-encrypted PDF.              |
| `order`   | String            | Yes      | Comma-separated list of 1-based page numbers defining the desired output order (e.g. `3,1,2`). Duplicates are allowed. |

---

## Output

- **Content-Type:** `application/pdf`
- **Content-Disposition:** `attachment; filename="reordered.pdf"`
- The response body is the reordered PDF binary.
- Page count in the output equals the number of entries in the `order` parameter (which may differ from the original if pages are duplicated or omitted).

---

## Libraries

| Library   | Purpose                                                              |
|-----------|----------------------------------------------------------------------|
| `pikepdf` | Opens the source PDF, accesses individual pages, and writes the new document. Handles complex PDF structures including cross-reference streams and object streams. |

---

## Configuration

| Setting              | Default | Description                                                        |
|----------------------|---------|--------------------------------------------------------------------|
| `MAX_UPLOAD_SIZE`    | 50 MB   | Maximum accepted file size for the uploaded PDF.                   |
| `ALLOWED_EXTENSIONS` | `pdf`   | Only `.pdf` files are accepted; other formats are rejected.        |
| `OUTPUT_FILENAME`    | `reordered.pdf` | Default filename used in the Content-Disposition header.  |

---

## Tips

1. **Verify page count first** — Use the `/pdf/info` endpoint to check the total number of pages before constructing your order string, so you avoid referencing out-of-range page numbers.
2. **Duplicate pages for emphasis** — You can repeat a page number (e.g. `1,2,1,3`) to include that page multiple times in the output, which is handy for cover pages or repeated reference sheets.
3. **Create a subset PDF** — Supply only the page numbers you need (e.g. `2,4,6`) to extract a specific subset of pages into a new document.
4. **Combine with other tools** — Reorder pages after merging multiple PDFs with `/pdf/merge` to get the final sequence exactly right.
5. **Check for encryption** — pikepdf cannot reorder pages in password-protected PDFs. Decrypt the file first using `/pdf/unlock` before submitting to this endpoint.

---

## Error Responses

| HTTP Status | Error Code            | Description                                                                                 |
|-------------|-----------------------|---------------------------------------------------------------------------------------------|
| `400`       | `MISSING_FILE`        | No PDF file was included in the request.                                                    |
| `400`       | `MISSING_ORDER`       | The `order` parameter is absent or empty.                                                   |
| `400`       | `INVALID_ORDER`       | The order string contains non-numeric values or page numbers outside the document range.    |
| `400`       | `ENCRYPTED_PDF`       | The uploaded PDF is password-protected and cannot be processed.                             |
| `500`       | `PROCESSING_ERROR`    | An unexpected error occurred while reading or writing the PDF. Check server logs for detail.|
