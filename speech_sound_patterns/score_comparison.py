"""Join every checkpoint 22E4 lane to the frozen expert relations and score it.

This is the first step in the checkpoint that is allowed to read an expert
outcome, and it may only run once every candidate output is complete. Each lane
produced its evidence label blind; here that evidence meets the truth, under the
thresholds and gates frozen before anything ran.

Nothing in this module chooses a candidate. It computes what each candidate did,
whether any operating point passes both partitions, and, when none does, the
closest point under the frozen reporting rule. A no-selection is a result.

    python3 -m speech_sound_patterns.score_comparison
"""

from __future__ import annotations

import argparse
import functools
import json
from collections import Counter, defaultdict
from pathlib import Path

from .comparison import (
    ACTIVE_COMPARISON_VERSION,
    CANDIDATE_PROFILES,
    CONTINUOUS_CANDIDATES,
    DEFAULT_COMPARISON_VERSION,
    SCORE_ROUNDING,
    ComparisonError,
    assert_valid_comparison_contract,
    average_precision,
    comparison_profile,
    azure_word_alignment,
    candidate_inventory,
    coverage_record,
    free_phone_target_states,
    load_expected_manifest,
    load_relation_rows,
    normalized_ipa,
    participant_metrics,
    partition_metrics,
    phone_map as load_frozen_phone_map,
    predictions_at_threshold,
    provider_word_alignment,
    threshold_search,
    verify_frozen_inputs,
)
from .feasibility import REPOSITORY_ROOT, canonical_json_bytes, file_sha256


# Which frozen comparison this process is scoring. It is set once, by
# ``run_scoring``, before any evidence is read.
_ACTIVE_VERSION = DEFAULT_COMPARISON_VERSION


def _profile():
    return comparison_profile(_ACTIVE_VERSION)


def evidence_root():
    return _profile()["private_root"] / "evidence"


def reference_path():
    return _profile()["sample_root"] / "references" / "speechocean762.json"


def default_output(version=ACTIVE_COMPARISON_VERSION):
    return comparison_profile(version)["private_root"] / "evidence" / "scoring"

AZURE_LOCALE_BY_CANDIDATE = {
    "azure_en_us_phone_score": "en-US",
    "azure_en_us_named_relation": "en-US",
    "azure_en_au_phone_score": "en-AU",
}


def _load_json(path):
    path = Path(path)
    if not path.is_file():
        raise ComparisonError(f"comparison evidence is missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


@functools.lru_cache(maxsize=None)
def _frozen_phone_map():
    """Read the frozen phone map once; it is immutable within a run."""
    return load_frozen_phone_map()


@functools.lru_cache(maxsize=None)
def _clip_records(lane_directory):
    # Cached per lane within one scoring run. ``run_scoring`` clears the cache
    # when it sets the active version, so evidence from one frozen comparison can
    # never be read while scoring the other.
    clips_root = evidence_root() / lane_directory / "clips"
    if not clips_root.is_dir():
        raise ComparisonError(f"{lane_directory} produced no clip evidence")
    records = {}
    for path in sorted(clips_root.glob("*.json")):
        record = _load_json(path)
        records[path.stem] = record
    return records


def _require_complete_process(lane_directory, filename, expected_clips):
    summary = _load_json(evidence_root() / lane_directory / filename)
    execution = summary.get("execution", {})
    if execution.get("expert_outcomes_read_by_candidate_runner") is not False:
        raise ComparisonError(f"{lane_directory} claims it read an expert outcome")
    if execution.get("all_repeats_exact") is not True:
        raise ComparisonError(f"{lane_directory} did not repeat exactly")
    if execution.get("held_out_participants") != 0:
        raise ComparisonError(f"{lane_directory} touched a held-out participant")
    if execution.get("clip_count") != expected_clips:
        raise ComparisonError(
            f"{lane_directory} completed {execution.get('clip_count')} clips, "
            f"expected {expected_clips}"
        )
    return summary


def _blank_row(relation, reason):
    return {
        "safe_id": relation["safe_id"],
        "private_participant_id": relation["private_participant_id"],
        "project_split": relation["project_split"],
        "age_stratum": relation["age_stratum"],
        "word_index": relation["word_index"],
        "target_index": relation["target_index"],
        "arpabet": relation["reference_phone"],
        "truth": relation["truth"],
        "label": int(relation["truth"] == "positive"),
        "state": "abstain",
        "abstention_reason": reason,
        "concern_score": None,
        "observed_phone": None,
    }


# --------------------------------------------------------------------------
# Lane row builders
# --------------------------------------------------------------------------


def sfgop_rows(relations, manifest, score_field):
    """Rows for one segmentation-free GOP variant.

    The published score is a log posterior for the expected phone, so a higher
    value means a better production. The concern score is its negation, which
    keeps every candidate in this checkpoint oriented the same way: larger means
    more concerning.
    """
    records = _clip_records("sfgop")
    _require_complete_process(
        "sfgop",
        "sfgop-comparison-process.json",
        _profile()["expected_only_clip_count"],
    )
    by_key = {}
    for clip in manifest["clips"]:
        record = records.get(clip["safe_id"])
        if record is None:
            raise ComparisonError(f"sfgop is missing {clip['safe_id']}")
        global_to_target = {
            target["global_index"]: target for target in clip["targets"]
        }
        for scored in record["evidence"]["targets"]:
            target = global_to_target[scored["global_index"]]
            key = (clip["safe_id"], target["word_index"], target["local_index"])
            by_key[key] = scored

    rows = []
    for relation in relations:
        key = (relation["safe_id"], relation["word_index"], relation["target_index"])
        scored = by_key.get(key)
        if scored is None:
            rows.append(_blank_row(relation, "no_candidate_output_for_target"))
            continue
        if scored["state"] != "scored":
            rows.append(
                _blank_row(
                    relation, scored.get("unscorable_reason") or "candidate_unscorable"
                )
            )
            continue
        value = scored[score_field]
        row = _blank_row(relation, None)
        row.update(
            {
                "state": "scored",
                "abstention_reason": None,
                "concern_score": round(-float(value), SCORE_ROUNDING),
                "observed_phone": (
                    scored["alternatives"][0]["token"]
                    if scored.get("alternatives")
                    else None
                ),
            }
        )
        rows.append(row)
    return rows


def free_phone_rows(lane_directory, process_filename, expected_clips, relations, manifest):
    """Rows for an unconstrained free-phone lane, using the frozen aligner."""
    records = _clip_records(lane_directory)
    _require_complete_process(lane_directory, process_filename, expected_clips)
    frozen_map = _frozen_phone_map()
    inventory = candidate_inventory(frozen_map)
    by_key = {}
    for clip in manifest["clips"]:
        record = records.get(clip["safe_id"])
        if record is None:
            raise ComparisonError(f"{lane_directory} is missing {clip['safe_id']}")
        if record.get("target_given_to_model") is not False:
            raise ComparisonError(f"{lane_directory} was given a target")
        if record.get("processed", True) is False:
            # The lane could not accept this clip at all, so it has no opinion
            # about any target in it. Every target abstains with the recorded
            # reason rather than being scored against an empty phone sequence,
            # which would read as a deletion at every position.
            for target in clip["targets"]:
                key = (clip["safe_id"], target["word_index"], target["local_index"])
                by_key[key] = {
                    "state": "abstain",
                    "relation_type": None,
                    "observed_phone": None,
                    "reason": record["unprocessable_reason"],
                }
            continue
        states = free_phone_target_states(
            clip, record["phones"], frozen_map, inventory
        )
        global_to_target = {
            target["global_index"]: target for target in clip["targets"]
        }
        for global_index, state in states.items():
            target = global_to_target.get(global_index)
            if target is None:
                continue
            key = (clip["safe_id"], target["word_index"], target["local_index"])
            by_key[key] = state

    rows = []
    for relation in relations:
        key = (relation["safe_id"], relation["word_index"], relation["target_index"])
        state = by_key.get(key)
        if state is None:
            rows.append(_blank_row(relation, "no_candidate_output_for_target"))
            continue
        if state["state"] == "abstain":
            rows.append(_blank_row(relation, state.get("reason") or "abstain"))
            continue
        row = _blank_row(relation, None)
        row.update(
            {
                "state": "scored",
                "abstention_reason": None,
                # A binary lane has no dial to turn. It is recorded at a fixed
                # concern score of one so it flows through the same scoring
                # path, and its threshold grid collapses to a single point.
                "concern_score": (
                    1.0 if state["state"] == "coarse_relation_candidate" else 0.0
                ),
                "observed_phone": state.get("observed_phone"),
                "relation_type": state.get("relation_type"),
            }
        )
        rows.append(row)
    return rows


def _azure_positions(clip, reference_words, record):
    """Locate this project's targets inside one provider response.

    Two alignments are needed and both can fail closed. The provider's word list
    contains words the reference does not, so words are aligned first. Within a
    matched word the provider uses its own lexicon, so a target counts only when
    the provider expected the same phone in the same place.
    """
    observation = record.get("observation")
    if not observation:
        return {}, "no_successful_provider_response"
    provider_words = observation.get("words") or []
    if not provider_words:
        return {}, "provider_returned_no_words"
    word_positions = provider_word_alignment(reference_words, provider_words)

    starts = list(clip["word_starts"]) + [len(clip["reference_phones"])]
    frozen_map = _frozen_phone_map()
    located = {}
    for word_index in range(len(reference_words)):
        provider_index = word_positions.get(word_index)
        if provider_index is None:
            continue
        provider_word = provider_words[provider_index]
        reference_arpabet = clip["reference_phones"][
            starts[word_index] : starts[word_index + 1]
        ]
        provider_phones = [
            phoneme.get("expected_phoneme") or ""
            for phoneme in provider_word["phonemes"]
        ]
        matched = azure_word_alignment(
            reference_arpabet, provider_phones, frozen_map
        )
        for local_index, provider_position in matched.items():
            located[(word_index, local_index)] = provider_word["phonemes"][
                provider_position
            ]
    return located, None


def azure_reference_agreement(locale, manifest, references):
    """Describe how far the provider's lexicon sits from this project's.

    This is descriptive only and is never a scoring path. It exists because the
    Australian locale names no phone, so the only visible sign of how much its
    reference differs is whether it expects the same number of phones in a word.
    A matching count is not evidence that the phones are the same.
    """
    records = _clip_records("azure")
    clips = {clip["safe_id"]: clip for clip in manifest["clips"]}
    counts = Counter()
    for key, record in records.items():
        if record["locale"] != locale:
            continue
        clip = clips[record["safe_id"]]
        observation = record.get("observation")
        if not observation:
            counts["clips_without_a_response"] += 1
            continue
        counts["clips"] += 1
        reference_words = [
            word["text"] for word in references[record["safe_id"]]["words"]
        ]
        provider_words = observation.get("words") or []
        matched = provider_word_alignment(reference_words, provider_words)
        counts["reference_words"] += len(reference_words)
        counts["reference_words_matched"] += len(matched)
        starts = list(clip["word_starts"]) + [len(clip["reference_phones"])]
        for word_index, provider_index in matched.items():
            names = [
                phoneme.get("expected_phoneme") or ""
                for phoneme in provider_words[provider_index]["phonemes"]
            ]
            counts["provider_phone_positions"] += len(names)
            counts["named_provider_phone_positions"] += sum(1 for name in names if name)
            reference_count = starts[word_index + 1] - starts[word_index]
            if reference_count == len(names):
                counts["words_expecting_the_same_phone_count"] += 1
            else:
                counts["words_expecting_a_different_phone_count"] += 1
    return {
        **{key: counts[key] for key in sorted(counts)},
        "matching_phone_count_is_not_matching_phones": True,
        "used_for_scoring": False,
    }


def azure_rows(candidate_id, relations, manifest, references):
    """Rows for one Azure candidate, in one locale, never pooled."""
    locale = AZURE_LOCALE_BY_CANDIDATE[candidate_id]
    records = _clip_records("azure")
    summary = _load_json(evidence_root() / "azure" / "azure-comparison-process.json")
    if summary.get("locales_pooled") is not False:
        raise ComparisonError("the Azure process claims pooled locales")
    if summary["transmission"]["child_clips_transmitted"] != 0:
        raise ComparisonError("the Azure process claims a child clip was sent")

    clips = {clip["safe_id"]: clip for clip in manifest["clips"]}
    # One alignment per clip, not one per target. The alignment is a property of
    # the clip and the locale, so recomputing it for each of a clip's targets
    # would repeat identical work thousands of times.
    located_by_clip = {}
    failure_by_clip = {}
    for record in records.values():
        if record["locale"] != locale:
            continue
        clip = clips.get(record["safe_id"])
        if clip is None:
            raise ComparisonError(f"{record['safe_id']} is not in the frozen manifest")
        reference_words = [
            word["text"] for word in references[record["safe_id"]]["words"]
        ]
        if record.get("same_input_repeats_exact") is not True:
            # The frozen contract grants zero numeric tolerance for an identical
            # repeated request. A configuration whose two responses disagreed is
            # not trustworthy evidence about that clip, so every target in it
            # abstains for this candidate and the count is reported. Scoring it
            # anyway would let one non-deterministic response into the metrics,
            # which is exactly what two repeats exist to prevent.
            located_by_clip[record["safe_id"]] = {}
            failure_by_clip[record["safe_id"]] = "provider_did_not_repeat_exactly"
            continue
        located, failure = _azure_positions(clip, reference_words, record)
        located_by_clip[record["safe_id"]] = located
        failure_by_clip[record["safe_id"]] = failure

    rows = []
    failures = Counter()
    for relation in relations:
        safe_id = relation["safe_id"]
        if safe_id not in located_by_clip:
            # Children and any clip outside the transmitted adult set were
            # deliberately never sent. That is a boundary, not a failure.
            rows.append(_blank_row(relation, "clip_not_transmitted_to_provider"))
            continue
        failure = failure_by_clip[safe_id]
        if failure:
            failures[failure] += 1
            rows.append(_blank_row(relation, failure))
            continue
        located = located_by_clip[safe_id]
        phoneme = located.get((relation["word_index"], relation["target_index"]))
        if phoneme is None:
            rows.append(_blank_row(relation, "provider_reference_disagreement"))
            continue

        if candidate_id.endswith("_phone_score"):
            score = phoneme.get("accuracy_score")
            if score is None:
                rows.append(_blank_row(relation, "provider_returned_no_score"))
                continue
            row = _blank_row(relation, None)
            row.update(
                {
                    "state": "scored",
                    "abstention_reason": None,
                    "concern_score": round(100.0 - float(score), SCORE_ROUNDING),
                    "observed_phone": None,
                }
            )
            rows.append(row)
            continue

        candidates = phoneme.get("nbest") or []
        if not candidates or not candidates[0].get("phoneme"):
            rows.append(_blank_row(relation, "provider_named_no_candidate_phone"))
            continue
        top = normalized_ipa(candidates[0]["phoneme"])
        expected = normalized_ipa(phoneme.get("expected_phoneme") or "")
        if not expected:
            rows.append(_blank_row(relation, "provider_named_no_expected_phone"))
            continue
        row = _blank_row(relation, None)
        row.update(
            {
                "state": "scored",
                "abstention_reason": None,
                "concern_score": 1.0 if top != expected else 0.0,
                "observed_phone": candidates[0]["phoneme"],
            }
        )
        rows.append(row)
    return rows, dict(failures)


# --------------------------------------------------------------------------
# Scoring
# --------------------------------------------------------------------------


def _partition(rows, split, age):
    return [
        row
        for row in rows
        if row["project_split"] == split and row["age_stratum"] == age
    ]


def _false_positive_phones(rows, threshold):
    """Every expected phone this candidate falsely raised a concern about.

    Reported in full rather than as a top ten, because the shape of the tail is
    what tells a reader whether a candidate has one fixable blind spot or is
    simply over-flagging everywhere.
    """
    counts = Counter()
    for row in predictions_at_threshold(rows, threshold):
        if row["prediction"] == "positive" and row["truth"] == "negative":
            counts[row["arpabet"]] += 1
    return dict(sorted(counts.items()))


AFFRICATE_TARGETS = {"JH", "CH"}


def _affricate_accounting(rows, threshold):
    """Separate the known affricate mismatch from a candidate's other errors.

    The frozen reference expects one tie-barred token for an affricate, while a
    free-phone model may emit the two component phones. That produces a concern
    the speaker did not earn. Recording it separately lets a reader see whether
    a candidate's failure is that fixable mapping mismatch or something larger.
    """
    decided = predictions_at_threshold(
        [row for row in rows if row["truth"] != "unscorable"], threshold
    )
    affricates = [row for row in decided if row["arpabet"] in AFFRICATE_TARGETS]
    false_concerns = [
        row
        for row in decided
        if row["prediction"] == "positive" and row["truth"] == "negative"
    ]
    affricate_false_concerns = [
        row for row in false_concerns if row["arpabet"] in AFFRICATE_TARGETS
    ]
    return {
        "affricate_targets": len(affricates),
        "affricate_false_concerns": len(affricate_false_concerns),
        "all_false_concerns": len(false_concerns),
        "affricate_share_of_false_concerns": (
            None
            if not false_concerns
            else round(len(affricate_false_concerns) / len(false_concerns), 6)
        ),
        "false_concerns_excluding_affricates": (
            len(false_concerns) - len(affricate_false_concerns)
        ),
    }


def _dominant_abstention_reason(rows):
    reasons = Counter(
        row.get("abstention_reason") or "unrecorded"
        for row in rows
        if row["state"] != "scored"
    )
    if not reasons:
        return None
    return reasons.most_common(1)[0][0]


BINARY_DECISION_THRESHOLD = 1.0


def single_point_search(development, tuning):
    """Evaluate a binary lane at the one decision it actually makes."""
    development_metrics = partition_metrics(
        predictions_at_threshold(development, BINARY_DECISION_THRESHOLD)
    )
    tuning_metrics = partition_metrics(
        predictions_at_threshold(tuning, BINARY_DECISION_THRESHOLD)
    )
    record = {
        "threshold": BINARY_DECISION_THRESHOLD,
        "development": development_metrics,
        "threshold_tuning": tuning_metrics,
        "both_partitions_pass": (
            development_metrics["selection_gates"]["passed"]
            and tuning_metrics["selection_gates"]["passed"]
        ),
    }
    return {
        "candidate_threshold_count": 1,
        "records": [record],
        "selected": record if record["both_partitions_pass"] else None,
        "closest": record,
        "closest_point_reporting_rule": (
            "a binary lane has one operating point; it is reported as it is"
        ),
    }


def score_candidate(candidate_id, rows, selection_eligible):
    """Apply the frozen procedure to one candidate and report everything."""
    development = _partition(rows, "development", "adult")
    tuning = _partition(rows, "threshold_tuning", "adult")
    for split, adults in (("development", development), ("threshold_tuning", tuning)):
        scorable = sum(1 for row in adults if row["truth"] != "unscorable")
        expected = _profile()["adult_scorable_counts"][split]
        if scorable != expected:
            raise ComparisonError(
                f"{candidate_id}: {split} adult opportunities changed from "
                f"{expected} to {scorable}"
            )

    scored_rows = sum(
        1 for row in development + tuning if row["state"] == "scored"
    )
    if scored_rows == 0:
        # A lane that produced nothing scorable did not fail the gates. It never
        # reached them, and saying otherwise would read as a performance result.
        return {
            "candidate_id": candidate_id,
            "decision_rule": CANDIDATE_PROFILES[candidate_id]["decision_rule"],
            "selection_eligible": selection_eligible,
            "evidence_available": False,
            "no_evidence_reason": _dominant_abstention_reason(development + tuning),
            "candidate_threshold_count": 0,
            "closest_point_reporting_rule": None,
            "coverage": {
                "development_adult": coverage_record(development),
                "threshold_tuning_adult": coverage_record(tuning),
            },
            "development_average_precision": None,
            "any_operating_point_passes_both_partitions": False,
            "reported_operating_point": None,
            "child_diagnostics": None,
        }, None

    binary = candidate_id not in CONTINUOUS_CANDIDATES
    if binary:
        # A binary lane has exactly one honest operating point: the decision it
        # actually makes. Running a grid over it would invent operating points
        # the lane does not offer, and the closest-point rule would then report
        # a "predict everything" or "predict nothing" corner that misrepresents
        # what the model did.
        search = single_point_search(development, tuning)
    else:
        search = threshold_search(development, tuning)
    result = {
        "candidate_id": candidate_id,
        "decision_rule": CANDIDATE_PROFILES[candidate_id]["decision_rule"],
        "selection_eligible": selection_eligible,
        "evidence_available": True,
        "no_evidence_reason": None,
        "candidate_threshold_count": search["candidate_threshold_count"],
        "closest_point_reporting_rule": search["closest_point_reporting_rule"],
        "coverage": {
            "development_adult": coverage_record(development),
            "threshold_tuning_adult": coverage_record(tuning),
        },
        "development_average_precision": (
            None if binary else average_precision(development)
        ),
        "any_operating_point_passes_both_partitions": bool(search["selected"]),
    }

    reported = search["selected"] or search["closest"]
    if reported is None:
        result["reported_operating_point"] = None
        return result, None

    threshold = reported["threshold"]
    result["reported_operating_point"] = {
        "threshold": None if binary else threshold,
        "is_a_selection": bool(search["selected"]),
        "development": reported["development"],
        "threshold_tuning": reported["threshold_tuning"],
        "both_partitions_pass": reported["both_partitions_pass"],
        "gate_checks_passed_of_ten": sum(
            1
            for partition in ("development", "threshold_tuning")
            for passed in reported[partition]["selection_gates"]["checks"].values()
            if passed
        ),
        "false_positive_expected_phones": {
            "development_adult": _false_positive_phones(development, threshold),
            "threshold_tuning_adult": _false_positive_phones(tuning, threshold),
        },
        "affricate_accounting": _affricate_accounting(
            development + tuning, threshold
        ),
    }
    result["child_diagnostics"] = {
        split: {
            **partition_metrics(
                predictions_at_threshold(_partition(rows, split, "child"), threshold)
            ),
            "adult_operating_point_only_not_selected_for_children": True,
        }
        for split in ("development", "threshold_tuning")
    }
    private = {
        "candidate_id": candidate_id,
        "threshold_grid": search["records"],
        "participants": {
            "development_adult": participant_metrics(
                predictions_at_threshold(development, threshold)
            ),
            "threshold_tuning_adult": participant_metrics(
                predictions_at_threshold(tuning, threshold)
            ),
        },
    }
    return result, private


def run_scoring(output_root=None, version=ACTIVE_COMPARISON_VERSION):
    global _ACTIVE_VERSION
    _ACTIVE_VERSION = version
    _clip_records.cache_clear()
    version_profile = comparison_profile(version)
    if output_root is None:
        output_root = default_output(version)
    contract = verify_frozen_inputs(version=version)
    assert_valid_comparison_contract(contract)
    relations = load_relation_rows(version=version)
    manifest = load_expected_manifest(version=version)
    references = {
        record["safe_id"]: record
        for record in _load_json(reference_path())["records"]
    }

    output_root = Path(output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    scored_path = output_root / "comparison-scored-evidence.json"
    if scored_path.exists():
        raise ComparisonError("scored comparison evidence already exists")

    lane_rows = {
        "sfgop_af": sfgop_rows(relations, manifest, "gop_af_s"),
        "sfgop_af_sd": sfgop_rows(relations, manifest, "gop_af_sd"),
        "powsm_free_phone_relation": free_phone_rows(
            "powsm",
            "powsm-comparison-process.json",
            version_profile["expected_only_clip_count"]
            + version_profile["secondary_clip_count"],
            relations,
            manifest,
        ),
        "wav2vec2_commonphone_free_phone_relation": free_phone_rows(
            "commonphone",
            "commonphone-comparison-process.json",
            version_profile["expected_only_clip_count"],
            relations,
            manifest,
        ),
    }
    azure_failures = {}
    for candidate_id in AZURE_LOCALE_BY_CANDIDATE:
        rows, failures = azure_rows(candidate_id, relations, manifest, references)
        lane_rows[candidate_id] = rows
        azure_failures[candidate_id] = failures

    candidates = []
    private_details = []
    for candidate_id in sorted(CANDIDATE_PROFILES):
        profile = CANDIDATE_PROFILES[candidate_id]
        rows = lane_rows[candidate_id]
        if profile["selection_eligible"]:
            summary, private = score_candidate(candidate_id, rows, True)
        else:
            # A supporting-only lane is described, never gated. Its numbers can
            # inform a human reading the report; they can never select anything.
            summary, private = score_candidate(candidate_id, rows, False)
            summary["gates_evaluated"] = False
            summary["any_operating_point_passes_both_partitions"] = None
            if summary["reported_operating_point"]:
                summary["reported_operating_point"]["is_a_selection"] = False
                summary["reported_operating_point"]["both_partitions_pass"] = None
                summary["reported_operating_point"]["development"].pop(
                    "selection_gates", None
                )
                summary["reported_operating_point"]["threshold_tuning"].pop(
                    "selection_gates", None
                )
        if candidate_id in azure_failures:
            summary["provider_failures"] = azure_failures[candidate_id]
            summary["provider_reference_agreement"] = azure_reference_agreement(
                AZURE_LOCALE_BY_CANDIDATE[candidate_id], manifest, references
            )
        candidates.append(summary)
        if private is not None:
            private_details.append(private)

    document = {
        "schema_version": "1.0.0",
        "evidence_id": "speech_sound_frozen_comparison_scored_private_v1",
        "checkpoint": version_profile["checkpoint"],
        "comparison_contract_sha256": file_sha256(version_profile["contract_path"]),
        "relation_evidence_sha256": contract["frozen_inputs"][
            "relation_evidence_sha256"
        ],
        "held_out_evaluation": False,
        "child_rows_used_for_selection_or_thresholds": False,
        "candidates": candidates,
        "private_details": private_details,
    }
    scored_path.write_bytes(canonical_json_bytes(document))
    return scored_path, document


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=None)
    parser.add_argument("--comparison-version", default=ACTIVE_COMPARISON_VERSION)
    arguments = parser.parse_args()
    path, document = run_scoring(
        arguments.output_root, version=arguments.comparison_version
    )
    print(f"Private scored evidence: {path.relative_to(REPOSITORY_ROOT)}")
    for candidate in document["candidates"]:
        point = candidate["reported_operating_point"]
        if point is None:
            print(f"{candidate['candidate_id']}: no operating point")
            continue
        development = point["development"]
        tuning = point["threshold_tuning"]
        print(
            f"{candidate['candidate_id']}: "
            f"passes={candidate['any_operating_point_passes_both_partitions']} "
            f"checks={point['gate_checks_passed_of_ten']}/10 "
            f"dev precision={development['precision']['value']} "
            f"recall={development['recall']['value']} "
            f"tuning precision={tuning['precision']['value']} "
            f"recall={tuning['recall']['value']}"
        )


if __name__ == "__main__":
    main()
