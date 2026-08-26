"""Build private relation rows and safe aggregates for checkpoint 22D."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from .benchmark import (
    FROZEN_BENCHMARK_MANIFEST_SHA256,
    PRIVATE_BENCHMARK_ROOT,
    canonical_json_sha256,
    insertion_consensus,
    insertion_predictions,
    load_benchmark_contract,
    load_phone_map,
    parse_review_phone_string,
    ratio_record,
    reviewer_agreement,
    score_binary_rows,
    scorable_reference_phone,
    strip_stress,
    target_consensus,
    target_predictions,
    validate_frozen_private_benchmark_manifest,
)
from .feasibility import REPOSITORY_ROOT, canonical_json_bytes, file_sha256


PRIVATE_ROOT = REPOSITORY_ROOT / ".research_data" / "speech_sound_patterns"
DEFAULT_MANIFEST = PRIVATE_ROOT / "benchmark" / "benchmark-manifest-v1.0.0.json"
DEFAULT_XEUS = (
    PRIVATE_BENCHMARK_ROOT
    / "v1"
    / "evidence"
    / "phoneticxeus"
    / "phoneticxeus-benchmark-process.json"
)
DEFAULT_OUTPUT = PRIVATE_BENCHMARK_ROOT / "v1" / "evidence" / "scoring"


def _load_verified(path, expected_sha256=None):
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"private benchmark evidence is missing: {path.name}")
    if expected_sha256 is not None and file_sha256(path) != expected_sha256:
        raise ValueError(f"private benchmark evidence changed: {path.name}")
    return json.loads(path.read_text(encoding="utf-8"))


def _source(manifest, source_id):
    matches = [item for item in manifest["sources"] if item["source_id"] == source_id]
    if len(matches) != 1:
        raise ValueError(f"private benchmark source {source_id} is unavailable")
    return matches[0]


def _age_stratum(source_stratum):
    if source_stratum.startswith("source_adult_"):
        return "adult"
    if source_stratum.startswith("source_child_"):
        return "child"
    raise ValueError("SpeechOcean age stratum is unavailable")


def _truth_state(decision, positive, negative):
    if decision == positive:
        return "positive"
    if decision == negative:
        return "negative"
    return "unscorable"


def _prediction_state(state, positive, negative):
    if state == positive:
        return "positive"
    if state == negative:
        return "negative"
    return "abstain"


def _scorable_inserted_reference(phones, phone_map):
    if not phones:
        return False
    for phone in phones:
        try:
            base = strip_stress(phone)
        except ValueError:
            return False
        item = phone_map["reference_phones"].get(base)
        if not item or item["class"] != "consonant" or item["scorable"] is False:
            return False
    return True


def _exact_expected_ipa(phone, phone_map):
    try:
        base = strip_stress(phone)
    except ValueError:
        return None
    item = phone_map["reference_phones"].get(base)
    if not item or item["class"] != "consonant" or len(item["ipa"]) != 1:
        return None
    return item["ipa"][0]


def score_speechocean(manifest, xeus_summary, xeus_process_sha256, output_root):
    phone_map = load_phone_map()
    source = _source(manifest, "speechocean762")
    reference = _load_verified(
        REPOSITORY_ROOT / source["private_reference_path"],
        source["private_reference_sha256"],
    )
    references = {item["safe_id"]: item for item in reference["records"]}
    clips = {item["safe_id"]: item for item in source["clips"]}
    xeus_index = {
        item["safe_id"]: item
        for item in xeus_summary["clips"]
        if item["source_id"] == "speechocean762"
    }
    if set(references) != set(clips) or set(clips) != set(xeus_index):
        raise ValueError("SpeechOcean reference, clip and model indexes differ")

    target_rows = []
    insertion_rows = []
    exact_rows = []
    agreement_rows = defaultdict(list)
    participant_sets = defaultdict(set)
    clip_counts = Counter()
    for safe_id in sorted(clips):
        clip = clips[safe_id]
        record = references[safe_id]
        if canonical_json_sha256(record) != clip["reference_record_sha256"]:
            raise ValueError(f"SpeechOcean reference row changed for {safe_id}")
        xeus_item = xeus_index[safe_id]
        output = _load_verified(
            REPOSITORY_ROOT / xeus_item["output_path"], xeus_item["output_sha256"]
        )
        if output["input_sha256"] != clip["canonical_audio_sha256"]:
            raise ValueError(f"SpeechOcean model input changed for {safe_id}")
        if not all(
            item["frame_ids_exact_match_first"]
            and item["collapsed_ids_exact_match_first"]
            for item in output["repeats"]
        ):
            raise ValueError(f"SpeechOcean repeatability failed for {safe_id}")
        split = clip["project_split"]
        age = _age_stratum(clip["source_stratum"])
        partition = (split, age)
        participant_sets[partition].add(clip["private_participant_id"])
        clip_counts[partition] += 1

        reference_phones = []
        word_starts = set()
        word_offsets = []
        parsed_words = []
        for word in record["words"]:
            word_starts.add(len(reference_phones))
            word_offsets.append(len(reference_phones))
            phones = word["reference_phones"].split()
            reference_phones.extend(phones)
            parsed = [
                parse_review_phone_string(word["reference_phones"], reviewer)
                for reviewer in word["five_reviewer_phone_strings"]
            ]
            parsed_words.append((word, phones, parsed))
        model = target_predictions(
            reference_phones,
            output["collapsed_tokens"],
            phone_map,
            word_starts,
        )
        target_by_index = {item["target_index"]: item for item in model["targets"]}
        model_insertions = insertion_predictions(
            model["alignment"],
            output["panphon_classifications"],
            len(reference_phones),
        )

        for word_position, (word, phones, parsed) in enumerate(parsed_words):
            offset = word_offsets[word_position]
            aggregate_by_index = {
                int(item["index"]): item
                for item in word["aggregate_mispronunciations"]
            }
            for local_index, phone in enumerate(phones):
                scorable, reason = scorable_reference_phone(
                    phones, local_index, phone_map
                )
                if not scorable:
                    continue
                reviewer_states = [
                    item["targets"][local_index]["state"] for item in parsed
                ]
                consensus = target_consensus(reviewer_states)
                global_index = offset + local_index
                prediction = target_by_index[global_index]
                target_rows.append(
                    {
                        "safe_id": safe_id,
                        "private_participant_id": clip["private_participant_id"],
                        "project_split": split,
                        "age_stratum": age,
                        "source_stratum": clip["source_stratum"],
                        "word_index": word["word_index"],
                        "target_index": local_index,
                        "reference_phone": strip_stress(phone),
                        "reviewer_states": reviewer_states,
                        "reference_decision": consensus["decision"],
                        "truth": _truth_state(
                            consensus["decision"],
                            "coarse_relation_present",
                            "no_relation_concern",
                        ),
                        "model_state": prediction["state"],
                        "model_relation_type": prediction.get("relation_type"),
                        "model_observed_phone": prediction.get("observed_phone"),
                        "prediction": _prediction_state(
                            prediction["state"],
                            "coarse_relation_candidate",
                            "no_relation_candidate",
                        ),
                        "abstention_reason": prediction.get("reason"),
                    }
                )
                agreement_rows[partition].append(reviewer_states)

                aggregate = aggregate_by_index.get(local_index)
                if aggregate is not None:
                    expected_ipa = _exact_expected_ipa(
                        aggregate["pronounced-phone"], phone_map
                    )
                    if expected_ipa is not None:
                        exact_rows.append(
                            {
                                "safe_id": safe_id,
                                "private_participant_id": clip[
                                    "private_participant_id"
                                ],
                                "project_split": split,
                                "age_stratum": age,
                                "canonical_phone": aggregate["canonical-phone"],
                                "pronounced_phone": aggregate["pronounced-phone"],
                                "expected_ipa": expected_ipa,
                                "model_relation_type": prediction.get(
                                    "relation_type"
                                ),
                                "model_observed_phone": prediction.get(
                                    "observed_phone"
                                ),
                                "model_exact_match": (
                                    prediction.get("relation_type") == "substitution"
                                    and prediction.get("observed_phone") == expected_ipa
                                ),
                                "supporting_reference_only": True,
                            }
                        )

            for local_boundary in range(1, len(phones)):
                consensus = insertion_consensus(
                    [item["insertions"] for item in parsed], local_boundary
                )
                truth = _truth_state(
                    consensus["decision"],
                    "explicit_insertion_present",
                    "no_insertion",
                )
                if truth == "positive" and not _scorable_inserted_reference(
                    consensus["phones"], phone_map
                ):
                    truth = "unscorable"
                candidates = model_insertions[offset + local_boundary]
                consonants = [
                    item
                    for item in candidates
                    if item["state"] == "consonant_insertion_candidate"
                ]
                abstained = any(item["state"] == "abstain" for item in candidates)
                if abstained:
                    prediction = "abstain"
                elif consonants:
                    prediction = "positive"
                else:
                    prediction = "negative"
                insertion_rows.append(
                    {
                        "safe_id": safe_id,
                        "private_participant_id": clip["private_participant_id"],
                        "project_split": split,
                        "age_stratum": age,
                        "word_index": word["word_index"],
                        "boundary_index": local_boundary,
                        "reference_decision": consensus["decision"],
                        "reference_inserted_phones": consensus["phones"],
                        "truth": truth,
                        "model_candidates": candidates,
                        "prediction": prediction,
                    }
                )

    partitions = []
    for split in ("development", "threshold_tuning"):
        for age in ("adult", "child"):
            key = (split, age)
            targets = [
                {"truth": row["truth"], "prediction": row["prediction"]}
                for row in target_rows
                if (row["project_split"], row["age_stratum"]) == key
            ]
            insertions = [
                {"truth": row["truth"], "prediction": row["prediction"]}
                for row in insertion_rows
                if (row["project_split"], row["age_stratum"]) == key
            ]
            exact = [
                row
                for row in exact_rows
                if (row["project_split"], row["age_stratum"]) == key
            ]
            exact_covered = sum(
                row["model_relation_type"] == "substitution" for row in exact
            )
            exact_matches = sum(row["model_exact_match"] for row in exact)
            partitions.append(
                {
                    "project_split": split,
                    "age_stratum": age,
                    "participants": len(participant_sets[key]),
                    "clips": clip_counts[key],
                    "coarse_target_relation": score_binary_rows(targets),
                    "explicit_internal_consonant_insertion": score_binary_rows(
                        insertions
                    ),
                    "five_reviewer_target_agreement": reviewer_agreement(
                        agreement_rows[key]
                    ),
                    "aggregate_exact_substitution_support": {
                        "explicit_in_scope_relations": len(exact),
                        "model_substitution_candidates_at_those_targets": exact_covered,
                        "exact_phone_matches": exact_matches,
                        "exact_match_per_explicit_relation": ratio_record(
                            exact_matches, len(exact)
                        ),
                        "exact_match_per_covered_model_substitution": ratio_record(
                            exact_matches, exact_covered
                        ),
                        "not_precision_or_independent_truth": True,
                    },
                }
            )

    private_document = {
        "schema_version": "1.0.0",
        "evidence_id": "speech_sound_relation_scoring_private_v1",
        "private_benchmark_manifest_sha256": FROZEN_BENCHMARK_MANIFEST_SHA256,
        "phoneticxeus_process_sha256": xeus_process_sha256,
        "held_out_evaluation": False,
        "source_id": "speechocean762",
        "truth_class": "expert_phone_relations",
        "target_rows": target_rows,
        "insertion_rows": insertion_rows,
        "aggregate_exact_substitution_rows": exact_rows,
    }
    output_root.mkdir(parents=True, exist_ok=True)
    private_path = output_root / "speechocean-relation-evidence.json"
    if private_path.exists():
        raise ValueError("private SpeechOcean scoring evidence already exists")
    private_path.write_bytes(canonical_json_bytes(private_document))
    aggregate = {
        "source_id": "speechocean762",
        "truth_class": "expert_phone_relations",
        "population_boundary": (
            "Mandarin-first-language child and adult readers; not representative "
            "Australian or world English evidence"
        ),
        "reference_rule": (
            "four of five original reviewers; disputed records unscorable; "
            "parentheses remain unresolved incorrect-or-missed relations"
        ),
        "private_evidence_sha256": file_sha256(private_path),
        "partitions": partitions,
    }
    return private_path, aggregate


def run_scoring(manifest_path=DEFAULT_MANIFEST, xeus_path=DEFAULT_XEUS, output_root=DEFAULT_OUTPUT):
    manifest = _load_verified(manifest_path)
    errors = validate_frozen_private_benchmark_manifest(
        manifest, FROZEN_BENCHMARK_MANIFEST_SHA256
    )
    if errors:
        raise ValueError("; ".join(errors))
    xeus = _load_verified(xeus_path)
    if xeus.get("private_benchmark_manifest_sha256") != FROZEN_BENCHMARK_MANIFEST_SHA256:
        raise ValueError("PhoneticXEUS evidence belongs to another benchmark")
    if len(xeus.get("clips", [])) != 565:
        raise ValueError("PhoneticXEUS evidence is incomplete")
    if not all(item.get("repeatability_passed") is True for item in xeus["clips"]):
        raise ValueError("PhoneticXEUS benchmark repeatability failed")
    private_path, aggregate = score_speechocean(
        manifest, xeus, file_sha256(xeus_path), Path(output_root).resolve()
    )
    aggregate_path = Path(output_root).resolve() / "speechocean-aggregate.json"
    aggregate_path.write_bytes(canonical_json_bytes(aggregate))
    return private_path, aggregate_path, aggregate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--phoneticxeus", type=Path, default=DEFAULT_XEUS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    private_path, aggregate_path, aggregate = run_scoring(
        args.manifest.resolve(), args.phoneticxeus.resolve(), args.output.resolve()
    )
    print(f"Private relation evidence: {private_path.relative_to(REPOSITORY_ROOT)}")
    print(f"Private aggregate evidence: {aggregate_path.relative_to(REPOSITORY_ROOT)}")
    for partition in aggregate["partitions"]:
        metrics = partition["coarse_target_relation"]
        print(
            partition["project_split"],
            partition["age_stratum"],
            f"precision={metrics['precision']['value']}",
            f"recall={metrics['recall']['value']}",
            f"coverage={metrics['coverage']['value']}",
        )


if __name__ == "__main__":
    main()
