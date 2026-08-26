"""Load and validate the guarded voice and prosody primitive contract."""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACT_PATH = Path(__file__).with_name("contract-v1.1.0.json")
REQUIRED_PRIMITIVES = {
    "f0_median_hz",
    "f0_percentiles_hz",
    "f0_distribution_span_st",
    "recorder_level_percentiles_dbfs",
    "recorder_level_span_db",
    "cpps_db",
    "jitter_local_pct",
    "shimmer_local_pct",
    "absolute_vocal_spl_db",
}
REQUIRED_TASK_PROFILES = {
    "fixed_reading",
    "listen_and_repeat",
    "spontaneous_speech",
    "conversation",
    "sustained_vowel_research",
    "repeated_phrase_research",
    "unknown_ad_hoc",
}
FORBIDDEN_RELEASES = {"personal_progress", "ranking", "screening", "diagnosis"}


def load_contract(path=CONTRACT_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _require_fields(value, fields, label, errors):
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return False
    missing = sorted(set(fields) - set(value))
    if missing:
        errors.append(f"{label} is missing: {', '.join(missing)}")
        return False
    return True


def validate_contract(document):
    """Return every safety or structural error in one contract document."""
    errors = []
    required_root = {
        "schema_version",
        "contract_version",
        "status",
        "purpose",
        "claim_boundaries",
        "task_profiles",
        "primitive_registry",
        "algorithm",
        "frame_contract",
        "device_policy",
        "validation_program",
        "release_limits",
    }
    if not _require_fields(document, required_root, "contract", errors):
        return errors
    if document["status"] != "engineering_active_scientific_release_locked":
        errors.append("scientific release must remain locked")

    boundaries = document["claim_boundaries"]
    required_boundaries = {
        "allowed_claim_level": "measured_observation",
        "released_interpretation_requires_separate_validation": True,
        "combined_voice_or_prosody_index_allowed": False,
        "confidence_or_personality_inference_allowed": False,
        "gender_or_identity_inference_allowed": False,
        "screening_allowed": False,
        "diagnosis_allowed": False,
        "ranking_allowed": False,
        "personal_progress_allowed": False,
        "universal_ideal_voice_allowed": False,
        "missing_evidence_becomes_zero": False,
    }
    if not isinstance(boundaries, dict):
        errors.append("claim_boundaries must be an object")
    else:
        for field, required in required_boundaries.items():
            if boundaries.get(field) != required:
                errors.append(f"claim boundary {field} must be {required!r}")

    task_profiles = document["task_profiles"]
    if not isinstance(task_profiles, dict):
        errors.append("task_profiles must be an object")
        task_profiles = {}
    missing_tasks = sorted(REQUIRED_TASK_PROFILES - set(task_profiles))
    if missing_tasks:
        errors.append("task profiles are missing: " + ", ".join(missing_tasks))
    assigned_ids = {}
    for profile_name, profile in task_profiles.items():
        if not _require_fields(
                profile, {"task_ids", "comparability", "supports"},
                f"task profile {profile_name}", errors):
            continue
        if not isinstance(profile["task_ids"], list):
            errors.append(f"task profile {profile_name} task_ids must be a list")
        else:
            for task_id in profile["task_ids"]:
                if task_id in assigned_ids:
                    errors.append(
                        f"task {task_id} is assigned to both {assigned_ids[task_id]} "
                        f"and {profile_name}"
                    )
                assigned_ids[task_id] = profile_name
        if not isinstance(profile["supports"], list):
            errors.append(f"task profile {profile_name} supports must be a list")
    for research_profile in (
            "sustained_vowel_research", "repeated_phrase_research"):
        if task_profiles.get(research_profile, {}).get(
                "requires_research_consent") is not True:
            errors.append(f"{research_profile} must require research consent")
    if task_profiles.get("unknown_ad_hoc", {}).get(
            "comparability") != "not_comparable":
        errors.append("unknown ad hoc speech must remain noncomparable")

    primitives = document["primitive_registry"]
    if not isinstance(primitives, dict):
        errors.append("primitive_registry must be an object")
        primitives = {}
    missing_primitives = sorted(REQUIRED_PRIMITIVES - set(primitives))
    if missing_primitives:
        errors.append("primitives are missing: " + ", ".join(missing_primitives))
    allowed_releases = {"experimental_observation", "research_only", "locked"}
    for name, primitive in primitives.items():
        if not _require_fields(
                primitive,
                {"construct", "unit", "minimum", "task_specific",
                 "device_validation", "release", "forbidden_interpretations"},
                f"primitive {name}", errors):
            continue
        if primitive["release"] not in allowed_releases:
            errors.append(f"primitive {name} has an unsupported release")
        if primitive["task_specific"] is not True:
            errors.append(f"primitive {name} must remain task specific")
        if primitive["device_validation"] != "not_established":
            errors.append(f"primitive {name} cannot claim device validation")
        if not primitive["forbidden_interpretations"]:
            errors.append(f"primitive {name} needs forbidden interpretations")
    for profile_name, profile in task_profiles.items():
        unknown = sorted(set(profile.get("supports", [])) - set(primitives))
        if unknown:
            errors.append(
                f"task profile {profile_name} supports unknown primitives: "
                + ", ".join(unknown)
            )

    algorithm = document["algorithm"]
    if not isinstance(algorithm, dict):
        errors.append("algorithm must be an object")
    else:
        if algorithm.get("version") != "voice-prosody-primitives-1.0.0":
            errors.append("voice and prosody algorithm version is unsupported")
        if algorithm.get("analysis_sample_rate_hz") != 48000:
            errors.append("analysis sample rate must be 48000 hertz")
        if algorithm.get("frame_step_s") != 0.01:
            errors.append("frame step must be 0.01 seconds")
        pitch = algorithm.get("pitch") or {}
        if pitch.get("primary") != (
                "praat_raw_autocorrelation_two_pass_adaptive"):
            errors.append(
                "pitch method must use two pass adaptive Praat raw autocorrelation"
            )
        if pitch.get("adaptive_pitch_ratio") != 3.0:
            errors.append("adaptive pitch ratio must be 3.0")
        if pitch.get("region_edge_margin_s") != 0.03:
            errors.append("pitch region edge margin must be 0.03 seconds")

    vowel_support = set(task_profiles.get(
        "sustained_vowel_research", {}).get("supports", []))
    for name in ("jitter_local_pct", "shimmer_local_pct"):
        supporting_profiles = {
            profile_name for profile_name, profile in task_profiles.items()
            if name in set(profile.get("supports", []))
        }
        if supporting_profiles != {"sustained_vowel_research"}:
            errors.append(f"{name} must be sustained vowel research only")
        if name not in vowel_support:
            errors.append(f"sustained vowel research must declare {name}")
        if primitives.get(name, {}).get("release") != "research_only":
            errors.append(f"{name} must remain research only")

    device = document["device_policy"]
    if isinstance(device, dict):
        if device.get("ordinary_upload_absolute_spl") != "unavailable":
            errors.append("ordinary uploads cannot provide absolute SPL")
        if device.get("hardware_fingerprint_allowed") is not False:
            errors.append("device hardware fingerprinting must remain forbidden")
        if device.get("validation_status") != "not_evaluated":
            errors.append("device validation must remain not evaluated")
    else:
        errors.append("device_policy must be an object")

    frame_contract = document["frame_contract"]
    if isinstance(frame_contract, dict):
        required_frame_fields = {
            "time_s", "f0_hz", "pitch_strength", "recorder_level_dbfs",
            "voiced", "speaker", "region_id", "quality_flags",
        }
        if set(frame_contract.get("required_fields") or []) != required_frame_fields:
            errors.append("frame contract required fields are incomplete")
        if frame_contract.get("unvoiced_f0", "missing") is not None:
            errors.append("unvoiced F0 must be null")
        for field in (
                "crosses_silence", "crosses_speaker_change",
                "crosses_overlap", "crosses_region_boundary"):
            if frame_contract.get(field) is not False:
                errors.append(f"frame contract {field} must be false")
    else:
        errors.append("frame_contract must be an object")

    limits = document["release_limits"]
    if not isinstance(limits, dict):
        errors.append("release_limits must be an object")
    else:
        for use in FORBIDDEN_RELEASES:
            if limits.get(use) != "blocked":
                errors.append(f"release limit {use} must remain blocked")
        if limits.get("combined_index") != "blocked":
            errors.append("combined indices must remain blocked")
        if limits.get("released_interpretation") != (
                "blocked_pending_separate_validation"):
            errors.append("released interpretation must remain blocked")

    validation = document["validation_program"]
    if isinstance(validation, dict):
        if validation.get(
                "development_and_evaluation_participants_separate") is not True:
            errors.append("development and evaluation participants must be separate")
        if validation.get("adam_recordings_role") != "functional_integration_only":
            errors.append("Adam recordings must remain functional integration only")
    else:
        errors.append("validation_program must be an object")
    return errors


def task_profile_for(task_id, recording_mode, contract=None):
    """Resolve a task without inferring task identity from the audio."""
    contract = contract or load_contract()
    if task_id:
        for profile_name, profile in contract["task_profiles"].items():
            if task_id in profile.get("task_ids", []):
                return profile_name
    if recording_mode == "conversation":
        return "conversation"
    return "unknown_ad_hoc"
