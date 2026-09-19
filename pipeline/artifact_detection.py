"""
Layer 3: Audio artifact / synthetic-speech detection.

IMPORTANT: this starter version is a crude heuristic, not a trained
deepfake classifier — it's here so the pipeline runs end to end on hour one.
Replace this with a real pretrained model if you have time (search Hugging
Face for models trained on ASVspoof — several are available as drop-in
classifiers that take a wav file and return a spoof-likelihood score).

The heuristic below leans on two real, documented signs of synthetic
speech: unnaturally low pitch variance (real speech has more natural pitch
wobble) and unnaturally high spectral flatness (synthetic audio tends to be
"cleaner"/flatter than real recorded audio, which has more natural noise).
It is NOT reliable on its own — treat it as one weak signal among several,
exactly as the fusion layer does.
"""

import librosa
import numpy as np


def artifact_risk_score(audio_path: str) -> float:
    y, sr = librosa.load(audio_path, sr=None)

    # Pitch variance: very flat/monotone pitch can indicate synthesis.
    pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
    pitch_values = pitches[magnitudes > np.median(magnitudes)]
    pitch_variance = float(np.var(pitch_values)) if len(pitch_values) > 0 else 0.0

    # Spectral flatness: how "noise-like" vs "tone-like" the audio is.
    flatness = float(np.mean(librosa.feature.spectral_flatness(y=y)))

    # Normalize into a 0-1 risk score. These thresholds are rough starting
    # points — tune them against a few real vs. synthetic clips before the
    # actual demo so the numbers aren't meaningless.
    low_pitch_variance_risk = 1.0 if pitch_variance < 500 else 0.3
    high_flatness_risk = min(flatness * 10, 1.0)

    return float(np.clip((low_pitch_variance_risk + high_flatness_risk) / 2, 0, 1))
