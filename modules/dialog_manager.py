from __future__ import annotations

import logging
import time
import uuid
from io import BytesIO
from typing import List, Optional, Tuple

from modules.embedding_handler import EmbeddingHandler
from modules.embedding_storage import EmbeddingStorage
from modules.answer_generator import AnswerGenerator
from modules.speech_processor import SpeechProcessor
from modules.dialog_history import DialogHistory
from config_models import DialogManagerConfig

logger = logging.getLogger(__name__)

class DialogManager:
    def __init__(
        self,
        embedder: EmbeddingHandler,
        storage: EmbeddingStorage,
        generator: AnswerGenerator,
        speech: SpeechProcessor,
        history: DialogHistory,
        config: DialogManagerConfig
    ) -> None:
        self.embedder  = embedder
        self.storage   = storage
        self.generator = generator
        self.speech    = speech
        self.history   = history

        self.config                 = config
        self.prompt_template        = config.prompt_template
        self.show_text_source_info  = config.show_text_source_info
        self.show_text_fragments    = config.show_text_fragments

        self._msg_empty  = config.messages.empty_storage
        self._msg_no_ctx = config.messages.no_contexts_found

    def answer_text(
        self,
        user_id: str,
        question: str,
        *,
        top_k: int = 5,
        request_source_info: Optional[bool] = None,
        request_fragments: Optional[bool] = None
        ) -> dict:
        """
        Обрабатывает запрос на получение ответа с учетом флагов для фрагментов текста и источников.
        
        :param user_id: Идентификатор пользователя.
        :param question: Вопрос пользователя.
        :param top_k: Количество наиболее похожих документов для обработки.
        :param request_source_info: Флаг запроса источников (переопределяет конфиг).
        :param request_fragments: Флаг запроса фрагментов текста (переопределяет конфиг).
        :return: Ответ в формате словарь.
        """

        req_id = uuid.uuid4().hex[:8]
        start = time.perf_counter()

        if self.storage.get_collection_stats()["count"] == 0:
            logger.info("[%s] storage empty", req_id)
            return {"answer": self._msg_empty}

        q_emb = self.embedder.get_text_embedding(question)
        hits: List[Tuple[str, float]] = self.storage.search_similar(q_emb, top_k=top_k)
        if not hits:
            return {"answer": self._msg_no_ctx}

        contexts: List[str] = []
        sources: List[str] = []
        for doc_id, _ in hits:
            _, meta = self.storage.get_embedding_with_metadata(doc_id)
            if meta and meta.get("content"):
                contexts.append(meta["content"])
            if meta and meta.get("source"):
                sources.append(meta["source"])

        if not contexts:
            return {"answer": self._msg_no_ctx}

        prompt = self.prompt_template.format(context="\n\n".join(contexts), question=question.strip())
        answer = self._trim(self.generator.generate_response(prompt))

        response = {"answer": answer}

        if self.show_text_fragments and (request_fragments is not False):
            response["fragments"] = contexts

        if self.show_text_source_info and (request_source_info is not False):
            response["sources"] = sources

        self.history.save(user_id=user_id, user_text=question, assistant_text=answer)
        logger.info("[%s] answered in %.2f s", req_id, time.perf_counter() - start)

        return response

    def answer_speech(self, audio: BytesIO) -> Optional[str]:
        try:
            return self.speech.speech_to_text(audio)
        except Exception as exc:  # noqa: BLE001
            logger.exception("STT error: %s", exc)
            return None

    def synthesize_speech(self, text: str) -> BytesIO:
        try:
            audio_seg = self.speech.text_to_speech(text)
            out = BytesIO()
            audio_seg.export(out, format="wav")  # type: ignore[arg-type]
            out.seek(0)
            return out
        except Exception as exc:  # noqa: BLE001
            logger.exception("TTS error: %s", exc)
            return BytesIO()

    def reload(
        self,
        *,
        embedder: EmbeddingHandler = None,
        storage: EmbeddingStorage = None,
        generator: AnswerGenerator = None,
        speech: SpeechProcessor = None,
        config: DialogManagerConfig = None
    ) -> None:
        if embedder:
            self.embedder = embedder
        if storage:
            self.storage = storage
        if generator:
            self.generator = generator
        if speech:
            self.speech = speech
        if config:
            self.config                 = config
            self.prompt_template        = config.prompt_template
            self.show_text_source_info  = config.show_text_source_info
            self.show_text_fragments    = config.show_text_fragments
            self._msg_empty  = config.messages.empty_storage
            self._msg_no_ctx = config.messages.no_contexts_found

    @staticmethod
    def _trim(text: str) -> str:
        text = text.strip()
        if text.endswith((".", "!", "?")):
            return text
        last = max(text.rfind("."), text.rfind("!"), text.rfind("?"))
        return text if last == -1 else text[: last + 1]
