"""Reject unsupported mental, identity, and health inferences from voice.

Know what this is before trusting it. It is a lexical blocklist: the patterns
below are matched against the serialized structured output, so it catches the
named words and nothing else. It cannot tell an inference from a quotation, a
negation, or a field name, and a paraphrase that never uses a listed word
passes untouched. It is a backstop for the prompt rules in the listener and
evaluator stages, not a substitute for them, and not a guarantee that a
response contains no unsupported inference.
"""

from __future__ import annotations

import json
import re


VOICE_INFERENCE_PATTERNS = {
    "anxiety": r"\b(?:anxious|anxiety)\b",
    "boredom": r"\b(?:bored|boredom)\b",
    "cognitive_load": r"\bcognitive load\b",
    "confidence": r"\b(?:confident|confidence)\b",
    "depression": r"\b(?:depressed|depression)\b",
    "fatigue": r"\b(?:fatigue|fatigued|exhausted|exhaustion|lifeless|tired)\b",
    "gender_identity": r"\b(?:gender|masculine|feminine)\b",
    "mental_state": r"\bmental state\b",
    "monotone": r"\b(?:monotone|monotonicity)\b",
    "nervousness": r"\b(?:nervous|nervousness)\b",
    "personality": r"\bpersonality\b",
    "sincerity": r"\b(?:sincere|sincerity|genuine enjoyment)\b",
    "vocal_health": (
        r"\b(?:vocal damage|vocal damaging|vocal health|voice disorder|"
        r"healthy voice|unhealthy voice|shaky voice)\b"
    ),
    "flat_voice_judgment": r"\bflat (?:voice|tone|prosody|delivery|whisper)\b",
}


def unsupported_voice_inferences(value):
    """Return stable codes for forbidden phrases in structured AI output."""
    text = value if isinstance(value, str) else json.dumps(
        value, ensure_ascii=False, sort_keys=True
    )
    return [
        code for code, pattern in VOICE_INFERENCE_PATTERNS.items()
        if re.search(pattern, text, re.IGNORECASE)
    ]
