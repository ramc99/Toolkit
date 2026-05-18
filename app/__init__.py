from flask import Flask
import os
from csv_flask_app import config

def create_app():
    """Factory to create the Flask application."""
    app = Flask(__name__)
    # Load configuration values from config.py
    app.config.from_object(config)

    # Ensure required directories exist
    for folder in (app.config["UPLOAD_FOLDER"], app.config["SPLIT_FOLDER"], app.config["MERGE_FOLDER"]):
        os.makedirs(folder, exist_ok=True)

    # Register blueprints (routes are defined in app.routes)
    from .routes import bp
    app.register_blueprint(bp)

    return app
