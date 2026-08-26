"""Calibrate the conservative adult repair without accessing held-out data."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from .benchmark import (
    PRIVATE_BENCHMARK_ROOT,
    ratio_record,
)
from .benchmark_repair import (
    FROZEN_EXPECTED_MANIFEST_SHA256,
    load_repair_contract,
    selection_gate_results,
    validate_repair_contract,
)
from .feasibility import REPOSITORY_ROOT, canonical_json_bytes, file_sha256


EXPECTED_MANIFEST_PATH = (
    PRIVATE_BENCHMARK_ROOT / "repair-v1" / "expected-only-manifest-v1.0.0.json"
)
CTC_ROOT = PRIVATE_BENCHMARK_ROOT / "repair-v1" / "evidence" / "ctc-official"
CTC_SUMMARY_PATH = CTC_ROOT / "phoneticxeus-ctc-process.json"
RELATION_PATH = (
    PRIVATE_BENCHMARK_ROOT
    / "v1"
    / "evidence"
    / "scoring"
    / "speechocean-relation-evidence.json"
)
DEFAULT_OUTPUT = (
    PRIVATE_BENCHMARK_ROOT
    / "repair-v1"
    / "evidence"
    / "calibration"
    / "adult-calibration-v1.0.0.json"
)


def _load(path):
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"repair evidence is missing: {path.name}")
    return json.loads(path.read_text(encoding="utf-8"))


def _feature_vector(row, feature_names):
    values = []
    for name in feature_names:
        value = row.get(name)
        if value is None:
            if name != "greedy_observed_panphon_feature_difference_rate":
                raise ValueError(f"unexpected missing repair feature: {name}")
            value = 1.0
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError(f"repair feature is not numeric: {name}")
        values.append(float(value))
    return values


def _load_feature_rows(expected_manifest, ctc_summary, feature_names):
    expected = {clip["safe_id"]: clip for clip in expected_manifest["clips"]}
    if len(expected) != 480 or set(expected) != {
        item["safe_id"] for item in ctc_summary["clips"]
    }:
        raise ValueError("expected-only and constrained feature indexes differ")
    rows = {}
    for item in ctc_summary["clips"]:
        path = REPOSITORY_ROOT / item["output_path"]
        if file_sha256(path) != item["output_sha256"]:
            raise ValueError(f"constrained feature record changed: {item['safe_id']}")
        record = _load(path)
        if (
            record.get("same_input_target_features_exact") is not True
            or record.get("claim_boundaries", {}).get(
                "candidate_runner_read_expert_outcomes"
            )
            is not False
        ):
            raise ValueError("constrained feature evidence violates its boundary")
        clip = expected[item["safe_id"]]
        for target in record["target_features"]:
            key = (
                item["safe_id"],
                target["word_index"],
                target["local_index"],
            )
            if key in rows:
                raise ValueError("constrained target feature key is duplicated")
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
                "features": _feature_vector(target, feature_names),
            }
    return rows


def _join_truth(feature_rows, relations):
    joined = []
    for relation in relations["target_rows"]:
        key = (
            relation["safe_id"],
            relation["word_index"],
            relation["target_index"],
        )
        feature = feature_rows.get(key)
        if feature is None:
            raise ValueError("expert target row has no constrained feature row")
        if (
            feature["private_participant_id"]
            != relation["private_participant_id"]
            or feature["project_split"] != relation["project_split"]
            or feature["age_stratum"] != relation["age_stratum"]
            or feature["arpabet"] != relation["reference_phone"]
        ):
            raise ValueError("expert target and constrained feature identity differ")
        if relation["truth"] == "unscorable":
            continue
        joined.append(
            {
                **feature,
                "truth": relation["truth"],
                "label": int(relation["truth"] == "positive"),
            }
        )
    if not joined:
        raise ValueError("repair calibration has no scorable rows")
    return joined


def _confusion(rows, probabilities, threshold):
    counts = Counter()
    for row, probability in zip(rows, probabilities):
        positive = probability >= threshold
        if row["label"] == 1 and positive:
            counts["true_positive"] += 1
        elif row["label"] == 1:
            counts["false_negative"] += 1
        elif positive:
            counts["false_positive"] += 1
        else:
            counts["true_negative"] += 1
        counts["reference_scorable"] += 1
    for name in (
        "true_positive",
        "false_positive",
        "false_negative",
        "true_negative",
        "reference_scorable",
    ):
        counts[name] += 0
    return dict(counts)


def _metrics(counts):
    true_positive = counts["true_positive"]
    false_positive = counts["false_positive"]
    false_negative = counts["false_negative"]
    scorable = counts["reference_scorable"]
    precision = ratio_record(true_positive, true_positive + false_positive)
    recall = ratio_record(true_positive, true_positive + false_negative)
    false_concern = ratio_record(false_positive, scorable)
    return {
        **counts,
        "precision": precision,
        "recall": recall,
        "false_concerns_per_scorable_opportunity": false_concern,
    }


def _participant_metrics(rows, probabilities, threshold):
    grouped = defaultdict(lambda: ([], []))
    for row, probability in zip(rows, probabilities):
        group_rows, group_probabilities = grouped[row["private_participant_id"]]
        group_rows.append(row)
        group_probabilities.append(probability)
    result = []
    for participant_id in sorted(grouped):
        group_rows, group_probabilities = grouped[participant_id]
        result.append(
            {
                "private_participant_id": participant_id,
                **_metrics(
                    _confusion(group_rows, group_probabilities, threshold)
                ),
            }
        )
    return result


def _fit_logistic(features, labels, c, random_state):
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    scaler = StandardScaler()
    scaled = scaler.fit_transform(features)
    model = LogisticRegression(
        C=c,
        class_weight="balanced",
        solver="liblinear",
        random_state=random_state,
        max_iter=2000,
    )
    model.fit(scaled, labels)
    return scaler, model


def _predict(scaler, model, features):
    return model.predict_proba(scaler.transform(features))[:, 1]


def _select_regularization(rows, feature_names, candidates, random_state):
    import numpy as np
    from sklearn.metrics import average_precision_score
    from sklearn.model_selection import GroupKFold

    features = np.asarray([row["features"] for row in rows], dtype=float)
    labels = np.asarray([row["label"] for row in rows], dtype=int)
    groups = np.asarray(
        [row["private_participant_id"] for row in rows], dtype=object
    )
    if len(set(groups)) != 8:
        raise ValueError("adult development calibration requires eight participants")
    folds = list(GroupKFold(n_splits=4).split(features, labels, groups))
    records = []
    probability_by_c = {}
    for c in candidates:
        probabilities = np.zeros(len(rows), dtype=float)
        fold_records = []
        for fold_index, (train_indexes, test_indexes) in enumerate(folds):
            train_groups = sorted(set(groups[train_indexes]))
            test_groups = sorted(set(groups[test_indexes]))
            if set(train_groups) & set(test_groups):
                raise ValueError("participant leaked across a development fold")
            scaler, model = _fit_logistic(
                features[train_indexes],
                labels[train_indexes],
                c,
                random_state,
            )
            fold_probabilities = _predict(
                scaler, model, features[test_indexes]
            )
            probabilities[test_indexes] = fold_probabilities
            fold_records.append(
                {
                    "fold_index": fold_index,
                    "training_participants": train_groups,
                    "validation_participants": test_groups,
                    "validation_rows": len(test_indexes),
                    "validation_positive_rows": int(labels[test_indexes].sum()),
                }
            )
        average_precision = float(average_precision_score(labels, probabilities))
        records.append(
            {
                "c": c,
                "development_out_of_fold_average_precision": round(
                    average_precision, 9
                ),
                "folds": fold_records,
            }
        )
        probability_by_c[c] = probabilities
    selected = min(
        records,
        key=lambda item: (
            -item["development_out_of_fold_average_precision"],
            item["c"],
        ),
    )
    return (
        selected["c"],
        probability_by_c[selected["c"]],
        records,
        features,
        labels,
    )


def _threshold_records(
    development_rows,
    development_probabilities,
    tuning_rows,
    tuning_probabilities,
    gates,
):
    records = []
    eligible = []
    for step in range(101):
        threshold = round(step / 100, 2)
        development_counts = _confusion(
            development_rows, development_probabilities, threshold
        )
        tuning_counts = _confusion(tuning_rows, tuning_probabilities, threshold)
        development_gate = selection_gate_results(
            development_counts, gates
        )
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
    if not eligible:
        return None, records
    selected = min(
        eligible,
        key=lambda item: (
            -(
                item["threshold_tuning"]["recall"]["value"]
                if item["threshold_tuning"]["recall"]["value"] is not None
                else -1
            ),
            -(
                item["threshold_tuning"]["precision"]["value"]
                if item["threshold_tuning"]["precision"]["value"] is not None
                else -1
            ),
            -item["threshold"],
        ),
    )
    return selected["threshold"], records


def calibrate(
    expected_manifest_path=EXPECTED_MANIFEST_PATH,
    ctc_summary_path=CTC_SUMMARY_PATH,
    relation_path=RELATION_PATH,
    output_path=DEFAULT_OUTPUT,
):
    import numpy as np
    import sklearn

    contract = load_repair_contract()
    errors = validate_repair_contract(contract)
    if errors:
        raise ValueError("; ".join(errors))
    expected_manifest_path = Path(expected_manifest_path)
    if file_sha256(expected_manifest_path) != FROZEN_EXPECTED_MANIFEST_SHA256:
        raise ValueError("expected-only repair manifest checksum changed")
    expected_manifest = _load(expected_manifest_path)
    if expected_manifest.get("held_out_participants") != 0:
        raise ValueError("repair calibration cannot access held-out participants")
    ctc_summary = _load(ctc_summary_path)
    if (
        ctc_summary.get("execution", {}).get("clip_count") != 480
        or ctc_summary.get("execution", {}).get("held_out_participants") != 0
        or ctc_summary.get("execution", {}).get(
            "expert_outcomes_read_by_candidate_runner"
        )
        is not False
    ):
        raise ValueError("constrained feature extraction is incomplete or unsafe")
    relations = _load(relation_path)
    if relations.get("held_out_evaluation") is not False:
        raise ValueError("repair calibration received held-out relation evidence")
    feature_names = contract["feature_extractor"]["numeric_features"]
    feature_rows = _load_feature_rows(
        expected_manifest, ctc_summary, feature_names
    )
    joined = _join_truth(feature_rows, relations)
    development_adults = [
        row
        for row in joined
        if row["project_split"] == "development"
        and row["age_stratum"] == "adult"
    ]
    tuning_adults = [
        row
        for row in joined
        if row["project_split"] == "threshold_tuning"
        and row["age_stratum"] == "adult"
    ]
    if len(development_adults) != 1971 or len(tuning_adults) != 984:
        raise ValueError("adult calibration opportunity counts changed")

    policy = contract["calibration_policy"]
    selected_c, oof_probabilities, cv_records, dev_features, dev_labels = (
        _select_regularization(
            development_adults,
            feature_names,
            policy["fixed_regularization_candidates"],
            policy["fixed_random_state"],
        )
    )
    final_scaler, final_model = _fit_logistic(
        dev_features,
        dev_labels,
        selected_c,
        policy["fixed_random_state"],
    )
    tuning_features = np.asarray(
        [row["features"] for row in tuning_adults], dtype=float
    )
    tuning_probabilities = _predict(
        final_scaler, final_model, tuning_features
    )
    selected_threshold, threshold_records = _threshold_records(
        development_adults,
        oof_probabilities,
        tuning_adults,
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
                        development_adults,
                        oof_probabilities,
                        selected_threshold,
                    )
                ),
                "participants": _participant_metrics(
                    development_adults,
                    oof_probabilities,
                    selected_threshold,
                ),
            },
            "threshold_tuning": {
                **_metrics(
                    _confusion(
                        tuning_adults,
                        tuning_probabilities,
                        selected_threshold,
                    )
                ),
                "participants": _participant_metrics(
                    tuning_adults,
                    tuning_probabilities,
                    selected_threshold,
                ),
            },
        }
        child_diagnostics = {}
        for split in ("development", "threshold_tuning"):
            child_rows = [
                row
                for row in joined
                if row["project_split"] == split
                and row["age_stratum"] == "child"
            ]
            child_features = np.asarray(
                [row["features"] for row in child_rows], dtype=float
            )
            child_probabilities = _predict(
                final_scaler, final_model, child_features
            )
            child_diagnostics[split] = {
                **_metrics(
                    _confusion(
                        child_rows, child_probabilities, selected_threshold
                    )
                ),
                "adult_model_only_not_selected_for_children": True,
            }

    private_rows = []
    for partition, rows, probabilities in (
        ("development_out_of_fold", development_adults, oof_probabilities),
        ("threshold_tuning", tuning_adults, tuning_probabilities),
    ):
        for row, probability in zip(rows, probabilities):
            private_rows.append(
                {
                    "safe_id": row["safe_id"],
                    "private_participant_id": row[
                        "private_participant_id"
                    ],
                    "partition": partition,
                    "word_index": row["word_index"],
                    "local_index": row["local_index"],
                    "arpabet": row["arpabet"],
                    "truth": row["truth"],
                    "probability": round(float(probability), 9),
                }
            )

    document = {
        "schema_version": "1.0.0",
        "calibration_id": "adult_conservative_ctc_logistic_v1",
        "repair_contract_sha256": file_sha256(
            Path(__file__).with_name("benchmark-repair-contract-v1.0.0.json")
        ),
        "expected_only_manifest_sha256": FROZEN_EXPECTED_MANIFEST_SHA256,
        "ctc_process_sha256": file_sha256(ctc_summary_path),
        "relation_evidence_sha256": file_sha256(relation_path),
        "held_out_labels_or_outputs_used": False,
        "child_labels_used_for_training_or_thresholds": False,
        "feature_names": feature_names,
        "numeric_preprocessing": contract["feature_extractor"][
            "numeric_preprocessing"
        ],
        "sklearn_version": sklearn.__version__,
        "regularization_search": cv_records,
        "selected_c": selected_c,
        "final_development_model": {
            "scaler_mean": [
                round(float(item), 12) for item in final_scaler.mean_
            ],
            "scaler_scale": [
                round(float(item), 12) for item in final_scaler.scale_
            ],
            "coefficients": [
                round(float(item), 12) for item in final_model.coef_[0]
            ],
            "intercept": round(float(final_model.intercept_[0]), 12),
            "class_weight": "balanced",
            "solver": "liblinear",
            "random_state": policy["fixed_random_state"],
            "refit_after_tuning": False,
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
        raise ValueError("repair calibration evidence already exists")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(canonical_json_bytes(document))
    return output_path, document


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--expected-manifest", type=Path, default=EXPECTED_MANIFEST_PATH
    )
    parser.add_argument("--ctc-summary", type=Path, default=CTC_SUMMARY_PATH)
    parser.add_argument("--relations", type=Path, default=RELATION_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    path, document = calibrate(
        args.expected_manifest,
        args.ctc_summary,
        args.relations,
        args.output,
    )
    print(f"Repair decision: {document['decision']}")
    print(f"Selected C: {document['selected_c']}")
    print(f"Selected threshold: {document['selected_threshold']}")
    print(f"Private calibration: {path.relative_to(REPOSITORY_ROOT)}")


if __name__ == "__main__":
    main()
