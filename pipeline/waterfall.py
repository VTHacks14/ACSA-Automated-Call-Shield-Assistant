"""
The 4-layer waterfall. Pure analysis — no Twilio, no HTTP — so the live call path,
the /demo/analyze fallback and scripts/run_pipeline_on_file.py all share it.

    Layer 1  scam number gate     match            -> AI_SCAM, stop
    (STT)    transcript           not a layer: no score; feeds Layer 2's name + Gemini + the UI
    Layer 2  speaker verification mismatch         -> AI_SCAM, stop   (match does NOT exit)
    Layer 3  local detector       confident AI     -> AI_SCAM, stop   (off by default)
    Layer 4  Gemini               content judgment -> LIKELY_HUMAN or HUMAN_LIKELY_SCAM

Only Layers 1-3 can produce AI_SCAM; only Layer 4 (Gemini) can produce green or yellow.

Transcription runs before Layer 2 because Layer 2 needs the stated name out of the
transcript. It's also why the transcript is available on-screen even when an audio
layer catches the call.
A layer that raises is recorded as an error and skipped — one broken integration
must not take down a live call.
"""

import logging
import time

from pipeline.gemini_reasoning import gemini_final_verdict
from pipeline.local_detector import analyze_local
from pipeline.scam_number_gate import check_scam_number
from pipeline.speaker_verification import verify_speaker
from pipeline.stated_name import extract_stated_name
from pipeline.transcribe import transcribe_audio
from pipeline.verdicts import AI_SCAM

log = logging.getLogger("acsa.waterfall")


def _safe(layers: dict, key: str, fn, *args):
    try:
        layers[key] = fn(*args)
    except Exception as exc:
        log.exception("layer %s crashed", key)
        layers[key] = {"status": "error", "verdict": "inconclusive", "score": None, "error": f"{type(exc).__name__}: {exc}"}
    return layers[key]


def _done(verdict, decided_by, explanation, layers, transcript="", stated_name=None, from_number=None, red_flags=None):
    return {
        "status": "done",
        "timestamp": time.time(),
        "from_number": from_number,
        "transcript": transcript,
        "stated_name": stated_name,
        "verdict": verdict,
        "decided_by": decided_by,
        "explanation": explanation,
        "red_flags": red_flags or [],
        "layers": layers,
    }


def run_waterfall(audio_path: str, from_number: str | None = None, on_transcript=None) -> dict:
    """`on_transcript(text)`, if given, is called as soon as transcription finishes — before the remaining layers
    run — so the UI can show the transcript while analysis is still going."""
    layers: dict = {}

    # Layer 1 — number only, so it runs before any audio work.
    gate = _safe(layers, "scam_number_gate", check_scam_number, from_number)
    if gate.get("status") == "match":
        n = gate.get("report_count")
        return _done(
            AI_SCAM, "scam_number_gate",
            f"This number appears in the FTC's Do Not Call reported-calls data"
            f"{f' ({n} reports)' if n else ''}. Reported isn't the same as proven fraud, "
            "but the call was flagged before any audio was analyzed.",
            layers, from_number=from_number,
        )

    # Speech-to-text (ElevenLabs) — needed for the stated name (Layer 2), the UI, and Gemini.
    try:
        transcript = transcribe_audio(audio_path)
    except Exception:
        log.exception("transcription failed")
        transcript = ""
    if on_transcript is not None and transcript:
        try:
            on_transcript(transcript)
        except Exception:
            log.exception("on_transcript callback failed")  # cosmetic; never let it affect the verdict
    stated_name = extract_stated_name(transcript)

    def done(verdict, decided_by, explanation, **kw):
        return _done(verdict, decided_by, explanation, layers, transcript, kw.pop("stated_name", stated_name),
                     from_number, **kw)

    # Layer 2 — only a confident mismatch exits.
    spk = _safe(layers, "speaker_verification", verify_speaker, audio_path, stated_name)
    if spk.get("status") == "mismatch":
        return done(
            AI_SCAM, "speaker_verification",
            f"The caller said they were {spk.get('name')}, but the voice doesn't match "
            f"{spk.get('name')}'s enrolled voiceprint (similarity {spk.get('similarity')}).",
        )

    # Layer 3 — local detector. Only "ai" exits; disabled unless calibrated (see local_detector.py).
    loc = _safe(layers, "local_detector", analyze_local, audio_path)
    if loc.get("verdict") == "ai":
        return done(
            AI_SCAM, "local_detector",
            f"An AI-voice detector rated this audio {round(loc['score'] * 100)}% likely to be AI-generated.",
        )

    # Layer 4 — Gemini, reached whenever Layers 1-3 didn't exit.
    g = gemini_final_verdict(transcript, layers, stated_name)
    return done(
        g["verdict"], "gemini", g["explanation"],
        stated_name=g.get("stated_name") or stated_name, red_flags=g.get("red_flags"),
    )
