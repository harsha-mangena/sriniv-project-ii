"""Speech-to-text using faster-whisper."""

import logging
from typing import Optional

from config import WHISPER_MODEL_SIZE

logger = logging.getLogger(__name__)

_model = None


def get_whisper_model():
    """Lazy-load the Whisper model."""
    global _model
    if _model is None:
        try:
            from faster_whisper import WhisperModel
            _model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
            logger.info("Whisper model '%s' loaded.", WHISPER_MODEL_SIZE)
        except ImportError:
            logger.warning("faster-whisper not installed. STT will be unavailable.")
            return None
        except Exception as e:
            logger.error("Failed to load Whisper model: %s", e)
            return None
    return _model


def transcribe_audio(audio_path: str, language: Optional[str] = "en") -> str:
    """Transcribe an audio file to text."""
    model = get_whisper_model()
    if model is None:
        return "[STT unavailable — faster-whisper not installed]"

    segments, info = model.transcribe(audio_path, language=language, beam_size=5)
    text = " ".join(segment.text.strip() for segment in segments)
    logger.info("Transcribed %.1fs audio (%s), detected language: %s", info.duration, audio_path, info.language)
    return text


def transcribe_audio_segments(audio_path: str, language: Optional[str] = "en") -> list[dict]:
    """Transcribe audio with timestamp segments."""
    model = get_whisper_model()
    if model is None:
        return []

    segments, info = model.transcribe(audio_path, language=language, beam_size=5)
    result = []
    for segment in segments:
        result.append({
            "start": segment.start,
            "end": segment.end,
            "text": segment.text.strip(),
        })
    return result
