"""Resolve the frozen Meta candidate at every distinct score boundary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .benchmark import PRIVATE_BENCHMARK_ROOT
from .calibrate_benchmark_repair import (
    _confusion,
    _metrics,
    _participant_metrics,
    _load,
)
from .calibrate_benchmark_repair_meta import DEFAULT_OUTPUT as META_OUTPUT
from .benchmark_repair import selection_gate_results
from .feasibility import REPOSITORY_ROOT, canonical_json_bytes, file_sha256


CONTRACT_PATH = Path(__file__).with_name(
    "benchmark-repair-meta-threshold-contract-v1.0.0.json"
)
CONTRACT_SHA256 = (
    "9063be3af105b6409b3f7fb3e1ffd5ddaa85faf998f0ef937df0dfb704584774"
)
DEFAULT_OUTPUT = (
    PRIVATE_BENCHMARK_ROOT
    / "repair-v1"
    / "evidence"
    / "calibration"
    / "adult-meta-exact-threshold-v1.0.0.json"
)


def validate_exact_threshold_contract(document):
    errors = []
    if not isinstance(document, dict):
        return ["exact threshold contract must be an object"]
    if document.get("status") != "rules_frozen_before_exact_threshold_scoring":
        errors.append("exact threshold rules must remain frozen before scoring")
    prior = document.get("prior_result", {})
    if prior.get("failed_result_may_be_rewritten") is not False:
        errors.append("failed coarse threshold result cannot be rewritten")
    inputs = document.get("input_policy", {})
    for field in (
        "held_out_access_allowed",
        "child_rows_allowed",
        "probabilities_may_be_recomputed",
        "model_or_preprocessor_may_be_refit",
        "features_or_categories_may_change",
    ):
        if inputs.get(field) is not False:
            errors.append(f"exact threshold input_policy.{field} must be false")
    threshold = document.get("threshold_policy", {})
    for field in (
        "candidate_thresholds_use_labels",
        "probability_order_may_be_changed",
        "tuning_may_change_model_or_features",
        "held_out_labels_or_outputs_used",
    ):
        if threshold.get(field) is not False:
            errors.append(f"exact threshold {field} must be false")
    if threshold.get("development_and_tuning_both_must_pass") is not True:
        errors.append("exact threshold requires both partitions to pass")
    expected_gates = {
        "minimum_precision_point_estimate": 0.75,
        "minimum_precision_wilson_95_lower": 0.5,
        "maximum_false_concerns_per_scorable_opportunity": 0.01,
        "minimum_recall": 0.2,
        "minimum_true_positives": 7,
        "every_tuning_participant_reported": True,
        "system_selection_if_all_gates_pass": (
            "adult_developer_review_candidate_only"
        ),
        "failure_behavior": "no_system_or_threshold_selected",
    }
    if document.get("selection_gates") != expected_gates:
        errors.append("exact threshold selection gates changed")
    release = document.get("release_boundaries", {})
    if not release or any(value is not False for value in release.values()):
        errors.append("exact threshold release boundaries must remain false")
    return errors


def load_exact_threshold_contract(path=CONTRACT_PATH):
    path = Path(path)
    if file_sha256(path) != CONTRACT_SHA256:
        raise ValueError("frozen exact threshold contract checksum changed")
    document = _load(path)
    errors = validate_exact_threshold_contract(document)
    if errors:
        raise ValueError("; ".join(errors))
    return document


def _threshold_interval(thresholds, selected):
    index = thresholds.index(selected)
    lower = None if index == 0 else thresholds[index - 1]
    return {
        "lower_exclusive": lower,
        "upper_inclusive": selected,
        "width": None if lower is None else round(selected - lower, 9),
    }


def score_exact_thresholds(
    contract_path=CONTRACT_PATH,
    meta_calibration_path=META_OUTPUT,
    output_path=DEFAULT_OUTPUT,
):
    contract = load_exact_threshold_contract(contract_path)
    if file_sha256(meta_calibration_path) != contract["prior_result"][
        "meta_calibration_sha256"
    ]:
        raise ValueError("frozen Meta calibration checksum changed")
    calibration = _load(meta_calibration_path)
    if (
        calibration.get("decision") != "no_system_or_threshold_selected"
        or calibration.get("selected_threshold") is not None
        or calibration.get("held_out_labels_or_outputs_used") is not False
        or calibration.get("child_labels_used_for_training_or_thresholds")
        is not False
    ):
        raise ValueError("exact threshold input is not the frozen failed result")
    selected_configuration = calibration["selected_configuration"]
    if (
        selected_configuration.get("family")
        != contract["prior_result"]["development_selected_model_family"]
        or selected_configuration.get("parameters", {}).get("c")
        != contract["prior_result"]["development_selected_model_c"]
        or selected_configuration.get(
            "development_out_of_fold_average_precision"
        )
        != contract["prior_result"]["development_grouped_average_precision"]
    ):
        raise ValueError("frozen development-selected model changed")

    private_rows = calibration["private_adult_rows"]
    development = [
        {**row, "label": int(row["truth"] == "positive")}
        for row in private_rows
        if row["partition"] == "development_out_of_fold"
    ]
    tuning = [
        {**row, "label": int(row["truth"] == "positive")}
        for row in private_rows
        if row["partition"] == "threshold_tuning"
    ]
    if len(development) != 1971 or len(tuning) != 984:
        raise ValueError("exact threshold adult opportunity counts changed")
    if len({row["private_participant_id"] for row in development}) != 8:
        raise ValueError("exact threshold development participants changed")
    if len({row["private_participant_id"] for row in tuning}) != 4:
        raise ValueError("exact threshold tuning participants changed")
    development_probabilities = [row["probability"] for row in development]
    tuning_probabilities = [row["probability"] for row in tuning]
    thresholds = sorted(
        {
            0.0,
            1.0,
            *development_probabilities,
            *tuning_probabilities,
        }
    )
    records = []
    eligible = []
    gates = contract["selection_gates"]
    for threshold in thresholds:
        development_counts = _confusion(
            development, development_probabilities, threshold
        )
        tuning_counts = _confusion(tuning, tuning_probabilities, threshold)
        development_gate = selection_gate_results(development_counts, gates)
        tuning_gate = selection_gate_results(tuning_counts, gates)
        record = {
            "threshold": threshold,
            "development_out_of_fold": {
                **_metrics(development_counts),
                "selection_gates": development_gate,
            },
            "threshold_tuning": {
                **_metrics(tuning_counts),
                "selection_gates": tuning_gate,
            },
            "both_partitions_pass": (
                development_gate["passed"] and tuning_gate["passed"]
            ),
        }
        records.append(record)
        if record["both_partitions_pass"]:
            eligible.append(record)

    if eligible:
        selected_record = min(
            eligible,
            key=lambda item: (
                -item["threshold_tuning"]["recall"]["value"],
                -item["threshold_tuning"]["precision"]["value"],
                -item["threshold"],
            ),
        )
        selected_threshold = selected_record["threshold"]
        selected_metrics = {
            "development_out_of_fold": {
                **_metrics(
                    _confusion(
                        development,
                        development_probabilities,
                        selected_threshold,
                    )
                ),
                "participants": _participant_metrics(
                    development,
                    development_probabilities,
                    selected_threshold,
                ),
            },
            "threshold_tuning": {
                **_metrics(
                    _confusion(
                        tuning,
                        tuning_probabilities,
                        selected_threshold,
                    )
                ),
                "participants": _participant_metrics(
                    tuning,
                    tuning_probabilities,
                    selected_threshold,
                ),
            },
        }
        selected_interval = _threshold_interval(
            thresholds, selected_threshold
        )
        decision = "adult_developer_review_candidate_only"
    else:
        selected_threshold = None
        selected_metrics = None
        selected_interval = None
        decision = "no_system_or_threshold_selected"

    output = {
        "schema_version": "1.0.0",
        "score_id": "adult_meta_exact_threshold_resolution_v1",
        "contract_sha256": CONTRACT_SHA256,
        "meta_calibration_sha256": file_sha256(meta_calibration_path),
        "held_out_labels_or_outputs_used": False,
        "child_rows_used": False,
        "model_or_probabilities_recomputed": False,
        "candidate_threshold_count": len(thresholds),
        "selected_threshold": selected_threshold,
        "selected_threshold_interval": selected_interval,
        "selected_metrics": selected_metrics,
        "eligible_threshold_count": len(eligible),
        "threshold_results": records,
        "decision": decision,
        "claim_boundaries": {
            "child_candidate": False,
            "insertion_candidate": False,
            "normal_pipeline": False,
            "candidate_artifact": False,
            "scientific_or_product_release": False,
        },
    }
    output_path = Path(output_path).resolve(strict=False)
    output_path.relative_to(PRIVATE_BENCHMARK_ROOT.resolve())
    if output_path.exists():
        raise ValueError("exact threshold evidence already exists")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(canonical_json_bytes(output))
    return output_path, output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, default=CONTRACT_PATH)
    parser.add_argument(
        "--meta-calibration", type=Path, default=META_OUTPUT
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    path, output = score_exact_thresholds(
        args.contract, args.meta_calibration, args.output
    )
    print(
        f"Exact candidate thresholds: {output['candidate_threshold_count']}"
    )
    print(f"Eligible thresholds: {output['eligible_threshold_count']}")
    print(f"Selected threshold: {output['selected_threshold']}")
    print(f"Decision: {output['decision']}")
    print(f"Private threshold evidence: {path.relative_to(REPOSITORY_ROOT)}")


if __name__ == "__main__":
    main()
