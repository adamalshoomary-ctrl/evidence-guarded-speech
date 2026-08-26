"""Check whether the empty Australian phone names are a calling mistake.

Checkpoint 22E3 found that Azure `en-AU` returns phone name fields as empty
strings. That was observed with the IPA alphabet only, which leaves an obvious
objection open: perhaps the call was wrong rather than the locale limited.

This probe answers that objection empirically instead of by argument. It sends
one permitted public corpus clip under several alphabet and locale settings and
reports which combinations name a phone. It uses corpus audio, never owner
audio, because this is a schema question rather than a speaker question.

Run with::

    python3 -m speech_sound_patterns.azure_locale_probe
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone

from dotenv import load_dotenv

from speech_sound_patterns.azure_smoke import (
    LANE_ID,
    PRIVATE_OUTPUT_ROOT,
    SOURCE_ID,
    _phonemes,
    _words,
    check_gates,
    intended_texts,
    select_clips,
)
from speech_sound_patterns.external_smoke import (
    load_smoke_contract,
    load_transfer_review,
)
from speech_sound_patterns.feasibility import REPOSITORY_ROOT, canonical_json_bytes


# Each variant changes exactly one thing, so a difference can be attributed.
VARIANTS = (
    {"variant_id": "en_au_ipa", "locale": "en-AU", "alphabet": "IPA"},
    {"variant_id": "en_au_sapi", "locale": "en-AU", "alphabet": "SAPI"},
    {"variant_id": "en_au_default", "locale": "en-AU", "alphabet": None},
    {"variant_id": "en_gb_ipa", "locale": "en-GB", "alphabet": "IPA"},
    {"variant_id": "en_us_sapi", "locale": "en-US", "alphabet": "SAPI"},
    {"variant_id": "en_us_ipa", "locale": "en-US", "alphabet": "IPA"},
)


def _observe(body):
    phonemes = _phonemes(body)
    candidates = [
        candidate
        for phoneme in phonemes
        for candidate in (phoneme.get("NBestPhonemes") or [])
    ]
    syllables = [
        syllable for word in _words(body) for syllable in (word.get("Syllables") or [])
    ]
    named = [item for item in phonemes if item.get("Phoneme")]
    return {
        "phoneme_positions": len(phonemes),
        "named_phonemes": len(named),
        "example_names": [item["Phoneme"] for item in named[:6]],
        "candidate_positions": len(candidates),
        "named_candidates": sum(1 for item in candidates if item.get("Phoneme")),
        "syllables": len(syllables),
        "named_syllables": sum(1 for item in syllables if item.get("Syllable")),
        "scores_present": all("AccuracyScore" in item for item in phonemes)
        and bool(phonemes),
    }


def run(argv=None):
    import requests

    load_dotenv(REPOSITORY_ROOT / ".env")
    contract = load_smoke_contract()
    review = load_transfer_review()
    check_gates(contract, review)

    clip = select_clips(contract)[0]
    reference_text = intended_texts([clip["safe_id"]])[clip["safe_id"]]
    audio = (REPOSITORY_ROOT / clip["canonical_audio_path"]).read_bytes()

    region = os.environ.get("AZURE_SPEECH_REGION")
    key = os.environ.get("AZURE_SPEECH_KEY")
    if not region or not key:
        raise SystemExit("AZURE_SPEECH_REGION and AZURE_SPEECH_KEY must be set")

    import base64

    session = requests.Session()
    observations = []
    for variant in VARIANTS:
        parameters = {
            "ReferenceText": reference_text,
            "GradingSystem": "HundredMark",
            "Granularity": "Phoneme",
            "Dimension": "Comprehensive",
            "EnableMiscue": "True",
            "NBestPhonemeCount": 5,
        }
        if variant["alphabet"]:
            parameters["PhonemeAlphabet"] = variant["alphabet"]

        response = session.post(
            f"https://{region}.stt.speech.microsoft.com"
            "/speech/recognition/conversation/cognitiveservices/v1"
            f"?language={variant['locale']}&format=detailed",
            headers={
                "Ocp-Apim-Subscription-Key": key,
                "Content-type": "audio/wav; codecs=audio/pcm; samplerate=16000",
                "Accept": "application/json",
                "Pronunciation-Assessment": base64.b64encode(
                    json.dumps(parameters, ensure_ascii=False).encode("utf-8")
                ).decode("ascii"),
            },
            data=audio,
            timeout=60,
        )
        record = {**variant, "status_code": response.status_code}
        if response.status_code == 200:
            record.update(_observe(response.json()))
        else:
            record["failure"] = response.text[:200]
        observations.append(record)
        print(
            f"  {variant['variant_id']:16s} http={record['status_code']} "
            f"named_phonemes={record.get('named_phonemes')} "
            f"of {record.get('phoneme_positions')} "
            f"examples={record.get('example_names')}"
        )
        time.sleep(3.5)

    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    PRIVATE_OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    path = PRIVATE_OUTPUT_ROOT / f"locale-probe-{started.replace(':', '')}.json"
    path.write_bytes(
        canonical_json_bytes(
            {
                "started": started,
                "lane_id": LANE_ID,
                "source_id": SOURCE_ID,
                "clip": clip["safe_id"],
                "observations": observations,
            }
        )
    )
    print(f"retained privately at {path}")
    return 0


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(run())
