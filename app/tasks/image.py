import os
import uuid
from flask import current_app
from PIL import Image

SUPPORTED_FORMATS = {'png', 'jpg', 'jpeg', 'webp', 'bmp', 'tiff', 'gif'}
PIL_FORMAT_MAP = {
    'jpg': 'JPEG',
    'jpeg': 'JPEG',
    'png': 'PNG',
    'webp': 'WEBP',
    'bmp': 'BMP',
    'tiff': 'TIFF',
    'gif': 'GIF',
}


def _out_path(ext):
    return os.path.join(current_app.config['UPLOAD_FOLDER'], f"{uuid.uuid4().hex}.{ext}")


def convert_image(input_path, target_fmt):
    """Convert image to target format (png/jpg/webp/bmp/tiff)."""
    target_fmt = target_fmt.lower().lstrip('.')
    pil_fmt = PIL_FORMAT_MAP.get(target_fmt, target_fmt.upper())
    img = Image.open(input_path).convert('RGB' if pil_fmt == 'JPEG' else 'RGBA' if pil_fmt == 'PNG' else 'RGB')
    out = _out_path(target_fmt if target_fmt != 'jpeg' else 'jpg')
    img.save(out, format=pil_fmt)
    return out


def compress_image(input_path, quality=60):
    """Re-save image at reduced quality (JPEG/WEBP). Returns output path."""
    img = Image.open(input_path)
    ext = os.path.splitext(input_path)[1].lower().lstrip('.')
    save_fmt = PIL_FORMAT_MAP.get(ext, 'JPEG')
    out_ext = 'jpg' if save_fmt == 'JPEG' else ext
    out = _out_path(out_ext)
    if save_fmt in ('JPEG', 'WEBP'):
        img.convert('RGB').save(out, format=save_fmt, quality=int(quality), optimize=True)
    else:
        img.save(out, format=save_fmt, optimize=True)
    return out


def resize_image(input_path, width, height, keep_aspect=True):
    """Resize image to (width, height). If keep_aspect, uses thumbnail mode."""
    img = Image.open(input_path)
    if keep_aspect:
        img.thumbnail((int(width), int(height)), Image.LANCZOS)
    else:
        img = img.resize((int(width), int(height)), Image.LANCZOS)
    ext = os.path.splitext(input_path)[1].lower().lstrip('.')
    out = _out_path(ext if ext != 'jpeg' else 'jpg')
    save_fmt = PIL_FORMAT_MAP.get(ext, 'PNG')
    if save_fmt == 'JPEG':
        img = img.convert('RGB')
    img.save(out, format=save_fmt)
    return out


def images_to_pdf(image_paths):
    """Combine a list of image file paths into a single PDF."""
    pil_images = [Image.open(p).convert('RGB') for p in image_paths]
    out = _out_path('pdf')
    pil_images[0].save(out, save_all=True, append_images=pil_images[1:])
    return out


def flip_image(input_path, direction='horizontal'):
    """Flip image horizontally or vertically."""
    img = Image.open(input_path)
    img = img.transpose(Image.FLIP_LEFT_RIGHT if direction == 'horizontal' else Image.FLIP_TOP_BOTTOM)
    ext = os.path.splitext(input_path)[1].lower().lstrip('.')
    out = _out_path(ext if ext != 'jpeg' else 'jpg')
    save_fmt = PIL_FORMAT_MAP.get(ext, 'PNG')
    if save_fmt == 'JPEG':
        img = img.convert('RGB')
    img.save(out, format=save_fmt)
    return out


def rotate_image(input_path, degrees=90):
    """Rotate image by given degrees (90, 180, 270)."""
    img = Image.open(input_path)
    img = img.rotate(-int(degrees), expand=True)
    ext = os.path.splitext(input_path)[1].lower().lstrip('.')
    out = _out_path(ext if ext != 'jpeg' else 'jpg')
    save_fmt = PIL_FORMAT_MAP.get(ext, 'PNG')
    if save_fmt == 'JPEG':
        img = img.convert('RGB')
    img.save(out, format=save_fmt)
    return out


def crop_image(input_path, left, top, right, bottom):
    from PIL import Image
    import os, uuid
    with Image.open(input_path) as img:
        w, h = img.size
        box = (max(0, int(left)), max(0, int(top)), min(w, int(right)), min(h, int(bottom)))
        cropped = img.crop(box)
        ext = os.path.splitext(input_path)[1]
        out = os.path.join(os.path.dirname(input_path), f'crop_{uuid.uuid4().hex[:8]}{ext}')
        if cropped.mode != 'RGB' and ext.lower() in ('.jpg', '.jpeg'):
            cropped = cropped.convert('RGB')
        cropped.save(out)
        return out


def watermark_image(input_path, text, position='center', opacity=40, font_size=36):
    from PIL import Image, ImageDraw, ImageFont
    import os, uuid
    with Image.open(input_path).convert('RGBA') as base:
        w, h = base.size
        txt_layer = Image.new('RGBA', base.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(txt_layer)
        try:
            font = ImageFont.truetype('/usr/share/fonts/liberation/LiberationSans-Bold.ttf', font_size)
        except Exception:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        positions = {
            'center':       ((w - tw) // 2, (h - th) // 2),
            'bottom-right': (w - tw - 20,   h - th - 20),
            'bottom-left':  (20,             h - th - 20),
            'top-right':    (w - tw - 20,   20),
            'top-left':     (20,             20),
        }
        x, y = positions.get(position, positions['center'])
        alpha = int(255 * max(0, min(100, int(opacity))) / 100)
        draw.text((x, y), text, font=font, fill=(255, 255, 255, alpha))
        draw.text((x + 1, y + 1), text, font=font, fill=(0, 0, 0, alpha // 2))
        out_img = Image.alpha_composite(base, txt_layer).convert('RGB')
        ext = os.path.splitext(input_path)[1]
        if ext.lower() in ('.png',):
            out_img = Image.alpha_composite(base, txt_layer)
        out = os.path.join(os.path.dirname(input_path), f'wm_{uuid.uuid4().hex[:8]}{ext}')
        out_img.save(out)
        return out


def collage_images(image_paths, layout='horizontal', gap=10, bg_color=(255, 255, 255)):
    from PIL import Image
    import os, uuid
    imgs = [Image.open(p).convert('RGB') for p in image_paths]
    if layout == 'horizontal':
        h = max(im.height for im in imgs)
        imgs = [im.resize((int(im.width * h / im.height), h)) for im in imgs]
        total_w = sum(im.width for im in imgs) + gap * (len(imgs) - 1)
        canvas = Image.new('RGB', (total_w, h), bg_color)
        x = 0
        for im in imgs:
            canvas.paste(im, (x, 0))
            x += im.width + gap
    elif layout == 'vertical':
        w = max(im.width for im in imgs)
        imgs = [im.resize((w, int(im.height * w / im.width))) for im in imgs]
        total_h = sum(im.height for im in imgs) + gap * (len(imgs) - 1)
        canvas = Image.new('RGB', (w, total_h), bg_color)
        y = 0
        for im in imgs:
            canvas.paste(im, (0, y))
            y += im.height + gap
    else:  # grid
        cols = 2
        rows = (len(imgs) + cols - 1) // cols
        cell_w = max(im.width for im in imgs)
        cell_h = max(im.height for im in imgs)
        imgs = [im.resize((cell_w, cell_h)) for im in imgs]
        canvas = Image.new('RGB', (cols * cell_w + gap * (cols - 1), rows * cell_h + gap * (rows - 1)), bg_color)
        for idx, im in enumerate(imgs):
            r, c = divmod(idx, cols)
            canvas.paste(im, (c * (cell_w + gap), r * (cell_h + gap)))
    out = os.path.join(os.path.dirname(image_paths[0]), f'collage_{uuid.uuid4().hex[:8]}.jpg')
    canvas.save(out, 'JPEG', quality=90)
    return out


def remove_background(input_path):
    from rembg import remove
    from PIL import Image as PILImage
    with open(input_path, 'rb') as f:
        data = f.read()
    result = remove(data)
    out = os.path.join(os.path.dirname(input_path), f'nobg_{uuid.uuid4().hex[:8]}.png')
    with open(out, 'wb') as f:
        f.write(result)
    return out


def blur_faces(input_path, blur_strength=25):
    import cv2
    img = cv2.imread(input_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    detector = cv2.CascadeClassifier(cascade_path)
    faces = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    face_count = len(faces)
    for (x, y, w, h) in faces:
        roi = img[y:y+h, x:x+w]
        k = blur_strength if blur_strength % 2 == 1 else blur_strength + 1
        img[y:y+h, x:x+w] = cv2.GaussianBlur(roi, (k, k), 0)
    ext = os.path.splitext(input_path)[1]
    out = os.path.join(os.path.dirname(input_path), f'faceblur_{uuid.uuid4().hex[:8]}{ext}')
    cv2.imwrite(out, img)
    return out, face_count
