"""Validation and scoring primitives for the conservative 22D repair."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from .benchmark import (
    FROZEN_BENCHMARK_MANIFEST_SHA256,
    FROZEN_BENCHMARK_REPORT_SHA256,
)
from .feasibility import canonical_json_bytes


MODULE_ROOT = Path(__file__).parent
REPAIR_CONTRACT_PATH = MODULE_ROOT / "benchmark-repair-contract-v1.0.0.json"
REPAIR_SCHEMA_VERSION = "1.0.0"
FROZEN_EXPECTED_MANIFEST_SHA256 = (
    "c918feffa7c0a3a3fa99ce7a9e028621e8fb002980777297f30088e5975331da"
)
NUMERIC_FEATURES = {
    "forced_path_expected_log_posterior",
    "best_expected_variant_log_posterior",
    "best_competing_consonant_log_posterior",
    "expected_variant_margin",
    "expected_variant_peak_posterior",
    "expected_variant_top_one_frame_rate",
    "forced_span_frame_count",
    "forced_span_duration_seconds",
    "greedy_alignment_relation_indicator",
    "competing_panphon_feature_difference_rate",
    "greedy_observed_panphon_feature_difference_rate",
}
RELEASE_BOUNDARIES = {
    "normal_pipeline",
    "candidate_artifact",
    "coaching",
    "personal_progress",
    "scientific_release",
    "product_release",
    "screening",
    "diagnosis",
    "severity",
    "cause",
    "treatment",
}
REPAIR_REPORT_PATH = MODULE_ROOT / "local-benchmark-repair-v1.0.0.json"
REPAIR_COMPARISON_IDS = {
    "frozen_greedy_phoneticxeus",
    "constrained_phoneticxeus_numeric",
    "constrained_phoneticxeus_contextual",
    "constrained_phoneticxeus_repeated_filter",
    "meta_wav2vec2_constrained_contextual",
}


def canonical_json_sha256(document):
    return hashlib.sha256(canonical_json_bytes(document)).hexdigest()


def load_repair_contract(path=REPAIR_CONTRACT_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_repair_contract(document):
    """Return every structural or safety error in the frozen repair rules."""
    errors = []
    required = {
        "schema_version",
        "repair_id",
        "status",
        "purpose",
        "baseline",
        "input_policy",
        "feature_extractor",
        "calibration_policy",
        "selection_gates",
        "report_policy",
        "release_boundaries",
    }
    if not isinstance(document, dict):
        return ["repair contract must be an object"]
    if set(document) != required:
        errors.append("repair contract fields do not match the frozen schema")
        if not required.issubset(document):
            return errors
    if document["schema_version"] != REPAIR_SCHEMA_VERSION:
        errors.append("repair contract schema is unsupported")
    if document["status"] != "rules_frozen_before_repair_feature_scoring":
        errors.append("repair rules must remain frozen before feature scoring")

    baseline = document["baseline"]
    if (
        baseline.get("report_path") != "local-benchmark-v1.0.0.json"
        or baseline.get("report_sha256") != FROZEN_BENCHMARK_REPORT_SHA256
        or baseline.get("baseline_may_be_rewritten") is not False
    ):
        errors.append("the failed frozen baseline cannot be rewritten")

    inputs = document["input_policy"]
    if (
        inputs.get("private_benchmark_manifest_sha256")
        != FROZEN_BENCHMARK_MANIFEST_SHA256
        or inputs.get("expected_only_manifest_sha256")
        != FROZEN_EXPECTED_MANIFEST_SHA256
        or inputs.get("expected_only_clip_count") != 480
    ):
        errors.append("repair input identities changed")
    if set(inputs.get("allowed_project_splits", [])) != {
        "development",
        "threshold_tuning",
    }:
        errors.append("repair inputs must remain development and tuning only")
    for field in (
        "held_out_access_allowed",
        "candidate_runner_may_read_expert_outcomes",
    ):
        if inputs.get(field) is not False:
            errors.append(f"input_policy.{field} must remain false")

    extractor = document["feature_extractor"]
    if extractor.get("system") != (
        "phoneticxeus_8d83dee94817a07dc150f87d08f7e0ee01bdb66d"
    ):
        errors.append("repair feature system changed")
    if (
        extractor.get("backend") != "mps"
        or extractor.get("same_input_repeats") != 2
        or extractor.get("blank_token_id") != 0
    ):
        errors.append("repair feature execution settings changed")
    for field in (
        "network_access",
        "silent_cpu_fallback",
        "full_logits_committed",
        "feature_values_are_calibrated_confidence",
        "forced_alignment_verifies_production",
    ):
        if extractor.get(field) is not False:
            errors.append(f"feature_extractor.{field} must remain false")
    if set(extractor.get("numeric_features", [])) != NUMERIC_FEATURES:
        errors.append("repair numeric feature set changed after freezing")
    if extractor.get("numeric_preprocessing") != {
        "only_nullable_feature": (
            "greedy_observed_panphon_feature_difference_rate"
        ),
        "nullable_feature_fixed_imputation": 1.0,
        "standardization": (
            "development_training_fold_mean_and_population_standard_deviation"
        ),
        "zero_variance_scaled_value": 0.0,
        "tuning_values_may_fit_preprocessing": False,
    }:
        errors.append("repair numeric preprocessing changed after freezing")

    calibration = document["calibration_policy"]
    if calibration.get("eligible_population") != "source_adults_only":
        errors.append("repair calibration must remain adult-only")
    if calibration.get("child_labels_used_for_training_or_thresholds") is not False:
        errors.append("child labels cannot train or tune this repair")
    if (
        calibration.get("training_split") != "development"
        or calibration.get("threshold_split") != "threshold_tuning"
        or calibration.get("participant_grouping_required") is not True
    ):
        errors.append("repair training and threshold partitions changed")
    if calibration.get("fixed_regularization_candidates") != [
        0.01,
        0.1,
        1.0,
        10.0,
    ]:
        errors.append("repair regularization candidates changed")
    if calibration.get("fixed_random_state") != 2204:
        errors.append("repair random state changed")
    threshold_grid = calibration.get("threshold_grid", {})
    if threshold_grid != {"minimum": 0.0, "maximum": 1.0, "step": 0.01}:
        errors.append("repair threshold grid changed")
    for field in (
        "tuning_labels_may_change_feature_set_or_regularization",
        "coefficients_refit_after_tuning",
        "held_out_labels_or_outputs_used",
    ):
        if calibration.get(field) is not False:
            errors.append(f"calibration_policy.{field} must remain false")

    gates = document["selection_gates"]
    expected_gates = {
        "minimum_precision_point_estimate": 0.75,
        "minimum_precision_wilson_95_lower": 0.5,
        "maximum_false_concerns_per_scorable_opportunity": 0.01,
        "minimum_recall": 0.2,
        "minimum_true_positives": 7,
    }
    for field, expected in expected_gates.items():
        if gates.get(field) != expected:
            errors.append(f"selection_gates.{field} changed")
    for field in (
        "development_out_of_fold_and_tuning_both_required",
        "same_input_target_features_exact",
        "every_tuning_participant_reported",
    ):
        if gates.get(field) is not True:
            errors.append(f"selection_gates.{field} must remain true")

    report = document["report_policy"]
    for field in (
        "development_and_tuning_separate",
        "adult_and_child_separate",
        "visible_denominators",
        "participant_distribution_required",
        "baseline_comparison_required",
    ):
        if report.get(field) is not True:
            errors.append(f"report_policy.{field} must remain true")
    for field in ("private_rows_committed", "held_out_fields_allowed"):
        if report.get(field) is not False:
            errors.append(f"report_policy.{field} must remain false")

    boundaries = document["release_boundaries"]
    if set(boundaries) != RELEASE_BOUNDARIES or any(
        boundaries.get(field) is not False for field in RELEASE_BOUNDARIES
    ):
        errors.append("every repair release boundary must remain false")
    return errors


def validate_expected_only_manifest(document):
    """Ensure candidate inference input cannot carry expert outcomes."""
    errors = []
    required = {
        "schema_version",
        "expected_manifest_id",
        "private_benchmark_manifest_sha256",
        "source_id",
        "source_reference_sha256",
        "selection_used_expert_labels_or_model_outputs",
        "expert_outcomes_included",
        "held_out_participants",
        "clips",
    }
    if not isinstance(document, dict) or set(document) != required:
        return ["expected-only manifest fields do not match the private schema"]
    if document["schema_version"] != "1.0.0":
        errors.append("expected-only manifest schema is unsupported")
    if document["private_benchmark_manifest_sha256"] != (
        FROZEN_BENCHMARK_MANIFEST_SHA256
    ):
        errors.append("expected-only manifest does not bind the frozen sample")
    for field in (
        "selection_used_expert_labels_or_model_outputs",
        "expert_outcomes_included",
    ):
        if document[field] is not False:
            errors.append(f"expected-only manifest {field} must remain false")
    if document["held_out_participants"] != 0:
        errors.append("expected-only manifest cannot contain held-out participants")
    clips = document["clips"]
    if not isinstance(clips, list) or len(clips) != 480:
        errors.append("expected-only manifest must contain 480 clips")
        return errors
    forbidden = {
        "five_reviewer_phone_strings",
        "aggregate_mispronunciations",
        "reviewer_states",
        "reference_decision",
        "truth",
        "prediction",
        "pronounced-phone",
    }

    def inspect(value):
        if isinstance(value, dict):
            if forbidden & set(value):
                return False
            return all(inspect(item) for item in value.values())
        if isinstance(value, list):
            return all(inspect(item) for item in value)
        return True

    if not inspect(document):
        errors.append("expected-only manifest contains expert outcome fields")
    if any(
        clip.get("project_split") not in {"development", "threshold_tuning"}
        for clip in clips
    ):
        errors.append("expected-only manifest contains an ineligible split")
    if len({clip.get("safe_id") for clip in clips}) != 480:
        errors.append("expected-only manifest safe IDs are not unique")
    return errors


def wilson_lower(numerator, denominator, z=1.959963984540054):
    if denominator <= 0:
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
    return max(0.0, center - margin)


def selection_gate_results(counts, gates):
    """Evaluate the frozen conservative selection gates for one partition."""
    true_positive = counts["true_positive"]
    false_positive = counts["false_positive"]
    false_negative = counts["false_negative"]
    scorable = counts["reference_scorable"]
    precision_denominator = true_positive + false_positive
    recall_denominator = true_positive + false_negative
    precision = (
        None if precision_denominator == 0 else true_positive / precision_denominator
    )
    recall = None if recall_denominator == 0 else true_positive / recall_denominator
    false_concern_rate = None if scorable == 0 else false_positive / scorable
    results = {
        "precision_point_estimate": (
            precision is not None
            and precision >= gates["minimum_precision_point_estimate"]
        ),
        "precision_wilson_95_lower": (
            precision_denominator > 0
            and wilson_lower(true_positive, precision_denominator)
            >= gates["minimum_precision_wilson_95_lower"]
        ),
        "false_concern_rate": (
            false_concern_rate is not None
            and false_concern_rate
            <= gates["maximum_false_concerns_per_scorable_opportunity"]
        ),
        "recall": recall is not None and recall >= gates["minimum_recall"],
        "true_positives": true_positive >= gates["minimum_true_positives"],
    }
    return {
        "passed": all(results.values()),
        "checks": results,
        "precision": precision,
        "precision_wilson_95_lower": wilson_lower(
            true_positive, precision_denominator
        ),
        "recall": recall,
        "false_concern_rate": false_concern_rate,
    }


def validate_repair_report(document):
    """Reject private evidence, weakened gates, or unsupported release claims."""
    errors = []
    required = {
        "schema_version",
        "checkpoint",
        "status",
        "purpose",
        "sample",
        "positive_reference_distribution",
        "selection_gates",
        "candidate_comparisons",
        "system_decision",
        "alternative_local_screen",
        "private_evidence",
        "release_boundaries",
        "limitations",
        "next_checkpoint",
    }
    if not isinstance(document, dict):
        return ["repair report must be an object"]
    if set(document) != required:
        errors.append("repair report fields do not match the aggregate schema")
        if not required.issubset(document):
            return errors
    if document["schema_version"] != "1.0.0" or document["checkpoint"] != "22D":
        errors.append("repair report identity is invalid")
    if document["status"] != "local_benchmark_repair_complete_release_locked":
        errors.append("repair report must remain release locked")
    if document["sample"] != {
        "clips": 480,
        "development_adult_participants": 8,
        "threshold_tuning_adult_participants": 4,
        "held_out_participants": 0,
        "expert_outcomes_read_by_candidate_runners": False,
        "same_input_repeats": 2,
    }:
        errors.append("repair report sample scope changed")
    expected_gates = {
        "minimum_precision_point_estimate": 0.75,
        "minimum_precision_wilson_95_lower": 0.5,
        "maximum_false_concerns_per_scorable_opportunity": 0.01,
        "minimum_recall": 0.2,
        "minimum_true_positives": 7,
        "development_and_tuning_both_required": True,
    }
    if document["selection_gates"] != expected_gates:
        errors.append("repair report selection gates changed")
    comparisons = document["candidate_comparisons"]
    if (
        not isinstance(comparisons, list)
        or {item.get("candidate_id") for item in comparisons}
        != REPAIR_COMPARISON_IDS
        or any(item.get("held_out_used") is not False for item in comparisons)
    ):
        errors.append("repair report candidate comparisons are incomplete")
    decision = document["system_decision"]
    if decision.get("paid_provider_evaluated") is not False:
        errors.append("repair report cannot claim a paid provider evaluation")
    selected = decision.get("selected_system")
    threshold = decision.get("selected_threshold")
    if selected is None:
        if threshold is not None or decision.get("decision") != (
            "no_system_or_threshold_selected"
        ):
            errors.append("repair report no-selection decision is inconsistent")
    elif (
        selected != "meta_wav2vec2_constrained_contextual"
        or not isinstance(threshold, (int, float))
        or isinstance(threshold, bool)
        or decision.get("decision") != "adult_developer_review_candidate_only"
    ):
        errors.append("repair report selected-system decision is unsupported")
    boundaries = document["release_boundaries"]
    if set(boundaries) != RELEASE_BOUNDARIES or any(
        boundaries.get(field) is not False for field in RELEASE_BOUNDARIES
    ):
        errors.append("repair report release boundaries must all remain false")
    if document["next_checkpoint"] != (
        "22E_paid_api_bake_off_after_owner_commit_and_explicit_approval"
    ):
        errors.append("repair report next checkpoint bypasses owner approval")

    forbidden_keys = {
        "safe_id",
        "private_participant_id",
        "output_path",
        "canonical_audio_path",
        "target_features",
        "private_adult_rows",
        "eligible_groups",
        "word_index",
        "local_index",
        "probability",
        "audio",
        "logits",
    }

    def inspect(value):
        if isinstance(value, dict):
            if forbidden_keys & set(value):
                return False
            return all(inspect(item) for item in value.values())
        if isinstance(value, list):
            return all(inspect(item) for item in value)
        return True

    if not inspect(document):
        errors.append("repair report contains private or row-level evidence")
    return errors
