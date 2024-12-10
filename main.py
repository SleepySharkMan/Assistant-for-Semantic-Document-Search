import AnswerGeneratorAndValidator as AG
import EmbeddingHandler as EH
import FileLoader as FL
import TextContextSplitter as TC

if __name__ == "__main__":
    qa_model_path = "models\\mdeberta-v3-base-squad2"       # Путь к модели для вопросов и ответов
    text_model_path = "models\\vicuna-7b-v1.5"  # Путь к модели для генерации текста
    embedding_model_path = "models\\paraphrase-multilingual-MiniLM-L12-v2"  # Путь к модели для создания эмбеддингов

    # Инициализация классов
    assistant = AG.AnswerGeneratorAndValidator(qa_model_path, text_model_path)
    embedding_handler = EH.EmbeddingHandler(embedding_model_path)
    file_loader = FL.FileLoader()
    splitter = TC.TextContextSplitter()

    # Добавляем отдельный текстовый файл
    text_file_path = 'D:\\Assistant-for-Semantic-Document-Search\\Новый текстовый документ.txt'  
    if file_loader.add_file(text_file_path):
        print(f"Файл {text_file_path} успешно добавлен")

    # Добавляем файлы из указанной папки
    folder_path = 'D:\\Assistant-for-Semantic-Document-Search\\documents' 
    added_count = file_loader.add_files_from_folder(folder_path)
    print(f"Из папки '{folder_path}' добавлено {added_count} файлов")

    combined_content = ""

    for file in file_loader.get_file_list():
        content = file_loader.get_file_content(file)
        if content:
            combined_content += content

    # Делим текст на абзацы с перекрытием в 1 строку
    knowledge_base = splitter.split_by_paragraphs(content=combined_content, paragraphs_per_context=1, overlap_lines=1)

    # # # Делим текст на предложения с перекрытием в 1 предложение
    # # knowledge_base = splitter.split_by_sentences(content=combined_content, sentences_per_context=2, overlap_sentences=1)

    # # # Делим текст на слова с перекрытием
    # # knowledge_base = splitter.split_by_words(content=combined_content, words_per_context=10, overlap_words=3)

    # print("Контексты:")
    # for i, context in enumerate(knowledge_base):
    #     print(f"\nКонтекст {i + 1}:\n{context}")

    # Вопросы
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

    # Вопрос
    question = questions[0]
    print(f"Вопрос:\n{question}")
    print("-------------------------")
    # Поиск наиболее релевантного контекста
    relevant_context = embedding_handler.find_most_relevant_contexts(question, knowledge_base, 1)
    print(f"Релевантный контекст:\n{relevant_context}")
    # Поиск ответа
    print("-------------------------")
    answer = assistant.find_answer(relevant_context, question)
    print(f"Ответ:\n{answer}")
    print("-------------------------")
    readable_answer = assistant.generate_human_readable_text(question, answer, relevant_context)
    print(f"Конечный ответ:\n{readable_answer}")
