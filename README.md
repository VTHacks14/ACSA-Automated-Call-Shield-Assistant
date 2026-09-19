# VoicePrint Consent — Starter Scaffold

## Setup

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

You'll also need:
- A free Twilio account (twilio.com/try-twilio) — buy a phone number (~$1)
- `ngrok` installed (ngrok.com/download)
- Your Twilio Account SID and Auth Token as environment variables:

```bash
export TWILIO_ACCOUNT_SID=xxxx
export TWILIO_AUTH_TOKEN=xxxx
```

## Run it

**1. Start the server:**
```bash
uvicorn main:app --reload --port 8000
```

**2. In another terminal, start the tunnel:**
```bash
ngrok http 8000
```
Copy the `https://xxxx.ngrok.io` URL it gives you.

**3. Configure your Twilio number:**
Go to the Twilio console → Phone Numbers → your number → "A call comes in" → set to:
`https://xxxx.ngrok.io/voice/incoming` (HTTP POST)

**4. Enroll a reference voice** (do this before testing — the speaker
verification layer needs something to compare against):
```bash
curl -F "name=Sarah" -F "audio=@sarah_sample.wav" http://localhost:8000/enroll
```

**5. Open the dashboard:**
Visit `http://localhost:8000` in your browser.

**6. Call your Twilio number** from any phone. Say something like:
*"Hi, this is Sarah, I need help with something urgent."*
Watch the dashboard update after you hang up.

## Notes / known rough edges to fix during the hackathon

- `artifact_detection.py` is a crude heuristic, not a trained classifier —
  swap in a real pretrained deepfake-audio model from Hugging Face
  (search "ASVspoof") if you have time. Right now it's there so the full
  pipeline runs end to end from hour one.
- `extract_stated_name()` in `main.py` is naive string matching. Once the
  rest of the pipeline works, consider replacing it with a small LLM call
  that extracts the name more robustly from the transcript.
- `ngrok`'s free tier gives you a new URL every restart — remember to
  update the Twilio webhook if you restart the tunnel.
- For the actual stage demo, deploy this to a free host (Render, Fly.io,
  Railway) instead of relying on your laptop + ngrok staying connected on
  hackathon Wi-Fi. Keep ngrok as your local dev/testing loop.
- Have a pre-recorded fallback clip ready in case live telephony fails
  during judging — run it through `run_pipeline()` directly as a backup
  demo path.
