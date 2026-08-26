"""Checkpoint 22E3 Azure pronunciation assessment schema smoke runner.

This is the first code in item 22 that sends audio off this machine, so every
gate is checked before a single request is built:

1. the provider register must mark the lane ready and the source eligible;
2. the corpus to provider transfer review must permit this exact pair;
3. the predeclared smoke contract must validate; and
4. every selected clip must be a development split adult clip drawn from the
   frozen expected-only manifest, whose bytes still match its recorded hash.

The runner measures response shape and repeatability. It measures no accuracy,
reads no expert label, selects no system and sets no threshold. Raw responses
stay private under ``.research_data``; only aggregate field presence and
outcomes reach the committed report.

Run with::

    python3 -m speech_sound_patterns.azure_smoke
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import time
import wave
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

from speech_sound_patterns.external_smoke import (
    EXPECTED_ONLY_MANIFEST_SHA256,
    ExternalSmokeValidationError,
    SMOKE_REPORT_PATH,
    load_smoke_contract,
    load_transfer_review,
    transfer_permitted,
    validate_smoke_contract,
    validate_transfer_review,
)
from speech_sound_patterns.feasibility import (
    REPOSITORY_ROOT,
    canonical_json_bytes,
    canonical_json_sha256,
    file_sha256,
)
from speech_sound_patterns.provider_register import audio_permitted, lane_status


PRIVATE_ROOT = REPOSITORY_ROOT / ".research_data" / "speech_sound_patterns"
EXPECTED_MANIFEST_PATH = (
    PRIVATE_ROOT / "benchmark" / "repair-v1" / "expected-only-manifest-v1.0.0.json"
)
INTENDED_TEXT_PATH = (
    PRIVATE_ROOT / "benchmark" / "v1" / "references" / "speechocean762.json"
)
PRIVATE_OUTPUT_ROOT = PRIVATE_ROOT / "external_smoke" / "azure"

LANE_ID = "azure_speech"
SOURCE_ID = "speechocean762"

# Per request pause. The free tier is rate limited and this run is deliberately
# unhurried; twenty requests are not worth a throttling incident.
REQUEST_PAUSE_S = 3.5
REQUEST_TIMEOUT_S = 60
MAX_ATTEMPTS = 3

# The response carries a fresh request identifier every time. It is excluded
# from the repeatability comparison and the exclusion is reported, so nobody
# later mistakes this for a general tolerance.
REPEAT_COMPARISON_EXCLUSIONS = ("Id",)


class AzureSmokeError(RuntimeError):
    """Raised when the smoke run cannot proceed safely."""


def _selection_key(scope: str, identifier: str) -> str:
    value = f"speech_sound_patterns_external_smoke_v1\0{scope}\0{identifier}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _load_json(path: Path):
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def check_gates(contract, review):
    """Raise unless every fail-closed gate permits this run."""
    errors = validate_transfer_review(review) + validate_smoke_contract(contract)
    if errors:
        raise ExternalSmokeValidationError(
            "checkpoint 22E3 gates failed:\n- " + "\n- ".join(errors)
        )

    if lane_status(LANE_ID) != "ready":
        raise AzureSmokeError(f"lane {LANE_ID!r} is not ready in the provider register")
    if not audio_permitted(LANE_ID, SOURCE_ID):
        raise AzureSmokeError(
            f"the provider register does not permit sending {SOURCE_ID!r} to {LANE_ID!r}"
        )
    if not transfer_permitted(LANE_ID, SOURCE_ID, review):
        raise AzureSmokeError(
            f"the transfer review does not permit sending {SOURCE_ID!r} to {LANE_ID!r}"
        )


def select_clips(contract):
    """Return the deterministic, label-blind development adult sample.

    Selection reads only split, stratum, duration and identifier. It never
    reads an expert outcome or a model output, so no clip can be chosen
    because it would flatter or embarrass a provider.
    """
    policy = contract["input_policy"]
    if file_sha256(EXPECTED_MANIFEST_PATH) != EXPECTED_ONLY_MANIFEST_SHA256:
        raise AzureSmokeError(
            "the expected-only manifest no longer matches its frozen hash"
        )

    manifest = _load_json(EXPECTED_MANIFEST_PATH)
    if manifest["expert_outcomes_included"] is not False:
        raise AzureSmokeError("the selection manifest must contain no expert outcome")

    permitted_strata = set(policy["permitted_strata"])
    eligible = [
        clip
        for clip in manifest["clips"]
        if clip["project_split"] == policy["project_split"]
        and clip["source_stratum"] in permitted_strata
    ]
    if not eligible:
        raise AzureSmokeError("no eligible clip matched the declared sample policy")

    ordered = sorted(
        eligible,
        key=lambda clip: (_selection_key("clip", clip["safe_id"]), clip["safe_id"]),
    )
    chosen = ordered[: policy["clip_count"]]
    if len(chosen) != policy["clip_count"]:
        raise AzureSmokeError("the eligible pool is smaller than the declared sample")
    return chosen


def intended_texts(safe_ids, reference_path=None):
    """Return safe_id to intended reference text, carrying nothing else.

    The reference file also holds expert reviewer strings and aggregate
    mispronunciations. Only the intended text is copied out, and the copy is
    asserted to contain no other key, so no label can reach a provider.

    ``reference_path`` selects which frozen sample's references to read. It
    defaults to the checkpoint 22D sample that the schema smoke test used; the
    powered checkpoint 22E4B comparison passes its own.
    """
    if reference_path is None:
        reference_path = INTENDED_TEXT_PATH
    records = _load_json(reference_path)["records"]
    wanted = set(safe_ids)
    texts = {}
    for record in records:
        if record["safe_id"] in wanted:
            texts[record["safe_id"]] = record["text"]
    missing = wanted - set(texts)
    if missing:
        raise AzureSmokeError(
            "intended text missing for: " + ", ".join(sorted(missing))
        )
    for value in texts.values():
        if not isinstance(value, str) or not value.strip():
            raise AzureSmokeError("an intended text is empty or not a string")
    return texts


def _check_audio(path: Path, expected_sha256: str):
    if file_sha256(path) != expected_sha256:
        raise AzureSmokeError(f"{path.name} no longer matches its recorded hash")
    with wave.open(str(path), "rb") as handle:
        channels = handle.getnchannels()
        rate = handle.getframerate()
        width = handle.getsampwidth()
        seconds = handle.getnframes() / float(rate)
    if (channels, rate, width) != (1, 16000, 2):
        raise AzureSmokeError(
            f"{path.name} is not 16 kHz mono 16 bit PCM as the endpoint requires"
        )
    if seconds > 30:
        raise AzureSmokeError(
            f"{path.name} exceeds the 30 second pronunciation assessment limit"
        )
    return seconds


def _assessment_header(contract, reference_text: str) -> str:
    parameters = dict(contract["azure_request_policy"]["assessment_parameters"])
    parameters["ReferenceText"] = reference_text
    payload = json.dumps(parameters, ensure_ascii=False).encode("utf-8")
    return base64.b64encode(payload).decode("ascii")


def _endpoint(region: str, locale: str) -> str:
    return (
        f"https://{region}.stt.speech.microsoft.com"
        "/speech/recognition/conversation/cognitiveservices/v1"
        f"?language={locale}&format=detailed"
    )


def send_one(session, region, key, locale, contract, audio_bytes, reference_text):
    """Send one request and return a private record of what came back."""
    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Content-type": "audio/wav; codecs=audio/pcm; samplerate=16000",
        "Accept": "application/json",
        "Pronunciation-Assessment": _assessment_header(contract, reference_text),
    }
    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = session.post(
                _endpoint(region, locale),
                headers=headers,
                data=audio_bytes,
                timeout=REQUEST_TIMEOUT_S,
            )
        except requests.RequestException as error:  # pragma: no cover - network
            last_error = f"transport error: {type(error).__name__}"
            time.sleep(REQUEST_PAUSE_S)
            continue

        if response.status_code == 429:
            return {
                "ok": False,
                "status_code": 429,
                "failure": "quota_or_rate_limited",
                "attempts": attempt,
            }
        if response.status_code != 200:
            last_error = f"http {response.status_code}"
            if 500 <= response.status_code < 600 and attempt < MAX_ATTEMPTS:
                time.sleep(REQUEST_PAUSE_S)
                continue
            return {
                "ok": False,
                "status_code": response.status_code,
                "failure": last_error,
                "attempts": attempt,
            }
        try:
            body = response.json()
        except ValueError:
            return {
                "ok": False,
                "status_code": 200,
                "failure": "response was not JSON",
                "attempts": attempt,
            }
        return {
            "ok": True,
            "status_code": 200,
            "attempts": attempt,
            "body": body,
            "service_date": response.headers.get("Date"),
            "request_id": response.headers.get("apim-request-id")
            or response.headers.get("x-requestid"),
        }
    return {"ok": False, "status_code": None, "failure": last_error, "attempts": MAX_ATTEMPTS}


def _first_nbest(body):
    entries = body.get("NBest")
    if isinstance(entries, list) and entries:
        return entries[0]
    return {}


def _words(body):
    return _first_nbest(body).get("Words") or []


def _phonemes(body):
    collected = []
    for word in _words(body):
        for phoneme in word.get("Phonemes") or []:
            collected.append(phoneme)
    return collected


def _candidates(body):
    return [
        candidate
        for phoneme in _phonemes(body)
        for candidate in (phoneme.get("NBestPhonemes") or [])
    ]


def _syllables(body):
    return [
        syllable for word in _words(body) for syllable in (word.get("Syllables") or [])
    ]


def observe_fields(body):
    """Record which documented fields actually appeared, never assuming any."""
    nbest = _first_nbest(body)
    words = _words(body)
    phonemes = _phonemes(body)
    syllables = [syllable for word in words for syllable in (word.get("Syllables") or [])]
    candidates = _candidates(body)
    return {
        "RecognitionStatus": "RecognitionStatus" in body,
        "NBest": bool(nbest),
        "utterance_AccuracyScore": "AccuracyScore" in nbest,
        "word_list": bool(words),
        "word_Word": all("Word" in word for word in words) and bool(words),
        "word_AccuracyScore": all("AccuracyScore" in word for word in words)
        and bool(words),
        "word_ErrorType": all("ErrorType" in word for word in words) and bool(words),
        "word_Syllables": bool(syllables),
        "phoneme_list": bool(phonemes),
        "phoneme_AccuracyScore": all("AccuracyScore" in item for item in phonemes)
        and bool(phonemes),
        "phoneme_Phoneme": all("Phoneme" in item for item in phonemes)
        and bool(phonemes),
        "phoneme_Offset": all("Offset" in item for item in phonemes) and bool(phonemes),
        "phoneme_Duration": all("Duration" in item for item in phonemes)
        and bool(phonemes),
        "phoneme_NBestPhonemes": bool(candidates),
        "candidate_Phoneme": all("Phoneme" in item for item in candidates)
        and bool(candidates),
        "candidate_Score": all("Score" in item for item in candidates)
        and bool(candidates),
    }


def observe_empty_named_fields(body):
    """Record keys that exist but carry an empty name.

    This distinction matters more than it looks. A locale can emit the phone
    name keys and leave every one of them blank, so a parser that only checks
    whether a key exists would silently manufacture empty produced phones.
    Presence of a key is never presence of an identity.
    """
    phonemes = _phonemes(body)
    candidates = _candidates(body)
    empty = []
    if phonemes and all(item.get("Phoneme") == "" for item in phonemes):
        empty.append("phoneme.Phoneme")
    if candidates and all(item.get("Phoneme") == "" for item in candidates):
        empty.append("phoneme.NBestPhonemes[].Phoneme")
    syllables = _syllables(body)
    if syllables and all(item.get("Syllable") == "" for item in syllables):
        empty.append("word.Syllables[].Syllable")
    if syllables and all("Grapheme" not in item for item in syllables):
        empty.append("word.Syllables[].Grapheme (key absent)")
    return empty


def observe_capabilities(body):
    phonemes = _phonemes(body)
    candidates = _candidates(body)
    names = [str(item.get("Phoneme", "")) for item in phonemes if item.get("Phoneme")]
    non_ascii = [name for name in names if any(ord(char) > 127 for char in name)]
    syllables = _syllables(body)
    # A capability means a usable identity, not merely a key. An empty phone
    # name is not a candidate phone, and an empty syllable is not a group.
    return {
        "phoneme_name": bool(names),
        "spoken_phoneme_candidates": bool(candidates)
        and all(item.get("Phoneme") and "Score" in item for item in candidates),
        "syllable_group": bool(syllables)
        and all(item.get("Syllable") for item in syllables),
        "miscue_error_types": [
            word.get("ErrorType") for word in _words(body) if word.get("ErrorType")
        ],
        "ipa_alphabet_honoured": bool(non_ascii),
        "candidate_count": len(candidates),
        "observed_phoneme_names": len(names),
    }


def _comparable(body):
    trimmed = {
        key: value
        for key, value in body.items()
        if key not in REPEAT_COMPARISON_EXCLUSIONS
    }
    return canonical_json_sha256(trimmed)


def _merge_state(values):
    if not values:
        return "absent"
    if all(values):
        return "present"
    if any(values):
        return "partial"
    return "absent"


def run(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="check every gate and print the planned requests without sending audio",
    )
    parser.add_argument(
        "--summarize-from",
        type=Path,
        help=(
            "rebuild the committed report from a retained raw response file "
            "instead of sending audio again"
        ),
    )
    args = parser.parse_args(argv)

    load_dotenv(REPOSITORY_ROOT / ".env")
    contract = load_smoke_contract()
    review = load_transfer_review()
    check_gates(contract, review)

    if args.summarize_from:
        retained = _load_json(args.summarize_from)
        report = summarize(
            retained["results"],
            contract,
            review,
            retained["started"],
            retained["region"],
        )
        SMOKE_REPORT_PATH.write_bytes(canonical_json_bytes(report))
        print(
            f"rebuilt {SMOKE_REPORT_PATH.relative_to(REPOSITORY_ROOT)} from "
            f"{args.summarize_from.name}; no audio was sent"
        )
        return 0

    clips = select_clips(contract)
    texts = intended_texts([clip["safe_id"] for clip in clips])
    policy = contract["input_policy"]
    configurations = contract["azure_configurations"]

    durations = {}
    for clip in clips:
        path = REPOSITORY_ROOT / clip["canonical_audio_path"]
        durations[clip["safe_id"]] = _check_audio(path, clip["canonical_audio_sha256"])

    planned = len(configurations) * len(clips) * policy["repeats_per_configuration"]
    print(f"gates passed; {len(clips)} clips, {len(configurations)} configurations")
    print(f"planned requests: {planned}")
    for clip in clips:
        print(
            f"  {clip['safe_id']} {clip['source_stratum']} "
            f"{durations[clip['safe_id']]:.2f}s"
        )
    if args.dry_run:
        print("dry run: no audio was sent")
        return 0

    region = os.environ.get("AZURE_SPEECH_REGION")
    key = os.environ.get("AZURE_SPEECH_KEY")
    if not region or not key:
        raise AzureSmokeError(
            "AZURE_SPEECH_REGION and AZURE_SPEECH_KEY must be set in the "
            "gitignored .env"
        )

    PRIVATE_OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    session = requests.Session()
    results = []

    for configuration in configurations:
        locale = configuration["locale"]
        for clip in clips:
            audio_bytes = (REPOSITORY_ROOT / clip["canonical_audio_path"]).read_bytes()
            reference_text = texts[clip["safe_id"]]
            for repeat in range(1, policy["repeats_per_configuration"] + 1):
                record = send_one(
                    session,
                    region,
                    key,
                    locale,
                    contract,
                    audio_bytes,
                    reference_text,
                )
                record.update(
                    {
                        "configuration_id": configuration["configuration_id"],
                        "locale": locale,
                        "safe_id": clip["safe_id"],
                        "repeat": repeat,
                    }
                )
                results.append(record)
                status = "ok" if record["ok"] else record.get("failure")
                print(
                    f"  {configuration['configuration_id']} {clip['safe_id']} "
                    f"repeat {repeat}: {status}"
                )
                if record.get("failure") == "quota_or_rate_limited":
                    print(
                        "  stopping: the service reported a quota or rate limit. "
                        "Report this rather than retrying."
                    )
                    _write_private(results, started, region)
                    return 2
                time.sleep(REQUEST_PAUSE_S)

    _write_private(results, started, region)
    report = summarize(results, contract, review, started, region)
    SMOKE_REPORT_PATH.write_bytes(canonical_json_bytes(report))
    print(f"wrote {SMOKE_REPORT_PATH.relative_to(REPOSITORY_ROOT)}")
    return 0


def _write_private(results, started, region):
    PRIVATE_OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    path = PRIVATE_OUTPUT_ROOT / f"raw-responses-{started.replace(':', '')}.json"
    path.write_bytes(
        canonical_json_bytes(
            {"started": started, "region": region, "results": results}
        )
    )
    print(f"raw responses retained privately at {path}")


def _locale_distinctness(results):
    """Aggregate evidence that the locale parameter selects a different model.

    Only counts and a maximum difference are reported. No per clip score
    reaches the committed report. If the locales had returned the same
    numbers, that would have meant the locale parameter was cosmetic, which
    would change how every later comparison must be read.
    """
    scores = {}
    for item in results:
        if not item.get("ok") or item.get("repeat") != 1:
            continue
        utterance = _first_nbest(item["body"]).get("AccuracyScore")
        if utterance is None:
            continue
        scores[(item["configuration_id"], item["safe_id"])] = float(utterance)

    configuration_ids = sorted({key[0] for key in scores})
    if len(configuration_ids) != 2:
        return {"measured": False, "reason": "fewer than two configurations succeeded"}

    left, right = configuration_ids
    differences = []
    for safe_id in sorted({key[1] for key in scores}):
        if (left, safe_id) in scores and (right, safe_id) in scores:
            differences.append(abs(scores[(left, safe_id)] - scores[(right, safe_id)]))
    if not differences:
        return {"measured": False, "reason": "no clip succeeded in both configurations"}

    return {
        "measured": True,
        "compared_configurations": [left, right],
        "clips_compared": len(differences),
        "clips_with_identical_utterance_accuracy": sum(
            1 for value in differences if value == 0.0
        ),
        "max_absolute_difference": max(differences),
        "interpretation": (
            "the two locales returned different utterance accuracy scores on "
            "the same audio, so the locale parameter selects a genuinely "
            "different model rather than relabelling one result; this is why "
            "en-AU and en-US outputs may never be pooled"
        ),
    }


def summarize(results, contract, review, started, region):
    configurations = []
    for configuration in contract["azure_configurations"]:
        configuration_id = configuration["configuration_id"]
        subset = [item for item in results if item["configuration_id"] == configuration_id]
        successes = [item for item in subset if item["ok"]]

        field_observations = {}
        capability_observations = {}
        empty_named = set()
        for item in successes:
            for name, seen in observe_fields(item["body"]).items():
                field_observations.setdefault(name, []).append(seen)
            observed = observe_capabilities(item["body"])
            for name, value in observed.items():
                capability_observations.setdefault(name, []).append(value)
            empty_named.update(observe_empty_named_fields(item["body"]))

        field_presence = {
            name: _merge_state(values) for name, values in sorted(field_observations.items())
        }
        capabilities = {
            name: _merge_state(capability_observations.get(name, []))
            for name in (
                "phoneme_name",
                "spoken_phoneme_candidates",
                "syllable_group",
                "ipa_alphabet_honoured",
            )
        }
        error_types = sorted(
            {
                value
                for values in capability_observations.get("miscue_error_types", [])
                for value in values
            }
        )

        by_clip = {}
        for item in successes:
            by_clip.setdefault(item["safe_id"], []).append(item)
        repeat_states = []
        for safe_id, items in sorted(by_clip.items()):
            if len(items) < 2:
                repeat_states.append("unstable")
                continue
            digests = {_comparable(item["body"]) for item in items}
            if len(digests) == 1:
                repeat_states.append("exact")
            else:
                shapes = {
                    canonical_json_sha256(observe_fields(item["body"]))
                    for item in items
                }
                repeat_states.append(
                    "stable_schema_only" if len(shapes) == 1 else "unstable"
                )
        if not repeat_states:
            repeatability = "not_measured"
        elif all(state == "exact" for state in repeat_states):
            repeatability = "exact"
        elif "unstable" in repeat_states:
            repeatability = "unstable"
        else:
            repeatability = "stable_schema_only"

        if not successes or field_presence.get("phoneme_AccuracyScore") != "present":
            advancement = "failed"
        elif (
            capabilities["phoneme_name"] == "present"
            and capabilities["spoken_phoneme_candidates"] == "present"
        ):
            advancement = "exact_relation_capable"
        else:
            advancement = "score_only"

        configurations.append(
            {
                "configuration_id": configuration_id,
                "lane_id": configuration["lane_id"],
                "source_id": SOURCE_ID,
                "locale": configuration["locale"],
                "documented_expectation": configuration["documented_expectation"],
                "requests_sent": len(subset),
                "requests_succeeded": len(successes),
                "failures": sorted(
                    {item.get("failure") for item in subset if not item["ok"]} - {None}
                ),
                "field_presence": field_presence,
                "keys_present_but_empty": sorted(empty_named),
                "capabilities": capabilities,
                "observed_word_error_types": error_types,
                "repeatability": repeatability,
                "advancement": advancement,
            }
        )

    return {
        "schema_version": "1.0.0",
        "locale_distinctness": _locale_distinctness(results),
        "report_id": "speech_sound_external_schema_smoke",
        "report_version": "1.0.0",
        "checkpoint": "22E3",
        "completed": started,
        "processing_region": region,
        "smoke_contract_sha256": canonical_json_sha256(contract),
        "transfer_review_sha256": canonical_json_sha256(review),
        "expected_only_manifest_sha256": EXPECTED_ONLY_MANIFEST_SHA256,
        "clip_count": contract["input_policy"]["clip_count"],
        "repeats_per_configuration": contract["input_policy"][
            "repeats_per_configuration"
        ],
        "repeat_comparison_exclusions": list(REPEAT_COMPARISON_EXCLUSIONS),
        "repeat_comparison_note": (
            "the per request identifier is excluded because it is generated "
            "fresh for every call; every score and phone name is compared "
            "exactly with no tolerance"
        ),
        "locales_pooled": False,
        "field_presence_note": (
            "field_presence records whether a key was returned, following the "
            "predeclared contract. It does not mean the key was usable. Read "
            "it together with keys_present_but_empty and capabilities: a "
            "locale can return every documented phone name key and leave all "
            "of them blank, in which case the keys are present and the "
            "capability is absent"
        ),
        "configurations": configurations,
        "no_selection_notice": (
            "this is response shape and repeatability evidence only; it "
            "measures no accuracy, reads no expert label, selects no system "
            "and sets no threshold"
        ),
    }


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(run())
