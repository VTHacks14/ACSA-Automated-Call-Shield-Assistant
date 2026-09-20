"""ElevenLabs speech-to-text wrapper: same signature as before, no network in tests."""

import pytest

from pipeline import transcribe


class FakeResponse:
    def __init__(self, status=200, payload=None, text=""):
        self.status_code, self._payload, self.text = status, payload or {}, text

    def json(self):
        return self._payload


@pytest.fixture
def audio(tmp_path):
    p = tmp_path / "call.wav"
    p.write_bytes(b"RIFF....WAVE")
    return str(p)


@pytest.fixture(autouse=True)
def key(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    monkeypatch.setattr(transcribe.time, "sleep", lambda s: None)


def test_returns_the_stripped_transcript_and_sends_the_expected_request(monkeypatch, audio):
    seen = {}

    def fake_post(url, headers, data, files, timeout):
        seen.update(url=url, headers=headers, data=data, filename=files["file"][0])
        return FakeResponse(200, {"text": "  Hey, it's Nehal.  "})

    monkeypatch.setattr(transcribe.requests, "post", fake_post)
    assert transcribe.transcribe_audio(audio) == "Hey, it's Nehal."
    assert seen["url"] == "https://api.elevenlabs.io/v1/speech-to-text"
    assert seen["headers"] == {"xi-api-key": "test-key"}
    assert seen["data"]["model_id"] == "scribe_v2" and seen["data"]["tag_audio_events"] == "false"
    assert seen["filename"] == "call.wav"


def test_missing_key_raises_without_any_request(monkeypatch, audio):
    monkeypatch.delenv("ELEVENLABS_API_KEY")
    monkeypatch.setattr(transcribe.requests, "post", lambda *a, **k: pytest.fail("must not call the API"))
    with pytest.raises(RuntimeError, match="ELEVENLABS_API_KEY"):
        transcribe.transcribe_audio(audio)


def test_retries_once_on_a_server_error_then_succeeds(monkeypatch, audio):
    replies = iter([FakeResponse(503, text="busy"), FakeResponse(200, {"text": "ok"})])
    monkeypatch.setattr(transcribe.requests, "post", lambda *a, **k: next(replies))
    assert transcribe.transcribe_audio(audio) == "ok"


def test_a_bad_key_fails_immediately_without_retrying(monkeypatch, audio):
    calls = []
    monkeypatch.setattr(transcribe.requests, "post", lambda *a, **k: calls.append(1) or FakeResponse(401, text="invalid key"))
    with pytest.raises(RuntimeError, match="401"):
        transcribe.transcribe_audio(audio)
    assert len(calls) == 1


def test_gives_up_after_the_retry(monkeypatch, audio):
    monkeypatch.setattr(transcribe.requests, "post", lambda *a, **k: FakeResponse(500, text="down"))
    with pytest.raises(RuntimeError, match="500"):
        transcribe.transcribe_audio(audio)


def test_warm_up_is_a_harmless_noop():
    assert transcribe.warm_up() is None
