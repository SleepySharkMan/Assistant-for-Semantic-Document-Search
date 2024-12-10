import torch
from transformers import AutoTokenizer, AutoModelForQuestionAnswering, AutoModelForCausalLM, pipeline, BitsAndBytesConfig


class AnswerGeneratorAndValidator:
    def __init__(self, qa_model_path, model_path):
        """
        Инициализация моделей для вопросов и ответов, генерации текста и проверки контекста.
        
        :param qa_model_path: Путь к модели для вопросов и ответов.
        :param model_path: Путь к модели для генерации текста.
        """
        # Устройство: GPU (если доступно) или CPU
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Модель для вопросов и ответов (QA)
        self.qa_tokenizer = AutoTokenizer.from_pretrained(qa_model_path)
        self.qa_model = AutoModelForQuestionAnswering.from_pretrained(qa_model_path).to(self.device)
        self.qa_pipeline = pipeline(
            "question-answering",
            model=self.qa_model,
            tokenizer=self.qa_tokenizer,
            device=0 if torch.cuda.is_available() else -1
        )

        # Модель для генерации текста (4-битная версия)
        # Настройка BitsAndBytes для 4-битного квантования
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,                # Загружаем модель в 4-битном формате
            bnb_4bit_use_double_quant=True,  # Активируем двойное квантование
            bnb_4bit_quant_type="nf4",       # Используем NF4-квантование
            bnb_4bit_compute_dtype=torch.float16  # Вычисления в FP16 для экономии памяти
        )

        # Загрузка токенизатора и модели генерации текста
        self.text_tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.text_model = AutoModelForCausalLM.from_pretrained(
            model_path,
            quantization_config=bnb_config,
            device_map="auto"  # Автоматическое распределение частей модели по устройствам
        ).to(self.device)

        # Расширенная конфигурация генерации текста
        self.generation_config = {
            'max_length': 400,           
            'min_length': 30,            
            'do_sample': True,           
            'temperature': 0.3,          
            'top_p': 0.7,                
            'top_k': 20,                 
            'num_return_sequences': 1,   
            'repetition_penalty': 1.2,   
            'no_repeat_ngram_size': 2,   
            'num_beams': 3,              
            'early_stopping': True,      
            'length_penalty': 0.8,       
        }

    def configure_model(self, **kwargs):
        """
        Настройка параметров генерации текста.
        """
        for key, value in kwargs.items():
            if key in self.generation_config:
                if key == 'temperature' and (value < 0 or value > 1):
                    raise ValueError("Temperature должен быть в диапазоне 0-1")
                if key == 'max_length' and (value < 10 or value > 1000):
                    raise ValueError("max_length должен быть в диапазоне 10-1000")
                self.generation_config[key] = value
            else:
                raise ValueError(f"Неизвестный параметр: {key}")
        return self


    def find_answer(self, contexts, question):
        """
        Извлекает ответ на основе вопроса из списка контекстов.
        
        :param contexts: Список контекстов для поиска ответа.
        :param question: Вопрос, на который нужно ответить.
        :return: Извлечённый ответ или сообщение о неудаче.
        """
        best_answer = None
        best_confidence = 0

        for context in contexts:
            qa_result = self.qa_pipeline(question=question, context=context)
            extracted_answer = qa_result['answer']
            confidence = qa_result.get('score', 0)  # Получаем confidence score, если доступно

            # Проверяем, что ответ не пустой и содержится в контексте
            if extracted_answer and extracted_answer.lower() in context.lower():
                # Выбираем ответ с наивысшей confidence
                if confidence > best_confidence:
                    best_answer = extracted_answer
                    best_confidence = confidence

        # Если ответ не найден ни в одном контексте
        if not best_answer:
            return "Ответ не удалось извлечь из предоставленных контекстов."

        return best_answer


    def generate_human_readable_text(self, question, answer, context=None):
        """
        Создаёт человекочитаемый текст на основе вопроса, ответа и, при наличии, контекста.
        
        :param question: Вопрос, на который был дан ответ.
        :param answer: Ответ на вопрос.
        :param context: Контекст, из которого был получен ответ (необязательный параметр).
        :return: Сформированный человекочитаемый текст.
        """
        try:
            if context:
                input_text = (
                    f"Вопрос: {question}\n"  
                    f"Контекст: {context}\n"  
                    f"Ответ: {answer}\n"  
                    "Внимательно используя ТОЛЬКО информацию из контекста, создай связный и информативный \
                    текст о происхождении мармелада. Опирайся строго на предоставленные факты!"  
                )
            else:
                input_text = (
                    f"Вопрос: {question}\n" 
                    f"Ответ: {answer}\n"
                    "Сформулируй читабельный текст:"  
                )
            
            # Токенизация входного текста для модели с ограничением на длину
            inputs = self.text_tokenizer(
                input_text,  # Исходный текст, который нужно токенизировать
                return_tensors="pt",  # Возвращаем данные в формате, совместимом с PyTorch
                max_length=512,  # Ограничение на длину текста 
                truncation=True  # Усечение текста, если его длина превышает max_length
            )
            
            # Перемещение токенизированных данных на нужное устройство
            inputs = {k: v.to(self.text_model.device) for k, v in inputs.items()}
            
            # Генерация текста с помощью модели на основе токенизированных данных
            outputs = self.text_model.generate(**inputs, **self.generation_config)
            
            # Декодирование сгенерированного текста в строку
            human_readable_text = self.text_tokenizer.decode(outputs[0], skip_special_tokens=True)

            return human_readable_text  # Возвращаем итоговый текст
        
        except Exception as e:
            print(f"Ошибка: {e}")
            return answer  

    
    def validate_answer(self, answer):
        pass
