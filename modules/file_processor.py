import mimetypes
import hashlib
import logging

from pathlib import Path
from typing import Optional, Union, Dict

from PyPDF2 import PdfReader
from docx import Document

from config_models import DocumentManagerConfig

logger = logging.getLogger(__name__)

class FileProcessor:
    """
    Обрабатывает файлы разных типов:
      - текстовые (txt и др.)
      - PDF
      - DOCX
      - изображения (через image_processor), если включено в конфиге
    """

    def __init__(self, config: DocumentManagerConfig, image_processor=None):
        self.config = config
        self.image_processor = image_processor
        mimetypes.init()
        logger.info("FileProcessor инициализирован: image_enabled=%s", config.image_enabled)

    def update_config(self, new_config: DocumentManagerConfig, image_processor=None) -> None:
        """
        Обновляет конфигурацию обработки файлов и, при необходимости,
        заменяет image_processor.
        """
        self.config = new_config
        if image_processor is not None:
            self.image_processor = image_processor
        logger.info("FileProcessor: конфигурация обновлена, image_enabled=%s", new_config.image_enabled)

    def extract_text(self, file_path: Union[str, Path]) -> Optional[str]:
        """
        Извлекает текст из файла. Для изображений вызывает image_processor.extract_text.
        Возвращает None, если формат не поддерживается или при ошибке.
        """
        file_path = Path(file_path)
        logger.debug("Начало extract_text для %s", file_path)

        if not file_path.exists():
            logger.warning("Файл не найден: %s", file_path)
            return None

        mime_type = self._get_mime_type(file_path)
        try:
            if mime_type and mime_type.startswith('text/'):
                text = self._extract_text(file_path)
            elif mime_type == 'application/pdf':
                text = self._extract_pdf(file_path)
            elif mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                text = self._extract_docx(file_path)
            elif mime_type and mime_type.startswith('image/') and self.image_processor and self.config.image_enabled:
                text = self.image_processor.extract_text(str(file_path))
            else:
                logger.warning("Неподдерживаемый формат %s для %s", mime_type, file_path)
                return None

            length = len(text) if text else 0
            logger.debug("Завершено extract_text для %s, длина текста: %d", file_path, length)
            return text

        except Exception as e:
            logger.error("Ошибка обработки файла %s: %s", file_path, e, exc_info=True)
            return None

    def get_metadata(self, file_path: Union[str, Path]) -> Dict:
        """
        Возвращает метаданные файла: путь, размер, время создания/модификации, MIME-тип.
        """
        file_path = Path(file_path)
        stat = file_path.stat()
        metadata = {
            'path': str(file_path.absolute()),
            'size': stat.st_size,
            'created': getattr(stat, 'st_birthtime', stat.st_ctime),
            'modified': stat.st_mtime,
            'mime_type': self._get_mime_type(file_path)
        }
        logger.debug("Метаданные для %s: %s", file_path, metadata)
        return metadata

    def calculate_hash(self, file_path: Union[str, Path], algorithm: str = 'sha256') -> Optional[str]:
        """
        Вычисляет хэш файла указанным алгоритмом (по умолчанию SHA-256).
        """
        try:
            hash_func = hashlib.new(algorithm)
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    hash_func.update(chunk)
            digest = hash_func.hexdigest()
            logger.debug("Хэш %s для %s: %s", algorithm, file_path, digest)
            return digest
        except Exception as e:
            logger.error("Ошибка вычисления хеша для %s: %s", file_path, e, exc_info=True)
            return None

    def _get_mime_type(self, file_path: Path) -> str:
        """
        Определяет MIME-тип по расширению файла.
        """
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or 'application/octet-stream'

    def _extract_text(self, file_path: Path) -> str:
        """
        Прочитать текстовый файл как UTF-8.
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    def _extract_pdf(self, file_path: Path) -> str:
        """
        Извлечь текст из PDF с помощью PyPDF2.
        """
        texts = []
        with open(file_path, 'rb') as f:
            reader = PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    texts.append(page_text)
        return '\n'.join(texts)

    def _extract_docx(self, file_path: Path) -> str:
        """
        Извлечь текст из DOCX через python-docx.
        """
        doc = Document(file_path)
        return '\n'.join(p.text for p in doc.paragraphs if p.text)