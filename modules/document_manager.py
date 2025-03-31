from pathlib import Path
from typing import Optional, List, Union

from .file_loader import FileLoader
from .file_processor import FileProcessor
from .image_captioner import ImageCaptioner

from config_models import AppConfig


class DocumentManager:
    """
    Унифицированный интерфейс для управления файлами и извлечения их содержимого/метаданных.
    Объединяет функциональность FileLoader и FileProcessor.
    """

    def __init__(self, config: AppConfig):
        self.config = config

        image_enabled = config.document_manager.image_enabled
        image_processor = ImageCaptioner(config.image_captioning) if image_enabled else None

        self.loader = FileLoader(config)
        self.processor = FileProcessor(config.document_manager, image_processor=image_processor)

    def update_config(self, new_config: AppConfig):
        self.config = new_config
        image_enabled = new_config.document_manager.image_enabled
        image_processor = ImageCaptioner(new_config.image_captioning) if image_enabled else None

        self.loader.update_config(new_config)
        self.processor.update_config(new_config.document_manager, image_processor=image_processor)

    def add_files_from_folder(self, folder_path: Union[str, Path]) -> int:
        return self.loader.add_files_from_folder(str(folder_path))

    def get_files(self, extension: Optional[str] = None) -> List[str]:
        return self.loader.get_file_list(extension)

    def get_text(self, file_path: Union[str, Path]) -> Optional[str]:
        if not self.loader.get_file_list():
            print("Файл не зарегистрирован в списке. Добавьте его сначала через add_file().")
            return None
        return self.processor.extract_text(file_path)

    def get_metadata(self, file_path: Union[str, Path]) -> dict:
        return self.processor.get_metadata(file_path)

    def get_hash(self, file_path: Union[str, Path]) -> Optional[str]:
        return self.processor.calculate_hash(file_path)

    def remove_file(self, file_path: Union[str, Path]) -> bool:
        return self.loader.remove_file(str(file_path))

    def clear_all(self) -> bool:
        return self.loader.clear_file_list()

    def is_supported_format(self, file_path: Union[str, Path]) -> bool:
        ext = Path(file_path).suffix.lower()
        return ext in self.loader.get_allowed_formats()