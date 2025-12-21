from flask import render_template, jsonify, request, Blueprint

errors_bp = Blueprint('errors', __name__)


@errors_bp.app_errorhandler(404)
def not_found_error(error):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Not Found'}), 404
    return render_template('404.html'), 404


@errors_bp.app_errorhandler(500)
def internal_error(error):
    # In a real app, you'd want to log the error.
    # current_app.logger.error(f"Server Error: {error}", exc_info=True)
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Internal Server Error'}), 500
    return render_template('500.html'), 500


def init_app(app):
    app.register_blueprint(errors_bp)
