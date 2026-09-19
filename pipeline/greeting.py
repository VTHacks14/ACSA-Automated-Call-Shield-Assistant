"""
ACSA's spoken greeting, generated once with ElevenLabs TTS and cached under
static/ so Twilio can <Play> it. (This is the TTS integration — distinct from
detection; ElevenLabs has no detection API.)

The filename embeds a hash of text+voice+model, so editing the wording or voice
regenerates automatically. If there's no key or the request fails, callers fall
back to Twilio's <Say>, so the demo never goes silent.
"""

import hashlib
import logging
import os

import requests

log = logging.getLogger("acsa.greeting")

GREETING_TEXT = (
    "Hey, I'm ACSA, the user's AI generated voice assistant. "
    "Please state your name and the reason for this call."
)
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")
DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # premade "Rachel"; override with ELEVENLABS_VOICE_ID
MODEL_ID = "eleven_multilingual_v2"


def ensure_greeting_audio() -> str | None:
    """Returns the cached mp3's filename inside static/ (generating it if needed), or None."""
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        log.warning("ELEVENLABS_API_KEY not set — greeting will use Twilio <Say>")
        return None
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", DEFAULT_VOICE_ID)
    digest = hashlib.sha256(f"{GREETING_TEXT}|{voice_id}|{MODEL_ID}".encode()).hexdigest()[:10]
    filename = f"greeting_{digest}.mp3"
    path = os.path.join(STATIC_DIR, filename)
    if os.path.exists(path):
        return filename
    try:
        resp = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            params={"output_format": "mp3_44100_128"},
            headers={"xi-api-key": api_key, "Content-Type": "application/json"},
            json={"text": GREETING_TEXT, "model_id": MODEL_ID},
            timeout=30,
        )
        resp.raise_for_status()
    except Exception as exc:
        log.warning("ElevenLabs TTS failed (%s) — greeting will use Twilio <Say>", exc)
        return None
    with open(path, "wb") as f:
        f.write(resp.content)
    log.info("generated greeting audio %s", filename)
    return filename
