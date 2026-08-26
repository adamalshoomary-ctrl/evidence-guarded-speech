"""Summarise pronunciation candidates against independent human references."""

from __future__ import annotations

from collections import defaultdict

from assessment.pronunciation import PHONE_OUTCOMES, WORD_OUTCOMES


BENCHMARK_SPLITS = {"development", "threshold_tuning", "held_out_evaluation"}
HUMAN_REFERENCE_SOURCE = (
    "blind_listeners_and_qualified_phonetic_adjudication"
)
SCORABLE_WORD_OUTCOMES = WORD_OUTCOMES - {"uncertain", "unscorable"}
SCORABLE_PHONE_OUTCOMES = PHONE_OUTCOMES - {"uncertain", "unscorable"}
PHONE_ISSUES = SCORABLE_PHONE_OUTCOMES - {"accepted_variant"}


class PronunciationBenchmarkError(ValueError):
    """Raised when benchmark records cannot support a fair comparison."""


def _safe_ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def validate_benchmark_records(records):
    """Return errors for malformed or scientifically unsafe benchmark data."""
    errors = []
    seen_trials = set()
    participant_splits = defaultdict(set)

    if not isinstance(records, list) or not records:
        return ["benchmark records must be a nonempty list"]

    for index, record in enumerate(records):
        location = f"records[{index}]"
        required = {
            "trial_id", "participant_id", "split", "human_reference",
            "candidate_outputs",
        }
        if not isinstance(record, dict) or not required.issubset(record):
            errors.append(f"{location} is missing required fields")
            continue

        trial_id = record["trial_id"]
        if trial_id in seen_trials:
            errors.append(f"duplicate trial_id: {trial_id}")
        seen_trials.add(trial_id)

        split = record["split"]
        if split not in BENCHMARK_SPLITS:
            errors.append(f"{location}.split is unsupported")
        participant_splits[record["participant_id"]].add(split)

        reference = record["human_reference"]
        if reference.get("source") != HUMAN_REFERENCE_SOURCE:
            errors.append(f"{location} does not use independent human truth")
        if reference.get("listener_word_outcome") not in WORD_OUTCOMES:
            errors.append(f"{location} has an unsupported listener outcome")
        slots = reference.get("phonetic_slots")
        if not isinstance(slots, list):
            errors.append(f"{location}.human_reference.phonetic_slots must be a list")
            slots = []
        reference_slot_ids = []
        for slot in slots:
            if not isinstance(slot, dict) or set(slot) != {"slot_id", "outcome"}:
                errors.append(f"{location} has a malformed human phonetic slot")
                continue
            reference_slot_ids.append(slot["slot_id"])
            if slot["outcome"] not in PHONE_OUTCOMES:
                errors.append(f"{location} has an unsupported human phone outcome")
        if len(reference_slot_ids) != len(set(reference_slot_ids)):
            errors.append(f"{location} has duplicate human phonetic slot ids")

        candidates = record["candidate_outputs"]
        if not isinstance(candidates, dict):
            errors.append(f"{location}.candidate_outputs must be an object")
            continue
        for candidate_id, candidate in candidates.items():
            status = candidate.get("status")
            if status not in {"available", "unavailable"}:
                errors.append(
                    f"{location}.{candidate_id}.status is unsupported"
                )
                continue
            if status == "unavailable":
                continue
            if candidate.get("word_outcome") not in WORD_OUTCOMES:
                errors.append(
                    f"{location}.{candidate_id} has an unsupported word outcome"
                )
            candidate_slots = candidate.get("phonetic_slots")
            if not isinstance(candidate_slots, list):
                errors.append(
                    f"{location}.{candidate_id}.phonetic_slots must be a list"
                )
                continue
            candidate_slot_ids = []
            for slot in candidate_slots:
                if (not isinstance(slot, dict)
                        or set(slot) != {"slot_id", "outcome"}):
                    errors.append(
                        f"{location}.{candidate_id} has a malformed phonetic slot"
                    )
                    continue
                candidate_slot_ids.append(slot["slot_id"])
                if slot["slot_id"] not in reference_slot_ids:
                    errors.append(
                        f"{location}.{candidate_id} has an unknown phonetic slot"
                    )
                if slot["outcome"] not in PHONE_OUTCOMES:
                    errors.append(
                        f"{location}.{candidate_id} has an unsupported phone outcome"
                    )
            if len(candidate_slot_ids) != len(set(candidate_slot_ids)):
                errors.append(
                    f"{location}.{candidate_id} has duplicate phonetic slot ids"
                )

    for participant_id, splits in participant_splits.items():
        if len(splits) > 1:
            errors.append(
                f"participant {participant_id} appears in multiple data splits"
            )
    return errors


def summarise_candidate(records, candidate_id):
    """Return research metrics for one candidate, never a product score."""
    errors = validate_benchmark_records(records)
    if errors:
        raise PronunciationBenchmarkError("\n".join(errors))

    counts = {
        "trials": 0,
        "candidate_unavailable_trials": 0,
        "scorable_word_opportunities": 0,
        "covered_word_opportunities": 0,
        "word_outcome_exact_matches": 0,
        "scorable_phone_opportunities": 0,
        "covered_phone_opportunities": 0,
        "phone_outcome_exact_matches": 0,
        "phone_issue_true_positives": 0,
        "phone_issue_false_positives": 0,
        "phone_issue_false_negatives": 0,
        "accepted_variant_covered_opportunities": 0,
        "accepted_variant_false_concerns": 0,
    }

    for record in records:
        counts["trials"] += 1
        reference = record["human_reference"]
        candidate = record["candidate_outputs"].get(candidate_id)
        available = candidate is not None and candidate["status"] == "available"
        if not available:
            counts["candidate_unavailable_trials"] += 1

        word_truth = reference["listener_word_outcome"]
        if word_truth in SCORABLE_WORD_OUTCOMES:
            counts["scorable_word_opportunities"] += 1
            word_prediction = candidate.get("word_outcome") if available else None
            if word_prediction in SCORABLE_WORD_OUTCOMES:
                counts["covered_word_opportunities"] += 1
                if word_prediction == word_truth:
                    counts["word_outcome_exact_matches"] += 1

        predicted_slots = {
            item["slot_id"]: item["outcome"]
            for item in (candidate.get("phonetic_slots", []) if available else [])
        }
        for slot in reference["phonetic_slots"]:
            truth = slot["outcome"]
            if truth not in SCORABLE_PHONE_OUTCOMES:
                continue
            counts["scorable_phone_opportunities"] += 1
            prediction = predicted_slots.get(slot["slot_id"])
            covered = prediction in SCORABLE_PHONE_OUTCOMES
            if covered:
                counts["covered_phone_opportunities"] += 1
                if prediction == truth:
                    counts["phone_outcome_exact_matches"] += 1

            truth_issue = truth in PHONE_ISSUES
            predicted_issue = covered and prediction in PHONE_ISSUES
            if truth_issue and predicted_issue:
                counts["phone_issue_true_positives"] += 1
            elif not truth_issue and predicted_issue:
                counts["phone_issue_false_positives"] += 1
            elif truth_issue and not predicted_issue:
                counts["phone_issue_false_negatives"] += 1

            if truth == "accepted_variant" and covered:
                counts["accepted_variant_covered_opportunities"] += 1
                if predicted_issue:
                    counts["accepted_variant_false_concerns"] += 1

    tp = counts["phone_issue_true_positives"]
    fp = counts["phone_issue_false_positives"]
    fn = counts["phone_issue_false_negatives"]
    precision = _safe_ratio(tp, tp + fp)
    recall = _safe_ratio(tp, tp + fn)
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall
        else None
    )
    return {
        "candidate_id": candidate_id,
        "claim_scope": "research_comparison_only",
        "counts": counts,
        "metrics": {
            "word_coverage": _safe_ratio(
                counts["covered_word_opportunities"],
                counts["scorable_word_opportunities"],
            ),
            "word_outcome_exact_agreement": _safe_ratio(
                counts["word_outcome_exact_matches"],
                counts["covered_word_opportunities"],
            ),
            "phone_coverage": _safe_ratio(
                counts["covered_phone_opportunities"],
                counts["scorable_phone_opportunities"],
            ),
            "phone_outcome_exact_agreement": _safe_ratio(
                counts["phone_outcome_exact_matches"],
                counts["covered_phone_opportunities"],
            ),
            "phone_issue_precision": precision,
            "phone_issue_recall": recall,
            "phone_issue_f1": f1,
            "accepted_variant_false_concern_rate": _safe_ratio(
                counts["accepted_variant_false_concerns"],
                counts["accepted_variant_covered_opportunities"],
            ),
        },
    }
