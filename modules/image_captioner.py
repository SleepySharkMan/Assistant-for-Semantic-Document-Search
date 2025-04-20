import torch
import logging
from PIL import Image

from transformers import BlipProcessor
from transformers import BlipForConditionalGeneration

from pathlib import Path
from typing import Union

from config_models import ImageCaptioningConfig

logger = logging.getLogger(__name__)

class ImageCaptioner:
    def __init__(self, config: ImageCaptioningConfig):
        self.config = config
        self.device = torch.device(self.config.device or ("cuda" if torch.cuda.is_available() else "cpu"))
        self.model_name = self.config.model_name

        self.processor = BlipProcessor.from_pretrained(self.model_name)
        self.model = BlipForConditionalGeneration.from_pretrained(self.model_name).to(self.device)

    def update_config(self, new_config: ImageCaptioningConfig) -> None:
        model_changed  = self.config.model_name != new_config.model_name
        device_changed = self.config.device != new_config.device

        self.config = new_config

        if model_changed or device_changed:
            self.device = torch.device(
                self.config.device or ("cuda" if torch.cuda.is_available() else "cpu")
            )
            self.model_name = self.config.model_name
            self.processor = BlipProcessor.from_pretrained(self.model_name)
            self.model = BlipForConditionalGeneration.from_pretrained(self.model_name).to(self.device)


    def extract_text(self, image_path: Union[str, Path]) -> str:
        try:
            image = Image.open(image_path).convert("RGB")
            inputs = self.processor(images=image, return_tensors="pt").to(self.device)
            out = self.model.generate(**inputs)
            return self.processor.decode(out[0], skip_special_tokens=True).strip()
        except Exception as e:
            logger.error("Ошибка генерации описания изображения: %s", e, exc_info=True)
            return ""
