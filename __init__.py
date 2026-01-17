import os
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional, Dict, Any
from flask import Flask
from flask_caching import Cache

# Initialize cache instance (configured in create_app)
cache: Cache = Cache()


def configure_logging(app: Flask) -> None:
    """Configure application logging with rotating file handler.

    Sets up structured logging to a file with rotation when not in debug/testing mode.
    Logs are written to logs/f1_calculator.log with a 10MB max size and 10 backup files.
    The log directory can be configured via LOG_FOLDER in app config.

    Args:
        app: The Flask application instance.
    """
    if app.debug or app.testing:
        return

    # Use configured log folder or default to logs/ in app root
    log_dir = app.config.get('LOG_FOLDER', os.path.join(app.root_path, 'logs'))
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, 'f1_calculator.log')
    handler = RotatingFileHandler(
        log_file,
        maxBytes=10240000,  # 10MB
        backupCount=10
    )
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)


def create_app(test_config: Optional[Dict[str, Any]] = None) -> Flask:
    """Create and configure the Flask application.

    Args:
        test_config: Optional configuration dictionary for testing.

    Returns:
        Configured Flask application instance.
    """
    # Set instance folder to be inside the project directory (not parent)
    # By default Flask puts instance in parent dir, but we want it in the project
    instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')

    # create and configure the app
    app = Flask(__name__, instance_relative_config=True, instance_path=instance_path)

    # Default configuration
    # Support environment variables for flexible deployment
    default_db_path = os.path.join(app.instance_path, 'championships.db')
    # Data folder inside the project (app.root_path is the package directory)
    default_data_folder = os.path.join(app.root_path, 'data')

    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'),
        DATABASE=os.environ.get('DATABASE_PATH', default_db_path),
        DATA_FOLDER=os.environ.get('DATA_FOLDER', default_data_folder),
        # Cache configuration - thread-safe SimpleCache by default
        # Can be changed to Redis for production: CACHE_TYPE='redis'
        CACHE_TYPE=os.environ.get('CACHE_TYPE', 'SimpleCache'),
        CACHE_DEFAULT_TIMEOUT=os.environ.get('CACHE_TIMEOUT', 3600),
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # Normalize paths (resolve relative paths)
    app.config['DATABASE'] = os.path.abspath(app.config['DATABASE'])
    app.config['DATA_FOLDER'] = os.path.abspath(app.config['DATA_FOLDER'])

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass

    # Initialize Flask-Caching with app
    cache.init_app(app)

    # Initialize database
    import db
    db.init_app(app)

    # Initialize Swagger documentation
    from flasgger import Swagger
    Swagger(app)

    # Register blueprints and commands from the championship module
    from championship import api_bp, views_bp, init_errors, init_all_commands
    app.register_blueprint(views_bp)
    app.register_blueprint(api_bp)
    init_errors(app)
    init_all_commands(app)

    # Configure logging
    configure_logging(app)
    app.logger.info('F1 Calculator startup')

    return app
