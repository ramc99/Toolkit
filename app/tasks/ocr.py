import os
import uuid
import subprocess
from flask import current_app


def ocr_image(image_path, lang='eng'):
    import pytesseract
    from PIL import Image
    img = Image.open(image_path)
    return pytesseract.image_to_string(img, lang=lang)


def ocr_pdf(pdf_path, lang='eng'):
    output_path = os.path.join(current_app.config['UPLOAD_FOLDER'], f"{uuid.uuid4().hex}.pdf")
    subprocess.check_call(['ocrmypdf', '--language', lang, pdf_path, output_path])
    return output_path
