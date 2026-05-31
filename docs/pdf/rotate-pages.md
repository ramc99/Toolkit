# Rotate Pages

**Route:** `POST /pdf/rotate`

## Overview

The Rotate Pages tool rotates all or selected pages of an uploaded PDF by a specified angle. It uses `pikepdf` to manipulate each page's `/Rotate` key directly in the page dictionary, producing a properly oriented output PDF saved under a UUID filename.

---

## Features

1. **Flexible page targeting** — rotate every page at once or supply a comma-separated list of 1-indexed page numbers.
2. **Standard rotation angles** — supports 90, 180, and 270 degree clockwise rotations.
3. **Cumulative rotation** — the new angle is added to any existing `/Rotate` value on the page, so prior orientation is preserved.
4. **Non-destructive output** — the original upload is never modified; output is written to a fresh UUID-named file.
5. **Multi-page PDF support** — handles PDFs of any length without loading full page images into memory.
6. **Preserves all metadata** — document-level metadata, bookmarks, and annotations are carried through untouched.
7. **Selective rotation** — pages not in the selection list remain at their original orientation.
8. **Clean error reporting** — invalid page numbers and unsupported angles return structured JSON error responses.

---

## How It Works

1. The client sends a `multipart/form-data` POST with the PDF file, a rotation `angle`, and an optional `pages` selector.
2. Flask receives and temporarily stores the upload.
3. `pikepdf.open()` loads the PDF into memory.
4. The tool iterates over `pdf.pages`. For each page, it checks whether the page index is in the target set.
5. For targeted pages, it reads the current `/Rotate` value (defaulting to `0` if absent) and adds the requested angle, normalising the result to the range `[0, 360)`.
6. The updated angle is written back to `page["/Rotate"]`.
7. The modified PDF is saved to `outputs/<uuid>.pdf` via `pdf.save()`.
8. The server responds with the output filename and a download URL.

---

## Input Parameters

| Parameter | Type            | Required | Description                                                                 |
|-----------|-----------------|----------|-----------------------------------------------------------------------------|
| `file`    | `file` (binary) | Yes      | The PDF file to rotate. Sent as `multipart/form-data`.                      |
| `angle`   | `integer`       | Yes      | Clockwise rotation in degrees. Accepted values: `90`, `180`, `270`.        |
| `pages`   | `string`        | No       | `"all"` (default) or a comma-separated list of 1-indexed page numbers, e.g. `"1,3,5"`. |

---

## Output

A JSON object is returned on success:

```json
{
  "success": true,
  "filename": "3f7a1c92-bd44-4e10-a801-df28e4c0b123.pdf",
  "download_url": "/download/3f7a1c92-bd44-4e10-a801-df28e4c0b123.pdf",
  "pages_rotated": 4,
  "angle": 90
}
```

The output file is available at the returned `download_url` until the server's temp-file cleanup cycle runs.

---

## Libraries

| Library    | Role                                                                 |
|------------|----------------------------------------------------------------------|
| `pikepdf`  | Opens, iterates, and mutates PDF page dictionaries; saves output.   |
| `uuid`     | Generates a unique filename for each output file.                   |
| `Flask`    | Handles HTTP routing, file upload parsing, and JSON responses.      |

---

## Configuration

| Setting              | Default         | Description                                              |
|----------------------|-----------------|----------------------------------------------------------|
| `UPLOAD_FOLDER`      | `uploads/`      | Temporary storage for incoming PDF uploads.              |
| `OUTPUT_FOLDER`      | `outputs/`      | Destination folder for rotated PDF files.                |
| `MAX_CONTENT_LENGTH` | `50 MB`         | Maximum allowed upload size enforced by Flask.           |
| `ALLOWED_EXTENSIONS` | `{'pdf'}`       | Only `.pdf` files are accepted.                          |

---

## Tips

1. **Combining rotations** — submit the same file twice with different `pages` selectors and angles to achieve mixed-rotation documents.
2. **Checking current orientation** — if pages appear already rotated on upload, the tool compounds rather than overrides; use angle `270` to undo a prior `90` rotation.
3. **Large files** — `pikepdf` streams pages lazily, so even hundred-page PDFs complete quickly without running out of memory.
4. **1-indexed pages** — the `pages` parameter uses human-readable numbering starting at `1`, not `0`; submitting `"0"` will return a validation error.
5. **Download promptly** — output files are stored temporarily; download the result before the server's cleanup job removes stale files (default TTL: 1 hour).

---

## Error Responses

| HTTP Status | `error` Value            | Cause                                                       |
|-------------|--------------------------|-------------------------------------------------------------|
| `400`       | `no_file`                | No file field in the request.                               |
| `400`       | `invalid_extension`      | Uploaded file is not a `.pdf`.                              |
| `400`       | `invalid_angle`          | `angle` is not one of `90`, `180`, or `270`.               |
| `400`       | `invalid_page_number`    | A value in `pages` is out of range or non-numeric.          |
| `500`       | `processing_error`       | `pikepdf` raised an exception while reading or saving.      |
