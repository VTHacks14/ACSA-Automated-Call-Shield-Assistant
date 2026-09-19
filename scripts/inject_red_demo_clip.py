"""
Trigger the RED (AI_SCAM) demo case on demand: Number 2 places one outbound call
into Number 1 (ACSA's line) and plays a pre-recorded AI-generated clip via <Play>.

    python scripts/inject_red_demo_clip.py            # uses static/demo/red_clip.mp3
    python scripts/inject_red_demo_clip.py --delay 12 # seconds to wait before the clip starts

Setup (one time, offline, ahead of the event):
  1. Generate the clip (Cartesia, per the plan) and save it as static/demo/red_clip.mp3
     (or .wav). Keep it under ~18 s — ACSA records at most 20 s.
  2. .env needs TWILIO_ACCOUNT_SID/AUTH_TOKEN, TWILIO_NUMBER_1, TWILIO_NUMBER_2, PUBLIC_BASE_URL.
  3. The backend must be running and reachable at PUBLIC_BASE_URL (Twilio fetches the clip from it).

Timing — the one thing to rehearse: when Number 1 is called, ACSA holds the caller until
someone taps Yes in the app (auto-answers after ACSA_ANSWER_TIMEOUT_SECONDS), then plays its
greeting and only then starts recording. The clip must start AFTER the greeting ends, or its
opening is lost. --delay is that wait; the default assumes you tap Yes within a few seconds.

Note: Twilio trial accounts can only call verified numbers and prepend a disclaimer, which
also eats into the delay. Use the upgraded account for the live demo.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse

STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static", "demo")


def need(name: str) -> str:
    value = os.getenv(name)
    if not value:
        sys.exit(f"{name} is not set — add it to .env (see .env.example)")
    return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--clip", default="red_clip.mp3", help="filename inside static/demo/")
    parser.add_argument("--delay", type=int, default=12, help="seconds to pause before playing the clip")
    args = parser.parse_args()

    if not os.path.exists(os.path.join(STATIC_DIR, args.clip)):
        sys.exit(f"static/demo/{args.clip} not found — generate the clip first (see the docstring)")

    base = need("PUBLIC_BASE_URL").rstrip("/")
    vr = VoiceResponse()
    vr.pause(length=args.delay)
    vr.play(f"{base}/static/demo/{args.clip}")
    vr.hangup()

    client = Client(need("TWILIO_ACCOUNT_SID"), need("TWILIO_AUTH_TOKEN"))
    call = client.calls.create(to=need("TWILIO_NUMBER_1"), from_=need("TWILIO_NUMBER_2"), twiml=str(vr))
    print(f"placed call {call.sid}: {os.environ['TWILIO_NUMBER_2']} -> {os.environ['TWILIO_NUMBER_1']}")
    print(f"tap Yes in the app; the clip starts {args.delay}s after the call connects.")


if __name__ == "__main__":
    main()
