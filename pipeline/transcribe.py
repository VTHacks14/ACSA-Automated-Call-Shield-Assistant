"""
Layer 5: Speech-to-text (Whisper).

Produces no risk score of its own — its only job is turning the caller's audio
into text for Gemini and for the on-screen transcript. Runs before Layer 2 in
practice, because Layer 2 needs the stated name out of the transcript.

The model loads lazily on first use and is then kept (loading per call would be
far too slow for a live demo; loading at import slows every server start and
test run). "base" is a good speed/accuracy tradeoff — bump to "small" if the
machine can take it. The server warms it at startup so the first real call isn't slow.
"""

import whisper

_model = None


def _get_model():
    global _model
    if _model is None:
        _model = whisper.load_model("base")
    return _model


def warm_up():
    _get_model()


def transcribe_audio(audio_path: str) -> str:
    result = _get_model().transcribe(audio_path)
    return result["text"].strip()
