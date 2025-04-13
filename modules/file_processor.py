import mimetypes
import hashlib

from pathlib import Path
from typing import Optional, Union, Dict

from PyPDF2 import PdfReader
from docx import Document

from config_models import DocumentManagerConfig


class FileProcessor:
    def __init__(self, config: DocumentManagerConfig, image_processor=None):
        self.config = config
        self.image_processor = image_processor
        mimetypes.init()

    def update_config(self, new_config: DocumentManagerConfig, image_processor=None) -> None:
        self.config = new_config
        if image_processor is not None:
            self.image_processor = image_processor

    def extract_text(self, file_path: Union[str, Path]) -> Optional[str]:
        file_path = Path(file_path)
        if not file_path.exists():
            print(f"Файл {file_path} не найден.")
            return None

        try:
            mime_type = self._get_mime_type(file_path)

            if mime_type.startswith('text/'):
                return self._extract_text(file_path)
            if mime_type == 'application/pdf':
                return self._extract_pdf(file_path)
            if mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                return self._extract_docx(file_path)
            if mime_type.startswith('image/') and self.image_processor and self.config.image_enabled:
                return self.image_processor.extract_text(file_path)

            print(f"Формат {mime_type} не поддерживается.")
            return None

        except Exception as e:
            print(f"Ошибка обработки файла {file_path}: {str(e)}")
            return None

    def get_metadata(self, file_path: Union[str, Path]) -> Dict:
        file_path = Path(file_path)
        stat = file_path.stat()
        return {
            'path': str(file_path.absolute()),
            'size': stat.st_size,
            'created': stat.st_birthtime if hasattr(stat, 'st_birthtime') else stat.st_ctime,
            'modified': stat.st_mtime,
            'mime_type': self._get_mime_type(file_path)
        }

    def calculate_hash(self, file_path: Union[str, Path], algorithm: str = 'sha256') -> Optional[str]:
        try:
            hash_func = hashlib.new(algorithm)
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    hash_func.update(chunk)
            return hash_func.hexdigest()
        except Exception as e:
            print(f"Ошибка вычисления хеша: {str(e)}")
            return None

    def _get_mime_type(self, file_path: Path) -> str:
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or 'application/octet-stream'

    def _extract_text(self, file_path: Path) -> str:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    def _extract_pdf(self, file_path: Path) -> str:
        text = []
        with open(file_path, 'rb') as f:
            reader = PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text.append(page_text)
        return '\n'.join(text)

    def _extract_docx(self, file_path: Path) -> str:
        doc = Document(file_path)
        return '\n'.join(paragraph.text for paragraph in doc.paragraphs if paragraph.text)
