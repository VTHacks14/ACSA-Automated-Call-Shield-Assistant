"""
Layer 4: Linguistic risk scoring.

Looks for the classic scam-script markers documented in FBI/CrowdStrike
reporting: urgency, isolation ("don't tell anyone"), and unusual payment
requests (gift cards, wire transfers, crypto). Keyword-based on purpose —
it's transparent, fast, and easy to defend under judge questioning.

If you have time left over, swap the keyword lists for a call to an LLM
(feed it the transcript, ask it to score urgency/isolation/payment-request
language on a 0-1 scale) for more nuance — but keyword matching is a
perfectly legitimate, explainable v1.
"""

URGENCY_TERMS = ["right now", "immediately", "emergency", "urgent", "hurry", "asap"]
ISOLATION_TERMS = ["don't tell", "do not tell", "keep this between", "don't call anyone", "secret"]
PAYMENT_TERMS = ["gift card", "wire transfer", "wire the money", "crypto", "bitcoin", "cash app", "venmo"]


def linguistic_risk_score(transcript: str):
    lowered = transcript.lower()
    flags = []

    if any(term in lowered for term in URGENCY_TERMS):
        flags.append("urgency language")
    if any(term in lowered for term in ISOLATION_TERMS):
        flags.append("isolation language")
    if any(term in lowered for term in PAYMENT_TERMS):
        flags.append("unusual payment method")

    # Each category found adds to the risk score; three-for-three is the
    # classic scam-script combination worth calling out explicitly.
    score = len(flags) / 3
    return score, flags
