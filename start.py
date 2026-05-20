"""Single-file launcher for CSV Split & Merge. Run with: python start.py"""
import csv
import io
import os
import secrets
import threading
import webbrowser
import zipfile

import pandas as pd
from flask import Flask, abort, flash, render_template_string, request, send_file
from fpdf import FPDF
from werkzeug.utils import secure_filename

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
SPLIT_FOLDER  = os.path.join(BASE_DIR, "splits")
MERGE_FOLDER  = os.path.join(BASE_DIR, "merged")
ALLOWED_EXTENSIONS      = {"csv", "tsv"}
MIN_ROWS_PER_FILE       = 10
DEFAULT_ROWS_PER_SPLIT  = 1000
MAX_CONTENT_LENGTH      = 50 * 1024 * 1024
PORT = 5000

# ── Embedded template ─────────────────────────────────────────────────────────
TEMPLATE = """<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>CSV Split &amp; Merge</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
    <style>
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        :root {
            --bg:        #f1f4f9;
            --surface:   #ffffff;
            --border:    #dde3ef;
            --primary:   #4a6cf7;
            --primary-h: #3a5ce5;
            --success:   #2a9d63;
            --text:      #1a2035;
            --muted:     #64748b;
            --radius:    12px;
            --shadow:    0 2px 12px rgba(30,40,80,.08);
        }
        body { font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }
        header {
            background: var(--surface); border-bottom: 1px solid var(--border);
            padding: 0 2rem; height: 60px; display: flex; align-items: center; gap: .75rem;
            box-shadow: 0 1px 4px rgba(30,40,80,.06);
        }
        header .logo-icon {
            width: 34px; height: 34px; background: var(--primary); border-radius: 8px;
            display: flex; align-items: center; justify-content: center; color: #fff; font-size: .95rem;
        }
        header h1 { font-size: 1.05rem; font-weight: 600; color: var(--text); }
        header .badge {
            margin-left: auto; font-size: .72rem; font-weight: 500;
            background: #eef1fd; color: var(--primary); padding: .25rem .65rem; border-radius: 20px;
        }
        main { max-width: 900px; margin: 2.5rem auto; padding: 0 1.5rem; }
        .page-title { font-size: 1.55rem; font-weight: 700; margin-bottom: .35rem; }
        .page-subtitle { color: var(--muted); font-size: .9rem; margin-bottom: 2rem; }
        .flash-list { margin-bottom: 1.5rem; }
        .flash {
            display: flex; align-items: flex-start; gap: .65rem; padding: .85rem 1rem;
            background: #eafaf2; border: 1px solid #b6e8d0; border-left: 4px solid var(--success);
            border-radius: var(--radius); font-size: .875rem; color: #1a5c3a; margin-bottom: .5rem;
        }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; }
        @media (max-width: 640px) { .grid { grid-template-columns: 1fr; } }
        .card {
            background: var(--surface); border: 1px solid var(--border);
            border-radius: var(--radius); box-shadow: var(--shadow); padding: 1.75rem;
        }
        .card-icon {
            width: 44px; height: 44px; border-radius: 10px;
            display: flex; align-items: center; justify-content: center;
            font-size: 1.1rem; margin-bottom: 1rem;
        }
        .card-icon.split { background: #eef1fd; color: var(--primary); }
        .card-icon.merge { background: #edf9f3; color: var(--success); }
        .card h2 { font-size: 1rem; font-weight: 600; margin-bottom: .35rem; }
        .card p.desc { font-size: .825rem; color: var(--muted); margin-bottom: 1.25rem; line-height: 1.5; }
        .form-group { margin-bottom: 1rem; }
        label {
            display: block; font-size: .8rem; font-weight: 500; color: var(--muted);
            margin-bottom: .4rem; text-transform: uppercase; letter-spacing: .03em;
        }
        .file-zone {
            border: 2px dashed var(--border); border-radius: 10px; padding: 1.25rem;
            text-align: center; cursor: pointer; transition: border-color .2s, background .2s; position: relative;
        }
        .file-zone:hover { border-color: var(--primary); background: #f6f8ff; }
        .file-zone input[type="file"] {
            position: absolute; inset: 0; opacity: 0; cursor: pointer; width: 100%; height: 100%;
        }
        .file-zone .zone-icon { font-size: 1.5rem; color: var(--muted); margin-bottom: .4rem; }
        .file-zone .zone-text { font-size: .8rem; color: var(--muted); }
        .file-zone .zone-text strong { color: var(--primary); }
        .file-name { margin-top: .5rem; font-size: .78rem; color: var(--text); font-weight: 500; min-height: 1rem; }
        input[type="number"], select {
            width: 100%; padding: .55rem .75rem; border: 1px solid var(--border); border-radius: 8px;
            font-size: .875rem; font-family: inherit; color: var(--text); background: #fafbfd;
            transition: border-color .15s, box-shadow .15s; appearance: none; -webkit-appearance: none;
        }
        input[type="number"]:focus, select:focus {
            outline: none; border-color: var(--primary); box-shadow: 0 0 0 3px rgba(74,108,247,.12);
        }
        select {
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2364748b' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E");
            background-repeat: no-repeat; background-position: right .75rem center; padding-right: 2rem;
        }
        .btn {
            display: inline-flex; align-items: center; gap: .5rem;
            width: 100%; justify-content: center; padding: .65rem 1.25rem;
            border: none; border-radius: 8px; font-family: inherit; font-size: .875rem; font-weight: 600;
            cursor: pointer; transition: background .15s, transform .1s, box-shadow .15s; margin-top: .5rem;
        }
        .btn-primary { background: var(--primary); color: #fff; box-shadow: 0 2px 8px rgba(74,108,247,.25); }
        .btn-primary:hover { background: var(--primary-h); box-shadow: 0 4px 14px rgba(74,108,247,.35); }
        .btn-primary:active { transform: translateY(1px); }
        .btn-success { background: var(--success); color: #fff; box-shadow: 0 2px 8px rgba(42,157,99,.25); }
        .btn-success:hover { background: #228a55; box-shadow: 0 4px 14px rgba(42,157,99,.35); }
        .btn-success:active { transform: translateY(1px); }
        .divider {
            display: flex; align-items: center; gap: .75rem;
            color: var(--muted); font-size: .75rem; margin: 2rem 0 1.5rem;
        }
        .divider::before, .divider::after { content: ''; flex: 1; height: 1px; background: var(--border); }
        footer { text-align: center; color: var(--muted); font-size: .78rem; margin: 3rem 0 2rem; }
    </style>
</head>
<body>

<header>
    <div class="logo-icon"><i class="fa-solid fa-table-columns"></i></div>
    <h1>CSV Split &amp; Merge</h1>
    <span class="badge">v1.0</span>
</header>

<main>
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        <div class="flash-list">
          {% for msg in messages %}
            <div class="flash"><i class="fa-solid fa-circle-check"></i> {{ msg }}</div>
          {% endfor %}
        </div>
      {% endif %}
    {% endwith %}

    <p class="page-title">File Tools</p>
    <p class="page-subtitle">Split large CSVs into manageable chunks, or merge multiple files into one.</p>

    <div class="grid">

        <!-- Split Card -->
        <div class="card">
            <div class="card-icon split"><i class="fa-solid fa-scissors"></i></div>
            <h2>Split a CSV</h2>
            <p class="desc">Upload a CSV and choose how many rows each output file should contain. You'll get a ZIP of all the parts.</p>
            <form action="/split" method="post" enctype="multipart/form-data">
                <div class="form-group">
                    <label for="split-file">CSV file</label>
                    <div class="file-zone">
                        <input type="file" name="file" id="split-file" accept=".csv" required>
                        <div class="zone-icon"><i class="fa-regular fa-file-csv"></i></div>
                        <div class="zone-text"><strong>Click to browse</strong> or drag &amp; drop</div>
                        <div class="zone-text">.csv only</div>
                    </div>
                    <div class="file-name"></div>
                </div>
                <div class="form-group">
                    <label for="row_count">Rows per split</label>
                    <input type="number" name="row_count" id="row_count" min="10" placeholder="Default: 1000">
                </div>
                <button type="submit" class="btn btn-primary">
                    <i class="fa-solid fa-scissors"></i> Split CSV
                </button>
            </form>
        </div>

        <!-- Merge Card -->
        <div class="card">
            <div class="card-icon merge"><i class="fa-solid fa-code-merge"></i></div>
            <h2>Merge Files</h2>
            <p class="desc">Select multiple CSV or TSV files — they'll be stacked row-by-row and returned as a single download.</p>
            <form action="/merge" method="post" enctype="multipart/form-data">
                <div class="form-group">
                    <label for="merge-files">CSV / TSV files</label>
                    <div class="file-zone">
                        <input type="file" name="files" id="merge-files" accept=".csv,.tsv" multiple required>
                        <div class="zone-icon"><i class="fa-regular fa-copy"></i></div>
                        <div class="zone-text"><strong>Click to browse</strong> or drag &amp; drop</div>
                        <div class="zone-text">.csv and .tsv — select multiple</div>
                    </div>
                    <div class="file-name"></div>
                </div>
                <div class="form-group">
                    <label for="format">Output format</label>
                    <select name="format" id="format">
                        <option value="csv" selected>CSV (default)</option>
                        <option value="tsv">TSV</option>
                        <option value="pdf">PDF</option>
                    </select>
                </div>
                <button type="submit" class="btn btn-success">
                    <i class="fa-solid fa-code-merge"></i> Merge Files
                </button>
            </form>
        </div>

    </div>

    <div class="divider">tips</div>

    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1rem;font-size:.82rem;color:var(--muted);">
        <div style="display:flex;gap:.5rem;align-items:flex-start;">
            <i class="fa-solid fa-circle-info" style="color:var(--primary);margin-top:2px;"></i>
            <span>The minimum split size is <strong>10 rows</strong>. Leftovers smaller than 10 are appended to the last file.</span>
        </div>
        <div style="display:flex;gap:.5rem;align-items:flex-start;">
            <i class="fa-solid fa-circle-info" style="color:var(--primary);margin-top:2px;"></i>
            <span>When merging, columns are <strong>union-joined</strong> — missing values fill as blank.</span>
        </div>
        <div style="display:flex;gap:.5rem;align-items:flex-start;">
            <i class="fa-solid fa-circle-info" style="color:var(--primary);margin-top:2px;"></i>
            <span>PDF output is limited to <strong>500 rows</strong> for performance. Use CSV/TSV for full data.</span>
        </div>
    </div>
</main>

<footer>CSV Split &amp; Merge &mdash; fast, local, no data retained after download.</footer>

<script>
    document.querySelectorAll('.file-zone input[type="file"]').forEach(input => {
        input.addEventListener('change', () => {
            const display = input.closest('.file-zone').nextElementSibling;
            if (!display) return;
            const names = Array.from(input.files).map(f => f.name);
            display.textContent = names.length ? names.join(', ') : '';
        });
    });
</script>
</body>
</html>"""

# ── App setup ─────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(32))
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

for _folder in (UPLOAD_FOLDER, SPLIT_FOLDER, MERGE_FOLDER):
    os.makedirs(_folder, exist_ok=True)


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template_string(TEMPLATE)


@app.route("/split", methods=["POST"])
def split_csv_route():
    if "file" not in request.files:
        abort(400, description="No file part in the request")
    file = request.files["file"]
    if file.filename == "" or not allowed_file(file.filename):
        abort(400, description="Invalid or missing file")

    try:
        rows_per_split = int(request.form.get("row_count", DEFAULT_ROWS_PER_SPLIT))
    except ValueError:
        rows_per_split = DEFAULT_ROWS_PER_SPLIT
    rows_per_split = max(rows_per_split, MIN_ROWS_PER_FILE)

    filename = secure_filename(file.filename)
    upload_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(upload_path)

    stem = os.path.splitext(filename)[0]
    split_dir = os.path.join(SPLIT_FOLDER, stem)
    os.makedirs(split_dir, exist_ok=True)

    total_rows = 0
    part_index = 1
    part_rows = []
    header = None

    with open(upload_path, newline="", encoding="utf-8") as src:
        reader = csv.reader(src)
        header = next(reader)
        for row in reader:
            part_rows.append(row)
            total_rows += 1
            if len(part_rows) >= rows_per_split:
                part_path = os.path.join(split_dir, f"{stem}_part_{part_index}.csv")
                with open(part_path, "w", newline="", encoding="utf-8") as out_f:
                    writer = csv.writer(out_f)
                    writer.writerow(header)
                    writer.writerows(part_rows)
                part_index += 1
                part_rows = []

        if part_rows:
            if len(part_rows) < MIN_ROWS_PER_FILE and part_index > 1:
                prev_path = os.path.join(split_dir, f"{stem}_part_{part_index - 1}.csv")
                with open(prev_path, "a", newline="", encoding="utf-8") as out_f:
                    csv.writer(out_f).writerows(part_rows)
            else:
                part_path = os.path.join(split_dir, f"{stem}_part_{part_index}.csv")
                with open(part_path, "w", newline="", encoding="utf-8") as out_f:
                    writer = csv.writer(out_f)
                    writer.writerow(header)
                    writer.writerows(part_rows)
                part_index += 1

    zip_path = os.path.join(SPLIT_FOLDER, f"{stem}_splits.zip")
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for root, _, files in os.walk(split_dir):
            for f in files:
                fp = os.path.join(root, f)
                zipf.write(fp, os.path.relpath(fp, split_dir))

    flash(f"File split into {part_index - 1} parts, total rows: {total_rows}")
    return send_file(zip_path, as_attachment=True, download_name=os.path.basename(zip_path))


@app.route("/merge", methods=["POST"])
def merge_csv_route():
    files = request.files.getlist("files")
    if not files:
        abort(400, description="No files uploaded")
    out_format = request.form.get("format", "csv").lower()
    if out_format not in {"csv", "tsv", "pdf"}:
        abort(400, description="Unsupported output format")

    data_frames = []
    for f in files:
        if f.filename == "" or not allowed_file(f.filename):
            continue
        filename = secure_filename(f.filename)
        upload_path = os.path.join(UPLOAD_FOLDER, filename)
        f.save(upload_path)
        sep = "\t" if os.path.splitext(filename)[1].lower() == ".tsv" else ","
        data_frames.append(pd.read_csv(upload_path, sep=sep, dtype=str, keep_default_na=False))

    if not data_frames:
        abort(400, description="No valid CSV/TSV files provided")

    merged_df = pd.concat(data_frames, axis=0, ignore_index=True, sort=False)
    out_path = os.path.join(MERGE_FOLDER, f"merged_output.{out_format}")

    if out_format == "csv":
        merged_df.to_csv(out_path, index=False)
    elif out_format == "tsv":
        merged_df.to_csv(out_path, index=False, sep="\t")
    else:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=10)
        col_width = pdf.w / (len(merged_df.columns) + 1)
        for col in merged_df.columns:
            pdf.cell(col_width, 8, txt=str(col), border=1)
        pdf.ln()
        for i, row in merged_df.iterrows():
            if i >= 500:
                pdf.cell(pdf.w, 8, txt="... (truncated)", border=0)
                break
            for item in row:
                pdf.cell(col_width, 8, txt=str(item), border=1)
            pdf.ln()
        pdf.output(out_path)

    return send_file(out_path, as_attachment=True, download_name=os.path.basename(out_path))


# ── Launch ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    url = f"http://localhost:{PORT}"
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    print(f"Opening {url} ...")
    app.run(host="0.0.0.0", port=PORT, debug=False)
