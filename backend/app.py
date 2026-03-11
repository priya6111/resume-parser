import os

from flask import Flask, send_from_directory
from flask_cors import CORS

from routes.parse import parse_bp


def create_app() -> Flask:
    backend_dir = os.path.dirname(__file__)
    project_root = os.path.dirname(backend_dir)
    frontend_dir = os.path.join(project_root, "frontend")
    assets_dir = os.path.join(project_root, "assets")

    app = Flask(__name__, static_folder=frontend_dir, static_url_path="")
    CORS(app)

    upload_dir = os.path.join(backend_dir, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    app.config["UPLOAD_FOLDER"] = upload_dir

    app.register_blueprint(parse_bp)

    @app.get("/")
    def landing_page():
        return app.send_static_file("index.html")

    @app.get("/assets/<path:filename>")
    def serve_assets(filename: str):
        return send_from_directory(assets_dir, filename)

    @app.get("/health")
    def health_check():
        return {"status": "ok"}, 200

    return app


if __name__ == "__main__":
    application = create_app()
    debug_mode = os.getenv("FLASK_DEBUG", "0") == "1"
    application.run(host="0.0.0.0", port=5000, debug=debug_mode, use_reloader=False)
