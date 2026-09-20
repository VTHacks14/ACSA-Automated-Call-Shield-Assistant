"""
Layer 3: local open-source AI-voice detector (Hugging Face wav2vec2 classifier).

Replaces the originally planned ElevenLabs classifier, which has no public API
(web UI only) and can't detect other vendors' audio anyway. This runs on-box, so
no key and no quota.

DISABLED BY DEFAULT (LOCAL_DETECTOR_ENABLED=1 to turn on). Measured on this
project's saved Twilio recordings (8 kHz), this model is miscalibrated: a clearly
live human caller scored 1.0 "fake", and macOS TTS scored 0.0 both wideband and
at 8 kHz. Left on, it would hand the green demo a false AI_SCAM. The model
card's ~99.7% accuracy is on its own wideband eval set, not phone audio.

To turn it on safely: generate the Cartesia red clip, play it through Twilio,
and compare its score against real human calls (scripts/run_pipeline_on_file.py
prints the Layer 3 score). Only enable if the two separate cleanly, then set
LOCAL_DETECTOR_AI_ABOVE between them — or swap MODEL_ID for a phone-robust model.

Only "ai" can end a call. Everything else proceeds to Gemini.
"""

import logging
import os

log = logging.getLogger("acsa.local_detector")

MODEL_ID = os.getenv("LOCAL_DETECTOR_MODEL", "MelodyMachine/Deepfake-audio-detection-V2")
_AI_LABEL_HINTS = ("fake", "spoof", "synthetic", "deepfake", "ai")
_MAX_SECONDS = 20  # calls are one short statement; cap it so inference stays fast

_extractor = None
_model = None


def _enabled() -> bool:
    return os.getenv("LOCAL_DETECTOR_ENABLED", "0") in ("1", "true", "True")


def _ai_above() -> float:
    return float(os.getenv("LOCAL_DETECTOR_AI_ABOVE", "0.95"))


def _load():
    global _extractor, _model
    if _model is None:
        from transformers import AutoFeatureExtractor, AutoModelForAudioClassification

        _extractor = AutoFeatureExtractor.from_pretrained(MODEL_ID)
        _model = AutoModelForAudioClassification.from_pretrained(MODEL_ID).eval()
    return _extractor, _model


def warm_up():
    if _enabled():
        _load()


def _ai_label_index(id2label: dict) -> int | None:
    for idx, label in id2label.items():
        if any(hint in str(label).lower() for hint in _AI_LABEL_HINTS):
            return int(idx)
    return None


def analyze_local(audio_path: str) -> dict:
    """{"verdict": "ai"|"human"|"inconclusive", "score": float|None, "error": str|None, "model": str}"""
    base = {"model": MODEL_ID}
    if not _enabled():
        return {**base, "verdict": "inconclusive", "score": None, "error": "disabled (uncalibrated on phone audio)"}
    try:
        import librosa
        import torch

        extractor, model = _load()
        ai_idx = _ai_label_index(model.config.id2label)
        if ai_idx is None:
            return {**base, "verdict": "inconclusive", "score": None,
                    "error": f"can't find an AI label in {model.config.id2label}"}
        sr = extractor.sampling_rate
        wav, _ = librosa.load(audio_path, sr=sr, mono=True, duration=_MAX_SECONDS)
        inputs = extractor(wav, sampling_rate=sr, return_tensors="pt")
        with torch.no_grad():
            probs = torch.softmax(model(**inputs).logits, dim=-1)[0]
        score = float(probs[ai_idx])
    except Exception as exc:
        log.warning("local detector failed: %s", exc)
        return {**base, "verdict": "inconclusive", "score": None, "error": f"{type(exc).__name__}: {exc}"}

    verdict = "ai" if score >= _ai_above() else "inconclusive"
    return {**base, "verdict": verdict, "score": round(score, 3), "error": None}
