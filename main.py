import logging.config
import os

from flask import Flask
from config_loader import ConfigLoader
from modules.document_manager import DocumentManager
from modules.file_metadata_db import FileMetadataDB
from modules.embedding_handler import EmbeddingHandler
from modules.embedding_storage import EmbeddingStorage
from modules.answer_generator import AnswerGeneratorAndValidator
from modules.text_splitter import TextContextSplitter
from modules.speech_processor import SpeechProcessor
from modules.dialog_manager import DialogManager
from modules.dialog_history import DialogHistory
from website import register_routes

from pathlib import Path

def create_app():
    # === Загрузка конфигурации ===
    config = ConfigLoader("config.yaml").full

    setup_logging(config)
    logger = logging.getLogger(__name__)
    logger.info("Логирование инициализировано")

    # === Инициализация компонентов ===
    metadata_db = FileMetadataDB(config.metadata_storage)
    document_manager = DocumentManager(config, metadata_db)
    embedder = EmbeddingHandler(config)
    storage = EmbeddingStorage(config.embedding_storage)
    generator = AnswerGeneratorAndValidator(config)
    splitter = TextContextSplitter(config.splitter)
    speech = SpeechProcessor(config.speech, config.models)
    history = DialogHistory(config.dialog_history.db_path)

    # === Индексация файлов из папки ===
    logger.info("Начало индексации папки %s", config.documents_folder)
    folder_path = Path(config.documents_folder)
    added = 0

    if folder_path.exists() and folder_path.is_dir():
        for file_path in folder_path.iterdir():
            logger.debug("Проверка файла %s", file_path)
            if not file_path.is_file():
                continue
            if not document_manager.is_supported_format(file_path):
                continue

            text = document_manager.get_text(file_path)
            if not text or len(text.strip()) < 30:
                continue

            file_hash = document_manager.get_hash(file_path)
            if metadata_db.get_file_by_hash(file_hash):
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
                storage.add_embedding(chunk_id, emb, metadata={
                    "source": str(file_path),
                    "content": ctx[:300] + "..." if len(ctx) > 300 else ctx
                })
                logger.debug("Добавлено %d фрагментов для %s", len(contexts), file_path)
            added += 1

    logger.info("Добавлено новых файлов: %d", added)

    # === Создаём диалоговый менеджер ===
    dialog_manager = DialogManager(
        embedder=embedder,
        storage=storage,
        generator=generator,
        speech=speech,
        history=history,
        prompt_template=config.dialog_prompt
    )

    # === Flask-приложение ===
    app = Flask(__name__)
    register_routes(app, dialog_manager)
    return app

def setup_logging(cfg):
    log_file = cfg.logging.file
    # создаём директорию, если её нет
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    log = cfg.logging
    dict_conf = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": log.format,
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": log.level,
                "formatter": "default",
                "filename": log_file,
                "maxBytes": log.max_bytes,
                "backupCount": log.backup_count
            },
            "console": {
                "class": "logging.StreamHandler",
                "level": log.console_level,
                "formatter": "default"
            }
        },
        "root": {
            "level": log.level,
            "handlers": ["file", "console"]
        }
    }
    logging.config.dictConfig(dict_conf)


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
