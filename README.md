# ACSA — Automated Call Shield Assistant (backend)

FastAPI + Twilio backend for VTHacks 14. A caller is greeted by ACSA, states their name and
reason for calling, and the recording runs a waterfall. Only Layers 1-4 can produce **AI_SCAM**;
only Gemini produces **LIKELY_HUMAN** / **HUMAN_LIKELY_SCAM**. See `ACSA(V1).md` for the design.

```
Layer 1  scam number gate (Atlas / FTC DNC)   match            -> AI_SCAM
Whisper  transcript (feeds Layer 2 + Gemini + the UI)
Layer 2  voiceprint (Resemblyzer)             confident mismatch -> AI_SCAM   (a match does not exit)
Layer 3  Sightengine AI-voice detector        confident AI     -> AI_SCAM
Layer 4  local detector (OFF by default)      confident AI     -> AI_SCAM
Gemini   content judgment                     -> LIKELY_HUMAN | HUMAN_LIKELY_SCAM
```

## Setup

```bash
brew install ffmpeg libsndfile          # system deps for Whisper / librosa
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt         # keeps setuptools<82 on purpose (pkg_resources)
cp .env.example .env                    # then fill in real values; .env is gitignored
```

## Run

```bash
uvicorn main:app --port 8000            # terminal 1
ngrok http 8000                         # terminal 2 -> copy the https URL into PUBLIC_BASE_URL in .env, restart uvicorn
```
Twilio console -> Number 1 -> "A call comes in" -> `https://<ngrok>/voice/incoming` (HTTP POST).
The URL changes every ngrok restart; re-paste it into both Twilio and `.env`.

Web fallback dashboard: `http://localhost:8000`. Tests: `python -m pytest tests`.

## Call flow / API

| Route | Who calls it | What it does |
|---|---|---|
| `POST /voice/incoming` | Twilio | new call -> status `ringing`, caller held on a `<Pause>`/`<Redirect>` loop |
| `POST /call/decision` `{"answer": true}` | iOS app | Yes -> ACSA answers (ElevenLabs greeting, `<Record>`); No -> forward/decline. No answer within `ACSA_ANSWER_TIMEOUT_SECONDS` = auto-answer |
| `POST /voice/recording` | Twilio | download recording, run the waterfall in the background (status `processing`) |
| `GET /results/latest` | app / dashboard | latest call: `status`, `caller_display`, `greeting_text`, `transcript`, `verdict`, `explanation`, `decided_by`, `layers` |
| `POST /enroll` (`name`, `audio`, optional `phone`) | you | register a reference voice |
| `POST /demo/analyze` (`audio`, optional `from_number`) | you | **fallback**: run the waterfall on a saved recording |

Statuses: `waiting` `ringing` `answered` `processing` `done` `declined` `error`.

## Scripts

- `scripts/load_ftc_dnc.py <csv...>` — bulk-load FTC Do Not Call data into Atlas.
- `scripts/run_pipeline_on_file.py <wav> [--from +1...]` — waterfall on a saved file; prints every layer's raw output.
- `scripts/inject_red_demo_clip.py` — Number 2 calls Number 1 and plays `static/demo/red_clip.mp3` (red case).

## Known limitations (be upfront if asked)

- The scam-number gate uses consumer-*reported* numbers, not confirmed fraud.
- A voiceprint *match* is weak evidence (a clone can pass); only a *mismatch* is strong.
- Enroll voices from a sample recorded through the phone line; thresholds are calibrated on 8 kHz audio (see `speaker_verification.py`).
- Layer 4 is off by default: the open-source model false-flagged a live human on phone audio. ElevenLabs has no detection API.
- The iOS app polls (no push) — it must be open and in the foreground.
