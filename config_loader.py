import json
import yaml
from pathlib import Path
from dataclasses import asdict, is_dataclass, fields
from typing import get_origin, get_args

from config_models import AppConfig


class ConfigLoader:
    """
    Загружает YAML и преобразует в AppConfig (включая вложенные структуры).
    """

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self._raw = self._load_yaml()
        self.config = self._from_dict(AppConfig, self._raw)

    def _load_yaml(self) -> dict:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Конфигурационный файл не найден: {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def reload(self):
        """
        Повторно загружает YAML и пересоздаёт AppConfig.
        """
        self.__init__(str(self.config_path))

    @property
    def full(self) -> AppConfig:
        return self.config

    def to_dict(self) -> dict:
        return asdict(self.config)

    def to_pretty_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    def _from_dict(self, cls, data: dict):
        """
        Рекурсивно конвертирует словарь в dataclass, включая вложенные структуры.
        """
        if not is_dataclass(cls):
            return data

        kwargs = {}
        for field in fields(cls):
            key = field.name
            field_type = field.type
            value = data.get(key)

            if value is None:
                continue

            origin = get_origin(field_type)
            args = get_args(field_type)

            if is_dataclass(field_type):
                value = self._from_dict(field_type, value)

            elif origin is list and len(args) == 1 and is_dataclass(args[0]):
                value = [self._from_dict(args[0], item) for item in value]

            kwargs[key] = value

        return cls(**kwargs)
