# Split CSV

**Route:** `POST /split`
**Category:** CSV Tools
**Returns:** ZIP archive (`.zip`)

---

## Overview

The Split CSV tool accepts a CSV file and a target row count, then divides the file into
equally-sized chunks. Each chunk is written as a separate CSV file with the original header
row preserved. All parts are bundled into a ZIP archive and returned for download. This tool
is useful for breaking large CSV exports into manageable segments for batch processing,
database imports, or distribution across workers.

---

## Key Features

1. Splits any valid CSV into N-row chunks with a single POST request.
2. Preserves the original header row in every output part file.
3. Merges trailing rows (fewer than `MIN_ROWS_PER_FILE`) into the final part to avoid
   undersized fragments.
4. Clears stale output files on each run by removing and recreating the split directory.
5. Returns all parts as a single ZIP archive — no intermediate downloads required.
6. Part files are named deterministically: `{filename}_part_1.csv`, `{filename}_part_2.csv`, …
7. Configurable defaults via `DEFAULT_ROWS_PER_SPLIT` and `MIN_ROWS_PER_FILE`.
8. Uses the Python standard library (`csv`, `zipfile`, `shutil`) — no external dependencies.

---

## How It Works

When a request arrives at `POST /split`, the route reads the uploaded CSV file using
Python's `csv.reader`. It extracts the header row from the first line, then buffers
subsequent data rows into chunks of `row_count` size. Before writing any output, the
route builds a split directory named after the uploaded filename and calls
`shutil.rmtree` on it to remove any files left over from a previous run, then
recreates the directory cleanly. Each full chunk is written to a new part file using
`csv.writer`, with the header prepended. If the final remaining batch contains fewer
rows than `MIN_ROWS_PER_FILE`, those rows are appended to the last completed part
rather than written to a new file. Once all parts are written, `zipfile.ZipFile` is
used to bundle every part file into `{filename}_splits.zip`. The ZIP is returned
directly as the HTTP response with `Content-Disposition: attachment`.

---

## Input

| Field        | Type    | Required | Description                                              |
|--------------|---------|----------|----------------------------------------------------------|
| `file`       | File    | Yes      | CSV file to split. Must include a header row.            |
| `row_count`  | Integer | Yes      | Number of data rows per output chunk (min `MIN_ROWS_PER_FILE`). |

> `row_count` must be a positive integer. Values below `MIN_ROWS_PER_FILE` (default: 10)
> are rejected with a 400 error.

---

## Output

| Property             | Value                                      |
|----------------------|--------------------------------------------|
| Content-Type         | `application/zip`                          |
| Content-Disposition  | `attachment; filename={filename}_splits.zip` |
| Archive contents     | `{filename}_part_1.csv` … `{filename}_part_N.csv` |
| Header row           | Included in every part file                |

---

## Libraries

| Library    | Purpose                                          | Source           |
|------------|--------------------------------------------------|------------------|
| `csv`      | Reading the uploaded file; writing part files    | Python stdlib    |
| `zipfile`  | Bundling all part files into a single archive    | Python stdlib    |
| `shutil`   | Removing the stale split directory before a run  | Python stdlib    |
| `os`       | Directory creation and path manipulation         | Python stdlib    |
| `flask`    | Route handling, request parsing, file response   | Third-party      |

---

## Configuration

These values are set in the application configuration (e.g., `config.py` or environment
variables) and control splitting behaviour:

| Config Key              | Default | Description                                                   |
|-------------------------|---------|---------------------------------------------------------------|
| `DEFAULT_ROWS_PER_SPLIT`| `1000`  | Row count used when `row_count` is not supplied by the client.|
| `MIN_ROWS_PER_FILE`     | `10`    | Minimum rows a final part must have; smaller remainders are   |
|                         |         | merged into the preceding part instead of written separately. |

---

## Usage Tips

1. **Large files:** For CSVs with millions of rows, keep `row_count` at or above 10,000
   to avoid generating hundreds of small part files.
2. **Consistent headers:** The tool reads the header from row 0. If your CSV has no
   header, prepend one before uploading or the first data row will be treated as a header
   and will appear in every part file.
3. **Stale file cleanup:** The split directory is wiped on every request. Do not rely on
   files from a previous run persisting on the server.
4. **Part numbering:** Parts are numbered from 1 (`_part_1.csv`). If you need zero-based
   numbering for downstream tooling, rename files after extracting the ZIP.
5. **Row count vs. part count:** The tool controls rows per part, not total part count.
   To target N parts, divide the total row count by N and pass the result as `row_count`.

---

## Error Handling

| Condition                              | HTTP Status | Response                                      |
|----------------------------------------|-------------|-----------------------------------------------|
| No file attached to request            | 400         | `{"error": "No file provided"}`               |
| `row_count` missing or non-integer     | 400         | `{"error": "row_count must be a valid integer"}` |
| `row_count` below `MIN_ROWS_PER_FILE`  | 400         | `{"error": "row_count below minimum allowed"}`|
| File is empty or has no data rows      | 400         | `{"error": "CSV has no data rows to split"}`  |
| Server-side I/O failure                | 500         | `{"error": "Internal server error"}`          |

---

## Code Location

| Component         | Path                        | Description                          |
|-------------------|-----------------------------|--------------------------------------|
| Route handler     | `app/routes.py`             | `POST /split` — core split logic     |
| Configuration     | `config.py`                 | `DEFAULT_ROWS_PER_SPLIT`, `MIN_ROWS_PER_FILE` |
| Templates (UI)    | `app/templates/split.html`  | Upload form for the Split CSV tool   |
| Static assets     | `app/static/`               | Shared JS/CSS for the Toolkit UI     |

---

*Part of the [Toolkit](../../README.md) — a collection of file utility tools built with Flask.*
