from modules.db import DBManager
from modules.file_metadata_db import FileMetadataDB
from modules.embedding_storage import EmbeddingStorage
from omegaconf import OmegaConf

cfg = OmegaConf.load("config.yaml")
db_manager = DBManager(cfg.database)
file_metadata_db = FileMetadataDB(db_manager.session_scope)
storage = EmbeddingStorage(cfg.embedding_storage)

# Проверка метаданных файла
files = file_metadata_db.get_all_files()
for f in files:
    print(f)

# Проверка хранилища эмбеддингов
stats = storage.get_collection_stats()
print(f"Количество документов: {stats['count']}")
results = storage.collection.get(include=["metadatas"])
for doc_id, meta in zip(results["ids"], results["metadatas"]):
    print(f"ID: {doc_id}, Source: {meta.get('source')}, Content: {meta.get('content')[:100]}...")