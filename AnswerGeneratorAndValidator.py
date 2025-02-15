import torch
from enum import Enum
from transformers import (
    AutoTokenizer,
    AutoModelForQuestionAnswering,
    AutoModelForCausalLM,
    pipeline,
    BitsAndBytesConfig
)
import re


class GenerationMode(Enum):
    DETERMINISTIC = "deterministic"
    STOCHASTIC = "stochastic"


class QuantizationMode(Enum):
    """
    Режимы квантования для оптимизации размера модели и скорости выполнения

    Параметры:
    -----------
    FP32 : 
        - Память: ~28 ГБ (7B параметров)
        - Описание: 32-битная точность (стандартный формат), максимальная точность вычислений
        - Использование: Для задач, требующих высокой точности, без ограничений по памяти

    FP16 : 
        - Память: ~14 ГБ (7B параметров)
        - Описание: 16-битная точность, оптимальный баланс скорости и точности
        - Использование: Основной выбор для GPU, ускоряет вычисления в 2-3 раза

    INT8 : 
        - Память: ~7 ГБ (7B параметров)
        - Описание: 8-битное целочисленное квантование
        - Использование: Для CPU, мобильных устройств или слабых GPU

    NF4 : 
        - Память: ~3.5 ГБ (7B параметров)
        - Описание: 4-битное нормализованное квантование
        - Использование: Для гигантских моделей (>10B параметров) на современных GPU

    Примечания:
    -----------
    1. Значения памяти даны для модели с 7 миллиардами параметров.
    2. Реальное потребление может отличаться на ±15% из-за:
       - Накладных расходов фреймворка
       - Дополнительных метаданных
       - Особенностей реализации модели
    3. Для NF4 требуется:
       - CUDA-совместимый GPU (NVIDIA)
       - Библиотеки типа `bitsandbytes`
    """

    FP32 = "fp32"
    FP16 = "fp16"
    INT8 = "int8"
    NF4 = "nf4"


class AnswerGeneratorAndValidator:
    def __init__(self, qa_model_path, text_model_path):
        """Инициализация класса с автоматическим выбором устройств и квантования"""
        self._detect_devices()
        self._init_device()
        self._init_quantization()
        self.generation_mode = GenerationMode.STOCHASTIC
        self._load_models(qa_model_path, text_model_path)
        self._configure_generation()

    def _detect_devices(self):
        """Обнаружение доступных устройств"""
        self.available_gpus = []
        if torch.cuda.is_available():
            self.available_gpus = [
                f"cuda:{i}" for i in range(torch.cuda.device_count())]
        self.available_devices = self.available_gpus + ["cpu"]

    def switch_to_cpu(self):
        """Принудительное переключение на CPU"""
        self.device = torch.device("cpu")
        self._reinitialize_models()

    def switch_to_gpu(self, device_id=0):
        """Переключение на указанный GPU"""
        if not self.available_gpus:
            raise RuntimeError("NVIDIA GPU не обнаружены")
        if device_id >= len(self.available_gpus):
            raise ValueError(f"GPU {device_id} недоступен")
        self.device = torch.device(f"cuda:{device_id}")
        torch.cuda.empty_cache()
        self._reinitialize_models()

    def _init_device(self):
        """Автоматическая инициализация устройства"""
        self.device = torch.device("cuda:0" if self.available_gpus else "cpu")

    def _init_quantization(self):
        """Автоматический выбор квантования"""
        if self.device.type == "cuda":
            mem_gb = torch.cuda.get_device_properties(
                self.device).total_memory / 1e9
            self.quantization = QuantizationMode.NF4 if mem_gb >= 8 else QuantizationMode.INT8
        else:
            self.quantization = QuantizationMode.FP32

    def set_quantization(self, mode: QuantizationMode):
        """Ручная установка квантования"""
        if mode == QuantizationMode.NF4 and self.device.type != "cuda":
            raise ValueError("4-битное квантование требует GPU")
        self.quantization = mode
        self._reinitialize_models()

    def _load_models(self, qa_path, text_path):
        """Загрузка моделей с учетом текущих настроек"""
        # Загрузка QA модели
        self.qa_tokenizer = AutoTokenizer.from_pretrained(qa_path)
        self.qa_model = AutoModelForQuestionAnswering.from_pretrained(
            qa_path).to(self.device)
        self.qa_pipeline = pipeline(
            "question-answering",
            model=self.qa_model,
            tokenizer=self.qa_tokenizer,
            device=self.device
        )

        # Конфигурация генеративной модели
        compute_dtype = torch.float16 if self.quantization in [
            QuantizationMode.FP16, QuantizationMode.NF4] else torch.float32
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=self.quantization == QuantizationMode.NF4,
            load_in_8bit=self.quantization == QuantizationMode.INT8,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=compute_dtype
        )

        # Загрузка текстовой модели
        self.text_tokenizer = AutoTokenizer.from_pretrained(text_path)
        self.text_model = AutoModelForCausalLM.from_pretrained(
            text_path,
            quantization_config=bnb_config if self.quantization != QuantizationMode.FP32 else None,
            torch_dtype=compute_dtype,
            device_map="auto" if self.device.type == "cuda" else None
        ).to(self.device)

    def _reinitialize_models(self):
        """Переинициализация моделей при изменении настроек"""
        self._init_quantization()
        self._load_models(self.qa_model.name_or_path,
                          self.text_model.name_or_path)
        self._configure_generation()

    def _configure_generation(self):
        """Конфигурация параметров генерации с автоматической валидацией"""
        base_params = {
            'max_length': 2048 if self.device.type == "cuda" else 512,
            'min_length': 300,
            'num_return_sequences': 1,
            'no_repeat_ngram_size': 3,
            'repetition_penalty': 1.1,
            'early_stopping': False
        }

        # Детерминированный режим (beam search)
        if self.generation_mode == GenerationMode.DETERMINISTIC:
            # Для детерминированного режима (DETERMINISTIC):
            self.generation_config = {
                **base_params,
                'do_sample': False,
                'num_beams': 6,
                'length_penalty': 0.9,
                'no_repeat_ngram_size': 4
            }

        # Стохастический режим (сэмплирование)
        else:
            self.generation_config = {
                **base_params,
                'do_sample': True,
                'temperature': 0.9,    # Больше креативности
                'top_p': 0.7,          # Умеренный контроль разнообразия
                'top_k': 30,           # Расширенный словарный запас
                'typical_p': 0.9,      # Естественность текста
                'num_beams': 1
            }

        # Автокоррекция для слабых GPU/CPU
        if self.device.type == "cpu":
            self.generation_config.update({
                'max_length': 768,
                'num_beams': 2 if self.generation_mode == GenerationMode.DETERMINISTIC else 1
            })

    def _adjust_max_length(self, prompt):
        """Динамически увеличивает max_length в зависимости от длины входного текста."""
        prompt_tokens = len(self.text_tokenizer.encode(
            prompt, add_special_tokens=False))
        min_length = 4096
        new_max_length = min(4096, max(min_length, int(2.5 * prompt_tokens)))

        self.generation_config['max_length'] = new_max_length

    def set_generation_mode(self, mode: GenerationMode):
        """Установка режима генерации"""
        self.generation_mode = mode
        self._configure_generation()

    def find_answer(self, contexts, question):
        """Поиск ответа в предоставленных контекстах"""
        best_answers = []
        for ctx in contexts:
            try:
                result = self.qa_pipeline(question=question, context=ctx)
                if len(result['answer']) >= 3 and result['answer'].lower() in ctx.lower():
                    best_answers.append({
                        'answer': result['answer'],
                        'score': result['score'],
                        'context': ctx
                    })
            except Exception as e:
                print(f"Ошибка обработки контекста: {str(e)}")

        if not best_answers:
            return "Ответ не найден"

        best_answers.sort(key=lambda x: x['score'], reverse=True)
        best = best_answers[0]

        # Расширение коротких ответов
        if len(best['answer']) < 10:
            sentences = re.findall(r'[^.!?]*[.!?]', best['context'])
            matches = [s.strip()
                       for s in sentences if best['answer'].lower() in s.lower()]
            if matches:
                best['answer'] = max(matches, key=len)

        return best['answer']

    def generate_response(self, prompt, context=None):
        """Генерация текста с улучшенной постобработкой"""
        try:
            self._adjust_max_length(prompt)
            inputs = self.text_tokenizer(
                prompt, return_tensors="pt").to(self.device)

            outputs = self.text_model.generate(
                inputs.input_ids,
                attention_mask=inputs.attention_mask,
                **self.generation_config
            )

            raw_answer = self.text_tokenizer.decode(
                outputs[0], skip_special_tokens=True)

            return raw_answer[len(prompt):].strip()

        except Exception as e:
            print(f"Ошибка генерации: {str(e)}")
            return ""

    def get_device_info(self):
        """Получение информации об устройстве"""
        info = {
            "type": "GPU" if self.device.type == "cuda" else "CPU",
            "quantization": self.quantization.value
        }
        if self.device.type == "cuda":
            prop = torch.cuda.get_device_properties(self.device)
            info.update({
                "name": prop.name,
                "memory_gb": round(prop.total_memory / 1e9, 1),
                "compute_capability": f"{prop.major}.{prop.minor}"
            })
        return info

    def __repr__(self):
        return f"<AnswerGenerator(device={self.device}, quant={self.quantization}, mode={self.generation_mode}>"
