import io
import os
import wave
import json

import pyttsx3
import requests
import sounddevice as sd
import speech_recognition as sr
import numpy as np

from vosk import Model
from vosk import KaldiRecognizer
from gtts import gTTS
from pydub import AudioSegment

from config_models import SpeechConfig
from config_models import ModelConfig


class SpeechProcessor:
    def __init__(self, config: SpeechConfig, models: ModelConfig):
        self.config = config
        self.engine = pyttsx3.init()
        self.language = config.language
        self.mode = config.mode
        self.model_path = models.vosk

        self.set_voice(self.language)

        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Модель не найдена: {self.model_path}")
        self.vosk_model = Model(self.model_path)

    def update_config(self, new_config: SpeechConfig, new_models: ModelConfig):
        self.config = new_config
        self.model_path = new_models.vosk
        self.__init__(new_config, new_models)

    def set_voice(self, language):
        voices = self.engine.getProperty('voices')
        target_voice = 'russian' if language == 'ru' else 'english'

        for voice in voices:
            if target_voice in voice.name.lower():
                self.engine.setProperty('voice', voice.id)
                return

        print(f"Предупреждение: Голос для языка '{language}' не найден. Установите RHVoice для русского языка.")

    def check_internet(self):
        try:
            requests.get("https://www.google.com", timeout=3)
            return True
        except (requests.ConnectionError, requests.Timeout):
            return False

    def text_to_speech(self, text):
        mode = self.mode
        if mode == 'auto':
            mode = 'online' if self.check_internet() else 'offline'

        if mode == 'online':
            tts = gTTS(text=text, lang=self.language)
            audio_bytes = io.BytesIO()
            tts.write_to_fp(audio_bytes)
            audio_bytes.seek(0)
            return AudioSegment.from_mp3(audio_bytes)
        else:
            audio_bytes = io.BytesIO()
            self.engine.save_to_file(text, 'temp_audio.wav')
            self.engine.runAndWait()
            with open('temp_audio.wav', 'rb') as f:
                audio_bytes.write(f.read())
            os.remove('temp_audio.wav')
            audio_bytes.seek(0)
            return AudioSegment.from_wav(audio_bytes)

    def play_audio(self, audio_segment):
        samples = np.array(audio_segment.get_array_of_samples())
        sd.play(samples, audio_segment.frame_rate)
        sd.wait()

    def speech_to_text(self, audio_bytes):
        mode = self.mode
        if mode == 'auto':
            mode = 'online' if self.check_internet() else 'offline'

        if mode == 'online':
            recognizer = sr.Recognizer()
            with sr.AudioFile(audio_bytes) as source:
                audio = recognizer.record(source)
            return recognizer.recognize_google(audio, language=self.language)
        else:
            audio_bytes.seek(0)
            wf = wave.open(audio_bytes, "rb")
            if not (wf.getnchannels() == 1 and wf.getsampwidth() == 2 and wf.getframerate() in (8000, 16000)):
                raise ValueError("Аудио должно быть в формате WAV: 1 канал, 16 бит, 8/16 кГц")

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