from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional, Callable, ContextManager

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from .models import File, Image

logger = logging.getLogger(__name__)


class FileMetadataDB:
    def __init__(self, session_factory: Callable[[], ContextManager]):
        """Создать обёртку над хранилищем.

        Параметры:
            session_factory: Функция без аргументов, возвращающая объект
                *Session*, который можно использовать как контекстный менеджер
                (через оператор ``with``).
        """
        self.session_factory = session_factory

    def add_file(
        self,
        path: str | Path,
        *,
        file_type: str,
        size: int,
        file_hash: str,
    ) -> Optional[int]:
        """Добавить новую запись о файле.

        Возвращает *id* вставленной или уже существующей записи. Если другой
        процесс уже добавил файл с тем же ``hash``, метод вернёт *id* найденной
        строки. Возвращает *None* только если существующая строка почему‑то не
        нашлась (в нормальной работе такого быть не должно).
        """
        path = str(path)
        with self.session_factory() as session:
            try:
                new_file = File(path=path, file_type=file_type, size=size, hash=file_hash)
                session.add(new_file)
                session.flush()  # получаем PK без явного commit
                return new_file.id
            except IntegrityError:
                session.rollback()
                existing = (
                    session.query(File.id)
                    .filter_by(hash=file_hash)
                    .first()
                )
                if existing:
                    logger.info("Файл с hash %s уже существует", file_hash)
                    return existing[0]
                logger.error("IntegrityError, но файл с hash=%s не найден", file_hash)
                return None

    def get_file_by_hash(self, file_hash: str) -> Optional[File]:
        """Вернуть объект *File* по его хэшу."""
        with self.session_factory() as session:
            return session.query(File).filter_by(hash=file_hash).first()

    def get_file_by_id(self, file_id: int) -> Optional[File]:
        """Вернуть объект *File* по его первичному ключу."""
        with self.session_factory() as session:
            return session.get(File, file_id)

    def mark_file_as_processed(self, file_id: int) -> bool:
        """Отметить файл как обработанный (``processed=True``)."""
        with self.session_factory() as session:
            file = session.get(File, file_id)
            if not file:
                logger.warning("Файл %s не найден", file_id)
                return False
            if not file.processed:
                file.processed = True
            else:
                logger.debug("Файл %s уже помечен как обработанный", file_id)
            return True

    def delete_file(self, file_id: int) -> bool:
        """Удалить запись о файле (каскадно удалит связанную *Image*, если есть)."""
        with self.session_factory() as session:
            file = session.get(File, file_id)
            if not file:
                return False
            session.delete(file)
            return True

    def upsert_metadata(self, path: str | Path, metadata: dict) -> int:
        """Вставить или обновить запись *File* по пути.

        Параметры:
            path: Путь к файлу на диске.
            metadata: Словарь с опциональными ключами ``mime_type``, ``size``
                (int) и ``hash``.

        Возвращает:
            Первичный ключ обновлённой или вставленной строки.
        """
        path = str(path)
        with self.session_factory() as session:
            file = session.query(File).filter_by(path=path).first()
            if file is None:
                file = File(
                    path=path,
                    file_type=metadata.get("mime_type", "unknown"),
                    size=metadata.get("size", 0),
                    hash=metadata.get("hash", ""),
                )
                session.add(file)
                session.flush()
            else:
                if (mime := metadata.get("mime_type")):
                    file.file_type = mime
                if (size := metadata.get("size")) is not None:
                    file.size = size
                if (h := metadata.get("hash")):
                    file.hash = h
            return file.id

    def add_image_metadata(
        self,
        file_id: int,
        *,
        width: int,
        height: int,
        thumbnail: bytes,
        caption: str,
    ) -> bool:
        """Добавить метаданные изображения к существующей записи *File*."""
        with self.session_factory() as session:
            if session.get(Image, file_id):
                return False
            image = Image(
                file_id=file_id,
                width=width,
                height=height,
                thumbnail=thumbnail,
                caption=caption,
            )
            session.add(image)
            return True

    def get_image_metadata(self, file_id: int) -> Optional[Image]:
        """Вернуть объект *Image* по *file_id*."""
        with self.session_factory() as session:
            return session.get(Image, file_id)

    def get_all_files(self) -> List[File]:
        """Вернуть список всех объектов *File*."""
        with self.session_factory() as session:
            return session.query(File).all()

    def get_files_by_extension(self, extension: str | None = None) -> List[str]:
        """Вернуть пути файлов с указанным расширением (регистр не учитывается).

        Если *extension* не задано, будут возвращены пути всех файлов.
        """
        with self.session_factory() as session:
            query = session.query(File.path)
            if extension:
                ext = extension.lower().lstrip(".")
                pattern = f'%.{ext}'
                return [row[0] for row in query.filter(File.path.ilike(pattern))]
            return [row[0] for row in query]
