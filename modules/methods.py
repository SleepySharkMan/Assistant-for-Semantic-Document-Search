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
        print(f"Эмбеддинг '{doc_id}' удалён.")
        deleted_count += 1
        chunk_index += 1

    print(f"Удалено эмбеддингов: {deleted_count} для файла: {file_path}")
    return deleted_count

def delete_file_metadata(metadata_db, document_manager, file_path):
    file_hash = document_manager.get_hash(file_path)
    if not file_hash:
        print(f"Не удалось вычислить хэш для файла: {file_path}")
        return False

    file_entry = metadata_db.get_file_by_hash(file_hash)
    if not file_entry:
        print(f"Метаданные для файла с hash '{file_hash}' не найдены.")
        return False

    file_id = file_entry["id"]
    if metadata_db.delete_file(file_id):
        print(f"Метаданные файла с hash '{file_hash}' успешно удалены.")
        return True
    else:
        print(f"Ошибка при удалении метаданных файла с hash '{file_hash}'.")
        return False


def delete_file_and_associated_data(metadata_db, document_manager, storage, file_path):
    embeddings_deleted = delete_embeddings_by_path(document_manager, storage, file_path)
    metadata_deleted = delete_file_metadata(metadata_db, document_manager, file_path)

    if embeddings_deleted >= 0 and metadata_deleted:
        print(f"Все данные для файла '{file_path}' успешно удалены.")
        return True
    else:
        print(f"Ошибка при удалении данных для файла '{file_path}'.")
        return False