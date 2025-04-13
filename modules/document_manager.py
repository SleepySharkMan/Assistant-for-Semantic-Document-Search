from pathlib import Path
from typing import Optional, List, Union

from .file_processor import FileProcessor
from .image_captioner import ImageCaptioner
from .file_metadata_db import FileMetadataDB

from config_models import AppConfig


class DocumentManager:
    """
    Унифицированный интерфейс для работы с файлами:
    извлечение текста, получение метаданных и хэшей, фильтрация по формату.
    """

    def __init__(self, config: AppConfig, metadata_db: FileMetadataDB):
        self.config = config
        self.metadata_db = metadata_db
        self.allowed_file_extensions = config.allowed_file_extensions  

        image_enabled = config.document_processing.image_enabled
        image_processor = ImageCaptioner(config.image_captioning) if image_enabled else None

        self.processor = FileProcessor(config.document_processing, image_processor=image_processor)

    def update_config(self, new_config: AppConfig) -> None:
        self.config = new_config
        self.allowed_file_extensions = new_config.allowed_file_extensions

        image_enabled = new_config.document_processing.image_enabled
        image_processor = self.processor.image_processor

        if image_enabled and image_processor is None:
            image_processor = ImageCaptioner(new_config.image_captioning)

        self.processor.update_config(new_config.document_processing, image_processor=image_processor)

    def is_supported_format(self, file_path: Union[str, Path]) -> bool:
        ext = Path(file_path).suffix.lower()
        return ext in self.allowed_file_extensions

    def get_files(self, extension: Optional[str] = None) -> List[str]:
        return self.metadata_db.get_files_by_extension(extension)

    def get_text(self, file_path: Union[str, Path]) -> Optional[str]:
        return self.processor.extract_text(file_path)

    def get_metadata(self, file_path: Union[str, Path]) -> dict:
        return self.processor.get_metadata(file_path)

    def get_hash(self, file_path: Union[str, Path]) -> Optional[str]:
        return self.processor.calculate_hash(file_path)
