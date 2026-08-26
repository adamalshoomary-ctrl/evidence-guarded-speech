"""Compare frozen contextual calibrators for the adult-only 22D repair."""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

from .benchmark import PRIVATE_BENCHMARK_ROOT
from .benchmark_repair import (
    load_repair_contract,
)
from .calibrate_benchmark_repair import (
    CTC_SUMMARY_PATH,
    EXPECTED_MANIFEST_PATH,
    RELATION_PATH,
    _confusion,
    _join_truth,
    _load,
    _metrics,
    _participant_metrics,
    _threshold_records,
)
from .feasibility import REPOSITORY_ROOT, canonical_json_bytes, file_sha256


CONTEXT_CONTRACT_PATH = Path(__file__).with_name(
    "benchmark-repair-context-contract-v1.0.0.json"
)
DEFAULT_OUTPUT = (
    PRIVATE_BENCHMARK_ROOT
    / "repair-v1"
    / "evidence"
    / "calibration"
    / "adult-context-calibration-v1.0.0.json"
)


def _load_context_contract(path=CONTEXT_CONTRACT_PATH):
    document = _load(path)
    if document.get("status") != "rules_frozen_before_contextual_calibration":
        raise ValueError("contextual repair rules are not frozen")
    if document["input_policy"]["held_out_access_allowed"] is not False:
        raise ValueError("contextual repair cannot access held-out evidence")
    if document["feature_policy"]["participant_identity_feature_allowed"] is not False:
        raise ValueError("participant identity cannot be a calibration feature")
    if document["feature_policy"]["reviewer_outcome_feature_allowed"] is not False:
        raise ValueError("reviewer outcomes cannot be calibration features")
    return document


def _word_context(expected_manifest):
    result = {}
    for clip in expected_manifest["clips"]:
        grouped = {}
        for target in clip["targets"]:
            grouped.setdefault(target["word_index"], []).append(target)
        for word_index, targets in grouped.items():
            targets = sorted(targets, key=lambda item: item["local_index"])
            for position, target in enumerate(targets):
                if len(targets) == 1:
                    word_position = "single"
                elif position == 0:
                    word_position = "initial"
                elif position == len(targets) - 1:
                    word_position = "final"
                else:
                    word_position = "medial"
                result[
                    (
                        clip["safe_id"],
                        word_index,
                        target["local_index"],
                    )
                ] = {
                    "word_position": word_position,
                    "previous_expected_arpabet": (
                        "<boundary>"
                        if position == 0
                        else targets[position - 1]["arpabet"]
                    ),
                    "next_expected_arpabet": (
                        "<boundary>"
                        if position == len(targets) - 1
                        else targets[position + 1]["arpabet"]
                    ),
                }
    return result


def _numeric_values(target, feature_names):
    result = []
    for name in feature_names:
        value = target.get(name)
        if value is None:
            if name != "greedy_observed_panphon_feature_difference_rate":
                raise ValueError(f"unexpected missing contextual feature: {name}")
            value = 1.0
        result.append(float(value))
    return result


def _load_context_rows(
    expected_manifest,
    ctc_summary,
    numeric_feature_names,
    categorical_feature_names,
):
    expected = {clip["safe_id"]: clip for clip in expected_manifest["clips"]}
    contexts = _word_context(expected_manifest)
    rows = {}
    for item in ctc_summary["clips"]:
        path = REPOSITORY_ROOT / item["output_path"]
        if file_sha256(path) != item["output_sha256"]:
            raise ValueError(f"context feature record changed: {item['safe_id']}")
        record = _load(path)
        if record.get("same_input_target_features_exact") is not True:
            raise ValueError("context feature record did not repeat exactly")
        clip = expected[item["safe_id"]]
        for target in record["target_features"]:
            key = (
                item["safe_id"],
                target["word_index"],
                target["local_index"],
            )
            context = contexts[key]
            categories = {
                "expected_arpabet": target["arpabet"],
                "word_position": context["word_position"],
                "previous_expected_arpabet": context[
                    "previous_expected_arpabet"
                ],
                "next_expected_arpabet": context["next_expected_arpabet"],
                "greedy_alignment_relation_type": (
                    target.get("greedy_alignment_relation_type") or "unavailable"
                ),
                "best_competing_consonant": target[
                    "best_competing_consonant"
                ],
                "expected_competing_pair": (
                    f"{target['arpabet']}|{target['best_competing_consonant']}"
                ),
            }
            if set(categories) != set(categorical_feature_names):
                raise ValueError("contextual categorical feature set changed")
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
                "features": _numeric_values(target, numeric_feature_names),
                "categories": [
                    categories[name] for name in categorical_feature_names
                ],
            }
    return rows


def _candidate_configurations(contract):
    configurations = []
    for candidate in contract["model_comparison"]["candidate_families"]:
        family = candidate["family"]
        order = candidate["family_order"]
        parameters = candidate["hyperparameters"]
        if family == "l2_logistic_regression":
            for c in parameters["c"]:
                configurations.append(
                    {
                        "family": family,
                        "family_order": order,
                        "parameters": {
                            "c": c,
                            "solver": parameters["solver"],
                            "max_iter": parameters["max_iter"],
                        },
                    }
                )
        elif family == "histogram_gradient_boosting":
            for leaves, regularization in itertools.product(
                parameters["max_leaf_nodes"],
                parameters["l2_regularization"],
            ):
                configurations.append(
                    {
                        "family": family,
                        "family_order": order,
                        "parameters": {
                            "learning_rate": parameters["learning_rate"],
                            "max_iter": parameters["max_iter"],
                            "max_leaf_nodes": leaves,
                            "l2_regularization": regularization,
                            "min_samples_leaf": parameters["min_samples_leaf"],
                        },
                    }
                )
        elif family == "random_forest":
            for depth, minimum in itertools.product(
                parameters["max_depth"],
                parameters["min_samples_leaf"],
            ):
                configurations.append(
                    {
                        "family": family,
                        "family_order": order,
                        "parameters": {
                            "n_estimators": parameters["n_estimators"],
                            "max_depth": depth,
                            "min_samples_leaf": minimum,
                            "max_features": parameters["max_features"],
                            "n_jobs": parameters["n_jobs"],
                        },
                    }
                )
        else:
            raise ValueError(f"unknown contextual candidate family: {family}")
    return configurations


def _matrix(rows):
    import numpy as np

    return np.asarray(
        [row["features"] + row["categories"] for row in rows],
        dtype=object,
    )


def _preprocessor(numeric_count, categorical_count, minimum_frequency):
    from sklearn.compose import ColumnTransformer
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    numeric_indexes = list(range(numeric_count))
    categorical_indexes = list(
        range(numeric_count, numeric_count + categorical_count)
    )
    return ColumnTransformer(
        [
            ("numeric", StandardScaler(), numeric_indexes),
            (
                "categorical",
                OneHotEncoder(
                    handle_unknown="ignore",
                    min_frequency=minimum_frequency,
                    sparse_output=False,
                ),
                categorical_indexes,
            ),
        ],
        sparse_threshold=0.0,
    )


def _classifier(configuration, random_state):
    parameters = configuration["parameters"]
    if configuration["family"] == "l2_logistic_regression":
        from sklearn.linear_model import LogisticRegression

        return LogisticRegression(
            C=parameters["c"],
            class_weight="balanced",
            solver=parameters["solver"],
            random_state=random_state,
            max_iter=parameters["max_iter"],
        )
    if configuration["family"] == "histogram_gradient_boosting":
        from sklearn.ensemble import HistGradientBoostingClassifier

        return HistGradientBoostingClassifier(
            learning_rate=parameters["learning_rate"],
            max_iter=parameters["max_iter"],
            max_leaf_nodes=parameters["max_leaf_nodes"],
            l2_regularization=parameters["l2_regularization"],
            min_samples_leaf=parameters["min_samples_leaf"],
            class_weight="balanced",
            random_state=random_state,
        )
    if configuration["family"] == "random_forest":
        from sklearn.ensemble import RandomForestClassifier

        return RandomForestClassifier(
            n_estimators=parameters["n_estimators"],
            max_depth=parameters["max_depth"],
            min_samples_leaf=parameters["min_samples_leaf"],
            max_features=parameters["max_features"],
            n_jobs=parameters["n_jobs"],
            class_weight="balanced",
            random_state=random_state,
        )
    raise ValueError("contextual classifier family is unsupported")


def _fit(
    features,
    labels,
    configuration,
    random_state,
    numeric_count,
    categorical_count,
    minimum_frequency,
):
    preprocessor = _preprocessor(
        numeric_count, categorical_count, minimum_frequency
    )
    transformed = preprocessor.fit_transform(features)
    classifier = _classifier(configuration, random_state)
    classifier.fit(transformed, labels)
    return preprocessor, classifier


def _predict(preprocessor, classifier, features):
    return classifier.predict_proba(preprocessor.transform(features))[:, 1]


def _compare_models(
    rows,
    configurations,
    random_state,
    numeric_count,
    categorical_count,
    minimum_frequency,
):
    import numpy as np
    from sklearn.metrics import average_precision_score
    from sklearn.model_selection import GroupKFold

    features = _matrix(rows)
    labels = np.asarray([row["label"] for row in rows], dtype=int)
    groups = np.asarray(
        [row["private_participant_id"] for row in rows], dtype=object
    )
    folds = list(GroupKFold(n_splits=4).split(features, labels, groups))
    comparisons = []
    probabilities_by_key = {}
    for configuration in configurations:
        probabilities = np.zeros(len(rows), dtype=float)
        fold_records = []
        for fold_index, (training, validation) in enumerate(folds):
            training_participants = sorted(set(groups[training]))
            validation_participants = sorted(set(groups[validation]))
            if set(training_participants) & set(validation_participants):
                raise ValueError("participant leaked across contextual fold")
            preprocessor, classifier = _fit(
                features[training],
                labels[training],
                configuration,
                random_state,
                numeric_count,
                categorical_count,
                minimum_frequency,
            )
            probabilities[validation] = _predict(
                preprocessor, classifier, features[validation]
            )
            fold_records.append(
                {
                    "fold_index": fold_index,
                    "training_participants": training_participants,
                    "validation_participants": validation_participants,
                    "validation_rows": len(validation),
                    "validation_positive_rows": int(labels[validation].sum()),
                }
            )
        average_precision = float(average_precision_score(labels, probabilities))
        key = json.dumps(configuration, sort_keys=True, separators=(",", ":"))
        probabilities_by_key[key] = probabilities
        comparisons.append(
            {
                **configuration,
                "configuration_key": key,
                "development_out_of_fold_average_precision": round(
                    average_precision, 9
                ),
                "folds": fold_records,
            }
        )
    selected = min(
        comparisons,
        key=lambda item: (
            -item["development_out_of_fold_average_precision"],
            item["family_order"],
            json.dumps(item["parameters"], sort_keys=True),
        ),
    )
    return (
        selected,
        probabilities_by_key[selected["configuration_key"]],
        comparisons,
        features,
        labels,
    )


def calibrate_context(
    context_contract_path=CONTEXT_CONTRACT_PATH,
    expected_manifest_path=EXPECTED_MANIFEST_PATH,
    ctc_summary_path=CTC_SUMMARY_PATH,
    relation_path=RELATION_PATH,
    output_path=DEFAULT_OUTPUT,
):
    import numpy as np
    import sklearn

    context_contract = _load_context_contract(context_contract_path)
    prior_contract = load_repair_contract()
    if file_sha256(Path(__file__).with_name("benchmark-repair-contract-v1.0.0.json")) != (
        context_contract["prior_repair"]["contract_sha256"]
    ):
        raise ValueError("prior numeric repair contract checksum changed")
    if file_sha256(expected_manifest_path) != (
        context_contract["input_policy"]["expected_only_manifest_sha256"]
    ):
        raise ValueError("contextual expected-only input checksum changed")
    if file_sha256(ctc_summary_path) != (
        context_contract["input_policy"]["ctc_process_sha256"]
    ):
        raise ValueError("contextual CTC process checksum changed")
    expected_manifest = _load(expected_manifest_path)
    ctc_summary = _load(ctc_summary_path)
    relations = _load(relation_path)
    if (
        expected_manifest.get("held_out_participants") != 0
        or ctc_summary["execution"].get("held_out_participants") != 0
        or relations.get("held_out_evaluation") is not False
    ):
        raise ValueError("contextual calibration cannot access held-out evidence")

    numeric_names = prior_contract["feature_extractor"]["numeric_features"]
    categorical_names = context_contract["feature_policy"][
        "categorical_features"
    ]
    feature_rows = _load_context_rows(
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
        raise ValueError("contextual adult opportunity counts changed")

    minimum_frequency = context_contract["feature_policy"][
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
        context_contract["model_comparison"]["fixed_random_state"],
        len(numeric_names),
        len(categorical_names),
        minimum_frequency,
    )
    final_preprocessor, final_classifier = _fit(
        development_features,
        development_labels,
        selected,
        context_contract["model_comparison"]["fixed_random_state"],
        len(numeric_names),
        len(categorical_names),
        minimum_frequency,
    )
    tuning_features = _matrix(tuning)
    tuning_probabilities = _predict(
        final_preprocessor, final_classifier, tuning_features
    )
    selected_threshold, threshold_records = _threshold_records(
        development,
        development_probabilities,
        tuning,
        tuning_probabilities,
        context_contract["selection_gates"],
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
                        tuning, tuning_probabilities, selected_threshold
                    )
                ),
                "participants": _participant_metrics(
                    tuning, tuning_probabilities, selected_threshold
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
                        children, child_probabilities, selected_threshold
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

    output = {
        "schema_version": "1.0.0",
        "calibration_id": "adult_contextual_candidate_comparison_v1",
        "context_contract_sha256": file_sha256(context_contract_path),
        "prior_repair_contract_sha256": context_contract["prior_repair"][
            "contract_sha256"
        ],
        "expected_only_manifest_sha256": context_contract["input_policy"][
            "expected_only_manifest_sha256"
        ],
        "ctc_process_sha256": context_contract["input_policy"][
            "ctc_process_sha256"
        ],
        "relation_evidence_sha256": file_sha256(relation_path),
        "held_out_labels_or_outputs_used": False,
        "child_labels_used_for_training_or_thresholds": False,
        "participant_identity_used_as_feature": False,
        "numeric_feature_names": numeric_names,
        "categorical_feature_names": categorical_names,
        "sklearn_version": sklearn.__version__,
        "model_comparison": comparisons,
        "selected_configuration": {
            key: value
            for key, value in selected.items()
            if key not in {"folds"}
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
        raise ValueError("contextual calibration evidence already exists")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(canonical_json_bytes(output))
    return output_path, output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--context-contract", type=Path, default=CONTEXT_CONTRACT_PATH
    )
    parser.add_argument(
        "--expected-manifest", type=Path, default=EXPECTED_MANIFEST_PATH
    )
    parser.add_argument("--ctc-summary", type=Path, default=CTC_SUMMARY_PATH)
    parser.add_argument("--relations", type=Path, default=RELATION_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    path, document = calibrate_context(
        args.context_contract,
        args.expected_manifest,
        args.ctc_summary,
        args.relations,
        args.output,
    )
    selected = document["selected_configuration"]
    print(f"Contextual family: {selected['family']}")
    print(
        "Development grouped average precision: "
        f"{selected['development_out_of_fold_average_precision']}"
    )
    print(f"Selected threshold: {document['selected_threshold']}")
    print(f"Decision: {document['decision']}")
    print(f"Private calibration: {path.relative_to(REPOSITORY_ROOT)}")


if __name__ == "__main__":
    main()
