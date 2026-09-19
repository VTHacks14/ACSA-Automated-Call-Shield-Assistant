"""
ACSA — Automated Call Shield Assistant. FastAPI backend.

Model A: telephony stays entirely server-side on Twilio. The iOS app (and the web
dashboard) only poll /results/latest and POST the Yes/No answer decision.

Call lifecycle (status field):
  ringing    /voice/incoming — caller is held on a short <Pause>/<Redirect> loop while
             the app shows "Would you like ACSA to answer for you?"
  answered   user tapped Yes (or the hold timed out) — static/acsa_greeting.mp3 plays, then <Record>
  processing /voice/recording — recording downloaded, waterfall running in the background
             (Twilio's webhook timeout is ~15 s; the pipeline is slower, so never run it inline)
  done       verdict ready; caller hears a goodbye and is hung up on
  declined   user tapped No — call is forwarded or politely declined
  error      recording/pipeline failed

Run:
  uvicorn main:app --port 8000
Then `ngrok http 8000`, set PUBLIC_BASE_URL in .env, and point Twilio Number 1's
"A call comes in" webhook at <ngrok-url>/voice/incoming (HTTP POST).
"""

import logging
import os
import threading
import time
from contextlib import asynccontextmanager

import requests
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from twilio.twiml.voice_response import VoiceResponse

load_dotenv()

from pipeline import greeting as greeting_mod  # noqa: E402  (after load_dotenv so env is set)
from pipeline.contacts import lookup_contact_name, register_contact_number  # noqa: E402
from pipeline.speaker_verification import enroll_voice  # noqa: E402
from pipeline.waterfall import run_waterfall  # noqa: E402

log = logging.getLogger("acsa")
logging.basicConfig(level=logging.INFO)

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
STATIC_DIR = os.path.join(BASE_DIR, "static")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

ANSWER_TIMEOUT = float(os.getenv("ACSA_ANSWER_TIMEOUT_SECONDS", "20"))
PROCESSING_TIMEOUT = 60.0  # stop holding the caller if the pipeline hasn't finished by then

_calls: dict[str, dict] = {}
_latest_sid: str | None = None
_lock = threading.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm the slow stuff now so the first real call isn't the one that pays for it.
    from pipeline import local_detector, transcribe

    threading.Thread(target=lambda: (transcribe.warm_up(), local_detector.warm_up()), daemon=True).start()
    if not greeting_mod.greeting_audio_exists():
        log.warning("static/%s missing — greeting will use Twilio <Say>", greeting_mod.GREETING_FILENAME)
    yield


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ── call state ───────────────────────────────────────────────────────────────

def _new_call(sid: str, from_number: str | None, status: str = "ringing") -> dict:
    global _latest_sid
    name = lookup_contact_name(from_number)
    call = {
        "call_sid": sid,
        "status": status,
        "from_number": from_number,
        "caller_name": name,
        "caller_display": name or from_number or "Unknown caller",
        "decision": "pending",
        "greeting_text": None,
        "ringing_at": time.time(),
        "updated_at": time.time(),
    }
    with _lock:
        _calls[sid] = call
        _latest_sid = sid
    return call


def _update(sid: str, **fields) -> None:
    with _lock:
        if sid in _calls:
            _calls[sid].update(fields, updated_at=time.time())


def _get(sid: str) -> dict | None:
    with _lock:
        call = _calls.get(sid)
        return dict(call) if call else None


def _apply_result(sid: str, result: dict) -> None:
    """Fold a finished waterfall result into the call, upgrading the display name if one was stated."""
    call = _get(sid) or {}
    display = call.get("caller_name") or result.get("stated_name") or call.get("from_number") or "Unknown caller"
    if display.islower():  # enrolled names are stored lowercased; numbers have no case so they pass through
        display = display.title()
    _update(
        sid, status="done", caller_display=display, transcript=result["transcript"],
        stated_name=result["stated_name"], verdict=result["verdict"], decided_by=result["decided_by"],
        explanation=result["explanation"], red_flags=result["red_flags"], layers=result["layers"],
        timestamp=result["timestamp"],
    )


def _xml(vr: VoiceResponse) -> Response:
    return Response(content=str(vr), media_type="application/xml")


def _public_base(request: Request) -> str:
    configured = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
    if configured:
        return configured
    base = str(request.base_url).rstrip("/")
    # ngrok terminates TLS, so the app sees http; Twilio needs https for <Play>.
    return base.replace("http://", "https://") if "localhost" not in base and "127.0.0.1" not in base else base


# ── Twilio webhooks ──────────────────────────────────────────────────────────

@app.post("/voice/incoming")
async def voice_incoming(request: Request):
    form = await request.form()
    sid = form.get("CallSid", f"local-{int(time.time())}")
    _new_call(sid, form.get("From"))
    return _hold_response(sid)


@app.post("/voice/hold")
async def voice_hold(request: Request):
    form = await request.form()
    return _hold_response(form.get("CallSid", ""), _public_base(request))


def _hold_response(sid: str, base: str | None = None) -> Response:
    call = _get(sid)
    if call is None:
        return _hangup("Sorry, something went wrong.")
    decision = call["decision"]
    if decision == "pending" and time.time() - call["ringing_at"] > ANSWER_TIMEOUT:
        # Nobody tapped in time. Auto-answering keeps a judge from sitting on dead air.
        _update(sid, decision="yes")
        decision = "yes"
    if decision == "no":
        return _decline_response(sid)
    if decision == "yes":
        return _answer_response(sid, base)
    vr = VoiceResponse()
    vr.pause(length=1)
    vr.redirect("/voice/hold", method="POST")
    return _xml(vr)


def _answer_response(sid: str, base: str | None) -> Response:
    _update(sid, status="answered", greeting_text=greeting_mod.GREETING_TEXT)
    vr = VoiceResponse()
    if base and greeting_mod.greeting_audio_exists():
        vr.play(f"{base}/static/{greeting_mod.GREETING_FILENAME}")
    else:
        vr.say(greeting_mod.GREETING_TEXT)
    vr.record(max_length=20, timeout=4, action="/voice/recording", play_beep=True, trim="trim-silence")
    return _xml(vr)


def _decline_response(sid: str) -> Response:
    _update(sid, status="declined")
    forward_to = os.getenv("ACSA_FORWARD_TO_NUMBER")
    vr = VoiceResponse()
    if forward_to:
        vr.dial(forward_to)
    else:
        vr.say("The person you're calling isn't available right now. Goodbye.")
        vr.hangup()
    return _xml(vr)


def _hangup(message: str) -> Response:
    vr = VoiceResponse()
    vr.say(message)
    vr.hangup()
    return _xml(vr)


@app.post("/voice/recording")
async def voice_recording(request: Request, background: BackgroundTasks):
    form = await request.form()
    sid = form.get("CallSid", "unknown")
    recording_url = form.get("RecordingUrl")
    if _get(sid) is None:
        _new_call(sid, form.get("From"))
    if not recording_url or form.get("RecordingDuration") == "0":
        _update(sid, status="error", explanation="No speech was recorded.")
        return _hangup("I didn't catch anything. Goodbye.")
    _update(sid, status="processing", processing_started=time.time())
    background.add_task(_process_recording, sid, recording_url)
    return _processing_response(sid)


def _process_recording(sid: str, recording_url: str) -> None:
    call = _get(sid) or {}
    try:
        path = _download_recording(recording_url, sid)
        _apply_result(sid, run_waterfall(path, call.get("from_number")))
    except Exception as exc:
        log.exception("pipeline failed for %s", sid)
        _update(sid, status="error", explanation=f"Analysis failed: {type(exc).__name__}")


@app.post("/voice/processing")
async def voice_processing(request: Request):
    form = await request.form()
    return _processing_response(form.get("CallSid", ""))


def _processing_response(sid: str) -> Response:
    call = _get(sid) or {}
    if call.get("status") in ("done", "error"):
        return _hangup("Thank you. Your call has been screened.")
    if time.time() - call.get("processing_started", time.time()) > PROCESSING_TIMEOUT:
        return _hangup("Thank you. Goodbye.")
    vr = VoiceResponse()
    vr.pause(length=1)
    vr.redirect("/voice/processing", method="POST")
    return _xml(vr)


def _download_recording(recording_url: str, sid: str) -> str:
    """Twilio recordings need '.wav' appended and your auth; the file can lag the webhook by a moment."""
    auth = (os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])
    for attempt in range(4):
        resp = requests.get(f"{recording_url}.wav", auth=auth, timeout=20)
        if resp.status_code == 200:
            break
        time.sleep(1 + attempt)
    else:
        raise RuntimeError(f"recording download failed ({resp.status_code})")
    path = os.path.join(DATA_DIR, f"call_{sid}.wav")
    with open(path, "wb") as f:
        f.write(resp.content)
    return path


# ── app-facing API ───────────────────────────────────────────────────────────

_PUBLIC_FIELDS = (
    "call_sid", "status", "from_number", "caller_name", "caller_display", "greeting_text", "transcript",
    "stated_name", "verdict", "decided_by", "explanation", "red_flags", "layers", "timestamp",
)


def _public(call: dict) -> dict:
    return {k: call[k] for k in _PUBLIC_FIELDS if k in call}


@app.get("/results/latest")
async def get_latest_result():
    with _lock:
        call = dict(_calls[_latest_sid]) if _latest_sid else None
    if call is None:
        return JSONResponse({"status": "waiting", "message": "No calls yet."})
    return JSONResponse(_public(call))


class Decision(BaseModel):
    answer: bool
    call_sid: str | None = None  # defaults to the latest call


@app.post("/call/decision")
async def call_decision(body: Decision):
    """The app's Yes/No bubble. Yes -> ACSA answers; No -> ring through / decline."""
    sid = body.call_sid or _latest_sid
    call = _get(sid) if sid else None
    if call is None:
        raise HTTPException(404, "no such call")
    if call["status"] != "ringing":
        raise HTTPException(409, f"call is already {call['status']}")
    _update(sid, decision="yes" if body.answer else "no")
    return {"call_sid": sid, "decision": "yes" if body.answer else "no"}


@app.post("/enroll")
async def enroll(name: str = Form(...), audio: UploadFile = None, phone: str = Form(None)):
    """
    Upload a short (10-30s) clean reference clip of a real person's voice. Optional `phone`
    lets the ring screen show their name instead of a raw number.
    curl -F "name=Sarah" -F "phone=+15405550100" -F "audio=@sarah_sample.wav" http://localhost:8000/enroll
    """
    if audio is None:
        raise HTTPException(422, "audio file is required")
    save_path = os.path.join(DATA_DIR, f"enroll_{name.lower()}.wav")
    with open(save_path, "wb") as f:
        f.write(await audio.read())
    enroll_voice(name, save_path)
    if phone:
        try:
            register_contact_number(name, phone)
        except ValueError as exc:
            raise HTTPException(422, str(exc))
    return {"status": "enrolled", "name": name}


@app.post("/demo/analyze")
async def demo_analyze(audio: UploadFile, background: BackgroundTasks, from_number: str = Form(None)):
    """
    Fallback path if live telephony fails during judging: run the exact same waterfall on a
    saved recording. Shows up in the app/dashboard as a call that goes straight to processing.
    curl -F "audio=@saved_call.wav" -F "from_number=+15405550100" http://localhost:8000/demo/analyze
    """
    sid = f"demo-{int(time.time() * 1000)}"
    path = os.path.join(DATA_DIR, f"{sid}.wav")
    with open(path, "wb") as f:
        f.write(await audio.read())
    _new_call(sid, from_number, status="processing")
    background.add_task(lambda: _apply_result(sid, run_waterfall(path, from_number)))
    return {"call_sid": sid, "status": "processing"}


@app.get("/")
async def dashboard():
    return FileResponse(os.path.join(STATIC_DIR, "dashboard.html"))
