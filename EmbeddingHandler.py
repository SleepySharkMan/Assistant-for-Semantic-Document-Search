import torch
from sentence_transformers import SentenceTransformer, util


class EmbeddingHandler:
    def __init__(self, embedding_model_path):
        """
        Инициализация модели для генерации эмбеддингов.

        :param embedding_model_path: Модель для создания эмбеддингов.
        """
        self.device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu")
        self.embedding_model = SentenceTransformer(
            embedding_model_path).to(self.device)

    def get_text_embedding(self, text):
        """
        Генерирует эмбеддинг для текста.

        :param text: Текст для создания эмбеддинга.
        :return: Векторное представление текста.
        """
        return self.embedding_model.encode(text, convert_to_tensor=True)

    def find_most_relevant_contexts(self, question, contexts, top_k=1):
        """
        Находит наиболее релевантные контексты для вопроса.

        :param question: Вопрос, который нужно связать с контекстом.
        :param contexts: Список контекстов для поиска.
        :param top_k: Количество наиболее релевантных контекстов, которые нужно вернуть.
        :return: Список наиболее релевантных контекстов, отсортированных по релевантности.
        """
        # Получаем эмбеддинг вопроса
        question_embedding = self.get_text_embedding(question)
        # Генерируем эмбеддинги для всех контекстов
        context_embeddings = [self.get_text_embedding(ctx) for ctx in contexts]
        # Вычисляем косинусные сходства
        scores = [util.pytorch_cos_sim(
            question_embedding, ctx_emb).item() for ctx_emb in context_embeddings]
        # Сортируем контексты по убыванию сходства
        top_indices = torch.topk(torch.tensor(
            scores), min(top_k, len(contexts))).indices
        # Возвращаем контексты, отсортированные по релевантности
        return [contexts[idx] for idx in top_indices]
