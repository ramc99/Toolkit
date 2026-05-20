import os
import secrets

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
SPLIT_FOLDER = os.path.join(BASE_DIR, 'splits')
MERGE_FOLDER = os.path.join(BASE_DIR, 'merged')

# Limit uploads to 50 MB total
MAX_CONTENT_LENGTH = 50 * 1024 * 1024

# Enforce at least this many rows per split file
MIN_ROWS_PER_FILE = 10
# Default rows per split if user does not specify
DEFAULT_ROWS_PER_SPLIT = 1000

ALLOWED_EXTENSIONS = {"csv", "tsv"}
