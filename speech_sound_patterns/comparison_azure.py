"""Run the Azure comparison lane over the frozen adult SpeechOcean clips.

This is the only checkpoint 22E4 step that sends audio off this machine, so it
repeats every gate the schema smoke test used and adds the ones this larger
sample needs:

1. the provider register must mark the lane ready and the source eligible;
2. the corpus to provider transfer review must permit this exact pair, at
   version 1.1.0, which is the version that extended the decision to the
   threshold tuning split;
3. the frozen comparison contract must validate and must still say that child
   strata, held-out clips, Australian Common Voice and owner audio are never
   transmitted;
4. every selected clip must be an adult development or tuning clip drawn from
   the frozen expected-only manifest, whose bytes still match its recorded
   hash; and
5. only the audio and the intended reference text may leave. No expert outcome,
   reviewer string, aggregate mispronunciation or speaker identity is ever put
   in a request.

The two locales are different models and are kept strictly apart. Requests are
identical within a locale and repeated twice, with zero numeric tolerance, so a
provider that silently returns different numbers is caught rather than assumed
stable.

    python3 -m speech_sound_patterns.comparison_azure
"""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

from speech_sound_patterns.azure_smoke import (
    INTENDED_TEXT_PATH,
    REQUEST_TIMEOUT_S,
    _assessment_header,
    _endpoint,
    _first_nbest,
    _words,
    intended_texts,
    send_one,
)
from speech_sound_patterns.comparison import (
    ACTIVE_COMPARISON_VERSION,
    PROHIBITED_PROVIDER_SCORES,
    ComparisonError,
    assert_valid_comparison_contract,
    comparison_profile,
    load_expected_manifest,
)
from speech_sound_patterns.external_smoke import (
    load_smoke_contract,
    load_transfer_review,
    transfer_permitted,
    validate_transfer_review,
)
from speech_sound_patterns.feasibility import (
    REPOSITORY_ROOT,
    canonical_json_bytes,
    file_sha256,
)
from speech_sound_patterns.provider_register import audio_permitted, lane_status


LANE_ID = "azure_speech"
SOURCE_ID = "speechocean762"
LOCALES = ("en-AU", "en-US")
ADULT_STRATA = {"source_adult_f", "source_adult_m"}
SAME_INPUT_REPEATS = 2


def default_output(version=ACTIVE_COMPARISON_VERSION):
    return comparison_profile(version)["private_root"] / "evidence" / "azure"

# There is no deadline here. A steady pace is worth more than finishing sooner
# and being throttled, so the checkpoint 22E4 pause is kept for the 8,160 powered
# requests even though the standard tier would allow a faster one. The run is
# resumable, so a slow run costs time and nothing else.
REQUEST_PAUSE_S = 1.0

# A fresh request identifier arrives with every response. It is excluded from
# the repeatability comparison and the exclusion is recorded, so this never
# becomes a general numeric tolerance.
REPEAT_COMPARISON_EXCLUSIONS = ("Id",)


def _load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def check_gates(contract):
    """Raise unless every fail-closed gate permits this transmission."""
    review = load_transfer_review()
    errors = validate_transfer_review(review)
    if errors:
        raise ComparisonError(
            "the corpus to provider transfer review failed validation:\n- "
            + "\n- ".join(errors)
        )
    if review.get("review_version") != contract["external_transmission_policy"][
        "transfer_review_version"
    ]:
        raise ComparisonError(
            "the transfer review on disk is not the version the frozen "
            "comparison contract was written against"
        )
    if lane_status(LANE_ID) != "ready":
        raise ComparisonError(f"lane {LANE_ID!r} is not ready in the provider register")
    if not audio_permitted(LANE_ID, SOURCE_ID):
        raise ComparisonError(
            f"the provider register does not permit sending {SOURCE_ID!r} to "
            f"{LANE_ID!r}"
        )
    if not transfer_permitted(LANE_ID, SOURCE_ID, review):
        raise ComparisonError(
            f"the transfer review does not permit sending {SOURCE_ID!r} to "
            f"{LANE_ID!r}"
        )
    plan_field = TRANSMISSION_PLAN_FIELDS[contract["schema_version"]]
    plan = review.get(plan_field)
    if not plan:
        raise ComparisonError(
            f"the transfer review carries no {plan_field} transmission plan"
        )
    if set(plan["strata"]) != ADULT_STRATA or set(plan["project_splits"]) != {
        "development",
        "threshold_tuning",
    }:
        raise ComparisonError("the transmission plan does not match this run")
    return review, plan


# Each frozen comparison version names its own transmission plan in the corpus
# to provider transfer review, so a larger run can never inherit the permission
# written for a smaller one.
TRANSMISSION_PLAN_FIELDS = {
    "1.0.0": "checkpoint_22e4_transmission_plan",
    "1.1.0": "checkpoint_22e4b_transmission_plan",
}


def select_clips(contract):
    """Return the adult development and tuning clips, label blind.

    Selection reads split, stratum and identifier only. It never reads an
    expert outcome or a model output, so no clip can be chosen because it would
    flatter or embarrass a provider.
    """
    manifest = load_expected_manifest(version=contract["schema_version"])
    policy = contract["external_transmission_policy"]
    permitted_splits = set(policy["permitted_splits"])
    permitted_strata = set(policy["permitted_strata"])
    if permitted_strata & {"source_child_f", "source_child_m"}:
        raise ComparisonError("child strata can never be transmitted")
    clips = [
        clip
        for clip in manifest["clips"]
        if clip["project_split"] in permitted_splits
        and clip["source_stratum"] in permitted_strata
    ]
    if not clips:
        raise ComparisonError("no eligible clip matched the transmission policy")
    if any(clip["source_stratum"] not in ADULT_STRATA for clip in clips):
        raise ComparisonError("a non adult clip reached the transmission set")
    return sorted(clips, key=lambda clip: clip["safe_id"])


def _repeat_comparable(body):
    """Strip only the per request identifier before comparing two responses."""
    if not isinstance(body, dict):
        return body
    return {
        key: value
        for key, value in body.items()
        if key not in REPEAT_COMPARISON_EXCLUSIONS
    }


def _phone_rows(body):
    """Flatten one response into per word, per position phone evidence.

    Nothing is assumed present. A missing field is recorded as missing, and an
    empty phone name stays an empty string rather than being filled in, because
    the Australian locale emits exactly that and a parser that quietly
    substituted something would manufacture a produced phone.
    """
    words = []
    for word_position, word in enumerate(_words(body)):
        phonemes = []
        for phoneme in word.get("Phonemes") or []:
            candidates = [
                {
                    "phoneme": candidate.get("Phoneme"),
                    "score": candidate.get("Score"),
                }
                for candidate in (phoneme.get("NBestPhonemes") or [])
            ]
            phonemes.append(
                {
                    "expected_phoneme": phoneme.get("Phoneme"),
                    "accuracy_score": phoneme.get("AccuracyScore"),
                    "nbest": candidates,
                }
            )
        words.append(
            {
                "word_position": word_position,
                "word": word.get("Word"),
                "error_type": word.get("ErrorType"),
                "phonemes": phonemes,
            }
        )
    return words


def _strip_prohibited(body):
    """Remove the score classes this project may never read.

    Azure returns overall pronunciation, fluency, completeness and prosody
    scores whether or not they are wanted. They are dropped here, at the
    boundary, so they cannot reach a scorer, a report or a reviewer's eye.
    """
    nbest = _first_nbest(body)
    return {
        "recognition_status": body.get("RecognitionStatus"),
        "utterance_accuracy_score": nbest.get("AccuracyScore"),
        "words": _phone_rows(body),
    }


def existing_records(output_root):
    clips_root = Path(output_root) / "clips"
    if not clips_root.is_dir():
        return {}
    records = {}
    for path in sorted(clips_root.glob("*.json")):
        record = _load_json(path)
        records[(record["safe_id"], record["locale"])] = (path, record)
    return records


def verify_existing(records, wanted):
    for (safe_id, locale), (path, record) in records.items():
        clip = wanted.get(safe_id)
        if clip is None:
            raise ComparisonError(f"{safe_id} is not in the transmission set")
        if locale not in LOCALES:
            raise ComparisonError(f"{safe_id}: locale {locale!r} was never approved")
        if record["input_sha256"] != clip["canonical_audio_sha256"]:
            raise ComparisonError(f"{safe_id} audio identity changed")
        if record.get("expert_outcomes_transmitted") is not False:
            raise ComparisonError(f"{safe_id} claims an expert outcome was sent")
        if canonical_json_bytes(record) != path.read_bytes():
            raise ComparisonError(f"{safe_id} record is not canonical")


def run_comparison(
    output_root=None,
    max_new_configurations=None,
    dry_run=False,
    version=ACTIVE_COMPARISON_VERSION,
):
    contract = assert_valid_comparison_contract(version=version)
    profile = comparison_profile(version)
    if output_root is None:
        output_root = default_output(version)
    review, plan = check_gates(contract)
    smoke_contract = load_smoke_contract()
    parameters = smoke_contract["azure_request_policy"]["assessment_parameters"]
    if parameters.get("Granularity") != "Phoneme":
        raise ComparisonError("phoneme granularity is required")
    if smoke_contract["azure_request_policy"]["prosody_assessment_enabled"] is not False:
        raise ComparisonError("prosody assessment is a prohibited output")

    clips = select_clips(contract)
    if len(clips) != plan["clip_count"]:
        raise ComparisonError(
            f"the transmission plan declares {plan['clip_count']} clips but "
            f"{len(clips)} were selected"
        )
    texts = intended_texts(
        [clip["safe_id"] for clip in clips],
        reference_path=(
            profile["sample_root"] / "references" / "speechocean762.json"
        ),
    )

    output_root = Path(output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    summary_path = output_root / "azure-comparison-process.json"
    if summary_path.exists():
        raise ComparisonError("completed Azure comparison evidence already exists")

    wanted = {clip["safe_id"]: clip for clip in clips}
    records = existing_records(output_root)
    verify_existing(records, wanted)
    pending = [
        (clip, locale)
        for clip in clips
        for locale in LOCALES
        if (clip["safe_id"], locale) not in records
    ]
    if dry_run:
        return {
            "status": "dry_run",
            "clips": len(clips),
            "locales": list(LOCALES),
            "requests_per_configuration": SAME_INPUT_REPEATS,
            "planned_requests": len(pending) * SAME_INPUT_REPEATS,
            "already_complete_configurations": len(records),
        }
    if max_new_configurations is not None:
        pending = pending[: max_new_configurations]

    load_dotenv(REPOSITORY_ROOT / ".env")
    key = os.environ.get("AZURE_SPEECH_KEY")
    region = os.environ.get("AZURE_SPEECH_REGION")
    if not key or not region:
        raise ComparisonError(
            "AZURE_SPEECH_KEY and AZURE_SPEECH_REGION must be present in .env"
        )
    if region != "australiaeast":
        raise ComparisonError(
            "the recorded processing region for this lane is australiaeast"
        )

    clips_root = output_root / "clips"
    clips_root.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    started_at = datetime.now(timezone.utc).isoformat()

    for clip, locale in pending:
        audio_path = REPOSITORY_ROOT / clip["canonical_audio_path"]
        if file_sha256(audio_path) != clip["canonical_audio_sha256"]:
            raise ComparisonError(f"audio checksum changed: {clip['safe_id']}")
        audio_bytes = audio_path.read_bytes()
        reference_text = texts[clip["safe_id"]]

        repeats = []
        latencies = []
        for _ in range(SAME_INPUT_REPEATS):
            request_started = time.perf_counter()
            result = send_one(
                session,
                region,
                key,
                locale,
                smoke_contract,
                audio_bytes,
                reference_text,
            )
            latencies.append(round(time.perf_counter() - request_started, 6))
            repeats.append(result)
            time.sleep(REQUEST_PAUSE_S)

        succeeded = [item for item in repeats if item.get("ok")]
        if succeeded:
            comparable = [_repeat_comparable(item["body"]) for item in succeeded]
            exact = all(
                canonical_json_bytes(item) == canonical_json_bytes(comparable[0])
                for item in comparable
            )
            observation = _strip_prohibited(succeeded[0]["body"])
        else:
            exact = None
            observation = None

        record = {
            "safe_id": clip["safe_id"],
            "lane_id": LANE_ID,
            "locale": locale,
            "source_id": SOURCE_ID,
            "project_split": clip["project_split"],
            "source_stratum": clip["source_stratum"],
            "input_sha256": clip["canonical_audio_sha256"],
            "duration_s": clip["duration_s"],
            "requests_sent": len(repeats),
            "requests_succeeded": len(succeeded),
            "status_codes": [item.get("status_code") for item in repeats],
            "failures": [
                item.get("failure") for item in repeats if not item.get("ok")
            ],
            "latency_seconds": latencies,
            "service_date": succeeded[0].get("service_date") if succeeded else None,
            "same_input_repeats_exact": exact,
            "repeat_comparison_exclusions": list(REPEAT_COMPARISON_EXCLUSIONS),
            "expert_outcomes_transmitted": False,
            "speaker_identity_transmitted": False,
            "prohibited_scores_retained": False,
            "observation": observation,
        }
        (clips_root / f"{clip['safe_id']}-{locale}.json").write_bytes(
            canonical_json_bytes(record)
        )

    finished = existing_records(output_root)
    verify_existing(finished, wanted)
    expected_configurations = {
        (clip["safe_id"], locale) for clip in clips for locale in LOCALES
    }
    if set(finished) != expected_configurations:
        return {
            "status": "paused_incomplete",
            "completed_configurations": len(finished),
            "expected_configurations": len(expected_configurations),
        }

    by_locale = {}
    for (safe_id, locale), (_, record) in sorted(finished.items()):
        bucket = by_locale.setdefault(
            locale,
            {
                "locale": locale,
                "clips": 0,
                "requests_sent": 0,
                "requests_succeeded": 0,
                "clips_with_no_successful_request": 0,
                "clips_repeating_exactly": 0,
                "named_phone_positions": 0,
                "total_phone_positions": 0,
                "latency_seconds_total": 0.0,
                "audio_seconds": 0.0,
            },
        )
        bucket["clips"] += 1
        bucket["requests_sent"] += record["requests_sent"]
        bucket["requests_succeeded"] += record["requests_succeeded"]
        bucket["audio_seconds"] += record["duration_s"]
        bucket["latency_seconds_total"] += sum(record["latency_seconds"])
        if not record["requests_succeeded"]:
            bucket["clips_with_no_successful_request"] += 1
        if record["same_input_repeats_exact"]:
            bucket["clips_repeating_exactly"] += 1
        for word in (record["observation"] or {}).get("words", []):
            for phoneme in word["phonemes"]:
                bucket["total_phone_positions"] += 1
                if phoneme["expected_phoneme"]:
                    bucket["named_phone_positions"] += 1

    summary = {
        "summary_id": "azure_comparison_process",
        "schema_version": "1.0.0",
        "checkpoint": contract["checkpoint"],
        "lane_id": LANE_ID,
        "source_id": SOURCE_ID,
        "started": started_at,
        "completed": datetime.now(timezone.utc).isoformat(),
        "region": region,
        "transfer_review_version": review["review_version"],
        "assessment_parameters": dict(parameters),
        "prosody_assessment_enabled": False,
        "transmission": {
            "clip_count": len(clips),
            "locales": list(LOCALES),
            "same_input_repeats": SAME_INPUT_REPEATS,
            "child_clips_transmitted": 0,
            "held_out_clips_transmitted": 0,
            "owner_audio_transmitted": 0,
            "expert_outcomes_transmitted": False,
            "transmitted_fields": ["canonical clip audio", "intended reference text"],
        },
        "locales_pooled": False,
        "prohibited_scores_retained": sorted(PROHIBITED_PROVIDER_SCORES),
        "prohibited_scores_discarded_at_the_boundary": True,
        "by_locale": [
            {
                **value,
                "audio_seconds": round(value["audio_seconds"], 6),
                "mean_latency_seconds": round(
                    value["latency_seconds_total"] / max(value["requests_sent"], 1), 6
                ),
                "latency_seconds_total": round(value["latency_seconds_total"], 6),
            }
            for _, value in sorted(by_locale.items())
        ],
    }
    summary_path.write_bytes(canonical_json_bytes(summary))
    return {
        "status": "complete",
        "summary_path": summary_path.relative_to(REPOSITORY_ROOT).as_posix(),
        "by_locale": summary["by_locale"],
    }


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Send the frozen adult SpeechOcean clips to the Azure comparison "
            "lane in both approved locales."
        )
    )
    parser.add_argument("--output-root", type=Path, default=None)
    parser.add_argument(
        "--comparison-version", default=ACTIVE_COMPARISON_VERSION
    )
    parser.add_argument("--max-new-configurations", type=int, default=None)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="check every gate and report the planned volume without sending",
    )
    arguments = parser.parse_args()
    result = run_comparison(
        output_root=arguments.output_root,
        max_new_configurations=arguments.max_new_configurations,
        dry_run=arguments.dry_run,
        version=arguments.comparison_version,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
