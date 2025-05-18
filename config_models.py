from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class GenerationMode(Enum):
    DETERMINISTIC = "deterministic"
    STOCHASTIC = "stochastic"


class QuantizationMode(Enum):
    FP32 = "fp32"
    FP16 = "fp16"
    INT8 = "int8"
    NF4 = "nf4"


@dataclass
class DeterministicConfig:
    num_beams: int 
    length_penalty: float 
    no_repeat_ngram_size: int 


@dataclass
class StochasticConfig:
    temperature: float 
    top_p: float 
    top_k: int 
    typical_p: float 
    num_beams: int 


@dataclass
class GenerationConfig:
    max_new_tokens: int 
    num_return_sequences: int 
    no_repeat_ngram_size: int = 3
    repetition_penalty: float = 1.1
    early_stopping: bool = False
    enable_cpu_offload: bool = True
    deterministic: DeterministicConfig = field(default_factory=DeterministicConfig)
    stochastic:   StochasticConfig     = field(default_factory=StochasticConfig)


@dataclass
class EmbeddingHandlerConfig:
    device: str
    model_path: str


@dataclass
class AnswerGeneratorConfig:
    device: str
    quantization: QuantizationMode
    generation_mode: GenerationMode
    text_model_path: str
    qa_model_path: str
    generation: GenerationConfig


@dataclass
class TextSplitterConfig:
    words_per_context: int
    overlap_words: int
    sentences_per_context: int
    overlap_sentences: int
    paragraphs_per_context: int
    overlap_lines: int


@dataclass
class DocumentProcessingConfig:
    image_enabled: bool
    allowed_extensions: List[str]


@dataclass
class ImageCaptioningConfig:
    device: str
    model_name: str


@dataclass
class DocumentManagerConfig:
    processing: DocumentProcessingConfig
    captioning: ImageCaptioningConfig


@dataclass
class EmbeddingStorageConfig:
    db_path: str
    collection_name: str
    embedding_dim: int
    similarity_threshold: float

@dataclass
class SpeechConfig:
    language: str
    model: str

@dataclass
class LoggingConfig:
    level: str
    file: str
    format: str
    max_bytes: int
    backup_count: int
    console_level: str


@dataclass
class DefaultMessages:
    empty_storage: str
    no_contexts_found: str


@dataclass
class TextDisplayConfig:
    show_text_source_info: bool
    show_text_fragments: bool

@dataclass
class DialogManagerConfig:
    prompt_template: str
    show_text_source_info: bool
    show_text_fragments: bool
    messages: DefaultMessages

@dataclass
class DatabaseConfig:
    url: str

@dataclass
class AppConfig:
    documents_folder: str
    embedding_handler: EmbeddingHandlerConfig
    answer_generator: AnswerGeneratorConfig
    splitter: TextSplitterConfig
    document_manager: DocumentManagerConfig
    embedding_storage: EmbeddingStorageConfig
    speech: SpeechConfig
    dialog_manager: DialogManagerConfig
    logging: LoggingConfig
    database: DatabaseConfig
