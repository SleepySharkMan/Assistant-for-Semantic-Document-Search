import torch
from sentence_transformers import SentenceTransformer, util

class EmbeddingHandler:
    def __init__(self, embedding_model_path):
        """
        Инициализация модели для генерации эмбеддингов.
        
        :param embedding_model_path: Модель для создания эмбеддингов.
        """
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.embedding_model = SentenceTransformer(embedding_model_path).to(self.device)


    def get_text_embedding(self, text):
        """
        Генерирует эмбеддинг для текста.
        
        :param text: Текст для создания эмбеддинга.
        :return: Векторное представление текста.
        """
        return self.embedding_model.encode(text, convert_to_tensor=True)


    def find_most_relevant_context(self, question, contexts):
        """
        Находит наиболее релевантный контекст для вопроса.
        
        :param question: Вопрос, который нужно связать с контекстом.
        :param contexts: Список контекстов для поиска.
        :return: Наиболее релевантный контекст.
        """
        question_embedding = self.get_text_embedding(question)
        context_embeddings = [self.get_text_embedding(ctx) for ctx in contexts]
        scores = [util.pytorch_cos_sim(question_embedding, ctx_emb) for ctx_emb in context_embeddings]
        best_idx = torch.argmax(torch.tensor(scores))
        return contexts[best_idx]
