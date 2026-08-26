"""Write the committed aggregate report for checkpoint 22E4.

The private scored evidence holds thresholds grids, participant rows and
provider responses. None of that is committed. This step keeps aggregates,
denominators, coverage, failures, cost, repeatability and limitations, and drops
everything that could identify a clip, a participant or a raw provider payload.

    python3 -m speech_sound_patterns.summarize_comparison
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .comparison import (
    ACTIVE_COMPARISON_VERSION,
    CANDIDATE_PROFILES,
    DEFAULT_COMPARISON_VERSION,
    FROZEN_SELECTION_GATES,
    ComparisonError,
    assert_valid_comparison_contract,
    comparison_profile,
)
from .feasibility import REPOSITORY_ROOT, canonical_json_bytes, file_sha256


# Which frozen comparison this process is summarising. Set by ``build_report``.
_ACTIVE_VERSION = DEFAULT_COMPARISON_VERSION


def _profile():
    return comparison_profile(_ACTIVE_VERSION)


def evidence_root():
    return _profile()["private_root"] / "evidence"


def default_scored_path(version=ACTIVE_COMPARISON_VERSION):
    return (
        comparison_profile(version)["private_root"]
        / "evidence"
        / "scoring"
        / "comparison-scored-evidence.json"
    )


# What the Azure lane actually cost, per comparison. The two runs were billed
# differently and the difference is large enough to matter: 240 clips fitted
# inside the free tier's five audio hours a month, and 2,040 clips did not, so
# the owner moved the Australia East resource to standard S0 before the powered
# run. Recording one string for both would have made the checkpoint 22E4B cost
# look like nothing.
AZURE_MONETARY_COST = {
    "1.0.0": (
        "no charge observed on the existing Free F0 Australia East "
        "resource for this volume"
    ),
    "1.1.0": (
        "about A$14 on the Australia East resource, which the owner moved from "
        "the free F0 tier to standard S0 before this run because F0 allows five "
        "audio hours a month and this run needed 9.72; billed at the A$1.4492 "
        "standard rate against A$289.83 of remaining account credit"
    ),
}

CHECKPOINT_22E4_LIMITATIONS = [
    "SpeechOcean762 is Mandarin first language read speech assessed against "
    "American English. It does not represent Australian or world English, and "
    "nothing measured here transfers to Australian speakers.",
    "Adult positive relations are concentrated in four of eight development "
    "participants and one of four tuning participants, so every precision and "
    "recall estimate rests on a small number of speakers.",
    "The threshold tuning partition holds 34 positive opportunities in total. "
    "At the operating points reported here a candidate raises roughly fifteen "
    "concerns on it, so one additional false concern moves its precision by "
    "about five points. A gate outcome on that partition is therefore fragile, "
    "and the difference between a near miss and a pass is not evidence of a "
    "real difference in quality.",
    "This checkpoint failed in the mirror image of checkpoint 22D. There the "
    "strongest candidate passed every threshold tuning gate and missed a "
    "development gate; here the strongest candidate passes every development "
    "gate and misses the tuning precision gates. Two failures in opposite "
    "directions around the same lines indicate performance sitting close to the "
    "gates rather than a single fixable defect, and neither result licenses "
    "moving a gate.",
    "Children have too few positive consensus relations, two in development and "
    "four in tuning, to support any child estimate. Child results are reported "
    "as diagnostics at the adult operating point and were never used to choose "
    "anything.",
    "No external lane can supply Australian variety exact relation evidence. "
    "Azure en-AU emits every phone name as an empty string and Azure en-US "
    "names phones only against a General American target.",
    "The Australian Common Voice set may not be transmitted to any external "
    "lane, so external Australian robustness evidence does not exist and is "
    "reported as missing rather than estimated.",
    "The frozen reference expects one tie barred token for an affricate. A free "
    "phone lane that emits the two component phones separately therefore "
    "produces a systematic concern at every affricate target. The affected "
    "count is reported per candidate so the cause is visible rather than mixed "
    "into a general accuracy claim.",
    "A provider score is not a measurement of a produced phone. An accuracy "
    "score can fall for reasons that have nothing to do with the speaker's "
    "articulation, including recording conditions and lexicon mismatch.",
    "Agreement between two candidates is not confirmation. POWSM and the "
    "supporting CommonPhone model both derive from automatically labelled "
    "training data, and neither carries human phone truth.",
    "The held-out participants remain sealed until checkpoint 22H.",
    "No result in this report establishes scientific validity, product "
    "readiness, Australian performance, coaching value or any clinical "
    "conclusion.",
]

# Checkpoint 22E4B replaces the sample size limitations with what the powered
# sample can and cannot fix. Everything that was true of the method rather than
# of the sample is carried over unchanged.
CHECKPOINT_22E4B_LIMITATIONS = [
    "SpeechOcean762 is Mandarin first language read speech assessed against "
    "American English. It does not represent Australian or world English, and "
    "nothing measured here transfers to Australian speakers. A larger sample "
    "makes this estimate more precise; it does not make it more general.",
    "This is every non held out adult in the corpus, so the participant sample "
    "cannot be enlarged again without unsealing the held-out set, which is "
    "reserved for checkpoint 22H. A further disagreement with these numbers "
    "needs a different corpus, not a bigger slice of this one.",
    "A larger sample narrows a confidence interval. It cannot remove a bias "
    "shared by every clip, and it cannot make the truth itself sharper: Fleiss "
    "kappa across the five reviewers is 0.566 for development adults and 0.520 "
    "for tuning adults, so a portion of every error measured here is reviewer "
    "disagreement rather than candidate error.",
    "The child sample was deliberately held at its checkpoint 22D size, because "
    "the frozen gates are adult only and a larger child sample could not change "
    "any pass or fail. Child results therefore remain as weakly supported as "
    "they were at checkpoint 22E4 and are reported as diagnostics at the adult "
    "operating point only.",
    "No external lane can supply Australian variety exact relation evidence. "
    "Azure en-AU emits every phone name as an empty string and Azure en-US "
    "names phones only against a General American target.",
    "The Australian Common Voice set may not be transmitted to any external "
    "lane, so external Australian robustness evidence does not exist and is "
    "reported as missing rather than estimated.",
    "The frozen reference expects one tie barred token for an affricate. A free "
    "phone lane that emits the two component phones separately therefore "
    "produces a systematic concern at every affricate target. The affected "
    "count is reported per candidate so the cause is visible rather than mixed "
    "into a general accuracy claim.",
    "A provider score is not a measurement of a produced phone. An accuracy "
    "score can fall for reasons that have nothing to do with the speaker's "
    "articulation, including recording conditions and lexicon mismatch.",
    "Agreement between two candidates is not confirmation. POWSM and the "
    "supporting CommonPhone model both derive from automatically labelled "
    "training data, and neither carries human phone truth.",
    "The held-out participants remain sealed until checkpoint 22H.",
    "No result in this report establishes scientific validity, product "
    "readiness, Australian performance, coaching value or any clinical "
    "conclusion.",
]

LIMITATIONS_BY_VERSION = {
    "1.0.0": CHECKPOINT_22E4_LIMITATIONS,
    "1.1.0": CHECKPOINT_22E4B_LIMITATIONS,
}


def _load_json(path):
    path = Path(path)
    if not path.is_file():
        raise ComparisonError(f"comparison evidence is missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _lane_process(directory, filename):
    return _load_json(evidence_root() / directory / filename)


def _runtime_records():
    sfgop = _lane_process("sfgop", "sfgop-comparison-process.json")
    powsm = _lane_process("powsm", "powsm-comparison-process.json")
    commonphone = _lane_process(
        "commonphone", "commonphone-comparison-process.json"
    )
    azure = _lane_process("azure", "azure-comparison-process.json")
    return [
        {
            "lane_id": "segmentation_free_gop",
            "kind": "local_method",
            "clips": sfgop["execution"]["clip_count"],
            "same_input_repeats": sfgop["execution"]["same_input_repeats"],
            "all_repeats_exact": sfgop["execution"]["all_repeats_exact"],
            "real_time_factor_all_repeats": sfgop["real_time_factor_all_repeats"],
            "peak_maxrss_bytes": sfgop["peak_maxrss_bytes"],
            "worst_forward_backward_abs_diff": sfgop[
                "worst_forward_backward_abs_diff"
            ],
            "monetary_cost": "none, runs on this machine",
            "network_access": sfgop["execution"]["network_access"],
        },
        {
            "lane_id": "powsm",
            "kind": "local_model",
            "clips": powsm["execution"]["clip_count"],
            "gate_eligible_clips": powsm["execution"]["gate_eligible_clips"],
            "same_input_repeats": powsm["execution"]["same_input_repeats"],
            "all_repeats_exact": powsm["execution"]["all_repeats_exact"],
            "real_time_factor_all_repeats": powsm["real_time_factor_all_repeats"],
            "peak_maxrss_bytes": powsm["peak_maxrss_bytes"],
            "monetary_cost": "none, runs on this machine",
            "network_access": powsm["execution"]["network_access"],
        },
        {
            "lane_id": "wav2vec2_commonphone",
            "kind": "local_model",
            "role": "supporting_only",
            "clips": commonphone["execution"]["clip_count"],
            "same_input_repeats": commonphone["execution"]["same_input_repeats"],
            "all_repeats_exact": commonphone["execution"]["all_repeats_exact"],
            "real_time_factor_all_repeats": commonphone[
                "real_time_factor_all_repeats"
            ],
            "peak_maxrss_bytes": commonphone["peak_maxrss_bytes"],
            "monetary_cost": "none, runs on this machine",
            "network_access": commonphone["execution"]["network_access"],
        },
        {
            "lane_id": "azure_speech",
            "kind": "external_api",
            "region": azure["region"],
            "clips_transmitted": azure["transmission"]["clip_count"],
            "child_clips_transmitted": azure["transmission"][
                "child_clips_transmitted"
            ],
            "held_out_clips_transmitted": azure["transmission"][
                "held_out_clips_transmitted"
            ],
            "owner_audio_transmitted": azure["transmission"][
                "owner_audio_transmitted"
            ],
            "locales_pooled": azure["locales_pooled"],
            "by_locale": azure["by_locale"],
            "monetary_cost": AZURE_MONETARY_COST[_ACTIVE_VERSION],
        },
    ]


def _secondary_source_evidence():
    powsm = _lane_process("powsm", "powsm-comparison-process.json")
    return {
        "role": (
            "availability, repeatability and system disagreement only; these "
            "sources carry no expert phone relation truth and can never enter a "
            "selection gate"
        ),
        "by_source_and_role": [
            item
            for item in powsm["by_source_and_role"]
            if item["evidence_role"] != "selection_gate_eligible"
        ],
        "australian_external_evidence": (
            "not available; the Australian Common Voice manifest blocks provider "
            "transfer, so no external lane was run on Australian speech"
        ),
        "segmentation_free_gop_on_secondary_sources": (
            "not run; that lane needs an expected phone sequence, and building "
            "one for these sources would require a pronunciation lexicon this "
            "project has not yet acquired. Checkpoint 22F is where that "
            "reference is created."
        ),
    }


def _candidate_summary(candidate, contract):
    declared = next(
        item
        for item in contract["candidates"]
        if item["candidate_id"] == candidate["candidate_id"]
    )
    summary = {
        "candidate_id": candidate["candidate_id"],
        "lane_id": declared["lane_id"],
        "evidence_class": declared["evidence_class"],
        "decision_rule": candidate["decision_rule"],
        "exact_relation_capable": declared["exact_relation_capable"],
        "selection_eligible": candidate["selection_eligible"],
        "evidence_available": candidate["evidence_available"],
        "no_evidence_reason": candidate["no_evidence_reason"],
        "candidate_threshold_count": candidate["candidate_threshold_count"],
        "development_average_precision": candidate["development_average_precision"],
        "coverage": candidate["coverage"],
        "any_operating_point_passes_both_partitions": candidate[
            "any_operating_point_passes_both_partitions"
        ],
        "reported_operating_point": candidate["reported_operating_point"],
        "child_diagnostics": candidate.get("child_diagnostics"),
    }
    if "locale" in declared:
        summary["locale"] = declared["locale"]
    if "locale_limitation" in declared:
        summary["locale_limitation"] = declared["locale_limitation"]
    if "gates_evaluated" in candidate:
        summary["gates_evaluated"] = candidate["gates_evaluated"]
    if "provider_failures" in candidate:
        summary["provider_failures"] = candidate["provider_failures"]
    if "provider_reference_agreement" in candidate:
        summary["provider_reference_agreement"] = candidate[
            "provider_reference_agreement"
        ]
    if "non_independent_sources" in declared:
        summary["non_independent_sources"] = declared["non_independent_sources"]
    return summary


def _opportunity_counts():
    """Count scorable and positive opportunities per partition.

    These are properties of the truth, not of any candidate, and the powered
    sample changes both. Reporting them makes the statistical claim checkable.
    """
    document = _load_json(_profile()["relation_path"])
    counts = {}
    for row in document["target_rows"]:
        key = f"{row['project_split']}_{row['age_stratum']}"
        record = counts.setdefault(key, {"scorable": 0, "positive": 0})
        if row["truth"] == "unscorable":
            continue
        record["scorable"] += 1
        if row["truth"] == "positive":
            record["positive"] += 1
    return counts


def _powered_sample_limitations(counts):
    """Limitations that state the real powered denominators."""
    development = counts.get("development_adult", {})
    tuning = counts.get("threshold_tuning_adult", {})
    child_development = counts.get("development_child", {})
    child_tuning = counts.get("threshold_tuning_child", {})
    return [
        "The threshold tuning partition holds "
        f"{tuning.get('positive', 0)} positive opportunities out of "
        f"{tuning.get('scorable', 0)} scorable ones, and development holds "
        f"{development.get('positive', 0)} out of "
        f"{development.get('scorable', 0)}. At checkpoint 22E4 the same "
        "partitions held 34 and about 135. A single extra false concern no "
        "longer moves a precision estimate by several points, which is the "
        "specific weakness this replication was run to remove.",
        "Children contribute "
        f"{child_development.get('positive', 0)} positive development "
        f"opportunities and {child_tuning.get('positive', 0)} positive tuning "
        "opportunities. That is still far too few to support any child "
        "estimate, and no child row entered a gate or a threshold.",
    ]


def _checkpoint_22e4_comparison(candidates):
    """State plainly what the powered sample did to the earlier near miss."""
    earlier = _load_json(
        comparison_profile("1.0.0")["report_path"]
    )
    earlier_by_id = {
        candidate["candidate_id"]: candidate for candidate in earlier["candidates"]
    }
    rows = []
    for candidate in candidates:
        before = earlier_by_id.get(candidate["candidate_id"])
        if before is None:
            continue
        before_point = before.get("reported_operating_point") or {}
        after_point = candidate.get("reported_operating_point") or {}
        rows.append(
            {
                "candidate_id": candidate["candidate_id"],
                "checkpoint_22e4_gate_checks_passed_of_ten": before_point.get(
                    "gate_checks_passed_of_ten"
                ),
                "checkpoint_22e4b_gate_checks_passed_of_ten": after_point.get(
                    "gate_checks_passed_of_ten"
                ),
                "checkpoint_22e4_passed_both_partitions": before.get(
                    "any_operating_point_passes_both_partitions"
                ),
                "checkpoint_22e4b_passed_both_partitions": candidate.get(
                    "any_operating_point_passes_both_partitions"
                ),
                "checkpoint_22e4_evidence_available": before.get(
                    "evidence_available"
                ),
                "checkpoint_22e4b_evidence_available": candidate.get(
                    "evidence_available"
                ),
            }
        )
    return {
        "checkpoint_22e4_decision": earlier["decision"]["decision"],
        "checkpoint_22e4_report_sha256": file_sha256(
            comparison_profile("1.0.0")["report_path"]
        ),
        "per_candidate": rows,
    }


def build_report(scored_path=None, version=ACTIVE_COMPARISON_VERSION):
    global _ACTIVE_VERSION
    _ACTIVE_VERSION = version
    profile = comparison_profile(version)
    if scored_path is None:
        scored_path = default_scored_path(version)
    contract = assert_valid_comparison_contract(version=version)
    scored = _load_json(scored_path)
    if scored.get("held_out_evaluation") is not False:
        raise ComparisonError("the scored evidence claims held-out evaluation")
    if scored.get("child_rows_used_for_selection_or_thresholds") is not False:
        raise ComparisonError("the scored evidence used child rows for selection")

    candidates = [
        _candidate_summary(candidate, contract)
        for candidate in scored["candidates"]
    ]
    passing = [
        candidate["candidate_id"]
        for candidate in candidates
        if candidate["selection_eligible"]
        and candidate["any_operating_point_passes_both_partitions"]
    ]
    decision = {
        "decision": (
            "candidates_passed_every_unchanged_gate"
            if passing
            else "no_selection"
        ),
        "candidates_passing_every_unchanged_gate": sorted(passing),
        "selection_recorded_in_this_checkpoint": False,
        "selection_recorded_at": "22E5",
        "no_selection_is_a_valid_completed_outcome": True,
        "gates_changed_in_this_checkpoint": False,
        "paid_provider_evaluated": True,
        "australian_variety_exact_relation_evidence_available": False,
        "children_supported": False,
        "insertions_supported": False,
    }

    counts = _opportunity_counts()
    limitations = list(LIMITATIONS_BY_VERSION[version])
    if version != "1.0.0":
        limitations[2:2] = _powered_sample_limitations(counts)
        decision["checkpoint_22e4_comparison"] = _checkpoint_22e4_comparison(
            candidates
        )
        decision["the_checkpoint_22e4_near_miss_survived_the_larger_sample"] = bool(
            passing
        )

    report = {
        "schema_version": version,
        "report_id": "speech_sound_frozen_comparison",
        "report_version": version,
        "checkpoint": profile["checkpoint"],
        "status": "frozen_comparison_complete_release_locked",
        "purpose": (
            "Record what every eligible checkpoint 22E lane did on the same "
            "frozen participant-exclusive clips under the unchanged checkpoint "
            "22D selection gates. This report supports a developer review "
            "candidate or a documented no-selection, and nothing else."
        ),
        "comparison_contract_sha256": file_sha256(profile["contract_path"]),
        "sample": {
            "clips": profile["expected_only_clip_count"],
            "gate_population": "source_adults_only",
            "development_adult_participants": contract["input_policy"].get(
                "development_adult_participants", 8
            ),
            "threshold_tuning_adult_participants": contract["input_policy"].get(
                "threshold_tuning_adult_participants", 4
            ),
            "development_adult_scorable_opportunities": profile[
                "adult_scorable_counts"
            ]["development"],
            "threshold_tuning_adult_scorable_opportunities": profile[
                "adult_scorable_counts"
            ]["threshold_tuning"],
            "held_out_participants": 0,
            "expert_outcomes_read_by_candidate_runners": False,
            "same_input_repeats": 2,
        },
        "selection_gates": {
            **FROZEN_SELECTION_GATES,
            "development_and_tuning_both_required": True,
            "inherited_unchanged_from_checkpoint_22d": True,
        },
        "candidates": candidates,
        "baseline_comparison": {
            **contract["baseline_reference"],
            "note": (
                "the checkpoint 22D local baseline is carried from its committed "
                "report for incremental value only and was not rerun here"
            ),
        },
        "secondary_source_evidence": _secondary_source_evidence(),
        "runtime_and_cost": _runtime_records(),
        "excluded_lanes": contract["excluded_lanes"],
        "external_transmission": contract["external_transmission_policy"],
        "decision": decision,
        "private_evidence": {
            "scored_evidence_sha256": file_sha256(scored_path),
            "raw_or_row_level_evidence_committed": False,
            "provider_responses_committed": False,
        },
        "limitations": limitations,
        "release_boundaries": contract["release_boundaries"],
        "next_checkpoint": (
            "22E5_selection_and_rejection_record_after_owner_commit"
        ),
    }
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scored", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--comparison-version", default=ACTIVE_COMPARISON_VERSION)
    arguments = parser.parse_args()
    version = arguments.comparison_version
    if arguments.output is None:
        arguments.output = comparison_profile(version)["report_path"]
    report = build_report(arguments.scored, version=version)
    Path(arguments.output).write_bytes(canonical_json_bytes(report))
    print(
        f"Committed comparison report: "
        f"{Path(arguments.output).resolve().relative_to(REPOSITORY_ROOT)}"
    )
    print(f"Decision: {report['decision']['decision']}")
    for candidate in report["candidates"]:
        print(
            f"  {candidate['candidate_id']}: passes="
            f"{candidate['any_operating_point_passes_both_partitions']}"
        )


if __name__ == "__main__":
    main()
