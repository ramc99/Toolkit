import os
import uuid
from flask import current_app


def protect_pdf(pdf_path, password):
    from PyPDF2 import PdfWriter, PdfReader
    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt(user_pwd=password, owner_pwd=None, use_128bit=True)
    output_path = os.path.join(current_app.config['UPLOAD_FOLDER'], f"{uuid.uuid4().hex}.pdf")
    with open(output_path, 'wb') as f:
        writer.write(f)
    return output_path


def unlock_pdf(pdf_path, password):
    from PyPDF2 import PdfWriter, PdfReader
    reader = PdfReader(pdf_path)
    if reader.is_encrypted:
        reader.decrypt(password)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    output_path = os.path.join(current_app.config['UPLOAD_FOLDER'], f"{uuid.uuid4().hex}.pdf")
    with open(output_path, 'wb') as f:
        writer.write(f)
    return output_path
