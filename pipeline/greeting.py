"""
ACSA's spoken greeting: a pre-generated mp3 checked in under static/ that Twilio
<Play>s when the user taps Yes. Nothing is generated at runtime. If the file is
missing, callers fall back to Twilio's <Say>, so the demo never goes silent.
"""

import os

GREETING_TEXT = (
    "Hey, I'm ACSA, the user's AI generated voice assistant. "
    "Please state your name and the reason for this call."
)
GREETING_FILENAME = "acsa_greeting.mp3"
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")


def greeting_audio_exists() -> bool:
    return os.path.isfile(os.path.join(STATIC_DIR, GREETING_FILENAME))
