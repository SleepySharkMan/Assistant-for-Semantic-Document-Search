from dataclasses import dataclass
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
class ModelConfig:
    qa: str
    text: str
    embedding: str
    vosk: str


@dataclass
class TextSplitterConfig:
    words_per_context: int
    overlap_words: int
    sentences_per_context: int
    overlap_sentences: int
    paragraphs_per_context: int
    overlap_lines: int


@dataclass
class EmbeddingStorageConfig:
    db_path: str
    collection_name: str
    embedding_dim: int
    similarity_threshold: float


@dataclass
class FileMetadataDBConfig:
    db_path: str


@dataclass
class SpeechConfig:
    language: str
    mode: str


@dataclass
class ImageCaptioningConfig:
    device: str
    model_name: str


@dataclass
class DocumentManagerConfig:
    image_enabled: bool


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
    no_repeat_ngram_size: int
    repetition_penalty: float
    early_stopping: bool
    deterministic: DeterministicConfig
    stochastic: StochasticConfig
    enable_cpu_offload: bool


@dataclass
class DialogHistoryConfig:
    db_path: str


@dataclass
class DefaultMessages:
    empty_storage: str
    no_contexts_found: str


@dataclass
class LoggingConfig:
    level: str            
    file: str             
    format: str           
    max_bytes: int        
    backup_count: int     
    console_level: str    


@dataclass
class AppConfig:
    device: str
    documents_folder: str
    quantization: QuantizationMode
    generation_mode: GenerationMode
    allowed_file_extensions: List[str]
    models: ModelConfig
    splitter: TextSplitterConfig
    embedding_storage: EmbeddingStorageConfig
    metadata_storage: FileMetadataDBConfig
    speech: SpeechConfig
    image_captioning: ImageCaptioningConfig
    document_processing: DocumentManagerConfig
    generation: GenerationConfig
    dialog_prompt: str
    dialog_history: DialogHistoryConfig
    messages: DefaultMessages
    logging: LoggingConfig
