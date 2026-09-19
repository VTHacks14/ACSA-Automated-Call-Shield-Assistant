"""
Pull the name a caller states out of the Whisper transcript.

Two passes: (1) any enrolled contact name appearing as a whole word — the only
case Layer 2 can act on, and far more robust than parsing grammar; (2) a naive
"my name is X" / "this is X" pattern, used just for display when the caller
isn't enrolled. Gemini also returns a stated_name and the waterfall prefers it
for display when it runs.
"""

import re

from pipeline.speaker_verification import find_enrolled_name_in_text

_PATTERN = re.compile(r"\b(?:my name is|this is|it's|it is|i'm|i am)\s+([A-Za-z][A-Za-z'-]+)", re.IGNORECASE)
# Words that follow those openers but aren't names ("this is an emergency", "I'm calling about...").
_NOT_NAMES = {
    "a", "an", "the", "calling", "just", "not", "here", "from", "trying", "sorry", "so", "really", "very",
    "in", "at", "on", "your", "with", "going", "looking", "having", "currently", "actually", "glad", "happy",
    "afraid", "worried", "fine", "good", "okay", "ok", "sure", "urgent", "important", "emergency", "me",
    "him", "her", "them", "you", "us", "it", "that", "what", "who", "how", "why", "when", "where", "yes", "no",
}


def extract_stated_name(transcript: str) -> str | None:
    enrolled = find_enrolled_name_in_text(transcript)
    if enrolled:
        return enrolled
    for match in _PATTERN.finditer(transcript or ""):
        word = match.group(1)
        if word.lower() not in _NOT_NAMES:
            return word.capitalize()
    return None
