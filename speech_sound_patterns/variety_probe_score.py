"""Checkpoint 22E8 scoring of the reference variety probe.

Turns per clip GOP evidence into the one comparison this checkpoint exists to
make: how often each speaker group is flagged, under each reference, per
consonant.

Three choices here are methodological rather than cosmetic, and all three were
frozen in the contract before any speaker was scored:

- **Rates are per speaker, then averaged.** A contributor who recorded more
  clips cannot pull a group's rate toward their own voice.
- **Several thresholds are reported, not one.** No operating point has ever
  passed a gate in this project, so quoting one would imply a choice nobody has
  earned. A real differential holds across the range; one that appears at a
  single threshold is an artefact.
- **Everything is reported twice**, once complete and once with the aligner's
  conditioned palatal series removed. That series is chosen by the following
  vowel, so a purely vocalic difference between varieties can otherwise surface
  as a consonant difference.

These are native speakers reading known text, so a flag is presumed a false
concern. Nothing here is an accuracy figure and nothing here selects anything.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from .variety_probe import PRIVATE_ROOT, REPORTING_GROUPS, load_contract
from .variety_reference import MAPPING_AMENDMENTS, MAPPING_VERSION

# The published bundle is the default because it is the copy anybody can run.
# It carries the same scores as the private evidence with contributor
# identifiers replaced, and the report it produces is byte identical, which is
# asserted in release/redistribution-decision-v1.0.0.json rather than assumed.
# The private root stays available through --evidence-root.
PUBLISHED_EVIDENCE_ROOT = (
    Path(__file__).resolve().parent / "variety-probe-evidence"
)
PRIVATE_EVIDENCE_ROOT = PRIVATE_ROOT / "variety-probe" / "evidence"
EVIDENCE_ROOT = PUBLISHED_EVIDENCE_ROOT

# Chosen by the following vowel rather than by the speaker, so a vowel
# difference between varieties can masquerade as a consonant difference.
# Retired at mapping version 1.2.0 and kept only so the superseded report stays
# readable. This was an attempt to subtract the conditioned palatal series from
# a result it should never have entered. It excluded four of the five and missed
# ç, which was 612 opportunities at 99.8 percent. The primary analysis now does
# the job properly, because the series is normalised to broad phonemes before a
# target is ever selected, so filtering it here would filter nothing.
CONDITIONED_PALATALS = frozenset({"c", "cʰ", "ɟ", "ʎ", "ɲ"})


class VarietyScoreError(RuntimeError):
    """Raised when the probe evidence cannot support the comparison."""


def load_evidence(evidence_root=EVIDENCE_ROOT):
    records = []
    for path in sorted(Path(evidence_root).glob("*/*.json")):
        if path.name == "bundle-manifest.json":
            continue
        records.append(json.loads(path.read_text(encoding="utf-8")))
    if not records:
        raise VarietyScoreError("no probe evidence has been produced")
    return records


def _reporting_group(source_id):
    for name, members in REPORTING_GROUPS.items():
        if source_id in members:
            return name
    raise VarietyScoreError(f"{source_id} belongs to no reporting group")


def _speaker_rates(records, reference, threshold, exclude=frozenset()):
    """Return per speaker flag rates, keyed by reporting group."""
    totals = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for record in records:
        group = _reporting_group(record["source_id"])
        person = record["participant"]
        for target in record["references"][reference]["targets"]:
            if target["token"] in exclude:
                continue
            counter = totals[group][person]
            counter[1] += 1
            if target["gop_af_sd"] < threshold:
                counter[0] += 1
    return {
        group: [
            flagged / opportunities
            for flagged, opportunities in speakers.values()
            if opportunities
        ]
        for group, speakers in totals.items()
    }


def _mean(values):
    return sum(values) / len(values) if values else None


def _consonant_rates(records, reference, threshold):
    """Return per consonant flag rates for every reporting group."""
    totals = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for record in records:
        group = _reporting_group(record["source_id"])
        for target in record["references"][reference]["targets"]:
            counter = totals[group][target["token"]]
            counter[1] += 1
            if target["gop_af_sd"] < threshold:
                counter[0] += 1
    return {
        group: {
            token: {
                "opportunities": opportunities,
                "flagged": flagged,
                "rate": round(flagged / opportunities, 6),
            }
            for token, (flagged, opportunities) in sorted(tokens.items())
            if opportunities
        }
        for group, tokens in totals.items()
    }


def build_report(records=None, contract=None, uncertainty=None):
    """Assemble the whole comparison, including its own falsification check.

    The uncertainty block is required. Item R2 established that not one of the
    five pre registered group level comparisons is distinguishable from zero,
    so a report of point estimates alone would now be describing noise without
    saying so.
    """
    contract = contract or load_contract()
    if uncertainty is None:
        raise VarietyScoreError(
            "a report may no longer be built without its uncertainty block; "
            "build it with speech_sound_patterns.variety_probe_uncertainty"
        )
    records = records if records is not None else load_evidence()
    thresholds = contract["scoring"]["reported_thresholds"]
    analyses = {}
    for label, exclude in (("complete", frozenset()),):
        by_threshold = {}
        for threshold in thresholds:
            entry = {}
            for reference in ("american", "british"):
                rates = _speaker_rates(records, reference, threshold, exclude)
                entry[reference] = {
                    group: {
                        "speakers": len(values),
                        "mean_speaker_flag_rate": round(_mean(values), 6),
                    }
                    for group, values in sorted(rates.items())
                }
            for group in ("australian", "british", "american"):
                american_reference = entry["american"][group]["mean_speaker_flag_rate"]
                british_reference = entry["british"][group]["mean_speaker_flag_rate"]
                entry.setdefault("change_under_the_repair", {})[group] = round(
                    british_reference - american_reference, 6
                )
            for reference in ("american", "british"):
                control = entry[reference]["american"]["mean_speaker_flag_rate"]
                entry.setdefault("differential_against_the_american_group", {})[
                    reference
                ] = {
                    group: round(
                        entry[reference][group]["mean_speaker_flag_rate"] - control, 6
                    )
                    for group in ("australian", "british")
                }
            by_threshold[str(threshold)] = entry
        analyses[label] = by_threshold
    consonants = {
        reference: _consonant_rates(records, reference, -1.0)
        for reference in ("american", "british")
    }
    return {
        "schema_version": "1.2.0",
        "report_id": "speech_sound_patterns_reference_variety_probe_v1",
        "checkpoint": "22E8",
        "contract_id": contract["probe_id"],
        "phone_mapping_version": MAPPING_VERSION,
        "phone_mapping_amendments": MAPPING_AMENDMENTS,
        "clips_scored": len(records),
        "speakers": len({(r["source_id"], r["participant"]) for r in records}),
        "analyses": analyses,
        "per_consonant_rates_at_threshold_minus_one": consonants,
        "predictions": _evaluate_predictions(analyses["complete"], thresholds),
        "uncertainty": uncertainty,
        "findings": _findings(analyses["complete"], consonants, uncertainty),
        "declared_confounds": contract["declared_confounds"],
        "what_this_cannot_establish": contract["what_this_cannot_establish"],
        "release_boundaries": contract["release_boundaries"],
    }


def _rate(consonants, reference, group, token, field="rate"):
    entry = consonants[reference].get(group, {}).get(token)
    return entry[field] if entry else None


def _family_member(uncertainty, family, name):
    """One test's row out of a frozen family, by name."""
    for row in uncertainty["families"][family]["members"]:
        if row["name"] == name:
            return row
    raise VarietyScoreError(f"{name} is not a member of family {family}")


def _findings(by_threshold, consonants, uncertainty):
    """State what the numbers support, including where they refute the brief."""
    entry = by_threshold["-1.0"]
    australian = entry["differential_against_the_american_group"]["american"][
        "australian"
    ]
    british = entry["differential_against_the_american_group"]["american"]["british"]
    british_repaired = entry["differential_against_the_american_group"]["british"][
        "british"
    ]
    opportunities = {
        group: {
            reference: _rate(consonants, reference, group, "ɹ", "opportunities")
            for reference in ("american", "british")
        }
        for group in ("australian", "british", "american")
    }
    return {
        "group_level_prediction_failed_for_australian_speakers": {
            "statement": "At group level the American reference did not flag Australian speakers more often than American speakers. The differential is negative at every reported threshold under mapping versions 1.1.0 and 1.2.0 alike, so the checkpoint's central prediction is recorded as wrong rather than reinterpreted. Correcting the phone mapping made it slightly more negative, not less.",
            "australian_differential_under_the_american_reference": australian,
        },
        "group_level_prediction_held_for_british_speakers": {
            "statement": "British speakers were flagged more often than the American control under the American reference, and the repaired reference roughly halved that gap. This is the informative middle case behaving as predicted, because it is the variety the repaired reference actually describes.",
            "british_differential_under_the_american_reference": british,
            "british_differential_under_the_british_reference": british_repaired,
        },
        "the_rhotic_effect_was_a_segmentation_artifact": {
            "statement": "Mapping version 1.1.0 reported that Australian speakers were flagged about three points more often than the American control on the rhotic, and called it the checkpoint's central positive finding. That effect does not exist. It was produced by pre-consonantal coda r, which the Montreal Forced Aligner writes as its own segment and which the frozen model carries inside a combined vowel token, so the expected standalone segment owned no frames and was flagged 96.6 percent of the time in the American control, the Australian group and the British group alike, to three decimal places. The apparent accent effect was that identical impossible rate multiplied by how often each group's prompts happened to contain the context. With post-vocalic r merged into the model's own token, the remaining onset rhotic differential is effectively zero.",
            "rhotic_australian_minus_american_under_the_american_reference": round(
                _rate(consonants, "american", "australian", "ɹ")
                - _rate(consonants, "american", "american", "ɹ"),
                6,
            ),
            "superseded_value_under_mapping_1_1_0": 0.030039,
            "what_the_rhotic_target_now_means": "onset r only. Post-vocalic r is not scored under either reference, because the reference and the model disagree about whether it is a segment at all. Rhoticity, which is the sharpest Australian and American consonantal difference, is therefore not measurable by this method and no claim about it is made here.",
        },
        "the_t_effect_survives_the_correction": {
            "statement": "The second consonant the superseded report named does survive. Under the American reference Australian speakers are flagged more often than the American control on t, and the gap nearly disappears under the repaired reference. It is now the largest single per consonant differential in the comparison. It is also not clearly separable from the noise floor: v runs almost as far in the opposite direction, with Australians flagged less often than the control, and no uncertainty has been computed for either. No claim about t may be made until speaker clustered intervals and a correction for testing many consonants at once exist.",
            "t_australian_minus_american_under_the_american_reference": round(
                _rate(consonants, "american", "australian", "t")
                - _rate(consonants, "american", "american", "t"),
                6,
            ),
            "t_australian_minus_american_under_the_british_reference": round(
                _rate(consonants, "british", "australian", "t")
                - _rate(consonants, "british", "american", "t"),
                6,
            ),
            "largest_opposite_direction_differential": {
                "consonant": "v",
                "australian_minus_american_under_the_american_reference": round(
                    _rate(consonants, "american", "australian", "v")
                    - _rate(consonants, "american", "american", "v"),
                    6,
                ),
            },
            "uncertainty_state": "computed_at_item_R2",
            "see": "the_t_differential_does_not_survive_correction",
        },
        "the_reference_swap_no_longer_moves_the_control_group": {
            "statement": "Mapping version 1.1.0 reported that the repaired reference lowered the flag rate in every group including the American control it should have left alone, and concluded that the repair worked by declining to score rather than by fitting better. That conclusion was itself an artifact. The control moved because post-vocalic r was scored and always failed under the American reference, while a non-rhotic reference stopped creating the opportunity at all. With that segment excluded under both references the asymmetry is gone, the control now stays approximately in place, and the two non-American groups fall slightly. That is the direction the contract predicted before the run. The movements are around a fifth of a percentage point, which is far too small to interpret without uncertainty, and none is claimed.",
            "control_change_under_the_repair": entry["change_under_the_repair"]["american"],
            "australian_change_under_the_repair": entry["change_under_the_repair"]["australian"],
            "british_change_under_the_repair": entry["change_under_the_repair"]["british"],
            "superseded_control_change_under_mapping_1_1_0": -0.028563,
            "uncertainty_state": "computed_at_item_R2",
            "what_uncertainty_established": "None of the three movements is distinguishable from zero. Each interval contains it and no permutation test approaches significance, so the sentence above describes a direction the point estimates happened to take and not an established effect.",
            "intervals": {
                group: {
                    key: _family_member(
                        uncertainty,
                        "G_pre_registered_group_level",
                        f"{group}_change_under_the_repair_at_-1.0",
                    )[key]
                    for key in ("point", "ci_low", "ci_high", "p_benjamini_hochberg")
                }
                for group in ("american", "australian", "british")
            },
            "a_second_caveat_established_at_item_R2": "The two references do not create the same scoring opportunities, so this quantity is a change in the whole measurement and not the same segments scoring better. See the_two_references_do_not_create_the_same_opportunities.",
        },
        "most_flags_came_from_phones_the_model_never_produces": {
            "statement": "Across the whole comparison, correcting the phone mapping removed roughly half of every flag the probe produced on native speakers reading known text. Six phone families were responsible: the conditioned palatal series c, ɟ, ɲ, ç and ʎ, each flagged at or within half a point of 100 percent in every group, and the glottal stop. All six exist in the model vocabulary and the model never uses any of them for English. This is the same defect the dark l correction fixed at mapping version 1.1.0, found five more times, plus the separate post-vocalic r segmentation mismatch.",
            "american_control_flag_rate_under_mapping_1_1_0": 0.166381,
            "american_control_flag_rate_under_mapping_1_2_0": entry["american"]["american"]["mean_speaker_flag_rate"],
        },
        "nothing_at_group_level_is_distinguishable_from_zero": {
            "statement": "Every one of the five group level comparisons this probe pre registered before it ran is indistinguishable from zero. All five speaker clustered intervals contain zero, the smallest uncorrected p value across them is nowhere near significance, and none survives correction within the family. The group level portion of this checkpoint has no result. That is the outcome and not a caveat attached to one.",
            "family": "G_pre_registered_group_level",
            "tests": uncertainty["families"]["G_pre_registered_group_level"]["tests"],
            "survivors_uncorrected": uncertainty["families"]["G_pre_registered_group_level"]["survivors_uncorrected"],
            "survivors_benjamini_hochberg": uncertainty["families"]["G_pre_registered_group_level"]["survivors_benjamini_hochberg"],
            "smallest_uncorrected_p_value": min(
                row["p_uncorrected"]
                for row in uncertainty["families"]["G_pre_registered_group_level"]["members"]
            ),
            "minimum_detectable_difference": uncertainty["detectable_effect"]["group_level"]["australian_minus_american"]["minimum_detectable_difference"],
            "why_that_matters": "The Australian differential is about four thousandths and this design could only reliably detect a difference of about fifteen thousandths. A null of this size is a look too small to tell, and not a demonstration that the two groups are scored alike.",
        },
        "the_t_differential_does_not_survive_correction": {
            "statement": "The t differential was the one live per consonant result carried forward from mapping version 1.2.0. It does not survive. It reaches the uncorrected five percent level at exactly one threshold, the one this report designates for per consonant reporting, and at no other: it is not significant at minus a half, minus one and a half or minus two, and at minus three it changes sign. Correcting across the 22 consonants of its declared family removes it under both corrections. Its own size sits below the smallest difference this design could reliably detect for that consonant. Two other consonants in the same family are of comparable size and run the opposite way. The honest reading is that t is a threshold artefact at the noise floor, and no claim rests on it.",
            "family": "A_primary_per_consonant",
            "point": _family_member(uncertainty, "A_primary_per_consonant", "australian_minus_american_t_american_reference_at_-1.0")["point"],
            "ci_low": _family_member(uncertainty, "A_primary_per_consonant", "australian_minus_american_t_american_reference_at_-1.0")["ci_low"],
            "ci_high": _family_member(uncertainty, "A_primary_per_consonant", "australian_minus_american_t_american_reference_at_-1.0")["ci_high"],
            "p_uncorrected": _family_member(uncertainty, "A_primary_per_consonant", "australian_minus_american_t_american_reference_at_-1.0")["p_uncorrected"],
            "p_benjamini_hochberg": _family_member(uncertainty, "A_primary_per_consonant", "australian_minus_american_t_american_reference_at_-1.0")["p_benjamini_hochberg"],
            "p_bonferroni": _family_member(uncertainty, "A_primary_per_consonant", "australian_minus_american_t_american_reference_at_-1.0")["p_bonferroni"],
            "survives_benjamini_hochberg": _family_member(uncertainty, "A_primary_per_consonant", "australian_minus_american_t_american_reference_at_-1.0")["survives_benjamini_hochberg"],
            "minimum_detectable_difference": uncertainty["detectable_effect"]["per_consonant_minimum_detectable_difference"]["australian_minus_american"]["t"],
            "the_family_was_declared_before_this_was_computed": True,
            "a_claim_that_may_not_be_made": "That the gap narrowing under the British reference shows the repaired reference fitting Australian speakers better. The British reference creates about 28 percent more t opportunities than the American one, so the two conditions are not scoring the same segments and the narrowing cannot be attributed to variety.",
        },
        "one_per_consonant_result_survives_correction_and_it_is_british": {
            "statement": "One test in the whole pre declared analysis survives correction, and it is not about Australian speakers. Under the American reference, British speakers are flagged more often than the American control on the voiced dental fricative. It holds its sign and rough size at all five thresholds and under both references, and it survives Benjamini Hochberg and the stricter Bonferroni alike inside its declared family. It is also one of only eight consonants whose opportunity count is stable across the two references, so unlike most of the inventory it is compared like with like. What it is not is evidence about British English. The groups read effectively disjoint prompt sets, 34 shared prompts out of hundreds, so variety is confounded with lexical material, and there is still no expert phone truth to check any of it against. It is a stable, corrected, unexplained differential and it is reported as exactly that.",
            "family": "B_secondary_per_consonant",
            "consonant": "\u00f0",
            "point": _family_member(uncertainty, "B_secondary_per_consonant", "british_minus_american_ð_american_reference_at_-1.0")["point"],
            "ci_low": _family_member(uncertainty, "B_secondary_per_consonant", "british_minus_american_ð_american_reference_at_-1.0")["ci_low"],
            "ci_high": _family_member(uncertainty, "B_secondary_per_consonant", "british_minus_american_ð_american_reference_at_-1.0")["ci_high"],
            "p_uncorrected": _family_member(uncertainty, "B_secondary_per_consonant", "british_minus_american_ð_american_reference_at_-1.0")["p_uncorrected"],
            "p_benjamini_hochberg": _family_member(uncertainty, "B_secondary_per_consonant", "british_minus_american_ð_american_reference_at_-1.0")["p_benjamini_hochberg"],
            "p_bonferroni": _family_member(uncertainty, "B_secondary_per_consonant", "british_minus_american_ð_american_reference_at_-1.0")["p_bonferroni"],
            "what_it_cannot_support": "No accuracy, no selection, no threshold, no gate, and no statement that British speakers pronounce this sound differently. A differential in a flag rate is a property of this measurement and not of the speakers.",
        },
        "the_two_references_do_not_create_the_same_opportunities": {
            "statement": "Swapping the reference variety changes the expected phone sequence, so it also changes which consonants get a scoring opportunity at all. Only 8 of the 25 consonants keep their opportunity count within two percent across the two references. The t target gains about 28 percent under the British reference and the affricates gain about 9 percent, while the rhotic loses. A cross reference comparison for any consonant outside those eight is not comparing like with like, and an apparent effect there may be the changed denominator rather than the speakers. This was not known when version 1.1.0 was written, and it withdraws the support for one sentence in it, that the t gap nearly disappears under the repaired reference.",
            "comparable_across_references": uncertainty["reference_opportunity_parity"]["comparable"],
            "not_comparable_across_references": uncertainty["reference_opportunity_parity"]["not_comparable"],
            "consequence_for_the_sceptical_family": "The largest differentials anywhere in the sensitivity family are on the affricate under the British reference, in both non American groups. They are not promoted to findings. They were not pre declared, and the affricate is one of the consonants whose opportunity count moves between references, so the comparison that produces them is not like with like. They are published in full so that a later pre declared analysis can test them properly.",
        },
        "no_detection_accuracy_claim": "These are native speakers reading known text, so a flag is presumed a false concern. Nothing here establishes that the system correctly detects a genuine Australian mispronunciation, and no accuracy, sensitivity or specificity figure is derivable from it.",
    }


def _evaluate_predictions(by_threshold, thresholds):
    """Check the contract's own predictions, including against itself.

    The contract committed to two directional predictions before running. This
    reports whether each held at every threshold, so a prediction that failed is
    recorded as failed rather than reinterpreted.
    """
    keys = [str(threshold) for threshold in thresholds]
    non_american_flagged_more = {
        key: {
            group: by_threshold[key]["differential_against_the_american_group"][
                "american"
            ][group]
            > 0
            for group in ("australian", "british")
        }
        for key in keys
    }
    gap_narrowed = {
        key: {
            group: abs(
                by_threshold[key]["differential_against_the_american_group"]["british"][
                    group
                ]
            )
            < abs(
                by_threshold[key]["differential_against_the_american_group"]["american"][
                    group
                ]
            )
            for group in ("australian", "british")
        }
        for key in keys
    }
    control_movement = {
        key: by_threshold[key]["change_under_the_repair"]["american"] for key in keys
    }
    return {
        "under_the_american_reference_non_american_groups_are_flagged_more": non_american_flagged_more,
        "held_at_every_threshold": all(
            all(values.values()) for values in non_american_flagged_more.values()
        ),
        "the_repair_narrowed_the_gap": gap_narrowed,
        "narrowed_at_every_threshold": all(
            all(values.values()) for values in gap_narrowed.values()
        ),
        "american_control_change_under_the_repair": control_movement,
        "largest_control_movement": max(
            abs(value) for value in control_movement.values()
        ),
    }


def main():
    """Regenerate the committed report, uncertainty and all."""
    import argparse
    from pathlib import Path

    from .feasibility import REPOSITORY_ROOT, canonical_json_bytes
    from .variety_probe_uncertainty import build_uncertainty_block

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).with_name("variety-probe-v1.2.0.json"),
    )
    parser.add_argument("--resamples", type=int, default=None)
    parser.add_argument("--permutations", type=int, default=None)
    parser.add_argument(
        "--evidence-root",
        type=Path,
        default=EVIDENCE_ROOT,
        help=(
            "per clip evidence to score, default: the published bundle. "
            "There is no fallback: a root that holds no evidence fails."
        ),
    )
    arguments = parser.parse_args()

    records = load_evidence(arguments.evidence_root)
    extra = {"evidence_root": arguments.evidence_root}
    if arguments.resamples:
        extra["resamples"] = arguments.resamples
    if arguments.permutations:
        extra["permutations"] = arguments.permutations
    uncertainty = build_uncertainty_block(**extra)
    report = build_report(records=records, uncertainty=uncertainty)
    print(f"Evidence: {Path(arguments.evidence_root).resolve()}")
    Path(arguments.output).write_bytes(canonical_json_bytes(report))
    written = Path(arguments.output).resolve()
    try:
        shown = written.relative_to(REPOSITORY_ROOT)
    except ValueError:
        shown = written
    print(f"Committed variety probe report: {shown}")
    for name in (
        "G_pre_registered_group_level",
        "A_primary_per_consonant",
        "B_secondary_per_consonant",
    ):
        family = report["uncertainty"]["families"][name]
        print(
            f"  {name}: {family['tests']} tests, "
            f"{len(family['survivors_benjamini_hochberg'])} survive correction"
        )


if __name__ == "__main__":
    main()
