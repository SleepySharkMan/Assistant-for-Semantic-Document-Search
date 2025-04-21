import re
import logging
from io import BytesIO
from typing import Optional

from modules.embedding_handler import EmbeddingHandler
from modules.embedding_storage import EmbeddingStorage
from modules.answer_generator import AnswerGeneratorAndValidator
from modules.speech_processor import SpeechProcessor
from modules.dialog_history import DialogHistory


def clean_cut(text: str) -> str:
    text = text.strip()
    if text.endswith(('.', '!', '?')):
        return text
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return ' '.join(sentences[:-1]) if len(sentences) > 1 else text

logger = logging.getLogger(__name__)

class DialogManager:
    """
    Обрабатывает текстовые и голосовые запросы пользователя.
    Использует внешние компоненты: эмбеддер, хранилище, генератор, речь, историю.
    """

    def __init__(
        self,
        embedder: EmbeddingHandler,
        storage: EmbeddingStorage,
        generator: AnswerGeneratorAndValidator,
        speech: SpeechProcessor,
        history: DialogHistory,
        prompt_template: str
    ):
        self.embedder = embedder
        self.storage = storage
        self.generator = generator
        self.speech = speech
        self.history = history
        self.prompt_template = prompt_template
        self.messages = generator.config.messages
        logger.info("DialogManager инициализирован")

    def reload(
        self,
        embedder: Optional[EmbeddingHandler] = None,
        storage: Optional[EmbeddingStorage] = None,
        generator: Optional[AnswerGeneratorAndValidator] = None,
        speech: Optional[SpeechProcessor] = None
    ):
        if embedder:
            self.embedder = embedder
        if storage:
            self.storage = storage
        if generator:
            self.generator = generator
            self.messages = generator.config.messages
        if speech:
            self.speech = speech

    def answer_text(self, user_id: str, question: str, top_k: int = 3) -> str:
        logger.info("answer_text: user=%s, вопрос=%s", user_id, question)
        stats = self.storage.get_collection_stats()
        if stats["count"] == 0:
            return self.messages.empty_storage

        query_embedding = self.embedder.get_text_embedding(question)
        results = self.storage.search_similar(query_embedding, top_k=top_k)
        logger.debug("Найдено %d результатов", len(results))

        contexts = []
        for doc_id, _ in results:
            embedding, metadata = self.storage.get_embedding_with_metadata(doc_id)
            if metadata and "content" in metadata:
                contexts.append(metadata["content"])

        if not contexts:
            return self.messages.no_contexts_found

        prompt = self.prompt_template.format(
            context="\n".join(contexts),
            question=question.strip()
        )

        answer = self.generator.generate_response(prompt)
        answer = clean_cut(answer)

        self.history.save(user_id=user_id, user_text=question, assistant_text=answer)
        logger.debug("Ответ сохранён для %s", user_id)
        return answer

    def answer_speech(self, audio_stream: BytesIO) -> Optional[str]:
        try:
            return self.speech.speech_to_text(audio_stream)
        except Exception:
            return None

    def synthesize_speech(self, text: str) -> BytesIO:
        try:
            return self.speech.text_to_speech(text).export(format="wav")
        except Exception:
            return BytesIO()
