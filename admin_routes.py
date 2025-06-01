from __future__ import annotations
import threading
import time
import datetime as dt
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit

from services import (
    minimal_init_classes,
    full_init_classes,
    get_config,
    save_config,
    optimize_config,
    list_files,
    delete_file,
    rebuild_embeddings,
    get_logs,
    start_app,
    stop_app,
    app_status,
    shutdown_app,
    rebuild_all_embeddings,
    upload_files
)
from website import register_routes as core_routes

socketio = SocketIO(cors_allowed_origins="*")

def register_admin_routes(app: Flask, *, config_path: str | Path = "config.yaml"):
    cfg_file = Path(config_path).resolve()
    socketio.init_app(app)

    class LazyDialogManager:
        def __init__(self, cfg_path: Path):
            self._cfg = cfg_path

        def _dm(self):
            return full_init_classes(self._cfg, socketio)["dialog_manager"]

        def __getattr__(self, name):
            return getattr(self._dm(), name)

    core_routes(app, LazyDialogManager(cfg_file))
    tpl_dir = Path(__file__).with_suffix("").parent / "templates"

    @app.get("/config")
    def config_page():
        try:
            return send_from_directory(tpl_dir, "config_interface.html")
        except FileNotFoundError:
            return jsonify({"status": "error", "message": "Страница не найдена"}), 500

    @app.get("/api/config")
    def get_config_route():
        response, status = get_config(cfg_file)
        return jsonify(response), status

    @app.post("/api/config")
    def save_config_route():
        data = request.get_json(silent=True) or {}
        response, status = save_config(cfg_file, data, socketio)
        return jsonify(response), status

    @app.get("/api/config/optimize")
    def optimize_config_route():
        response, status = optimize_config(cfg_file, socketio)
        return jsonify(response), status

    @app.get("/api/files")
    def list_files_route():
        services = minimal_init_classes(cfg_file, socketio)
        response, status = list_files(services)
        return jsonify(response), status

    @app.delete("/api/files/<path:filename>")
    def delete_file_route(filename):
        services = minimal_init_classes(cfg_file, socketio)
        response, status = delete_file(filename, services, socketio)
        return jsonify(response), status

    @app.post("/api/files/<path:filename>/rebuild")
    def rebuild_embeddings_route(filename):
        services = minimal_init_classes(cfg_file, socketio)
        response, status = rebuild_embeddings(filename, services, socketio)
        return jsonify(response), status
    
    @app.post("/api/files/rebuild-all")
    def rebuild_all_embeddings_route():
        services = minimal_init_classes(cfg_file, socketio)
        response, status = rebuild_all_embeddings(services, socketio)
        return jsonify(response), status
    
    @app.post("/api/files/upload")
    def upload_files_route():
        services = minimal_init_classes(cfg_file, socketio)
        response, status = upload_files(request.files.getlist("files"), services, socketio)
        return jsonify(response), status

    @app.get("/api/logs")
    def get_logs_route():
        try:
            limit = int(request.args.get("limit", 100))
        except ValueError:
            return jsonify({"status": "error", "message": "Недопустимый лимит"}), 400
        response, status = get_logs(cfg_file, limit)
        return jsonify(response), status

    @app.post("/api/app/start")
    def start_app_route():
        response, status = start_app(cfg_file, socketio)
        return jsonify(response), status

    @app.post("/api/app/stop")
    def stop_app_route():
        try:
            response, status = stop_app(socketio)
            return jsonify(response), status
        except Exception as e:
            return jsonify({"status": "error", "message": f"Ошибка сервера: {str(e)}"}), 500

    @app.get("/api/app/status")
    def app_status_route():
        response, status = app_status()
        return jsonify(response), status

    @app.post("/api/app/shutdown")
    def shutdown_app_route():
        response = {"status": "success", "message": "Выключено"}
        def do_shutdown_later(env):
            time.sleep(0.1)
            shutdown_app(env, socketio)
        threading.Thread(target=do_shutdown_later, args=(request.environ,)).start()
        return jsonify(response), 200

    @socketio.on('connect', namespace='/ws/logs')
    def handle_connect():
        emit('log_message', {'timestamp': dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                            'level': 'INFO', 
                            'message': 'WebSocket подключен'})