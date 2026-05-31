# Convert CSV

## Route

`POST /csv-convert`

---

## Overview

The Convert CSV tool accepts an uploaded CSV file and a target format, then streams back the converted file without writing anything to disk. Supported output formats are **Excel** (`.xlsx`) and **JSON** (`.json`). The conversion is handled server-side using pandas, so clients receive a ready-to-use file in a single request.

---

## Key Features

1. **Zero disk I/O** — conversion uses an in-memory `BytesIO` buffer; no temporary files are created or left behind.
2. **Excel output via openpyxl** — produces a standards-compliant `.xlsx` workbook with correct MIME type (`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`).
3. **JSON output as records array** — serialises every row as a flat JSON object, indented for readability.
4. **Single-request workflow** — upload and receive the converted file in one `POST`; no polling or download step required.
5. **Automatic header detection** — pandas infers column names from the first row of the CSV automatically.
6. **Streaming response** — Flask sends the `BytesIO` buffer directly, keeping memory usage proportional to file size.
7. **MIME-typed responses** — each format returns the correct `Content-Type` and `Content-Disposition` header so browsers trigger a file download.
8. **Minimal configuration** — no environment variables or database connections required; the route is self-contained.

---

## How It Works

1. The client sends a `multipart/form-data` `POST` to `/csv-convert` with two fields:
   - `file` — the CSV file.
   - `format` — either `excel` or `json`.
2. Flask receives the upload via `request.files['file']`.
3. pandas reads the file stream with `pd.read_csv()`, producing a `DataFrame`.
4. **Excel path**
   - A `BytesIO` buffer is created.
   - `DataFrame.to_excel(buffer, index=False, engine='openpyxl')` writes the workbook into the buffer.
   - The buffer is seeked back to position `0`.
   - Flask returns the buffer with `mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'` and a `.xlsx` filename.
5. **JSON path**
   - `DataFrame.to_json(orient='records', indent=2)` produces a UTF-8 string.
   - Flask returns the string with `mimetype='application/json'` and a `.json` filename.
6. The `Content-Disposition: attachment` header ensures the file is downloaded rather than rendered in the browser.

---

## Input

| Field    | Type              | Required | Description                                      |
|----------|-------------------|----------|--------------------------------------------------|
| `file`   | File (CSV)        | Yes      | The CSV file to convert. Must be valid CSV.      |
| `format` | String (`excel` or `json`) | Yes | Target output format.                  |

The request must use `enctype="multipart/form-data"` (or equivalent in API clients such as curl `--form`).

---

## Output

| Format  | MIME Type                                                          | Extension | Structure                                   |
|---------|--------------------------------------------------------------------|-----------|---------------------------------------------|
| `excel` | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` | `.xlsx`   | Single worksheet; first row contains headers. |
| `json`  | `application/json`                                                 | `.json`   | Array of objects, one per CSV row; keys are column headers. |

---

## Libraries

| Library    | Version Constraint | Purpose                                     |
|------------|--------------------|---------------------------------------------|
| `pandas`   | `>=1.5`            | CSV parsing and DataFrame-to-format conversion. |
| `openpyxl` | `>=3.0`            | Excel `.xlsx` write engine used by pandas.  |
| `io`       | stdlib             | `BytesIO` in-memory buffer for Excel output. |

---

## Configuration

No additional environment variables are required. The route relies only on Flask's built-in request handling and the libraries listed above. Ensure both `pandas` and `openpyxl` are present in `requirements.txt`.

---

## Usage Tips

1. **Large files** — pandas loads the entire CSV into memory. For files larger than ~50 MB consider chunked processing or a background task queue.
2. **Encoding** — `pd.read_csv()` defaults to UTF-8. If your CSV uses a different encoding (e.g. `latin-1`), pre-process or detect encoding client-side before uploading.
3. **curl example**
   ```bash
   curl -X POST http://localhost:5000/csv-convert \
     -F "file=@data.csv" \
     -F "format=excel" \
     --output converted.xlsx
   ```
4. **Verifying the response** — check the `Content-Disposition` header in the response to confirm the filename and format before saving programmatically.
5. **Column types** — pandas infers column data types. Numeric columns will be stored as numbers in Excel, which may affect formatting. Cast columns explicitly in a pre-processing step if strict types are required.

---

## Error Handling

| Scenario                        | Behaviour                                                     |
|---------------------------------|---------------------------------------------------------------|
| Missing `file` field            | Flask raises `400 Bad Request`.                               |
| Missing or invalid `format`     | Route returns `400` with a descriptive error message.         |
| Malformed CSV                   | pandas raises `ParserError`; the route should catch and return `422 Unprocessable Entity`. |
| Empty CSV (no rows)             | Returns a valid but empty workbook or empty JSON array `[]`.  |
| openpyxl not installed          | pandas raises `ModuleNotFoundError` at runtime; install `openpyxl`. |

---

## Code Location

| Artefact        | Path                  |
|-----------------|-----------------------|
| Route handler   | `app/routes.py`       |
| Flask app entry | `app/__init__.py`     |
| Dependencies    | `requirements.txt`    |
