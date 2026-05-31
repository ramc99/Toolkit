"""Launcher for the Splitting & Merging Flask app using the application factory.
Running this file starts the server and opens the UI in the browser.
"""

import os
import threading
import webbrowser

from app import create_app

# Use PORT environment variable if set, otherwise default to 5000
PORT = int(os.getenv("PORT", "5000"))

# Create the Flask app via the factory – this registers all blueprints (split/merge + PDF tools)
app = create_app()

if __name__ == "__main__":
    url = f"http://localhost:{PORT}"
    # Open the browser shortly after the server starts
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    print(f"Opening {url} ...")
    app.run(host="0.0.0.0", port=PORT, debug=False)
