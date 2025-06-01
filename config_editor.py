import torch
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple
from ruamel.yaml import YAML
from config_loader import ConfigLoader
from config_models import GenerationMode, QuantizationMode
from dataclasses import asdict, is_dataclass
from enum import Enum
from ruamel.yaml.comments import CommentedMap

def asdict_with_enums(obj):
    def convert_value(val):
        if isinstance(val, Enum):
            return val.value
        if is_dataclass(val):
            return asdict_with_enums(val)
        if isinstance(val, dict):
            return {k: convert_value(v) for k, v in val.items()}
        if isinstance(val, list):
            return [convert_value(item) for item in val]
        return val
    return asdict(obj, dict_factory=lambda x: {k: convert_value(v) for k, v in x})

class ConfigEditor:
    def __init__(self, config_path: str | Path, components: Dict[str, Any] | None = None):
        self.config_path = Path(config_path)
        self.component_map: Dict[str, Any] = components or {}
        self._yaml = YAML()
        self._yaml.preserve_quotes = True
        self._load()  # загружаем YAML в self._yaml_data

    def _cast_scalar(self, value):
        if isinstance(value, str):
            lower = value.lower()
            if lower == "true":
                return True
            if lower == "false":
                return False

            if re.fullmatch(r"-?\d+", value):
                try:
                    return int(value)
                except ValueError:
                    pass

            if re.fullmatch(r"-?\d+\.\d+", value):
                try:
                    return float(value)
                except ValueError:
                    pass

        return value

    def update(self, dotted_path: str, value):
        """
        Исправленный метод update:
        - вместо self.data используем self._yaml_data,
        - вместо save() вызываем _save().
        """
        casted_value = self._cast_scalar(value)

        keys = dotted_path.split(".")
        node = self._yaml_data  # ВАЖНО: теперь работаем с _yaml_data
        for k in keys[:-1]:
            if not isinstance(node, CommentedMap):
                raise TypeError(f"Узел `{k}` в пути `{dotted_path}` — не mapping, а {type(node)}")
            # Спускаемся глубже
            node = node[k]

        last_key = keys[-1]
        if not isinstance(node, CommentedMap):
            raise TypeError(f"Невозможно установить `{dotted_path}`: узел `{keys[-2]}` — не mapping, а {type(node)}")

        node[last_key] = casted_value
        self._save()  # вместо save() вызываем _save()
        # После сохранения можно обновить dataclass-версию конфига:
        self._reload_dataclass()
        # И распространить изменения на компоненты, если нужно
        self._propagate_update(keys[0])

    def suggest_generation_params(self) -> Dict[str, Any]:
        device, mem_gb = self._detect_device()
        q, mode, gen = self._heuristic_for_memory(mem_gb)
        return {
            "device": device,
            "quantization": q.value,
            "generation_mode": mode.value,
            "generation": gen,
        }

    def apply_suggested_generation_params(self) -> Dict[str, Any]:
        """
        Предлагает оптимальные параметры генерации в зависимости от доступной памяти
        и применяет их к уже существующему разделу answer_generator, обновляя
        только вложенные поля, но не затрагивая другие (например, text_model_path).
        """
        params = self.suggest_generation_params()

        # 1) Обновляем базовые поля answer_generator
        #    (тут мы не затираем раздел целиком, а обновляем только конкретные ключи)
        if "device" in params:
            self.update("answer_generator.device", params["device"])
        if "quantization" in params:
            self.update("answer_generator.quantization", params["quantization"])
        if "generation_mode" in params:
            self.update("answer_generator.generation_mode", params["generation_mode"])

        # 2) Обновляем параметры генерации внутри answer_generator.generation.*
        # Собираем вложенный словарь из предложенных параметров
        gen_params = params.get("generation", {})

        # 2.1) Общие параметры для обоих режимов (deterministic и stochastic)
        common_keys = [
            "max_new_tokens",
            "num_return_sequences",
            "no_repeat_ngram_size",
            "repetition_penalty",
            "early_stopping",
            "enable_cpu_offload",
        ]
        for key in common_keys:
            if key in gen_params:
                self.update(f"answer_generator.generation.{key}", gen_params[key])

        # 2.2) Обновляем только ту группу, которая соответствует выбранному режиму
        mode = params.get("generation_mode", "").lower()

        # Если пользователь выбрал детерминированный режим
        if mode == GenerationMode.DETERMINISTIC.value:
            det_keys = ["num_beams", "length_penalty", "no_repeat_ngram_size"]
            for key in det_keys:
                # Убедимся, что этот ключ есть в предложенных параметрах
                if key in gen_params:
                    self.update(f"answer_generator.generation.deterministic.{key}", gen_params[key])

        # Если пользователь выбрал стохастический режим
        elif mode == GenerationMode.STOCHASTIC.value:
            stoch_keys = ["temperature", "top_p", "top_k", "typical_p", "num_beams"]
            for key in stoch_keys:
                if key in gen_params:
                    self.update(f"answer_generator.generation.stochastic.{key}", gen_params[key])

        return params

    def register_component(self, top_key: str, component: Any) -> None:
        self.component_map[top_key] = component

    def unregister_component(self, top_key: str) -> None:
        self.component_map.pop(top_key, None)

    def get_config(self):
        return self._app_config

    def _detect_device(self) -> Tuple[str, float]:
        pref = None
        if hasattr(self._app_config, "answer_generator"):
            pref = getattr(self._app_config.answer_generator, "device", None)
        if isinstance(pref, str):
            p = pref.lower()
            if p == "cpu":
                return "cpu", self._get_ram_gb()
            if p.startswith("cuda"):
                idx = self._parse_cuda_index(p)
                if torch.cuda.is_available():
                    prop = torch.cuda.get_device_properties(idx)
                    return f"cuda:{idx}", prop.total_memory / 1e9
        if torch.cuda.is_available():
            idx = torch.cuda.current_device()
            prop = torch.cuda.get_device_properties(idx)
            return f"cuda:{idx}", prop.total_memory / 1e9
        return "cpu", self._get_ram_gb()

    @staticmethod
    def _parse_cuda_index(dev: str) -> int:
        try:
            return int(dev.split(":", 1)[1])
        except (IndexError, ValueError):
            return 0

    @staticmethod
    def _get_ram_gb() -> float:
        try:
            import psutil
            return psutil.virtual_memory().total / 1e9
        except ModuleNotFoundError:
            return 8.0

    @staticmethod
    def _heuristic_for_memory(mem_gb: float):
        base = {
            "num_return_sequences": 1,
            "no_repeat_ngram_size": 3,
            "repetition_penalty": 1.1,
            "early_stopping": False,
        }
        if mem_gb < 8:
            q, m = QuantizationMode.NF4, GenerationMode.STOCHASTIC
            gen = {
                **base,
                "max_new_tokens": 256,
                "enable_cpu_offload": True,
                "temperature": 0.95,
                "top_p": 0.8,
                "top_k": 40,
                "typical_p": 0.9,
                "num_beams": 1,
            }
        elif mem_gb < 16:
            q, m = QuantizationMode.INT8, GenerationMode.STOCHASTIC
            gen = {
                **base,
                "max_new_tokens": 512,
                "enable_cpu_offload": True,
                "temperature": 0.9,
                "top_p": 0.8,
                "top_k": 40,
                "typical_p": 0.9,
                "num_beams": 1,
            }
        elif mem_gb < 24:
            q, m = QuantizationMode.FP16, GenerationMode.DETERMINISTIC
            gen = {
                **base,
                "max_new_tokens": 1024,
                "enable_cpu_offload": False,
                "num_beams": 1,
                "length_penalty": 0.7,
                "no_repeat_ngram_size": 4,
            }
        else:
            q, m = QuantizationMode.FP32, GenerationMode.DETERMINISTIC
            gen = {
                **base,
                "max_new_tokens": 2048,
                "enable_cpu_offload": False,
                "num_beams": 1,
                "length_penalty": 0.7,
                "no_repeat_ngram_size": 4,
            }
        return q, m, gen

    def _load(self):
        """
        Загружаем файл config.yaml в self._yaml_data и сразу обновляем dataclass-версию.
        """
        with self.config_path.open("r", encoding="utf-8") as f:
            self._yaml_data = self._yaml.load(f) or CommentedMap()
        self._reload_dataclass()

    def _save(self):
        """
        Сохраняем текущее self._yaml_data обратно в файл.
        """
        with self.config_path.open("w", encoding="utf-8") as f:
            self._yaml.dump(self._yaml_data, f)

    def _reload_dataclass(self):
        """
        Перезагружаем dataclass-объект из свежего config.yaml.
        """
        loader = ConfigLoader(str(self.config_path))
        self._app_config = loader.full

    def _traverse(self, parts: List[str]):
        """
        Вспомогательный метод для обхода вложенной структуры self._yaml_data по списку ключей.
        """
        node = self._yaml_data
        for p in parts:
            if p not in node:
                raise KeyError(f"key '{p}' not found")
            node = node[p]
        return node

    def _propagate_update(self, top_key: str):
        """
        Если в component_map зарегистрирована компонента с именем top_key,
        вызовем у неё update_config или reload с новым под-config.
        """
        comp = self.component_map.get(top_key)
        if not comp:
            return
        new_cfg = getattr(self._app_config, top_key)
        if hasattr(comp, "update_config"):
            comp.update_config(new_cfg)
        elif hasattr(comp, "reload"):
            comp.reload(config=new_cfg)

    def _validate(self, path: str, value: Any):
        low = path.lower()
        if low.endswith(".quantization"):
            self._ensure_enum(value, QuantizationMode, path)
        elif low.endswith(".generation_mode"):
            self._ensure_enum(value, GenerationMode, path)
        elif low == "dialog_manager.prompt_template":
            if "{context}" not in value or "{question}" not in value:
                raise ValueError("prompt_template must contain {context} and {question}")
        if isinstance(value, (int, float)) and value < 0:
            raise ValueError(f"{path}: negative values not allowed")

    @staticmethod
    def _ensure_enum(value: Any, enum_cls, path: str):
        if str(value).lower() not in {e.value for e in enum_cls}:
            raise ValueError(f"{path}: invalid value")
