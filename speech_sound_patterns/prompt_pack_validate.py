"""Fail-closed checks on the checkpoint 22F research prompt pack.

The pack's job is to say what it probes and to refuse everything else out loud.
These checks exist so that neither half can be edited away later: a refused
opportunity cannot be relabelled scorable, a declared coverage shortfall cannot
be quietly dropped, the derived lexicon boundary cannot be opened, and the
developer pack cannot become the product's onboarding task by having a field
changed.

The variety rules are re-derived here from the fields the pack records rather
than trusted from the ``reason`` beside them. A pack that says an opportunity is
scorable while its own recorded position and context say the rules refuse it is
inconsistent with itself, and that is exactly the edit worth catching.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from .prompt_pack import (
    DENTAL_FRICATIVES,
    ENGLISH_CONSONANTS,
    OPPORTUNITY_REFUSAL_REASONS,
)

PACK_PATH = Path(__file__).with_name("research-prompt-pack-v1.0.0.json")
ONBOARDING_PATH = (
    Path(__file__).resolve().parents[1]
    / "assessment"
    / "pronunciation-research-v1.0.0.json"
)

ALLOWED_STATES = frozenset({"scorable", "unscorable"})
ROOT_FIELDS = frozenset(
    {
        "schema_version",
        "pack_id",
        "pack_version",
        "checkpoint",
        "status",
        "contract_id",
        "elicitation_modes",
        "references",
        "words",
        "totals",
        "coverage",
        "declared_shortfalls",
        "eligible_pool",
        "content_screen",
        "unmet_activation_requirements",
        "distribution_boundary",
        "limitations",
        "release_boundaries",
    }
)
WORD_FIELDS = frozenset(
    {
        "word",
        "written_prompt",
        "selection_reason",
        "british_forms",
        "australian_forms",
        "opportunities",
        "scorable_opportunities",
    }
)
OPPORTUNITY_FIELDS = frozenset(
    {
        "opportunity",
        "phoneme",
        "position",
        "prevocalic",
        "postvocalic",
        "syllabic",
        "state",
        "reason",
    }
)
VARIANT_OPPORTUNITY_FIELDS = frozenset(
    {
        "opportunity",
        "phonemes_documented",
        "state",
        "reason",
    }
)
RELEASE_BOUNDARY_FIELDS = frozenset(
    {
        "any_speaker_scored",
        "artifact_produced",
        "coaching_progress_screening_or_diagnosis_output",
        "extractor_implemented",
        "frozen_benchmark_touched",
        "gates_applied",
        "held_out_read",
        "machine_generated_targets",
        "onboarding_word_pack_filled",
        "pipeline_behaviour_changed",
        "selection_record_touched",
        "system_selected",
        "task_activated",
        "threshold_selected",
    }
)

REQUIRED_LIMITATION_TOPICS = {
    "a lexicon is not truth": "never observes how anybody said it",
    "the pack is unreviewed": "not professionally reviewed",
    "the exclusion list is ours": "this project's own construction",
    "the reference is non rhotic": "declining to ask",
    "the union rule did little here": "almost nothing to union",
}


def _rule_refuses(item):
    """Re-derive whether the variety rules refuse this recorded opportunity.

    This reads only what the pack itself wrote down, which is why the pack
    records both the prevocalic and the postvocalic context: without them the
    flapping rule could not be checked, and an unverifiable rule is one that can
    be edited away. The same goes for syllabicity, which is why it is recorded
    beside every opportunity even though only a refused one can carry it.
    """
    phoneme = item.get("phoneme")
    prevocalic = item.get("prevocalic")
    postvocalic = item.get("postvocalic")
    if item.get("syllabic"):
        return "syllabic_consonant_reduction"
    if not isinstance(phoneme, str):
        return None
    if phoneme in DENTAL_FRICATIVES:
        return "dental_fricative_variation"
    if phoneme == "ɹ" and not prevocalic:
        return "post_vocalic_rhotic"
    if phoneme in ("t", "d") and prevocalic and postvocalic:
        return "intervocalic_flapping_context"
    if phoneme == "t" and not prevocalic:
        return "coda_t_glottalling"
    if phoneme == "l" and not prevocalic:
        return "coda_l_vocalisation"
    return None


def validate_pack(document, onboarding=None):
    """Return every reason this pack may not be trusted as written."""
    errors = []
    if not isinstance(document, dict):
        return ["pack must be an object"]
    missing = sorted(ROOT_FIELDS - set(document))
    extras = sorted(set(document) - ROOT_FIELDS)
    if missing:
        errors.append(f"pack is missing: {', '.join(missing)}")
    if extras:
        errors.append(f"pack has unsupported fields: {', '.join(extras)}")
    if missing:
        return errors

    exact_identity = {
        "schema_version": "1.0.0",
        "pack_id": "speech_sound_patterns_research_prompt_pack_v1",
        "pack_version": "1.0.0",
        "checkpoint": "22F",
        "status": "developer_research_pack_not_reviewed_not_active",
        "contract_id": "speech_sound_patterns_research_prompt_pack_v1",
    }
    for field, expected in exact_identity.items():
        if document[field] != expected:
            errors.append(f"pack {field} must remain {expected}")

    required_container_types = {
        "elicitation_modes": dict,
        "references": dict,
        "words": list,
        "totals": dict,
        "coverage": dict,
        "declared_shortfalls": list,
        "eligible_pool": dict,
        "content_screen": dict,
        "unmet_activation_requirements": list,
        "distribution_boundary": dict,
        "limitations": list,
        "release_boundaries": dict,
    }
    invalid_containers = []
    for field, expected_type in required_container_types.items():
        if not isinstance(document[field], expected_type):
            errors.append(f"pack {field} must be a {expected_type.__name__}")
            invalid_containers.append(field)
    if invalid_containers:
        return errors

    if document["checkpoint"] != "22F":
        errors.append("pack must declare its checkpoint")

    if set(document["release_boundaries"]) != RELEASE_BOUNDARY_FIELDS:
        errors.append("pack release boundaries are incomplete or unsupported")
    for flag, value in document["release_boundaries"].items():
        if value is not False:
            errors.append(f"release boundary {flag} must stay closed")

    expected_references = {
        "british": {
            "file": "english_uk_mfa.dict",
            "source_id": "mfa_english_dictionary",
        },
        "australian_overlay": {
            "source_id": "wiktionary_australian_kaikki",
            "transcriptions_used": "phonemic only",
        },
        "machine_generated_targets": False,
    }
    if document["references"] != expected_references:
        errors.append("pack reference bindings changed")
    if document["references"].get("machine_generated_targets") is not False:
        errors.append(
            "no target in this pack may be machine generated; a pack saying "
            "otherwise contradicts the rule it was built under"
        )

    if document["elicitation_modes"].get("modes_are_comparable") is not False:
        errors.append(
            "the written and recorded prompt modes are different tasks with "
            "different confounders and may never be declared comparable"
        )

    words = document["words"]
    if not words:
        errors.append("a pack with no words cannot be valid")
        return errors

    seen = set()
    scorable = 0
    unscorable = 0
    total_opportunities = 0
    multiple_form_words = 0
    derived_coverage = defaultdict(set)
    for entry_index, entry in enumerate(words):
        if not isinstance(entry, dict):
            errors.append(f"word entry {entry_index} must be an object")
            continue
        missing_word = sorted(WORD_FIELDS - set(entry))
        extra_word = sorted(set(entry) - WORD_FIELDS)
        if missing_word:
            errors.append(
                f"word entry {entry_index} is missing: {', '.join(missing_word)}"
            )
            continue
        if extra_word:
            errors.append(
                f"word entry {entry_index} has unsupported fields: "
                + ", ".join(extra_word)
            )
        word = entry.get("word")
        if not isinstance(word, str) or not word or word != word.casefold():
            errors.append(f"word entry {entry_index} must use nonempty lowercase text")
            word_label = f"word entry {entry_index}"
        else:
            word_label = word
            if word in seen:
                errors.append(f"{word} appears twice")
            seen.add(word)
        if entry.get("written_prompt") != word:
            errors.append(f"{word_label} has a written prompt that is not the word")
        if not entry.get("selection_reason"):
            errors.append(f"{word_label} was chosen without a recorded reason")
        if (
            not isinstance(entry.get("british_forms"), int)
            or isinstance(entry.get("british_forms"), bool)
            or entry["british_forms"] < 1
        ):
            errors.append(f"{word_label} carries no British reference form")
        if (
            not isinstance(entry.get("australian_forms"), int)
            or isinstance(entry.get("australian_forms"), bool)
            or entry["australian_forms"] < 1
        ):
            errors.append(f"{word_label} carries no Australian tagged form")
        if (
            isinstance(entry.get("british_forms"), int)
            and isinstance(entry.get("australian_forms"), int)
            and (
                entry["british_forms"] > 1
                or entry["australian_forms"] > 1
            )
        ):
            multiple_form_words += 1
        opportunities = entry.get("opportunities")
        if not isinstance(opportunities, list) or not opportunities:
            errors.append(f"{word_label} must carry a nonempty opportunity list")
            continue
        total_opportunities += len(opportunities)
        for expected_index, item in enumerate(opportunities):
            if not isinstance(item, dict):
                errors.append(
                    f"{word_label} opportunity {expected_index} must be an object"
                )
                continue
            if item.get("reason") == "documented_variant_disagreement":
                missing_variant = sorted(VARIANT_OPPORTUNITY_FIELDS - set(item))
                extra_variant = sorted(set(item) - VARIANT_OPPORTUNITY_FIELDS)
                if missing_variant:
                    errors.append(
                        f"{word_label} variant opportunity {expected_index} is missing: "
                        + ", ".join(missing_variant)
                    )
                    continue
                if extra_variant:
                    errors.append(
                        f"{word_label} variant opportunity {expected_index} has "
                        "unsupported fields: "
                        + ", ".join(extra_variant)
                    )
                if item.get("opportunity") != expected_index:
                    errors.append(
                        f"{word_label} opportunity ids must be contiguous from zero"
                    )
                documented = item.get("phonemes_documented")
                if (
                    not isinstance(documented, list)
                    or any(
                        not isinstance(phoneme, str) or not phoneme
                        for phoneme in documented
                    )
                    or len(set(documented)) < 2
                ):
                    errors.append(
                        f"{word_label} variant opportunity must retain distinct phones"
                    )
                if item.get("state") != "unscorable":
                    errors.append(
                        f"{word_label} documented reference disagreement must be unscorable"
                    )
                unscorable += 1
                continue
            missing_opportunity = sorted(OPPORTUNITY_FIELDS - set(item))
            extra_opportunity = sorted(set(item) - OPPORTUNITY_FIELDS)
            if missing_opportunity:
                errors.append(
                    f"{word_label} opportunity {expected_index} is missing: "
                    + ", ".join(missing_opportunity)
                )
                continue
            if extra_opportunity:
                errors.append(
                    f"{word_label} opportunity {expected_index} has unsupported fields: "
                    + ", ".join(extra_opportunity)
                )
            if item.get("opportunity") != expected_index:
                errors.append(
                    f"{word_label} opportunity ids must be contiguous from zero"
                )
            position = item.get("position")
            position_valid = (
                isinstance(position, str)
                and position in {"initial", "medial", "final"}
            )
            if not position_valid:
                errors.append(
                    f"{word_label} opportunity {expected_index} has an invalid word position"
                )
            for field in ("prevocalic", "postvocalic", "syllabic"):
                if not isinstance(item.get(field), bool):
                    errors.append(
                        f"{word_label} opportunity {expected_index} {field} must be boolean"
                    )
            state = item.get("state")
            if not isinstance(state, str) or state not in ALLOWED_STATES:
                errors.append(f"{word_label} opportunity {item.get('opportunity')} has "
                              f"an unknown state {state!r}")
                continue
            if state == "unscorable":
                unscorable += 1
                reason = item.get("reason")
                if (
                    not isinstance(reason, str)
                    or reason not in OPPORTUNITY_REFUSAL_REASONS
                ):
                    errors.append(
                        f"{word_label} refuses opportunity {item.get('opportunity')} "
                        "without a declared reason"
                    )
                refusal = _rule_refuses(item)
                if item.get("reason") != refusal:
                    errors.append(
                        f"{word_label} opportunity {item.get('opportunity')} refusal "
                        "does not follow its recorded context"
                    )
                continue
            scorable += 1
            if item.get("reason") is not None:
                errors.append(
                    f"{word_label} opportunity {item.get('opportunity')} is scorable "
                    "and carries a refusal reason"
                )
            phoneme = item.get("phoneme")
            if not isinstance(phoneme, str) or phoneme not in ENGLISH_CONSONANTS:
                errors.append(
                    f"{word_label} scores {phoneme!r}, which is not an English "
                    "consonant this pack may probe"
                )
                continue
            refusal = _rule_refuses(item)
            if refusal is not None:
                errors.append(
                    f"{word_label} opportunity {item.get('opportunity')} is recorded "
                    f"scorable, but its own position and context are refused by "
                    f"{refusal}"
                )
            if position_valid:
                derived_coverage[phoneme].add(position)
        if entry.get("scorable_opportunities") != sum(
            1
            for item in entry.get("opportunities", [])
            if isinstance(item, dict) and item.get("state") == "scorable"
        ):
            errors.append(f"{word} miscounts its own scorable opportunities")

    totals = document["totals"]
    if totals.get("words") != len(words):
        errors.append("the pack miscounts its own words")
    if totals.get("opportunities") != total_opportunities:
        errors.append("the pack miscounts its total opportunities")
    if totals.get("scorable_opportunities") != scorable:
        errors.append("the pack miscounts its own scorable opportunities")
    if totals.get("unscorable_opportunities") != unscorable:
        errors.append("the pack miscounts its own unscorable opportunities")
    if totals.get("words_with_more_than_one_documented_form") != multiple_form_words:
        errors.append("the pack miscounts words with multiple documented forms")

    normalized_coverage = {
        phoneme: sorted(positions)
        for phoneme, positions in sorted(derived_coverage.items())
    }
    if document["coverage"] != normalized_coverage:
        errors.append("the pack coverage does not recompute from scorable opportunities")

    if not all(
        isinstance(item, dict)
        and set(item) == {"phoneme", "positions_achieved", "reason"}
        and isinstance(item.get("phoneme"), str)
        and item["phoneme"]
        and isinstance(item.get("positions_achieved"), int)
        and not isinstance(item.get("positions_achieved"), bool)
        and isinstance(item.get("reason"), str)
        and item["reason"]
        for item in document["declared_shortfalls"]
    ):
        errors.append("declared shortfalls must be objects with phonemes")
        shortfalls = {}
    else:
        shortfall_phonemes = [
            item["phoneme"] for item in document["declared_shortfalls"]
        ]
        if len(shortfall_phonemes) != len(set(shortfall_phonemes)):
            errors.append("declared shortfalls may not contain duplicate phonemes")
        if set(shortfall_phonemes) != {"h", "ʒ"}:
            errors.append("declared shortfalls must remain exactly h and ʒ")
        shortfalls = {item["phoneme"]: item for item in document["declared_shortfalls"]}
    for phoneme, positions in document["coverage"].items():
        if (
            not isinstance(phoneme, str)
            or not isinstance(positions, list)
            or any(
                not isinstance(position, str)
                or position not in {"initial", "medial", "final"}
                for position in positions
            )
        ):
            errors.append("pack coverage entries must name valid position lists")
            continue
        if len(positions) >= 2:
            continue
        declared = shortfalls.get(phoneme)
        if declared is None:
            errors.append(
                f"{phoneme} reaches one position and no shortfall is declared "
                "for it; a thin coverage may be reported but never hidden"
            )
        elif declared["positions_achieved"] != len(positions):
            errors.append(f"the declared shortfall for {phoneme} does not match the pack")
        if declared is not None and not declared.get("reason"):
            errors.append(f"the shortfall for {phoneme} is declared without a reason")

    pool = document["eligible_pool"]
    if pool.get("words", 0) <= len(words):
        errors.append(
            "the eligible pool must be larger than the pack, or the twenty "
            "words were not chosen from anything"
        )
    refusals = pool.get("opportunity_refusals_across_the_pool", {}).get(
        "unscorable_by_reason", {}
    )
    for reason in OPPORTUNITY_REFUSAL_REASONS:
        if reason not in refusals:
            errors.append(
                f"the pool report drops {reason}; a rule that never fires must "
                "read zero rather than be absent"
            )

    boundary = document["distribution_boundary"]
    if boundary.get("derived_lexicon_stays_server_side") is not True:
        errors.append("the derived lexicon may not leave the server")
    if not boundary.get("attribution_required"):
        errors.append("the required attributions may not be emptied")
    if not boundary.get("what_stays_private"):
        errors.append("the list of what stays private may not be emptied")

    screen = document["content_screen"]
    if not screen.get("categories_screened_out"):
        errors.append(
            "the content screen may not be emptied; these words are read aloud "
            "by a person"
        )
    if not screen.get("this_is_not_the_review_the_protocol_requires"):
        errors.append(
            "the content screen must keep saying that it is not the cultural "
            "and familiarity review the protocol requires"
        )

    if not document["unmet_activation_requirements"]:
        errors.append(
            "this pack is not reviewed and not active; its unmet activation "
            "requirements may not be emptied"
        )
    if not document["limitations"]:
        errors.append("the stated limitations may not be emptied")
    else:
        written = " ".join(document["limitations"]).lower()
        for topic, phrase in sorted(REQUIRED_LIMITATION_TOPICS.items()):
            if phrase.lower() not in written:
                errors.append(f"the limitation about {topic} may not be removed")

    onboarding = onboarding if onboarding is not None else _read_onboarding()
    if onboarding is not None:
        word_pack = onboarding.get("word_pack") if isinstance(onboarding, dict) else None
        if not isinstance(word_pack, dict):
            errors.append("the onboarding pronunciation word pack is unreadable")
        else:
            if word_pack.get("pack_id") != "controlled_word_candidates_en_v1":
                errors.append("the onboarding pronunciation pack identity changed")
            if word_pack.get("pack_version") != "1.0.0":
                errors.append("the onboarding pronunciation pack version changed")
            if word_pack.get("status") != "awaiting_professional_review":
                errors.append(
                    "the onboarding pronunciation pack is no longer awaiting review"
                )
            if word_pack.get("stimuli") != []:
                errors.append(
                    "the onboarding pronunciation word pack is no longer empty; this "
                    "developer research pack may not become the product task"
                )
    return errors


def _read_onboarding():
    if not ONBOARDING_PATH.is_file():
        return None
    return json.loads(ONBOARDING_PATH.read_text(encoding="utf-8"))


def assert_valid_pack(path=PACK_PATH):
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    errors = validate_pack(document)
    if errors:
        raise ValueError("\n".join(errors))
    return document
