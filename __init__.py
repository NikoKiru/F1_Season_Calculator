import os
from typing import Optional, Dict, Any
from flask import Flask
from flask_caching import Cache

# Initialize cache instance (configured in create_app)
cache: Cache = Cache()


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

    # Import modules - try relative first, then absolute
    try:
        from . import db
    except ImportError:
        import db
    db.init_app(app)

    from flasgger import Swagger
    Swagger(app)

    # Register blueprints from the championship module
    try:
        from .championship import api, commands, views, errors
    except ImportError:
        from championship import api, commands, views, errors
    app.register_blueprint(views.bp)
    app.register_blueprint(api.bp)
    errors.init_app(app)
    commands.init_app(app)

    return app
