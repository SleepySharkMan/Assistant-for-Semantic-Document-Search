from __future__ import annotations

import logging
import mimetypes
import time
from pathlib import Path
from typing import List, Optional, Union

from .file_processor import FileProcessor
from .image_captioner import ImageCaptioner
from .file_metadata_db import FileMetadataDB
from config_models import DocumentManagerConfig

logger = logging.getLogger(__name__)


class DocumentManager:
    def __init__(self, config: DocumentManagerConfig, metadata_db: FileMetadataDB) -> None:
        self.config = config
        self.db = metadata_db
        self.allowed_file_extensions = {
            ext.lower() for ext in config.processing.allowed_extensions
        }
        self._build_processor(config)

    def is_supported_format(self, file_path: Union[str, Path]) -> bool:
        path = Path(file_path)
        if path.suffix.lower() in self.allowed_file_extensions:
            return True
        mime, _ = mimetypes.guess_type(path.name)
        return bool(mime and mime.startswith(("text/", "image/", "application/pdf")))

    def get_files(self, extension: Optional[str] = None) -> List[str]:
        return self.db.get_files_by_extension(extension)

    def get_text(self, file_path: Union[str, Path]) -> Optional[str]:
        start = time.perf_counter()
        text = self.processor.extract_text(file_path)
        logger.debug("extract_text(%s) — %.3f s", file_path, time.perf_counter() - start)
        return text

    def get_metadata(self, file_path: Union[str, Path]) -> dict:
        return self.processor.get_metadata(file_path)

    def get_hash(self, file_path: Union[str, Path]) -> Optional[str]:
        return self.processor.calculate_hash(file_path)

    def save_metadata(self, file_path: Union[str, Path]) -> None:
        meta = self.get_metadata(file_path)
        meta["hash"] = self.get_hash(file_path)
        self.db.upsert_metadata(str(file_path), meta)

    def update_config(self, new_config: DocumentManagerConfig) -> None:
        if new_config == self.config:
            return
        self.config = new_config
        self.allowed_file_extensions = {
            ext.lower() for ext in new_config.processing.allowed_extensions
        }
        self._build_processor(new_config)
        logger.info("DocumentManager: config updated")

    def _build_processor(self, cfg: DocumentManagerConfig) -> None:
        image_proc = None
        if cfg.processing.image_enabled:
            image_proc = ImageCaptioner(cfg.captioning)
        self.processor = FileProcessor(cfg.processing, image_processor=image_proc)
