import re

from config_models import TextSplitterConfig


class TextContextSplitter:
    def __init__(self, config: TextSplitterConfig):
        self.config = config

    def update_config(self, new_config: TextSplitterConfig):
        self.config = new_config

    def split_by_words(self, content):
        words_per_context = self.config.words_per_context
        overlap_words = self.config.overlap_words

        words = content.split()
        contexts = []
        step = words_per_context - overlap_words

        for i in range(0, len(words), step):
            start = max(0, i - overlap_words)
            end = min(len(words), i + words_per_context + overlap_words)
            context = ' '.join(words[start:end])
            contexts.append(context)

        return contexts

    def split_by_sentences(self, content):
        sentences_per_context = self.config.sentences_per_context
        overlap_sentences = self.config.overlap_sentences

        sentences = re.split(r'(?<=[.!?])\s+', content)
        sentences = [s.strip() for s in sentences if s.strip()]

        contexts = []
        for i in range(0, len(sentences), sentences_per_context):
            start = max(0, i - overlap_sentences)
            end = min(len(sentences), i + sentences_per_context + overlap_sentences)
            context = ' '.join(sentences[start:end])
            contexts.append(context)

        return contexts

    def split_by_paragraphs(self, content):
        paragraphs_per_context = self.config.paragraphs_per_context
        overlap_lines = self.config.overlap_lines

        raw_paragraphs = [p.strip() for p in re.split(r'\n\s*\n', content.strip()) if p.strip()]
        contexts = []

        for i in range(0, len(raw_paragraphs), paragraphs_per_context):
            current_paragraphs = raw_paragraphs[i:i + paragraphs_per_context]

            if i > 0 and overlap_lines > 0:
                previous_paragraph = raw_paragraphs[i - 1]
                overlap = '\n'.join(previous_paragraph.split('\n')[-overlap_lines:])
                current_paragraphs.insert(0, overlap)

            contexts.append('\n\n'.join(current_paragraphs))

        return contexts
