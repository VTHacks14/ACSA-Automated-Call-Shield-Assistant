"""
Speech-to-text (ElevenLabs Scribe, POST /v1/speech-to-text). Not one of the four layers.

Produces no risk score of its own — its only job is turning the caller's audio
into text for Gemini and for the on-screen transcript. Runs before Layer 2,
because Layer 2 needs the stated name out of the transcript.

Needs ELEVENLABS_API_KEY. Every call sends the recording to ElevenLabs and uses
credits. If the key is missing or the request fails, `transcribe_audio` raises and
the waterfall records an empty transcript (Layer 2 then has no name to act on and the
call falls through to the later layers) — there is no local fallback model any more.

Optional env: ELEVENLABS_STT_MODEL (default scribe_v2), ELEVENLABS_STT_LANGUAGE (default en).
`keyterms` (bias toward given words, +20% cost) is deliberately not used: biasing toward an
enrolled name would make the recognizer snap a garbled name to it and hide real mishearings.
"""

import logging
import mimetypes
import os
import time

import requests

log = logging.getLogger("acsa.transcribe")

ENDPOINT = "https://api.elevenlabs.io/v1/speech-to-text"
DEFAULT_MODEL = "scribe_v2"
_TIMEOUT_SECONDS = 60
_ATTEMPTS = 2  # one retry for a rate limit / 5xx / network blip; calls are short but this runs live on a phone call


def warm_up():
    """Nothing to load (the old local model needed this); kept so the server's startup hook doesn't change."""


def transcribe_audio(audio_path: str) -> str:
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is not set")
    data = {
        "model_id": os.getenv("ELEVENLABS_STT_MODEL", DEFAULT_MODEL),
        "language_code": os.getenv("ELEVENLABS_STT_LANGUAGE", "en"),
        "tag_audio_events": "false",  # keep "(laughter)" / "(footsteps)" out of the transcript
        "diarize": "false",
    }
    content_type = mimetypes.guess_type(audio_path)[0] or "application/octet-stream"

    last_error = "no attempt made"
    for attempt in range(_ATTEMPTS):
        try:
            with open(audio_path, "rb") as f:
                resp = requests.post(
                    ENDPOINT, headers={"xi-api-key": api_key}, data=data,
                    files={"file": (os.path.basename(audio_path), f, content_type)}, timeout=_TIMEOUT_SECONDS,
                )
        except requests.RequestException as exc:
            last_error = f"{type(exc).__name__}"
        else:
            if resp.status_code == 200:
                return (resp.json().get("text") or "").strip()
            last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
            if resp.status_code != 429 and resp.status_code < 500:
                break  # a bad key / bad request won't get better by retrying
        if attempt + 1 < _ATTEMPTS:
            log.warning("ElevenLabs STT attempt %d failed (%s) — retrying", attempt + 1, last_error)
            time.sleep(1)
    raise RuntimeError(f"ElevenLabs speech-to-text failed ({last_error})")
