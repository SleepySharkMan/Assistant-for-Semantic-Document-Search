import logging
from io import BytesIO
from pathlib import Path
from typing import Dict, Union

import torch
from PIL import Image
from transformers import BlipProcessor, BlipForConditionalGeneration

from config_models import ImageCaptioningConfig

logger = logging.getLogger(__name__)

class ImageCaptioner:
    """
    Генерирует текстовое описание (caption) для изображений с помощью BLIP.
    Также может выдавать размеры изображения и thumbnail.
    """

    def __init__(self, config: ImageCaptioningConfig):
        self.config     = config
        device_str      = config.device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.device     = torch.device(device_str)
        self.model_name = config.model_name
        self.processor  = BlipProcessor.from_pretrained(self.model_name)
        self.model      = BlipForConditionalGeneration.from_pretrained(self.model_name).to(self.device)

    def extract_text(self, image_path: Union[str, Path]) -> str:
        """
        Генерирует caption для изображения.
        Ресайзит до 512×512 для экономии памяти.
        """
        image_path = Path(image_path)
        logger.debug("Начало генерации описания для %s", image_path)

        img = Image.open(image_path).convert("RGB")
        img_resized = img.resize((512, 512), Image.LANCZOS)

        inputs = self.processor(images=img_resized, return_tensors="pt").to(self.device)
        out = self.model.generate(**inputs)
        caption = self.processor.decode(out[0], skip_special_tokens=True).strip()

        logger.debug("Сгенерировано описание для %s: %s", image_path, caption)
        return caption

    def extract_metadata(self, image_path: Union[str, Path]) -> Dict:
        """
        Возвращает словарь с:
          - caption: сгенерированное описание
          - width, height: оригинальный размер изображения
          - thumbnail: PNG-миниатюра 128×128
        """
        image_path = Path(image_path)
        logger.debug("Извлечение metadata для %s", image_path)

        img = Image.open(image_path).convert("RGB")
        width, height = img.size

        # создаём thumbnail
        thumb = img.copy()
        thumb.thumbnail((128, 128), Image.LANCZOS)
        buf = BytesIO()
        thumb.save(buf, format="PNG")
        thumbnail_bytes = buf.getvalue()

        # генерируем caption
        caption = self.extract_text(image_path)

        logger.debug(
            "Metadata для %s: width=%d, height=%d, thumbnail_size=%d bytes",
            image_path, width, height, len(thumbnail_bytes)
        )
        return {
            "caption": caption,
            "width": width,
            "height": height,
            "thumbnail": thumbnail_bytes
        }

    def update_config(self, new_config: ImageCaptioningConfig) -> None:
        model_changed  = self.config.model_name != new_config.model_name
        device_changed = self.config.device     != new_config.device
        self.config = new_config

        if model_changed or device_changed:
            device_str      = new_config.device or ("cuda" if torch.cuda.is_available() else "cpu")
            self.device     = torch.device(device_str)
            self.model_name = new_config.model_name
            self.processor  = BlipProcessor.from_pretrained(self.model_name)
            self.model      = BlipForConditionalGeneration.from_pretrained(self.model_name).to(self.device)
