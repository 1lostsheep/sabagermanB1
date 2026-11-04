"""Flask server: JSON API under /api, the web app at /, media at /media."""
from flask import Flask, jsonify, send_from_directory

from . import config, db

ROOT = config.ROOT
WEB = ROOT / "web"
MEDIA = ROOT / "content" / "media"


def create_app(db_path=None):
    app = Flask(__name__, static_folder=None)
    app.config["DB_PATH"] = db_path
    conn = db.connect(db_path)
    db.init(conn)
    conn.close()

    @app.get("/health")
    def health():
        return jsonify(ok=True)

    @app.get("/")
    def index():
        return send_from_directory(WEB, "index.html")

    @app.get("/web/<path:path>")
    def web(path):
        return send_from_directory(WEB, path)

    @app.get("/media/<path:path>")
    def media(path):
        return send_from_directory(MEDIA, path, max_age=86400)

    return app


def main():
    port = int(config.get("PORT", 8765))
    app = create_app()
    # 127.0.0.1 only: nothing on the network can reach Saba's data
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
