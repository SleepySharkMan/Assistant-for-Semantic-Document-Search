def delete_embeddings_by_path(document_manager, storage, file_path):
    file_hash = document_manager.get_hash(file_path)
    if not file_hash:
        print(f"Не удалось вычислить хэш для файла: {file_path}")
        return -1

    deleted_count = 0
    chunk_index = 0
    while True:
        doc_id = f"{file_hash}_chunk{chunk_index}"
        embedding = storage.get_embedding(doc_id)
        if embedding is None:
            break
        storage.delete_embedding(doc_id)
        logger.info("Эмбеддинг '%s' удалён.", doc_id)
        deleted_count += 1
        chunk_index += 1

    logger.info("Удалено эмбеддингов: %d для файла: %s", deleted_count, file_path)
    return deleted_count

def delete_file_metadata(metadata_db, document_manager, file_path):
    file_hash = document_manager.get_hash(file_path)
    if not file_hash:
        logger.warning("Не удалось вычислить хэш для файла: %s", file_path)
        return False

    file_entry = metadata_db.get_file_by_hash(file_hash)
    if not file_entry:
        logger.warning("Метаданные для файла с hash '%s' не найдены.", file_hash)
        return False

    file_id = file_entry["id"]
    if metadata_db.delete_file(file_id):
        logger.info("Метаданные файла с hash '%s' успешно удалены.", file_hash)
        return True
    else:
        logger.error("Ошибка при удалении метаданных файла с hash '%s'.", file_hash)
        return False


def delete_file_and_associated_data(metadata_db, document_manager, storage, file_path):
    embeddings_deleted = delete_embeddings_by_path(document_manager, storage, file_path)
    metadata_deleted = delete_file_metadata(metadata_db, document_manager, file_path)

    if embeddings_deleted >= 0 and metadata_deleted:
        logger.info("Все данные для файла '%s' успешно удалены.", file_path)
        return True
    else:
        logger.error("Ошибка при удалении данных для файла '%s'.", file_path)
        return False