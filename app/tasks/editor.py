import os
import uuid
import shutil
from flask import current_app


def edit_pdf_text(pdf_path, edits):
    """Copy the PDF as a placeholder — real PyMuPDF editing goes here."""
    output_path = os.path.join(current_app.config['UPLOAD_FOLDER'], f"{uuid.uuid4().hex}.pdf")
    shutil.copy(pdf_path, output_path)
    return output_path
