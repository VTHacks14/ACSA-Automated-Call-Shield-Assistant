"""
Layer 3: AI-vs-human audio classification via Sightengine's AI Voice Detector
(POST /1.0/audio/check.json, models=ai_speech; ~55 voice generators).

`artifact_risk_score(audio_path) -> float` keeps its original signature (0 = sounds
human, 1 = looks synthetic) for anything that already imports it. The waterfall
uses `analyze_artifact()`, which adds the confident-AI / confident-human /
inconclusive call the early-exit logic needs.

Only "ai" can end a call (-> AI_SCAM). "human" and "inconclusive" both proceed:
a real human can still be reading a scam script, so that's Gemini's call.

Free tier: 2,000 ops/month, 500/day — don't loop this over test files.
"""

import logging
import os

import requests

log = logging.getLogger("acsa.sightengine")

ENDPOINT = "https://api.sightengine.com/1.0/audio/check.json"


def _ai_above() -> float:
    return float(os.getenv("SIGHTENGINE_AI_ABOVE", "0.85"))


def _human_below() -> float:
    return float(os.getenv("SIGHTENGINE_HUMAN_BELOW", "0.15"))


def classify(score: float) -> str:
    if score >= _ai_above():
        return "ai"
    if score <= _human_below():
        return "human"
    return "inconclusive"


def analyze_artifact(audio_path: str) -> dict:
    """{"verdict": "ai"|"human"|"inconclusive", "score": float|None, "error": str|None}"""
    user, secret = os.getenv("SIGHTENGINE_API_USER"), os.getenv("SIGHTENGINE_API_SECRET")
    if not user or not secret:
        return {"verdict": "inconclusive", "score": None, "error": "SIGHTENGINE_API_USER/SECRET not set"}
    try:
        with open(audio_path, "rb") as f:
            resp = requests.post(
                ENDPOINT,
                files={"audio": f},
                data={"models": "ai_speech", "api_user": user, "api_secret": secret},
                timeout=25,
            )
        body = resp.json()
    except Exception as exc:  # network, timeout, bad JSON — never take the call down
        log.warning("Sightengine request failed: %s", exc)
        return {"verdict": "inconclusive", "score": None, "error": f"request failed: {type(exc).__name__}"}

    if body.get("status") != "success":
        message = (body.get("error") or {}).get("message", "unknown error")
        log.warning("Sightengine error: %s", message)
        return {"verdict": "inconclusive", "score": None, "error": message}

    score = float(body["type"]["ai_speech"])
    return {"verdict": classify(score), "score": round(score, 3), "error": None}


def artifact_risk_score(audio_path: str) -> float:
    """0 = sounds human, 1 = looks synthetic. Returns a neutral 0.5 if the API is unavailable."""
    score = analyze_artifact(audio_path)["score"]
    return 0.5 if score is None else score
