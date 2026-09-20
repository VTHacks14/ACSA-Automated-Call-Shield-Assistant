"""The hold loop: Yes answers, No or silence = "busy or unavailable" + hangup. Never auto-answer."""

import pytest
from fastapi.testclient import TestClient

import main

BUSY = "The person you are dialing is busy or unavailable."


@pytest.fixture
def client():
    return TestClient(main.app)  # no context manager: skips the model warm-up in lifespan


def _hold(client, sid):
    return client.post("/voice/hold", data={"CallSid": sid}).text


def _ring(client, sid):
    client.post("/voice/incoming", data={"CallSid": sid, "From": "+15555550100"})


def _assert_busy_hangup(twiml):
    assert BUSY in twiml and "<Say>" in twiml and "<Hangup" in twiml
    assert "<Record" not in twiml and "<Play>" not in twiml and "<Dial" not in twiml


def test_no_tap_within_timeout_is_busy_not_answered(client, monkeypatch):
    monkeypatch.setattr(main, "ANSWER_TIMEOUT", -1)  # every call is already past the timeout
    _ring(client, "CA-timeout")
    _assert_busy_hangup(_hold(client, "CA-timeout"))
    assert main._get("CA-timeout")["status"] == "declined"
    assert main._get("CA-timeout")["decision"] == "no"


def test_tapping_no_is_busy(client):
    _ring(client, "CA-no")
    assert client.post("/call/decision", json={"answer": False, "call_sid": "CA-no"}).status_code == 200
    _assert_busy_hangup(_hold(client, "CA-no"))
    assert main._get("CA-no")["status"] == "declined"


def test_tapping_yes_plays_greeting_then_records(client, monkeypatch):
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://example.test")
    _ring(client, "CA-yes")
    client.post("/call/decision", json={"answer": True, "call_sid": "CA-yes"})
    twiml = _hold(client, "CA-yes")
    assert "<Play>https://example.test/static/acsa_greeting.mp3</Play>" in twiml
    assert "<Record" in twiml and BUSY not in twiml


def test_still_pending_within_timeout_keeps_holding(client, monkeypatch):
    monkeypatch.setattr(main, "ANSWER_TIMEOUT", 3600)
    _ring(client, "CA-wait")
    twiml = _hold(client, "CA-wait")
    assert "<Pause" in twiml and "<Redirect" in twiml
    assert "<Record" not in twiml and BUSY not in twiml
    assert main._get("CA-wait")["decision"] == "pending"
