import os
from flask import Blueprint, render_template, request, abort, send_file, current_app
from werkzeug.utils import secure_filename

pdf_toolkit = Blueprint('pdf_toolkit', __name__, url_prefix='/pdf')

_IMPLEMENTED_CONVERSIONS = {'docx', 'excel', 'csv', 'image', 'pdf_from_images', 'pptx'}


@pdf_toolkit.route('/')
def pdf_home():
    return render_template('pdf_home.html')


@pdf_toolkit.route('/compare', methods=['GET', 'POST'])
def compare():
    if request.method == 'POST':
        if 'file1' not in request.files or 'file2' not in request.files:
            abort(400, description='Both PDF files are required')
        file1 = request.files['file1']
        file2 = request.files['file2']
        if not file1.filename.lower().endswith('.pdf') or not file2.filename.lower().endswith('.pdf'):
            abort(400, description='Only PDF files are accepted')
        fn1 = secure_filename(file1.filename)
        fn2 = secure_filename(file2.filename)
        path1 = os.path.join(current_app.config['UPLOAD_FOLDER'], fn1)
        path2 = os.path.join(current_app.config['UPLOAD_FOLDER'], fn2)
        file1.save(path1)
        file2.save(path2)
        size1 = os.path.getsize(path1)
        size2 = os.path.getsize(path2)
        current_app.logger.info('PDF comparison: %s (%d bytes) vs %s (%d bytes)', fn1, size1, fn2, size2)
        diff = f'File sizes: {fn1} = {size1} bytes, {fn2} = {size2} bytes.'
        return render_template('compare.html', result=diff)
    return render_template('compare.html')


@pdf_toolkit.route('/conversion')
def conversion_home():
    return render_template('conversion.html')


@pdf_toolkit.route('/conversion/<target>', methods=['POST'])
def conversion_target(target):
    if target not in _IMPLEMENTED_CONVERSIONS:
        abort(501, description=f'Conversion to "{target}" is not yet implemented')

    if 'file' not in request.files:
        abort(400, description='No file part in the request')
    file = request.files['file']
    if file.filename == '':
        abort(400, description='No selected file')

    filename = secure_filename(file.filename)
    upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    file.save(upload_path)

    from app.tasks.conversion import pdf_to_docx, pdf_to_excel, pdf_to_csv, pdf_to_image, image_to_pdf

    try:
        if target == 'docx':
            result_path = pdf_to_docx(upload_path)
        elif target == 'excel':
            result_path = pdf_to_excel(upload_path)
        elif target == 'csv':
            result_path = pdf_to_csv(upload_path)
        elif target == 'image':
            result_path = pdf_to_image(upload_path)
        elif target == 'pdf_from_images':
            images = request.form.get('images')
            if not images:
                abort(400, description='No image list provided')
            result_path = image_to_pdf(images)
        elif target == 'pptx':
            from app.tasks.conversion import pdf_to_pptx
            result_path = pdf_to_pptx(upload_path)
    except Exception as e:
        current_app.logger.error('Conversion error: %s', e)
        abort(500, description=str(e))

    current_app.logger.info('PDF conversion: target=%s, input=%s, output=%s', target, upload_path, result_path)
    return send_file(result_path, as_attachment=True)


@pdf_toolkit.route('/editor', methods=['GET', 'POST'])
def editor():
    if request.method == 'POST':
        if 'file' not in request.files:
            abort(400, description='No file part in the request')
        file = request.files['file']
        if file.filename == '' or not file.filename.lower().endswith('.pdf'):
            abort(400, description='Please upload a PDF file')
        edits = request.form.get('edits', '')
        secure_name = secure_filename(file.filename)
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], secure_name)
        file.save(upload_path)
        from app.tasks.editor import edit_pdf_text
        result_path = edit_pdf_text(upload_path, edits)
        current_app.logger.info('PDF edit: %s -> %s', upload_path, result_path)
        return send_file(result_path, as_attachment=True, download_name=os.path.basename(result_path))
    return render_template('editor.html')


@pdf_toolkit.route('/organization')
def organization():
    return render_template('coming_soon.html', title='PDF Organization')


@pdf_toolkit.route('/ocr', methods=['GET', 'POST'])
def ocr():
    if request.method == 'POST':
        if 'file' not in request.files:
            abort(400, description='No file part in the request')
        file = request.files['file']
        if file.filename == '':
            abort(400, description='No file selected')
        secure_name = secure_filename(file.filename)
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], secure_name)
        file.save(upload_path)
        ext = os.path.splitext(secure_name)[1].lower()
        if ext in {'.png', '.jpg', '.jpeg', '.tif', '.tiff'}:
            from app.tasks.ocr import ocr_image
            text = ocr_image(upload_path)
            return render_template('ocr_result.html', text=text, filename=secure_name)
        elif ext == '.pdf':
            from app.tasks.ocr import ocr_pdf
            result_path = ocr_pdf(upload_path)
            current_app.logger.info('PDF OCR: %s -> %s', upload_path, result_path)
            return send_file(result_path, as_attachment=True, download_name=os.path.basename(result_path))
        else:
            abort(400, description='Unsupported file type for OCR')
    return render_template('ocr.html')


@pdf_toolkit.route('/security', methods=['GET', 'POST'])
def security():
    if request.method == 'POST':
        action = request.form.get('action')
        password = request.form.get('password')
        if not password:
            abort(400, description='Password is required')
        if 'file' not in request.files:
            abort(400, description='No file part in the request')
        file = request.files['file']
        if file.filename == '' or not file.filename.lower().endswith('.pdf'):
            abort(400, description='Please upload a PDF file')
        secure_name = secure_filename(file.filename)
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], secure_name)
        file.save(upload_path)
        if action == 'protect':
            from app.tasks.security import protect_pdf
            result_path = protect_pdf(upload_path, password)
        elif action == 'unlock':
            from app.tasks.security import unlock_pdf
            result_path = unlock_pdf(upload_path, password)
        else:
            abort(400, description='Invalid action')
        current_app.logger.info('PDF security: %s - action %s -> %s', upload_path, action, result_path)
        return send_file(result_path, as_attachment=True, download_name=os.path.basename(result_path))
    return render_template('security.html')


def _file_context(f) -> str:
    """Extract readable context from an uploaded file to inject into the AI prompt."""
    import io
    name = secure_filename(f.filename)
    ext  = os.path.splitext(name)[1].lower()
    raw  = f.read()

    if ext in ('.csv', '.tsv'):
        import csv as _csv
        sep = '\t' if ext == '.tsv' else ','
        try:
            import pandas as pd
            df = pd.read_csv(io.BytesIO(raw), sep=sep, dtype=str, keep_default_na=False)
            rows, cols = df.shape
            col_info = ', '.join(f'{c} ({df[c].dtype})' for c in df.columns)
            sample   = df.head(5).to_csv(index=False)
            nulls    = df.isnull().sum().to_dict()
            null_info = ', '.join(f'{k}:{v}' for k, v in nulls.items() if v)
            ctx = (
                f'File: {name}\nType: CSV/TSV\nShape: {rows} rows × {cols} columns\n'
                f'Columns: {col_info}\n'
                + (f'Missing values: {null_info}\n' if null_info else '')
                + f'First 5 rows:\n{sample}'
            )
        except Exception:
            text = raw.decode('utf-8', errors='replace')[:3000]
            ctx  = f'File: {name}\nContent (truncated):\n{text}'

    elif ext == '.pdf':
        try:
            import pikepdf, pdfminer.high_level as ph
            text = ph.extract_text(io.BytesIO(raw))[:4000]
            ctx  = f'File: {name}\nType: PDF\nExtracted text (first ~4000 chars):\n{text}'
        except Exception as e:
            ctx = f'File: {name}\nType: PDF (could not extract text: {e})'

    elif ext in ('.txt', '.md', '.json', '.log'):
        text = raw.decode('utf-8', errors='replace')[:4000]
        ctx  = f'File: {name}\nType: text\nContent:\n{text}'

    else:
        ctx = f'File: {name} (binary file, cannot read content directly)'

    return ctx


@pdf_toolkit.route('/ai/ask', methods=['POST'])
def ai_ask():
    """AJAX endpoint — returns JSON for the side-panel chat."""
    from flask import jsonify
    from app.tasks.ai import ollama_chat, OllamaRateLimitError

    # Support both JSON (no file) and multipart (with file)
    uploaded = request.files.get('file')
    if uploaded and uploaded.filename:
        prompt  = (request.form.get('prompt') or 'Explain this file and help me understand it.').strip()
        context = (request.form.get('context') or '').strip()
        file_ctx = _file_context(uploaded)
        system  = (context + '\n\n' if context else '') + \
                  f'The user has uploaded a file. Here is its content/summary:\n\n{file_ctx}\n\n' \
                  f'Analyse this file thoroughly and answer the user\'s question.'
    else:
        data    = request.get_json(silent=True) or {}
        prompt  = (data.get('prompt') or '').strip()
        context = (data.get('context') or '').strip()
        system  = context or None

    if not prompt:
        return jsonify({'error': 'Prompt is required'}), 400

    current_app.logger.info('AI ask: prompt=%.80s  file=%s', prompt,
                            uploaded.filename if uploaded and uploaded.filename else 'none')
    try:
        reply = ollama_chat(prompt, system=system)
        return jsonify({'reply': reply})
    except OllamaRateLimitError as e:
        return jsonify({'error': str(e), 'upgrade_url': 'https://ollama.com/upgrade'}), 429
    except Exception as e:
        current_app.logger.error('Ollama AJAX error: %s', e)
        return jsonify({'error': f'Could not reach the AI model: {e}'}), 500


@pdf_toolkit.route('/ai', methods=['GET', 'POST'])
def ai():
    prefill = request.args.get('prompt', '')
    if request.method == 'POST':
        prompt = request.form.get('prompt')
        if not prompt:
            abort(400, description='Prompt is required')
        from app.tasks.ai import ollama_chat, OllamaRateLimitError
        try:
            result = ollama_chat(prompt)
            return render_template('ai.html', response=result, prompt=prompt)
        except OllamaRateLimitError as e:
            current_app.logger.warning('Ollama rate limit: %s', e)
            return render_template('ai.html', error=str(e), prompt=prompt)
        except Exception as e:
            current_app.logger.error('Ollama error: %s', e)
            return render_template('ai.html', error=f'Could not reach the AI model: {e}', prompt=prompt)
    return render_template('ai.html', prefill=prefill)


@pdf_toolkit.route('/batch')
def batch():
    return render_template('coming_soon.html', title='Batch Processing')


# ── Merge ──────────────────────────────────────────────────────────────────

@pdf_toolkit.route('/merge', methods=['GET', 'POST'])
def merge_pdf():
    if request.method == 'POST':
        files = request.files.getlist('files')
        paths = []
        for f in files:
            if f.filename == '' or not f.filename.lower().endswith('.pdf'):
                continue
            name = secure_filename(f.filename)
            p = os.path.join(current_app.config['UPLOAD_FOLDER'], name)
            f.save(p)
            paths.append(p)
        if len(paths) < 2:
            abort(400, description='Please upload at least two PDF files')
        from app.tasks.pdf_ops import merge_pdfs
        try:
            result = merge_pdfs(paths)
        except Exception as e:
            current_app.logger.error('Merge error: %s', e)
            abort(500, description=str(e))
        return send_file(result, as_attachment=True, download_name='merged.pdf')
    return render_template('pdf_merge.html')


# ── Split ──────────────────────────────────────────────────────────────────

def _parse_ranges(s, total):
    ranges = []
    for part in s.split(','):
        part = part.strip()
        if not part:
            continue
        if '-' in part:
            bits = part.split('-', 1)
            if bits[0].strip().isdigit() and bits[1].strip().isdigit():
                a, b = int(bits[0].strip()) - 1, int(bits[1].strip()) - 1
                ranges.append((max(0, a), min(b, total - 1)))
        elif part.isdigit():
            i = int(part) - 1
            if 0 <= i < total:
                ranges.append((i, i))
    return ranges


@pdf_toolkit.route('/split', methods=['GET', 'POST'])
def split_pdf():
    if request.method == 'POST':
        if 'file' not in request.files:
            abort(400, description='No file uploaded')
        f = request.files['file']
        if f.filename == '' or not f.filename.lower().endswith('.pdf'):
            abort(400, description='Please upload a PDF file')
        name = secure_filename(f.filename)
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], name)
        f.save(upload_path)

        import pikepdf
        total = len(pikepdf.Pdf.open(upload_path).pages)

        from app.tasks.pdf_ops import split_pdf as _split
        mode = request.form.get('mode', 'every')
        try:
            if mode == 'every':
                every = int(request.form.get('every', 1))
                result = _split(upload_path, every=max(1, every))
            else:
                ranges_str = request.form.get('ranges', '')
                ranges = _parse_ranges(ranges_str, total)
                if not ranges:
                    abort(400, description='No valid page ranges provided')
                result = _split(upload_path, ranges=ranges)
        except Exception as e:
            current_app.logger.error('Split error: %s', e)
            abort(500, description=str(e))
        return send_file(result, as_attachment=True, download_name='split_pages.zip')
    return render_template('pdf_split.html')


# ── Compress ───────────────────────────────────────────────────────────────

@pdf_toolkit.route('/compress', methods=['GET', 'POST'])
def compress_pdf():
    if request.method == 'POST':
        if 'file' not in request.files:
            abort(400, description='No file uploaded')
        f = request.files['file']
        if f.filename == '' or not f.filename.lower().endswith('.pdf'):
            abort(400, description='Please upload a PDF file')
        name = secure_filename(f.filename)
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], name)
        f.save(upload_path)
        from app.tasks.pdf_ops import compress_pdf as _compress
        try:
            result = _compress(upload_path)
        except Exception as e:
            current_app.logger.error('Compress error: %s', e)
            abort(500, description=str(e))
        return send_file(result, as_attachment=True, download_name='compressed.pdf')
    return render_template('pdf_compress.html')


# ── Rotate ─────────────────────────────────────────────────────────────────

@pdf_toolkit.route('/rotate', methods=['GET', 'POST'])
def rotate_pdf():
    if request.method == 'POST':
        if 'file' not in request.files:
            abort(400, description='No file uploaded')
        f = request.files['file']
        if f.filename == '' or not f.filename.lower().endswith('.pdf'):
            abort(400, description='Please upload a PDF file')
        name = secure_filename(f.filename)
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], name)
        f.save(upload_path)
        try:
            angle = int(request.form.get('angle', 90))
        except ValueError:
            angle = 90
        page_mode = request.form.get('page_mode', 'all')
        pages = 'all' if page_mode == 'all' else request.form.get('pages', 'all')
        from app.tasks.pdf_ops import rotate_pdf as _rotate
        try:
            result = _rotate(upload_path, angle, pages)
        except Exception as e:
            current_app.logger.error('Rotate error: %s', e)
            abort(500, description=str(e))
        return send_file(result, as_attachment=True, download_name='rotated.pdf')
    return render_template('pdf_rotate.html')


# ── Delete pages ───────────────────────────────────────────────────────────

@pdf_toolkit.route('/delete-pages', methods=['GET', 'POST'])
def delete_pages():
    if request.method == 'POST':
        if 'file' not in request.files:
            abort(400, description='No file uploaded')
        f = request.files['file']
        if f.filename == '' or not f.filename.lower().endswith('.pdf'):
            abort(400, description='Please upload a PDF file')
        pages = request.form.get('pages', '').strip()
        if not pages:
            abort(400, description='No pages specified')
        name = secure_filename(f.filename)
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], name)
        f.save(upload_path)
        from app.tasks.pdf_ops import delete_pages as _delete
        try:
            result = _delete(upload_path, pages)
        except Exception as e:
            current_app.logger.error('Delete pages error: %s', e)
            abort(500, description=str(e))
        return send_file(result, as_attachment=True, download_name='pages_deleted.pdf')
    return render_template('pdf_delete_pages.html')


# ── Extract pages ──────────────────────────────────────────────────────────

@pdf_toolkit.route('/extract-pages', methods=['GET', 'POST'])
def extract_pages():
    if request.method == 'POST':
        if 'file' not in request.files:
            abort(400, description='No file uploaded')
        f = request.files['file']
        if f.filename == '' or not f.filename.lower().endswith('.pdf'):
            abort(400, description='Please upload a PDF file')
        pages = request.form.get('pages', '').strip()
        if not pages:
            abort(400, description='No pages specified')
        name = secure_filename(f.filename)
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], name)
        f.save(upload_path)
        from app.tasks.pdf_ops import extract_pages as _extract
        try:
            result = _extract(upload_path, pages)
        except Exception as e:
            current_app.logger.error('Extract pages error: %s', e)
            abort(500, description=str(e))
        return send_file(result, as_attachment=True, download_name='extracted.pdf')
    return render_template('pdf_extract_pages.html')


# ── Reorder ────────────────────────────────────────────────────────────────

@pdf_toolkit.route('/reorder', methods=['GET', 'POST'])
def reorder_pdf():
    if request.method == 'POST':
        if 'file' not in request.files:
            abort(400, description='No file uploaded')
        f = request.files['file']
        if f.filename == '' or not f.filename.lower().endswith('.pdf'):
            abort(400, description='Please upload a PDF file')
        order = request.form.get('order', '').strip()
        if not order:
            abort(400, description='No page order specified')
        name = secure_filename(f.filename)
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], name)
        f.save(upload_path)
        from app.tasks.pdf_ops import reorder_pdf as _reorder
        try:
            result = _reorder(upload_path, order)
        except Exception as e:
            current_app.logger.error('Reorder error: %s', e)
            abort(500, description=str(e))
        return send_file(result, as_attachment=True, download_name='reordered.pdf')
    return render_template('pdf_reorder.html')


# ── Watermark ──────────────────────────────────────────────────────────────

@pdf_toolkit.route('/watermark', methods=['GET', 'POST'])
def watermark_pdf():
    if request.method == 'POST':
        if 'file' not in request.files:
            abort(400, description='No file uploaded')
        f = request.files['file']
        if f.filename == '' or not f.filename.lower().endswith('.pdf'):
            abort(400, description='Please upload a PDF file')
        text = request.form.get('text', '').strip()
        if not text:
            abort(400, description='Watermark text is required')
        name = secure_filename(f.filename)
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], name)
        f.save(upload_path)
        from app.tasks.pdf_ops import watermark_pdf as _watermark
        try:
            result = _watermark(upload_path, text)
        except Exception as e:
            current_app.logger.error('Watermark error: %s', e)
            abort(500, description=str(e))
        return send_file(result, as_attachment=True, download_name='watermarked.pdf')
    return render_template('pdf_watermark.html')


# ── Number pages ───────────────────────────────────────────────────────────

@pdf_toolkit.route('/number-pages', methods=['GET', 'POST'])
def number_pages():
    if request.method == 'POST':
        if 'file' not in request.files:
            abort(400, description='No file uploaded')
        f = request.files['file']
        if f.filename == '' or not f.filename.lower().endswith('.pdf'):
            abort(400, description='Please upload a PDF file')
        position = request.form.get('position', 'bottom-center')
        try:
            start = int(request.form.get('start', 1))
        except ValueError:
            start = 1
        name = secure_filename(f.filename)
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], name)
        f.save(upload_path)
        from app.tasks.pdf_ops import number_pages as _number
        try:
            result = _number(upload_path, position, start)
        except Exception as e:
            current_app.logger.error('Number pages error: %s', e)
            abort(500, description=str(e))
        return send_file(result, as_attachment=True, download_name='numbered.pdf')
    return render_template('pdf_number_pages.html')


# ── Header & Footer ────────────────────────────────────────────────────────

@pdf_toolkit.route('/header-footer', methods=['GET', 'POST'])
def header_footer():
    if request.method == 'POST':
        if 'file' not in request.files:
            abort(400, description='No file uploaded')
        f = request.files['file']
        if f.filename == '' or not f.filename.lower().endswith('.pdf'):
            abort(400, description='Please upload a PDF file')
        header = request.form.get('header', '').strip()
        footer = request.form.get('footer', '').strip()
        if not header and not footer:
            abort(400, description='Please enter at least a header or footer text')
        name = secure_filename(f.filename)
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], name)
        f.save(upload_path)
        from app.tasks.pdf_ops import add_header_footer
        try:
            result = add_header_footer(upload_path, header, footer)
        except Exception as e:
            current_app.logger.error('Header/footer error: %s', e)
            abort(500, description=str(e))
        return send_file(result, as_attachment=True, download_name='header_footer.pdf')
    return render_template('pdf_header_footer.html')


# ── Repair ─────────────────────────────────────────────────────────────────

@pdf_toolkit.route('/repair', methods=['GET', 'POST'])
def repair_pdf():
    if request.method == 'POST':
        if 'file' not in request.files:
            abort(400, description='No file uploaded')
        f = request.files['file']
        if f.filename == '' or not f.filename.lower().endswith('.pdf'):
            abort(400, description='Please upload a PDF file')
        name = secure_filename(f.filename)
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], name)
        f.save(upload_path)
        from app.tasks.pdf_ops import repair_pdf as _repair
        try:
            result = _repair(upload_path)
        except Exception as e:
            current_app.logger.error('Repair error: %s', e)
            abort(500, description=str(e))
        return send_file(result, as_attachment=True, download_name='repaired.pdf')
    return render_template('pdf_repair.html')


# ── Sign ───────────────────────────────────────────────────────────────────

@pdf_toolkit.route('/sign', methods=['GET', 'POST'])
def sign_pdf():
    if request.method == 'POST':
        if 'file' not in request.files:
            abort(400, description='No file uploaded')
        f = request.files['file']
        if f.filename == '' or not f.filename.lower().endswith('.pdf'):
            abort(400, description='Please upload a PDF file')
        name_val = request.form.get('name', '').strip()
        if not name_val:
            abort(400, description='Signer name is required')
        date_val = request.form.get('date', '')
        reason_val = request.form.get('reason', '')
        name = secure_filename(f.filename)
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], name)
        f.save(upload_path)
        from app.tasks.pdf_ops import sign_pdf as _sign
        try:
            result = _sign(upload_path, name_val, date_val, reason_val)
        except Exception as e:
            current_app.logger.error('Sign error: %s', e)
            abort(500, description=str(e))
        return send_file(result, as_attachment=True, download_name='signed.pdf')
    return render_template('pdf_sign.html')


# ── PDF to PPTX ────────────────────────────────────────────────────────────

@pdf_toolkit.route('/to-pptx', methods=['GET', 'POST'])
def to_pptx():
    if request.method == 'POST':
        if 'file' not in request.files:
            abort(400, description='No file uploaded')
        f = request.files['file']
        if f.filename == '' or not f.filename.lower().endswith('.pdf'):
            abort(400, description='Please upload a PDF file')
        name = secure_filename(f.filename)
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], name)
        f.save(upload_path)
        from app.tasks.conversion import pdf_to_pptx
        try:
            result = pdf_to_pptx(upload_path)
        except Exception as e:
            current_app.logger.error('PDF to PPTX error: %s', e)
            abort(500, description=str(e))
        return send_file(result, as_attachment=True, download_name='presentation.pptx')
    return render_template('pdf_to_pptx.html')


# ── Office to PDF ──────────────────────────────────────────────────────────

_OFFICE_EXTENSIONS = {'.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt', '.odt', '.ods', '.odp'}


@pdf_toolkit.route('/office-to-pdf', methods=['GET', 'POST'])
def office_to_pdf():
    if request.method == 'POST':
        if 'file' not in request.files:
            abort(400, description='No file uploaded')
        f = request.files['file']
        ext = os.path.splitext(f.filename)[1].lower() if f.filename else ''
        if f.filename == '' or ext not in _OFFICE_EXTENSIONS:
            abort(400, description='Please upload a Word, Excel or PowerPoint file')
        name = secure_filename(f.filename)
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], name)
        f.save(upload_path)
        from app.tasks.conversion import office_to_pdf as _office_to_pdf
        try:
            result = _office_to_pdf(upload_path)
        except Exception as e:
            current_app.logger.error('Office to PDF error: %s', e)
            abort(500, description=str(e))
        return send_file(result, as_attachment=True, download_name='converted.pdf')
    return render_template('pdf_office_to_pdf.html')


@pdf_toolkit.route('/to-images', methods=['GET', 'POST'])
def pdf_to_images():
    if request.method == 'POST':
        if 'file' not in request.files:
            abort(400, description='No file uploaded')
        f = request.files['file']
        if f.filename == '' or not f.filename.lower().endswith('.pdf'):
            abort(400, description='Please upload a PDF file')
        fmt = request.form.get('fmt', 'png')
        if fmt not in ('png', 'jpg'):
            fmt = 'png'
        dpi = int(request.form.get('dpi', 150))
        dpi = max(72, min(300, dpi))
        name = secure_filename(f.filename)
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], name)
        f.save(upload_path)
        from app.tasks.pdf_ops import pdf_to_images as _to_images
        try:
            result = _to_images(upload_path, fmt=fmt, dpi=dpi)
        except Exception as e:
            current_app.logger.error('PDF to images error: %s', e)
            abort(500, description=str(e))
        current_app.logger.info('PDF to images: %s fmt=%s dpi=%d', name, fmt, dpi)
        stem = name.rsplit('.', 1)[0]
        return send_file(result, as_attachment=True, download_name=f'{stem}_images.zip')
    return render_template('pdf_to_images.html')
