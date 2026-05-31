import os
import uuid
import glob
from flask import Blueprint, render_template, request, abort, send_file, current_app, jsonify
from werkzeug.utils import secure_filename

image_toolkit = Blueprint('image_toolkit', __name__, url_prefix='/image')

_ALLOWED = {'png', 'jpg', 'jpeg', 'webp', 'bmp', 'tiff', 'gif'}


def _compressed_folder():
    folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'compressed')
    os.makedirs(folder, exist_ok=True)
    return folder


def _process_image(input_path, output_path, settings):
    """Full image processing: resize, enhancements, compress. Ported from Image-compressor."""
    import shutil
    from PIL import Image as PILImage, ImageEnhance, ImageFilter

    quality     = max(1, min(100, int(settings.get('quality', 60))))
    out_fmt     = settings.get('format', 'jpg').lower()
    resize_mode = settings.get('resize_mode', 'none')
    brightness  = float(settings.get('brightness', 1.0))
    contrast    = float(settings.get('contrast',   1.0))
    sharpness   = float(settings.get('sharpness',  1.0))
    blur        = float(settings.get('blur',        0.0))

    # Normalise input extension for comparison
    in_ext = os.path.splitext(input_path)[1].lstrip('.').lower()
    in_ext = 'jpg' if in_ext == 'jpeg' else in_ext
    out_ext = 'jpg' if out_fmt == 'jpeg' else out_fmt

    no_adjustments = (
        resize_mode == 'none'
        and brightness == 1.0
        and contrast   == 1.0
        and sharpness  == 1.0
        and blur       == 0.0
    )

    # At quality=100 with no adjustments and same format → copy original unchanged
    if quality == 100 and no_adjustments and in_ext == out_ext:
        shutil.copy2(input_path, output_path)
        with PILImage.open(output_path) as img:
            return img.size

    with PILImage.open(input_path) as img:
        orig_w, orig_h = img.size

        if resize_mode == 'percentage':
            pct = max(1, min(200, float(settings.get('resize_percent', 100)))) / 100
            img = img.resize((max(1, int(orig_w * pct)), max(1, int(orig_h * pct))), PILImage.LANCZOS)
        elif resize_mode == 'custom':
            rw = settings.get('resize_width')
            rh = settings.get('resize_height')
            locked = settings.get('lock_aspect', True)
            if rw and rh:
                img = img.resize((int(rw), int(rh)), PILImage.LANCZOS)
            elif rw:
                rw = max(1, int(rw))
                img = img.resize((rw, max(1, int(orig_h * rw / orig_w)) if locked else orig_h), PILImage.LANCZOS)
            elif rh:
                rh = max(1, int(rh))
                img = img.resize((max(1, int(orig_w * rh / orig_h)) if locked else orig_w, rh), PILImage.LANCZOS)

        if out_fmt in ('jpg', 'jpeg') and img.mode != 'RGB':
            img = img.convert('RGB')
        elif out_fmt == 'webp' and img.mode not in ('RGB', 'RGBA'):
            img = img.convert('RGB')

        if brightness != 1.0: img = ImageEnhance.Brightness(img).enhance(brightness)
        if contrast   != 1.0: img = ImageEnhance.Contrast(img).enhance(contrast)
        if sharpness  != 1.0: img = ImageEnhance.Sharpness(img).enhance(sharpness)
        if blur > 0:           img = img.filter(ImageFilter.GaussianBlur(radius=blur))

        fmt_map = {'jpg': 'JPEG', 'jpeg': 'JPEG', 'png': 'PNG', 'webp': 'WEBP'}
        pil_fmt = fmt_map.get(out_fmt, 'JPEG')

        if pil_fmt == 'JPEG':
            w, h = img.size
            progressive = (w * h) > 100_000
            img.save(output_path, 'JPEG', quality=quality, optimize=True, progressive=progressive)
            # If re-encoding made the file larger, fall back to the original
            if os.path.getsize(output_path) > os.path.getsize(input_path) and in_ext == 'jpg' and no_adjustments:
                import shutil as _sh
                _sh.copy2(input_path, output_path)
        elif pil_fmt == 'PNG':
            img.save(output_path, 'PNG', optimize=True, compress_level=9)
        else:
            img.save(output_path, 'WEBP', quality=quality, method=4)

        return img.size


def _allowed(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in _ALLOWED


def _save_upload(file):
    name = secure_filename(file.filename)
    path = os.path.join(current_app.config['UPLOAD_FOLDER'], name)
    file.save(path)
    return path


def _fmt_size(n):
    if n < 1024:
        return f'{n} B'
    if n < 1024 ** 2:
        return f'{n/1024:.1f} KB'
    return f'{n/1024**2:.1f} MB'


def _image_info(path):
    """Return dict with size, dimensions, format for a given image path."""
    from PIL import Image as PILImage
    size = os.path.getsize(path)
    try:
        with PILImage.open(path) as img:
            w, h = img.size
            fmt = img.format or os.path.splitext(path)[1][1:].upper()
    except Exception:
        w = h = 0
        fmt = os.path.splitext(path)[1][1:].upper()
    return {'size': size, 'size_fmt': _fmt_size(size), 'width': w, 'height': h, 'format': fmt}


def _preview_url(path):
    return f'/image/preview/{os.path.basename(path)}'


def _is_ajax():
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


def _comparison(upload_path, result, download_name):
    orig = _image_info(upload_path)
    res  = _image_info(result)
    saving = round((1 - res['size'] / orig['size']) * 100, 1) if orig['size'] else 0
    return jsonify({
        'original': {**orig, 'url': _preview_url(upload_path)},
        'result':   {**res,  'url': _preview_url(result)},
        'download_url':  f'/image/download/{os.path.basename(result)}',
        'download_name': download_name,
        'saving_pct':    saving,
    })


# ── Preview / download endpoints ─────────────────────────────────────────────

@image_toolkit.route('/preview/<filename>')
def preview(filename):
    safe = secure_filename(filename)
    for folder in (current_app.config['UPLOAD_FOLDER'],
                   current_app.config.get('OUTPUT_FOLDER', current_app.config['UPLOAD_FOLDER'])):
        path = os.path.join(folder, safe)
        if os.path.isfile(path):
            return send_file(path)
    # also check split/merge folders neighbour
    base = os.path.dirname(current_app.config['UPLOAD_FOLDER'])
    for root, dirs, files in os.walk(base):
        if safe in files:
            return send_file(os.path.join(root, safe))
    abort(404)


@image_toolkit.route('/download/<filename>')
def download(filename):
    safe = secure_filename(filename)
    base = os.path.dirname(current_app.config['UPLOAD_FOLDER'])
    for root, dirs, files in os.walk(base):
        if safe in files:
            return send_file(os.path.join(root, safe), as_attachment=True, download_name=safe)
    abort(404)


# ── Tools ─────────────────────────────────────────────────────────────────────

@image_toolkit.route('/')
def image_home():
    return render_template('image_home.html')


@image_toolkit.route('/convert', methods=['GET', 'POST'])
def convert():
    if request.method == 'POST':
        if 'file' not in request.files:
            abort(400, description='No file uploaded')
        f = request.files['file']
        if not f.filename or not _allowed(f.filename):
            abort(400, description='Unsupported image format')
        target = request.form.get('target_fmt', 'png').lower()
        if target not in _ALLOWED:
            abort(400, description='Unsupported target format')
        upload_path = _save_upload(f)
        from app.tasks.image import convert_image
        try:
            result = convert_image(upload_path, target)
        except Exception as e:
            current_app.logger.error('Image convert error: %s', e)
            abort(500, description=str(e))
        current_app.logger.info('Image convert: %s -> %s', upload_path, result)
        if _is_ajax():
            return _comparison(upload_path, result, os.path.basename(result))
        return send_file(result, as_attachment=True, download_name=os.path.basename(result))
    return render_template('image_convert.html')


@image_toolkit.route('/compress-upload', methods=['POST'])
def compress_upload():
    """Step 1: accept the original file, run default compression, return JSON with IDs + stats."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    f = request.files['file']
    if not f or not f.filename or not _allowed(f.filename):
        return jsonify({'error': 'Invalid file type'}), 400

    ext     = f.filename.rsplit('.', 1)[1].lower()
    file_id = uuid.uuid4().hex[:12]
    orig_fn = f'{file_id}_orig.{ext}'
    orig_path = os.path.join(current_app.config['UPLOAD_FOLDER'], orig_fn)
    f.save(orig_path)

    comp_folder = _compressed_folder()
    comp_fn   = f'{file_id}_comp.{ext}'
    comp_path = os.path.join(comp_folder, comp_fn)

    from PIL import Image as PILImage
    with PILImage.open(orig_path) as img:
        orig_w, orig_h = img.size
    orig_size = os.path.getsize(orig_path)

    try:
        _process_image(orig_path, comp_path, {'quality': 60, 'format': ext})
    except Exception as e:
        current_app.logger.error('compress-upload error: %s', e)
        return jsonify({'error': str(e)}), 500

    comp_size = os.path.getsize(comp_path)
    reduction = round((orig_size - comp_size) / orig_size * 100, 1) if orig_size else 0
    current_app.logger.info('Compress upload: %s orig=%d comp=%d (%.1f%%)', orig_fn, orig_size, comp_size, reduction)
    return jsonify({
        'file_id':          file_id,
        'orig_ext':         ext,
        'original_size':    orig_size,
        'original_size_str': _fmt_size(orig_size),
        'compressed_size':  comp_size,
        'compressed_size_str': _fmt_size(comp_size),
        'reduction_percent': reduction,
        'original_url':     f'/image/serve-orig/{orig_fn}',
        'compressed_url':   f'/image/serve-comp/{comp_fn}',
        'download_url':     f'/image/dl-comp/{comp_fn}',
        'orig_width': orig_w, 'orig_height': orig_h,
    })


@image_toolkit.route('/compress-process', methods=['POST'])
def compress_process():
    """Step 2: re-apply settings to the stored original, return updated stats."""
    data    = request.get_json(silent=True) or {}
    file_id = data.get('file_id', '')
    matches = glob.glob(os.path.join(current_app.config['UPLOAD_FOLDER'], f'{file_id}_orig.*'))
    if not matches:
        return jsonify({'error': 'Original not found — please re-upload'}), 404

    orig_path   = matches[0]
    out_fmt     = data.get('format', 'jpg').lower()
    ext         = 'jpg' if out_fmt in ('jpg', 'jpeg') else out_fmt
    comp_folder = _compressed_folder()
    comp_fn     = f'{file_id}_comp.{ext}'
    comp_path   = os.path.join(comp_folder, comp_fn)

    for old in glob.glob(os.path.join(comp_folder, f'{file_id}_comp.*')):
        try: os.remove(old)
        except OSError: pass

    try:
        final_w, final_h = _process_image(orig_path, comp_path, data)
    except Exception as e:
        current_app.logger.error('compress-process error: %s', e)
        return jsonify({'error': str(e)}), 500

    orig_size = os.path.getsize(orig_path)
    comp_size = os.path.getsize(comp_path)
    reduction = round((orig_size - comp_size) / orig_size * 100, 1) if orig_size else 0
    return jsonify({
        'compressed_size': comp_size,
        'compressed_size_str': _fmt_size(comp_size),
        'reduction_percent': reduction,
        'compressed_url':  f'/image/serve-comp/{comp_fn}',
        'download_url':    f'/image/dl-comp/{comp_fn}',
        'output_width': final_w, 'output_height': final_h,
    })


@image_toolkit.route('/serve-orig/<filename>')
def serve_orig(filename):
    path = os.path.join(current_app.config['UPLOAD_FOLDER'], secure_filename(filename))
    return send_file(path) if os.path.isfile(path) else abort(404)


@image_toolkit.route('/serve-comp/<filename>')
def serve_comp(filename):
    path = os.path.join(_compressed_folder(), secure_filename(filename))
    return send_file(path) if os.path.isfile(path) else abort(404)


@image_toolkit.route('/dl-comp/<filename>')
def dl_comp(filename):
    safe = secure_filename(filename)
    path = os.path.join(_compressed_folder(), safe)
    return send_file(path, as_attachment=True, download_name=safe) if os.path.isfile(path) else abort(404)


@image_toolkit.route('/compress', methods=['GET', 'POST'])
def compress():
    if request.method == 'POST':
        if 'file' not in request.files:
            abort(400, description='No file uploaded')
        f = request.files['file']
        if not f.filename or not _allowed(f.filename):
            abort(400, description='Unsupported image format')
        quality = request.form.get('quality', 60)
        upload_path = _save_upload(f)
        from app.tasks.image import compress_image
        try:
            result = compress_image(upload_path, quality=int(quality))
        except Exception as e:
            current_app.logger.error('Image compress error: %s', e)
            abort(500, description=str(e))
        orig_size = os.path.getsize(upload_path)
        new_size  = os.path.getsize(result)
        current_app.logger.info('Image compress: %s bytes -> %s bytes', orig_size, new_size)
        if _is_ajax():
            return _comparison(upload_path, result, os.path.basename(result))
        return send_file(result, as_attachment=True, download_name=os.path.basename(result))
    return render_template('image_compress.html')


@image_toolkit.route('/resize', methods=['GET', 'POST'])
def resize():
    if request.method == 'POST':
        if 'file' not in request.files:
            abort(400, description='No file uploaded')
        f = request.files['file']
        if not f.filename or not _allowed(f.filename):
            abort(400, description='Unsupported image format')
        try:
            width  = int(request.form.get('width', 800))
            height = int(request.form.get('height', 600))
        except ValueError:
            abort(400, description='Width and height must be integers')
        keep_aspect = request.form.get('keep_aspect', 'true') == 'true'
        upload_path = _save_upload(f)
        from app.tasks.image import resize_image
        try:
            result = resize_image(upload_path, width, height, keep_aspect=keep_aspect)
        except Exception as e:
            current_app.logger.error('Image resize error: %s', e)
            abort(500, description=str(e))
        current_app.logger.info('Image resize: %s -> %dx%d', upload_path, width, height)
        if _is_ajax():
            return _comparison(upload_path, result, os.path.basename(result))
        return send_file(result, as_attachment=True, download_name=os.path.basename(result))
    return render_template('image_resize.html')


@image_toolkit.route('/to-pdf', methods=['GET', 'POST'])
def to_pdf():
    if request.method == 'POST':
        files = request.files.getlist('files')
        valid = [f for f in files if f.filename and _allowed(f.filename)]
        if not valid:
            abort(400, description='No valid image files provided')
        paths = [_save_upload(f) for f in valid]
        from app.tasks.image import images_to_pdf
        try:
            result = images_to_pdf(paths)
        except Exception as e:
            current_app.logger.error('Images to PDF error: %s', e)
            abort(500, description=str(e))
        current_app.logger.info('Images to PDF: %d images -> %s', len(paths), result)
        return send_file(result, as_attachment=True, download_name='images.pdf')
    return render_template('image_to_pdf.html')


@image_toolkit.route('/rotate', methods=['GET', 'POST'])
def rotate():
    if request.method == 'POST':
        if 'file' not in request.files:
            abort(400, description='No file uploaded')
        f = request.files['file']
        if not f.filename or not _allowed(f.filename):
            abort(400, description='Unsupported image format')
        degrees   = request.form.get('degrees', '90')
        direction = request.form.get('direction', 'rotate')
        upload_path = _save_upload(f)
        from app.tasks.image import rotate_image, flip_image
        try:
            if direction == 'flip_h':
                result = flip_image(upload_path, 'horizontal')
            elif direction == 'flip_v':
                result = flip_image(upload_path, 'vertical')
            else:
                result = rotate_image(upload_path, degrees=int(degrees))
        except Exception as e:
            current_app.logger.error('Image rotate/flip error: %s', e)
            abort(500, description=str(e))
        current_app.logger.info('Image transform: %s dir=%s deg=%s', upload_path, direction, degrees)
        if _is_ajax():
            return _comparison(upload_path, result, os.path.basename(result))
        return send_file(result, as_attachment=True, download_name=os.path.basename(result))
    return render_template('image_rotate.html')


@image_toolkit.route('/crop', methods=['GET', 'POST'])
def crop():
    if request.method == 'POST':
        if 'file' not in request.files:
            abort(400, description='No file uploaded')
        f = request.files['file']
        if not f.filename or not _allowed(f.filename):
            abort(400, description='Unsupported image format')
        upload_path = _save_upload(f)
        from PIL import Image as _PIL
        with _PIL.open(upload_path) as _im:
            orig_w, orig_h = _im.size
        left   = float(request.form.get('left',   0))
        top    = float(request.form.get('top',    0))
        right  = float(request.form.get('right',  orig_w))
        bottom = float(request.form.get('bottom', orig_h))
        from app.tasks.image import crop_image
        try:
            result = crop_image(upload_path, left, top, right, bottom)
        except Exception as e:
            current_app.logger.error('Crop error: %s', e)
            abort(500, description=str(e))
        current_app.logger.info('Image crop: %s box=(%s,%s,%s,%s)', upload_path, left, top, right, bottom)
        if _is_ajax():
            return _comparison(upload_path, result, os.path.basename(result))
        return send_file(result, as_attachment=True, download_name=os.path.basename(result))
    return render_template('image_crop.html')


@image_toolkit.route('/watermark', methods=['GET', 'POST'])
def watermark():
    if request.method == 'POST':
        if 'file' not in request.files:
            abort(400, description='No file uploaded')
        f = request.files['file']
        if not f.filename or not _allowed(f.filename):
            abort(400, description='Unsupported image format')
        text      = request.form.get('text', 'WATERMARK').strip() or 'WATERMARK'
        position  = request.form.get('position', 'center')
        opacity   = int(request.form.get('opacity', 40))
        font_size = int(request.form.get('font_size', 36))
        upload_path = _save_upload(f)
        from app.tasks.image import watermark_image
        try:
            result = watermark_image(upload_path, text, position, opacity, font_size)
        except Exception as e:
            current_app.logger.error('Watermark error: %s', e)
            abort(500, description=str(e))
        current_app.logger.info('Image watermark: %s text=%s pos=%s', upload_path, text, position)
        if _is_ajax():
            return _comparison(upload_path, result, os.path.basename(result))
        return send_file(result, as_attachment=True, download_name=os.path.basename(result))
    return render_template('image_watermark.html')


@image_toolkit.route('/collage', methods=['GET', 'POST'])
def collage():
    if request.method == 'POST':
        files = request.files.getlist('files')
        files = [f for f in files if f.filename and _allowed(f.filename)]
        if len(files) < 2:
            abort(400, description='Upload at least 2 images')
        layout = request.form.get('layout', 'horizontal')
        gap    = int(request.form.get('gap', 10))
        paths  = [_save_upload(f) for f in files]
        from app.tasks.image import collage_images
        try:
            result = collage_images(paths, layout=layout, gap=gap)
        except Exception as e:
            current_app.logger.error('Collage error: %s', e)
            abort(500, description=str(e))
        current_app.logger.info('Image collage: %d images layout=%s', len(paths), layout)
        return send_file(result, as_attachment=True, download_name='collage.jpg')
    return render_template('image_collage.html')


@image_toolkit.route('/remove-bg', methods=['GET', 'POST'])
def remove_bg():
    if request.method == 'POST':
        if 'file' not in request.files:
            abort(400, description='No file uploaded')
        f = request.files['file']
        if not f.filename or not _allowed(f.filename):
            abort(400, description='Unsupported image format')
        upload_path = _save_upload(f)
        from app.tasks.image import remove_background
        try:
            result = remove_background(upload_path)
        except Exception as e:
            current_app.logger.error('BG remove error: %s', e)
            abort(500, description=str(e))
        current_app.logger.info('BG remove: %s', upload_path)
        if _is_ajax():
            return _comparison(upload_path, result, os.path.basename(result))
        return send_file(result, as_attachment=True, download_name='background_removed.png')
    return render_template('image_remove_bg.html')


@image_toolkit.route('/blur-faces', methods=['GET', 'POST'])
def blur_faces():
    if request.method == 'POST':
        if 'file' not in request.files:
            abort(400, description='No file uploaded')
        f = request.files['file']
        if not f.filename or not _allowed(f.filename):
            abort(400, description='Unsupported image format')
        strength = int(request.form.get('strength', 25))
        strength = max(5, min(99, strength))
        upload_path = _save_upload(f)
        from app.tasks.image import blur_faces as _blur
        try:
            result, face_count = _blur(upload_path, blur_strength=strength)
        except Exception as e:
            current_app.logger.error('Face blur error: %s', e)
            abort(500, description=str(e))
        current_app.logger.info('Face blur: %s faces=%d', upload_path, face_count)
        if _is_ajax():
            resp = _comparison(upload_path, result, os.path.basename(result))
            from flask import jsonify
            return resp
        return send_file(result, as_attachment=True, download_name=os.path.basename(result))
    return render_template('image_blur_faces.html')
