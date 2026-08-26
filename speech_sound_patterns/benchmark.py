"""Fail-closed, developer-only speech-sound benchmark primitives.

The functions in this module parse source annotations, align declared phone
inventories and calculate transparent engineering metrics.  They do not create
the future ``speech_sound_candidates.json`` artifact and are never called by
the normal pipeline.
"""

from __future__ import annotations

import json
import hashlib
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path

from .feasibility import REPOSITORY_ROOT, canonical_json_bytes, file_sha256


MODULE_ROOT = Path(__file__).parent
BENCHMARK_CONTRACT_PATH = MODULE_ROOT / "benchmark-contract-v1.0.0.json"
PHONE_MAP_PATH = MODULE_ROOT / "benchmark-phone-map-v1.0.0.json"
BENCHMARK_REPORT_PATH = MODULE_ROOT / "local-benchmark-v1.0.0.json"
BENCHMARK_SCHEMA_VERSION = "1.0.0"
FROZEN_BENCHMARK_MANIFEST_SHA256 = (
    "e856b2fef404cd28c9d09c6748797e1c6b888361c83c8d62f47ebf2560e03b98"
)
FROZEN_BENCHMARK_REPORT_SHA256 = (
    "3b3911c3917fe85467a3d4c146b6383dca379a48f07fee281a91f38ddf188a8b"
)
ALLOWED_SPLITS = {"development", "threshold_tuning"}

# How large the private sample is expected to be. Checkpoint 22E4B replicates the
# checkpoint 22D rules on a larger participant sample, so the manifest validator
# takes the expected shape as a parameter. Only the counts move: participant
# exclusivity, the held-out prohibition, safe paths and every other safety check
# below apply identically to both samples.
FROZEN_SAMPLE_EXPECTATION = {
    "sample_id": "checkpoint_22d_frozen_sample",
    "clip_counts": {
        "speechocean762": 480,
        "acted_clear_speech": 25,
        "common_phone_1_0": 30,
        "common_voice_26_australian_english": 30,
    },
    "speechocean_clips_per_participant": 20,
    "speechocean_participants": {
        "development": {
            "source_adult_f": 4,
            "source_adult_m": 4,
            "source_child_f": 4,
            "source_child_m": 4,
        },
        "threshold_tuning": {
            "source_adult_f": 2,
            "source_adult_m": 2,
            "source_child_f": 2,
            "source_child_m": 2,
        },
    },
}
REVIEW_STATES = {
    "reviewer_confirmed_expected_phone",
    "accent_marked_but_not_a_relation_concern",
    "incorrect_or_missed_relation_type_unresolved",
}
NO_RELATION_REVIEW_STATES = {
    "reviewer_confirmed_expected_phone",
    "accent_marked_but_not_a_relation_concern",
}
DECORATIONS = {
    None: "reviewer_confirmed_expected_phone",
    "{": "accent_marked_but_not_a_relation_concern",
    "(": "incorrect_or_missed_relation_type_unresolved",
}
STRESS = re.compile(r"[012]$")
ARPABET = re.compile(r"^[A-Z]+[012]?$")
SAFE_IDENTIFIER = re.compile(r"^[a-z0-9_]+$")
PRIVATE_BENCHMARK_ROOT = (
    REPOSITORY_ROOT / ".research_data" / "speech_sound_patterns" / "benchmark"
)


class BenchmarkValidationError(ValueError):
    """Raised when benchmark evidence would violate the frozen rules."""


def load_benchmark_contract(path=BENCHMARK_CONTRACT_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_phone_map(path=PHONE_MAP_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_benchmark_contract(document):
    """Return safety and semantic errors for the frozen checkpoint 22D rules."""
    errors = []
    required = {
        "schema_version",
        "benchmark_id",
        "status",
        "purpose",
        "release_state",
        "split_policy",
        "sample_policy",
        "truth_classes",
        "expert_label_policy",
        "phone_scope",
        "candidate_system_policy",
        "metrics_policy",
        "report_policy",
        "prohibited_outputs",
    }
    if not isinstance(document, dict):
        return ["benchmark contract must be an object"]
    missing = sorted(required - set(document))
    extra = sorted(set(document) - required)
    if missing:
        errors.append(f"benchmark contract missing fields: {', '.join(missing)}")
    if extra:
        errors.append(f"benchmark contract has unknown fields: {', '.join(extra)}")
    if missing:
        return errors
    if document["schema_version"] != BENCHMARK_SCHEMA_VERSION:
        errors.append("benchmark schema version is unsupported")
    if document["status"] != "rules_frozen_before_development_or_tuning_scoring":
        errors.append("benchmark rules must be frozen before scoring")

    release = document["release_state"]
    expected_release = {
        "engineering_checkpoint": "22D",
        "scientific_release": "locked",
        "product_release": "locked",
        "normal_pipeline_activation": "blocked",
        "candidate_artifact": "not_implemented",
        "paid_provider_comparison": "not_started",
    }
    if release != expected_release:
        errors.append("benchmark release state must remain locked and developer only")

    split = document["split_policy"]
    if set(split.get("allowed_splits", [])) != ALLOWED_SPLITS:
        errors.append("only development and threshold tuning splits are allowed")
    for field in (
        "held_out_evaluation_allowed",
        "selection_uses_labels_or_model_outputs",
        "held_out_result_fields_allowed",
    ):
        if split.get(field) is not False:
            errors.append(f"split_policy.{field} must remain false")
    if split.get("participant_exclusive") is not True:
        errors.append("benchmark participants must remain split exclusive")
    if split.get("final_evaluation_checkpoint") != "22H":
        errors.append("held out evaluation must remain reserved for checkpoint 22H")

    labels = document["expert_label_policy"]
    if labels.get("reviewer_count") != 5:
        errors.append("SpeechOcean evidence must retain five reviewers")
    if labels.get("minimum_matching_reviewers_for_scorable_consensus") != 4:
        errors.append("the conservative four reviewer consensus rule changed")
    for field, expected in {
        "original_reviewer_records_retained": True,
        "reviewer_records_overwritten_by_consensus": False,
        "parenthesis_may_be_forced_to_substitution_or_deletion": False,
        "scalar_scores_are_relation_labels": False,
    }.items():
        if labels.get(field) is not expected:
            errors.append(f"expert_label_policy.{field} must remain {expected}")
    if labels.get("disputed_behavior") != "unscorable":
        errors.append("disputed expert relations must remain unscorable")

    scope = document["phone_scope"]
    if scope.get("included_target_class") != "consonants":
        errors.append("the initial benchmark must remain consonant only")
    if scope.get("unsupported_behavior") != "unscorable":
        errors.append("unsupported phones must remain unscorable")
    alignment = scope.get("alignment", {})
    if alignment.get("algorithm") != "deterministic_unit_cost_levenshtein":
        errors.append("benchmark alignment algorithm changed")
    if alignment.get("weighted_panphon_distance_used") is not False:
        errors.append("weighted PanPhon distance remains prohibited")
    if alignment.get("model_output_is_reference_truth") is not False:
        errors.append("candidate model output cannot become reference truth")

    systems = document["candidate_system_policy"]
    for field in (
        "cross_system_agreement_is_truth",
        "provider_required",
        "network_access_during_local_inference",
        "committed_clip_level_outputs",
    ):
        if systems.get(field) is not False:
            errors.append(f"candidate_system_policy.{field} must remain false")
    if systems.get("phoneticxeus_confidence") != "unavailable":
        errors.append("PhoneticXEUS confidence must remain unavailable")
    if systems.get("mfa_role") != "expected_text_conditioned_timing_only":
        errors.append("MFA must remain timing evidence only")

    metrics = document["metrics_policy"]
    if metrics.get("zero_denominator_behavior") != (
        "null_with_visible_zero_denominator"
    ):
        errors.append("zero metric denominators must remain visible")
    if metrics.get("one_combined_headline_score_allowed") is not False:
        errors.append("one combined benchmark score is prohibited")
    if metrics.get("every_denominator_visible") is not True:
        errors.append("every metric denominator must remain visible")
    if metrics.get("missing_is_zero") is not False:
        errors.append("missing benchmark evidence cannot become zero")

    report = document["report_policy"]
    for field in (
        "private_participant_or_clip_identifier_allowed_in_committed_report",
        "held_out_results_allowed",
        "system_selection_allowed",
        "threshold_selection_allowed",
    ):
        if report.get(field) is not False:
            errors.append(f"report_policy.{field} must remain false")
    for required_output in (
        "speech_sound_candidates.json",
        "coaching",
        "personal_progress",
        "screening",
        "diagnosis",
        "treatment",
    ):
        if required_output not in document["prohibited_outputs"]:
            errors.append(f"prohibited output {required_output} is missing")
    return errors


def validate_phone_map(document):
    errors = []
    required = {
        "schema_version",
        "mapping_id",
        "normalization",
        "reference_inventory",
        "candidate_inventory",
        "reference_phones",
        "declared_equivalents",
        "unsupported_candidate_details",
        "special_nonphones",
        "claims",
    }
    if not isinstance(document, dict):
        return ["benchmark phone map must be an object"]
    missing = sorted(required - set(document))
    extra = sorted(set(document) - required)
    if missing:
        errors.append(f"phone map missing fields: {', '.join(missing)}")
    if extra:
        errors.append(f"phone map has unknown fields: {', '.join(extra)}")
    if missing:
        return errors
    if document["schema_version"] != BENCHMARK_SCHEMA_VERSION:
        errors.append("phone map schema version is unsupported")
    if document["normalization"] != "NFD":
        errors.append("phone map must use NFD normalization")
    phones = document["reference_phones"]
    expected_arpabet = {
        "AA", "AE", "AH", "AO", "AW", "AY", "B", "CH", "D", "DH",
        "EH", "ER", "EY", "F", "G", "HH", "IH", "IY", "JH", "K",
        "L", "M", "N", "NG", "OW", "OY", "P", "R", "S", "SH", "T",
        "TH", "UH", "UW", "V", "W", "Y", "Z", "ZH",
    }
    if set(phones) != expected_arpabet:
        errors.append("phone map does not exactly cover the SpeechOcean inventory")
    for phone, item in phones.items():
        if set(item) != {"ipa", "class", "scorable"}:
            errors.append(f"reference phone {phone} has an invalid shape")
            continue
        if not isinstance(item["ipa"], list) or not item["ipa"]:
            errors.append(f"reference phone {phone} has no IPA mapping")
        for token in item["ipa"]:
            if token != unicodedata.normalize("NFD", token):
                errors.append(f"reference phone {phone} is not NFD normalized")
        if item["class"] not in {"vowel", "diphthong", "consonant"}:
            errors.append(f"reference phone {phone} has an unsupported class")
        if item["class"] != "consonant" and item["scorable"] is not False:
            errors.append(f"nonconsonant reference phone {phone} became scorable")
    equivalents = document["declared_equivalents"]
    unsupported = document["unsupported_candidate_details"]
    if set(equivalents) & set(unsupported):
        errors.append("candidate details cannot be both equivalent and unsupported")
    claims = document["claims"]
    for field in (
        "mapping_is_perceptual_truth",
        "mapping_defines_acceptable_varieties",
        "weighted_feature_distance_used",
    ):
        if claims.get(field) is not False:
            errors.append(f"phone map claim {field} must remain false")
    if claims.get("unknown_candidate_phone_behavior") != "unscorable":
        errors.append("unknown candidate phones must remain unscorable")
    return errors


def assert_valid_benchmark_rules():
    contract = load_benchmark_contract()
    phone_map = load_phone_map()
    errors = validate_benchmark_contract(contract) + validate_phone_map(phone_map)
    if errors:
        raise BenchmarkValidationError("\n".join(errors))
    return contract, phone_map


def canonical_json_sha256(document):
    return hashlib.sha256(canonical_json_bytes(document)).hexdigest()


def _inside_private_benchmark(relative_path, repository_root=REPOSITORY_ROOT):
    if not isinstance(relative_path, str) or not relative_path.startswith(
        ".research_data/speech_sound_patterns/benchmark/"
    ):
        return False
    root = (
        Path(repository_root)
        / ".research_data"
        / "speech_sound_patterns"
        / "benchmark"
    ).resolve()
    path = (Path(repository_root) / relative_path).resolve(strict=False)
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def validate_private_benchmark_manifest(
    document, repository_root=REPOSITORY_ROOT, expectation=None
):
    """Validate the ignored benchmark selection without accepting held-out data.

    ``expectation`` states how many clips and participants the sample should
    hold. It defaults to the frozen checkpoint 22D sample; checkpoint 22E4B
    passes its larger powered sample. Nothing else about this validator changes
    with the sample: a held-out participant, a participant crossing splits, an
    unsafe path or a short participant remains an error either way.
    """
    errors = []
    if expectation is None:
        expectation = FROZEN_SAMPLE_EXPECTATION
    required = {
        "schema_version",
        "protocol_id",
        "selection_seed",
        "benchmark_contract_sha256",
        "phone_map_sha256",
        "held_out_evaluation_accessed",
        "selection_used_labels_or_outputs",
        "sources",
    }
    if not isinstance(document, dict):
        return ["private benchmark manifest must be an object"]
    if set(document) != required:
        return ["private benchmark manifest fields do not match the frozen schema"]
    if document["schema_version"] != BENCHMARK_SCHEMA_VERSION:
        errors.append("private benchmark manifest schema is unsupported")
    if document["protocol_id"] != "speech_sound_patterns_developer_benchmark_v1":
        errors.append("private benchmark protocol id changed")
    contract = load_benchmark_contract()
    phone_map = load_phone_map()
    if document["selection_seed"] != contract["split_policy"]["selection_seed"]:
        errors.append("private benchmark selection seed changed")
    if document["benchmark_contract_sha256"] != canonical_json_sha256(contract):
        errors.append("private benchmark contract identity changed")
    if document["phone_map_sha256"] != canonical_json_sha256(phone_map):
        errors.append("private benchmark phone map identity changed")
    if document["held_out_evaluation_accessed"] is not False:
        errors.append("held out evaluation access is prohibited in checkpoint 22D")
    if document["selection_used_labels_or_outputs"] is not False:
        errors.append("benchmark selection cannot use labels or model outputs")
    sources = document["sources"]
    if not isinstance(sources, list) or len(sources) != 4:
        errors.append("private benchmark must contain exactly four evidence sources")
        return errors
    expected_truth = {
        "speechocean762": "expert_phone_relations",
        "acted_clear_speech": "human_corrected_phone_boundaries",
        "common_phone_1_0": "automatic_forced_alignments",
        "common_voice_26_australian_english": "validated_sentence_audio",
    }
    found_sources = set()
    expected_clip_counts = expectation["clip_counts"]
    for source in sources:
        if not isinstance(source, dict) or set(source) != {
            "source_id",
            "truth_class",
            "private_reference_path",
            "private_reference_sha256",
            "clips",
        }:
            errors.append("private benchmark source has an invalid shape")
            continue
        source_id = source["source_id"]
        if source_id in found_sources:
            errors.append(f"private benchmark source {source_id} is duplicated")
        found_sources.add(source_id)
        if source_id not in expected_truth:
            errors.append(f"private benchmark source {source_id} is not permitted")
            continue
        if source["truth_class"] != expected_truth[source_id]:
            errors.append(f"private benchmark source {source_id} changed truth class")
        if not _inside_private_benchmark(source["private_reference_path"], repository_root):
            errors.append(f"private benchmark source {source_id} reference path is unsafe")
        if not re.fullmatch(r"[0-9a-f]{64}", str(source["private_reference_sha256"])):
            errors.append(f"private benchmark source {source_id} reference hash is invalid")
        clips = source["clips"]
        if not isinstance(clips, list) or len(clips) != expected_clip_counts[source_id]:
            errors.append(f"private benchmark source {source_id} clip count changed")
            continue
        seen_safe_ids = set()
        participant_splits = {}
        for clip in clips:
            required_clip = {
                "safe_id",
                "private_record_id",
                "private_participant_id",
                "project_split",
                "source_stratum",
                "canonical_audio_path",
                "canonical_audio_sha256",
                "duration_s",
                "intended_text_path",
                "intended_text_sha256",
                "reference_record_sha256",
                "eligible_tools",
                "same_clip_local_system_subset",
            }
            if not isinstance(clip, dict) or set(clip) != required_clip:
                errors.append(f"private benchmark source {source_id} clip shape changed")
                continue
            safe_id = clip["safe_id"]
            if not isinstance(safe_id, str) or not SAFE_IDENTIFIER.fullmatch(safe_id):
                errors.append(f"private benchmark source {source_id} safe id is invalid")
            if safe_id in seen_safe_ids:
                errors.append(f"private benchmark source {source_id} safe id repeats")
            seen_safe_ids.add(safe_id)
            split = clip["project_split"]
            if source_id == "acted_clear_speech":
                if split != "fixture":
                    errors.append("Acted Clear benchmark clips must remain fixtures")
            elif split not in ALLOWED_SPLITS:
                errors.append(f"private benchmark source {source_id} includes held out data")
            participant = clip["private_participant_id"]
            prior = participant_splits.setdefault(participant, split)
            if prior != split:
                errors.append(f"private benchmark source {source_id} participant crosses splits")
            for field in ("canonical_audio_path", "intended_text_path"):
                if not _inside_private_benchmark(clip[field], repository_root):
                    errors.append(f"private benchmark source {source_id} {field} is unsafe")
            for field in (
                "canonical_audio_sha256",
                "intended_text_sha256",
                "reference_record_sha256",
            ):
                if not re.fullmatch(r"[0-9a-f]{64}", str(clip[field])):
                    errors.append(f"private benchmark source {source_id} {field} is invalid")
            if not isinstance(clip["duration_s"], (int, float)) or not (
                0 < clip["duration_s"] <= 30
            ):
                errors.append(f"private benchmark source {source_id} duration is invalid")
            if clip["eligible_tools"] != ["mfa", "panphon", "phoneticxeus"]:
                errors.append(f"private benchmark source {source_id} tool eligibility changed")
            if not isinstance(clip["same_clip_local_system_subset"], bool):
                errors.append(f"private benchmark source {source_id} subset flag is invalid")

        if source_id == "speechocean762" and clips:
            participants = {}
            for clip in clips:
                key = (
                    clip.get("project_split"),
                    clip.get("source_stratum"),
                    clip.get("private_participant_id"),
                )
                participants[key] = participants.get(key, 0) + 1
            clips_per_participant = expectation["speechocean_clips_per_participant"]
            if any(count != clips_per_participant for count in participants.values()):
                errors.append(
                    "SpeechOcean selected participants must each contribute "
                    f"{clips_per_participant} clips"
                )
            counts = Counter((split, stratum) for split, stratum, _ in participants)
            expected_participants = expectation["speechocean_participants"]
            if set(expected_participants) != ALLOWED_SPLITS:
                errors.append("SpeechOcean sample expectation must cover both splits")
            for split, per_stratum in sorted(expected_participants.items()):
                if set(per_stratum) != set(
                    contract["sample_policy"]["speechocean762"]["source_strata"]
                ):
                    errors.append(
                        f"SpeechOcean {split} sample expectation strata changed"
                    )
                for stratum, expected_count in sorted(per_stratum.items()):
                    if counts[(split, stratum)] != expected_count:
                        errors.append(
                            f"SpeechOcean {split} stratum {stratum} count changed"
                        )
    if found_sources != set(expected_truth):
        errors.append("private benchmark source set is incomplete")
    all_safe_ids = [
        clip["safe_id"]
        for source in sources
        if isinstance(source, dict)
        for clip in source.get("clips", [])
        if isinstance(clip, dict) and "safe_id" in clip
    ]
    if len(all_safe_ids) != len(set(all_safe_ids)):
        errors.append("private benchmark safe ids repeat across sources")
    return errors


def validate_frozen_private_benchmark_manifest(
    document, expected_sha256, repository_root=REPOSITORY_ROOT, expectation=None
):
    errors = validate_private_benchmark_manifest(
        document, repository_root, expectation
    )
    if canonical_json_sha256(document) != expected_sha256:
        errors.append("private benchmark manifest does not match the frozen identity")
    return errors


def strip_stress(phone):
    if not isinstance(phone, str) or not ARPABET.fullmatch(phone):
        raise BenchmarkValidationError(f"invalid ARPAbet phone: {phone!r}")
    return STRESS.sub("", phone)


def _decorated_token(raw):
    if not raw:
        raise BenchmarkValidationError("empty reviewer phone token")
    opening = raw[0] if raw[0] in "{([" else None
    if opening is None:
        if raw[-1:] in "})]":
            raise BenchmarkValidationError(f"unbalanced reviewer phone token: {raw}")
        inner = raw
    else:
        closing = {"{": "}", "(": ")", "[": "]"}[opening]
        if not raw.endswith(closing) or len(raw) < 3:
            raise BenchmarkValidationError(f"unbalanced reviewer phone token: {raw}")
        inner = raw[1:-1]
        if any(character in inner for character in "{}()[]"):
            raise BenchmarkValidationError(f"nested reviewer phone token: {raw}")
    return opening, strip_stress(inner)


def parse_review_phone_string(reference_phones, annotated):
    """Parse one original SpeechOcean reviewer string without guessing relations."""
    if not isinstance(reference_phones, str) or not reference_phones.strip():
        raise BenchmarkValidationError("reference phone string is empty")
    if not isinstance(annotated, str) or not annotated.strip():
        raise BenchmarkValidationError("reviewer phone string is empty")
    reference = [strip_stress(item) for item in reference_phones.split()]
    targets = []
    insertions = []
    reference_index = 0
    for raw in annotated.split():
        decoration, phone = _decorated_token(raw)
        if decoration == "[":
            insertions.append(
                {
                    "boundary_index": reference_index,
                    "phone": phone,
                    "state": "explicit_inserted_phone",
                }
            )
            continue
        if reference_index >= len(reference):
            raise BenchmarkValidationError("reviewer string has extra target phones")
        expected = reference[reference_index]
        if phone != expected:
            raise BenchmarkValidationError(
                f"reviewer target {phone} does not match reference {expected}"
            )
        targets.append(
            {
                "target_index": reference_index,
                "phone": expected,
                "state": DECORATIONS[decoration],
            }
        )
        reference_index += 1
    if reference_index != len(reference):
        raise BenchmarkValidationError("reviewer string omits undecorated target positions")
    return {"targets": targets, "insertions": insertions}


def target_consensus(states, minimum_reviewers=4):
    if len(states) != 5 or any(item not in REVIEW_STATES for item in states):
        raise BenchmarkValidationError("target consensus requires five valid reviews")
    positive = sum(
        item == "incorrect_or_missed_relation_type_unresolved" for item in states
    )
    negative = sum(item in NO_RELATION_REVIEW_STATES for item in states)
    if positive >= minimum_reviewers:
        decision = "coarse_relation_present"
    elif negative >= minimum_reviewers:
        decision = "no_relation_concern"
    else:
        decision = "disputed_unscorable"
    return {
        "decision": decision,
        "relation_reviews": positive,
        "no_relation_reviews": negative,
        "accent_marked_reviews": sum(
            item == "accent_marked_but_not_a_relation_concern" for item in states
        ),
        "reviewer_count": len(states),
    }


def insertion_consensus(reviewer_insertions, boundary_index, minimum_reviewers=4):
    if len(reviewer_insertions) != 5:
        raise BenchmarkValidationError("insertion consensus requires five reviewers")
    values = []
    for items in reviewer_insertions:
        phones = tuple(
            item["phone"] for item in items if item["boundary_index"] == boundary_index
        )
        values.append(phones)
    counts = Counter(values)
    winner, votes = min(
        counts.items(), key=lambda item: (-item[1], item[0])
    )
    if votes < minimum_reviewers:
        decision = "disputed_unscorable"
    elif not winner:
        decision = "no_insertion"
    else:
        decision = "explicit_insertion_present"
    return {
        "decision": decision,
        "phones": list(winner),
        "matching_reviews": votes,
        "reviewer_count": 5,
    }


def normalize_candidate_token(token, phone_map):
    if not isinstance(token, str) or not token:
        raise BenchmarkValidationError("candidate phone token must be nonempty text")
    token = unicodedata.normalize("NFD", token)
    if token in phone_map["special_nonphones"]:
        return {"raw": token, "normalized": None, "state": "special_nonphone"}
    if token in phone_map["unsupported_candidate_details"]:
        return {"raw": token, "normalized": token, "state": "unsupported_detail"}
    equivalent = phone_map["declared_equivalents"].get(token)
    if equivalent:
        return {
            "raw": token,
            "normalized": equivalent["base"],
            "state": "declared_equivalent",
        }
    return {"raw": token, "normalized": token, "state": "identity"}


def expand_reference_phones(reference_phones, phone_map):
    result = []
    for origin_index, raw in enumerate(reference_phones):
        base = strip_stress(raw)
        if base not in phone_map["reference_phones"]:
            raise BenchmarkValidationError(f"unmapped reference phone: {base}")
        mapping = phone_map["reference_phones"][base]
        for part_index, token in enumerate(mapping["ipa"]):
            result.append(
                {
                    "token": token,
                    "reference_phone": base,
                    "origin_index": origin_index,
                    "part_index": part_index,
                    "part_count": len(mapping["ipa"]),
                    "class": mapping["class"],
                    "scorable": mapping["scorable"],
                }
            )
    return result


def align_phone_sequences(expected_items, observed_tokens, phone_map):
    """Return a deterministic unit-cost alignment with explicit tie breaking."""
    observed = [normalize_candidate_token(item, phone_map) for item in observed_tokens]
    observed = [item for item in observed if item["state"] != "special_nonphone"]
    rows = len(expected_items)
    columns = len(observed)
    costs = [[0] * (columns + 1) for _ in range(rows + 1)]
    choices = [[None] * (columns + 1) for _ in range(rows + 1)]
    for row in range(1, rows + 1):
        costs[row][0] = row
        choices[row][0] = "deletion"
    for column in range(1, columns + 1):
        costs[0][column] = column
        choices[0][column] = "insertion"
    priority = {"match": 0, "substitution": 1, "deletion": 2, "insertion": 3}
    for row in range(1, rows + 1):
        expected = expected_items[row - 1]["token"]
        for column in range(1, columns + 1):
            candidate = observed[column - 1]["normalized"]
            equivalent = expected == candidate
            diagonal_kind = "match" if equivalent else "substitution"
            candidates = [
                (costs[row - 1][column - 1] + (0 if equivalent else 1), diagonal_kind),
                (costs[row - 1][column] + 1, "deletion"),
                (costs[row][column - 1] + 1, "insertion"),
            ]
            best_cost, best_kind = min(
                candidates, key=lambda item: (item[0], priority[item[1]])
            )
            costs[row][column] = best_cost
            choices[row][column] = best_kind

    alignment = []
    row, column = rows, columns
    while row or column:
        kind = choices[row][column]
        if kind in {"match", "substitution"}:
            alignment.append(
                {
                    "kind": kind,
                    "expected_index": row - 1,
                    "observed_index": column - 1,
                    "expected": expected_items[row - 1],
                    "observed": observed[column - 1],
                }
            )
            row -= 1
            column -= 1
        elif kind == "deletion":
            alignment.append(
                {
                    "kind": kind,
                    "expected_index": row - 1,
                    "observed_index": None,
                    "expected": expected_items[row - 1],
                    "observed": None,
                }
            )
            row -= 1
        elif kind == "insertion":
            alignment.append(
                {
                    "kind": kind,
                    "expected_index": None,
                    "observed_index": column - 1,
                    "expected": None,
                    "observed": observed[column - 1],
                }
            )
            column -= 1
        else:
            raise BenchmarkValidationError("phone alignment backtrace is incomplete")
    alignment.reverse()
    return {"edit_cost": costs[rows][columns], "operations": alignment}


def scorable_reference_phone(reference_phones, index, phone_map, word_starts=None):
    base = strip_stress(reference_phones[index])
    mapping = phone_map["reference_phones"][base]
    if mapping["scorable"] is False:
        return False, "vowel_or_diphthong_unsupported"
    if mapping["scorable"] == "pre_vocalic_only":
        starts = set(word_starts or {0})
        previous = (
            None
            if index == 0 or index in starts
            else strip_stress(reference_phones[index - 1])
        )
        if previous and phone_map["reference_phones"][previous]["class"] in {
            "vowel",
            "diphthong",
        }:
            return False, "post_vocalic_r_unsupported"
    return True, None


def target_predictions(reference_phones, observed_tokens, phone_map, word_starts=None):
    expected = expand_reference_phones(reference_phones, phone_map)
    aligned = align_phone_sequences(expected, observed_tokens, phone_map)
    by_origin = {}
    for operation in aligned["operations"]:
        item = operation["expected"]
        if item is not None:
            by_origin.setdefault(item["origin_index"], []).append(operation)
    predictions = []
    for index, raw in enumerate(reference_phones):
        scorable, reason = scorable_reference_phone(
            reference_phones, index, phone_map, word_starts
        )
        if not scorable:
            predictions.append(
                {
                    "target_index": index,
                    "phone": strip_stress(raw),
                    "state": "abstain",
                    "reason": reason,
                }
            )
            continue
        operations = by_origin.get(index, [])
        if len(operations) != 1:
            predictions.append(
                {
                    "target_index": index,
                    "phone": strip_stress(raw),
                    "state": "abstain",
                    "reason": "alignment_not_one_to_one",
                }
            )
            continue
        operation = operations[0]
        observed = operation["observed"]
        if observed is not None and observed["state"] == "unsupported_detail":
            state = "abstain"
            reason = "unsupported_candidate_detail"
        elif operation["kind"] == "match":
            state = "no_relation_candidate"
            reason = None
        elif operation["kind"] == "substitution":
            state = "coarse_relation_candidate"
            reason = None
        elif operation["kind"] == "deletion":
            state = "coarse_relation_candidate"
            reason = None
        else:
            state = "abstain"
            reason = "unsupported_alignment_state"
        predictions.append(
            {
                "target_index": index,
                "phone": strip_stress(raw),
                "state": state,
                "relation_type": operation["kind"],
                "observed_phone": None if observed is None else observed["raw"],
                "reason": reason,
            }
        )
    return {"alignment": aligned, "targets": predictions}


def insertion_predictions(alignment, observed_classifications, reference_phone_count):
    """Locate model insertions at unambiguous ARPAbet opportunity boundaries."""
    operations = alignment["operations"]
    if len(observed_classifications) != sum(
        operation["observed"] is not None for operation in operations
    ):
        raise BenchmarkValidationError(
            "observed classifications do not match aligned candidate phones"
        )
    classification_index = 0
    enriched = []
    for operation in operations:
        item = dict(operation)
        if operation["observed"] is not None:
            item["observed_classification"] = observed_classifications[
                classification_index
            ]
            classification_index += 1
        else:
            item["observed_classification"] = None
        enriched.append(item)
    result = {index: [] for index in range(reference_phone_count + 1)}
    for index, operation in enumerate(enriched):
        if operation["kind"] != "insertion":
            continue
        previous_origin = None
        next_origin = None
        for prior in reversed(enriched[:index]):
            if prior["expected"] is not None:
                previous_origin = prior["expected"]["origin_index"]
                break
        for following in enriched[index + 1 :]:
            if following["expected"] is not None:
                next_origin = following["expected"]["origin_index"]
                break
        if previous_origin is not None and previous_origin == next_origin:
            continue
        boundary = (
            next_origin
            if next_origin is not None
            else reference_phone_count
        )
        if boundary < 0 or boundary > reference_phone_count:
            raise BenchmarkValidationError("candidate insertion boundary is invalid")
        classification = operation["observed_classification"]
        features = classification.get("features", {})
        if classification.get("decision") != "identity_nfd":
            state = "abstain"
        elif features.get("syl") == -1:
            state = "consonant_insertion_candidate"
        elif features.get("syl") == 1:
            state = "vowel_insertion_unsupported"
        else:
            state = "abstain"
        result[boundary].append(
            {
                "phone": operation["observed"]["raw"],
                "normalized_phone": operation["observed"]["normalized"],
                "state": state,
            }
        )
    return result


def score_binary_rows(rows):
    """Score rows with truth positive/negative and prediction positive/negative/abstain."""
    counts = Counter()
    for row in rows:
        truth = row.get("truth")
        prediction = row.get("prediction")
        if truth not in {"positive", "negative", "unscorable"}:
            raise BenchmarkValidationError(f"unsupported truth state: {truth}")
        if prediction not in {"positive", "negative", "abstain"}:
            raise BenchmarkValidationError(
                f"unsupported prediction state: {prediction}"
            )
        counts["total_opportunities"] += 1
        if truth == "unscorable":
            counts["unscorable_reference"] += 1
            continue
        counts["reference_scorable"] += 1
        if prediction == "abstain":
            counts["abstained"] += 1
            continue
        counts["covered"] += 1
        if truth == "positive" and prediction == "positive":
            counts["true_positive"] += 1
        elif truth == "positive" and prediction == "negative":
            counts["false_negative"] += 1
        elif truth == "negative" and prediction == "positive":
            counts["false_positive"] += 1
        else:
            counts["true_negative"] += 1
    for name in (
        "total_opportunities",
        "unscorable_reference",
        "reference_scorable",
        "abstained",
        "covered",
        "true_positive",
        "false_positive",
        "false_negative",
        "true_negative",
    ):
        counts[name] += 0
    precision_denominator = counts["true_positive"] + counts["false_positive"]
    recall_denominator = counts["true_positive"] + counts["false_negative"]
    precision = safe_ratio(counts["true_positive"], precision_denominator)
    recall = safe_ratio(counts["true_positive"], recall_denominator)
    f1 = (
        None
        if precision is None or recall is None or precision + recall == 0
        else 2 * precision * recall / (precision + recall)
    )
    result = dict(counts)
    result.update(
        {
            "precision": ratio_record(counts["true_positive"], precision_denominator),
            "recall": ratio_record(counts["true_positive"], recall_denominator),
            "f1": None if f1 is None else round(f1, 6),
            "false_concerns_per_scorable_opportunity": ratio_record(
                counts["false_positive"], counts["reference_scorable"]
            ),
            "abstention_rate": ratio_record(
                counts["abstained"], counts["reference_scorable"]
            ),
            "coverage": ratio_record(
                counts["covered"], counts["reference_scorable"]
            ),
        }
    )
    return result


def safe_ratio(numerator, denominator):
    return None if denominator == 0 else numerator / denominator


def wilson_interval(numerator, denominator, z=1.959963984540054):
    if denominator == 0:
        return None
    proportion = numerator / denominator
    z2 = z * z
    center = (proportion + z2 / (2 * denominator)) / (1 + z2 / denominator)
    margin = (
        z
        * math.sqrt(
            proportion * (1 - proportion) / denominator
            + z2 / (4 * denominator * denominator)
        )
        / (1 + z2 / denominator)
    )
    return [round(max(0.0, center - margin), 6), round(min(1.0, center + margin), 6)]


def ratio_record(numerator, denominator):
    value = safe_ratio(numerator, denominator)
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": None if value is None else round(value, 6),
        "wilson_95_percent": wilson_interval(numerator, denominator),
    }


def reviewer_agreement(category_rows):
    """Report raw pair agreement and Fleiss kappa without hiding prevalence."""
    if not category_rows:
        return {
            "opportunities": 0,
            "reviewer_pairs": 0,
            "matching_pairs": 0,
            "raw_pair_agreement": ratio_record(0, 0),
            "fleiss_kappa": None,
            "category_totals": {},
        }
    categories = sorted(REVIEW_STATES)
    total_pairs = 0
    matching_pairs = 0
    category_totals = Counter()
    item_agreements = []
    for row in category_rows:
        if len(row) != 5 or any(item not in REVIEW_STATES for item in row):
            raise BenchmarkValidationError("reviewer agreement rows require five states")
        counts = Counter(row)
        category_totals.update(row)
        pairs = 5 * 4
        matches = sum(value * (value - 1) for value in counts.values())
        total_pairs += pairs
        matching_pairs += matches
        item_agreements.append(matches / pairs)
    observed = sum(item_agreements) / len(item_agreements)
    ratings = len(category_rows) * 5
    expected = sum((category_totals[item] / ratings) ** 2 for item in categories)
    kappa = None if expected == 1 else (observed - expected) / (1 - expected)
    return {
        "opportunities": len(category_rows),
        "reviewer_pairs": total_pairs,
        "matching_pairs": matching_pairs,
        "raw_pair_agreement": ratio_record(matching_pairs, total_pairs),
        "fleiss_kappa": None if kappa is None else round(kappa, 6),
        "category_totals": dict(sorted(category_totals.items())),
    }


def validate_partition(split, stratum):
    if split not in ALLOWED_SPLITS:
        raise BenchmarkValidationError("held out or unknown split is prohibited")
    if stratum not in {"adult", "child", "fixture", "not_available"}:
        raise BenchmarkValidationError("benchmark stratum is unsupported")


def contains_private_material(value):
    """Conservative recursive check for committed-report privacy leaks."""
    forbidden_keys = {
        "participant_id",
        "private_participant_id",
        "clip_id",
        "safe_id",
        "utterance_id",
        "transcript",
        "audio_path",
        "collapsed_tokens",
        "reviewer_records",
    }
    if isinstance(value, dict):
        if forbidden_keys & set(value):
            return True
        return any(contains_private_material(item) for item in value.values())
    if isinstance(value, list):
        return any(contains_private_material(item) for item in value)
    if isinstance(value, str):
        return value.startswith("/") or ".research_data" in value
    return False


def validate_safe_benchmark_report(document):
    """Reject private, held-out, pooled or release-promoting benchmark reports."""
    errors = []
    required = {
        "schema_version",
        "report_id",
        "status",
        "benchmark_contract",
        "phone_map",
        "private_evidence",
        "sample",
        "expert_phone_relations",
        "human_corrected_timing_fixture",
        "automatic_alignment_engineering",
        "australian_sentence_robustness",
        "local_system_repeatability",
        "system_decision",
        "limitations",
        "release_boundaries",
        "next_checkpoint",
    }
    if not isinstance(document, dict):
        return ["safe benchmark report must be an object"]
    if set(document) != required:
        return ["safe benchmark report fields do not match the aggregate schema"]
    if document["schema_version"] != BENCHMARK_SCHEMA_VERSION:
        errors.append("safe benchmark report schema is unsupported")
    if document["status"] != (
        "benchmark_harness_complete_development_and_tuning_only_release_locked"
    ):
        errors.append("benchmark report must remain development and tuning only")
    if contains_private_material(document):
        errors.append("benchmark report contains private or clip-level material")
    private = document["private_evidence"]
    if private.get("raw_or_row_level_evidence_committed") is not False:
        errors.append("raw or row-level benchmark evidence cannot be committed")
    if private.get("held_out_evaluation_accessed_or_scored") is not False:
        errors.append("held out benchmark evidence must remain untouched")
    sample = document["sample"]
    if sample.get("held_out_participants") != 0:
        errors.append("safe benchmark sample cannot include held out participants")
    if set(sample.get("project_splits", [])) != {
        "development",
        "threshold_tuning",
        "fixture",
    }:
        errors.append("safe benchmark sample split set changed")
    partitions = document["expert_phone_relations"].get("partitions", [])
    if {
        (item.get("project_split"), item.get("age_stratum"))
        for item in partitions
    } != {
        ("development", "adult"),
        ("development", "child"),
        ("threshold_tuning", "adult"),
        ("threshold_tuning", "child"),
    }:
        errors.append("expert relation partitions must keep split and age separate")
    decision = document["system_decision"]
    if decision.get("selected_system") is not None:
        errors.append("checkpoint 22D cannot select a speech-sound system")
    if decision.get("threshold_selected") is not False:
        errors.append("checkpoint 22D cannot select a candidate threshold")
    if decision.get("scientific_or_product_release_supported") is not False:
        errors.append("benchmark evidence cannot support scientific or product release")
    boundaries = document["release_boundaries"]
    required_boundaries = {
        "candidate_artifact",
        "normal_pipeline",
        "coaching",
        "personal_progress",
        "screening",
        "diagnosis",
        "severity",
        "cause",
        "treatment",
        "scientific_release",
        "product_release",
    }
    if set(boundaries) != required_boundaries or any(
        boundaries.get(name) is not False for name in required_boundaries
    ):
        errors.append("every benchmark release boundary must remain false")
    if document["next_checkpoint"] != (
        "22E_paid_api_bake_off_after_owner_commit_and_explicit_approval"
    ):
        errors.append("benchmark report cannot advance beyond checkpoint 22D")
    return errors
