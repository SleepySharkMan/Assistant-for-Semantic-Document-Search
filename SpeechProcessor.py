import io
import os
import wave
import json
import pyttsx3
import requests
import sounddevice as sd
import speech_recognition as sr
import numpy as np
from vosk import Model, KaldiRecognizer
from gtts import gTTS
from pydub import AudioSegment


class SpeechProcessor:
    def __init__(self, model_path, language='ru', mode='auto'):
        """
        Инициализация обработчика речи.

        :param language: Язык ('ru')
        :param mode: Режим работы ('auto', 'online', 'offline')
        :param model_path: Путь к модели Vosk для русского языка
        """
        self.language = language
        self.mode = mode
        self.engine = pyttsx3.init()
        self.set_voice(language)

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Модель не найдена: {model_path}")
        self.vosk_model = Model(model_path)

    def set_voice(self, language):
        """Устанавливает голос для синтеза речи."""
        voices = self.engine.getProperty('voices')
        target_voice = 'russian' if language == 'ru' else 'english'

        for voice in voices:
            if target_voice in voice.name.lower():
                self.engine.setProperty('voice', voice.id)
                return

        print(
            f"Предупреждение: Голос для языка '{language}' не найден. Установите RHVoice для русского языка.")

    def check_internet(self):
        """Проверяет подключение к интернету."""
        try:
            requests.get("https://www.google.com", timeout=3)
            return True
        except (requests.ConnectionError, requests.Timeout):
            return False

    def set_mode(self, mode):
        """Устанавливает режим работы."""
        self.mode = mode
        print(f"Режим установлен: {mode}")

    def text_to_speech(self, text):
        """Синтезирует речь из текста и возвращает аудиоданные."""
        if self.mode == 'auto':
            self.mode = 'online' if self.check_internet() else 'offline'

        if self.mode == 'online':
            # Онлайн-синтез через gTTS
            tts = gTTS(text=text, lang=self.language)
            audio_bytes = io.BytesIO()
            tts.write_to_fp(audio_bytes)
            audio_bytes.seek(0)
            return AudioSegment.from_mp3(audio_bytes)
        else:
            # Оффлайн-синтез через pyttsx3
            audio_bytes = io.BytesIO()
            self.engine.save_to_file(text, 'temp_audio.wav')
            self.engine.runAndWait()
            with open('temp_audio.wav', 'rb') as f:
                audio_bytes.write(f.read())
            os.remove('temp_audio.wav')
            return AudioSegment.from_wav(audio_bytes)

    def play_audio(self, audio_segment):
        """Воспроизводит аудио через наушники."""
        samples = np.array(audio_segment.get_array_of_samples())
        sd.play(samples, audio_segment.frame_rate)
        sd.wait()

    def speech_to_text(self, audio_bytes):
        """Распознает речь из аудиоданных."""
        if self.mode == 'auto':
            self.mode = 'online' if self.check_internet() else 'offline'

        if self.mode == 'online':
            # Онлайн-распознавание через Google
            recognizer = sr.Recognizer()
            with sr.AudioFile(audio_bytes) as source:
                audio = recognizer.record(source)
            return recognizer.recognize_google(audio, language=self.language)
        else:
            # Оффлайн-распознавание через Vosk
            audio_bytes.seek(0)
            wf = wave.open(audio_bytes, "rb")
            if not (wf.getnchannels() == 1 and
                    wf.getsampwidth() == 2 and
                    wf.getframerate() in (8000, 16000)):
                raise ValueError(
                    "Аудио должно быть в формате WAV: 1 канал, 16 бит, 8/16 кГц")

            recognizer = KaldiRecognizer(self.vosk_model, wf.getframerate())
            result = []
            while True:
                data = wf.readframes(4000)
                if not data:
                    break
                if recognizer.AcceptWaveform(data):
                    result.append(json.loads(recognizer.Result())['text'])

            result.append(json.loads(recognizer.FinalResult())['text'])
            return ' '.join(result)


if __name__ == "__main__":
    # Пример использования
    processor = SpeechProcessor(
        model_path='D:\\Assistant-for-Semantic-Document-Search\\models\\vosk-model-small-ru-0.22',
        language='ru',
        mode='auto'
    )

    # Синтез и воспроизведение речи
    audio = processor.text_to_speech("Привет! Как ваши дела?")
    processor.play_audio(audio)

    # Распознавание речи из аудио
    audio_bytes = io.BytesIO()
    audio.export(audio_bytes, format="wav")
    audio_bytes.seek(0)
    text = processor.speech_to_text(audio_bytes)
    print(f"Распознанный текст: {text}")
