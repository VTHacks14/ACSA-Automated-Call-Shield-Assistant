"""
Pull the name a caller states out of the transcript.

Three passes, in order:
  1. An enrolled contact name appearing as a whole word anywhere — exact, the strongest signal.
  2. A FUZZY match: speech-to-text often mishears or garbles a name ("Nehal" -> "Nihal", "Neal", "Neha"),
     and an exact-only check would let exactly that caller skip Layer 2's voice comparison. So the word
     the caller uses in the name slot ("it's X", "this is X", "my name is X", "X here") is compared with each
     enrolled name using difflib.SequenceMatcher; a ratio >= NAME_MATCH_MIN (default 0.6) counts, and the
     enrolled name is returned so Layer 2 runs. Only the name slot is considered, and only capitalized words:
     scoring every word in the call would match ordinary words ("near", "half", "heal", "hall" all score
     0.67 against "nehal") and send innocent callers to a voiceprint check they'd fail.
  3. A naive "my name is X" / "this is X" pattern, used just for display when the caller isn't enrolled.
     Gemini also returns a stated_name and the waterfall prefers it for display when it runs.

Why 0.6: on a recorded test, speech-to-text turned a spoken "Nihal" into "Nihau", which scores exactly 0.60
against "nehal"; at 0.65 that garble skipped Layer 2 and the call fell through to Gemini as LIKELY_HUMAN.

Trade-off to know about: a genuinely different person whose name sounds like an enrolled one (a real "Neil"
scores 0.67, "Hazel"/"Nahla"/"Halle" exactly 0.60 against "nehal") is also sent to Layer 2 — and a voiceprint
mismatch exits the waterfall as AI_SCAM. Raise NAME_MATCH_MIN (0.7 drops all of those but keeps Nihal, Neal,
Neha) to trade that false alarm against catching fewer garbled names.
"""

import logging
import os
import re
from difflib import SequenceMatcher

from pipeline.speaker_verification import find_enrolled_name_in_text, list_enrolled_names

log = logging.getLogger("acsa.stated_name")

_PATTERN = re.compile(r"\b(?:my name is|this is|it's|it is|i'm|i am)\s+([A-Za-z][A-Za-z'-]+)", re.IGNORECASE)
# Where a name is likely to sit: the word right after an introduction, or right before "here/speaking/calling".
_SLOT = re.compile(
    r"\b(?:my name is|my name's|the name is|the name's|name is|this is|it's|it is|i'm|i am)\s+([A-Za-z][A-Za-z'’-]*)",
    re.IGNORECASE)
_TRAILING = re.compile(r"\b([A-Z][A-Za-z'’-]*)\s+(?:here|speaking|calling)\b")  # case-sensitive: capitalized only
# Words that follow those openers but aren't names ("this is an emergency", "I'm calling about...").
_NOT_NAMES = {
    "a", "an", "the", "calling", "just", "not", "here", "from", "trying", "sorry", "so", "really", "very",
    "in", "at", "on", "your", "with", "going", "looking", "having", "currently", "actually", "glad", "happy",
    "afraid", "worried", "fine", "good", "okay", "ok", "sure", "urgent", "important", "emergency", "me",
    "him", "her", "them", "you", "us", "it", "that", "what", "who", "how", "why", "when", "where", "yes", "no",
}


def _min_ratio() -> float:
    return float(os.getenv("NAME_MATCH_MIN", "0.6"))


def fuzzy_enrolled_name(transcript: str) -> tuple[str, str, float] | None:
    """(enrolled name, the word as heard, similarity) for the best name-slot match at or above the threshold."""
    enrolled = list_enrolled_names()
    if not enrolled or not transcript:
        return None
    floor = _min_ratio()
    heard = [m.group(1) for m in _SLOT.finditer(transcript)] + [m.group(1) for m in _TRAILING.finditer(transcript)]
    best = None
    for token in heard:
        if not token[:1].isupper():  # names are proper nouns; "it's nearly done" must not become a name
            continue
        word = re.sub(r"['’]s$", "", token).strip("'’-").lower()  # "Nehal's" -> "nehal"
        if len(word) < 3 or word in _NOT_NAMES:
            continue
        for name in enrolled:
            score = SequenceMatcher(None, word, name).ratio()
            if score >= floor and (best is None or score > best[2]):
                best = (name, token, score)
    return best


def extract_stated_name(transcript: str) -> str | None:
    enrolled = find_enrolled_name_in_text(transcript)
    if enrolled:
        return enrolled
    fuzzy = fuzzy_enrolled_name(transcript)
    if fuzzy:
        name, heard, score = fuzzy
        log.info("heard name %r is close to enrolled %r (similarity %.2f) — Layer 2 will compare voices", heard, name, score)
        return name
    for match in _PATTERN.finditer(transcript or ""):
        word = match.group(1)
        if word.lower() not in _NOT_NAMES:
            return word.capitalize()
    return None
