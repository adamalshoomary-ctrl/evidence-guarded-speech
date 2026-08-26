"""Load and validate the guarded timestamped speech event contract."""

from __future__ import annotations

import json
from pathlib import Path


CONTRACT_PATH = Path(__file__).with_name("contract-v1.1.0.json")
REQUIRED_EVENT_TYPES = {
    "sound_or_syllable_repetition",
    "single_syllable_whole_word_repetition",
    "whole_word_repetition_unclassified",
    "prolonged_sound",
    "possible_block",
    "phrase_repetition",
    "interjection",
}
BLOCKED_USES = {
    "released_interpretation",
    "personal_progress",
    "monitoring",
    "screening",
    "diagnosis",
    "severity",
    "ranking",
    "high_stakes_decision",
}


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
    """Return every structural and safety error in one contract document."""
    errors = []
    root_fields = {
        "schema_version",
        "contract_version",
        "status",
        "purpose",
        "terminology",
        "event_types",
        "candidate_contract",
        "review_contract",
        "algorithm",
        "task_policy",
        "quality_policy",
        "validation_program",
        "downstream_policy",
        "release_limits",
    }
    if not _require_fields(document, root_fields, "contract", errors):
        return errors
    if document["status"] != "engineering_active_scientific_release_locked":
        errors.append("scientific release must remain locked")

    terminology = document["terminology"]
    if isinstance(terminology, dict):
        if terminology.get("automated_output") != "speech_event_candidate":
            errors.append("automatic output must remain a candidate")
        if terminology.get("candidate_is_not_fact") is not True:
            errors.append("a candidate cannot be treated as fact")
        if terminology.get("absence_is_not_fluency") is not True:
            errors.append("candidate absence cannot establish fluency")
        if terminology.get("forbidden_automatic_label") != (
                "confirmed_stuttering_event"):
            errors.append("confirmed stuttering must remain an automatic label ban")
    else:
        errors.append("terminology must be an object")

    event_types = document["event_types"]
    if not isinstance(event_types, dict):
        errors.append("event_types must be an object")
        event_types = {}
    missing_types = sorted(REQUIRED_EVENT_TYPES - set(event_types))
    if missing_types:
        errors.append("event types are missing: " + ", ".join(missing_types))
    for name, event in event_types.items():
        if not _require_fields(
                event,
                {"construct", "automated_state", "automation_sources",
                 "required_review", "important_alternatives"},
                f"event type {name}", errors):
            continue
        if event["automated_state"] not in {
                "candidate_only", "context_only", "unavailable"}:
            errors.append(f"event type {name} has an unsafe automated state")
        if not isinstance(event["important_alternatives"], list) or not event[
                "important_alternatives"]:
            errors.append(f"event type {name} needs alternative explanations")
    possible_block = event_types.get("possible_block") or {}
    if possible_block.get("automated_state") != "unavailable":
        errors.append("possible block automation must remain unavailable")
    if possible_block.get("automation_sources") != []:
        errors.append("possible block cannot claim an automatic source")

    candidate = document["candidate_contract"]
    required_candidate_fields = {
        "event_id", "candidate_type", "start_s", "end_s", "speaker",
        "evidence", "alternatives", "uncertainty", "review",
    }
    if isinstance(candidate, dict):
        if set(candidate.get("required_fields") or []) != required_candidate_fields:
            errors.append("candidate required fields are incomplete")
        if candidate.get("confidence_is_probability") is not False:
            errors.append("candidate confidence cannot claim probability")
        if candidate.get("raw_evidence_preserved") is not True:
            errors.append("candidate raw evidence must be preserved")
    else:
        errors.append("candidate_contract must be an object")

    review = document["review_contract"]
    if isinstance(review, dict):
        states = set(review.get("states") or [])
        if not {"unreviewed", "confirmed_observable_event", "rejected",
                "relabeled", "uncertain"}.issubset(states):
            errors.append("review states are incomplete")
        truth = review.get("reference_truth_requires") or {}
        if truth.get("independent_reviewers", 0) < 2:
            errors.append("reference truth needs at least two reviewers")
        for field in ("blind_to_automation", "disagreements_retained",
                      "adjudication", "written_annotation_guide"):
            if truth.get(field) is not True:
                errors.append(f"reference truth must require {field}")
        if review.get("speaker_self_report_is_reference_truth") is not False:
            errors.append("speaker self report alone cannot be reference truth")
        if review.get("single_reviewer_is_reference_truth") is not False:
            errors.append("one reviewer cannot be reference truth")
        if review.get("review_cannot_create_diagnosis") is not True:
            errors.append("review cannot create a diagnosis")
    else:
        errors.append("review_contract must be an object")

    algorithm = document["algorithm"]
    if isinstance(algorithm, dict):
        if algorithm.get("version") != "fluency-event-candidates-1.0.0":
            errors.append("event candidate algorithm version is unsupported")
        block = algorithm.get("possible_block") or {}
        if block.get("automatic_detection_enabled") is not False:
            errors.append("automatic block detection must remain disabled")
        if block.get("silence_is_block") is not False:
            errors.append("silence cannot be called a block")
        word = algorithm.get("whole_word_repetition") or {}
        if word.get("syllable_classification") != "manual_only":
            errors.append("syllable classification must remain manual")
    else:
        errors.append("algorithm must be an object")

    task = document["task_policy"]
    if isinstance(task, dict):
        if task.get("unknown_task_comparability") != "not_comparable":
            errors.append("unknown tasks must remain noncomparable")
        if task.get("cross_task_pooling") != "blocked":
            errors.append("cross task pooling must remain blocked")
        excluded = set(task.get("excluded") or [])
        if not {"sustained_vowel_research", "repeated_phrase_research"}.issubset(
                excluded):
            errors.append("vowel and repeated phrase research tasks must be excluded")
        if task.get(
                "repeated_phrase_task_requires_prompt_aware_interpretation"
        ) is not True:
            errors.append("repeated phrase tasks need prompt aware interpretation")
    else:
        errors.append("task_policy must be an object")

    validation = document["validation_program"]
    if isinstance(validation, dict):
        if validation.get("adam_recordings_role") != "functional_integration_only":
            errors.append("Adam recordings must remain integration evidence only")
        if validation.get("scientific_release_status") != "not_evaluated":
            errors.append("scientific release cannot claim evaluation")
        metrics = set(validation.get("primary_metrics") or [])
        if not {
            "event_level_precision_recall_and_f1_by_type",
            "false_positive_events_per_speaking_minute_by_type",
            "onset_and_offset_error_by_type",
            "abstention_and_unavailable_rate",
        }.issubset(metrics):
            errors.append("event validation metrics are incomplete")
    else:
        errors.append("validation_program must be an object")

    downstream = document["downstream_policy"]
    if isinstance(downstream, dict):
        for field in (
                "included_in_evaluator_input", "included_in_listener_prompt",
                "included_in_claim_ledger", "included_in_personal_progress",
                "included_in_released_interpretation", "combined_count_or_severity_score",
                "absence_used_as_positive_fluency_claim"):
            if downstream.get(field) is not False:
                errors.append(f"downstream policy {field} must remain false")
    else:
        errors.append("downstream_policy must be an object")

    limits = document["release_limits"]
    if isinstance(limits, dict):
        for use in BLOCKED_USES:
            if limits.get(use) != "blocked":
                errors.append(f"release limit {use} must remain blocked")
        if limits.get("candidate_collection") != "engineering_only":
            errors.append("candidate collection must remain engineering only")
    else:
        errors.append("release_limits must be an object")
    return errors
