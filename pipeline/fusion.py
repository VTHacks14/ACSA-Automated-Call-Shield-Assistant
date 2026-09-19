"""
Layer 5: Fusion — combines the independent signals into one composite score
and a plain-English verdict. This is the layer worth demoing most, because
it's the actual product insight: no single signal is reliable alone, but a
scammer has to defeat all of them simultaneously.

speaker_score: 0 (no match) .. 1 (strong match) .. None (no enrollment found)
artifact_score: 0 (sounds natural) .. 1 (looks synthetic)
linguistic_score: 0 (benign) .. 1 (classic scam script)
"""


def fuse_signals(speaker_score, artifact_score: float, linguistic_score: float) -> dict:
    # If we have no enrolled voice to compare against, don't let a missing
    # signal silently drag the risk score down — just weight around it.
    if speaker_score is None:
        composite = (artifact_score * 0.5) + (linguistic_score * 0.5)
        speaker_note = "No enrolled voice on file for the stated name — relying on audio and language signals only."
    else:
        speaker_mismatch_risk = 1 - speaker_score
        composite = (speaker_mismatch_risk * 0.4) + (artifact_score * 0.3) + (linguistic_score * 0.3)
        speaker_note = (
            f"Voice did not match the enrolled sample (similarity {speaker_score:.2f})."
            if speaker_score < 0.6
            else f"Voice matched the enrolled sample (similarity {speaker_score:.2f})."
        )

    if composite >= 0.65:
        verdict = "HIGH RISK"
    elif composite >= 0.35:
        verdict = "UNCERTAIN"
    else:
        verdict = "LIKELY LEGITIMATE"

    explanation = f"{speaker_note} Audio artifact risk: {artifact_score:.2f}. Linguistic risk: {linguistic_score:.2f}."

    return {"score": round(composite, 2), "verdict": verdict, "explanation": explanation}
