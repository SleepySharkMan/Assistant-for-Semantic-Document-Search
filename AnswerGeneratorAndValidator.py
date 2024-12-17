import torch
from transformers import (
    AutoTokenizer, 
    AutoModelForQuestionAnswering, 
    AutoModelForCausalLM, 
    pipeline, 
    BitsAndBytesConfig
)
import re

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

        # Настройка BitsAndBytes для 4-битного квантования
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            # bnb_4bit_compute_device=self.device
        )

        # Загрузка токенизатора и модели генерации текста
        self.text_tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.text_model = AutoModelForCausalLM.from_pretrained(
            model_path,
            quantization_config=bnb_config,
            device_map="auto"
        ).to(self.device)

        # Расширенная конфигурация генерации текста
        self.generation_config = {
        'max_length': 1000,
        'min_length': 100,
        'num_return_sequences': 1,
        'do_sample': True,  
        'temperature': 0.3,
        'no_repeat_ngram_size': 3,
        'num_beams': 1, 
        'diversity_penalty': 0.0
        }


    def configure_model(self, **kwargs):
        """
        Настройка параметров генерации текста с расширенной валидацией.
        """
        # Список допустимых параметров с их ограничениями
        param_constraints = {
            'temperature': (0, 1),
            'max_length': (10, 1000),
            'min_length': (10, 500),
            'num_return_sequences': (1, 5),
            'no_repeat_ngram_size': (1, 5),
            'repetition_penalty': (1.0, 2.0),
            'num_beams': (1, 10),
            'diversity_penalty': (0, 1)
        }

        for key, value in kwargs.items():
            if key not in param_constraints:
                raise ValueError(f"Неизвестный параметр: {key}")

            min_val, max_val = param_constraints[key]
            if not (min_val <= value <= max_val):
                raise ValueError(f"{key} должен быть в диапазоне {min_val}-{max_val}")

            self.generation_config[key] = value
        
        return self


    def find_answer(self, contexts, question):
        """
        Извлекает наиболее релевантный ответ из списка контекстов.
        """
        best_answers = []

        for context in contexts:
            try:
                qa_result = self.qa_pipeline(question=question, context=context)
                extracted_answer = qa_result['answer']
                confidence = qa_result.get('score', 0)

                # Более мягкие критерии отбора ответов
                if (len(extracted_answer) >= 3 and 
                    extracted_answer.lower() in context.lower()):
                    best_answers.append({
                        'answer': extracted_answer, 
                        'confidence': confidence, 
                        'context': context
                    })
            except Exception as e:
                print(f"Ошибка при извлечении ответа: {e}")

        # Сортировка ответов по confidence
        if best_answers:
            best_answers.sort(key=lambda x: x['confidence'], reverse=True)
            
            # Возвращаем наиболее полный ответ
            full_answer = best_answers[0]['answer']
            
            # Если ответ слишком короткий, пытаемся расширить из контекста
            if len(full_answer) < 10:
                context = best_answers[0]['context']
                sentences = re.findall(r'[^.!?]+[.!?]', context)
                matching_sentences = [
                    s for s in sentences 
                    if full_answer.lower() in s.lower()
                ]
                
                if matching_sentences:
                    full_answer = matching_sentences[0].strip()

            return full_answer

        return "Не удалось найти релевантный ответ в предоставленных контекстах."


    def generate_human_readable_text(self, question, answer, context=None):
        """
        Генерирует человеко-читаемый текст на основе вопроса, ответа и контекста.
        """
        # Более информативный промпт
        prompt = f"""Контекст: {context[0] if context else ''}

        Вопрос: {question}
        Ключевой ответ: {answer}

        Инструкции для генерации:
        - Используй только информацию из предоставленного контекста
        - Развернуто и подробно объясни ключевой ответ
        - Структурируй ответ логично
        - Включи дополнительные релевантные детали
        - Избегай вымышленной информации

        Подробное объяснение:
        """
        
        try:
            inputs = self.text_tokenizer(prompt, return_tensors="pt").to(self.device)
            
            # Упрощенная генерация с четкими параметрами
            outputs = self.text_model.generate(
                input_ids=inputs['input_ids'], 
                attention_mask=inputs['attention_mask'],
                max_length=500,
                min_length=100,
                do_sample=True,
                temperature=0.7,  # Немного повысили температуру
                num_return_sequences=1,
                no_repeat_ngram_size=2
            )
            
            generated_text = self.text_tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Извлечение только сгенерированной части
            explanation = generated_text[len(prompt):].strip()
            
            # Постобработка текста
            explanation = self._enhance_explanation(explanation, answer, context)
            
            return explanation
        
        except Exception as e:
            print(f"Ошибка при генерации текста: {e}")
            return f"Не удалось сгенерировать подробный ответ. Техническая информация: {str(e)}"


    def _enhance_explanation(self, text, answer, context):
        """
        Улучшение сгенерированного объяснения.
        """
        # Если текст слишком короткий, добавляем информацию из контекста
        if len(text) < 50 and context:
            context_text = context[0] if isinstance(context, list) else context
            text += " " + context_text[:500]  # Добавляем часть контекста
        
        # Удаление повторов и незавершенных предложений
        text = re.sub(r'(.+?)\1+', r'\1', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Убеждаемся, что ответ упоминается
        if answer.lower() not in text.lower():
            text = f"{answer}. {text}"
        
        return text

    def generate_human_readable_text_without_answer(self, question, context=None):
        """
        Генерирует текст без предварительного извлечения ответа.
        """
        prompt = f"""Контекст: {context[0] if context else ''}

        Вопрос: {question}

        Инструкции:
        - Используй только информацию из предоставленного контекста
        - Дай полный и развернутый ответ
        - Будь информативным и точным
        - Структурируй текст логично

        Подробный ответ:
        """
        
        try:
            inputs = self.text_tokenizer(prompt, return_tensors="pt").to(self.device)
            
            outputs = self.text_model.generate(
                input_ids=inputs['input_ids'], 
                attention_mask=inputs['attention_mask'],
                max_length=500,
                min_length=100,
                do_sample=True,
                temperature=0.7,
                num_return_sequences=1,
                no_repeat_ngram_size=2
            )
            
            generated_text = self.text_tokenizer.decode(outputs[0], skip_special_tokens=True)
            explanation = generated_text[len(prompt):].strip()
            
            # Постобработка текста
            explanation = self._enhance_explanation(explanation, "", context)
            
            return explanation
        
        except Exception as e:
            print(f"Ошибка при генерации текста: {e}")
            return f"Не удалось сгенерировать подробный ответ. Техническая информация: {str(e)}"