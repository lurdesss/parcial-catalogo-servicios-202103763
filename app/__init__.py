from flask import Flask, jsonify, send_from_directory

from .config import Config
from .errors import register_error_handlers
from .extensions import db


def create_app(test_config=None):
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY no está configurada (ver .env.example).")
    app.config["PERMANENT_SESSION_LIFETIME"] = app.config["SESSION_HOURS"] * 3600

    db.init_app(app)
    register_error_handlers(app)

    from . import cli
    from .api import register_api
    from .security import guard_request

    app.before_request(guard_request)
    register_api(app)
    cli.register(app)

    @app.get("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.get("/health")
    def health():
        db.session.execute(db.text("SELECT 1"))
        return jsonify(status="ok")

    return app
