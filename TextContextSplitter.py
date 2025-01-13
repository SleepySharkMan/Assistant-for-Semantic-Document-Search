import re


class TextContextSplitter:
    def split_by_words(self, content, words_per_context, overlap_words=None):
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

    def split_by_sentences(self, content, sentences_per_context=1, overlap_sentences=None):
        """
        Разделение текста на контексты по предложениям с возможностью перекрытия

        :param content: Текстовое содержимое
        :param sentences_per_context: Количество предложений в основном контексте
        :param overlap_sentences: Количество перекрывающихся предложений
        :return: Список контекстов
        """
        # Разделяем текст на предложения
        sentences = re.split(r'(?<=[.!?])\s+', content)
        sentences = [sentence.strip()
                     for sentence in sentences if sentence.strip()]

        # Если перекрытие не указано, устанавливаем его как 1 предложение
        if overlap_sentences is None:
            overlap_sentences = 1

        contexts = []

        # Создаем контексты с перекрытием
        for i in range(0, len(sentences), sentences_per_context):
            # Определяем границы контекста с перекрытием
            start = max(0, i - overlap_sentences)
            end = min(len(sentences), i +
                      sentences_per_context + overlap_sentences)

            context = ' '.join(sentences[start:end])
            contexts.append(context)

        return contexts

    def split_by_paragraphs(self, content, paragraphs_per_context=1, overlap_lines=0):
        """
        Разделение текста на контексты по абзацам с возможностью перекрытия строк.

        :param content: Текстовое содержимое
        :param paragraphs_per_context: Количество абзацев в одном контексте
        :param overlap_lines: Количество строк перекрытия между контекстами
        :return: Список контекстов
        """
        # Разделяем текст на абзацы (учитываем строки перед первым двойным переносом)
        raw_paragraphs = [p.strip() for p in re.split(
            r'\n\s*\n', content.strip()) if p.strip()]
        contexts = []

        for i in range(0, len(raw_paragraphs), paragraphs_per_context):
            # Текущие абзацы для контекста
            current_paragraphs = raw_paragraphs[i:i + paragraphs_per_context]

            # Добавляем строки перекрытия
            if i > 0 and overlap_lines > 0:
                previous_paragraph = raw_paragraphs[i - 1]
                overlap = '\n'.join(
                    previous_paragraph.split('\n')[-overlap_lines:])
                current_paragraphs.insert(0, overlap)

            # Формируем контекст
            contexts.append('\n\n'.join(current_paragraphs))

        return contexts
