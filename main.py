import logging.config
import os

from flask import Flask
from config_loader import ConfigLoader
from modules.db import DBManager
from modules.document_manager import DocumentManager
from modules.file_metadata_db import FileMetadataDB
from modules.embedding_handler import EmbeddingHandler
from modules.embedding_storage import EmbeddingStorage
from modules.answer_generator import AnswerGeneratorAndValidator
from modules.text_splitter import TextContextSplitter
from modules.speech_processor import SpeechProcessor
from modules.dialog_history import DialogHistory
from website import register_routes
from dataclasses import is_dataclass, asdict

from invoke_system import (
    call_ping,
    call_index,
    call_message,
    call_get_history,
    call_delete_history,
    call_text_to_speech
)
from pathlib import Path


def create_app():
    # === Загрузка конфигурации ===
    config = ConfigLoader("config.yaml").full
    setup_logging(config)

    logger = logging.getLogger(__name__)
    logger.info("Логирование инициализировано")

    # === БД ===
    db = DBManager(config.database)
    db.init_db()
    
    # === Компоненты ===
    metadata_db      = FileMetadataDB(db.session_scope)
    history          = DialogHistory(db.session_scope)
    document_manager = DocumentManager(config.document_manager, metadata_db)
    embedder         = EmbeddingHandler(config.embedding_handler)
    storage          = EmbeddingStorage(config.embedding_storage)
    generator        = AnswerGeneratorAndValidator(config.answer_generator)
    splitter         = TextContextSplitter(config.splitter)
    speech           = SpeechProcessor(config.speech, config.speech_models)

    # === Индексация документов ===
    folder_path = Path(config.documents_folder)
    logger.info("Индексация документов в: %s", folder_path)
    if folder_path.exists() and folder_path.is_dir():
        for file_path in folder_path.iterdir():
            if not file_path.is_file():
                continue
            if not document_manager.is_supported_format(file_path):
                continue
            text = document_manager.get_text(file_path)
            if not text or len(text.strip()) < 30:
                continue
            file_hash = document_manager.get_hash(file_path)
            if not file_hash or metadata_db.get_file_by_hash(file_hash):
                continue
            metadata = document_manager.get_metadata(file_path)
            metadata_db.add_file(
                path=str(file_path),
                file_type=metadata["mime_type"],
                size=metadata["size"],
                file_hash=file_hash
            )
            contexts = splitter.split_by_paragraphs(text)
            for i, ctx in enumerate(contexts):
                chunk_id = f"{file_hash}_chunk{i}"
                emb = embedder.get_text_embedding(ctx)
                storage.add_embedding(
                    chunk_id,
                    emb,
                    metadata={
                        "source": file_path.name,
                        "content": (ctx[:300] + ".") if len(ctx) > 300 else ctx
                    }
                )

    # === Инициализация Flask-приложения ===
    from modules.dialog_manager import DialogManager
    dialog_manager = DialogManager(embedder, storage, generator, speech, history, config.dialog_manager)

    app = Flask(__name__)
    register_routes(app, dialog_manager)
    return app


def setup_logging(cfg):
    # Приводим cfg к обычному dict, если это dataclass
    if is_dataclass(cfg):
        cfg_dict = asdict(cfg)
    elif isinstance(cfg, dict):
        cfg_dict = cfg
    else:
        raise TypeError(f"Неподдерживаемый тип конфига: {type(cfg)}")

    # Забираем секцию logging
    log_section = cfg_dict.get("logging", {})
    if is_dataclass(log_section):
        log_conf = asdict(log_section)
    else:
        log_conf = log_section

    # Параметры из конфига
    log_file      = log_conf["file"]
    level         = log_conf["level"]
    fmt           = log_conf["format"]
    max_bytes     = log_conf["max_bytes"]
    backup_count  = log_conf["backup_count"]
    console_level = log_conf["console_level"]

    # Убеждаемся, что папка для логов существует
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    # Формируем конфиг для logging
    dict_conf = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": fmt,
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": level,
                "formatter": "default",
                "filename": log_file,
                "maxBytes": max_bytes,
                "backupCount": backup_count
            },
            "console": {
                "class": "logging.StreamHandler",
                "level": console_level,
                "formatter": "default"
            }
        },
        "root": {
            "level": level,
            "handlers": ["file", "console"]
        }
    }

    # Применяем настройки
    logging.config.dictConfig(dict_conf)


if __name__ == "__main__":
    # Инициализация приложения и клиента
    app = create_app()
    client = app.test_client()

    # Вызовы интеграционных методов после полной загрузки
    call_ping(client)
    call_index(client, 'test_user')
    call_message(client, 'test_user', 'Что такое мороженое?', info='source')
    call_message(client, 'test_user', 'Что такое мороженое?', info='fragments')
    call_message(client, 'test_user', 'Что такое мороженое?', info='all')
    call_get_history(client, 'test_user')
    call_delete_history(client, 'test_user')

    # Запуск HTTP-сервера
    app.run(debug=True)

