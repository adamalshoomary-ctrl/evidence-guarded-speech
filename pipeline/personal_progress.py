"""Evidence-gated personal baseline and meaningful change evaluation."""

from __future__ import annotations

import json
import math
import re
from datetime import datetime
from pathlib import Path
from statistics import median

try:
    from measurement_evidence import is_measurement_usable_for_progress
except ModuleNotFoundError:
    from .measurement_evidence import is_measurement_usable_for_progress


REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACT_PATH = REPO_ROOT / "progress_model" / "contract-v1.1.0.json"
REGISTRY_PATH = (
    REPO_ROOT / "progress_model" / "reliability-registry-v1.1.0.json"
)
PROGRESS_RESULT_SCHEMA_VERSION = "1.0.0"
PROGRESS_CONTRACT_SCHEMA_VERSION = "1.1.0"
RELIABILITY_REGISTRY_SCHEMA_VERSION = "1.1.0"
# 3.0.0 removes stat_scores. Version 2.0.0 records carried five language
# model scores parsed out of a report by regular expression; item R5 deleted
# the scores on 2026-08-24, so the field can no longer be populated and is not
# written. Existing 2.0.0 records are left exactly as they are.
HISTORY_RECORD_VERSION = "3.0.0"
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")

PROGRESS_INTENTS = {
    "baseline_observation",
    "change_check",
    "practice",
    "retention",
    "transfer",
}
CHANGE_INTENTS = {"change_check", "retention", "transfer"}
CORE_COMPARISON_FIELDS = {
    "account_id",
    "context_id",
    "task_id",
    "task_version",
    "prompt_id",
    "prompt_version",
    "language",
    "recording_mode",
    "quality_policy",
    "device_class",
    "platform",
    "microphone",
    "environment_setting",
    "environment_noise",
    "preparation_allowed_s",
    "accommodations",
}


class PersonalProgressValidationError(ValueError):
    """Raised when a progress contract or release registry is unsafe."""


def load_progress_contract(path=CONTRACT_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_reliability_registry(path=REGISTRY_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _required(value, fields, location, errors):
    if not isinstance(value, dict):
        errors.append(f"{location} must be an object")
        return False
    missing = sorted(fields - set(value))
    if missing:
        errors.append(f"{location} missing fields: {', '.join(missing)}")
        return False
    return True


def validate_progress_contract(document):
    """Return errors when the committed progress safety contract is weakened."""
    errors = []
    root_fields = {
        "schema_version",
        "contract_version",
        "status",
        "purpose",
        "claim_boundaries",
        "evidence_streams",
        "comparability",
        "baseline_model",
        "change_model",
        "metric_release_profile",
        "mastery_model",
        "runtime_outputs",
        "sources",
    }
    if not _required(document, root_fields, "$", errors):
        return errors
    if document["schema_version"] != PROGRESS_CONTRACT_SCHEMA_VERSION:
        errors.append("progress contract schema_version is unsupported")
    if not SEMVER.fullmatch(str(document["contract_version"])):
        errors.append("progress contract version must use semantic versioning")
    if document["status"] != "personal_progress_protocol_metrics_locked":
        errors.append("the committed progress protocol must keep metrics locked")

    boundaries = document["claim_boundaries"]
    false_boundaries = {
        "one_observation_is_a_baseline",
        "same_day_success_is_mastery",
        "detectable_change_is_automatically_improvement",
        "user_report_is_a_speech_measurement",
        "practice_is_skill_mastery",
        "model_scores_are_progress_measures",
        "run_quality_is_skill_progress",
        "missing_evidence_becomes_zero",
        "universal_ideal_voice_allowed",
        "confidence_inferred_from_voice",
    }
    for field in false_boundaries:
        if boundaries.get(field) is not False:
            errors.append(f"claim_boundaries.{field} must remain false")

    streams = document["evidence_streams"]
    if set(streams) != {
            "speech_measurements", "user_reports", "real_world_outcomes",
            "practice", "mastery"}:
        errors.append("progress evidence streams must remain separate")
    for name in ("user_reports", "real_world_outcomes"):
        if streams.get(name, {}).get(
                "kept_separate_from_speech_measurements") is not True:
            errors.append(f"{name} must remain separate from speech measurements")
    if streams.get("practice", {}).get("proves_mastery") is not False:
        errors.append("practice cannot prove mastery")
    if streams.get("mastery", {}).get(
            "requires_retention_and_transfer") is not True:
        errors.append("mastery must require retention and transfer")

    comparability = document["comparability"]
    if set(comparability.get("core_exact_match_fields") or []) != (
            CORE_COMPARISON_FIELDS):
        errors.append("comparability core fields must contain approved values exactly")
    for field in (
            "different_contexts_are_automatically_comparable",
            "different_tasks_are_automatically_comparable",
            "different_prompts_are_automatically_comparable",
            "different_devices_are_automatically_comparable"):
        if comparability.get(field) is not False:
            errors.append(f"comparability.{field} must remain false")

    baseline = document["baseline_model"]
    if baseline.get("explicit_progress_intent_required") is not True:
        errors.append("baseline records require explicit progress intent")
    if baseline.get("baseline_intent") != "baseline_observation":
        errors.append("baseline intent is unsupported")
    if baseline.get("eligible_attempt_roles") != ["first"]:
        errors.append("only first attempts may enter the initial baseline")
    if baseline.get("global_minimum_observation_count") is not None:
        errors.append("a global baseline observation threshold is not allowed")
    if baseline.get("one_recording_default_allowed") is not False:
        errors.append("one recording cannot become a baseline by default")
    if baseline.get("summary", {}).get("outliers_are_silently_deleted") is not False:
        errors.append("baseline outliers cannot be silently deleted")

    change = document["change_model"]
    if set(change.get("change_intents") or []) != CHANGE_INTENTS:
        errors.append("change intents must contain the approved values exactly")
    for field in (
            "requires_established_baseline",
            "requires_current_measurement_quality",
            "requires_metric_release_profile",
            "requires_measurement_error",
            "requires_expected_natural_variation",
            "requires_separately_justified_meaningful_change"):
        if change.get(field) is not True:
            errors.append(f"change_model.{field} must remain true")
    if change.get("global_percentage_rule") is not None:
        errors.append("a global percentage change rule is not allowed")
    if change.get(
            "improving_and_slipping_labels_allowed_without_goal_specific_evidence"
            ) is not False:
        errors.append("change direction cannot be called improvement without evidence")

    release = document["metric_release_profile"]
    if release.get("owner_recordings_can_set_release_thresholds") is not False:
        errors.append("owner recordings cannot set progress thresholds")
    for field in (
            "development_and_evaluation_participants_separate",
            "independent_held_out_evaluation_required",
            "representative_conditions_required",
            "subgroup_reporting_required",
            "professional_measurement_review_required",
            "owner_release_approval_required"):
        if release.get(field) is not True:
            errors.append(f"metric_release_profile.{field} must remain true")

    mastery = document["mastery_model"]
    if mastery.get("retention_must_be_later_day") is not True:
        errors.append("mastery retention must be measured on a later day")
    if mastery.get("transfer_must_use_suitable_new_prompt") is not True:
        errors.append("mastery transfer must use a suitable new prompt")
    if mastery.get("retention_and_transfer_remain_separate") is not True:
        errors.append("retention and transfer must remain separate")
    if mastery.get("current_mastery_release") != (
            "blocked_until_skill_specific_policy"):
        errors.append("current mastery claims must remain blocked")

    if not isinstance(document["sources"], list) or not document["sources"]:
        errors.append("progress contract must retain its research sources")
    return errors


def _positive_integer(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 2


def _positive_number(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and value > 0)


def _validate_metric_profile(profile, index, errors):
    location = f"approved_metric_profiles[{index}]"
    required = {
        "metric_path",
        "construct",
        "unit",
        "release_status",
        "eligible_attempt_roles",
        "comparison_fields",
        "minimum_baseline_observations",
        "minimum_distinct_sessions",
        "minimum_distinct_days",
        "measurement_error",
        "natural_variation",
        "meaningful_change",
        "validated_algorithm_versions",
        "evidence",
    }
    if not _required(profile, required, location, errors):
        return
    if profile["release_status"] != "approved_for_personal_change":
        errors.append(f"{location}.release_status is unsupported")
    if profile["eligible_attempt_roles"] != ["first"]:
        errors.append(f"{location} baseline roles must contain only first")
    comparison_fields = profile["comparison_fields"]
    if (not isinstance(comparison_fields, list)
            or not CORE_COMPARISON_FIELDS.issubset(comparison_fields)):
        errors.append(f"{location} cannot omit unvalidated comparison fields")
    for field in (
            "minimum_baseline_observations", "minimum_distinct_sessions",
            "minimum_distinct_days"):
        if not _positive_integer(profile[field]):
            errors.append(f"{location}.{field} must be an evidence based integer of at least 2")
    for name in ("measurement_error", "natural_variation", "meaningful_change"):
        value = profile[name]
        if not _required(value, {"method", "boundary"},
                         f"{location}.{name}", errors):
            continue
        if not _positive_number(value["boundary"]):
            errors.append(f"{location}.{name}.boundary must be a positive number")
    measurement_error = profile["measurement_error"]
    if (not isinstance(measurement_error, dict)
            or measurement_error.get("method") not in {
                "individual_sdc95_agreement",
                "justified_limits_of_agreement",
            }):
        errors.append(f"{location} has unsupported measurement error method")
    meaningful = profile["meaningful_change"]
    if (not isinstance(meaningful, dict)
            or meaningful.get("distribution_only") is not False):
        errors.append(f"{location} meaningful change cannot be distribution only")
    anchors = meaningful.get("anchor_references") if isinstance(
        meaningful, dict
    ) else None
    if not isinstance(anchors, list) or not anchors:
        errors.append(f"{location} meaningful change needs user relevant anchors")
    versions = profile["validated_algorithm_versions"]
    if not isinstance(versions, list) or not versions:
        errors.append(f"{location} must identify validated algorithm versions")
    evidence = profile["evidence"]
    evidence_fields = {
        "development_participants",
        "evaluation_participants",
        "participants_separated",
        "independent_held_out_evaluation",
        "representative_conditions",
        "subgroups_reported",
        "study_reference",
        "sample_size_justification",
        "development_protocol_reference",
        "held_out_results_reference",
        "measurement_review_role",
        "owner_release_approved",
    }
    if _required(evidence, evidence_fields, f"{location}.evidence", errors):
        if not all(_positive_integer(evidence[field]) for field in (
                "development_participants", "evaluation_participants")):
            errors.append(f"{location} needs multiple development and evaluation participants")
        for field in (
                "participants_separated", "independent_held_out_evaluation",
                "representative_conditions", "subgroups_reported"):
            if evidence[field] is not True:
                errors.append(f"{location}.evidence.{field} must be true")
        if not isinstance(evidence["study_reference"], str) or not (
                evidence["study_reference"].strip()):
            errors.append(f"{location} needs an auditable study reference")
        for field in (
                "sample_size_justification", "development_protocol_reference",
                "held_out_results_reference", "measurement_review_role"):
            if not isinstance(evidence[field], str) or not evidence[field].strip():
                errors.append(f"{location}.evidence.{field} must be auditable text")
        if evidence["owner_release_approved"] is not True:
            errors.append(f"{location}.evidence.owner_release_approved must be true")


def validate_reliability_registry(document, contract=None):
    """Validate a registry that may later release individual metrics."""
    errors = []
    required = {
        "schema_version",
        "registry_version",
        "progress_contract_version",
        "status",
        "approved_metric_profiles",
        "current_blockers",
        "owner_recordings_may_unlock_metrics",
    }
    if not _required(document, required, "$", errors):
        return errors
    contract = contract or load_progress_contract()
    if document["schema_version"] != RELIABILITY_REGISTRY_SCHEMA_VERSION:
        errors.append("reliability registry schema_version is unsupported")
    if not SEMVER.fullmatch(str(document["registry_version"])):
        errors.append("registry version must use semantic versioning")
    if document["progress_contract_version"] != contract.get("contract_version"):
        errors.append("registry and progress contract versions do not match")
    if document["owner_recordings_may_unlock_metrics"] is not False:
        errors.append("owner recordings cannot unlock progress metrics")
    profiles = document["approved_metric_profiles"]
    if not isinstance(profiles, list):
        errors.append("approved_metric_profiles must be a list")
        return errors
    for index, profile in enumerate(profiles):
        _validate_metric_profile(profile, index, errors)
    metric_paths = [item.get("metric_path") for item in profiles
                    if isinstance(item, dict)]
    if len(metric_paths) != len(set(metric_paths)):
        errors.append("approved metric paths must be unique")
    expected_status = "metrics_released" if profiles else "no_metrics_released"
    if document["status"] != expected_status:
        errors.append(f"registry status must be {expected_status}")
    return errors


def assert_valid_progress_contract(document):
    errors = validate_progress_contract(document)
    if errors:
        raise PersonalProgressValidationError("\n".join(errors))
    return document


def assert_valid_reliability_registry(document, contract=None):
    errors = validate_reliability_registry(document, contract)
    if errors:
        raise PersonalProgressValidationError("\n".join(errors))
    return document


def comparison_from_session_context(session_context):
    """Build the explicit condition record used for future comparisons."""
    session = session_context["session"]
    context = session_context["context"]
    task = session_context["task"]
    capture = session_context["capture"]
    device = capture["device"]
    environment = context["environment"]
    return {
        "account_id": session_context["account"]["account_id"],
        "context_id": context["context_id"],
        "task_id": task["task_id"],
        "task_version": task["task_version"],
        "prompt_id": task["prompt_id"],
        "prompt_version": task["prompt_version"],
        "language": task["language"],
        "recording_mode": session["recording_mode"],
        "quality_policy": capture["quality_policy"],
        "device_class": device["device_class"],
        "platform": device["platform"],
        "microphone": device["microphone"],
        "environment_setting": environment["setting"],
        "environment_noise": environment["noise"],
        "preparation_allowed_s": task["preparation"]["allowed_s"],
        "accommodations": sorted(task["accommodations"]),
    }


def _canonical(value):
    if isinstance(value, list):
        return tuple(_canonical(item) for item in value)
    if isinstance(value, dict):
        return tuple(sorted((key, _canonical(child))
                            for key, child in value.items()))
    return value


def records_are_comparable(left, right, fields):
    """Return true only when all profile-required conditions match exactly."""
    left_conditions = left.get("comparison") or {}
    right_conditions = right.get("comparison") or {}
    return all(
        field in left_conditions
        and field in right_conditions
        and _canonical(left_conditions[field]) == _canonical(right_conditions[field])
        for field in fields
    )


def _timestamp(record):
    value = record.get("recorded_at_utc") or record.get("date")
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed


def _day(record):
    parsed = _timestamp(record)
    return parsed.date().isoformat() if parsed else None


def _value_at(value, path):
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def _metric_value(record, path):
    value = _value_at(record.get("computed_metrics") or {}, path)
    if (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value)):
        return float(value)
    return None


def _metric_evidence(record, path):
    evidence = ((record.get("measurement_metadata") or {})
                .get("computed_metrics") or {})
    return evidence.get(path)


def _quality_eligible(record):
    quality = ((record.get("run_quality") or {}).get("audio_quality") or {})
    comparison = record.get("comparison") or {}
    report = record.get("user_report") or {}
    return (
        comparison.get("quality_policy") == "baseline"
        and quality.get("overall_status") == "pass"
        and report.get("representativeness") == "typical"
    )


def _observation(record, profile):
    value = _metric_value(record, profile["metric_path"])
    evidence = _metric_evidence(record, profile["metric_path"])
    algorithm_version = (evidence or {}).get("algorithm_version")
    if value is None or not is_measurement_usable_for_progress(evidence):
        return None
    if algorithm_version not in profile["validated_algorithm_versions"]:
        return None
    if not _quality_eligible(record):
        return None
    return value


def _summarize_user_reports(records):
    observations = []
    for record in records:
        report = record.get("user_report")
        if isinstance(report, dict):
            observations.append({
                "session_id": record.get("session_id"),
                "recorded_at_utc": record.get("recorded_at_utc"),
                "source": "user_declared",
                "difficulty": report.get("difficulty"),
                "confidence": report.get("confidence"),
                "representativeness": report.get("representativeness"),
                "usefulness": report.get("usefulness"),
            })
    return {
        "source": "user_declared",
        "kept_separate_from_speech_change": True,
        "observations": observations,
    }


def _summarize_outcomes(records):
    observations = []
    for record in records:
        outcome = record.get("real_world_outcome")
        if isinstance(outcome, dict):
            observations.append({
                "session_id": record.get("session_id"),
                "recorded_at_utc": record.get("recorded_at_utc"),
                "source": "user_declared",
                "report": outcome,
            })
    return {
        "source": "user_declared",
        "kept_separate_from_speech_change": True,
        "observations": observations,
    }


def _summarize_practice(records):
    attempts = [
        {
            "attempt_id": record.get("task_attempt_id"),
            "attempt_role": record.get("attempt_role"),
            "exercise_id": record.get("exercise_id"),
            "recorded_at_utc": record.get("recorded_at_utc"),
        }
        for record in records
        if record.get("progress_intent") == "practice"
        or record.get("attempt_role") in {
            "matched_repeat", "post_exercise_repeat"}
    ]
    return {
        "status": "recorded_not_mastery",
        "attempt_count": len(attempts),
        "attempts": attempts,
    }


def _summarize_mastery(records):
    baseline_prompts = {
        (record.get("comparison") or {}).get("prompt_id")
        for record in records
        if record.get("progress_intent") == "baseline_observation"
    }
    baseline_days = {
        _day(record) for record in records
        if record.get("progress_intent") == "baseline_observation"
    } - {None}
    retention = [record for record in records
                 if record.get("progress_intent") == "retention"]
    transfer = [record for record in records
                if record.get("progress_intent") == "transfer"]
    later_retention = any(
        _day(record) is not None
        and all(_day(record) > day for day in baseline_days)
        for record in retention
    ) if baseline_days else False
    new_prompt_transfer = any(
        (record.get("comparison") or {}).get("prompt_id") not in baseline_prompts
        for record in transfer
    ) if baseline_prompts else False
    return {
        "status": "blocked_until_skill_specific_policy",
        "retention_attempts": len(retention),
        "transfer_attempts": len(transfer),
        "later_day_retention_present": later_retention,
        "new_prompt_transfer_present": new_prompt_transfer,
        "same_day_practice_is_mastery": False,
    }


def _summarize_run_quality(records):
    return {
        "is_skill_progress": False,
        "observations": [
            {
                "session_id": record.get("session_id"),
                "recorded_at_utc": record.get("recorded_at_utc"),
                "audio_quality": (record.get("run_quality") or {}).get(
                    "audio_quality"),
                "verification_pct": (record.get("run_quality") or {}).get(
                    "verification_pct"),
            }
            for record in records
        ],
    }


def _evaluate_metric(records, current, profile):
    fields = profile["comparison_fields"]
    baseline_records = [
        record for record in records
        if record is not current
        and record.get("progress_intent") == "baseline_observation"
        and record.get("attempt_role") in profile["eligible_attempt_roles"]
        and records_are_comparable(record, current, fields)
    ]
    observations = [
        (record, _observation(record, profile)) for record in baseline_records
    ]
    observations = [(record, value) for record, value in observations
                    if value is not None]
    values = [value for _, value in observations]
    sessions = {record.get("session_id") for record, _ in observations} - {None}
    days = {_day(record) for record, _ in observations} - {None}
    baseline = {
        "status": "insufficient_comparable_observations",
        "observation_count": len(values),
        "distinct_session_count": len(sessions),
        "distinct_day_count": len(days),
        "required_observations": profile["minimum_baseline_observations"],
        "required_distinct_sessions": profile["minimum_distinct_sessions"],
        "required_distinct_days": profile["minimum_distinct_days"],
        "median": None,
        "observed_minimum": None,
        "observed_maximum": None,
    }
    enough = (
        len(values) >= profile["minimum_baseline_observations"]
        and len(sessions) >= profile["minimum_distinct_sessions"]
        and len(days) >= profile["minimum_distinct_days"]
    )
    if enough:
        baseline.update({
            "status": "established",
            "median": median(values),
            "observed_minimum": min(values),
            "observed_maximum": max(values),
        })
    result = {
        "metric_path": profile["metric_path"],
        "construct": profile["construct"],
        "unit": profile["unit"],
        "baseline": baseline,
        "change": {
            "status": "unavailable",
            "reason": "baseline is not established",
            "current_value": None,
            "baseline_median": baseline["median"],
            "delta": None,
            "direction": None,
            "required_boundary": max(
                profile["measurement_error"]["boundary"],
                profile["natural_variation"]["boundary"],
                profile["meaningful_change"]["boundary"],
            ),
        },
    }
    if not enough:
        return result
    if current.get("progress_intent") not in CHANGE_INTENTS:
        result["change"]["reason"] = "current record is not a declared change check"
        return result
    current_value = _observation(current, profile)
    if current_value is None:
        result["change"]["reason"] = "current measurement is unavailable or ineligible"
        return result
    centre = baseline["median"]
    delta = current_value - centre
    magnitude = abs(delta)
    error_boundary = profile["measurement_error"]["boundary"]
    variation_boundary = max(
        error_boundary, profile["natural_variation"]["boundary"]
    )
    meaningful_boundary = max(
        variation_boundary, profile["meaningful_change"]["boundary"]
    )
    if magnitude <= error_boundary:
        status = "within_measurement_error"
    elif magnitude <= variation_boundary:
        status = "within_expected_variation"
    elif magnitude <= meaningful_boundary:
        status = "detectable_not_proven_meaningful"
    else:
        status = "credible_change"
    direction = "unchanged"
    if delta > 0:
        direction = "increased"
    elif delta < 0:
        direction = "decreased"
    result["change"].update({
        "status": status,
        "reason": None,
        "current_value": current_value,
        "baseline_median": centre,
        "delta": delta,
        "direction": direction,
        "required_boundary": meaningful_boundary,
        "called_improvement": False,
    })
    return result


def evaluate_personal_progress(records, registry=None, contract=None):
    """Return a deterministic, source-separated personal progress result."""
    contract = contract or load_progress_contract()
    registry = registry or load_reliability_registry()
    assert_valid_progress_contract(contract)
    assert_valid_reliability_registry(registry, contract)
    records = [record for record in records if isinstance(record, dict)]
    current = records[-1] if records else None
    profiles = registry["approved_metric_profiles"]
    metrics = []
    if current is not None:
        metrics = [_evaluate_metric(records, current, profile)
                   for profile in profiles]
    if not records:
        baseline_status = "insufficient_comparable_observations"
        reason = "no durable observations were supplied"
    elif not profiles:
        baseline_status = "metric_not_released"
        reason = "no speech metric has completed the personal progress release gate"
    elif any(item["baseline"]["status"] == "established" for item in metrics):
        baseline_status = "established_for_released_metrics"
        reason = None
    else:
        baseline_status = "insufficient_comparable_observations"
        reason = "released metrics do not yet have enough comparable observations"
    credible_count = sum(
        item["change"]["status"] == "credible_change" for item in metrics
    )
    scope = None
    if current is not None:
        scope = {
            "account_id": current.get("account_id"),
            "context_id": current.get("context_id"),
        }
    return {
        "schema_version": PROGRESS_RESULT_SCHEMA_VERSION,
        "contract_version": contract["contract_version"],
        "registry_version": registry["registry_version"],
        "scope": scope,
        "record_count": len(records),
        "baseline_status": {
            "status": baseline_status,
            "reason": reason,
        },
        "speech_change": {
            "status": (
                "credible_change_present" if credible_count
                else "no_credible_change_available"
            ),
            "credible_change_count": credible_count,
            "called_overall_improvement": False,
            "metrics": metrics,
        },
        "user_reports": _summarize_user_reports(records),
        "real_world_outcomes": _summarize_outcomes(records),
        "practice": _summarize_practice(records),
        "mastery": _summarize_mastery(records),
        "run_quality": _summarize_run_quality(records),
    }


def _shown(value):
    if value is None:
        return "not answered"
    return str(value).replace("_", " ")


def render_progress_markdown(result):
    """Render the source-separated result without inventing progress."""
    scope = result.get("scope") or {}
    baseline = result["baseline_status"]
    lines = [
        "# Personal progress",
        "",
        f"Account: {scope.get('account_id', 'unknown')}",
        f"Context: {scope.get('context_id', 'unknown')}",
        f"Recorded observations: {result['record_count']}",
        "",
        "## Baseline status",
        "",
        f"Status: {baseline['status'].replace('_', ' ')}.",
    ]
    if baseline.get("reason"):
        lines.append(f"Reason: {baseline['reason']}.")
    lines += ["", "## Speech change", ""]
    metrics = result["speech_change"]["metrics"]
    if not metrics:
        lines.append(
            "No speech metric is currently released for personal change. "
            "No improvement claim is available."
        )
    for item in metrics:
        change = item["change"]
        baseline_item = item["baseline"]
        lines.append(
            f"- {item['metric_path']}: baseline {baseline_item['status'].replace('_', ' ')}, "
            f"change {change['status'].replace('_', ' ')}"
        )
    lines += ["", "## User reports", ""]
    reports = result["user_reports"]["observations"]
    if not reports:
        lines.append("No user report is available.")
    else:
        latest = reports[-1]
        lines.append(f"Difficulty: {_shown(latest.get('difficulty'))}.")
        lines.append(f"Confidence: {_shown(latest.get('confidence'))}.")
        lines.append(f"Usefulness: {_shown(latest.get('usefulness'))}.")
        lines.append("These are the user's own reports, not speech measurements.")
    lines += ["", "## Real world outcomes", ""]
    outcomes = result["real_world_outcomes"]["observations"]
    lines.append(
        "No real world outcome is available." if not outcomes
        else "A user declared real world outcome is recorded separately."
    )
    lines += [
        "",
        "## Practice",
        "",
        f"Recorded practice attempts: {result['practice']['attempt_count']}.",
        "Practice is not treated as mastery.",
        "",
        "## Mastery",
        "",
        "Mastery is blocked until a skill specific policy is validated. "
        "It will require separate later retention and new prompt transfer evidence.",
        "",
        "## Run quality",
        "",
        "Recording and verification quality are retained for audit. They are not skill progress.",
        "",
    ]
    return "\n".join(lines)
