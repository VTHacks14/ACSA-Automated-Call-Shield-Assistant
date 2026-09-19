"""
Layer 2: Speaker verification (voiceprint matching).

Enrolls a reference voice sample per contact name, then compares any new
call's voice embedding against the enrolled one for that name using cosine
similarity. This is the layer that catches "sounds right but isn't them"
even when the audio is otherwise convincing.
"""

import os
import json
import numpy as np
from resemblyzer import VoiceEncoder, preprocess_wav

_encoder = VoiceEncoder()
_ENROLL_STORE = os.path.join(os.path.dirname(__file__), "..", "data", "enrolled_embeddings.json")


def _load_store() -> dict:
    if os.path.exists(_ENROLL_STORE):
        with open(_ENROLL_STORE) as f:
            return json.load(f)
    return {}


def _save_store(store: dict):
    with open(_ENROLL_STORE, "w") as f:
        json.dump(store, f)


def _embed(audio_path: str) -> list:
    wav = preprocess_wav(audio_path)
    embedding = _encoder.embed_utterance(wav)
    return embedding.tolist()


def enroll_voice(name: str, audio_path: str):
    store = _load_store()
    store[name.lower()] = _embed(audio_path)
    _save_store(store)


def compare_to_enrolled(audio_path: str, stated_name: str):
    """
    Returns a similarity score from 0 (no match) to 1 (strong match),
    or None if we have no enrollment on file for the stated name — in
    which case the fusion layer should lean on the other signals instead.
    """
    store = _load_store()
    key = stated_name.lower()
    if key not in store:
        return None

    enrolled_embedding = np.array(store[key])
    live_embedding = np.array(_embed(audio_path))

    cosine_sim = np.dot(enrolled_embedding, live_embedding) / (
        np.linalg.norm(enrolled_embedding) * np.linalg.norm(live_embedding)
    )
    # Cosine similarity is roughly -1..1; clip and rescale to 0..1 for the fusion layer.
    return float(np.clip((cosine_sim + 1) / 2, 0, 1))
