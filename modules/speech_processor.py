import io
import json
import logging
import tempfile
import wave
from pathlib import Path
from typing import Union

import pyttsx3
import vosk
from pydub import AudioSegment

from config_models import SpeechConfig

logger = logging.getLogger(__name__)

audio_bytes_like = Union[bytes, io.BytesIO, AudioSegment]

class SpeechProcessor: 
    def __init__(self, config: SpeechConfig):
        self.config = config
        self.model_path = Path(config.model)
        if not self.model_path.exists():
            raise FileNotFoundError(f"Vosk‑модель не найдена: {self.model_path}")

        # TTS
        self._engine = pyttsx3.init()
        self._set_voice(config.language)

        # STT
        self._sample_rate = 16_000
        self._rec_model = vosk.Model(str(self.model_path))
        logger.info("SpeechProcessor инициализирован — язык=%s, offline‑only, модель=%s",
                    config.language, self.model_path)

    def text_to_speech(self, text: str) -> AudioSegment:
        """Преобразует *text* в WAV‑аудио и возвращает **AudioSegment**."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp_path = Path(tmp.name)
        try:
            self._engine.save_to_file(text, str(tmp_path))
            self._engine.runAndWait()
            audio = AudioSegment.from_wav(tmp_path)
            return audio
        finally:
            tmp_path.unlink(missing_ok=True)

    def speech_to_text(self, audio_data: audio_bytes_like) -> str:
        """Преобразует WAV‑аудио (bytes/BytesIO/AudioSegment) в строку текста."""
        wav_path = self._to_wav_temp(audio_data)
        try:
            with wave.open(str(wav_path), "rb") as wf:
                if wf.getnchannels() != 1 or wf.getsampwidth() != 2:
                    raise ValueError("Аудио должно быть моно 16‑бит")

                recognizer = vosk.KaldiRecognizer(self._rec_model, wf.getframerate())
                while True:
                    data = wf.readframes(4000)
                    if len(data) == 0:
                        break
                    recognizer.AcceptWaveform(data)
                result = json.loads(recognizer.FinalResult())
                return result.get("text", "").strip()
        finally:
            wav_path.unlink(missing_ok=True)

    def _set_voice(self, language: str) -> None:
        voices = self._engine.getProperty("voices")
        target = "russian" if language.startswith("ru") else "english"
        for voice in voices:
            if target in voice.name.lower():
                self._engine.setProperty("voice", voice.id)
                return
        logger.warning("Голос для языка '%s' не найден — используется дефолтный", language)

    def _to_wav_temp(self, audio: audio_bytes_like) -> Path:
        """Сохраняет *audio* как WAV и возвращает путь к временному файлу."""
        if isinstance(audio, AudioSegment):
            seg = audio
        else:
            if isinstance(audio, io.BytesIO):
                raw = audio.getvalue()
            elif isinstance(audio, bytes):
                raw = audio
            else:
                raise TypeError("audio_data должен быть bytes, BytesIO или AudioSegment")
            seg = AudioSegment.from_file(io.BytesIO(raw))

        # Приводим к 16kHz / моно / 16‑bit
        seg = seg.set_frame_rate(self._sample_rate).set_channels(1).set_sample_width(2)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            seg.export(tmp, format="wav")
            return Path(tmp.name)
