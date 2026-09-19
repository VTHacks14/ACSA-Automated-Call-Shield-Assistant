"""
Layer 1: Speech-to-text.

Loads Whisper once at import time (loading it per-call would be way too slow
for a live demo). "base" is a good speed/accuracy tradeoff for a hackathon —
bump to "small" if your machine can handle it and you want better accuracy.
"""

import whisper

_model = whisper.load_model("base")


def transcribe_audio(audio_path: str) -> str:
    result = _model.transcribe(audio_path)
    return result["text"].strip()
