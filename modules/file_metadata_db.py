import logging
from .models import File, Image

logger = logging.getLogger(__name__)

class FileMetadataDB:
    def __init__(self, session_factory):
        """
        session_factory — функция, возвращающая контекстный менеджер SQLAlchemy-сессии.
        Обычно это DBManager.session_scope
        """
        self.session_factory = session_factory

    def add_file(self, path: str, file_type: str, size: int, file_hash: str) -> int | None:
        with self.session_factory() as session:
            if session.query(File).filter_by(hash=file_hash).first():
                logger.info("Файл уже существует: %s", path)
                return None
            new_file = File(path=path, file_type=file_type, size=size, hash=file_hash)
            session.add(new_file)
            session.flush()
            logger.info("Добавлен файл: %s", path)
            return new_file.id

    def get_file_by_hash(self, file_hash: str) -> File | None:
        with self.session_factory() as session:
            file = session.query(File).filter_by(hash=file_hash).first()
            logger.debug("Поиск файла по хэшу %s: %s", file_hash, file)
            return file

    def mark_file_as_processed(self, file_id: int) -> bool:
        with self.session_factory() as session:
            file = session.query(File).get(file_id)
            if not file:
                logger.warning("Файл не найден для отметки processed: %s", file_id)
                return False
            file.processed = True
            logger.info("Файл %s отмечен как обработанный", file_id)
            return True

    def delete_file(self, file_id: int) -> bool:
        with self.session_factory() as session:
            file = session.query(File).get(file_id)
            if not file:
                logger.warning("Файл не найден для удаления: %s", file_id)
                return False
            session.delete(file)
            logger.info("Файл удалён: %s", file_id)
            return True

    def add_image_metadata(self, file_id: int, width: int, height: int, thumbnail: bytes, caption: str) -> bool:
        with self.session_factory() as session:
            if session.query(Image).filter_by(file_id=file_id).first():
                logger.info("Метаданные изображения уже существуют для файла %s", file_id)
                return False
            image = Image(file_id=file_id, width=width, height=height, thumbnail=thumbnail, caption=caption)
            session.add(image)
            logger.info("Добавлены метаданные изображения для файла %s", file_id)
            return True

    def get_image_metadata(self, file_id: int) -> Image | None:
        with self.session_factory() as session:
            metadata = session.query(Image).filter_by(file_id=file_id).first()
            logger.debug("Метаданные изображения для файла %s: %s", file_id, metadata)
            return metadata

    def get_all_files(self) -> list[File]:
        with self.session_factory() as session:
            files = session.query(File).all()
            logger.debug("Загружены все файлы: %d", len(files))
            return files

    def get_files_by_extension(self, extension: str | None = None) -> list[str]:
        with self.session_factory() as session:
            query = session.query(File.path)
            if extension:
                extension = extension.lower() if extension.startswith('.') else f".{extension.lower()}"
                paths = [row[0] for row in query.filter(File.path.ilike(f"%{extension}")).all()]
                logger.debug("Найдено файлов с расширением %s: %d", extension, len(paths))
                return paths
            all_paths = [row[0] for row in query.all()]
            logger.debug("Найдено всех файлов: %d", len(all_paths))
            return all_paths