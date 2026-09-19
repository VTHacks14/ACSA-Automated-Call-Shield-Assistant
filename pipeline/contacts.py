"""
Tiny phone-number -> contact-name book, filled by the optional `phone` field on
/enroll. Only used so the iOS ring screen can show "Sarah" instead of a raw
number when an enrolled contact calls. Deliberately not a reverse caller-ID lookup.
"""

import json
import os

from pipeline.phone import normalize_e164

_STORE = os.path.join(os.path.dirname(__file__), "..", "data", "contacts.json")


def _load() -> dict:
    if os.path.exists(_STORE):
        with open(_STORE) as f:
            return json.load(f)
    return {}


def register_contact_number(name: str, phone: str) -> None:
    number = normalize_e164(phone)
    if not number:
        raise ValueError(f"not a valid phone number: {phone!r}")
    store = _load()
    store[number] = name
    os.makedirs(os.path.dirname(_STORE), exist_ok=True)
    with open(_STORE, "w") as f:
        json.dump(store, f)


def lookup_contact_name(phone) -> str | None:
    number = normalize_e164(phone)
    return _load().get(number) if number else None
