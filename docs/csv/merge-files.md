# Merge Files

**Route:** `POST /merge`
**Category:** CSV Tools
**Location:** `app/routes.py`

---

## Overview

The Merge Files tool combines two or more CSV or TSV files into a single unified output file. It performs a vertical union (row-wise concatenation) across all uploaded files, automatically aligning columns by name and filling any missing values with empty strings. The merged result can be downloaded as CSV, TSV, or PDF.

---

## Key Features

1. **Multi-file upload** — Accepts any number of CSV or TSV files in a single request.
2. **Automatic separator detection** — Detects the delimiter based on file extension (`.tsv` uses tab, `.csv` uses comma); no manual configuration required.
3. **Column union merging** — All unique columns across every file are preserved in the output, regardless of which file they originated from.
4. **Missing value safety** — Cells that have no corresponding column in a given source file are filled with an empty string, never `NaN`.
5. **Multiple output formats** — Returns the merged result as CSV (default), TSV, or a formatted PDF document.
6. **Non-destructive ordering** — Column order from the first file is preserved; new columns from subsequent files are appended without sorting.
7. **Index-clean output** — Row indices are reset after concatenation, producing a clean zero-based integer index in the output.
8. **Persistent output file** — The merged file is written to `MERGE_FOLDER` as `merged_output.{format}`, making it retrievable after the request completes.

---

## How It Works

### 1. File Reception

The route accepts a `multipart/form-data` POST request. The `files` field must contain at least two file objects. An optional `format` field specifies the desired output format (`csv`, `tsv`, or `pdf`); it defaults to `csv` if omitted.

### 2. Separator Auto-Detection

Each uploaded file is inspected by its extension:

```python
sep = '\t' if filename.endswith('.tsv') else ','
df = pd.read_csv(file, sep=sep, keep_default_na=False)
```

This ensures TSV files are parsed correctly without user intervention.

### 3. Concatenation

All individual DataFrames are collected into a list and merged with pandas `concat`:

```python
merged = pd.concat(frames, axis=0, ignore_index=True, sort=False)
```

- `axis=0` stacks rows vertically.
- `ignore_index=True` resets row indices to a clean sequence.
- `sort=False` preserves the original column order rather than sorting alphabetically.

### 4. Output Generation

The merged DataFrame is written to `MERGE_FOLDER/merged_output.{format}`:

- **CSV** — `merged.to_csv(..., index=False)`
- **TSV** — `merged.to_csv(..., sep='\t', index=False)`
- **PDF** — Rendered using `fpdf`, with a header row and one row per record, using the `FPDF` class with `add_page()` and `cell()` calls.

The file is then served back to the client as a downloadable attachment.

---

## Input Parameters

| Parameter | Type            | Required | Description                                          |
|-----------|-----------------|----------|------------------------------------------------------|
| `files`   | File (multiple) | Yes      | Two or more `.csv` or `.tsv` files to merge          |
| `format`  | String          | No       | Output format: `csv` (default), `tsv`, or `pdf`      |

---

## Output

A single downloadable file containing all rows from every uploaded file, with columns unified across all sources. The filename is `merged_output.csv`, `merged_output.tsv`, or `merged_output.pdf` depending on the chosen format.

Missing column values (where a source file did not contain a given column) appear as empty strings in the output.

---

## Libraries

| Library   | Purpose                                             |
|-----------|-----------------------------------------------------|
| `pandas`  | DataFrame creation, CSV/TSV parsing, concatenation  |
| `fpdf`    | PDF rendering of the merged tabular data            |
| `csv`     | Used for any supplementary CSV writing utilities    |
| `flask`   | Route handling, request parsing, file response      |

---

## Configuration

| Setting        | Description                                                     |
|----------------|-----------------------------------------------------------------|
| `MERGE_FOLDER` | Filesystem path where `merged_output.{format}` is written       |

Set `MERGE_FOLDER` in your Flask application config or environment before starting the server. The folder must be writable by the application process.

---

## Usage Tips

1. **Column name consistency** — Ensure column headers use the same spelling and casing across files. `Name` and `name` are treated as different columns.
2. **Mixed formats** — You can mix `.csv` and `.tsv` files in a single request; each file's separator is detected independently.
3. **Large files** — For files with hundreds of thousands of rows, the PDF output format is not recommended due to rendering overhead. Use CSV or TSV instead.
4. **Header requirement** — Every uploaded file must include a header row. Files without headers will cause the first data row to be treated as column names.
5. **Duplicate rows** — The tool performs a union concatenation; it does not deduplicate rows. If the same row appears in multiple files, it will appear multiple times in the output.

---

## Error Handling

| Scenario                          | Behavior                                              |
|-----------------------------------|-------------------------------------------------------|
| Fewer than two files uploaded     | Returns a `400 Bad Request` with a descriptive message |
| Unsupported file extension        | File is rejected; error message returned to client    |
| Malformed CSV/TSV content         | `pandas` raises a parse error; `500` is returned      |
| Invalid `format` value            | Defaults to `csv` or returns a `400` validation error |
| `MERGE_FOLDER` not writable       | Server-side `IOError`; `500` is returned              |

---

## Code Location

- **Route handler:** `app/routes.py` — `POST /merge`
- **Output directory config:** `app/config.py` or environment variable `MERGE_FOLDER`
- **PDF rendering logic:** inline within the route handler using `fpdf.FPDF`
