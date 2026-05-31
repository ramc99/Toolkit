# Split PDF

**Route:** `POST /pdf/split`

## Overview

The Split PDF tool divides a single PDF document into multiple smaller PDFs. It supports two distinct modes: splitting every N pages into equal-sized chunks, or splitting by custom page ranges defined as a comma-separated expression (e.g. `1-3,5,7-9`). Each output part is written as an independent PDF file with a UUID-based name, and all parts are packaged into a single ZIP archive returned to the caller.

---

## Features

- **Even-chunk splitting** — divide a PDF into equal segments of N pages each.
- **Custom range splitting** — extract arbitrary page sets using range notation (e.g. `1-3,5,7-9`).
- **Range parser** — handles mixed single pages and hyphenated ranges in any order.
- **UUID-named outputs** — every part file receives a unique name to prevent collisions.
- **ZIP packaging** — all parts are bundled into one `.zip` for a single download.
- **Zero-index normalization** — user-facing page numbers are 1-based; internally converted for pikepdf.
- **Boundary safety** — page numbers exceeding the document length are clamped and reported.
- **In-memory ZIP assembly** — archive is built in a `BytesIO` buffer; no temporary disk writes for the ZIP itself.

---

## How It Works

### Mode 1 — Split Every N Pages

1. pikepdf opens the uploaded PDF and reads the total page count.
2. The page list is sliced into consecutive chunks of size `every` (the last chunk may be smaller).
3. Each chunk is written to a new `pikepdf.Pdf` object and saved to a temp file named `<uuid>.pdf`.
4. All temp files are added to a `zipfile.ZipFile` buffer.
5. The buffer is returned as `application/zip`.

### Mode 2 — Custom Page Ranges

1. The `ranges` string (e.g. `1-3,5,7-9`) is tokenized on commas.
2. Each token is evaluated: a hyphenated token expands to a list of consecutive pages; a bare integer becomes a single-page list.
3. Duplicate or out-of-order pages within a token are preserved as supplied.
4. Each resolved list is treated as one output part and follows the same UUID + ZIP pipeline as Mode 1.

---

## Input

| Field    | Type          | Required | Description                                                                 |
|----------|---------------|----------|-----------------------------------------------------------------------------|
| `file`   | `multipart`   | Yes      | The PDF file to split. Must be a valid PDF readable by pikepdf.             |
| `mode`   | `string`      | Yes      | `"every"` for equal-chunk splitting, or `"ranges"` for custom page ranges.  |
| `every`  | `integer`     | No*      | Number of pages per chunk. Required when `mode` is `"every"`. Min value: 1. |
| `ranges` | `string`      | No*      | Comma-separated page range string (e.g. `1-3,5,7-9`). Required when `mode` is `"ranges"`. Pages are 1-indexed. |

\* Exactly one of `every` or `ranges` must be supplied depending on the chosen mode.

---

## Output

A `200 OK` response with `Content-Type: application/zip` containing:

```
split_parts.zip
├── <uuid-1>.pdf   # Part 1
├── <uuid-2>.pdf   # Part 2
└── <uuid-n>.pdf   # Part N
```

Each PDF inside the ZIP is a self-contained, valid PDF document.

---

## Libraries

| Library    | Role                                                             |
|------------|------------------------------------------------------------------|
| `pikepdf`  | Opens the source PDF, reads pages, constructs and saves output parts. |
| `zipfile`  | Assembles all part files into a single in-memory ZIP archive.    |
| `uuid`     | Generates collision-free filenames for each output PDF part.     |
| `io`       | Provides the `BytesIO` buffer used for in-memory ZIP assembly.   |

---

## Configuration

| Parameter        | Default | Notes                                              |
|------------------|---------|----------------------------------------------------|
| Max upload size  | 50 MB   | Enforced at the Flask layer before pikepdf opens the file. |
| Max parts        | 100     | Requests that would produce more than 100 parts are rejected with `400`. |
| Temp directory   | `TMPDIR` | Part PDFs are written here before ZIP assembly; cleaned up after response. |

---

## Tips

1. **Use `ranges` for selective extraction** — if you only need pages 1, 5, and 10, supply `ranges=1,5,10` rather than splitting the whole file and discarding unwanted parts.
2. **Reverse ranges are valid** — `9-7` is parsed as pages 9, 8, 7 in that order, which can be useful for reordering.
3. **Single-page PDFs are fine** — `every=1` produces one PDF per page; useful for converting a scanned multi-page document into individual image-backed PDFs.
4. **Check page count first** — use the `/pdf/info` endpoint to retrieve total page count before building a `ranges` string so you avoid out-of-bounds errors.
5. **ZIP filenames are UUIDs** — if you need human-readable names, rename the entries after extraction; the order of files in the ZIP matches the order of parts as split.

---

## Errors

| HTTP Status | Code                  | Cause                                                          |
|-------------|-----------------------|----------------------------------------------------------------|
| `400`       | `MISSING_FILE`        | No file was attached to the request.                           |
| `400`       | `INVALID_MODE`        | `mode` is not `"every"` or `"ranges"`.                         |
| `400`       | `MISSING_PARAM`       | `every` not provided for mode `every`, or `ranges` not provided for mode `ranges`. |
| `400`       | `INVALID_RANGE`       | A token in the `ranges` string is not a valid integer or hyphenated pair. |
| `400`       | `OUT_OF_BOUNDS`       | A page number in `ranges` exceeds the document's page count.   |
| `422`       | `CORRUPT_PDF`         | pikepdf could not open or parse the uploaded file.             |
| `500`       | `SPLIT_FAILED`        | An unexpected error occurred during page extraction or ZIP assembly. |
