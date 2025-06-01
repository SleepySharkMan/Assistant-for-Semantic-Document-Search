import re
from config_models import TextSplitterConfig


class TextContextSplitter:
    def __init__(self, config: TextSplitterConfig):
        self.config = config
        self._validate_config()

    def update_config(self, new_config: TextSplitterConfig):
        self.config = new_config
        self._validate_config()

    def _validate_pair(self, bigger: int, overlap: int):
        if bigger < overlap or bigger <= 0 or overlap < 0:
            raise ValueError

    def _validate_config(self):
        c = self.config
        self._validate_pair(c.words_per_context, c.overlap_words)
        self._validate_pair(c.sentences_per_context, c.overlap_sentences)
        if c.paragraphs_per_context <= 0 or c.overlap_lines < 0:
            raise ValueError
        
    def split(self, content: str) -> list[str]:
        if self.config.method == "words":
            return self.split_by_words(content)
        if self.config.method == "sentences":
            return self.split_by_sentences(content)
        if self.config.method == "paragraphs":
            return self.split_by_paragraphs(content)
        raise ValueError(f"Unknown split method: {self.method}")

    def split_by_words(self, content: str) -> list[str]:
        wp, ow = self.config.words_per_context, self.config.overlap_words
        step = wp - ow
        words = content.split()
        contexts = []
        for i in range(0, len(words), step):
            start = max(0, i - ow)
            end = min(len(words), i + wp)
            contexts.append(" ".join(words[start:end]))
        return contexts

    def split_by_sentences(self, content: str) -> list[str]:
        sp, os_ = self.config.sentences_per_context, self.config.overlap_sentences
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", content) if s.strip()]
        contexts = []
        for i in range(0, len(sentences), sp):
            start = max(0, i - os_)
            end = min(len(sentences), i + sp)
            contexts.append(" ".join(sentences[start:end]))
        return contexts

    def split_by_paragraphs(self, content: str) -> list[str]:
        pp, ol = self.config.paragraphs_per_context, self.config.overlap_lines
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", content.strip()) if p.strip()]
        contexts = []
        for i in range(0, len(paragraphs), pp):
            chunk = paragraphs[i:i + pp]
            if i > 0 and ol > 0:
                prev_tail = paragraphs[i - 1].split("\n")[-ol:]
                chunk.insert(0, "\n".join(prev_tail))
            contexts.append("\n\n".join(chunk))
        return contexts
