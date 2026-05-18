# CSV Split & Merge

A lightweight Flask web app for splitting large CSV files into smaller chunks and merging multiple CSV/TSV files into one.

## Features

- **Split** — upload a CSV, choose rows-per-file, download a ZIP of all parts
- **Merge** — upload multiple CSV or TSV files, get a single combined file (CSV, TSV, or PDF)
- PDF output truncates at 500 rows for performance; full data available via CSV/TSV
- Tiny leftovers (< 10 rows) are appended to the last split part instead of creating a micro-file

## Stack

| Layer | Tech |
|-------|------|
| Backend | Python 3.11+ / Flask 3.x |
| Data processing | pandas 2.x |
| PDF generation | fpdf |

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

App runs at `http://127.0.0.1:5000`.

## Project layout

```
app/
  __init__.py      # app factory
  routes.py        # split + merge endpoints
  templates/
    base.html      # layout, styles, header
    index.html     # split & merge forms
config.py          # upload/split/merge folders, limits
run.py             # dev entry point
requirements.txt
```

## Configuration

Edit `config.py` to change:

| Key | Default | Description |
|-----|---------|-------------|
| `DEFAULT_ROWS_PER_SPLIT` | 1000 | Rows per split file |
| `MIN_ROWS_PER_FILE` | 10 | Minimum rows before merging leftovers |
| `ALLOWED_EXTENSIONS` | csv, tsv | Accepted upload types |
