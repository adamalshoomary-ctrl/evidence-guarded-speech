"""Create the committed aggregate-only checkpoint 22D benchmark report."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from .benchmark import (
    BENCHMARK_CONTRACT_PATH,
    FROZEN_BENCHMARK_MANIFEST_SHA256,
    PHONE_MAP_PATH,
    PRIVATE_BENCHMARK_ROOT,
    align_phone_sequences,
    canonical_json_sha256,
    expand_reference_phones,
    load_benchmark_contract,
    load_phone_map,
    ratio_record,
    strip_stress,
    validate_frozen_private_benchmark_manifest,
    validate_safe_benchmark_report,
)
from .feasibility import REPOSITORY_ROOT, canonical_json_bytes, file_sha256
from .mfa_probe import NONPHONE_LABELS


PRIVATE_ROOT = REPOSITORY_ROOT / ".research_data" / "speech_sound_patterns"
MANIFEST_PATH = PRIVATE_ROOT / "benchmark" / "benchmark-manifest-v1.0.0.json"
XEUS_PATH = (
    PRIVATE_BENCHMARK_ROOT
    / "v1"
    / "evidence"
    / "phoneticxeus"
    / "phoneticxeus-benchmark-process.json"
)
MFA_PATH = PRIVATE_BENCHMARK_ROOT / "v1" / "evidence" / "mfa" / "mfa-benchmark-process.json"
RELATION_PATH = (
    PRIVATE_BENCHMARK_ROOT
    / "v1"
    / "evidence"
    / "scoring"
    / "speechocean-aggregate.json"
)
REPORT_PATH = Path(__file__).with_name("local-benchmark-v1.0.0.json")


ACTED_CONSONANT_TO_ARPA = {
    "D": "DH",
    "N": "NG",
    "S": "SH",
    "Z": "ZH",
    "b": "B",
    "d": "D",
    "f": "F",
    "g": "G",
    "h": "HH",
    "j": "Y",
    "k": "K",
    "l": "L",
    "m": "M",
    "n": "N",
    "p": "P",
    "r": "R",
    "s": "S",
    "t": "T",
    "tS": "CH",
    "v": "V",
    "w": "W",
    "z": "Z",
}


def _load(path):
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"benchmark evidence is missing: {path.name}")
    return json.loads(path.read_text(encoding="utf-8"))


def _source(manifest, source_id):
    matches = [item for item in manifest["sources"] if item["source_id"] == source_id]
    if len(matches) != 1:
        raise ValueError(f"benchmark source {source_id} is unavailable")
    return matches[0]


def _references(manifest, source_id):
    source = _source(manifest, source_id)
    path = REPOSITORY_ROOT / source["private_reference_path"]
    if file_sha256(path) != source["private_reference_sha256"]:
        raise ValueError(f"private {source_id} reference evidence changed")
    document = _load(path)
    records = {item["safe_id"]: item for item in document["records"]}
    return source, records


def _percentile(values, proportion):
    if not values:
        return None
    ordered = sorted(values)
    rank = (len(ordered) - 1) * proportion
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[lower]
    weight = rank - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _timing_value(values):
    return {
        "count": len(values),
        "median_s": None if not values else round(statistics.median(values), 6),
        "p95_s": None if not values else round(_percentile(values, 0.95), 6),
        "maximum_s": None if not values else round(max(values), 6),
    }


def _align_labels(reference, candidate):
    rows, columns = len(reference), len(candidate)
    costs = [[0] * (columns + 1) for _ in range(rows + 1)]
    choices = [[None] * (columns + 1) for _ in range(rows + 1)]
    for row in range(1, rows + 1):
        costs[row][0] = row
        choices[row][0] = "deletion"
    for column in range(1, columns + 1):
        costs[0][column] = column
        choices[0][column] = "insertion"
    priority = {"match": 0, "substitution": 1, "deletion": 2, "insertion": 3}
    for row in range(1, rows + 1):
        for column in range(1, columns + 1):
            match = reference[row - 1][2] == candidate[column - 1][2]
            diagonal = "match" if match else "substitution"
            options = [
                (costs[row - 1][column - 1] + (0 if match else 1), diagonal),
                (costs[row - 1][column] + 1, "deletion"),
                (costs[row][column - 1] + 1, "insertion"),
            ]
            costs[row][column], choices[row][column] = min(
                options, key=lambda item: (item[0], priority[item[1]])
            )
    matches = []
    row, column = rows, columns
    while row or column:
        choice = choices[row][column]
        if choice in {"match", "substitution"}:
            if choice == "match":
                matches.append((row - 1, column - 1))
            row -= 1
            column -= 1
        elif choice == "deletion":
            row -= 1
        elif choice == "insertion":
            column -= 1
        else:
            raise ValueError("timing label alignment is incomplete")
    matches.reverse()
    return matches


def _mfa_raw(safe_id):
    return _load(
        PRIVATE_BENCHMARK_ROOT
        / "v1"
        / "evidence"
        / "mfa"
        / "clips"
        / safe_id
        / "repeat-1"
        / "alignment.json"
    )


def _timing_fixture(manifest, mfa_summary):
    source, references = _references(manifest, "acted_clear_speech")
    mfa_ids = {
        item["safe_id"]
        for item in mfa_summary["clips"]
        if item["source_id"] == "acted_clear_speech"
    }
    if set(references) != mfa_ids:
        raise ValueError("Acted Clear timing and MFA record sets differ")
    condition_values = defaultdict(lambda: {"reference": 0, "matches": 0, "start": [], "end": []})
    uncertain_or_compound = 0
    for safe_id, record in references.items():
        reference = []
        for start, end, label in record["hand_corrected_phone_intervals"]:
            mapped = ACTED_CONSONANT_TO_ARPA.get(label)
            if mapped is None:
                if label not in {"sil", ""}:
                    uncertain_or_compound += 1
                continue
            reference.append((start, end, mapped))
        raw = _mfa_raw(safe_id)
        candidate = []
        for start, end, label in raw["tiers"]["phones"]["entries"]:
            if label in NONPHONE_LABELS:
                continue
            base = strip_stress(label)
            if base in {item for item in ACTED_CONSONANT_TO_ARPA.values()}:
                candidate.append((float(start), float(end), base))
        matches = _align_labels(reference, candidate)
        values = condition_values[record["condition"]]
        values["reference"] += len(reference)
        values["matches"] += len(matches)
        for reference_index, candidate_index in matches:
            ref_item = reference[reference_index]
            candidate_item = candidate[candidate_index]
            values["start"].append(abs(ref_item[0] - candidate_item[0]))
            values["end"].append(abs(ref_item[1] - candidate_item[1]))
    conditions = []
    total = {"reference": 0, "matches": 0, "start": [], "end": []}
    for condition, values in sorted(condition_values.items()):
        conditions.append(
            {
                "condition": condition,
                "clips": 5,
                "clean_consonant_reference_intervals": values["reference"],
                "exact_phone_label_matches": values["matches"],
                "match_coverage": ratio_record(values["matches"], values["reference"]),
                "start_boundary_absolute_error": _timing_value(values["start"]),
                "end_boundary_absolute_error": _timing_value(values["end"]),
            }
        )
        for field in total:
            if isinstance(total[field], list):
                total[field].extend(values[field])
            else:
                total[field] += values[field]
    return {
        "source_id": "acted_clear_speech",
        "truth_class": "human_corrected_phone_boundaries",
        "clips": len(references),
        "speakers": 1,
        "conditions": conditions,
        "clean_consonant_reference_intervals": total["reference"],
        "exact_phone_label_matches": total["matches"],
        "match_coverage": ratio_record(total["matches"], total["reference"]),
        "start_boundary_absolute_error": _timing_value(total["start"]),
        "end_boundary_absolute_error": _timing_value(total["end"]),
        "uncertain_compound_vowel_or_nonconsonant_intervals_not_scored": uncertain_or_compound,
        "population_accuracy_supported": False,
        "phone_relation_accuracy_supported": False,
    }


def _model_outputs(summary, source_id):
    return {
        item["safe_id"]: _load(REPOSITORY_ROOT / item["output_path"])
        for item in summary["clips"]
        if item["source_id"] == source_id
    }


def _candidate_disagreement(manifest, xeus_summary, mfa_summary, source_id):
    source = _source(manifest, source_id)
    clips = {item["safe_id"]: item for item in source["clips"]}
    xeus = _model_outputs(xeus_summary, source_id)
    mfa_ids = {
        item["safe_id"]
        for item in mfa_summary["clips"]
        if item["source_id"] == source_id
    }
    if set(clips) != set(xeus) or set(clips) != mfa_ids:
        raise ValueError(f"candidate system sets differ for {source_id}")
    phone_map = load_phone_map()
    partitions = defaultdict(lambda: Counter())
    unknown_intervals = Counter()
    for safe_id, clip in clips.items():
        raw = _mfa_raw(safe_id)
        reference_phones = []
        for _, _, label in raw["tiers"]["phones"]["entries"]:
            if label in NONPHONE_LABELS:
                if label in {"spn", ""}:
                    unknown_intervals[clip["project_split"]] += 1
                continue
            base = strip_stress(label)
            if base in phone_map["reference_phones"]:
                reference_phones.append(base)
            else:
                unknown_intervals[clip["project_split"]] += 1
        expected = expand_reference_phones(reference_phones, phone_map)
        aligned = align_phone_sequences(
            expected, xeus[safe_id]["collapsed_tokens"], phone_map
        )
        values = partitions[clip["project_split"]]
        values["clips"] += 1
        values["mfa_expected_phone_tokens"] += len(expected)
        values["phoneticxeus_phone_tokens"] += len(xeus[safe_id]["collapsed_tokens"])
        values["unit_edit_operations"] += aligned["edit_cost"]
    result = []
    for split, values in sorted(partitions.items()):
        denominator = values["mfa_expected_phone_tokens"]
        result.append(
            {
                "project_split": split,
                "clips": values["clips"],
                "mfa_expected_phone_tokens": denominator,
                "phoneticxeus_phone_tokens": values["phoneticxeus_phone_tokens"],
                "unit_edit_operations": values["unit_edit_operations"],
                "unit_edit_operations_per_mfa_expected_phone": {
                    "numerator": values["unit_edit_operations"],
                    "denominator": denominator,
                    "value": (
                        None
                        if not denominator
                        else round(values["unit_edit_operations"] / denominator, 6)
                    ),
                },
                "mfa_unknown_or_unlabeled_intervals": unknown_intervals[split],
                "interpretation": "candidate_system_disagreement_not_phone_error_rate",
            }
        )
    return result


def _source_reference_count(manifest, source_id, field):
    _, references = _references(manifest, source_id)
    return sum(len(item[field]) for item in references.values())


def build_report():
    manifest = _load(MANIFEST_PATH)
    errors = validate_frozen_private_benchmark_manifest(
        manifest, FROZEN_BENCHMARK_MANIFEST_SHA256
    )
    if errors:
        raise ValueError("; ".join(errors))
    xeus = _load(XEUS_PATH)
    mfa = _load(MFA_PATH)
    relations = _load(RELATION_PATH)
    if len(xeus["clips"]) != 565 or len(mfa["clips"]) != 109:
        raise ValueError("local benchmark process evidence is incomplete")
    if not all(item["repeatability_passed"] for item in xeus["clips"]):
        raise ValueError("PhoneticXEUS repeatability failed")
    if not all(item["repeatability_passed"] for item in mfa["clips"]):
        raise ValueError("MFA repeatability failed")
    source_counts = {
        source["source_id"]: len(source["clips"]) for source in manifest["sources"]
    }
    held_out = sum(
        clip["project_split"] == "held_out_evaluation"
        for source in manifest["sources"]
        for clip in source["clips"]
    )
    common_phone_disagreement = _candidate_disagreement(
        manifest, xeus, mfa, "common_phone_1_0"
    )
    common_voice_disagreement = _candidate_disagreement(
        manifest, xeus, mfa, "common_voice_26_australian_english"
    )
    _, common_voice_references = _references(
        manifest, "common_voice_26_australian_english"
    )
    validation_votes = Counter()
    for item in common_voice_references.values():
        validation_votes["up"] += item["validation_votes"]["up"]
        validation_votes["down"] += item["validation_votes"]["down"]
    report = {
        "schema_version": "1.0.0",
        "report_id": "speech_sound_local_benchmark_v1",
        "status": "benchmark_harness_complete_development_and_tuning_only_release_locked",
        "benchmark_contract": {
            "path": BENCHMARK_CONTRACT_PATH.name,
            "sha256": canonical_json_sha256(load_benchmark_contract()),
            "rules_frozen_before_scoring": True,
        },
        "phone_map": {
            "path": PHONE_MAP_PATH.name,
            "sha256": canonical_json_sha256(load_phone_map()),
            "weighted_panphon_distance_used": False,
        },
        "private_evidence": {
            "benchmark_manifest_sha256": FROZEN_BENCHMARK_MANIFEST_SHA256,
            "phoneticxeus_process_sha256": file_sha256(XEUS_PATH),
            "mfa_process_sha256": file_sha256(MFA_PATH),
            "relation_evidence_sha256": relations["private_evidence_sha256"],
            "raw_or_row_level_evidence_committed": False,
            "held_out_evaluation_accessed_or_scored": False,
        },
        "sample": {
            "total_clips": sum(source_counts.values()),
            "source_clip_counts": source_counts,
            "project_splits": ["development", "threshold_tuning", "fixture"],
            "held_out_participants": held_out,
            "selection_used_labels_or_model_outputs": False,
        },
        "expert_phone_relations": {
            "source_id": relations["source_id"],
            "truth_class": relations["truth_class"],
            "population_boundary": relations["population_boundary"],
            "reference_rule": relations["reference_rule"],
            "partitions": relations["partitions"],
            "headline_score": None,
        },
        "human_corrected_timing_fixture": _timing_fixture(manifest, mfa),
        "automatic_alignment_engineering": {
            "source_id": "common_phone_1_0",
            "truth_class": "automatic_forced_alignments",
            "source_automatic_phone_intervals": _source_reference_count(
                manifest, "common_phone_1_0", "automatic_phone_intervals"
            ),
            "partitions": common_phone_disagreement,
            "phone_relation_accuracy_supported": False,
            "independent_of_common_voice": False,
        },
        "australian_sentence_robustness": {
            "source_id": "common_voice_26_australian_english",
            "truth_class": "validated_sentence_audio",
            "validation_votes": dict(validation_votes),
            "partitions": common_voice_disagreement,
            "phone_truth_available": False,
            "australian_lexical_variant_truth_available": False,
            "false_concern_accuracy_supported": False,
        },
        "local_system_repeatability": {
            "phoneticxeus": {
                "clips_repeated": 565,
                "exact_frame_and_collapsed_path_matches": 565,
                "rate": ratio_record(565, 565),
            },
            "mfa": {
                "clips_repeated": 5,
                "exact_canonical_alignment_matches": 5,
                "rate": ratio_record(5, 5),
            },
        },
        "system_decision": {
            "selected_system": None,
            "threshold_selected": False,
            "development_finding": (
                "The frozen greedy PhoneticXEUS relation path produced high recall "
                "but unacceptable false-concern counts and very low exact supporting "
                "relation matches. It is not eligible for selection in its current form."
            ),
            "paid_provider_evaluated": False,
            "scientific_or_product_release_supported": False,
        },
        "limitations": [
            "SpeechOcean762 is Mandarin-first-language read speech with a single expected pronunciation and cannot define acceptable English or Australian truth.",
            "SpeechOcean parentheses combine incorrect and missed phones, so the primary target metric is deliberately coarse and disputed records are unscorable.",
            "The aggregate exact substitutions are supporting source records, not independent five-reviewer truth and not a precision denominator.",
            "Child positive-relation denominators are very small in this frozen sample, so their recall estimates are highly uncertain.",
            "MFA is conditioned on expected text and a General American model; it supplies timing and candidate disagreement, not produced-phone truth.",
            "Acted Clear contains one British speaker and cannot estimate population performance.",
            "Common Phone annotations are automatic and share Common Voice lineage.",
            "Australian Common Voice supplies sentence robustness only, not phone truth or lexical Australian variants.",
            "PhoneticXEUS has no calibrated confidence or official phone timestamps, and its complete commercial provenance remains unresolved.",
            "No final held-out participant was accessed or scored, and no threshold or system was selected.",
        ],
        "release_boundaries": {
            "candidate_artifact": False,
            "normal_pipeline": False,
            "coaching": False,
            "personal_progress": False,
            "screening": False,
            "diagnosis": False,
            "severity": False,
            "cause": False,
            "treatment": False,
            "scientific_release": False,
            "product_release": False,
        },
        "next_checkpoint": "22E_paid_api_bake_off_after_owner_commit_and_explicit_approval",
    }
    report_errors = validate_safe_benchmark_report(report)
    if report_errors:
        raise ValueError("; ".join(report_errors))
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=REPORT_PATH)
    args = parser.parse_args()
    report = build_report()
    output = args.output.resolve()
    output.write_bytes(canonical_json_bytes(report))
    print(f"Safe checkpoint 22D report: {output.relative_to(REPOSITORY_ROOT)}")
    print(f"SHA256: {file_sha256(output)}")
    print("Scientific release, product release and every downstream use remain locked.")


if __name__ == "__main__":
    main()
