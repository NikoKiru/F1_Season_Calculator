import os
from flask import Flask

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'championships.db'),
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    from . import db
    db.init_app(app)

    from . import f1
    f1.init_app(app)

    # Move the database file to the instance folder
    db_path = os.path.join(app.root_path, 'championships.db')
    instance_db_path = app.config['DATABASE']
    if os.path.exists(db_path) and not os.path.exists(instance_db_path):
        os.rename(db_path, instance_db_path)

    from flasgger import Swagger
    swagger = Swagger(app)

    # Register blueprints here
    from . import app as main_app
    app.register_blueprint(main_app.bp)

    return app
