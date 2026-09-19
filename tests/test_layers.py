import pytest

from pipeline import speaker_verification as sv
from pipeline.artifact_detection import classify
from pipeline.phone import normalize_e164
from pipeline.stated_name import extract_stated_name


@pytest.mark.parametrize("cos,expected", [(0.74, "mismatch"), (0.79, "mismatch"), (0.82, "inconclusive"), (0.85, "match"), (0.93, "match")])
def test_speaker_thresholds(monkeypatch, cos, expected):
    monkeypatch.setattr(sv, "_cosine", lambda path, name: cos)
    assert sv.verify_speaker("x.wav", "sarah")["status"] == expected


def test_speaker_without_enrollment_or_name(monkeypatch):
    monkeypatch.setattr(sv, "_cosine", lambda path, name: None)
    assert sv.verify_speaker("x.wav", "nobody")["status"] == "no_enrollment"
    assert sv.verify_speaker("x.wav", None)["status"] == "no_enrollment"


@pytest.mark.parametrize("score,expected", [(0.97, "ai"), (0.85, "ai"), (0.5, "inconclusive"), (0.1, "human"), (0.0, "human")])
def test_sightengine_classification(score, expected):
    assert classify(score) == expected


@pytest.mark.parametrize("raw,expected", [
    ("+15405550100", "+15405550100"), ("(540) 555-0100", "+15405550100"), ("1-540-555-0100", "+15405550100"),
    ("5405550100", "+15405550100"), ("", None), (None, None), ("abc", None), ("12345", None),
])
def test_normalize_e164(raw, expected):
    assert normalize_e164(raw) == expected


@pytest.mark.parametrize("text,expected", [
    ("Hi, my name is Sarah and I need help", "Sarah"),
    ("this is an emergency, please hurry", None),
    ("I'm calling about your car warranty", None),
    ("Hey it's Mike from the bank", "Mike"),
    ("", None),
])
def test_extract_stated_name(monkeypatch, text, expected):
    monkeypatch.setattr("pipeline.stated_name.find_enrolled_name_in_text", lambda t: None)
    assert extract_stated_name(text) == expected
