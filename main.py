"""
VoicePrint Consent — main app.

Flow:
  1. Someone calls your Twilio number.
  2. Twilio POSTs to /voice/incoming -> we respond with TwiML that plays a
     greeting and records their response.
  3. Twilio POSTs to /voice/recording once the recording is done -> we
     download the audio, run the full pipeline, and store the result.
  4. The dashboard (static/dashboard.html) polls /results/latest to show it.

Run:
  uvicorn main:app --reload --port 8000
Then point ngrok at port 8000 and set that URL + "/voice/incoming" as your
Twilio number's "A call comes in" webhook (HTTP POST).
"""

import os
import time
import requests
from fastapi import FastAPI, Request, UploadFile, Form
from fastapi.responses import Response, JSONResponse, FileResponse
from twilio.twiml.voice_response import VoiceResponse

from pipeline.transcribe import transcribe_audio
from pipeline.speaker_verification import enroll_voice, compare_to_enrolled
from pipeline.artifact_detection import artifact_risk_score
from pipeline.linguistic_risk import linguistic_risk_score
from pipeline.fusion import fuse_signals

app = FastAPI()

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

# In-memory store of the latest call result. Fine for a hackathon demo;
# swap for a real DB if you have time left over.
latest_result = {"status": "waiting", "message": "No calls analyzed yet."}


@app.post("/voice/incoming")
async def voice_incoming():
    """Twilio hits this the moment someone calls the number."""
    vr = VoiceResponse()
    vr.say(
        "Hi. This is an automated verification line. "
        "Please say your name, and the reason for your call, after the tone."
    )
    vr.record(
        max_length=20,
        action="/voice/recording",   # Twilio POSTs here when recording finishes
        play_beep=True,
        trim="trim-silence",
    )
    return Response(content=str(vr), media_type="application/xml")


@app.post("/voice/recording")
async def voice_recording(request: Request):
    """Twilio hits this once the caller's response has been recorded."""
    form = await request.form()
    recording_url = form.get("RecordingUrl")  # base URL, needs a format suffix
    call_sid = form.get("CallSid", "unknown")

    global latest_result
    latest_result = {"status": "processing", "call_sid": call_sid}

    audio_path = _download_recording(recording_url, call_sid)
    result = run_pipeline(audio_path)
    result["call_sid"] = call_sid
    latest_result = result

    # Let the caller know screening is done, then hang up.
    vr = VoiceResponse()
    vr.say("Thank you. Your call has been screened.")
    vr.hangup()
    return Response(content=str(vr), media_type="application/xml")


def _download_recording(recording_url: str, call_sid: str) -> str:
    """Twilio recordings need '.wav' appended and require your auth."""
    account_sid = os.environ["TWILIO_ACCOUNT_SID"]
    auth_token = os.environ["TWILIO_AUTH_TOKEN"]
    wav_url = f"{recording_url}.wav"
    resp = requests.get(wav_url, auth=(account_sid, auth_token))
    path = os.path.join(DATA_DIR, f"call_{call_sid}.wav")
    with open(path, "wb") as f:
        f.write(resp.content)
    return path


def run_pipeline(audio_path: str) -> dict:
    """The actual multi-signal analysis. This is the core of the product."""
    transcript = transcribe_audio(audio_path)
    stated_name = extract_stated_name(transcript)  # naive first pass, see transcribe.py

    speaker_score = compare_to_enrolled(audio_path, stated_name)   # 0 = no match, 1 = perfect match, None = no enrollment on file
    artifact_score = artifact_risk_score(audio_path)               # 0 = sounds natural, 1 = looks synthetic
    linguistic_score, flags = linguistic_risk_score(transcript)    # 0 = benign, 1 = classic scam language

    composite = fuse_signals(speaker_score, artifact_score, linguistic_score)

    return {
        "status": "done",
        "timestamp": time.time(),
        "transcript": transcript,
        "stated_name": stated_name,
        "speaker_match_score": speaker_score,
        "artifact_risk_score": artifact_score,
        "linguistic_risk_score": linguistic_score,
        "linguistic_flags": flags,
        "composite_risk": composite["score"],
        "verdict": composite["verdict"],
        "explanation": composite["explanation"],
    }


def extract_stated_name(transcript: str) -> str:
    """
    Extremely naive placeholder: looks for 'this is <name>' or 'my name is <name>'.
    Swap this for a small LLM call (feed the transcript, ask it to extract the
    stated name) once the rest of the pipeline is working end to end —
    that'll be far more robust than string matching.
    """
    lowered = transcript.lower()
    for marker in ["my name is ", "this is "]:
        if marker in lowered:
            after = lowered.split(marker, 1)[1]
            return after.split(".")[0].split(",")[0].strip().split(" ")[0].capitalize()
    return "unknown"


@app.get("/results/latest")
async def get_latest_result():
    return JSONResponse(latest_result)


@app.post("/enroll")
async def enroll(name: str = Form(...), audio: UploadFile = None):
    """
    Upload a short (10-30s) clean reference clip of a real person's voice.
    curl -F "name=Sarah" -F "audio=@sarah_sample.wav" http://localhost:8000/enroll
    """
    save_path = os.path.join(DATA_DIR, f"enroll_{name.lower()}.wav")
    with open(save_path, "wb") as f:
        f.write(await audio.read())
    enroll_voice(name, save_path)
    return {"status": "enrolled", "name": name}


@app.get("/")
async def dashboard():
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", "dashboard.html"))
