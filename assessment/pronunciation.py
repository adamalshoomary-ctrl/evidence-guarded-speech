"""Load and validate the controlled pronunciation research contract."""

from __future__ import annotations

import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = (
    REPO_ROOT / "assessment" / "pronunciation-research-v1.0.0.json"
)
SUPPORTED_SCHEMA_VERSION = "1.0.0"
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")

WORD_OUTCOMES = {
    "understood_as_intended",
    "different_word_heard",
    "omission",
    "addition",
    "uncertain",
    "unscorable",
}
PHONE_OUTCOMES = {
    "accepted_variant",
    "substitution",
    "deletion",
    "insertion",
    "break",
    "uncertain",
    "unscorable",
}
REQUIRED_FAILURES = {
    "poor_audio",
    "unsupported_language",
    "unsupported_or_unrepresented_variety",
    "asr_or_alignment_conflict",
    "insufficient_word_opportunities",
    "insufficient_phone_opportunities",
    "unresolved_human_disagreement",
    "remote_provider_failure",
    "missing_provider_version",
}
REQUIRED_RELEASE_BLOCKS = {
    "normal_coaching",
    "individual_progress",
    "ranking",
    "screening",
    "diagnosis",
}
REQUIRED_EVALUATION_METRICS = {
    "word_identification_agreement_with_listener_reference",
    "phone_issue_precision",
    "phone_issue_recall",
    "phone_issue_f1",
    "acceptable_variant_false_concern_rate",
    "abstention_coverage",
    "calibration",
    "exact_same_input_repeatability",
    "repeated_human_production_reliability",
    "subgroup_results_with_uncertainty",
}


class PronunciationProtocolValidationError(ValueError):
    """Raised when the research contract violates its safety boundaries."""


def load_protocol(path=PROTOCOL_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _require_fields(value, required, location, errors):
    if not isinstance(value, dict):
        errors.append(f"{location} must be an object")
        return False
    missing = sorted(required - set(value))
    if missing:
        errors.append(f"{location} missing fields: {', '.join(missing)}")
        return False
    return True


def _require_exact_set(value, expected, location, errors):
    if not isinstance(value, list) or set(value) != expected:
        errors.append(f"{location} must contain the approved values exactly")


def validate_protocol(document):
    """Return human-readable errors; an empty list means the contract is safe."""
    errors = []
    required_root = {
        "schema_version",
        "protocol_id",
        "protocol_version",
        "status",
        "language",
        "purpose",
        "claim_boundaries",
        "task",
        "word_pack",
        "variant_policy",
        "observation_model",
        "reference_truth",
        "candidate_systems",
        "evaluation_plan",
        "failure_policy",
        "release_policy",
        "sources",
    }
    if not _require_fields(document, required_root, "$", errors):
        return errors

    if document["schema_version"] != SUPPORTED_SCHEMA_VERSION:
        errors.append("schema_version is unsupported")
    if not SEMVER.fullmatch(str(document["protocol_version"])):
        errors.append("protocol_version must use semantic versioning")
    if document["status"] != "research_only_not_validated":
        errors.append("protocol must remain research_only_not_validated")
    if document["language"] != "en":
        errors.append("version 1 pronunciation research must remain English only")

    boundaries = document["claim_boundaries"]
    boundary_fields = {
        "allowed_claim_levels",
        "forbidden_outputs",
        "provider_agreement_is_truth",
        "automatic_transcription_is_phonetic_truth",
    }
    if _require_fields(boundaries, boundary_fields, "claim_boundaries", errors):
        if boundaries["allowed_claim_levels"] != ["measured_observation"]:
            errors.append("research may create measured observations only")
        required_forbidden = {
            "overall_pronunciation_score",
            "native_likeness",
            "prestige_accent_similarity",
            "accent_quality",
            "diagnosis",
            "screening_result",
            "ranking_between_people",
            "individual_progress",
        }
        if not required_forbidden.issubset(boundaries["forbidden_outputs"]):
            errors.append("claim boundaries are missing required forbidden outputs")
        if boundaries["provider_agreement_is_truth"] is not False:
            errors.append("provider agreement cannot be reference truth")
        if boundaries["automatic_transcription_is_phonetic_truth"] is not False:
            errors.append("automatic transcription cannot be phonetic truth")

    task = document["task"]
    task_fields = {
        "task_id",
        "task_version",
        "status",
        "recording_mode",
        "expected_duration_s",
        "quality_policy",
        "elicitation_modes",
        "elicitation_modes_are_comparable",
        "listener_can_see_expected_word",
        "prompt_audio_must_be_excluded_from_trial_audio",
        "required_consents",
        "skipping_affects_normal_coaching",
        "stop_conditions",
    }
    if _require_fields(task, task_fields, "task", errors):
        if not SEMVER.fullmatch(str(task["task_version"])):
            errors.append("task.task_version must use semantic versioning")
        if task["status"] != "research_protocol_only":
            errors.append("controlled word task must remain research protocol only")
        if task["recording_mode"] != "solo":
            errors.append("controlled word research must use solo mode")
        if task["quality_policy"] != "baseline":
            errors.append("controlled word research must use baseline quality")
        duration = task["expected_duration_s"]
        if _require_fields(
                duration, {"minimum", "target", "maximum"},
                "task.expected_duration_s", errors):
            values = (duration["minimum"], duration["target"], duration["maximum"])
            if not all(isinstance(value, (int, float)) for value in values):
                errors.append("task duration values must be numeric")
            elif not values[0] <= values[1] <= values[2]:
                errors.append("task duration must satisfy minimum <= target <= maximum")
        modes = {item.get("id") for item in task["elicitation_modes"]}
        if modes != {"written_word", "recorded_prompt_alternative"}:
            errors.append("task must preserve written and recorded-prompt modes")
        if task["elicitation_modes_are_comparable"] is not False:
            errors.append("different elicitation modes cannot be declared comparable")
        if task["listener_can_see_expected_word"] is not False:
            errors.append("intelligibility listeners must remain blind to the word")
        if task["prompt_audio_must_be_excluded_from_trial_audio"] is not True:
            errors.append("recorded prompts must be excluded from listener audio")
        required_consents = {
            "research_collection", "human_review", "raw_audio_retention"
        }
        if set(task["required_consents"]) != required_consents:
            errors.append("research requires separate collection review and retention consent")
        if task["skipping_affects_normal_coaching"] is not False:
            errors.append("skipping research cannot affect normal coaching")

    word_pack = document["word_pack"]
    pack_fields = {
        "pack_id",
        "pack_version",
        "status",
        "target_word_count",
        "stimuli",
        "activation_requirements",
        "selection_rules",
    }
    if _require_fields(word_pack, pack_fields, "word_pack", errors):
        if not SEMVER.fullmatch(str(word_pack["pack_version"])):
            errors.append("word_pack.pack_version must use semantic versioning")
        if word_pack["status"] != "awaiting_professional_review":
            errors.append("word pack must remain awaiting professional review")
        if word_pack["stimuli"]:
            errors.append("unreviewed word pack cannot contain active stimuli")
        requirements = set(word_pack["activation_requirements"])
        if "qualified_phonetic_or_speech_pathology_review" not in requirements:
            errors.append("word pack needs qualified professional review")
        if "versioned_acceptable_pronunciation_variants" not in requirements:
            errors.append("word pack needs versioned acceptable variants")
        if "owner_approval" not in requirements:
            errors.append("word pack activation needs owner approval")

    variants = document["variant_policy"]
    variant_fields = {
        "unit",
        "sources_required",
        "self_reported_variety_is_context_not_truth",
        "unrepresented_or_disputed_variant_behavior",
        "acceptable_variant_is_error",
        "single_canonical_native_target_allowed",
    }
    if _require_fields(variants, variant_fields, "variant_policy", errors):
        if variants["acceptable_variant_is_error"] is not False:
            errors.append("an acceptable accent or dialect variant cannot be an error")
        if variants["single_canonical_native_target_allowed"] is not False:
            errors.append("a single canonical native target is forbidden")
        if variants["unrepresented_or_disputed_variant_behavior"] != "uncertain":
            errors.append("unrepresented variants must remain uncertain")

    observations = document["observation_model"]
    observation_fields = {
        "word_outcomes",
        "phone_outcomes",
        "primitive_evidence_fields",
        "denominators",
        "combined_score_allowed",
        "missing_evidence_is_zero",
    }
    if _require_fields(observations, observation_fields, "observation_model", errors):
        _require_exact_set(
            observations["word_outcomes"], WORD_OUTCOMES,
            "observation_model.word_outcomes", errors,
        )
        _require_exact_set(
            observations["phone_outcomes"], PHONE_OUTCOMES,
            "observation_model.phone_outcomes", errors,
        )
        denominator_fields = {
            "expected_word_opportunities",
            "scorable_word_opportunities",
            "expected_phone_opportunities",
            "scorable_phone_opportunities",
            "insertions",
            "additions",
        }
        _require_fields(
            observations["denominators"], denominator_fields,
            "observation_model.denominators", errors,
        )
        if observations["combined_score_allowed"] is not False:
            errors.append("a combined pronunciation score is forbidden")
        if observations["missing_evidence_is_zero"] is not False:
            errors.append("missing pronunciation evidence cannot become zero")

    truth = document["reference_truth"]
    truth_fields = {
        "listener_intelligibility",
        "phonetic_reference",
        "listener_intelligibility_and_phonetic_reference_are_separate",
    }
    if _require_fields(truth, truth_fields, "reference_truth", errors):
        listener = truth["listener_intelligibility"]
        phonetic = truth["phonetic_reference"]
        if listener.get("automatic_system_allowed_as_truth") is not False:
            errors.append("automatic systems cannot create listener truth")
        if phonetic.get("automatic_system_allowed_as_truth") is not False:
            errors.append("automatic systems cannot create phonetic truth")
        if phonetic.get("reviewers_blind_to_system_outputs") is not True:
            errors.append("phonetic reviewers must be blind to system outputs")
        if phonetic.get("disagreements_retained") is not True:
            errors.append("phonetic reviewer disagreements must be retained")
        if truth["listener_intelligibility_and_phonetic_reference_are_separate"] is not True:
            errors.append("listener and phonetic truth must remain separate")

    candidates = document["candidate_systems"]
    if _require_fields(
            candidates, {"selected_provider", "comparison_status", "systems"},
            "candidate_systems", errors):
        if candidates["selected_provider"] is not None:
            errors.append("no pronunciation provider may be selected before evaluation")
        if len(candidates["systems"]) < 2:
            errors.append("research must compare more than one candidate system")
        for system in candidates["systems"]:
            system_id = system.get("id", "<unknown>")
            if system.get("status") != "candidate_research_only":
                errors.append(f"candidate {system_id} must remain research only")
            if not system.get("outputs_to_capture"):
                errors.append(f"candidate {system_id} must retain raw evidence")
            if not system.get("known_risks"):
                errors.append(f"candidate {system_id} must document known risks")

    evaluation = document["evaluation_plan"]
    evaluation_fields = {
        "data_splits",
        "participant_exclusive_splits",
        "thresholds_fixed_before_held_out_evaluation",
        "same_recording_sent_to_every_candidate",
        "provider_outputs_hidden_from_human_annotators",
        "required_metrics",
        "required_evaluation_dimensions",
        "sample_size_rule",
        "provider_agreement_counts_as_reference_truth",
    }
    if _require_fields(evaluation, evaluation_fields, "evaluation_plan", errors):
        if evaluation["data_splits"] != [
                "development", "threshold_tuning", "held_out_evaluation"]:
            errors.append("evaluation must preserve development tuning and held-out splits")
        for field in (
                "participant_exclusive_splits",
                "thresholds_fixed_before_held_out_evaluation",
                "same_recording_sent_to_every_candidate",
                "provider_outputs_hidden_from_human_annotators"):
            if evaluation[field] is not True:
                errors.append(f"evaluation_plan.{field} must remain true")
        if not REQUIRED_EVALUATION_METRICS.issubset(evaluation["required_metrics"]):
            errors.append("evaluation plan is missing required metrics")
        if evaluation["provider_agreement_counts_as_reference_truth"] is not False:
            errors.append("provider agreement cannot count as reference truth")

    failures = document["failure_policy"]
    if not _require_fields(
            failures,
            REQUIRED_FAILURES | {
                "retry_policy", "fallback_to_zero", "fallback_to_llm_judgment"
            },
            "failure_policy",
            errors):
        pass
    else:
        for failure in REQUIRED_FAILURES:
            if failures[failure] != "unavailable":
                errors.append(f"failure_policy.{failure} must become unavailable")
        if failures["fallback_to_zero"] is not False:
            errors.append("pronunciation failures cannot fall back to zero")
        if failures["fallback_to_llm_judgment"] is not False:
            errors.append("pronunciation failures cannot fall back to LLM judgment")

    release = document["release_policy"]
    if _require_fields(
            release,
            REQUIRED_RELEASE_BLOCKS | {
                "research_storage", "future_normal_coaching_limit",
                "unlock_requirements"
            },
            "release_policy",
            errors):
        for field in REQUIRED_RELEASE_BLOCKS:
            if release[field] != "blocked":
                errors.append(f"release_policy.{field} must remain blocked")
        if "separate owner approval" not in release["unlock_requirements"]:
            errors.append("release requires separate owner approval")

    if not isinstance(document["sources"], list) or not document["sources"]:
        errors.append("protocol must retain its research sources")

    return errors


def assert_valid_protocol(document):
    errors = validate_protocol(document)
    if errors:
        raise PronunciationProtocolValidationError("\n".join(errors))
    return document
