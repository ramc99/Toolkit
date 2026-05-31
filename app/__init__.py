from flask import Flask, request, g
import os
import time
import logging
import config

def create_app():
    app = Flask(__name__)

    # ── Logging setup ────────────────────────────────────────────────────────
    log_file_path = os.path.join(config.BASE_DIR, 'app.log')
    fmt = logging.Formatter('%(asctime)s  %(levelname)-8s  %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(fmt)

    if not app.logger.handlers:
        app.logger.addHandler(file_handler)
        app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.DEBUG)

    # ── Request / response logging ───────────────────────────────────────────
    @app.before_request
    def _before():
        g.t0 = time.perf_counter()
        # Skip logging for static assets
        if not request.path.startswith('/static'):
            app.logger.info('→ %s %s  ip=%s  ua=%s',
                request.method, request.path,
                request.remote_addr,
                (request.user_agent.string or '')[:80])

    @app.after_request
    def _after(response):
        if not request.path.startswith('/static'):
            ms = (time.perf_counter() - g.t0) * 1000
            app.logger.info('← %s %s  status=%d  %.1fms',
                request.method, request.path,
                response.status_code, ms)
        return response

    @app.teardown_request
    def _teardown(exc):
        if exc:
            app.logger.error('Unhandled exception on %s %s: %s',
                request.method, request.path, exc, exc_info=exc)

    # ── Config & folders ─────────────────────────────────────────────────────
    app.config.from_object(config)
    for folder in (app.config["UPLOAD_FOLDER"], app.config["SPLIT_FOLDER"], app.config["MERGE_FOLDER"]):
        os.makedirs(folder, exist_ok=True)

    # ── Blueprints ───────────────────────────────────────────────────────────
    from .routes import bp
    app.register_blueprint(bp)

    from .pdf_toolkit import pdf_toolkit
    app.register_blueprint(pdf_toolkit)

    from .image_toolkit import image_toolkit
    app.register_blueprint(image_toolkit)

    from .resume import resume_bp
    app.register_blueprint(resume_bp)

    from .cover_letter import cover_letter_bp
    app.register_blueprint(cover_letter_bp)

    from .invoice import invoice_bp
    app.register_blueprint(invoice_bp)

    app.logger.info('App started — upload=%s  split=%s  merge=%s',
        app.config["UPLOAD_FOLDER"], app.config["SPLIT_FOLDER"], app.config["MERGE_FOLDER"])
    return app
