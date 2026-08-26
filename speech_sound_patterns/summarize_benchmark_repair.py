"""Build the safe aggregate report for the completed 22D repair work."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from .benchmark import BENCHMARK_REPORT_PATH, PRIVATE_BENCHMARK_ROOT
from .benchmark_meta_ctc import META_CONTRACT_SHA256
from .benchmark_repair import (
    REPAIR_REPORT_PATH,
    validate_repair_report,
)
from .calibrate_benchmark_repair import (
    CTC_SUMMARY_PATH,
    EXPECTED_MANIFEST_PATH,
    RELATION_PATH,
    _load,
)
from .calibrate_benchmark_repair_context import DEFAULT_OUTPUT as CONTEXT_OUTPUT
from .calibrate_benchmark_repair_meta import (
    DEFAULT_OUTPUT as META_CALIBRATION_OUTPUT,
    META_CTC_SUMMARY_PATH,
)
from .feasibility import canonical_json_bytes, file_sha256
from .score_benchmark_repair_repeated import DEFAULT_OUTPUT as REPEATED_OUTPUT
from .score_benchmark_repair_meta_threshold import (
    CONTRACT_SHA256 as META_EXACT_THRESHOLD_CONTRACT_SHA256,
    DEFAULT_OUTPUT as META_EXACT_THRESHOLD_OUTPUT,
)


NUMERIC_CALIBRATION_PATH = (
    PRIVATE_BENCHMARK_ROOT
    / "repair-v1"
    / "evidence"
    / "calibration"
    / "adult-calibration-v1.0.0.json"
)


def _safe_partition(partition):
    return {
        "true_positive": partition["true_positive"],
        "false_positive": partition["false_positive"],
        "false_negative": partition["false_negative"],
        "true_negative": partition["true_negative"],
        "reference_scorable": partition["reference_scorable"],
        "precision": partition["precision"],
        "recall": partition["recall"],
        "false_concerns_per_scorable_opportunity": partition[
            "false_concerns_per_scorable_opportunity"
        ],
        "selection_gates": partition["selection_gates"],
    }


def _gate_count(record):
    return sum(
        bool(value)
        for partition_name in (
            "development_out_of_fold",
            "threshold_tuning",
        )
        for value in record[partition_name]["selection_gates"][
            "checks"
        ].values()
    )


def _ratio_value(partition, name):
    value = partition[name]["value"]
    return -1.0 if value is None else float(value)


def _closest_threshold(records):
    """Choose one descriptive point without changing the frozen selection rule."""
    record = min(
        records,
        key=lambda item: (
            -_gate_count(item),
            -min(
                _ratio_value(item["development_out_of_fold"], "precision"),
                _ratio_value(item["threshold_tuning"], "precision"),
            ),
            -min(
                _ratio_value(item["development_out_of_fold"], "recall"),
                _ratio_value(item["threshold_tuning"], "recall"),
            ),
            (
                item["development_out_of_fold"]["false_positive"]
                + item["threshold_tuning"]["false_positive"]
            ),
            -item["threshold"],
        ),
    )
    return {
        "reporting_rule": (
            "most_frozen_gate_checks_passed_then_highest_worst_partition_"
            "precision_then_recall_then_fewest_false_positives"
        ),
        "threshold": record["threshold"],
        "gate_checks_passed_of_ten": _gate_count(record),
        "both_partitions_pass": record["both_partitions_pass"],
        "development_out_of_fold": _safe_partition(
            record["development_out_of_fold"]
        ),
        "threshold_tuning": _safe_partition(record["threshold_tuning"]),
    }


def _closest_repeated(records):
    selected = min(
        records,
        key=lambda item: (
            -_gate_count(item),
            -min(
                _ratio_value(item["development_out_of_fold"], "precision"),
                _ratio_value(item["threshold_tuning"], "precision"),
            ),
            -min(
                _ratio_value(item["development_out_of_fold"], "recall"),
                _ratio_value(item["threshold_tuning"], "recall"),
            ),
            (
                item["development_out_of_fold"]["false_positive"]
                + item["threshold_tuning"]["false_positive"]
            ),
            -item["configuration"]["opportunity_probability_threshold"],
            -item["configuration"]["minimum_candidates_for_same_expected_sound"],
            -item["configuration"]["minimum_distinct_words"],
            -item["configuration"]["minimum_distinct_clips"],
        ),
    )
    return {
        "reporting_rule": (
            "most_frozen_gate_checks_passed_then_highest_worst_partition_"
            "precision_then_recall_then_fewest_false_positives"
        ),
        "configuration": selected["configuration"],
        "gate_checks_passed_of_ten": _gate_count(selected),
        "both_partitions_pass": selected["both_partitions_pass"],
        "development_out_of_fold": _safe_partition(
            selected["development_out_of_fold"]
        ),
        "threshold_tuning": _safe_partition(selected["threshold_tuning"]),
    }


def _adult_baseline(report, project_split):
    matches = [
        item
        for item in report["expert_phone_relations"]["partitions"]
        if item["project_split"] == project_split
        and item["age_stratum"] == "adult"
    ]
    if len(matches) != 1:
        raise ValueError("frozen baseline adult partition is missing")
    relation = matches[0]["coarse_target_relation"]
    return {
        "true_positive": relation["true_positive"],
        "false_positive": relation["false_positive"],
        "false_negative": relation["false_negative"],
        "true_negative": relation["true_negative"],
        "reference_scorable": relation["reference_scorable"],
        "precision": relation["precision"],
        "recall": relation["recall"],
        "false_concerns_per_scorable_opportunity": relation[
            "false_concerns_per_scorable_opportunity"
        ],
    }


def _positive_distribution(relations):
    result = {}
    for split, expected_participants in (
        ("development", 8),
        ("threshold_tuning", 4),
    ):
        rows = [
            row
            for row in relations["target_rows"]
            if row["project_split"] == split and row["age_stratum"] == "adult"
        ]
        participants = sorted(
            {row["private_participant_id"] for row in rows}
        )
        if len(participants) != expected_participants:
            raise ValueError("adult participant count changed")
        positives = Counter(
            row["private_participant_id"]
            for row in rows
            if row["truth"] == "positive"
        )
        counts = sorted(
            (positives[participant] for participant in participants),
            reverse=True,
        )
        result[split] = {
            "participants": len(participants),
            "participants_with_positive_opportunities": sum(
                count > 0 for count in counts
            ),
            "positive_opportunities": sum(counts),
            "positive_opportunities_per_participant_descending": counts,
        }
    return result


def summarize(output_path=REPAIR_REPORT_PATH):
    baseline = _load(BENCHMARK_REPORT_PATH)
    numeric = _load(NUMERIC_CALIBRATION_PATH)
    context = _load(CONTEXT_OUTPUT)
    repeated = _load(REPEATED_OUTPUT)
    meta_process = _load(META_CTC_SUMMARY_PATH)
    meta = _load(META_CALIBRATION_OUTPUT)
    meta_exact = _load(META_EXACT_THRESHOLD_OUTPUT)
    relations = _load(RELATION_PATH)
    expected_manifest = _load(EXPECTED_MANIFEST_PATH)

    if (
        expected_manifest.get("held_out_participants") != 0
        or relations.get("held_out_evaluation") is not False
        or meta_process["execution"].get("held_out_participants") != 0
        or meta.get("held_out_labels_or_outputs_used") is not False
        or meta.get("meta_contract_sha256") != META_CONTRACT_SHA256
        or meta_exact.get("held_out_labels_or_outputs_used") is not False
        or meta_exact.get("contract_sha256")
        != META_EXACT_THRESHOLD_CONTRACT_SHA256
    ):
        raise ValueError("repair summary received held-out or unfrozen evidence")

    selected_threshold = meta_exact["selected_threshold"]
    selected = selected_threshold is not None
    report = {
        "schema_version": "1.0.0",
        "checkpoint": "22D",
        "status": "local_benchmark_repair_complete_release_locked",
        "purpose": (
            "Record the label-blind local repairs attempted after the frozen "
            "greedy phone comparison produced too many false concerns. This "
            "report supports only a developer review candidate selection or "
            "a no-selection decision."
        ),
        "sample": {
            "clips": 480,
            "development_adult_participants": 8,
            "threshold_tuning_adult_participants": 4,
            "held_out_participants": 0,
            "expert_outcomes_read_by_candidate_runners": False,
            "same_input_repeats": 2,
        },
        "positive_reference_distribution": _positive_distribution(relations),
        "selection_gates": {
            "minimum_precision_point_estimate": 0.75,
            "minimum_precision_wilson_95_lower": 0.5,
            "maximum_false_concerns_per_scorable_opportunity": 0.01,
            "minimum_recall": 0.2,
            "minimum_true_positives": 7,
            "development_and_tuning_both_required": True,
        },
        "candidate_comparisons": [
            {
                "candidate_id": "frozen_greedy_phoneticxeus",
                "method": "sentence_wide_greedy_phone_alignment",
                "development_out_of_fold_average_precision": None,
                "closest_reported_operating_point": {
                    "development": _adult_baseline(baseline, "development"),
                    "threshold_tuning": _adult_baseline(
                        baseline, "threshold_tuning"
                    ),
                },
                "decision": "rejected_too_many_false_concerns",
                "held_out_used": False,
            },
            {
                "candidate_id": "constrained_phoneticxeus_numeric",
                "method": "expected_phone_ctc_alignment_with_numeric_calibration",
                "development_out_of_fold_average_precision": max(
                    item["development_out_of_fold_average_precision"]
                    for item in numeric["regularization_search"]
                ),
                "closest_reported_operating_point": _closest_threshold(
                    numeric["threshold_grid"]
                ),
                "decision": numeric["decision"],
                "held_out_used": False,
            },
            {
                "candidate_id": "constrained_phoneticxeus_contextual",
                "method": "expected_phone_ctc_alignment_with_contextual_calibration",
                "development_out_of_fold_average_precision": context[
                    "selected_configuration"
                ]["development_out_of_fold_average_precision"],
                "closest_reported_operating_point": _closest_threshold(
                    context["threshold_grid"]
                ),
                "decision": context["decision"],
                "held_out_used": False,
            },
            {
                "candidate_id": "constrained_phoneticxeus_repeated_filter",
                "method": "same_expected_sound_across_distinct_words_and_clips",
                "development_out_of_fold_average_precision": context[
                    "selected_configuration"
                ]["development_out_of_fold_average_precision"],
                "closest_reported_operating_point": _closest_repeated(
                    repeated["grid_results"]
                ),
                "decision": repeated["decision"],
                "held_out_used": False,
            },
            {
                "candidate_id": "meta_wav2vec2_constrained_contextual",
                "method": (
                    "full_precision_onnx_expected_phone_ctc_alignment_with_"
                    "contextual_calibration"
                ),
                "development_out_of_fold_average_precision": meta[
                    "selected_configuration"
                ]["development_out_of_fold_average_precision"],
                "closest_reported_operating_point": _closest_threshold(
                    meta_exact["threshold_results"]
                ),
                "coarse_threshold_grid_decision": meta["decision"],
                "exact_threshold_count": meta_exact[
                    "candidate_threshold_count"
                ],
                "decision": meta_exact["decision"],
                "held_out_used": False,
            },
        ],
        "system_decision": {
            "decision": (
                "adult_developer_review_candidate_only"
                if selected
                else "no_system_or_threshold_selected"
            ),
            "selected_system": (
                "meta_wav2vec2_constrained_contextual" if selected else None
            ),
            "selected_threshold": selected_threshold,
            "children_supported": False,
            "insertions_supported": False,
            "paid_provider_evaluated": False,
            "scientific_or_product_release_supported": False,
        },
        "alternative_local_screen": [
            {
                "system": "Meta wav2vec2 multilingual phoneme model",
                "status": "evaluated",
                "reason": (
                    "Apache 2.0 ONNX weights, Common Voice training provenance "
                    "and no SpeechOcean primary benchmark training overlap."
                ),
            },
            {
                "system": "Allosaurus",
                "status": "rejected_before_download",
                "reason": (
                    "GPL 3 code and incomplete separately stated pretrained "
                    "weight terms are not a clean commercial product path."
                ),
            },
            {
                "system": "GOPT",
                "status": "rejected_before_download",
                "reason": (
                    "The released model is trained and evaluated on "
                    "SpeechOcean762 and predicts quality scores rather than "
                    "the required independent phone relations."
                ),
            },
        ],
        "private_evidence": {
            "expected_only_manifest_sha256": file_sha256(
                EXPECTED_MANIFEST_PATH
            ),
            "relation_evidence_sha256": file_sha256(RELATION_PATH),
            "phoneticxeus_ctc_process_sha256": file_sha256(CTC_SUMMARY_PATH),
            "phoneticxeus_numeric_calibration_sha256": file_sha256(
                NUMERIC_CALIBRATION_PATH
            ),
            "phoneticxeus_context_calibration_sha256": file_sha256(
                CONTEXT_OUTPUT
            ),
            "phoneticxeus_repeated_filter_sha256": file_sha256(
                REPEATED_OUTPUT
            ),
            "meta_ctc_process_sha256": file_sha256(META_CTC_SUMMARY_PATH),
            "meta_calibration_sha256": file_sha256(
                META_CALIBRATION_OUTPUT
            ),
            "meta_exact_threshold_sha256": file_sha256(
                META_EXACT_THRESHOLD_OUTPUT
            ),
            "raw_or_row_level_evidence_committed": False,
        },
        "release_boundaries": {
            "normal_pipeline": False,
            "candidate_artifact": False,
            "coaching": False,
            "personal_progress": False,
            "scientific_release": False,
            "product_release": False,
            "screening": False,
            "diagnosis": False,
            "severity": False,
            "cause": False,
            "treatment": False,
        },
        "limitations": [
            (
                "SpeechOcean762 is Mandarin first language read speech and "
                "does not represent Australian or world English."
            ),
            (
                "Adult positive relations are concentrated in four of eight "
                "development participants and one of four tuning participants."
            ),
            (
                "Children have too few positive consensus relations for "
                "selection and remain unsupported."
            ),
            (
                "No positive consensus insertion examples exist in the "
                "frozen sample, so insertions remain unsupported."
            ),
            (
                "Common Voice training lineage means the Meta model is not "
                "independent evidence for the separate Common Voice stress set."
            ),
            (
                "The Meta and ONNX model cards declare Apache 2.0, but product "
                "use still requires a complete provenance and legal review."
            ),
            (
                "The held-out participants remain sealed until checkpoint 22H."
            ),
            (
                "No local result in this report establishes scientific or "
                "product validity."
            ),
        ],
        "next_checkpoint": (
            "22E_paid_api_bake_off_after_owner_commit_and_explicit_approval"
        ),
    }
    errors = validate_repair_report(report)
    if errors:
        raise ValueError("; ".join(errors))
    output_path = Path(output_path)
    if output_path.exists():
        raise ValueError("safe repair report already exists")
    output_path.write_bytes(canonical_json_bytes(report))
    return output_path, report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=REPAIR_REPORT_PATH)
    args = parser.parse_args()
    path, report = summarize(args.output)
    print(f"Repair decision: {report['system_decision']['decision']}")
    print(
        "Selected system: "
        f"{report['system_decision']['selected_system']}"
    )
    print(f"Safe aggregate report: {path.name}")


if __name__ == "__main__":
    main()
