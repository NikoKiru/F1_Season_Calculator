"""
Centralized error handlers for the F1 Season Calculator.

Provides consistent error responses across all API endpoints and views.
"""
from flask import render_template, jsonify, request, Blueprint

try:
    from .validators import (
        ErrorCode,
        ValidationError,
        NotFoundError,
        build_error_response,
        format_validation_error,
        format_not_found_error,
    )
except ImportError:
    from championship.validators import (
        ErrorCode,
        ValidationError,
        NotFoundError,
        build_error_response,
        format_validation_error,
        format_not_found_error,
    )

errors_bp = Blueprint('errors', __name__)


def is_api_request() -> bool:
    """Check if the current request is for an API endpoint."""
    return request.path.startswith('/api/')


@errors_bp.app_errorhandler(ValidationError)
def handle_validation_error(error):
    """Handle ValidationError exceptions."""
    response, status = format_validation_error(error)
    return jsonify(response), status


@errors_bp.app_errorhandler(NotFoundError)
def handle_not_found_error(error):
    """Handle NotFoundError exceptions."""
    response, status = format_not_found_error(error)
    return jsonify(response), status


@errors_bp.app_errorhandler(400)
def bad_request_error(error):
    """Handle 400 Bad Request errors."""
    if is_api_request():
        response, status = build_error_response(
            code=ErrorCode.BAD_REQUEST,
            message=str(error.description) if hasattr(error, 'description') else "Bad request"
        )
        return jsonify(response), status
    return render_template('errors/400.html'), 400


@errors_bp.app_errorhandler(404)
def not_found_error(error):
    """Handle 404 Not Found errors."""
    if is_api_request():
        response, status = build_error_response(
            code=ErrorCode.NOT_FOUND,
            message="The requested resource was not found"
        )
        return jsonify(response), status
    return render_template('404.html'), 404


@errors_bp.app_errorhandler(405)
def method_not_allowed_error(error):
    """Handle 405 Method Not Allowed errors."""
    if is_api_request():
        response, status = build_error_response(
            code=ErrorCode.BAD_REQUEST,
            message=f"Method not allowed for this endpoint",
            http_status=405
        )
        return jsonify(response), 405
    return render_template('errors/405.html'), 405


@errors_bp.app_errorhandler(500)
def internal_error(error):
    """Handle 500 Internal Server Error."""
    # In a real app, you'd want to log the error.
    # current_app.logger.error(f"Server Error: {error}", exc_info=True)
    if is_api_request():
        response, status = build_error_response(
            code=ErrorCode.INTERNAL_ERROR,
            message="An unexpected error occurred. Please try again later."
        )
        return jsonify(response), status
    return render_template('500.html'), 500


def init_app(app):
    """Register error handlers with the Flask app."""
    app.register_blueprint(errors_bp)
