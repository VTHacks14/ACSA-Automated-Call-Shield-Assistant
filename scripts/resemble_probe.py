"""
Send audio to Resemble Detect with source tracing on, and print the main verdict AND the
separate audio_source_tracing block side by side.

    python scripts/resemble_probe.py "Nehals AI Voice.mp3" [more files...]

Resemble only accepts a public HTTPS URL (or a media_token), so each file is copied into
static/demo/ (gitignored) and fetched through PUBLIC_BASE_URL (the backend + ngrok must be up).
That means the audio is publicly reachable for the length of the run, and it is sent to Resemble.
The copies are removed at the end.

Per Resemble's docs, audio_source_tracing is only returned when the main label is "fake" — if the
main verdict says "real", there will be no platform ID even if the clip came from ElevenLabs.
Costs Resemble credits per file.
"""

import os
import shutil
import sys
import time
import uuid

import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

API = "https://app.resemble.ai/api/v2"
STAGE_DIR = os.path.join(os.path.dirname(__file__), "..", "static", "demo")
POLL_SECONDS, POLL_TIMEOUT = 3, 180


def need(name: str) -> str:
    value = os.getenv(name)
    if not value:
        sys.exit(f"{name} is not set — add it to .env")
    return value


def source_tracing_summary(block) -> str:
    """The docs show two shapes ({label, error_message} and {status, results: [...]}), so accept both."""
    if not block:
        return "absent (Resemble only returns this when the main label is 'fake')"
    results = block.get("results", block)
    if isinstance(results, list):
        results = results[0] if results else {}
    label = results.get("label") if isinstance(results, dict) else None
    parts = [f"label={label!r}", f"status={block.get('status')!r}"]
    error = results.get("error_message") if isinstance(results, dict) else None
    if error:
        parts.append(f"error={error!r}")
    return " ".join(parts) + f"   raw={block}"


def probe(path: str, base: str, headers: dict) -> None:
    os.makedirs(STAGE_DIR, exist_ok=True)
    staged = f"probe_{uuid.uuid4().hex[:8]}{os.path.splitext(path)[1]}"
    shutil.copyfile(path, os.path.join(STAGE_DIR, staged))
    try:
        url = f"{base}/static/demo/{staged}"
        head = requests.head(url, headers={"ngrok-skip-browser-warning": "1"}, timeout=10)
        if head.status_code != 200:
            print(f"{os.path.basename(path)}: staged file not reachable at PUBLIC_BASE_URL (HTTP {head.status_code})")
            return
        resp = requests.post(f"{API}/detect", headers=headers, timeout=30,
                             json={"url": url, "audio_source_tracing": True})
        resp.raise_for_status()
        detect_uuid = resp.json()["item"]["uuid"]
        deadline = time.time() + POLL_TIMEOUT
        while True:
            item = requests.get(f"{API}/detect/{detect_uuid}", headers=headers, timeout=30).json()["item"]
            if item.get("status") in ("completed", "failed") or time.time() > deadline:
                break
            time.sleep(POLL_SECONDS)
    finally:
        os.remove(os.path.join(STAGE_DIR, staged))

    m = item.get("metrics") or {}
    scores = m.get("score") or []
    print(f"\n{os.path.basename(path)}  [{item.get('status')}]")
    print(f"  main verdict : label={m.get('label')!r} aggregated_score={m.get('aggregated_score')} "
          f"consistency={m.get('consistency')} chunks={len(scores)} "
          f"(min {min(map(float, scores), default=None)}, max {max(map(float, scores), default=None)})")
    print(f"  source trace : {source_tracing_summary(item.get('audio_source_tracing'))}")


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    headers = {"Authorization": f"Bearer {need('RESEMBLE_API_KEY')}", "Content-Type": "application/json"}
    base = need("PUBLIC_BASE_URL").rstrip("/")
    for path in sys.argv[1:]:
        probe(path, base, headers)


if __name__ == "__main__":
    main()
