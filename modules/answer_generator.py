import numpy as np
import torch

from transformers import AutoModelForCausalLM
from transformers import AutoModelForQuestionAnswering
from transformers import AutoTokenizer
from transformers import BitsAndBytesConfig
from transformers import pipeline

from config_models import AppConfig
from config_models import QuantizationMode
from config_models import GenerationMode


class AnswerGeneratorAndValidator:
    def __init__(self, config: AppConfig):
        self.config = config
        self._detect_devices()
        self._init_device()
        self._init_quantization()
        self._load_models()
        self._configure_generation()

    def update_config(self, new_config: AppConfig):
        self.config = new_config
        self.reload()

    def reload(self):
        self._init_device()
        self._init_quantization()
        self._load_models()
        self._configure_generation()

    def _detect_devices(self):
        self.available_gpus = [f"cuda:{i}" for i in range(torch.cuda.device_count())] if torch.cuda.is_available() else []
        self.available_devices = self.available_gpus + ["cpu"]

    def _init_device(self):
        device = self.config.device or ("cuda:0" if self.available_gpus else "cpu")
        if device.startswith("cuda") and device not in self.available_devices:
            raise ValueError(f"GPU {device} недоступен")
        self.device = torch.device(device)
        if self.device.type == "cuda":
            torch.cuda.empty_cache()

    def _init_quantization(self):
        mode = self.config.quantization
        if mode == QuantizationMode.NF4 and self.device.type != "cuda":
            raise ValueError("4-битное квантование требует GPU")
        self.quantization = mode

    def _load_models(self):
        qa_path = self.config.models.qa
        text_path = self.config.models.text

        self.qa_tokenizer = AutoTokenizer.from_pretrained(qa_path)
        self.qa_model = AutoModelForQuestionAnswering.from_pretrained(qa_path).to(self.device)
        self.qa_pipeline = pipeline("question-answering", model=self.qa_model, tokenizer=self.qa_tokenizer, device=self.device)

        compute_dtype = torch.float16 if self.quantization in [QuantizationMode.FP16, QuantizationMode.NF4] else torch.float32
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=self.quantization == QuantizationMode.NF4,
            load_in_8bit=self.quantization == QuantizationMode.INT8,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=compute_dtype
        ) if self.quantization != QuantizationMode.FP32 else None

        self.text_tokenizer = AutoTokenizer.from_pretrained(text_path)
        self.text_model = AutoModelForCausalLM.from_pretrained(
            text_path,
            quantization_config=bnb_config,
            torch_dtype=compute_dtype,
            device_map="auto" if self.device.type == "cuda" else None
        ).to(self.device)

    def _configure_generation(self):
        mode = self.config.generation_mode
        self.generation_mode = mode
        gen_cfg = self.config.generation_config

        self.generation_config = {
            'max_length': gen_cfg.max_length,
            'min_length': gen_cfg.min_length,
            'num_return_sequences': gen_cfg.num_return_sequences,
            'no_repeat_ngram_size': gen_cfg.no_repeat_ngram_size,
            'repetition_penalty': gen_cfg.repetition_penalty,
            'early_stopping': gen_cfg.early_stopping,
        }

        if mode == GenerationMode.DETERMINISTIC:
            det_cfg = gen_cfg.deterministic
            self.generation_config.update({
                'do_sample': False,
                'num_beams': det_cfg.num_beams,
                'length_penalty': det_cfg.length_penalty,
                'no_repeat_ngram_size': det_cfg.no_repeat_ngram_size
            })
        else:
            stoch_cfg = gen_cfg.stochastic
            self.generation_config.update({
                'do_sample': True,
                'temperature': stoch_cfg.temperature,
                'top_p': stoch_cfg.top_p,
                'top_k': stoch_cfg.top_k,
                'typical_p': stoch_cfg.typical_p,
                'num_beams': stoch_cfg.num_beams
            })

    def _adjust_max_length(self, prompt):
        prompt_tokens = len(self.text_tokenizer.encode(prompt, add_special_tokens=False))
        min_length = 4096
        new_max_length = min(4096, max(min_length, int(2.5 * prompt_tokens)))
        self.generation_config['max_length'] = new_max_length

    def generate_response(self, prompt):
        try:
            self._adjust_max_length(prompt)
            
            inputs = self.text_tokenizer(prompt, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            outputs = self.text_model.generate(
                inputs["input_ids"], 
                attention_mask=inputs["attention_mask"], 
                **self.generation_config
            )

            raw_answer = self.text_tokenizer.decode(outputs[0], skip_special_tokens=True)
            return raw_answer[len(prompt):].strip()
        except Exception as e:
            print(f"Ошибка генерации: {str(e)}")
            return ""

    def get_device_info(self):
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
        return f"<AnswerGenerator(device={self.device}, quant={self.quantization}, mode={self.generation_mode})>"
