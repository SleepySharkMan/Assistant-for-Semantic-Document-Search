import io
import json
import logging
import tempfile
import wave
import threading
import queue
from pathlib import Path
from typing import Union, Optional
import time

import pyttsx3
import vosk
from pydub import AudioSegment

from config_models import SpeechConfig

logger = logging.getLogger(__name__)

audio_bytes_like = Union[bytes, io.BytesIO, AudioSegment]

class TTSWorker:
    """Выделенный поток для работы с TTS"""
    
    def __init__(self, config: SpeechConfig):
        self.config = config
        self.task_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.worker_thread = None
        self._engine = None
        self.start_worker()
    
    def start_worker(self):
        """Запуск worker потока"""
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
    
    def _worker_loop(self):
        """Основной цикл worker потока"""
        try:
            # Инициализация движка в worker потоке
            self._engine = pyttsx3.init()
            self._set_voice(self.config.language)
            logger.info("TTS Worker поток запущен")
            
            while not self.stop_event.is_set():
                try:
                    # Ждем задачу с таймаутом
                    task = self.task_queue.get(timeout=1.0)
                    if task is None:  # Сигнал завершения
                        break
                    
                    task_id, text, tmp_path = task
                    try:
                        self._engine.save_to_file(text, str(tmp_path))
                        self._engine.runAndWait()
                        self.result_queue.put((task_id, True, None))
                    except Exception as e:
                        logger.error("Ошибка TTS в worker потоке: %s", e)
                        self.result_queue.put((task_id, False, str(e)))
                    finally:
                        self.task_queue.task_done()
                        
                except queue.Empty:
                    continue
                    
        except Exception as e:
            logger.error("Критическая ошибка TTS worker потока: %s", e)
        finally:
            if self._engine:
                try:
                    self._engine.stop()
                except:
                    pass
            logger.info("TTS Worker поток завершен")
    
    def synthesize(self, text: str, timeout: float = 10.0) -> Optional[Path]:
        """Синтез речи с таймаутом"""
        if self.stop_event.is_set():
            return None
            
        task_id = id(text)  # Простой ID для задачи
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp_path = Path(tmp.name)
        
        # Отправляем задачу в worker поток
        self.task_queue.put((task_id, text, tmp_path))
        
        # Ждем результат
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                result_task_id, success, error = self.result_queue.get(timeout=0.1)
                if result_task_id == task_id:
                    if success:
                        return tmp_path
                    else:
                        logger.error("TTS синтез провален: %s", error)
                        tmp_path.unlink(missing_ok=True)
                        return None
            except queue.Empty:
                continue
        
        logger.error("TTS синтез превысил таймаут")
        tmp_path.unlink(missing_ok=True)
        return None
    
    def _set_voice(self, language: str) -> None:
        if not self._engine:
            return
            
        try:
            voices = self._engine.getProperty("voices")
            if not voices:
                return
                
            target = "russian" if language.startswith("ru") else "english"
            for voice in voices:
                if target in voice.name.lower():
                    self._engine.setProperty("voice", voice.id)
                    return
        except Exception as e:
            logger.error("Ошибка установки голоса: %s", e)
    
    def stop(self):
        """Остановка worker потока"""
        self.stop_event.set()
        self.task_queue.put(None)  # Сигнал завершения
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=2.0)


class SpeechProcessor: 
    def __init__(self, config: SpeechConfig):
        self.config = config
        self.model_path = Path(config.model)
        if not self.model_path.exists():
            raise FileNotFoundError(f"Vosk‑модель не найдена: {self.model_path}")

        # TTS через выделенный поток
        self.tts_worker = TTSWorker(config)

        # STT
        self._sample_rate = 16_000
        self._rec_model = vosk.Model(str(self.model_path))
        logger.info("SpeechProcessor инициализирован — язык=%s, offline‑only, модель=%s",
                    config.language, self.model_path)

    def text_to_speech(self, text: str) -> AudioSegment:
        """Преобразует *text* в WAV‑аудио и возвращает **AudioSegment**."""
        try:
            tmp_path = self.tts_worker.synthesize(text, timeout=15.0)
            if not tmp_path or not tmp_path.exists():
                logger.error("TTS не создал аудиофайл")
                return AudioSegment.silent(duration=1000)
            
            try:
                audio = AudioSegment.from_wav(tmp_path)
                return audio
            finally:
                tmp_path.unlink(missing_ok=True)
                
        except Exception as e:
            logger.error("Критическая ошибка TTS: %s", e)
            return AudioSegment.silent(duration=1000)

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

    def __del__(self):
        """Очистка ресурсов при удалении объекта"""
        try:
            if hasattr(self, 'tts_worker'):
                self.tts_worker.stop()
        except Exception as e:
            logger.error("Ошибка при очистке TTS worker: %s", e)