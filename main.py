from flask import Flask
from flask_cors import CORS
from admin_routes import register_admin_routes

def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)
    register_admin_routes(app, config_path="config.yaml")
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8000, debug=True, threaded=True)