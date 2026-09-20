"""
Run the full waterfall directly on a saved recording — no Twilio, no server.

Two uses:
  * the fallback demo path if live telephony breaks during judging
  * a smoke test: shows exactly what every layer returned (check the Layer 3 score here)

    python scripts/run_pipeline_on_file.py data/call_CA....wav [--from +15405550100]

Each run sends the audio to ElevenLabs for transcription (credits) and, if no layer exits first, the
transcript to Gemini — don't loop this.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from pipeline.waterfall import run_waterfall

parser = argparse.ArgumentParser()
parser.add_argument("audio")
parser.add_argument("--from", dest="from_number", help="caller number to use for the Layer 1 lookup")
args = parser.parse_args()

result = run_waterfall(args.audio, args.from_number)
print(json.dumps(result, indent=2, default=str))
print(f"\n=> {result['verdict']} (decided by {result['decided_by']})")
