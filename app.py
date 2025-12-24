"""
Flask application entry point.

This file creates the Flask app instance and makes it importable
for the Flask CLI and WSGI servers.
"""
import sys
import os

# Add the current directory to path if needed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import create_app from __init__.py
from __init__ import create_app  # noqa: E402
from flask import Flask

app: Flask = create_app()

if __name__ == '__main__':
    app.run()
