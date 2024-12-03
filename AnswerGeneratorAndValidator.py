import torch
from transformers import pipeline, AutoModelForQuestionAnswering, AutoTokenizer, AutoModelForCausalLM

class AnswerGeneratorAndValidator:
    def __init__(self, qa_model_path, model_path):
        """
        Инициализация моделей для вопросов и ответов, генерации текста и проверки контекста.
        
        :param qa_model_path: Путь к модели для вопросов и ответов.
        :param model_path: Путь к модели для генерации текста.
        """
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Модель для вопросов и ответов (QA)
        self.qa_tokenizer = AutoTokenizer.from_pretrained(qa_model_path)
        self.qa_model = AutoModelForQuestionAnswering.from_pretrained(qa_model_path).to(self.device)
        self.qa_pipeline = pipeline("question-answering", model=self.qa_model, tokenizer=self.qa_tokenizer, device=0 if torch.cuda.is_available() else -1)

        # Модель для генерации текста 
        self.text_tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.text_model = AutoModelForCausalLM.from_pretrained(model_path).to(self.device)

        # Расширенная конфигурация генерации с подробными параметрами
        self.generation_config = {
            # Основные параметры контроля генерации
            'max_length': 150,  # Максимальная длина генерируемого текста
            'min_length': 30,   # Минимальная длина генерируемого текста
            'temperature': 0.7, # Креативность и вариативность текста
            'top_p': 0.9,       # Nucleus sampling для диверсификации
            'top_k': 50,        # Фильтрация top-k токенов
            # Параметры разнообразия и уникальности
            'num_return_sequences': 1,  # Количество генерируемых вариантов
            'do_sample': True,   # Использование стохастического семплирования
            'repetition_penalty': 1.2,  # Штраф за повторения
            'no_repeat_ngram_size': 2,  # Предотвращение повторов n-грамм
            # Параметры управления содержанием
            'num_beams': 5,     # Количество лучей при beam search
            'early_stopping': True,  # Остановка генерации при достижении критериев
            'length_penalty': 1.0,  # Штраф/бонус за длину текста
            # Специфические параметры для некоторых моделей
            'bad_words_ids': None,  # Список токенов для исключения
            'forced_bos_token_id': None,  # Форсированный начальный токен
            'forced_eos_token_id': None,  # Форсированный конечный токен
        }


    def configure_model(self, **kwargs):
        """
        Детальная настройка параметров генерации текста с расширенными возможностями.

        Категории параметров:
        1. Параметры длины и структуры текста
        - max_length (int): Максимальная длина текста 
          * Диапазон: 10-1000 
          * Пример: 200 для длинных объяснений, 50 для кратких ответов
        
        - min_length (int): Минимальная длина текста
          * Препятствует генерации слишком коротких ответов
          * Пример: 30-50 слов для содержательного ответа

        2. Параметры креативности и разнообразия
        - temperature (float): Контроль стохастичности 
          * 0.1 - очень консервативный текст
          * 0.5 - сбалансированный режим
          * 0.9 - максимальное разнообразие
          * Пример: 0.3 для научных текстов, 0.8 для творческих

        - top_p (float): Nucleus sampling
          * Вероятностный метод фильтрации токенов
          * 0.5 - строгий отбор
          * 0.9 - широкий выбор
          * Пример: 0.7 для сбалансированного текста

        - top_k (int): Ограничение токенов по вероятности
          * 10 - очень строгий выбор
          * 50 - стандартный режим
          * 100 - максимальное разнообразие
          * Пример: 30 для технических текстов

        3. Параметры уникальности
        - repetition_penalty (float): Штраф за повторения
          * 1.0 - без штрафа
          * 1.2 - умеренное подавление повторов
          * 1.5 - сильное подавление
          * Пример: 1.3 для предотвращения зацикливания

        - no_repeat_ngram_size (int): Блокировка повторяющихся n-грамм
          * 2 - запрет повторов биграмм
          * 3 - запрет повторов триграмм
          * Пример: 2 для предотвращения дублирования фраз

        4. Параметры генерационной стратегии
        - num_beams (int): Количество лучей при beam search
          * 3 - быстрый поиск
          * 5 - сбалансированный
          * 10 - глубокий поиск вариантов
          * Пример: 4 для баланса качества и скорости

        - num_return_sequences (int): Количество генерируемых вариантов
          * 1 - один вариант ответа
          * 3 - множественные варианты
          * Пример: 2 для сравнения интерпретаций

        Примеры использования:
        Строгий научный режим
        generator.configure_model(
            temperature=0.3, 
            top_p=0.6, 
            max_length=100,
            repetition_penalty=1.3
        )

        Креативный режим
        generator.configure_model(
            temperature=0.8, 
            top_p=0.9, 
            max_length=200,
            num_return_sequences=3
        )

        :param kwargs: Словарь параметров для настройки
        :return: self для цепочки вызовов
        """
        for key, value in kwargs.items():
            if key in self.generation_config:
                # Добавляем дополнительные проверки для некоторых параметров
                if key == 'temperature' and (value < 0 or value > 1):
                    raise ValueError("Temperature должен быть в диапазоне 0-1")
                if key == 'max_length' and (value < 10 or value > 1000):
                    raise ValueError("max_length должен быть в диапазоне 10-1000")
                
                self.generation_config[key] = value
            else:
                raise ValueError(f"Неизвестный параметр: {key}")
        return self


    def generate_answer(self, context, question):
        """
        Генерирует ответ на основе вопроса и контекста без дополнительной генерации текста.
        
        :param context: Контекст для поиска ответа.
        :param question: Вопрос, на который нужно ответить.
        :return: Извлечённый ответ.
        """
        # Получение ответа на основе QA-модели
        qa_result = self.qa_pipeline(question=question, context=context)
        extracted_answer = qa_result['answer']

        # Проверка валидности извлечённого ответа
        if not extracted_answer or extracted_answer.lower() not in context.lower():
            return "Ответ не удалось извлечь из контекста."

        return extracted_answer


    def validate_answer(self, context, answer):
        return None