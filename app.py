"""
Flask application entry point.

This file creates the Flask app instance and makes it importable
for the Flask CLI and WSGI servers.
"""
import sys
import os
from flask import Flask

# Add the current directory to path if needed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import create_app from __init__.py
from __init__ import create_app  # noqa: E402


app: Flask = create_app()

if __name__ == '__main__':
    use_dev = '--debug' in sys.argv or '--dev' in sys.argv
    if use_dev:
        app.run(debug=True)
    else:
        from waitress import serve
        print("Starting production server with Waitress on http://127.0.0.1:5000")
        print("Use --debug flag for Flask development server")
        serve(app, host='0.0.0.0', port=5000, threads=4)
