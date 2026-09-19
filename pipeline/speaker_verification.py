"""
Layer 2: Speaker verification (voiceprint matching).

Enrolls a reference voice sample per contact name, then compares a live call's
voice embedding against the enrolled one for the stated name (cosine similarity).

Asymmetric on purpose:
  * a confident MISMATCH is strong evidence -> the waterfall exits to AI_SCAM
  * a MATCH is weak evidence (a good clone can pass a voiceprint check) ->
    it only means "not disqualified yet"; the waterfall keeps going

Thresholds are on RAW cosine similarity. Measured on this project's saved 8 kHz
Twilio recordings: same speaker (two halves of one call) 0.87-0.93; different
speakers 0.73-0.76. Defaults sit in that gap (mismatch < 0.80, match >= 0.85);
the band between them is "inconclusive" and never exits.

Enroll from a sample recorded THROUGH THE PHONE LINE (e.g. reuse a saved
data/call_*.wav via /enroll), not a studio mic. Cross-channel same-speaker scores
run lower than the same-channel numbers above and could land under the mismatch
line — a false AI_SCAM on a real contact. Re-check with your own enrolled voice
before the demo and adjust SPEAKER_MISMATCH_BELOW if needed.
"""

import json
import os
import re

import numpy as np

_ENROLL_STORE = os.path.join(os.path.dirname(__file__), "..", "data", "enrolled_embeddings.json")
_encoder = None


def _get_encoder():
    # Lazy: loading the encoder at import time slows every server start and every test run.
    global _encoder
    if _encoder is None:
        from resemblyzer import VoiceEncoder

        _encoder = VoiceEncoder()
    return _encoder


def _mismatch_below() -> float:
    return float(os.getenv("SPEAKER_MISMATCH_BELOW", "0.80"))


def _match_at_or_above() -> float:
    return float(os.getenv("SPEAKER_MATCH_ABOVE", "0.85"))


def _load_store() -> dict:
    if os.path.exists(_ENROLL_STORE):
        with open(_ENROLL_STORE) as f:
            return json.load(f)
    return {}


def _save_store(store: dict):
    os.makedirs(os.path.dirname(_ENROLL_STORE), exist_ok=True)
    with open(_ENROLL_STORE, "w") as f:
        json.dump(store, f)


def _embed(audio_path: str) -> list:
    from resemblyzer import preprocess_wav

    wav = preprocess_wav(audio_path)
    return _get_encoder().embed_utterance(wav).tolist()


def enroll_voice(name: str, audio_path: str):
    store = _load_store()
    store[name.lower()] = _embed(audio_path)
    _save_store(store)


def list_enrolled_names() -> list[str]:
    return sorted(_load_store().keys())


def find_enrolled_name_in_text(text: str) -> str | None:
    """First enrolled contact name that appears as a whole word in `text`."""
    lowered = (text or "").lower()
    for name in list_enrolled_names():
        if re.search(rf"\b{re.escape(name)}\b", lowered):
            return name
    return None


def _cosine(audio_path: str, stated_name: str):
    """Raw cosine similarity (-1..1) vs the enrolled sample, or None if not enrolled."""
    store = _load_store()
    key = (stated_name or "").lower()
    if key not in store:
        return None
    enrolled = np.array(store[key])
    live = np.array(_embed(audio_path))
    return float(np.dot(enrolled, live) / (np.linalg.norm(enrolled) * np.linalg.norm(live)))


def compare_to_enrolled(audio_path: str, stated_name: str):
    """
    Legacy 0..1 similarity (cosine rescaled), or None if no enrollment is on file
    for the stated name. Kept so existing callers don't break.
    """
    cosine = _cosine(audio_path, stated_name)
    return None if cosine is None else float(np.clip((cosine + 1) / 2, 0, 1))


def verify_speaker(audio_path: str, stated_name) -> dict:
    """
    Layer 2 entry point. status is one of:
      no_enrollment — no stated name, or nobody enrolled under it (proceed)
      match         — cosine >= match threshold (proceed; NOT a green light)
      inconclusive  — between thresholds (proceed)
      mismatch      — cosine < mismatch threshold (waterfall exits to AI_SCAM)
    """
    if not stated_name:
        return {"status": "no_enrollment", "name": None}
    cosine = _cosine(audio_path, stated_name)
    if cosine is None:
        return {"status": "no_enrollment", "name": stated_name}
    if cosine < _mismatch_below():
        status = "mismatch"
    elif cosine >= _match_at_or_above():
        status = "match"
    else:
        status = "inconclusive"
    return {"status": status, "name": stated_name, "similarity": round(cosine, 3)}
