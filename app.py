"""
Flask application entry point.

This file creates the Flask app instance and makes it importable
for the Flask CLI and WSGI servers.
"""
# Import create_app from the __init__ module in the current directory
from __init__ import create_app

app = create_app()

if __name__ == '__main__':
    app.run()
