import numpy as np
import torch
import logging

from transformers import AutoModelForCausalLM
from transformers import AutoModelForQuestionAnswering
from transformers import AutoTokenizer
from transformers import BitsAndBytesConfig
from transformers import pipeline

from config_models import AppConfig
from config_models import QuantizationMode
from config_models import GenerationMode

logger = logging.getLogger(__name__)

class AnswerGeneratorAndValidator:
    def __init__(self, config: AppConfig):
        self.config = config
        self._detect_devices()
        self._init_device()
        self._init_quantization()
        self._load_models()
        self._configure_generation()

    def update_config(self, new_config: AppConfig) -> None:
        reload_device = self.config.device != new_config.device
        reload_quant  = self.config.quantization != new_config.quantization
        reload_models = (
            self.config.models.text != new_config.models.text or
            self.config.models.qa   != new_config.models.qa
        )
        reload_gen_cfg = self.config.generation != new_config.generation
        reload_mode    = self.config.generation_mode != new_config.generation_mode

        self.config = new_config

        if reload_device or reload_quant:
            self._init_device()
            self._init_quantization()

        if reload_models or reload_device or reload_quant:
            self._load_models()

        if reload_gen_cfg or reload_mode:
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
        offload = self.config.generation.enable_cpu_offload
        quant = self.quantization
        dtype = torch.float16 if quant in [QuantizationMode.FP16, QuantizationMode.NF4] else torch.float32

        self.qa_tokenizer = AutoTokenizer.from_pretrained(qa_path)
        self.qa_model = AutoModelForQuestionAnswering.from_pretrained(qa_path).to(self.device)
        self.qa_pipeline = pipeline("question-answering", model=self.qa_model, tokenizer=self.qa_tokenizer, device=self.device)

        bnb_config = None
        if quant == QuantizationMode.NF4:
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=dtype,
                llm_int8_enable_fp32_cpu_offload=offload
            )
        elif quant == QuantizationMode.INT8:
            bnb_config = BitsAndBytesConfig(
                load_in_8bit=True,
                llm_int8_enable_fp32_cpu_offload=offload
            )

        self.text_tokenizer = AutoTokenizer.from_pretrained(
            text_path,
            trust_remote_code=True
        )

        model_kwargs = {
            "trust_remote_code": True,
            "torch_dtype": dtype,
            "device_map": "auto"
        }

        if bnb_config:
            model_kwargs["quantization_config"] = bnb_config

        self.text_model = AutoModelForCausalLM.from_pretrained(
            text_path,
            **model_kwargs
        )

    def _configure_generation(self):
        mode = self.config.generation_mode
        self.generation_mode = mode
        gen_cfg = self.config.generation

        self.generation_config = {
            'max_new_tokens': gen_cfg.max_new_tokens,
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

    def _adjust_max_new_tokens(self, prompt):
        prompt_tokens = len(self.text_tokenizer.encode(prompt, add_special_tokens=False))
        new_max_new_tokens = int(2.5 * prompt_tokens)
        self.generation_config['max_new_tokens'] = new_max_new_tokens

    def generate_response(self, prompt):
        try:
            self._adjust_max_new_tokens(prompt)
            
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
            logger.error("Ошибка генерации: %s", e, exc_info=True)
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
