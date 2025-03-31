import yaml
from pathlib import Path

from config_models import AppConfig
from config_models import DeterministicConfig
from config_models import DocumentManagerConfig
from config_models import EmbeddingStorageConfig
from config_models import FileMetadataDBConfig
from config_models import GenerationConfig
from config_models import GenerationMode
from config_models import ImageCaptioningConfig
from config_models import ModelConfig
from config_models import QuantizationMode
from config_models import SpeechConfig
from config_models import StochasticConfig
from config_models import TextSplitterConfig


class ConfigLoader:
    """Загружает конфигурацию из YAML и преобразует в типизированный AppConfig."""

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self._raw = self._load_yaml()
        self.config = self._parse_config(self._raw)

    def _load_yaml(self) -> dict:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Конфиг '{self.config_path}' не найден")
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _parse_config(self, raw: dict) -> AppConfig:
        return AppConfig(
            device=raw["device"],
            quantization=QuantizationMode(raw["quantization"]),
            generation_mode=GenerationMode(raw["generation_mode"]),
            allowed_formats=raw["allowed_formats"],
            models=ModelConfig(**raw["models"]),
            text_splitter=TextSplitterConfig(**raw["text_splitter"]),
            embedding_storage=EmbeddingStorageConfig(**raw["embedding_storage"]),
            file_metadata_db=FileMetadataDBConfig(**raw["file_metadata_db"]),
            speech=SpeechConfig(**raw["speech"]),
            image_captioning=ImageCaptioningConfig(**raw["image_captioning"]),
            document_manager=DocumentManagerConfig(**raw["document_manager"]),
            generation_config=GenerationConfig(
                max_length=raw["generation_config"]["max_length"],
                min_length=raw["generation_config"]["min_length"],
                num_return_sequences=raw["generation_config"]["num_return_sequences"],
                no_repeat_ngram_size=raw["generation_config"]["no_repeat_ngram_size"],
                repetition_penalty=raw["generation_config"]["repetition_penalty"],
                early_stopping=raw["generation_config"]["early_stopping"],
                deterministic=DeterministicConfig(**raw["generation_config"]["deterministic"]),
                stochastic=StochasticConfig(**raw["generation_config"]["stochastic"])
            )
        )

    def reload(self):
        self.__init__(self.config_path)

    @property
    def full(self) -> AppConfig:
        return self.config
