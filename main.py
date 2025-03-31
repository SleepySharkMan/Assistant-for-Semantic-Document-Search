import time
from pathlib import Path

from config_loader import ConfigLoader
from modules.document_manager import DocumentManager
from modules.file_metadata_db import FileMetadataDB
from modules.embedding_handler import EmbeddingHandler
from modules.embedding_storage import EmbeddingStorage
from modules.answer_generator import AnswerGeneratorAndValidator
from modules.text_splitter import TextContextSplitter


class MainProcessor:
    """
    Основной класс для обработки документов и генерации ответов.
    Проверяет работу всех компонентов на одном запуске.
    """

    def __init__(self, config_path="config.yaml"):
        self.config_loader = ConfigLoader(config_path)
        config = self.config_loader.full

        self.doc_manager = DocumentManager(config)
        self.metadata_db = FileMetadataDB(config.file_metadata_db)
        self.embedding_handler = EmbeddingHandler(config)
        self.embedding_storage = EmbeddingStorage(config.embedding_storage)
        self.answer_generator = AnswerGeneratorAndValidator(config)
        self.splitter = TextContextSplitter(config.text_splitter)

        Path(config.embedding_storage.db_path).mkdir(parents=True, exist_ok=True)

    def process_files_to_embeddings(self) -> None:
        print("\n=== Обработка файлов ===")
        total_start = time.time()
        processed_contexts = 0

        documents_dir = "documents"
        Path(documents_dir).mkdir(parents=True, exist_ok=True)
        
        self.doc_manager.add_files_from_folder(documents_dir)
        files = self.doc_manager.get_files()
        print(f"Найдено файлов: {len(files)}")

        for file_path in files:
            print(f"\nОбработка файла: {file_path}")
            try:
                content = self.doc_manager.get_text(file_path)
                if not content or len(content.strip()) < 30:
                    print("Пропуск: слишком короткий текст")
                    continue

                context_hash = self.doc_manager.get_hash(file_path)
                if self.metadata_db.get_file_by_hash(context_hash):
                    print("Контекст уже в базе, пропуск")
                    continue

                file_id = self.metadata_db.add_file(
                    path=str(file_path),
                    file_type="text_context",
                    size=len(content),
                    file_hash=context_hash
                )
                if not file_id:
                    continue

                contexts = self.splitter.split_by_paragraphs(content)

                for i, context in enumerate(contexts):
                    chunk_id = f"{context_hash}_chunk{i}"
                    embedding = self.embedding_handler.get_text_embedding(context)
                    self.embedding_storage.add_embedding(
                        doc_id=chunk_id,
                        embedding=embedding,
                        metadata={
                            "source": str(file_path),
                            "content": context[:300] + "..."
                        }
                    )
                    processed_contexts += 1
                    print(f"Добавлен контекст #{i + 1}")

            except Exception as e:
                print(f"Ошибка: {e}")

        print("\n=== Завершено ===")
        print(f"Обработано: {processed_contexts} контекстов")
        print(f"Время: {time.time() - total_start:.2f} сек")

    def answer_question(self, question: str) -> None:
        print(f"\nВопрос: {question}")
        try:
            stats = self.embedding_storage.get_collection_stats()
            if stats['count'] == 0:
                print("Хранилище эмбеддингов пусто")
                return

            question_embedding = self.embedding_handler.get_text_embedding(question)
            results = self.embedding_storage.search_similar(
                query_embedding=question_embedding,
                top_k=min(3, stats['count']),
                filters={"source": {"$ne": ""}}
            )

            SIMILARITY_THRESHOLD = 0.3
            matches = []
            for doc_id, score in results:
                if score < SIMILARITY_THRESHOLD:
                    continue
                result = self.embedding_storage.get_embedding_with_metadata(doc_id)
                if result is None:
                    continue

                embedding, metadata = result
                if metadata and "content" in metadata:
                    matches.append((metadata["content"], score))

            if not matches:
                print("К сожаленияю, я не знаю ответа на ваш вопрос")
                return

            print("\nСовпадения:")
            for i, (ctx, score) in enumerate(matches, 1):
                print(f"{i}. ({score:.2f}) {ctx[:200]}...")

            prompt = f"Контекст:\n{matches}\n\nВопрос: {question.strip()}\nОтвет:"
            answer = self.answer_generator.generate_response(prompt)
            print(f"\nОтвет: {answer}")

        except Exception as e:
            print(f"Ошибка при ответе: {e}")


if __name__ == "__main__":
    processor = MainProcessor()
    processor.process_files_to_embeddings()

    questions = [
        "Какие бывают виды мармелада?",
        "Как устроен вулкан?",
        "Чем полезно мороженое?"
    ]

    for q in questions:
        processor.answer_question(q)

    print("\nТест завершён")