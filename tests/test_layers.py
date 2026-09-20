import pytest

from pipeline import speaker_verification as sv
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
    monkeypatch.setattr("pipeline.stated_name.list_enrolled_names", lambda: [])
    assert extract_stated_name(text) == expected


# --- fuzzy matching against enrolled names (enrolled: "nehal") ---------------------------------------------

@pytest.fixture
def enrolled_nehal(monkeypatch):
    monkeypatch.setattr("pipeline.stated_name.find_enrolled_name_in_text", lambda t: None)
    monkeypatch.setattr("pipeline.stated_name.list_enrolled_names", lambda: ["nehal"])


@pytest.mark.parametrize("text", [
    "Hey, it's Nihal, I've been working on this hackathon project",   # 0.80
    "Hi, this is Neha calling",                                        # 0.89
    "Hey it's Neal, just checking in",                                 # 0.89
    "My name is Nahal and I have a question",                          # 0.80
    "It's Nehla, how are you",                                         # 0.80
    "Nihal here, got a minute?",                                       # trailing "X here"
    "Hey, it's Nayhal so I've been pretty busy",                       # 0.73
    "Hey it's Neil, just calling to check in",                         # 0.67
    "Hey, it's Nihau, I've been working on this hackathon project",    # 0.60 — what STT actually wrote for a spoken "Nihal"
    "Hey, it's Newhole, I've been working on this hackathon project",  # 0.67 — STT's take on a rushed "Nuhal"
    "Hey, it's Neel, I've been working on this hackathon project",     # 0.67 — STT's take on "Neehal"
    "Hey, it's Nehal's phone",                                         # possessive
])
def test_garbled_name_still_maps_to_the_enrolled_contact(enrolled_nehal, text):
    assert extract_stated_name(text) == "nehal"


@pytest.mark.parametrize("text", [
    "it's nearly done, just a moment",            # ordinary word, and lowercase: not a proper noun
    "It's near the bank on Main Street",          # "Near" scores 0.67 but is capitalized only by accident of case
    "so it's half past two already",
    "I'm calling about your car warranty",
    "Hey, it's Robert from the bank",
    "this is Michael calling about your account",
    "Hi, my name is Hannah",
    "it's been a lot of fun",
])
def test_ordinary_words_and_other_names_do_not_map_to_the_enrolled_contact(enrolled_nehal, text):
    assert extract_stated_name(text) != "nehal"


def test_fuzzy_threshold_is_configurable(enrolled_nehal, monkeypatch):
    text = "Hey it's Neil, just checking in"
    assert extract_stated_name(text) == "nehal"           # default 0.6 keeps a 0.67 match
    monkeypatch.setenv("NAME_MATCH_MIN", "0.7")
    assert extract_stated_name(text) == "Neil"            # stricter: falls back to the display name only
    assert extract_stated_name("Hey it's Nihal, hi") == "nehal"  # 0.80 survives 0.7


def test_exact_match_still_wins_and_is_case_insensitive(monkeypatch):
    monkeypatch.setattr("pipeline.stated_name.list_enrolled_names", lambda: ["nehal"])
    monkeypatch.setattr("pipeline.stated_name.find_enrolled_name_in_text", lambda t: "nehal")
    assert extract_stated_name("HEY IT'S NEHAL") == "nehal"
