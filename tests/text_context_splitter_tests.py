import pytest
from TextContextSplitter import TextContextSplitter


@pytest.fixture
def splitter():
    """Фикстура для создания экземпляра TextContextSplitter"""
    return TextContextSplitter()


@pytest.fixture
def sample_text():
    """Фикстура с тестовым текстом"""
    return """First sentence. Second sentence! Third sentence?
    
    First paragraph line 1
    First paragraph line 2
    First paragraph line 3
    
    Second paragraph line 1
    Second paragraph line 2
    
    Third paragraph single line."""


@pytest.fixture
def simple_text():
    """Фикстура с простым текстом для тестирования разделения по словам"""
    return "one two three four five six seven eight nine ten"


def test_split_by_words_basic(splitter, simple_text):
    """Тест базового разделения по словам"""
    # Тест с размером контекста 3 слова и перекрытием 1 слово
    contexts = splitter.split_by_words(
        simple_text, words_per_context=3, overlap_words=1)
    assert len(contexts) > 0
    assert contexts[0] == "one two three four"  # 3 слова + 1 перекрытие
    assert "two three four" in contexts[1]  # проверка перекрытия


def test_split_by_words_no_overlap(splitter, simple_text):
    """Тест разделения по словам без перекрытия"""
    contexts = splitter.split_by_words(
        simple_text, words_per_context=3, overlap_words=0)
    assert len(contexts) > 0
    assert contexts[0] == "one two three"
    assert contexts[1] == "four five six"


def test_split_by_words_default_overlap(splitter, simple_text):
    """Тест разделения по словам с дефолтным перекрытием"""
    contexts = splitter.split_by_words(simple_text, words_per_context=3)
    assert len(contexts) > 0
    # Проверяем, что перекрытие равно 1/3 от размера контекста
    first_context_words = contexts[0].split()
    assert len(first_context_words) == 4  # 3 + 1 перекрытие


def test_split_by_words_edge_cases(splitter):
    """Тест граничных случаев при разделении по словам"""
    # Пустой текст
    assert splitter.split_by_words("", words_per_context=3) == []

    # Текст меньше размера контекста
    contexts = splitter.split_by_words("one two", words_per_context=3)
    assert len(contexts) == 1
    assert contexts[0] == "one two"


def test_split_by_sentences_basic(splitter, sample_text):
    """Тест базового разделения по предложениям"""
    contexts = splitter.split_by_sentences(
        sample_text, sentences_per_context=2, overlap_sentences=1)
    assert len(contexts) > 0
    assert "First sentence. Second sentence!" in contexts[0]
    assert "Second sentence! Third sentence?" in contexts[1]


def test_split_by_sentences_no_overlap(splitter, sample_text):
    """Тест разделения по предложениям без перекрытия"""
    contexts = splitter.split_by_sentences(
        sample_text, sentences_per_context=1, overlap_sentences=0)
    assert len(contexts) > 0
    assert contexts[0] == "First sentence."
    assert contexts[1] == "Second sentence!"


def test_split_by_sentences_default_overlap(splitter, sample_text):
    """Тест разделения по предложениям с дефолтным перекрытием"""
    contexts = splitter.split_by_sentences(
        sample_text, sentences_per_context=2)
    assert len(contexts) > 0
    # Проверяем, что есть перекрытие в 1 предложение
    assert "Second sentence!" in contexts[0] and "Second sentence!" in contexts[1]


def test_split_by_sentences_edge_cases(splitter):
    """Тест граничных случаев при разделении по предложениям"""
    # Пустой текст
    assert splitter.split_by_sentences("", sentences_per_context=1) == []

    # Одно предложение
    contexts = splitter.split_by_sentences(
        "Single sentence.", sentences_per_context=2)
    assert len(contexts) == 1
    assert contexts[0] == "Single sentence."


def test_split_by_paragraphs_basic(splitter, sample_text):
    """Тест базового разделения по абзацам"""
    contexts = splitter.split_by_paragraphs(
        sample_text, paragraphs_per_context=1, overlap_lines=1)
    assert len(contexts) > 0
    assert "First paragraph line 1" in contexts[1]


def test_split_by_paragraphs_no_overlap(splitter, sample_text):
    """Тест разделения по абзацам без перекрытия строк"""
    contexts = splitter.split_by_paragraphs(
        sample_text, paragraphs_per_context=1, overlap_lines=0)
    assert len(contexts) > 0
    assert contexts[0].strip(
    ) == "First sentence. Second sentence! Third sentence?"
    assert contexts[1].startswith("First paragraph line 1")


def test_split_by_paragraphs_default_overlap(splitter, sample_text):
    """Тест разделения по абзацам с дефолтным перекрытием"""
    contexts = splitter.split_by_paragraphs(
        sample_text, paragraphs_per_context=1, overlap_lines=1)
    assert len(contexts) > 0

    if len(contexts) > 1:
        lines_first = set(contexts[0].split('\n'))
        lines_second = set(contexts[1].split('\n'))
        overlap = lines_first.intersection(lines_second)
        assert len(overlap) > 0, f"No overlap found. Contexts: {contexts}"


def test_split_by_paragraphs_edge_cases(splitter):
    """Тест граничных случаев при разделении по абзацам"""
    # Пустой текст
    assert splitter.split_by_paragraphs("", paragraphs_per_context=1) == []

    # Один абзац
    single_paragraph = "Line 1\nLine 2\nLine 3"
    contexts = splitter.split_by_paragraphs(
        single_paragraph, paragraphs_per_context=2)
    assert len(contexts) == 1
    assert contexts[0] == single_paragraph


def test_split_by_paragraphs_multiple_newlines(splitter):
    """Тест разделения текста с множественными переносами строк"""
    text = "Paragraph 1\n\n\n\nParagraph 2\n\nParagraph 3"
    contexts = splitter.split_by_paragraphs(text, paragraphs_per_context=1)
    assert len(contexts) == 3
    assert "Paragraph 1" in contexts[0]
    assert "Paragraph 2" in contexts[1]
    assert "Paragraph 3" in contexts[2]
