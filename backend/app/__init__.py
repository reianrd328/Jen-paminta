import os
from flask import Flask, send_from_directory, redirect
from flask_cors import CORS

from app.config import Config
from app.db import init_db
from app.routes.auth import auth_bp
from app.routes.products import products_bp
from app.routes.inventory import inventory_bp
from app.routes.sales import sales_bp
from app.routes.dashboard import dashboard_bp
from app.routes.settings import settings_bp

def create_app():
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
    assets_dir = os.path.join(frontend_dir, "assets")

    app = Flask(
        __name__,
        static_folder=assets_dir,
        static_url_path="/assets"
    )
    app.config["SECRET_KEY"] = Config.SECRET_KEY

    CORS(app)

    # Initialize Database Schema & Seeds
    with app.app_context():
        try:
            init_db()
        except Exception as e:
            print(f"[DB INIT ERROR] {e}")

    # Register API Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(settings_bp)

    # Serve Frontend Pages
    @app.route("/")
    def home():
        return send_from_directory(frontend_dir, "index.html")

    @app.route("/admin")
    @app.route("/admin/")
    def admin_page():
        return send_from_directory(frontend_dir, "admin.html")

    @app.route("/login")
    @app.route("/login/")
    def login_page():
        return send_from_directory(frontend_dir, "login.html")

    @app.route("/pos")
    @app.route("/pos/")
    def pos_redirect():
        return redirect("/admin#sales")

    @app.route("/logo.jpg")
    def serve_logo():
        return send_from_directory(os.path.join(assets_dir, "images"), "logo.jpg")

    return app

