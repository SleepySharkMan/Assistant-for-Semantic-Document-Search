import threading
import pyttsx3
import pythoncom  # Нужно для CoInitialize и CoUninitialize

def tts_thread(text):
    pythoncom.CoInitialize()  # Инициализация COM в потоке
    try:
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
    finally:
        pythoncom.CoUninitialize()  # Освобождение ресурсов COM

# Создание и запуск потоков с собственными экземплярами TTS
thread1 = threading.Thread(target=tts_thread, args=("Привет из потока 1",))
thread2 = threading.Thread(target=tts_thread, args=("Привет из потока 2",))

thread1.start()
thread2.start()

thread1.join()
thread2.join()
