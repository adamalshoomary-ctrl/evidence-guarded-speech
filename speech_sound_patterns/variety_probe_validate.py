"""Fail-closed checks on the checkpoint 22E8 reference variety probe report.

The report's job is to describe a measurement honestly, including where the
measurement refuted the brief that commissioned it. These checks exist so that
honesty cannot be edited out later: a failed prediction cannot be quietly
recorded as held, a release boundary cannot be opened, and the report cannot
start claiming a detection accuracy that the design cannot produce.
"""

from __future__ import annotations

from pathlib import Path

REPORT_PATH = Path(__file__).with_name("variety-probe-v1.2.0.json")
SUPERSEDED_REPORT_PATHS = (
    Path(__file__).with_name("variety-probe-v1.0.0.json"),
    Path(__file__).with_name("variety-probe-v1.1.0.json"),
)
# Retained for callers written before item R2 added a second superseded record.
SUPERSEDED_REPORT_PATH = SUPERSEDED_REPORT_PATHS[0]

UNCERTAINTY_CONTRACT_ID = (
    "speech_sound_patterns_reference_variety_probe_uncertainty_v1"
)
REQUIRED_FAMILIES = (
    "G_pre_registered_group_level",
    "A_primary_per_consonant",
    "B_secondary_per_consonant",
    "S_sceptical_sensitivity",
)
CONTRACT_PATH = Path(__file__).with_name("variety-probe-contract-v1.0.0.json")

REQUIRED_FINDINGS = (
    "group_level_prediction_failed_for_australian_speakers",
    "group_level_prediction_held_for_british_speakers",
    "the_rhotic_effect_was_a_segmentation_artifact",
    "the_t_effect_survives_the_correction",
    "the_reference_swap_no_longer_moves_the_control_group",
    "most_flags_came_from_phones_the_model_never_produces",
    "nothing_at_group_level_is_distinguishable_from_zero",
    "the_t_differential_does_not_survive_correction",
    "one_per_consonant_result_survives_correction_and_it_is_british",
    "the_two_references_do_not_create_the_same_opportunities",
    "no_detection_accuracy_claim",
)

# Findings the superseded mapping version 1.1.0 report carried, which the
# corrected evidence retracts. A report reintroducing one of these is claiming
# an effect the measurement does not contain.
RETRACTED_FINDINGS = (
    "the_group_mean_hid_a_real_per_consonant_effect",
    "the_repair_removes_opportunities_rather_than_improving_fit",
)


def validate_report(document):
    """Return every reason this report may not be trusted as written."""
    errors = []
    if not isinstance(document, dict):
        return ["report must be an object"]
    for field in (
        "schema_version",
        "report_id",
        "checkpoint",
        "contract_id",
        "phone_mapping_version",
        "clips_scored",
        "speakers",
        "analyses",
        "predictions",
        "findings",
        "declared_confounds",
        "release_boundaries",
        "uncertainty",
    ):
        if field not in document:
            errors.append(f"report is missing {field}")
    if errors:
        return errors
    if document["checkpoint"] != "22E8":
        errors.append("report must declare its checkpoint")

    boundaries = document["release_boundaries"]
    for flag, value in boundaries.items():
        if value is not False:
            errors.append(f"release boundary {flag} must stay closed")

    if document["clips_scored"] < 1 or document["speakers"] < 1:
        errors.append("a report with no evidence cannot be valid")

    missing_findings = [
        name for name in REQUIRED_FINDINGS if name not in document["findings"]
    ]
    for name in missing_findings:
        errors.append(f"findings must retain {name}")
    if missing_findings:
        # The remaining checks read those findings, and a report that has
        # dropped one cannot be repaired by inspecting what is left.
        return errors

    # The central prediction failed for Australian speakers. It may be
    # superseded by new evidence in a new report version, never softened in
    # this one.
    predictions = document["predictions"]
    if predictions.get("held_at_every_threshold") is not False:
        errors.append(
            "the recorded outcome is that the group level prediction did not "
            "hold at every threshold; it cannot be reported as though it did"
        )
    australian = predictions[
        "under_the_american_reference_non_american_groups_are_flagged_more"
    ]
    if any(values["australian"] for values in australian.values()):
        errors.append(
            "no threshold showed Australian speakers flagged more than the "
            "American control; a report claiming one contradicts its evidence"
        )

    findings = document["findings"]

    # The rhotic effect was retracted at mapping version 1.2.0. It was produced
    # by a segment the model never emits, at an identical rate in every group
    # including the control, so a report reasserting it contradicts its evidence.
    rhotic = findings["the_rhotic_effect_was_a_segmentation_artifact"]
    if abs(rhotic["rhotic_australian_minus_american_under_the_american_reference"]) > 0.01:
        errors.append(
            "the onset rhotic differential is recorded as effectively zero; a "
            "report showing a material one has not applied the mapping "
            "correction, or is measuring post-vocalic r again"
        )
    if not rhotic.get("what_the_rhotic_target_now_means"):
        errors.append(
            "a report scoring only onset r must say so, because rhoticity is "
            "the difference a reader will assume it measured"
        )

    # Item R2 computed the uncertainty these two findings were missing. The
    # requirement inverts: what previously had to stay recorded as absent must
    # now be recorded as present, so the intervals cannot be quietly dropped
    # again by a later regeneration.
    for name in (
        "the_t_effect_survives_the_correction",
        "the_reference_swap_no_longer_moves_the_control_group",
    ):
        if findings[name].get("uncertainty_state") != "computed_at_item_R2":
            errors.append(
                f"{name} carried no uncertainty until item R2 and now does; a "
                "report that has lost it is describing a movement of a fifth of "
                "a percentage point as though its size were known"
            )

    errors.extend(_validate_uncertainty(document, findings))

    # The correction roughly halved the flag rate. A report that has lost that
    # comparison cannot show a reader how much of the original was noise.
    scale = findings["most_flags_came_from_phones_the_model_never_produces"]
    before = scale.get("american_control_flag_rate_under_mapping_1_1_0")
    after = scale.get("american_control_flag_rate_under_mapping_1_2_0")
    if not isinstance(before, (int, float)) or not isinstance(after, (int, float)):
        errors.append("the before and after control flag rates must be reported")
    elif after >= before:
        errors.append(
            "the mapping correction removed flags; a report showing it adding "
            "them has not been regenerated from the corrected evidence"
        )

    for name in RETRACTED_FINDINGS:
        if name in findings:
            errors.append(
                f"{name} was retracted at mapping version 1.2.0 and may not "
                "return; the evidence it rested on was a segmentation artifact"
            )

    if document.get("schema_version") != "1.2.0":
        errors.append(
            "item R2 raised the report to schema version 1.2.0; an earlier "
            "version carries no uncertainty and is superseded"
        )

    if document.get("phone_mapping_version") == "1.1.0":
        errors.append(
            "mapping version 1.1.0 scored six phone families the model never "
            "produces for English; a report built on it is superseded"
        )

    if not document["declared_confounds"]:
        errors.append("declared confounds may not be emptied")
    if not document.get("what_this_cannot_establish"):
        errors.append("the limits of this measurement may not be removed")
    return errors


def _validate_uncertainty(document, findings):
    """Check that the uncertainty record still says what the measurement said.

    Every check here exists because the corresponding sentence would be
    flattering if it were quietly edited: a family that grew or shrank after
    the fact, a survivor list that stopped matching its own members, a failed
    consonant recorded as passing, or the one surviving result losing the
    confound that stops it being a claim about British English.
    """
    errors = []
    uncertainty = document.get("uncertainty")
    if not isinstance(uncertainty, dict):
        return ["the uncertainty record must be an object"]

    if uncertainty.get("contract_id") != UNCERTAINTY_CONTRACT_ID:
        errors.append("the uncertainty record must name the contract it was frozen under")

    method = uncertainty.get("method") or {}
    if method.get("unit_of_analysis") != "the speaker":
        errors.append(
            "the unit of analysis is the speaker; a report aggregating tokens "
            "has reintroduced the clustering defect item R2 repaired"
        )
    for field in ("resamples", "permutations"):
        if not isinstance(method.get(field), int) or method[field] < 1000:
            errors.append(f"{field} must be recorded and may not fall below 1000")
    if not method.get("seed"):
        errors.append("the seed must be recorded, or no interval here is reproducible")
    if sorted(method.get("corrections") or []) != [
        "benjamini_hochberg",
        "bonferroni",
        "uncorrected",
    ]:
        errors.append(
            "all three corrections are published together so that no reader has "
            "to trust that the flattering one was not selected"
        )

    families = uncertainty.get("families") or {}
    if families.get("declared_before_computing") is not True:
        errors.append(
            "the multiple comparison families were declared before they were "
            "computed; a report that cannot say so has lost the only thing that "
            "makes the correction meaningful"
        )
    for name in REQUIRED_FAMILIES:
        if name not in families:
            errors.append(f"family {name} may not be dropped")
    if any(name not in families for name in REQUIRED_FAMILIES):
        return errors

    # A survivor list is the part a later edit would reach for. It must be
    # derivable from the members it claims to summarise.
    for name in REQUIRED_FAMILIES:
        family = families[name]
        members = family.get("members") or []
        if family.get("tests") != len(members):
            errors.append(f"family {name} reports a test count it does not carry")
        for key, flag in (
            ("survivors_uncorrected", "survives_uncorrected"),
            ("survivors_benjamini_hochberg", "survives_benjamini_hochberg"),
            ("survivors_bonferroni", "survives_bonferroni"),
        ):
            derived = sorted(row["name"] for row in members if row.get(flag))
            if sorted(family.get(key) or []) != derived:
                errors.append(
                    f"family {name} lists {key} that its own members do not support"
                )

    # The declared families are fixed. A per consonant family that acquired a
    # second reference or a second threshold would be a different family,
    # chosen after the answers were known.
    for name, marker in (
        ("A_primary_per_consonant", "australian_minus_american"),
        ("B_secondary_per_consonant", "british_minus_american"),
    ):
        for row in families[name].get("members") or []:
            if not row["name"].startswith(marker):
                errors.append(f"family {name} contains a contrast it did not declare")
            if not row["name"].endswith("_american_reference_at_-1.0"):
                errors.append(
                    f"family {name} was declared at one reference and one "
                    "threshold; a member from elsewhere widens it after the fact"
                )
    if families["S_sceptical_sensitivity"].get("tests", 0) <= max(
        families["A_primary_per_consonant"].get("tests", 0),
        families["B_secondary_per_consonant"].get("tests", 0),
    ):
        errors.append(
            "the sceptical family spans the whole grid and must be larger than "
            "the primary families it exists to check"
        )

    # The group level analysis found nothing. It may be superseded by new
    # evidence in a new report, never softened in this one.
    group_level = findings["nothing_at_group_level_is_distinguishable_from_zero"]
    if group_level.get("survivors_benjamini_hochberg"):
        errors.append(
            "no group level comparison survived correction; a report listing one "
            "contradicts its own family record"
        )
    if families["G_pre_registered_group_level"].get("survivors_uncorrected"):
        errors.append(
            "no group level comparison reached significance even uncorrected; a "
            "report claiming one contradicts its evidence"
        )

    # t failed. This is the question item R2 was created to answer and it is
    # the one a later edit would most want to reverse.
    t_finding = findings["the_t_differential_does_not_survive_correction"]
    if t_finding.get("survives_benjamini_hochberg") is not False:
        errors.append(
            "the t differential does not survive correction across its declared "
            "family; a report recording that it does has changed the family, the "
            "correction, or the evidence"
        )
    if not isinstance(t_finding.get("p_benjamini_hochberg"), (int, float)):
        errors.append("the t differential must report its corrected p value")
    elif t_finding["p_benjamini_hochberg"] < 0.05:
        errors.append(
            "the t differential is recorded as failing correction; a corrected p "
            "value below the level contradicts that record"
        )
    if not isinstance(t_finding.get("minimum_detectable_difference"), (int, float)):
        errors.append(
            "the t differential must report the smallest difference this design "
            "could have detected, because that is what makes its size readable"
        )

    # The one surviving result is not a claim about British English, and the
    # confound that stops it being one may not be dropped.
    survivor = findings["one_per_consonant_result_survives_correction_and_it_is_british"]
    for field in ("p_benjamini_hochberg", "p_bonferroni"):
        value = survivor.get(field)
        if not isinstance(value, (int, float)) or value >= 0.05:
            errors.append(
                f"the surviving per consonant result must carry a {field} below "
                "the declared level or it is not a survivor"
            )
    low, high = survivor.get("ci_low"), survivor.get("ci_high")
    if not isinstance(low, (int, float)) or not isinstance(high, (int, float)):
        errors.append("the surviving result must carry its interval")
    elif low <= 0.0 <= high:
        errors.append(
            "an interval containing zero may not be reported as a surviving effect"
        )
    if "disjoint prompt" not in survivor.get("statement", "") and (
        "34 shared prompts" not in survivor.get("statement", "")
    ):
        errors.append(
            "the surviving result is confounded with lexical material because the "
            "groups read effectively disjoint prompts; that sentence may not be "
            "removed from it"
        )
    if not survivor.get("what_it_cannot_support"):
        errors.append("the surviving result must state what it cannot support")

    parity = findings["the_two_references_do_not_create_the_same_opportunities"]
    comparable = parity.get("comparable_across_references")
    not_comparable = parity.get("not_comparable_across_references")
    if not comparable or not not_comparable:
        errors.append(
            "the reference opportunity parity record must list both the "
            "consonants that are comparable across references and those that "
            "are not"
        )
    elif survivor.get("consonant") not in comparable:
        errors.append(
            "the surviving result is reported as compared like with like; it "
            "cannot be a consonant whose opportunity count moves between "
            "references"
        )

    lineage = uncertainty.get("training_lineage_declaration") or {}
    if lineage.get("resolution") != "declared, not resolved":
        errors.append(
            "the Common Voice training lineage overlap is declared and not "
            "resolved; a report claiming otherwise needs a model that does not "
            "share the evaluation data"
        )
    if not lineage.get("what_this_does_not_license"):
        errors.append(
            "the lineage declaration must keep the limit that travels with it: a "
            "differential running the way lineage bias predicts would be "
            "uninterpretable under the same reasoning"
        )
    if not uncertainty.get("detectable_effect"):
        errors.append(
            "a null result without a detectable effect statement cannot be told "
            "apart from a look too small to tell"
        )
    return errors


def assert_valid_report(path=REPORT_PATH):
    import json

    document = json.loads(Path(path).read_text(encoding="utf-8"))
    errors = validate_report(document)
    if errors:
        raise ValueError("\n".join(errors))
    return document
