import io
import os
import wave
import json
import logging

import pyttsx3
import requests
import sounddevice as sd
import speech_recognition as sr
import numpy as np

from vosk import Model
from vosk import KaldiRecognizer
from gtts import gTTS
from pydub import AudioSegment
from pathlib import Path


from config_models import SpeechConfig
from config_models import SpeechModelsConfig

logger = logging.getLogger(__name__)

class SpeechProcessor:
    def __init__(self, config: SpeechConfig, models: SpeechModelsConfig):
        self.config     = config
        self.model_path = models.vosk
        self.engine     = pyttsx3.init()
        self.set_voice(config.language)
        self.vosk_model = Model(self.model_path)
        logger.info("SpeechProcessor: язык=%s, режим=%s, модель=%s",
                    config.language, config.mode, self.model_path)

    def __init__(self, config: SpeechConfig, models: SpeechModelsConfig):
        self.config     = config
        self.model_path = models.vosk
        self.engine     = pyttsx3.init()
        self.set_voice(config.language)
        self.vosk_model = Model(self.model_path)
        logger.info("SpeechProcessor: язык=%s, режим=%s, модель=%s",
                    config.language, config.mode, self.model_path)

    def set_voice(self, language):
        voices = self.engine.getProperty('voices')
        target_voice = 'russian' if language == 'ru' else 'english'

        for voice in voices:
            if target_voice in voice.name.lower():
                self.engine.setProperty('voice', voice.id)
                return

        logger.warning("Голос для языка '%s' не найден", language)

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
