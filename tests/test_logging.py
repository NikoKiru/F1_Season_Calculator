"""Tests for application logging configuration."""
import os
import sys
import tempfile
import logging

import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from __init__ import create_app, configure_logging  # noqa: E402


def close_log_handlers(app):
    """Close and remove all file handlers from the app logger."""
    handlers_to_remove = []
    for handler in app.logger.handlers:
        if hasattr(handler, 'close'):
            handler.close()
        handlers_to_remove.append(handler)
    for handler in handlers_to_remove:
        app.logger.removeHandler(handler)


class TestLoggingConfiguration:
    """Test suite for logging configuration."""

    def test_configure_logging_skips_in_debug_mode(self):
        """Logging configuration should be skipped when app is in debug mode."""
        app = create_app({'TESTING': True, 'DEBUG': True})
        app.debug = True

        # Store original handler count
        original_handler_count = len(app.logger.handlers)

        configure_logging(app)

        # Should not add new handlers in debug mode
        assert len(app.logger.handlers) == original_handler_count

    def test_configure_logging_skips_in_testing_mode(self):
        """Logging configuration should be skipped when app is in testing mode."""
        app = create_app({'TESTING': True})

        # Store original handler count
        original_handler_count = len(app.logger.handlers)

        configure_logging(app)

        # Should not add new handlers in testing mode
        assert len(app.logger.handlers) == original_handler_count

    def test_configure_logging_creates_log_directory(self):
        """Logging configuration should create logs directory when not in debug/testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, 'test.db')
            log_dir = os.path.join(temp_dir, 'logs')
            app = create_app({
                'TESTING': False,
                'DEBUG': False,
                'DATABASE': db_path,
                'LOG_FOLDER': log_dir,
            })
            app.testing = False
            app.debug = False

            try:
                configure_logging(app)

                # Check that logs directory was created
                assert os.path.exists(log_dir)
            finally:
                close_log_handlers(app)

    def test_configure_logging_adds_file_handler(self):
        """Logging configuration should add a RotatingFileHandler."""
        from logging.handlers import RotatingFileHandler

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, 'test.db')
            log_dir = os.path.join(temp_dir, 'logs')
            app = create_app({
                'TESTING': False,
                'DEBUG': False,
                'DATABASE': db_path,
                'LOG_FOLDER': log_dir,
            })
            app.testing = False
            app.debug = False

            try:
                configure_logging(app)

                # Check that a RotatingFileHandler was added
                rotating_handlers = [
                    h for h in app.logger.handlers
                    if isinstance(h, RotatingFileHandler)
                ]
                assert len(rotating_handlers) >= 1
            finally:
                close_log_handlers(app)

    def test_configure_logging_sets_info_level(self):
        """Logging should be set to INFO level."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, 'test.db')
            log_dir = os.path.join(temp_dir, 'logs')
            app = create_app({
                'TESTING': False,
                'DEBUG': False,
                'DATABASE': db_path,
                'LOG_FOLDER': log_dir,
            })
            app.testing = False
            app.debug = False

            try:
                configure_logging(app)

                assert app.logger.level == logging.INFO
            finally:
                close_log_handlers(app)

    def test_logging_writes_to_file(self):
        """Verify that log messages are written to the log file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, 'test.db')
            log_dir = os.path.join(temp_dir, 'logs')
            app = create_app({
                'TESTING': False,
                'DEBUG': False,
                'DATABASE': db_path,
                'LOG_FOLDER': log_dir,
            })
            app.testing = False
            app.debug = False

            try:
                configure_logging(app)

                # Write a test log message
                test_message = 'Test log message for verification'
                app.logger.info(test_message)

                # Force flush all handlers
                for handler in app.logger.handlers:
                    handler.flush()

                # Check log file contents
                log_file = os.path.join(log_dir, 'f1_calculator.log')
                assert os.path.exists(log_file)
                with open(log_file, 'r') as f:
                    log_contents = f.read()
                assert test_message in log_contents
            finally:
                close_log_handlers(app)

    def test_log_format_contains_required_fields(self):
        """Verify that log format includes timestamp, level, message, and location."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, 'test.db')
            log_dir = os.path.join(temp_dir, 'logs')
            app = create_app({
                'TESTING': False,
                'DEBUG': False,
                'DATABASE': db_path,
                'LOG_FOLDER': log_dir,
            })
            app.testing = False
            app.debug = False

            try:
                configure_logging(app)

                # Write a test log message
                app.logger.info('Format test message')

                # Force flush
                for handler in app.logger.handlers:
                    handler.flush()

                # Check log file contents
                log_file = os.path.join(log_dir, 'f1_calculator.log')
                with open(log_file, 'r') as f:
                    log_contents = f.read()

                # Verify format contains expected components
                assert 'INFO' in log_contents
                assert 'Format test message' in log_contents
                assert '[in' in log_contents  # pathname:lineno marker
            finally:
                close_log_handlers(app)
