import re
from typing import List, Optional

class TextContextSplitter:
    def split_by_words(self, content, words_per_context, overlap_words = None):
        """
        Разделение текста на контексты по определенному количеству слов с возможностью перекрытия

        :param content: Текстовое содержимое
        :param words_per_context: Количество слов в основном контексте
        :param overlap_words: Количество слов для захвата из соседних контекстов
        :return: Список контекстов
        """
        # Если перекрытие не указано, устанавливаем его как 1/3 от основного контекста
        if overlap_words is None:
            overlap_words = words_per_context // 3

        # Разбиваем текст на слова
        words = content.split()
        contexts = []

        # Определяем шаг смещения 
        step = words_per_context - overlap_words

        for i in range(0, len(words), step):
            # Определяем границы контекста с перекрытием
            start = max(0, i - overlap_words)
            end = min(len(words), i + words_per_context + overlap_words)

            context = ' '.join(words[start:end])
            contexts.append(context)

        return contexts

    def split_by_sentences(self, content, sentences_per_context = 1, overlap_sentences = None):
        """
        Разделение текста на контексты по предложениям с возможностью перекрытия

        :param content: Текстовое содержимое
        :param sentences_per_context: Количество предложений в основном контексте
        :param overlap_sentences: Количество перекрывающихся предложений
        :return: Список контекстов
        """
        # Разделяем текст на предложения
        sentences = re.split(r'(?<=[.!?])\s+', content)
        sentences = [sentence.strip() for sentence in sentences if sentence.strip()]

        # Если перекрытие не указано, устанавливаем его как 1 предложение
        if overlap_sentences is None:
            overlap_sentences = 1

        contexts = []
        
        # Создаем контексты с перекрытием
        for i in range(0, len(sentences), sentences_per_context):
            # Определяем границы контекста с перекрытием
            start = max(0, i - overlap_sentences)
            end = min(len(sentences), i + sentences_per_context + overlap_sentences)

            context = ' '.join(sentences[start:end])
            contexts.append(context)

        return contexts

    def split_by_paragraphs(self, content, paragraphs_per_context = 1, overlap_lines = None):
        """
        Разделение текста на контексты по абзацам с частичным перекрытием строк

        :param content: Текстовое содержимое
        :param paragraphs_per_context: Количество абзацев в основном контексте
        :param overlap_lines: Количество перекрывающихся строк в абзацах
        :return: Список контекстов
        """
        # Разделяем текст на абзацы
        paragraphs = re.split(r'\n\s*\n', content)
        paragraphs = [paragraph.strip() for paragraph in paragraphs if paragraph.strip()]

        # Если перекрытие не указано, устанавливаем его как 1/3 строк абзаца
        if overlap_lines is None:
            overlap_lines = 1

        contexts = []
        
        # Создаем контексты с частичным перекрытием
        for i in range(0, len(paragraphs), paragraphs_per_context):
            # Определяем границы контекста с перекрытием
            start = max(0, i - paragraphs_per_context)
            end = min(len(paragraphs), i + paragraphs_per_context + 1)

            # Берем выбранные абзацы
            selected_paragraphs = paragraphs[start:end]

            # Для каждого абзаца, кроме первого, обрезаем начало
            if len(selected_paragraphs) > 1:
                for j in range(1, len(selected_paragraphs)):
                    # Разбиваем абзац на строки
                    lines = selected_paragraphs[j].split('\n')
                    # Оставляем только последние overlap_lines строк
                    selected_paragraphs[j] = '\n'.join(lines[-overlap_lines:])

            # Объединяем абзацы
            context = '\n\n'.join(selected_paragraphs)
            contexts.append(context)

        return contexts
