from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from config import config


db = SQLAlchemy()


def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    db.init_app(app)

    # if not app.debug and not app.testing and not app.config['SSL_DISABLE']:
    #     from flask_sslify import SSLify
    #     sslify = SSLify(app)

    from .app import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from . import filters
    app.jinja_env.filters['format_point_differential'] = filters.format_point_differential
    app.jinja_env.filters['percent'] = filters.percent

    return app