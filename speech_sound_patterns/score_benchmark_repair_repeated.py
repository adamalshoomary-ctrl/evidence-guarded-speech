"""Score the frozen same-sound repeated-evidence repair filter."""

from __future__ import annotations

import argparse
import itertools
import json
from collections import defaultdict
from pathlib import Path

from .benchmark import PRIVATE_BENCHMARK_ROOT
from .benchmark_repair import selection_gate_results
from .calibrate_benchmark_repair import (
    _confusion,
    _load,
    _metrics,
    _participant_metrics,
)
from .feasibility import REPOSITORY_ROOT, canonical_json_bytes, file_sha256


REPEATED_CONTRACT_PATH = Path(__file__).with_name(
    "benchmark-repair-repeated-contract-v1.0.0.json"
)
CONTEXT_CALIBRATION_PATH = (
    PRIVATE_BENCHMARK_ROOT
    / "repair-v1"
    / "evidence"
    / "calibration"
    / "adult-context-calibration-v1.0.0.json"
)
DEFAULT_OUTPUT = (
    PRIVATE_BENCHMARK_ROOT
    / "repair-v1"
    / "evidence"
    / "calibration"
    / "adult-repeated-filter-v1.0.0.json"
)


def _contract(path):
    document = _load(path)
    if document.get("status") != (
        "rules_frozen_before_repeated_evidence_scoring"
    ):
        raise ValueError("repeated-evidence repair rules are not frozen")
    if document["input_policy"]["held_out_access_allowed"] is not False:
        raise ValueError("repeated-evidence repair cannot access held-out data")
    if document["grouping_policy"]["named_pattern_created"] is not False:
        raise ValueError("benchmark repair cannot create a named pattern")
    return document


def _filtered_probabilities(
    rows,
    opportunity_threshold,
    minimum_candidates,
    minimum_words,
    minimum_clips,
):
    candidates = [
        row["probability"] >= opportunity_threshold for row in rows
    ]
    grouped = defaultdict(list)
    for index, (row, candidate) in enumerate(zip(rows, candidates)):
        if candidate:
            grouped[
                (row["private_participant_id"], row["arpabet"])
            ].append(index)
    eligible = set()
    group_records = []
    for key, indexes in grouped.items():
        word_occurrences = {
            (rows[index]["safe_id"], rows[index]["word_index"])
            for index in indexes
        }
        clips = {rows[index]["safe_id"] for index in indexes}
        passed = (
            len(indexes) >= minimum_candidates
            and len(word_occurrences) >= minimum_words
            and len(clips) >= minimum_clips
        )
        if passed:
            eligible.add(key)
        group_records.append(
            {
                "private_participant_id": key[0],
                "expected_arpabet": key[1],
                "candidate_opportunities": len(indexes),
                "distinct_word_occurrences": len(word_occurrences),
                "distinct_clips": len(clips),
                "eligible": passed,
            }
        )
    predictions = [
        1.0
        if candidate
        and (row["private_participant_id"], row["arpabet"]) in eligible
        else 0.0
        for row, candidate in zip(rows, candidates)
    ]
    return predictions, group_records


def _score_configuration(rows, configuration, gates):
    probabilities, groups = _filtered_probabilities(
        rows,
        configuration["opportunity_probability_threshold"],
        configuration["minimum_candidates_for_same_expected_sound"],
        configuration["minimum_distinct_words"],
        configuration["minimum_distinct_clips"],
    )
    counts = _confusion(rows, probabilities, 0.5)
    return {
        **_metrics(counts),
        "selection_gates": selection_gate_results(counts, gates),
        "participants": _participant_metrics(rows, probabilities, 0.5),
        "eligible_groups": groups,
    }


def _configurations(contract):
    grid = contract["fixed_search_grid"]
    threshold = grid["opportunity_probability_threshold"]
    first = round(threshold["minimum"] * 100)
    last = round(threshold["maximum"] * 100)
    step = round(threshold["step"] * 100)
    for value, candidates, words, clips in itertools.product(
        range(first, last + 1, step),
        grid["minimum_candidates_for_same_expected_sound"],
        grid["minimum_distinct_words"],
        grid["minimum_distinct_clips"],
    ):
        yield {
            "opportunity_probability_threshold": round(value / 100, 2),
            "minimum_candidates_for_same_expected_sound": candidates,
            "minimum_distinct_words": words,
            "minimum_distinct_clips": clips,
        }


def score_repeated_filter(
    contract_path=REPEATED_CONTRACT_PATH,
    context_calibration_path=CONTEXT_CALIBRATION_PATH,
    output_path=DEFAULT_OUTPUT,
):
    contract = _contract(contract_path)
    if file_sha256(context_calibration_path) != (
        contract["input_policy"]["context_calibration_sha256"]
    ):
        raise ValueError("context calibration checksum changed")
    context = _load(context_calibration_path)
    if (
        context.get("held_out_labels_or_outputs_used") is not False
        or context.get("child_labels_used_for_training_or_thresholds") is not False
    ):
        raise ValueError("context calibration violates repeated filter scope")
    development = [
        {**row, "label": int(row["truth"] == "positive")}
        for row in context["private_adult_rows"]
        if row["partition"] == "development_out_of_fold"
    ]
    tuning = [
        {**row, "label": int(row["truth"] == "positive")}
        for row in context["private_adult_rows"]
        if row["partition"] == "threshold_tuning"
    ]
    if len(development) != 1971 or len(tuning) != 984:
        raise ValueError("repeated filter opportunity counts changed")
    gates = contract["selection_gates"]
    records = []
    eligible = []
    for configuration in _configurations(contract):
        development_result = _score_configuration(
            development, configuration, gates
        )
        tuning_result = _score_configuration(tuning, configuration, gates)
        record = {
            "configuration": configuration,
            "development_out_of_fold": development_result,
            "threshold_tuning": tuning_result,
            "both_partitions_pass": (
                development_result["selection_gates"]["passed"]
                and tuning_result["selection_gates"]["passed"]
            ),
        }
        records.append(record)
        if record["both_partitions_pass"]:
            eligible.append(record)
    if eligible:
        selected = min(
            eligible,
            key=lambda item: (
                -item["threshold_tuning"]["recall"]["value"],
                -item["threshold_tuning"]["precision"]["value"],
                -item["configuration"][
                    "opportunity_probability_threshold"
                ],
                -item["configuration"][
                    "minimum_candidates_for_same_expected_sound"
                ],
                -item["configuration"]["minimum_distinct_words"],
                -item["configuration"]["minimum_distinct_clips"],
            ),
        )
        decision = "adult_repeated_expected_sound_candidate_filter"
    else:
        selected = None
        decision = "no_system_filter_or_threshold_selected"
    output = {
        "schema_version": "1.0.0",
        "filter_id": "adult_repeated_expected_sound_filter_v1",
        "contract_sha256": file_sha256(contract_path),
        "context_calibration_sha256": file_sha256(
            context_calibration_path
        ),
        "held_out_labels_or_outputs_used": False,
        "children_used_for_selection": False,
        "configurations_evaluated": len(records),
        "grid_results": records,
        "selected_result": selected,
        "decision": decision,
        "claim_boundaries": {
            "named_pattern": False,
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
        raise ValueError("repeated filter evidence already exists")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(canonical_json_bytes(output))
    return output_path, output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--contract", type=Path, default=REPEATED_CONTRACT_PATH
    )
    parser.add_argument(
        "--context-calibration",
        type=Path,
        default=CONTEXT_CALIBRATION_PATH,
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    path, document = score_repeated_filter(
        args.contract, args.context_calibration, args.output
    )
    print(f"Repeated filter decision: {document['decision']}")
    if document["selected_result"] is not None:
        print(
            "Selected configuration: "
            + json.dumps(
                document["selected_result"]["configuration"],
                sort_keys=True,
            )
        )
    print(f"Private repeated evidence: {path.relative_to(REPOSITORY_ROOT)}")


if __name__ == "__main__":
    main()
