import chromadb
import numpy as np
import logging

from chromadb.config import Settings
from chromadb.errors import InvalidCollectionException
from pathlib import Path
from typing import List, Tuple, Optional, Dict

from config_models import EmbeddingStorageConfig

logger = logging.getLogger(__name__)

class EmbeddingStorage:
    def __init__(self, config: EmbeddingStorageConfig):
        self.config = config
        self.db_path = Path(config.db_path)
        self.collection_name = config.collection_name
        self.embedding_dim = config.embedding_dim
        self.similarity_threshold = config.similarity_threshold

        self.db_path.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=str(self.db_path),
            settings=Settings(allow_reset=True)
        )
        self._init_collection()
        logger.info("EmbeddingStorage готов: %s/%s", self.db_path, self.collection_name)

    def update_config(self, new_config: EmbeddingStorageConfig):
        self.config = new_config
        self.__init__(new_config)

    def _init_collection(self) -> None:
        try:
            self.collection = self.client.get_collection(self.collection_name)
        except InvalidCollectionException:
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={
                    "hnsw:space": "cosine",
                    "embedding_dim": str(self.embedding_dim)
                }
            )
            logger.info("Коллекция '%s' создана", self.collection_name)

    def add_embedding(self, doc_id: str, embedding: np.ndarray, metadata: dict = None) -> None:
        if not isinstance(doc_id, str):
            raise TypeError("doc_id должен быть строкой")

        if embedding.shape != (self.embedding_dim,):
            raise ValueError(f"Неверная размерность вектора: {embedding.shape}. Ожидается: ({self.embedding_dim},)")

        metadata = metadata or {}
        metadata.setdefault("source", "unknown")

        self.collection.upsert(
            ids=[doc_id],
            embeddings=[embedding.tolist()],
            metadatas=[metadata]
        )

    def search_similar(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
        filters: Optional[Dict] = None
    ) -> List[Tuple[str, float]]:
        query = query_embedding.tolist()

        results = self.collection.query(
            query_embeddings=[query],
            n_results=min(top_k, self.collection.count()),
            where=filters,
            include=["distances"]
        )

        threshold = self.similarity_threshold
        return [
            (doc_id, 1 - distance)
            for doc_id, distance in zip(results["ids"][0], results["distances"][0])
            if (1 - distance) >= threshold
        ]

    def get_embedding(self, doc_id: str) -> Optional[np.ndarray]:
        result = self.collection.get(
            ids=[doc_id],
            include=["embeddings"]
        )
        return np.array(result["embeddings"][0]) if result["embeddings"] else None

    def delete_embedding(self, doc_id: str) -> None:
        self.collection.delete(ids=[doc_id])

    def reset_storage(self) -> None:
        self.client.reset()
        self._init_collection()

    def get_collection_stats(self) -> Dict:
        return {
            "count": self.collection.count(),
            "dimension": self.embedding_dim,
            "space": "cosine"
        }

    def get_embedding_with_metadata(self, doc_id: str) -> Optional[Tuple[np.ndarray, Dict]]:
        result = self.collection.get(
            ids=[doc_id],
            include=["embeddings", "metadatas"]
        )
        embeddings = result.get("embeddings", [])
        metadatas = result.get("metadatas", [])

        if len(embeddings) > 0 and len(metadatas) > 0:
            return np.array(embeddings[0]), metadatas[0]
        return None, None
