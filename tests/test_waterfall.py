"""
Waterfall exit-point tests. Every layer is stubbed, so these check the routing
rules from the design doc, not the vendors:
  - only Layers 1-3 can produce AI_SCAM; only Layer 4 (Gemini) produces green/yellow
  - a voiceprint MATCH never exits early
"""

import pytest

from pipeline import waterfall
from pipeline.verdicts import AI_SCAM, HUMAN_LIKELY_SCAM, LIKELY_HUMAN


@pytest.fixture
def stub(monkeypatch):
    """Default: every layer says 'nothing to see'. Tests override one at a time."""
    calls = []

    def rec(name, value):
        def fn(*a, **k):
            calls.append(name)
            return value
        monkeypatch.setattr(waterfall, name, fn)

    rec("check_scam_number", {"status": "no_match"})
    rec("transcribe_audio", "hi, this is a normal call")
    rec("extract_stated_name", None)
    rec("verify_speaker", {"status": "no_enrollment", "name": None})
    rec("analyze_local", {"verdict": "inconclusive", "score": None, "error": "disabled"})
    rec("gemini_final_verdict", {"verdict": LIKELY_HUMAN, "explanation": "benign", "stated_name": None, "red_flags": []})
    return calls, rec


def test_layer1_match_exits_before_any_audio_work(stub):
    calls, rec = stub
    rec("check_scam_number", {"status": "match", "report_count": 7})
    out = waterfall.run_waterfall("x.wav", "+15405550100")
    assert out["verdict"] == AI_SCAM and out["decided_by"] == "scam_number_gate"
    assert calls == ["check_scam_number"]


def test_transcript_is_published_before_the_remaining_layers_run(stub):
    calls, rec = stub
    seen = []
    rec("verify_speaker", {"status": "no_enrollment", "name": None})
    real_verify = waterfall.verify_speaker
    waterfall.verify_speaker = lambda *a, **k: (seen.append(("layer2", list(seen))), real_verify(*a, **k))[1]
    try:
        waterfall.run_waterfall("x.wav", on_transcript=lambda t: seen.append(("transcript", t)))
    finally:
        waterfall.verify_speaker = real_verify
    assert seen[0] == ("transcript", "hi, this is a normal call")  # first, before Layer 2 ran
    assert seen[1][0] == "layer2"


def test_a_failing_on_transcript_callback_cannot_break_the_verdict(stub):
    def boom(_):
        raise RuntimeError("ui hiccup")
    out = waterfall.run_waterfall("x.wav", on_transcript=boom)
    assert out["verdict"] == LIKELY_HUMAN


def test_layer2_mismatch_exits(stub):
    calls, rec = stub
    rec("extract_stated_name", "sarah")
    rec("verify_speaker", {"status": "mismatch", "name": "sarah", "similarity": 0.41})
    out = waterfall.run_waterfall("x.wav")
    assert out["verdict"] == AI_SCAM and out["decided_by"] == "speaker_verification"
    assert "analyze_local" not in calls and "gemini_final_verdict" not in calls
    assert out["transcript"]  # transcript is still available for the UI


def test_layer2_match_does_not_exit(stub):
    calls, rec = stub
    rec("extract_stated_name", "sarah")
    rec("verify_speaker", {"status": "match", "name": "sarah", "similarity": 0.9})
    out = waterfall.run_waterfall("x.wav")
    assert out["decided_by"] == "gemini" and "analyze_local" in calls


def test_layer4_gemini_can_be_yellow_and_names_the_caller(stub):
    calls, rec = stub
    rec("gemini_final_verdict", {"verdict": HUMAN_LIKELY_SCAM, "explanation": "gift cards", "stated_name": "Bob", "red_flags": ["gift card"]})
    out = waterfall.run_waterfall("x.wav")
    assert out["verdict"] == HUMAN_LIKELY_SCAM and out["decided_by"] == "gemini"
    assert out["stated_name"] == "Bob"


def test_layer3_local_detector_confident_ai_exits(stub):
    calls, rec = stub
    rec("analyze_local", {"verdict": "ai", "score": 0.99, "error": None})
    out = waterfall.run_waterfall("x.wav")
    assert out["verdict"] == AI_SCAM and out["decided_by"] == "local_detector"
    assert "gemini_final_verdict" not in calls


def test_fully_inconclusive_reaches_gemini_and_passes_layer_values(stub, monkeypatch):
    seen = {}

    def fake_gemini(transcript, layers, stated_name):
        seen["layers"] = layers
        return {"verdict": LIKELY_HUMAN, "explanation": "ok", "stated_name": None, "red_flags": []}

    calls, rec = stub
    monkeypatch.setattr(waterfall, "gemini_final_verdict", fake_gemini)
    out = waterfall.run_waterfall("x.wav")
    assert out["verdict"] == LIKELY_HUMAN
    assert {"speaker_verification", "local_detector"} <= set(seen["layers"])
    assert "sightengine" not in seen["layers"]  # removed: no such layer any more


def test_crashing_layer_is_skipped_not_fatal(stub, monkeypatch):
    calls, rec = stub

    def boom(*a, **k):
        raise RuntimeError("vendor down")

    monkeypatch.setattr(waterfall, "analyze_local", boom)
    out = waterfall.run_waterfall("x.wav")
    assert out["decided_by"] == "gemini"
    assert out["layers"]["local_detector"]["status"] == "error"
