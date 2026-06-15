"""
Astravox AI Backend Server
02-Backend/server/app.py
Stable Flask application factory and core server bootstrap.
"""

import os
import sys
from datetime import timedelta
from dotenv import load_dotenv, find_dotenv
from flask import Flask
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.dirname(BASE_DIR)
PROJECT_ROOT = os.path.dirname(BACKEND_ROOT)
FRONTEND_ROOT = os.path.join(PROJECT_ROOT, "01-Frontend")

sys.path.insert(0, BACKEND_ROOT)

from database.database import init_db
from routes.auth_routes import auth_bp
from routes.chat_routes import chat_bp
from routes.api_routes import api_bp
from routes.page_routes import page_bp
from utils.logger import setup_logger, app_logger
from utils.middleware import setup_request_logging


def create_app():
    load_dotenv(find_dotenv())

    app = Flask(
        __name__,
        static_folder=FRONTEND_ROOT,
        static_url_path="",
    )

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY") or os.urandom(24).hex()
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = False
    app.permanent_session_lifetime = timedelta(days=7)
    app.config["JSON_SORT_KEYS"] = False

    # Setup logging middleware
    setup_request_logging(app)
    app_logger.info("[READY] Astravox AI Backend Ready")
    CORS(app, origins="*", supports_credentials=True)
    app_logger.debug("CORS enabled")

    Limiter(
        get_remote_address,
        app=app,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="memory://"
    )
    app_logger.debug("Rate limiting configured")

    os.makedirs(os.path.join(BACKEND_ROOT, "uploads"), exist_ok=True)

    app.register_blueprint(page_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(chat_bp, url_prefix="/chat")
    app.register_blueprint(api_bp, url_prefix="/api")
    app_logger.debug("All routes registered")

    with app.app_context():
        init_db()
    app_logger.info("✅ Database initialized")

    @app.errorhandler(Exception)
    def _handle_exception(e):
        import traceback
        tb = traceback.format_exc()
        app_logger.error(f"Unhandled exception: {e}\n{tb}")
        return ({
            "status": "ERROR",
            "error": "Internal server error",
            "detail": str(e)
        }, 500)

    app_logger.info("✅ Astravox AI Backend Ready")
    return app


if __name__ == '__main__':
    app_logger.info("🚀 Astravox AI backend starting on http://127.0.0.1:5000")
    create_app().run(host='127.0.0.1', port=5000, debug=True)