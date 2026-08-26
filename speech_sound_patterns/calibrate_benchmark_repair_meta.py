"""Calibrate the frozen Meta local alternative without accessing held-out data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .benchmark import PRIVATE_BENCHMARK_ROOT
from .benchmark_meta_ctc import (
    META_CONTRACT_PATH,
    META_CONTRACT_SHA256,
    load_meta_contract,
)
from .calibrate_benchmark_repair import (
    EXPECTED_MANIFEST_PATH,
    RELATION_PATH,
    _confusion,
    _join_truth,
    _load,
    _metrics,
    _participant_metrics,
    _threshold_records,
)
from .calibrate_benchmark_repair_context import (
    CONTEXT_CONTRACT_PATH,
    _candidate_configurations,
    _compare_models,
    _fit,
    _load_context_contract,
    _matrix,
    _predict,
)
from .feasibility import REPOSITORY_ROOT, canonical_json_bytes, file_sha256


META_CTC_SUMMARY_PATH = (
    PRIVATE_BENCHMARK_ROOT
    / "repair-v1"
    / "evidence"
    / "meta-official"
    / "meta-ctc-process.json"
)
DEFAULT_OUTPUT = (
    PRIVATE_BENCHMARK_ROOT
    / "repair-v1"
    / "evidence"
    / "calibration"
    / "adult-meta-calibration-v1.0.0.json"
)


def _load_meta_rows(expected_manifest, ctc_summary, numeric_names, categorical_names):
    expected = {clip["safe_id"]: clip for clip in expected_manifest["clips"]}
    if len(expected) != 480 or set(expected) != {
        item["safe_id"] for item in ctc_summary["clips"]
    }:
        raise ValueError("expected-only and Meta feature indexes differ")
    rows = {}
    for item in ctc_summary["clips"]:
        path = REPOSITORY_ROOT / item["output_path"]
        if file_sha256(path) != item["output_sha256"]:
            raise ValueError(f"Meta feature record changed: {item['safe_id']}")
        record = _load(path)
        if (
            record.get("same_input_target_features_exact") is not True
            or record.get("claim_boundaries", {}).get(
                "candidate_runner_read_expert_outcomes"
            )
            is not False
            or record.get("meta_contract_sha256") != META_CONTRACT_SHA256
        ):
            raise ValueError("Meta feature evidence violates its frozen boundary")
        clip = expected[item["safe_id"]]
        for target in record["target_features"]:
            key = (
                item["safe_id"],
                target["word_index"],
                target["local_index"],
            )
            if key in rows:
                raise ValueError("Meta target feature key is duplicated")
            numeric = []
            for name in numeric_names:
                value = target.get(name)
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    raise ValueError(f"Meta feature is not numeric: {name}")
                numeric.append(float(value))
            categories = []
            for name in categorical_names:
                value = (
                    target.get("arpabet")
                    if name == "expected_arpabet"
                    else target.get(name)
                )
                if not isinstance(value, str) or not value:
                    raise ValueError(f"Meta category is invalid: {name}")
                categories.append(value)
            rows[key] = {
                "safe_id": item["safe_id"],
                "private_participant_id": clip["private_participant_id"],
                "project_split": clip["project_split"],
                "source_stratum": clip["source_stratum"],
                "age_stratum": (
                    "adult"
                    if clip["source_stratum"].startswith("source_adult_")
                    else "child"
                ),
                "word_index": target["word_index"],
                "local_index": target["local_index"],
                "arpabet": target["arpabet"],
                "features": numeric,
                "categories": categories,
            }
    return rows


def calibrate_meta(
    meta_contract_path=META_CONTRACT_PATH,
    expected_manifest_path=EXPECTED_MANIFEST_PATH,
    ctc_summary_path=META_CTC_SUMMARY_PATH,
    relation_path=RELATION_PATH,
    output_path=DEFAULT_OUTPUT,
):
    import sklearn

    contract = load_meta_contract(meta_contract_path)
    context_contract = _load_context_contract(CONTEXT_CONTRACT_PATH)
    if file_sha256(CONTEXT_CONTRACT_PATH) != contract["prior_repair"][
        "context_contract_sha256"
    ]:
        raise ValueError("frozen contextual comparison contract changed")
    if file_sha256(expected_manifest_path) != contract["input_policy"][
        "expected_only_manifest_sha256"
    ]:
        raise ValueError("Meta expected-only input checksum changed")
    expected_manifest = _load(expected_manifest_path)
    ctc_summary = _load(ctc_summary_path)
    relations = _load(relation_path)
    if (
        expected_manifest.get("held_out_participants") != 0
        or ctc_summary.get("execution", {}).get("clip_count") != 480
        or ctc_summary.get("execution", {}).get("held_out_participants") != 0
        or ctc_summary.get("execution", {}).get(
            "expert_outcomes_read_by_candidate_runner"
        )
        is not False
        or relations.get("held_out_evaluation") is not False
    ):
        raise ValueError("Meta calibration cannot access held-out evidence")
    if ctc_summary.get("meta_contract_sha256") != META_CONTRACT_SHA256:
        raise ValueError("Meta process did not use the frozen contract")

    numeric_names = contract["feature_extractor"]["numeric_features"]
    categorical_names = contract["feature_extractor"]["categorical_features"]
    feature_rows = _load_meta_rows(
        expected_manifest,
        ctc_summary,
        numeric_names,
        categorical_names,
    )
    joined = _join_truth(feature_rows, relations)
    development = [
        row
        for row in joined
        if row["project_split"] == "development"
        and row["age_stratum"] == "adult"
    ]
    tuning = [
        row
        for row in joined
        if row["project_split"] == "threshold_tuning"
        and row["age_stratum"] == "adult"
    ]
    if len(development) != 1971 or len(tuning) != 984:
        raise ValueError("Meta adult opportunity counts changed")

    model_policy = context_contract["model_comparison"]
    minimum_frequency = contract["calibration_policy"][
        "categorical_preprocessing"
    ]["minimum_frequency"]
    configurations = _candidate_configurations(context_contract)
    (
        selected,
        development_probabilities,
        comparisons,
        development_features,
        development_labels,
    ) = _compare_models(
        development,
        configurations,
        model_policy["fixed_random_state"],
        len(numeric_names),
        len(categorical_names),
        minimum_frequency,
    )
    final_preprocessor, final_classifier = _fit(
        development_features,
        development_labels,
        selected,
        model_policy["fixed_random_state"],
        len(numeric_names),
        len(categorical_names),
        minimum_frequency,
    )
    tuning_probabilities = _predict(
        final_preprocessor, final_classifier, _matrix(tuning)
    )
    selected_threshold, threshold_records = _threshold_records(
        development,
        development_probabilities,
        tuning,
        tuning_probabilities,
        contract["selection_gates"],
    )

    if selected_threshold is None:
        selected_metrics = None
        child_diagnostics = None
    else:
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
        child_diagnostics = {}
        for split in ("development", "threshold_tuning"):
            children = [
                row
                for row in joined
                if row["project_split"] == split
                and row["age_stratum"] == "child"
            ]
            child_probabilities = _predict(
                final_preprocessor, final_classifier, _matrix(children)
            )
            child_diagnostics[split] = {
                **_metrics(
                    _confusion(
                        children,
                        child_probabilities,
                        selected_threshold,
                    )
                ),
                "adult_model_only_not_selected_for_children": True,
            }

    private_rows = []
    for partition, rows, probabilities in (
        ("development_out_of_fold", development, development_probabilities),
        ("threshold_tuning", tuning, tuning_probabilities),
    ):
        for row, probability in zip(rows, probabilities):
            private_rows.append(
                {
                    "safe_id": row["safe_id"],
                    "private_participant_id": row["private_participant_id"],
                    "partition": partition,
                    "word_index": row["word_index"],
                    "local_index": row["local_index"],
                    "arpabet": row["arpabet"],
                    "truth": row["truth"],
                    "probability": round(float(probability), 9),
                }
            )

    output = {
        "schema_version": "1.0.0",
        "calibration_id": "adult_meta_local_candidate_comparison_v1",
        "meta_contract_sha256": META_CONTRACT_SHA256,
        "expected_only_manifest_sha256": contract["input_policy"][
            "expected_only_manifest_sha256"
        ],
        "ctc_process_sha256": file_sha256(ctc_summary_path),
        "relation_evidence_sha256": file_sha256(relation_path),
        "held_out_labels_or_outputs_used": False,
        "child_labels_used_for_training_or_thresholds": False,
        "participant_identity_used_as_feature": False,
        "numeric_feature_names": numeric_names,
        "categorical_feature_names": categorical_names,
        "sklearn_version": sklearn.__version__,
        "model_comparison": comparisons,
        "selected_configuration": {
            key: value for key, value in selected.items() if key != "folds"
        },
        "threshold_grid": threshold_records,
        "selected_threshold": selected_threshold,
        "selected_metrics": selected_metrics,
        "child_diagnostics": child_diagnostics,
        "private_adult_rows": private_rows,
        "decision": (
            "adult_developer_review_candidate_only"
            if selected_threshold is not None
            else "no_system_or_threshold_selected"
        ),
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
        raise ValueError("Meta calibration evidence already exists")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(canonical_json_bytes(output))
    return output_path, output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--meta-contract", type=Path, default=META_CONTRACT_PATH
    )
    parser.add_argument(
        "--expected-manifest", type=Path, default=EXPECTED_MANIFEST_PATH
    )
    parser.add_argument(
        "--ctc-summary", type=Path, default=META_CTC_SUMMARY_PATH
    )
    parser.add_argument("--relations", type=Path, default=RELATION_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    path, document = calibrate_meta(
        args.meta_contract,
        args.expected_manifest,
        args.ctc_summary,
        args.relations,
        args.output,
    )
    selected = document["selected_configuration"]
    print(f"Meta family: {selected['family']}")
    print(
        "Development grouped average precision: "
        f"{selected['development_out_of_fold_average_precision']}"
    )
    print(f"Selected threshold: {document['selected_threshold']}")
    print(f"Decision: {document['decision']}")
    print(f"Private calibration: {path.relative_to(REPOSITORY_ROOT)}")


if __name__ == "__main__":
    main()
