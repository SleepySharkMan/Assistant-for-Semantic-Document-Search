from __future__ import annotations
import logging.config
import os
import sys
import threading
import signal
import datetime as dt
import re
import torch
from pathlib import Path
from typing import Dict, Any, Tuple, List
from dataclasses import is_dataclass, asdict
from threading import Lock
from ruamel.yaml import YAML
from enum import Enum
from flask import request
from flask_socketio import SocketIO

from config_loader import ConfigLoader
from config_editor import ConfigEditor
from modules.db import DBManager
from modules.file_metadata_db import FileMetadataDB, File
from modules.document_manager import DocumentManager
from modules.embedding_handler import EmbeddingHandler
from modules.embedding_storage import EmbeddingStorage
from modules.answer_generator import AnswerGenerator
from modules.text_splitter import TextContextSplitter
from modules.speech_processor import SpeechProcessor
from modules.dialog_history import DialogHistory
from modules.dialog_manager import DialogManager

logger = logging.getLogger(__name__)
_services: Dict[str, Any] | None = None
_running = False
_services_lock = Lock()
_yaml = YAML()
_yaml.preserve_quotes = True
socketio: SocketIO | None = None



class WebSocketHandler(logging.Handler):
    def emit(self, record):
        if socketio is None:
            return
        log_entry = self.format(record)
        try:
            socketio.emit('log_message', {
                           'timestamp': record.asctime, 'level': record.levelname, 'message': log_entry})
        except Exception as e:
            logger.info(f"Ошибка отправки лога через WebSocket: {e}")


def _convert_config_to_dict(obj: Any) -> Any:
    if isinstance(obj, Enum):
        return obj.value
    elif is_dataclass(obj):
        return {k: _convert_config_to_dict(v) for k, v in asdict(obj).items()}
    elif isinstance(obj, dict):
        return {k: _convert_config_to_dict(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_config_to_dict(item) for item in obj]
    return obj


def _setup_logging(cfg: Any, socketio: SocketIO = None) -> None:
    log_cfg = cfg.logging
    os.makedirs(os.path.dirname(log_cfg.file) or ".", exist_ok=True)
    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {"format": "%(asctime)s %(levelname)-8s [%(name)s] %(message)s", "datefmt": "%Y-%m-%d %H:%M:%S"}
        },
        "handlers": {
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": log_cfg.level,
                "filename": log_cfg.file,
                "formatter": "default",
                "maxBytes": log_cfg.max_bytes,
                "backupCount": log_cfg.backup_count,
                "encoding": "utf-8",
            },
            "console": {
                "class": "logging.StreamHandler",
                "level": log_cfg.console_level,
                "formatter": "default",
            },
            "websocket": {
                "class": __name__ + ".WebSocketHandler",
                "level": log_cfg.level,
                "formatter": "default",
            }
        },
        "root": {"level": log_cfg.level, "handlers": ["file", "console", "websocket"]},
    })


def minimal_init_classes(config_path: str | Path = "config.yaml", socketio: SocketIO = None) -> Dict[str, Any]:
    global _services
    with _services_lock:
        if _services is None:
            cfg_loader = ConfigLoader(config_path)
            cfg = cfg_loader.full
            _setup_logging(cfg, socketio)
            db = DBManager(cfg.database)
            db.init_db()
            metadata_db = FileMetadataDB(db.session_scope)
            document_manager = DocumentManager(
                cfg.document_manager, metadata_db)
            splitter = TextContextSplitter(cfg.splitter)
            embedder = EmbeddingHandler(cfg.embedding_handler)
            storage = EmbeddingStorage(cfg.embedding_storage)
            _services = {
                "config": cfg,
                "metadata_db": metadata_db,
                "document_manager": document_manager,
                "splitter": splitter,
                "embedder": embedder,
                "embedding_storage": storage,
            }

        cfg = _services["config"]
        document_manager = _services["document_manager"]
        try:
            docs_path = Path(cfg.documents_folder).resolve()
            if docs_path.is_dir():
                for file_path in docs_path.rglob("*"):
                    if not file_path.is_file():
                        continue
                    if not document_manager.is_supported_format(file_path):
                        continue
                    document_manager.save_metadata(file_path)
        except Exception as e:
            logger.exception(
                "Ошибка при автозагрузке файлов из папки %s: %s",
                cfg.documents_folder, e
            )

    return _services


def full_init_classes(config_path: str | Path = "config.yaml", socketio: SocketIO = None) -> Dict[str, Any]:
    global _services
    if _services is None:
        _services = minimal_init_classes(config_path, socketio)
    cfg = _services["config"]
    if "dialog_manager" not in _services:
        logger.info("Инициализация приложения началась")
        history = DialogHistory(_services["metadata_db"].session_factory)
        generator = AnswerGenerator(cfg.answer_generator)
        speech = SpeechProcessor(cfg.speech)
        dialog_manager = DialogManager(
            _services["embedder"],
            _services["embedding_storage"],
            generator,
            speech,
            history,
            cfg.dialog_manager,
        )
        _services.update({
            "generator": generator,
            "speech": speech,
            "dialog_manager": dialog_manager,
        })
        logger.info("Приложение инициализировано")
    return _services


def safe_filename(filename: str) -> str:
    invalid_chars = r'[<>:"/\\|?*]'
    filename = re.sub(invalid_chars, '_', filename)
    filename = filename.strip()
    if not filename or filename == '.':
        from uuid import uuid4
        filename = f"file_{uuid4().hex[:8]}.txt"
    return filename


def process_single_file(file_path: Path, services: Dict[str, Any], socketio: SocketIO = None) -> None:
    socketio.emit(
        'log_message',
        {
            'timestamp': dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'level': 'INFO',
            'message': 'Обработка файла'
        },
        namespace='/ws/logs'
    )
    document_manager = services["document_manager"]
    splitter = services.get("splitter")
    embedder = services.get("embedder")
    storage = services.get("embedding_storage")
    metadata_db = services["metadata_db"]

    if not file_path.is_file() or not document_manager.is_supported_format(file_path):
        logger.warning(
            "Файл %s не является файлом или не поддерживается", file_path)
        return
    try:
        text = document_manager.get_text(file_path)
        if not text or len(text.strip()) < 30:
            logger.warning(
                "Пустой или слишком короткий текст для файла: %s", file_path)
            return
        file_hash = document_manager.get_hash(file_path)
        if not file_hash or metadata_db.get_file_by_hash(file_hash):
            logger.info("Файл %s уже обработан или хэш отсутствует", file_path)
            return
        meta = document_manager.get_metadata(file_path)
        metadata_db.add_file(
            path=str(file_path),
            file_type=meta["mime_type"],
            size=meta["size"],
            file_hash=file_hash,
        )
        for i, chunk in enumerate(splitter.split(text)):
            emb = embedder.get_text_embedding(chunk)
            storage.add_embedding(
                f"{file_hash}_chunk{i}",
                emb,
                metadata={"source": file_path.name, "content": chunk[:300]},
            )
        logger.info("Файл %s успешно обработан", file_path)
    except Exception as e:
        logger.exception("Ошибка обработки файла %s: %s", file_path, e)


def process_folder(folder: Path, services: Dict[str, Any], socketio: SocketIO = None) -> None:
    if not folder.exists():
        logger.warning("Папка %s не существует", folder)
        return
    for file_path in folder.iterdir():
        process_single_file(file_path, services, socketio)


def build_services(config_path: str | Path = "config.yaml", socketio: SocketIO = None) -> Dict[str, Any]:
    services = full_init_classes(config_path, socketio)
    process_folder(Path(services["config"].documents_folder), services)
    return services


def get_config(config_path: Path, socketio: SocketIO = None) -> Tuple[Dict[str, Any], int]:
    try:
        services = minimal_init_classes(config_path, socketio)
        return {"status": "success", "config": _convert_config_to_dict(services["config"])}, 200
    except Exception as e:
        logger.exception("Ошибка получения конфигурации")
        return {"status": "error", "message": str(e)}, 500


def save_config(config_path: Path, data: Dict[str, Any], socketio: SocketIO = None) -> Tuple[Dict[str, Any], int]:
    if not data:
        return {"status": "error", "message": "Пустая конфигурация"}, 400
    socketio.emit(
        'log_message',
        {
            'timestamp': dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'level': 'INFO',
            'message': 'Сохранение конфига'
        },
        namespace='/ws/logs'
    )
    valid_devices = ["cuda:0", "cuda:1", "cpu"]
    valid_quantizations = ["fp32", "fp16", "int8", "nf4"]
    valid_splitter_methods = ["words", "sentences", "paragraphs"]
    valid_log_levels = ["INFO", "DEBUG", "WARNING", "ERROR", "CRITICAL"]
    try:
        editor = ConfigEditor(config_path)
        flat: Dict[str, Any] = {}

        def _flat(prefix: str, obj: Any):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    _flat(f"{prefix}.{k}" if prefix else k, v)
            else:
                flat[prefix] = obj
        _flat("", data)
        if "embedding_handler.device" in flat and flat["embedding_handler.device"] not in valid_devices:
            return {"status": "error", "message": f"Недопустимое устройство: {flat['embedding_handler.device']}"}, 400
        if "answer_generator.device" in flat and flat["answer_generator.device"] not in valid_devices:
            return {"status": "error", "message": f"Недопустимое устройство: {flat['answer_generator.device']}"}, 400
        if "answer_generator.quantization" in flat and flat["answer_generator.quantization"] not in valid_quantizations:
            return {"status": "error", "message": f"Недопустимая квантизация: {flat['answer_generator.quantization']}"}, 400
        if "splitter.method" in flat and flat["splitter.method"] not in valid_splitter_methods:
            return {"status": "error", "message": f"Недопустимый метод разделения: {flat['splitter.method']}"}, 400
        if "logging.level" in flat and flat["logging.level"] not in valid_log_levels:
            return {"status": "error", "message": f"Недопустимый уровень логирования: {flat['logging.level']}"}, 400
        if "logging.console_level" in flat and flat["logging.console_level"] not in valid_log_levels:
            return {"status": "error", "message": f"Недопустимый уровень консольного логирования: {flat['logging.console_level']}"}, 400
        for path, val in flat.items():
            editor.update(path, val)
        global _services
        with _services_lock:
            if _services is not None:
                cfg_loader = ConfigLoader(config_path)
                _services["config"] = cfg_loader.full
        return {"status": "success", "message": "Конфигурация сохранена"}, 200
    except Exception as e:
        logger.exception("Ошибка сохранения конфигурации")
        return {"status": "error", "message": str(e)}, 500


def optimize_config(config_path: Path, socketio: SocketIO = None) -> Tuple[Dict[str, Any], int]:
    try:
        socketio.emit(
            'log_message',
            {
                'timestamp': dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'level': 'INFO',
                'message': 'Оптимизация параметров'
            },
            namespace='/ws/logs'
        )
        editor = ConfigEditor(config_path)
        params = editor.apply_suggested_generation_params()
        global _services
        with _services_lock:
            if _services is not None:
                cfg_loader = ConfigLoader(config_path)
                _services["config"] = cfg_loader.full
        return {"status": "success", "config": _convert_config_to_dict(params)}, 200
    except Exception as e:
        logger.exception("Ошибка оптимизации конфигурации")
        return {"status": "error", "message": str(e)}, 500


def list_files(services: Dict[str, Any], socketio: SocketIO = None) -> Tuple[Dict[str, Any], int]:
    try:
        with services["metadata_db"].session_factory() as session:
            files = services["metadata_db"].get_all_files()
            logger.info("Получено %d записей из get_all_files: %s", len(files), files) 
            rows = []
            seen_paths = set() 
            for f in files:
                if not f.get("path") or not f.get("size") or not f.get("created_at"):
                    logger.warning("Некорректная запись в базе данных: %s", f)
                    continue
                if f["path"] in seen_paths:
                    logger.warning("Обнаружен дубликат в данных: %s", f["path"])
                    continue
                seen_paths.add(f["path"])
                try:
                    row = {
                        "name": Path(f["path"]).name,
                        "size": f"{f['size']/1_048_576:.1f} MB",
                        "modified": dt.datetime.fromtimestamp(f["created_at"].timestamp()).strftime("%Y-%m-%d"),
                        "splitter_method": f["splitter_method"] or "unknown",
                    }
                    rows.append(row)
                    logger.debug("Добавлен файл в ответ: %s", row)
                except Exception as e:
                    logger.warning("Ошибка обработки файла %s: %s", f.get("path", "unknown"), e)
                    continue
            logger.info("Возвращено %d файлов в ответе: %s", len(rows), rows)
            return {"status": "success", "files": rows}, 200
    except Exception as e:
        logger.exception("Ошибка получения списка файлов: %s", e)
        return {"status": "error", "message": str(e)}, 500


def delete_file(filename: str, services: Dict[str, Any], socketio: SocketIO = None) -> Tuple[Dict[str, Any], int]:
    try:
        with services["metadata_db"].session_factory() as session:
            socketio.emit(
                'log_message',
                {
                    'timestamp': dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'level': 'INFO',
                    'message': 'Удаление файла'
                },
                namespace='/ws/logs'
            )
            files = services["metadata_db"].get_all_files()
            rec = next((f for f in files if Path(
                f["path"]).name == filename), None)
            if not rec:
                return {"status": "error", "message": "Файл не найден"}, 404
            documents_folder = Path(
                services["config"].documents_folder).resolve()
            file_path = Path(rec["path"]).resolve()
            if not str(file_path).startswith(str(documents_folder)):
                logger.warning(
                    "Попытка удалить файл вне папки документов: %s", file_path)
                return {"status": "error", "message": "Недопустимый путь"}, 403
            ids = services["embedding_storage"].collection.get(
                where={"source": {"$eq": filename}})["ids"]
            if ids:
                services["embedding_storage"].collection.delete(ids=ids)
            else:
                logger.info("Эмбеддинги для файла %s не найдены", filename)
            file_path.unlink(missing_ok=True)
            session.query(File).filter(File.path == str(file_path)).delete()
        return {"status": "success", "message": "Файл удалён"}, 200
    except Exception as e:
        logger.exception("Ошибка удаления файла")
        return {"status": "error", "message": str(e)}, 500


def rebuild_embeddings(filename: str, services: Dict[str, Any], socketio: SocketIO = None) -> Tuple[Dict[str, Any], int]:
    try:
        with services["metadata_db"].session_factory() as session:
            socketio.emit(
                'log_message',
                {
                    'timestamp': dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'level': 'INFO',
                    'message': 'Пересоздание эмбенддингов'
                },
                namespace='/ws/logs'
            )
            files = services["metadata_db"].get_all_files()
            rec = next((f for f in files if Path(
                f["path"]).name == filename), None)
            if not rec:
                return {"status": "error", "message": "Файл не найден"}, 404
            text = services["document_manager"].get_text(Path(rec["path"]))
            if not text or len(text.strip()) < 30:
                logger.warning(
                    "Пустой или слишком короткий текст для файла: %s", filename)
                return {"status": "error", "message": "Пустой или слишком короткий текст"}, 400
            old_ids = services["embedding_storage"].collection.get(
                where={"source": {"$eq": filename}})["ids"]
            if old_ids:
                services["embedding_storage"].collection.delete(ids=old_ids)
            else:
                logger.info(
                    "Предыдущие эмбеддинги для файла %s не найдены", filename)
            for i, chunk in enumerate(services["splitter"].split(text)):
                emb = services["embedder"].get_text_embedding(chunk)
                services["embedding_storage"].add_embedding(
                    f"{filename}_chunk{i}",
                    emb,
                    metadata={"source": filename, "content": chunk[:300]},
                )
            session.query(File).filter(File.path == str(rec["path"])).update(
                {"splitter_method": services["splitter"].config.method}
            )
            session.commit()
        return {"status": "success", "message": "Эмбеддинги пересозданы"}, 200
    except Exception as e:
        logger.exception("Ошибка пересоздания эмбеддингов")
        return {"status": "error", "message": str(e)}, 500


def get_logs(config_path: Path, limit: int = 100) -> Tuple[Dict[str, Any], int]:
    try:
        raw_cfg = _yaml.load(config_path.open("r", encoding="utf-8"))
        log_file = Path(raw_cfg["logging"]["file"])
        if not log_file.exists():
            return {"status": "error", "message": "Файл логов не найден"}, 500
        with log_file.open("r", encoding="utf-8", errors="ignore") as f:
            tail = f.readlines()[-limit:]
        parsed = []
        for line in tail:
            try:
                ts, lvl, msg = line.strip().split(" ", 2)
                parsed.append({"timestamp": ts, "level": lvl, "message": msg})
            except ValueError:
                continue
        return {"status": "success", "logs": parsed}, 200
    except Exception as e:
        logger.exception("Ошибка получения логов")
        return {"status": "error", "message": str(e)}, 500


def start_app(config_path: Path, socketio: SocketIO = None) -> Tuple[Dict[str, Any], int]:
    global _services, _running
    with _services_lock:
        socketio.emit(
            'log_message',
            {
                'timestamp': dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'level': 'INFO',
                'message': 'Начался запуск приложения'
            },
            namespace='/ws/logs'
        )
        if _running:
            return {"status": "success", "message": "Уже запущено"}, 200
        _services = full_init_classes(config_path, socketio)
        _running = True
        socketio.emit(
            'log_message',
            {
                'timestamp': dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'level': 'INFO',
                'message': 'Приложение загружено'
            },
            namespace='/ws/logs'
        )
    return {"status": "success", "message": "Запущено"}, 200


def stop_app(socketio: SocketIO = None):
    global _services, _running

    try:
        _running = False
        _services.update({
        "generator": None,
        "speech": None,
        "dialog_manager": None,
    })
    except Exception as e:
        return {"status": "error", "message": f"Ошибка при остановке: {e}"}, 500

    return {"status": "success", "message": "Остановлено"}, 200


def app_status() -> Tuple[Dict[str, Any], int]:
    return {"status": "success", "running": _running}, 200


def shutdown_app(request_environ: Dict[str, Any], socketio: SocketIO = None) -> Tuple[Dict[str, Any], int]:
    try:
        socketio.emit(
            'log_message',
            {
                'timestamp': dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'level': 'INFO',
                'message': 'Выключение'
            },
            namespace='/ws/logs'
        )
        fn = request_environ.get("werkzeug.server.shutdown")
        if fn is not None:
            fn()
            return {"status": "success", "message": "Выключено"}, 200
        if hasattr(threading, "main_thread"):
            os.kill(os.getpid(), signal.SIGINT)
            return {"status": "success", "message": "Процесс остановлен (SIGINT)"}, 200
        sys.exit(0)
    except Exception as e:
        logger.exception("Ошибка выключения приложения")
        return {"status": "error", "message": str(e)}, 500


def upload_files(files: List[Any], services: Dict[str, Any], socketio: SocketIO = None) -> Tuple[Dict[str, Any], int]:
    try:
        socketio.emit(
            'log_message',
            {
                'timestamp': dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'level': 'INFO',
                'message': 'Начата загрузка файл(-ов)'
            },
            namespace='/ws/logs'
        )
        documents_folder = Path(services["config"].documents_folder).resolve()
        documents_folder.mkdir(parents=True, exist_ok=True)
        success_count = 0
        errors = []
        processed_files = []
        overwrite = request.form.get("overwrite", "false").lower() == "true"
        for file in files:
            original_filename = file.filename
            if not original_filename:
                errors.append({"filename": original_filename,
                              "error": "Недопустимое имя файла"})
                continue
            filename = safe_filename(original_filename)
            file_path = documents_folder / filename
            if file_path.exists() and not overwrite:
                errors.append({"filename": original_filename,
                              "error": "Файл уже существует"})
                continue
            file.save(str(file_path))
            try:
                process_single_file(file_path, services, socketio)
                processed_files.append(filename)
                success_count += 1
            except Exception as e:
                errors.append({"filename": original_filename, "error": str(e)})
                file_path.unlink(missing_ok=True)
                logger.exception("Ошибка обработки файла %s: %s", filename, e)
        message = f"Добавлено и обработано {success_count} из {len(files)} файлов"
        if errors:
            message += f". Ошибки: {len(errors)}"
            return {"status": "partial_success", "message": message, "files": processed_files, "errors": errors}, 200
        socketio.emit(
            'log_message',
            {
                'timestamp': dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'level': 'INFO',
                'message': 'Файл(-ы) загружен(-ы)'
            },
            namespace='/ws/logs'
        )
        return {"status": "success", "message": message, "files": processed_files}, 200
    except Exception as e:
        logger.exception("Ошибка загрузки файлов")
        return {"status": "error", "message": str(e)}, 500


def rebuild_all_embeddings(services: Dict[str, Any], socketio: SocketIO = None) -> Tuple[Dict[str, Any], int]:
    try:
        with services["metadata_db"].session_factory() as session:
            socketio.emit(
                'log_message',
                {
                    'timestamp': dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'level': 'INFO',
                    'message': 'Пересоздание всех эмбенддигов'
                },
                namespace='/ws/logs'
            )
            files = services["metadata_db"].get_all_files()
            if not files:
                return {"status": "success", "message": "Нет файлов для пересчета эмбеддингов"}, 200
            success_count = 0
            for file in files:
                filename = Path(file["path"]).name
                response, status = rebuild_embeddings(filename, services, socketio)
                if status == 200:
                    success_count += 1
                else:
                    logger.warning("Не удалось пересчитать эмбеддинги для %s: %s", filename, response.get(
                        "message", "Неизвестная ошибка"))
            return {
                "status": "success",
                "message": f"Эмбеддинги пересозданы для {success_count} из {len(files)} файлов"
            }, 200
    except Exception as e:
        logger.exception("Ошибка пересоздания эмбеддингов для всех файлов")
        return {"status": "error", "message": str(e)}, 500

def rebuild_services(config_path: str | Path = "config.yaml", socketio: SocketIO | None = None) -> Dict[str, Any]:
    """Пересоздает только существующие сервисы из _services, используя minimal_init_classes и full_init_classes."""
    global _services, _running
    if _services is None:
        logger.warning("Нет сервисов для пересоздания")
        return {}

    # Сохраняем копию существующих сервисов
    existing_services = dict(_services)

    _services = None

    try:
        _services = minimal_init_classes(config_path, socketio)
        full_keys = {"generator", "speech", "dialog_manager"}
        if any(k in existing_services for k in full_keys):
            _services = full_init_classes(config_path, socketio)
            _running = True


    except Exception as e:
        logger.exception("Ошибка пересоздания сервисов: %s", e)
        _services = {}
        return {}

    return _services