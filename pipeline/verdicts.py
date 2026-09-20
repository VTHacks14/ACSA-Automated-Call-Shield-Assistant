"""
The three verdict values the whole system speaks. The iOS gauge and the web
dashboard map colors off these exact strings, so change them in one place only.

AI_SCAM           red    — set only by Layers 1-3 (audio/number-level evidence).
HUMAN_LIKELY_SCAM yellow — set only by Layer 4, Gemini (human voice, scam-script content).
LIKELY_HUMAN      green  — set only by Layer 4, Gemini (human voice, benign content).
"""

AI_SCAM = "AI_SCAM"
HUMAN_LIKELY_SCAM = "HUMAN_LIKELY_SCAM"
LIKELY_HUMAN = "LIKELY_HUMAN"

ALL_VERDICTS = (AI_SCAM, HUMAN_LIKELY_SCAM, LIKELY_HUMAN)
