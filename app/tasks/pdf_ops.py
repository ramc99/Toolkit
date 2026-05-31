import os
import uuid


def _out(ext):
    from flask import current_app
    return os.path.join(current_app.config['UPLOAD_FOLDER'], f"{uuid.uuid4().hex}.{ext}")


def merge_pdfs(input_paths):
    import pikepdf
    out = _out('pdf')
    sources = [pikepdf.Pdf.open(p) for p in input_paths]
    try:
        with pikepdf.Pdf.new() as pdf:
            for src in sources:
                pdf.pages.extend(src.pages)
            pdf.save(out)
    finally:
        for src in sources:
            src.close()
    return out


def split_pdf(input_path, every=None, ranges=None):
    import pikepdf
    import zipfile as zf
    from flask import current_app

    src = pikepdf.Pdf.open(input_path)
    total = len(src.pages)

    if every:
        chunks = [(i, min(i + every - 1, total - 1)) for i in range(0, total, every)]
    elif ranges:
        chunks = ranges
    else:
        chunks = [(0, total - 1)]

    out_paths = []
    for i, (s, e) in enumerate(chunks, 1):
        p = os.path.join(
            current_app.config['UPLOAD_FOLDER'],
            f"{uuid.uuid4().hex}_part{i}.pdf"
        )
        with pikepdf.Pdf.new() as out_pdf:
            for idx in range(s, min(e + 1, total)):
                out_pdf.pages.append(src.pages[idx])
            out_pdf.save(p)
        out_paths.append(p)
    src.close()

    zip_path = _out('zip')
    with zf.ZipFile(zip_path, 'w') as z:
        for i, p in enumerate(out_paths, 1):
            z.write(p, f'part_{i}.pdf')
    return zip_path


def compress_pdf(input_path):
    import pikepdf
    out = _out('pdf')
    with pikepdf.Pdf.open(input_path) as pdf:
        pdf.save(
            out,
            compress_streams=True,
            object_stream_mode=pikepdf.ObjectStreamMode.generate
        )
    return out


def rotate_pdf(input_path, angle, pages='all'):
    import pikepdf
    out = _out('pdf')
    with pikepdf.Pdf.open(input_path) as pdf:
        total = len(pdf.pages)
        if pages == 'all':
            idxs = list(range(total))
        else:
            idxs = [
                int(p.strip()) - 1
                for p in pages.split(',')
                if p.strip().isdigit() and 0 < int(p.strip()) <= total
            ]
        for i in idxs:
            page = pdf.pages[i]
            cur = int(page.get('/Rotate', 0))
            page['/Rotate'] = (cur + angle) % 360
        pdf.save(out)
    return out


def delete_pages(input_path, page_nums):
    import pikepdf
    out = _out('pdf')
    with pikepdf.Pdf.open(input_path) as pdf:
        total = len(pdf.pages)
        to_del = sorted(
            {
                int(p.strip()) - 1
                for p in page_nums.split(',')
                if p.strip().isdigit() and 0 < int(p.strip()) <= total
            },
            reverse=True
        )
        for i in to_del:
            del pdf.pages[i]
        pdf.save(out)
    return out


def extract_pages(input_path, page_nums):
    import pikepdf
    out = _out('pdf')
    with pikepdf.Pdf.open(input_path) as src:
        total = len(src.pages)
        idxs = _parse_page_list(page_nums, total)
        with pikepdf.Pdf.new() as dst:
            for i in idxs:
                dst.pages.append(src.pages[i])
            dst.save(out)
    return out


def reorder_pdf(input_path, order):
    import pikepdf
    out = _out('pdf')
    with pikepdf.Pdf.open(input_path) as src:
        total = len(src.pages)
        idxs = [
            int(p.strip()) - 1
            for p in order.split(',')
            if p.strip().isdigit() and 0 < int(p.strip()) <= total
        ]
        with pikepdf.Pdf.new() as dst:
            for i in idxs:
                dst.pages.append(src.pages[i])
            dst.save(out)
    return out


def watermark_pdf(input_path, text):
    import fitz
    out = _out('pdf')
    doc = fitz.open(input_path)
    for page in doc:
        r = page.rect
        fontsize = max(32, int(min(r.width, r.height) * 0.09))
        font = fitz.Font("helv")
        tw = fitz.TextWriter(r)
        text_w = fitz.get_text_length(text, fontname="helv", fontsize=fontsize)
        origin = fitz.Point((r.width - text_w) / 2, r.height / 2)
        tw.append(origin, text, fontsize=fontsize, font=font)
        pivot = fitz.Point(r.width / 2, r.height / 2)
        tw.write_text(page, color=(0.65, 0.65, 0.65), opacity=0.28,
                      morph=(pivot, fitz.Matrix(45)))
    doc.save(out)
    doc.close()
    return out


def number_pages(input_path, position='bottom-center', start=1):
    import fitz
    out = _out('pdf')
    doc = fitz.open(input_path)
    fs = 10
    margin = 18
    for i, page in enumerate(doc):
        r = page.rect
        label = str(i + start)
        tw = len(label) * fs * 0.5
        if position == 'bottom-center':
            pt = fitz.Point(r.width / 2 - tw / 2, r.height - margin)
        elif position == 'bottom-right':
            pt = fitz.Point(r.width - margin - tw, r.height - margin)
        elif position == 'bottom-left':
            pt = fitz.Point(margin, r.height - margin)
        elif position == 'top-center':
            pt = fitz.Point(r.width / 2 - tw / 2, margin + fs)
        elif position == 'top-right':
            pt = fitz.Point(r.width - margin - tw, margin + fs)
        else:  # top-left
            pt = fitz.Point(margin, margin + fs)
        page.insert_text(pt, label, fontsize=fs, color=(0, 0, 0))
    doc.save(out)
    doc.close()
    return out


def add_header_footer(input_path, header='', footer=''):
    import fitz
    out = _out('pdf')
    doc = fitz.open(input_path)
    fs = 9
    for page in doc:
        r = page.rect
        if header:
            hw = len(header) * fs * 0.5
            page.insert_text(
                fitz.Point(r.width / 2 - hw / 2, 16 + fs),
                header, fontsize=fs, color=(0.3, 0.3, 0.3)
            )
        if footer:
            fw = len(footer) * fs * 0.5
            page.insert_text(
                fitz.Point(r.width / 2 - fw / 2, r.height - 12),
                footer, fontsize=fs, color=(0.3, 0.3, 0.3)
            )
    doc.save(out)
    doc.close()
    return out


def repair_pdf(input_path):
    import pikepdf
    out = _out('pdf')
    with pikepdf.Pdf.open(input_path, suppress_warnings=True) as pdf:
        pdf.save(out)
    return out


def sign_pdf(input_path, name, date='', reason=''):
    import fitz
    out = _out('pdf')
    doc = fitz.open(input_path)
    page = doc[-1]
    r = page.rect
    lines = [f'Signed by: {name}']
    if date:
        lines.append(f'Date: {date}')
    if reason:
        lines.append(f'Reason: {reason}')
    sig_text = '\n'.join(lines)
    sig_rect = fitz.Rect(r.width - 230, r.height - 90, r.width - 20, r.height - 20)
    page.draw_rect(sig_rect, color=(0.2, 0.35, 0.75), width=1)
    page.insert_textbox(sig_rect, sig_text, fontsize=8, color=(0.1, 0.1, 0.5), align=0)
    doc.save(out)
    doc.close()
    return out


def _parse_page_list(s, total):
    idxs = []
    for part in s.split(','):
        part = part.strip()
        if not part:
            continue
        if '-' in part:
            bits = part.split('-', 1)
            if bits[0].strip().isdigit() and bits[1].strip().isdigit():
                a, b = int(bits[0].strip()) - 1, int(bits[1].strip()) - 1
                idxs.extend(range(max(0, a), min(b + 1, total)))
        elif part.isdigit():
            i = int(part) - 1
            if 0 <= i < total:
                idxs.append(i)
    return idxs


def pdf_to_images(input_path, fmt='png', dpi=150):
    import fitz, os, uuid, zipfile
    doc = fitz.open(input_path)
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    out_dir = os.path.join(os.path.dirname(input_path), f'pdf_imgs_{uuid.uuid4().hex[:8]}')
    os.makedirs(out_dir, exist_ok=True)
    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=mat, alpha=False)
        out_path = os.path.join(out_dir, f'page_{i + 1:03d}.{fmt}')
        pix.save(out_path)
    zip_path = out_dir + '.zip'
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for fname in sorted(os.listdir(out_dir)):
            zf.write(os.path.join(out_dir, fname), fname)
    return zip_path
