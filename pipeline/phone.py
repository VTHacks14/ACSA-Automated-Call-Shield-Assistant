"""Phone-number normalization shared by the scam gate and the contact book."""

import re


def normalize_e164(raw) -> str | None:
    """
    Best-effort E.164. Twilio's `From` is already E.164 ("+15405550100"); the FTC
    dataset stores bare 10-digit US numbers. Returns None if it can't be a number.
    """
    if not raw:
        return None
    text = str(raw).strip()
    digits = re.sub(r"\D", "", text)
    if not digits:
        return None
    if text.startswith("+"):
        return "+" + digits if 8 <= len(digits) <= 15 else None
    if len(digits) == 10:
        return "+1" + digits
    if len(digits) == 11 and digits.startswith("1"):
        return "+" + digits
    return None
