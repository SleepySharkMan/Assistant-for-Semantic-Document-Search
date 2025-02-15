import time
import AnswerGeneratorAndValidator as AG
import EmbeddingHandler as EH
import FileLoader as FL
import TextContextSplitter as TC
from AnswerGeneratorAndValidator import GenerationMode, QuantizationMode

if __name__ == "__main__":
    start_time = time.time()

    # Пути к моделям
    qa_model_path = "models\\mdeberta-v3-base-squad2"
    text_model_path = "models\\vicuna-7b-v1.5"
    embedding_model_path = "models\\paraphrase-multilingual-MiniLM-L12-v2"

    # Инициализация классов
    t1 = time.time()
    
    # Инициализация ассистента с настройками
    assistant = AG.AnswerGeneratorAndValidator(qa_model_path, text_model_path)
    assistant.set_generation_mode(GenerationMode.DETERMINISTIC)
    
    embedding_handler = EH.EmbeddingHandler(embedding_model_path)
    file_loader = FL.FileLoader()
    splitter = TC.TextContextSplitter()
    
    print("\nКонфигурация системы:")
    print(f"Устройство: {assistant.get_device_info()}")
    print(f"Режим генерации: {assistant.generation_mode.name}")
    print(f"Инициализация классов: {time.time() - t1:.2f} секунд")

    # Загрузка файлов
    t2 = time.time()
    text_file_path = 'D:\\Assistant-for-Semantic-Document-Search\\Новый текстовый документ.txt'
    folder_path = 'D:\\Assistant-for-Semantic-Document-Search\\documents'
    
    file_loader.add_file(text_file_path)
    added_count = file_loader.add_files_from_folder(folder_path)
    
    print(f"\nЗагружено файлов: {added_count + 1}")
    print(f"Время загрузки файлов: {time.time() - t2:.2f} секунд")

    # Обработка контента
    t3 = time.time()
    combined_content = "".join(
        file_loader.get_file_content(file) 
        for file in file_loader.get_file_list()
    )
    
    # Разделение на контексты
    knowledge_base = splitter.split_by_paragraphs(
        content=combined_content, 
        paragraphs_per_context=1, 
        overlap_lines=1
    )
    
    print(f"\nОбработано контекстов: {len(knowledge_base)}")
    print(f"Время обработки контента: {time.time() - t3:.2f} секунд")

    # Список вопросов
    questions = [
        # Вопросы о мармеладе
        "Какое происхождение имеет название 'мармелад' и из какого фрукта он изначально изготавливался?",  # 0
        "Какие желирующие вещества чаще всего используются для производства мармелада?",  # 1
        "Какие полезные свойства имеют пектин и агар-агар?",  # 2
        "В каких формах и вариантах выпускается современный мармелад?",  # 3
        "Почему мармелад можно считать подходящим лакомством для тех, кто следит за своим питанием?",  # 4

        # Вопросы о тихоходках
        "Какая особенность тихоходок позволяет им выживать в экстремальных условиях, таких как космический вакуум или высокие температуры?",  # 5
        "Что такое криптобиоз, и как он помогает тихоходкам?",  # 6
        "Каким образом тихоходки питаются и что составляет основу их рациона?",  # 7
        "В каких условиях обитания чаще всего встречаются тихоходки?",  # 8
        "Какую роль тихоходки играют в научных исследованиях и какие области знаний они помогают развивать?",  # 9

        # Вопросы о мороженом
        "Какую роль играет мороженое в культуре разных народов?",  # 10
        "Какие виды мороженого есть?",  # 11
        "Чем отличается пломбир от сорбета?",  # 12
        "Какие формы мороженого сущесвуют?",  # 13
        "Какое значение имеет натуральный состав мороженого?"  # 14
    ]

    # Обработка вопроса
    question = questions[3]
    print(f"\nВопрос:\n{question}")
    print("─" * 50)

    # Поиск контекста и генерация ответа
    try:
        # Поиск релевантного контекста
        t4 = time.time()
        relevant_context = embedding_handler.find_most_relevant_contexts(
            question, knowledge_base, 1
        )
        print(f"Релевантный контекст найден за: {time.time() - t4:.2f} сек")
        
        # Извлечение ответа
        t5 = time.time()
        answer = assistant.find_answer(relevant_context, question)
        print(f"\nБазовый ответ: {answer}")
        print(f"Время извлечения ответа: {time.time() - t5:.2f} сек")
        
        # Генерация полного ответа
        t6 = time.time()
        full_answer = assistant.generate_response(
            prompt=f"""Сформулируй развернутый ответ на русском языке, используя:
            - Контекст: {relevant_context} 
            - Собственные знания (не ограничивайся контекстом)
            Ответ должен быть структурированным и содержать примеры, даже если их нет в контексте.
            Вопрос: {question}""")
        print(f"\nПолный ответ:\n{full_answer}")
        print(f"Время генерации ответа: {time.time() - t6:.2f} сек")
        
    except Exception as e:
        print(f"\nОшибка обработки: {str(e)}")

    # Итоговая информация
    total_time = time.time() - start_time
    print("\n" + "═" * 50)
    print(f"Общее время выполнения: {total_time:.2f} секунд")
    print(f"Используемое устройство: {assistant.get_device_info()}")