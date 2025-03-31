import torch
import numpy as np

from sentence_transformers import SentenceTransformer
from typing import List, Union

from config_models import AppConfig


class EmbeddingHandler:
    def __init__(self, config: AppConfig):
        self.config = config
        self.model_path = config.models.embedding
        self.device = self._get_device(config.device)
        self.model = self._load_model()

    def update_config(self, new_config: AppConfig):
        self.config = new_config
        self.model_path = new_config.models.embedding
        self.device = self._get_device(new_config.device)
        self.model = self._load_model()

    def _get_device(self, device: Union[str, None]) -> torch.device:
        if device:
            return torch.device(device)
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def _load_model(self) -> SentenceTransformer:
        model = SentenceTransformer(self.model_path)
        model.to(self.device)
        print(f"Модель загружена на устройство: {self.device}")
        return model

    def get_text_embedding(self, text: str, normalize: bool = True) -> np.ndarray:
        with torch.no_grad():
            embedding = self.model.encode(
                text,
                convert_to_tensor=True,
                device=self.device,
                normalize_embeddings=normalize
            )
            return embedding.cpu().numpy()

    def get_batch_embeddings(self, texts: List[str], batch_size: int = 32) -> List[np.ndarray]:
        with torch.no_grad():
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                convert_to_tensor=True,
                device=self.device,
                normalize_embeddings=True
            )
            return [emb.cpu().numpy() for emb in embeddings]
