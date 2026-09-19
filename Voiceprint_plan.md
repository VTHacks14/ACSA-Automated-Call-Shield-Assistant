# VoicePrint Consent — Project Context

You are helping build "VoicePrint Consent" for VTHacks 14 (a 36-hour hackathon at
Virginia Tech). Read this whole file before making changes — it captures
decisions already made so you don't need to re-litigate them or ask about
things that have already been settled.

## What this product is

A call-screening tool that defends against AI voice-cloning scam calls (e.g.
someone impersonating a family member asking for emergency money). A caller
is greeted by an automated line, asked to state their name and reason for
calling, and the response is run through a multi-signal pipeline that scores
how likely the call is a scam. Explicit design requirement: the solution must
be **entirely technical** — no reliance on a human-shared secret or challenge
question. Defense comes from combining independent signals a scammer would
have to defeat simultaneously.

## Architecture — Model A (do not switch to Model B without discussion)

Two considered approaches were compared. We are committed to Model A:

- **Model A (chosen):** Telephony stays entirely server-side via Twilio.
  Twilio's `<Record>` verb captures the caller's response; a FastAPI backend
  runs the analysis pipeline; a native iOS app is a thin display layer that
  polls the backend and shows a "bubble" UI (Truecaller Assistant-style)
  reacting to what the backend already knows. The iOS app does **not**
  receive real phone calls — it never uses Twilio's Voice SDK, CallKit, or
  PushKit.
- **Model B (rejected):** True live VoIP call routed into the iOS app via
  Twilio Voice Client SDK + CallKit. Rejected as too complex/risky for a
  36-hour build — requires a VoIP Push Certificate, PushKit registration,
  and live audio capture inside the app instead of server-side recording.

**Push notifications are intentionally NOT used.** Real push requires the
paid Apple Developer Program; we are using a free Apple ID (Personal Team).
Instead, the iOS app polls the backend's `/results/latest` endpoint every
1-2 seconds while in the foreground. This is a known, accepted limitation
for the demo (app must be open; won't wake from locked/background) — if
asked by judges, the honest answer is "that's a push-notification
integration away, gated behind the paid developer program we didn't have
time to enroll in this weekend," not something to hide or over-engineer
around right now.

## Backend pipeline — components and status

All files live under a Python/FastAPI project (see actual repo structure).

- `main.py` — FastAPI app. Routes: `/voice/incoming` (Twilio webhook, returns
  TwiML greeting + record), `/voice/recording` (Twilio webhook, receives
  finished recording, runs pipeline), `/results/latest` (polled by iOS app
  and the web dashboard), `/enroll` (register a reference voice sample by
  name). **Status: working, tested end-to-end with real phone calls via
  ngrok tunnel.**
- `pipeline/transcribe.py` — Whisper "base" model, speech-to-text on the
  recorded response. **Status: working.**
- `pipeline/speaker_verification.py` — Resemblyzer voice embeddings; enrolls
  a reference sample per contact name, compares live call audio via cosine
  similarity. **Status: working, tested both match and mismatch cases.**
- `pipeline/linguistic_risk.py` — keyword-based scam-script detector
  (urgency / isolation / unusual-payment-method language). **Status: built,
  not yet stress-tested in combination with other signals.**
- `pipeline/artifact_detection.py` — **currently a crude spectral heuristic
  placeholder (pitch variance + spectral flatness). This needs to be
  replaced with a real call to Sightengine's AI Voice Detector API**
  (detects across 55+ voice generators including Cartesia, which is what
  we're using to generate the demo scam clip; free tier is 2,000
  ops/month, 500/day cap — plenty for hackathon use). Keep the same
  function signature (`artifact_risk_score(audio_path) -> float`) so
  nothing else needs to change when you swap the implementation.
- `pipeline/fusion.py` — combines speaker match, artifact risk, and
  linguistic risk into one composite score + verdict (HIGH RISK / UNCERTAIN
  / LIKELY LEGITIMATE) + plain-English explanation. **Status: working.**
- `static/dashboard.html` — simple polling web dashboard. Working, will be
  superseded by the iOS app for the actual demo but keep it as a fallback.

## iOS app — not yet built

New SwiftUI app. Do NOT fork Twilio's CallKit quickstart — Model A doesn't
need Twilio's Voice SDK on the app side at all. Needs:
1. Three UI states: incoming-call bubble → "Assistant is screening..." →
   color-coded verdict screen. Reuse the same verdict language as the
   backend (HIGH RISK / UNCERTAIN / LIKELY LEGITIMATE) for consistency.
2. A polling loop hitting `/results/latest` every 1-2 seconds while the app
   is foregrounded.
3. Build and run via a free Apple ID (Personal Team) — no push entitlements,
   no paid Apple Developer Program needed for anything in this app.

## Known environment gotchas (already solved once — don't rediscover these)

- On Mac, `brew install ffmpeg libsndfile` is required before `pip install
  -r requirements.txt` (Whisper and librosa need these at the system level).
- `ModuleNotFoundError: No module named 'pkg_resources'` — fix is
  `pip install "setuptools<82"`. Do NOT just `pip install --upgrade
  setuptools`; versions 82+ removed `pkg_resources` entirely and will make
  it worse.
- Twilio's "A call comes in" webhook URL must include the full path
  `/voice/incoming`, not just the bare ngrok URL — a bare root URL produces
  a 405 error that Twilio surfaces as a generic "application error."
- ngrok's free tier gives a new random URL every restart — must re-paste
  the current URL into Twilio's webhook config each session.
- Twilio trial accounts restrict inbound calls to pre-verified caller IDs
  only, and prepend a "trial account" disclaimer to calls. Plan: upgrade
  with a $10-15 balance plus auto-recharge before the live judged demo so
  any judge's phone can call in without pre-verification.

## Remaining build order

1. Swap `artifact_detection.py` to call Sightengine's API for real.
2. Stress-test linguistic risk flags together with a voice mismatch case
   (someone impersonating an enrolled name using scam-script language).
3. Generate the demo scam clip with Cartesia ahead of time (clone a
   teammate's voice with their consent) and test that exact clip against
   Sightengine now, so real detection numbers are known before pitching.
4. Build the iOS app (see above).
5. Full rehearsal on real hackathon Wi-Fi, plus a fallback path that calls
   `run_pipeline()` directly on a saved recording, bypassing Twilio, in
   case live telephony has issues during judging.
6. Commit incrementally throughout, not as one final commit — this is both
   an MLH rules expectation and good practice.

## How to work with me on this

- Don't re-propose Model B, push notifications, or forking Twilio's CallKit
  quickstart — those were considered and explicitly rejected for this
  build; only revisit if the person raises it themselves.
- Keep the artifact-detection function signature stable when replacing its
  internals — other modules depend on it.
- Flag known limitations honestly rather than quietly working around them
  (e.g. the locked/backgrounded-app gap is a known, accepted tradeoff, not
  a bug to silently patch with a hack).
