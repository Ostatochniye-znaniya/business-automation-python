from flask import Flask, jsonify

from .config import config_by_name
from .extensions import db, migrate


def create_app(config_name: str = "development") -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    db.init_app(app)
    migrate.init_app(app, db)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "OK"})

    return app
