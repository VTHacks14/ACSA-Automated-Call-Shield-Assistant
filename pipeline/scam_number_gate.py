"""
Layer 1: Scam number gate.

Checks the caller's number against the `known_scam_numbers` collection in
MongoDB Atlas, loaded from the FTC's public Do Not Call Reported Calls data
(scripts/load_ftc_dnc.py). A match resolves the call straight to AI_SCAM.

Honest limitation: those numbers are consumer-*reported* as unwanted, not
confirmed fraud. A match means "reported", not "proven".

Fails open on purpose: if Atlas isn't configured or is unreachable we return
status "unavailable" and the waterfall carries on. A database hiccup must never
block (or falsely flag) a live call.

Document shape: {_id: "+15405550100", report_count: int, last_reported: str|None}
"""

import logging
import os

from pipeline.phone import normalize_e164

log = logging.getLogger("acsa.scam_gate")

COLLECTION = "known_scam_numbers"
_client = None


def get_collection():
    """Shared by the loader script. Raises KeyError if MONGODB_URI is unset."""
    global _client
    from pymongo import MongoClient

    if _client is None:
        # Short selection timeout: on hackathon Wi-Fi we'd rather skip the gate than stall the call.
        _client = MongoClient(os.environ["MONGODB_URI"], serverSelectionTimeoutMS=2500)
    return _client[os.getenv("MONGODB_DB", "acsa")][COLLECTION]


def check_scam_number(phone) -> dict:
    number = normalize_e164(phone)
    if not number:
        return {"status": "no_match", "number": None, "detail": "no usable caller number"}
    if not os.getenv("MONGODB_URI"):
        log.warning("MONGODB_URI not set — scam number gate skipped")
        return {"status": "unavailable", "number": number, "detail": "MONGODB_URI not set"}
    try:
        doc = get_collection().find_one({"_id": number})
    except Exception as exc:  # network, auth, timeout — all fail open
        log.warning("scam number gate lookup failed: %s", exc)
        return {"status": "unavailable", "number": number, "detail": f"lookup failed: {type(exc).__name__}"}
    if doc:
        return {
            "status": "match",
            "number": number,
            "report_count": doc.get("report_count"),
            "last_reported": doc.get("last_reported"),
        }
    return {"status": "no_match", "number": number}
