import os
import csv
import io
import zipfile
from flask import Blueprint, render_template, request, send_file, current_app, abort, flash
from werkzeug.utils import secure_filename
import pandas as pd
from fpdf import FPDF

bp = Blueprint('main', __name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]

@bp.route('/', methods=['GET'])
def index():
    """Render the home page with split and merge forms."""
    return render_template('index.html')

@bp.route('/split', methods=['POST'])
def split_csv_route():
    """Handle CSV splitting based on row count.
    The user supplies a CSV file and an optional row count.
    """
    if 'file' not in request.files:
        abort(400, description='No file part in the request')
    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        abort(400, description='Invalid or missing file')
    # Determine rows per split – fallback to default if missing or invalid
    try:
        rows_per_split = int(request.form.get('row_count', current_app.config['DEFAULT_ROWS_PER_SPLIT']))
    except ValueError:
        rows_per_split = current_app.config['DEFAULT_ROWS_PER_SPLIT']
    # Enforce a sensible lower bound (minimum 10 rows as per spec)
    rows_per_split = max(rows_per_split, current_app.config['MIN_ROWS_PER_FILE'])

    filename = secure_filename(file.filename)
    upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    file.save(upload_path)

    # Read CSV and split
    split_dir = os.path.join(current_app.config['SPLIT_FOLDER'], os.path.splitext(filename)[0])
    os.makedirs(split_dir, exist_ok=True)

    total_rows = 0
    part_index = 1
    part_rows = []
    header = None

    with open(upload_path, newline='', encoding='utf-8') as src:
        reader = csv.reader(src)
        header = next(reader)
        for row in reader:
            part_rows.append(row)
            total_rows += 1
            if len(part_rows) >= rows_per_split:
                # Write current part
                part_path = os.path.join(split_dir, f"{os.path.splitext(filename)[0]}_part_{part_index}.csv")
                with open(part_path, 'w', newline='', encoding='utf-8') as out_f:
                    writer = csv.writer(out_f)
                    writer.writerow(header)
                    writer.writerows(part_rows)
                part_index += 1
                part_rows = []
        # Write any remaining rows (ensure at least MIN_ROWS_PER_FILE)
        if part_rows:
            # If the leftover is smaller than the minimum, merge it with the previous file
            if len(part_rows) < current_app.config['MIN_ROWS_PER_FILE'] and part_index > 1:
                # Append to previous part
                prev_path = os.path.join(split_dir, f"{os.path.splitext(filename)[0]}_part_{part_index - 1}.csv")
                with open(prev_path, 'a', newline='', encoding='utf-8') as out_f:
                    writer = csv.writer(out_f)
                    writer.writerows(part_rows)
            else:
                part_path = os.path.join(split_dir, f"{os.path.splitext(filename)[0]}_part_{part_index}.csv")
                with open(part_path, 'w', newline='', encoding='utf-8') as out_f:
                    writer = csv.writer(out_f)
                    writer.writerow(header)
                    writer.writerows(part_rows)
                    part_index += 1

    # Create a zip archive of the split files
    zip_path = os.path.join(current_app.config['SPLIT_FOLDER'], f"{os.path.splitext(filename)[0]}_splits.zip")
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for root, _, files in os.walk(split_dir):
            for f in files:
                file_path = os.path.join(root, f)
                arcname = os.path.relpath(file_path, split_dir)
                zipf.write(file_path, arcname)

    # Provide a summary in a flash message (optional) and send the zip
    flash(f"File split into {part_index - 1} parts, total rows: {total_rows}")
    return send_file(zip_path, as_attachment=True, download_name=os.path.basename(zip_path))

@bp.route('/merge', methods=['POST'])
def merge_csv_route():
    """Merge multiple CSV/TSV files into a single file.
    The user may request CSV, TSV, or PDF output.
    """
    files = request.files.getlist('files')
    if not files:
        abort(400, description='No files uploaded')
    # Determine desired output format – default CSV
    out_format = request.form.get('format', 'csv').lower()
    if out_format not in {'csv', 'tsv', 'pdf'}:
        abort(400, description='Unsupported output format')

    data_frames = []
    for f in files:
        if f.filename == '' or not allowed_file(f.filename):
            continue
        filename = secure_filename(f.filename)
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        f.save(upload_path)
        # Use pandas to read – infer separator from extension if needed
        ext = os.path.splitext(filename)[1].lower()
        sep = '\t' if ext == '.tsv' else ','
        df = pd.read_csv(upload_path, sep=sep, dtype=str, keep_default_na=False)
        data_frames.append(df)

    if not data_frames:
        abort(400, description='No valid CSV/TSV files provided')

    # Concatenate, using union of columns
    merged_df = pd.concat(data_frames, axis=0, ignore_index=True, sort=False)

    # Prepare output path
    base_name = 'merged_output'
    out_path = os.path.join(current_app.config['MERGE_FOLDER'], f"{base_name}.{out_format}")

    if out_format == 'csv':
        merged_df.to_csv(out_path, index=False)
    elif out_format == 'tsv':
        merged_df.to_csv(out_path, index=False, sep='\t')
    else:  # PDF generation
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font('Arial', size=10)
        # Header row
        col_width = pdf.w / (len(merged_df.columns) + 1)
        for col in merged_df.columns:
            pdf.cell(col_width, 8, txt=str(col), border=1)
        pdf.ln()
        # Data rows – truncate if very large for performance
        max_rows = 500
        for i, row in merged_df.iterrows():
            if i >= max_rows:
                pdf.cell(pdf.w, 8, txt='... (truncated)', border=0)
                break
            for item in row:
                pdf.cell(col_width, 8, txt=str(item), border=1)
            pdf.ln()
        pdf.output(out_path)

    return send_file(out_path, as_attachment=True, download_name=os.path.basename(out_path))
