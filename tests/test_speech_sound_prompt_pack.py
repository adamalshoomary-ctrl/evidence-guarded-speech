import copy
import json
import unittest
from pathlib import Path

from speech_sound_patterns.build_prompt_pack import serialise
from speech_sound_patterns.prompt_pack import (
    ALIGNER_CONSONANTS,
    ALIGNER_REFUSED,
    ALIGNER_SYLLABIC,
    ALIGNER_VOWELS,
    BRITISH_DICTIONARY,
    ENGLISH_CONSONANTS,
    OPPORTUNITY_REFUSAL_REASONS,
    PACK_PATH,
    WORD_REFUSAL_REASONS,
    PromptPackError,
    build_pack,
    consonant_frame,
    load_contract,
    opportunities,
    segment_aligner_form,
    segment_wiktionary_form,
    variety_refusal,
)
from speech_sound_patterns.prompt_pack_validate import validate_pack
from speech_sound_patterns.variety_reference import (
    VarietyReferenceError,
    load_dictionary,
)

from tests.research_data import (
    needs_repository_history,
    needs_research_data,
)

COMMITTED = json.loads(PACK_PATH.read_text(encoding="utf-8"))


def reading(source, form):
    """One (source, verbatim, segments) reading, the shape opportunities reads."""
    segments = (
        segment_aligner_form(form)
        if source == "british"
        else segment_wiktionary_form(form)
    )
    verbatim = " ".join(form) if source == "british" else form
    return (source, verbatim, segments)


class AlignerNormalisationTests(unittest.TestCase):
    """The aligner's allophonic detail collapses, and nothing is dropped silently."""

    def test_an_unlisted_symbol_fails_closed(self):
        with self.assertRaises(PromptPackError):
            segment_aligner_form(("ʘ",))

    def test_a_glottal_variant_refuses_the_word(self):
        # The first measurable scope excludes glottal variants, so a word whose
        # documented pronunciation uses one cannot be a prompt.
        with self.assertRaises(PromptPackError) as raised:
            segment_aligner_form(("ə", "b", "aw", "ʔ"))
        self.assertEqual(raised.exception.code, "refused_symbol_in_a_documented_form")

    def test_aligner_machinery_is_never_a_phone(self):
        for token in ("spn", "<unk>", "[laughter]"):
            with self.subTest(token=token):
                with self.assertRaises(PromptPackError):
                    segment_aligner_form((token,))

    def test_predictable_detail_collapses_to_the_phoneme(self):
        for symbol, phoneme in (
            ("pʰ", "p"),
            ("tʲ", "t"),
            ("kʷ", "k"),
            ("c", "k"),
            ("ɟ", "ɡ"),
            ("ɲ", "n"),
            ("ʎ", "l"),
            ("ç", "h"),
        ):
            with self.subTest(symbol=symbol):
                self.assertEqual(
                    segment_aligner_form((symbol,))[0]["phoneme"], phoneme
                )

    def test_the_dental_stops_are_the_dental_fricatives(self):
        # The aligner writes the consonant of "the" and the consonant of "bath"
        # as dental stops. Mapping them on symbol shape would mis-expect the
        # most frequent consonant context in English, which is the defect phone
        # mapping version 1.1.0 corrected at checkpoint 22E8.
        self.assertEqual(segment_aligner_form(("d̪",))[0]["phoneme"], "ð")
        self.assertEqual(segment_aligner_form(("t̪",))[0]["phoneme"], "θ")

    def test_dark_l_is_l(self):
        for symbol in ("ɫ", "ɫ̩"):
            with self.subTest(symbol=symbol):
                self.assertEqual(segment_aligner_form((symbol,))[0]["phoneme"], "l")

    def test_syllabic_consonants_are_marked_rather_than_hidden(self):
        for symbol in sorted(ALIGNER_SYLLABIC):
            with self.subTest(symbol=symbol):
                self.assertTrue(segment_aligner_form((symbol,))[0]["syllabic"])

    def test_every_symbol_the_british_dictionary_uses_is_named(self):
        # An unlisted symbol refuses a word, so an incomplete table would
        # silently shrink the eligible pool instead of failing.
        try:
            dictionary = load_dictionary(BRITISH_DICTIONARY)
        except VarietyReferenceError:
            self.skipTest("the acquired dictionaries are not present on this machine")
        used = {
            phone
            for forms in dictionary.values()
            for form in forms
            for phone in form
        }
        known = set(ALIGNER_CONSONANTS) | set(ALIGNER_VOWELS) | set(ALIGNER_REFUSED)
        self.assertEqual(sorted(used - known), [])

    def test_every_mapped_phoneme_is_an_english_consonant(self):
        for symbol, (phoneme, _) in ALIGNER_CONSONANTS.items():
            with self.subTest(symbol=symbol):
                self.assertIn(phoneme, ENGLISH_CONSONANTS)


class WiktionaryNormalisationTests(unittest.TestCase):
    """Volunteer transcriptions are read strictly or not at all."""

    def test_a_tie_barred_affricate_is_one_consonant(self):
        segments = segment_wiktionary_form("t͡ʃɪp")
        self.assertEqual(
            [item.get("phoneme") for item in segments if item["kind"] == "consonant"],
            ["tʃ", "p"],
        )

    def test_stress_syllable_and_length_marks_are_dropped(self):
        plain = segment_wiktionary_form("siːd")
        marked = segment_wiktionary_form("ˈsiː.d")
        self.assertEqual(plain, marked)

    def test_a_narrow_mark_on_a_vowel_is_dropped(self):
        # The pack scores consonants, and the mark never touches one here.
        self.assertEqual(
            segment_wiktionary_form("fɪ̝ʃ"), segment_wiktionary_form("fɪʃ")
        )

    def test_a_narrow_mark_on_a_consonant_refuses_the_form(self):
        with self.assertRaises(PromptPackError) as raised:
            segment_wiktionary_form("fɪs̝")
        self.assertEqual(raised.exception.code, "narrow_quality_mark_on_a_consonant")

    def test_an_optional_segment_refuses_the_form(self):
        # Parentheses mark an optional sound. Choosing one reading would be
        # inventing a target rather than reading one.
        with self.assertRaises(PromptPackError):
            segment_wiktionary_form("ɡäːd(ə)n")

    def test_a_plain_r_is_read_as_the_english_approximant(self):
        self.assertEqual(segment_wiktionary_form("red")[0]["phoneme"], "ɹ")

    def test_an_empty_transcription_is_refused(self):
        with self.assertRaises(PromptPackError):
            segment_wiktionary_form("ˈ.ː")


class OpportunityTests(unittest.TestCase):
    """Positions are compared, never guessed, and refusals are named."""

    def test_readings_that_disagree_on_consonant_count_refuse_the_word(self):
        with self.assertRaises(PromptPackError) as raised:
            opportunities([reading("british", ("k", "ɑː")), reading("australian", "kɑːɹ")])
        self.assertEqual(
            raised.exception.code, "documented_readings_disagree_on_consonant_count"
        )

    def test_a_disagreement_at_one_position_leaves_the_rest_intact(self):
        found = opportunities(
            [reading("british", ("b", "ej", "ʒ")), reading("australian", "beɪdʒ")]
        )
        self.assertEqual(found[0]["state"], "scorable")
        self.assertEqual(found[1]["state"], "unscorable")
        self.assertEqual(found[1]["reason"], "documented_variant_disagreement")
        self.assertEqual(found[1]["phonemes_documented"], ["dʒ", "ʒ"])

    def test_the_disagreeing_position_names_both_documented_forms(self):
        # Neither documented form is an error, so both are recorded. A variety
        # mismatch may be excluded but never subtracted.
        found = opportunities(
            [reading("british", ("b", "ej", "ʒ")), reading("australian", "beɪdʒ")]
        )
        self.assertNotIn("phoneme", found[1])

    def test_a_word_with_no_consonant_is_refused(self):
        # An all vowel word carries nothing this pack can probe, and admitting
        # it would put an empty opportunity list into the eligible pool.
        with self.assertRaises(PromptPackError) as raised:
            opportunities([reading("british", ("aj",)), reading("australian", "ɑɪ")])
        self.assertEqual(raised.exception.code, "no_consonant_opportunity")

    def test_a_postvocalic_rhotic_is_never_scored(self):
        frame = consonant_frame(
            [{"kind": "vowel"}, {"kind": "consonant", "phoneme": "ɹ", "syllabic": False}]
        )
        self.assertEqual(variety_refusal(frame[0]), "post_vocalic_rhotic")

    def test_an_onset_rhotic_is_the_one_rhotic_context_that_is_scored(self):
        frame = consonant_frame(
            [{"kind": "consonant", "phoneme": "ɹ", "syllabic": False}, {"kind": "vowel"}]
        )
        self.assertIsNone(variety_refusal(frame[0]))

    def test_an_intervocalic_stop_is_never_scored(self):
        for phoneme in ("t", "d"):
            with self.subTest(phoneme=phoneme):
                frame = consonant_frame(
                    [
                        {"kind": "vowel"},
                        {"kind": "consonant", "phoneme": phoneme, "syllabic": False},
                        {"kind": "vowel"},
                    ]
                )
                self.assertEqual(
                    variety_refusal(frame[0]), "intervocalic_flapping_context"
                )

    def test_a_coda_t_and_a_coda_l_are_never_scored(self):
        for phoneme, reason in (("t", "coda_t_glottalling"), ("l", "coda_l_vocalisation")):
            with self.subTest(phoneme=phoneme):
                frame = consonant_frame(
                    [
                        {"kind": "vowel"},
                        {"kind": "consonant", "phoneme": phoneme, "syllabic": False},
                    ]
                )
                self.assertEqual(variety_refusal(frame[0]), reason)

    def test_a_dental_fricative_is_never_scored(self):
        for phoneme in ("θ", "ð"):
            with self.subTest(phoneme=phoneme):
                frame = consonant_frame(
                    [
                        {"kind": "consonant", "phoneme": phoneme, "syllabic": False},
                        {"kind": "vowel"},
                    ]
                )
                self.assertEqual(variety_refusal(frame[0]), "dental_fricative_variation")

    def test_a_syllabic_consonant_is_never_scored(self):
        frame = consonant_frame(
            [
                {"kind": "vowel"},
                {"kind": "consonant", "phoneme": "l", "syllabic": True},
            ]
        )
        self.assertEqual(variety_refusal(frame[0]), "syllabic_consonant_reduction")

    def test_an_onset_t_and_an_onset_l_are_scored(self):
        for phoneme in ("t", "l"):
            with self.subTest(phoneme=phoneme):
                frame = consonant_frame(
                    [
                        {"kind": "consonant", "phoneme": phoneme, "syllabic": False},
                        {"kind": "vowel"},
                    ]
                )
                self.assertIsNone(variety_refusal(frame[0]))


class ContractTests(unittest.TestCase):
    """The rules were frozen before any word was read out of a dictionary."""

    def setUp(self):
        self.contract = load_contract()

    def test_every_release_boundary_is_closed(self):
        for flag, value in self.contract["release_boundaries"].items():
            with self.subTest(flag=flag):
                self.assertFalse(value)

    def test_a_contract_with_an_open_boundary_is_refused(self):
        opened = copy.deepcopy(self.contract)
        opened["release_boundaries"]["system_selected"] = True
        with self.assertRaises(PromptPackError):
            build_pack(contract=opened)

    def test_the_contract_names_twenty_distinct_words_with_reasons(self):
        words = self.contract["word_selection"]["words"]
        self.assertEqual(len(words), 20)
        self.assertEqual(len({item["word"] for item in words}), 20)
        for item in words:
            with self.subTest(word=item["word"]):
                self.assertTrue(item["reason"].strip())

    def test_the_contract_bars_a_generated_target(self):
        barred = " ".join(
            self.contract["sources"]["sources_that_may_not_define_a_target"]
        ).lower()
        self.assertIn("grapheme to phoneme", barred)
        self.assertIn("bookbot", barred)

    def test_every_variety_rule_carries_evidence_and_a_real_effect(self):
        # A rule that names no refusal the code can actually produce would read
        # as a safeguard while doing nothing.
        for rule in self.contract["variety_sensitive_exclusions"]["rules"]:
            with self.subTest(rule=rule["id"]):
                self.assertTrue(rule["evidence"].strip())
                if rule["effect"] == "opportunity_unscorable":
                    self.assertIn(rule["refusal_code"], OPPORTUNITY_REFUSAL_REASONS)
                else:
                    self.assertEqual(rule["effect"], "word_refused")
                    self.assertIn(rule["refusal_code"], WORD_REFUSAL_REASONS)


class PackTests(unittest.TestCase):
    """What the committed pack says about itself must be true of it."""

    def test_the_committed_pack_is_valid(self):
        self.assertEqual(validate_pack(copy.deepcopy(COMMITTED)), [])

    def test_the_pack_probes_only_english_consonants(self):
        for entry in COMMITTED["words"]:
            for item in entry["opportunities"]:
                if item["state"] != "scorable":
                    continue
                with self.subTest(word=entry["word"], index=item["opportunity"]):
                    self.assertIn(item["phoneme"], ENGLISH_CONSONANTS)

    def test_the_pack_refuses_at_least_one_opportunity_of_its_own(self):
        # The rules must be visible in the pack, not only in these tests.
        refused = [
            item
            for entry in COMMITTED["words"]
            for item in entry["opportunities"]
            if item["state"] == "unscorable"
        ]
        self.assertTrue(refused)

    def test_the_pool_reports_the_rhotic_rule_as_never_firing(self):
        # Under a non-rhotic British reference the opportunity mostly does not
        # exist to be refused. That is the checkpoint 22E8 mechanism, and it is
        # reported as a zero rather than as an absent key.
        counts = COMMITTED["eligible_pool"]["opportunity_refusals_across_the_pool"][
            "unscorable_by_reason"
        ]
        self.assertEqual(counts["post_vocalic_rhotic"], 0)

    def test_the_pack_records_how_rarely_the_union_rule_had_anything_to_union(self):
        # Requiring every documented form to agree tends to select words with
        # only one, so the safeguard must not be read as having done work here
        # that it did not do.
        self.assertLess(
            COMMITTED["totals"]["words_with_more_than_one_documented_form"],
            len(COMMITTED["words"]) // 2,
        )
        self.assertTrue(
            any("almost nothing to union" in line for line in COMMITTED["limitations"])
        )

    def test_the_twenty_words_were_chosen_from_thousands(self):
        self.assertGreater(COMMITTED["eligible_pool"]["words"], 1000)

    def test_the_recorded_prompt_mode_is_not_built(self):
        self.assertEqual(
            COMMITTED["elicitation_modes"]["recorded_prompt_alternative"], "not_built"
        )
        self.assertFalse(COMMITTED["elicitation_modes"]["modes_are_comparable"])

    def test_the_onboarding_word_pack_is_still_empty(self):
        # This developer research pack may not become the product task.
        onboarding = json.loads(
            (
                Path(__file__).resolve().parents[1]
                / "assessment"
                / "pronunciation-research-v1.0.0.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(onboarding["word_pack"]["stimuli"], [])
        self.assertEqual(onboarding["word_pack"]["status"], "awaiting_professional_review")

    def test_the_committed_pack_rebuilds_byte_for_byte(self):
        try:
            pack, _ = build_pack()
        except (PromptPackError, VarietyReferenceError):
            self.skipTest("the acquired references are not present on this machine")
        self.assertEqual(serialise(pack), PACK_PATH.read_text(encoding="utf-8"))

    @needs_research_data
    def test_a_chosen_word_that_stops_being_eligible_fails_the_build(self):
        broken = copy.deepcopy(load_contract())
        broken["word_selection"]["words"][0]["word"] = "zzzzzz"
        with self.assertRaises(PromptPackError):
            build_pack(contract=broken)


class ValidatorTests(unittest.TestCase):
    """Every honest statement in the pack must be one that cannot be edited out."""

    def setUp(self):
        self.pack = copy.deepcopy(COMMITTED)

    def assertRejected(self, fragment):
        errors = validate_pack(self.pack)
        self.assertTrue(errors, "the edited pack was accepted")
        self.assertTrue(
            any(fragment in error for error in errors),
            f"expected an error mentioning {fragment!r}, got {errors}",
        )

    def test_relabelling_a_refused_opportunity_as_scorable_fails(self):
        for entry in self.pack["words"]:
            for item in entry["opportunities"]:
                if item["state"] == "unscorable" and "phoneme" in item:
                    item["state"] = "scorable"
                    item["reason"] = None
                    entry["scorable_opportunities"] += 1
                    self.pack["totals"]["scorable_opportunities"] += 1
                    self.pack["totals"]["unscorable_opportunities"] -= 1
                    self.assertRejected("refused by")
                    return
        self.fail("the pack carries no refused opportunity to test with")

    def test_documented_reference_disagreement_shape_is_supported(self):
        child = next(
            item for item in self.pack["words"] if item["word"] == "child"
        )
        child["opportunities"][1] = {
            "opportunity": 1,
            "phonemes_documented": ["l", "w"],
            "state": "unscorable",
            "reason": "documented_variant_disagreement",
        }

        self.assertEqual(validate_pack(self.pack), [])

    def test_documented_reference_disagreement_needs_two_phones(self):
        child = next(
            item for item in self.pack["words"] if item["word"] == "child"
        )
        child["opportunities"][1] = {
            "opportunity": 1,
            "phonemes_documented": ["l"],
            "state": "unscorable",
            "reason": "documented_variant_disagreement",
        }

        self.assertRejected("distinct phones")

    def test_opening_a_release_boundary_fails(self):
        self.pack["release_boundaries"]["extractor_implemented"] = True
        self.assertRejected("must stay closed")

    def test_deleting_or_adding_a_release_boundary_fails(self):
        del self.pack["release_boundaries"]["held_out_read"]
        self.pack["release_boundaries"]["invented_boundary"] = False
        self.assertRejected("incomplete or unsupported")

    def test_claiming_a_generated_target_fails(self):
        self.pack["references"]["machine_generated_targets"] = True
        self.assertRejected("machine generated")

    def test_reference_source_bindings_cannot_drift(self):
        self.pack["references"]["british"]["source_id"] = "unregistered"
        self.assertRejected("reference bindings changed")

    def test_declaring_the_two_prompt_modes_comparable_fails(self):
        self.pack["elicitation_modes"]["modes_are_comparable"] = True
        self.assertRejected("comparable")

    def test_dropping_a_declared_coverage_shortfall_fails(self):
        self.pack["declared_shortfalls"] = []
        self.assertRejected("no shortfall is declared")

    def test_duplicate_declared_coverage_shortfall_fails(self):
        self.pack["declared_shortfalls"].append(
            copy.deepcopy(self.pack["declared_shortfalls"][0])
        )
        self.assertRejected("duplicate phonemes")

    def test_declared_coverage_shortfall_shape_is_exact(self):
        self.pack["declared_shortfalls"][0]["unsupported"] = True
        self.assertRejected("objects with phonemes")

    def test_emptying_the_limitations_fails(self):
        self.pack["limitations"] = []
        self.assertRejected("limitations may not be emptied")

    def test_removing_the_unreviewed_limitation_fails(self):
        self.pack["limitations"] = [
            line
            for line in self.pack["limitations"]
            if "not professionally reviewed" not in line
        ]
        self.assertRejected("the pack is unreviewed")

    def test_removing_the_union_rule_limitation_fails(self):
        self.pack["limitations"] = [
            line
            for line in self.pack["limitations"]
            if "almost nothing to union" not in line
        ]
        self.assertRejected("the union rule did little here")

    def test_emptying_the_content_screen_fails(self):
        self.pack["content_screen"]["categories_screened_out"] = []
        self.assertRejected("content screen may not be emptied")

    def test_claiming_the_content_screen_is_the_professional_review_fails(self):
        self.pack["content_screen"]["this_is_not_the_review_the_protocol_requires"] = ""
        self.assertRejected("not the cultural")

    def test_emptying_the_unmet_activation_requirements_fails(self):
        self.pack["unmet_activation_requirements"] = []
        self.assertRejected("may not be emptied")

    def test_opening_the_derived_lexicon_boundary_fails(self):
        self.pack["distribution_boundary"]["derived_lexicon_stays_server_side"] = False
        self.assertRejected("may not leave the server")

    def test_dropping_the_required_attribution_fails(self):
        self.pack["distribution_boundary"]["attribution_required"] = []
        self.assertRejected("attributions may not be emptied")

    def test_a_pool_no_larger_than_the_pack_fails(self):
        self.pack["eligible_pool"]["words"] = 20
        self.assertRejected("larger than the pack")

    def test_dropping_a_refusal_reason_from_the_pool_report_fails(self):
        del self.pack["eligible_pool"]["opportunity_refusals_across_the_pool"][
            "unscorable_by_reason"
        ]["post_vocalic_rhotic"]
        self.assertRejected("must read zero rather than be absent")

    def test_a_word_without_an_australian_form_fails(self):
        self.pack["words"][0]["australian_forms"] = 0
        self.assertRejected("no Australian tagged form")

    def test_a_word_chosen_without_a_reason_fails(self):
        self.pack["words"][0]["selection_reason"] = ""
        self.assertRejected("without a recorded reason")

    def test_a_miscounted_total_fails(self):
        self.pack["totals"]["scorable_opportunities"] += 1
        self.assertRejected("miscounts")

    def test_filling_the_onboarding_word_pack_fails(self):
        onboarding = {
            "word_pack": {"stimuli": [{"word": "pumpkin"}], "status": "active"}
        }
        errors = validate_pack(self.pack, onboarding=onboarding)
        self.assertTrue(
            any("may not become the product task" in error for error in errors), errors
        )

    def test_marking_a_scorable_opportunity_syllabic_fails(self):
        # Syllabicity is recorded beside every opportunity so this rule can be
        # re-derived too, rather than being trusted from the reason field.
        self.pack["words"][0]["opportunities"][0]["syllabic"] = True
        self.assertRejected("syllabic_consonant_reduction")

    def test_scoring_a_vowel_fails(self):
        self.pack["words"][0]["opportunities"][0]["phoneme"] = "ə"
        self.assertRejected("not an English")

    def test_pack_identity_version_and_status_are_pinned(self):
        self.pack["pack_id"] = "product_pack"
        self.pack["pack_version"] = "9.0.0"
        self.pack["status"] = "active"
        errors = validate_pack(self.pack)
        self.assertGreaterEqual(sum("must remain" in error for error in errors), 3)

    def test_malformed_nested_values_are_rejected_without_crashing(self):
        mutations = [
            lambda pack: pack["words"][0].update({"word": []}),
            lambda pack: pack["words"][0]["opportunities"][0].update(
                {"position": []}
            ),
            lambda pack: pack["words"][0]["opportunities"][0].update(
                {"state": []}
            ),
            lambda pack: pack["declared_shortfalls"][0].update(
                {"phoneme": []}
            ),
        ]

        for mutation in mutations:
            with self.subTest(mutation=mutation):
                candidate = copy.deepcopy(self.pack)
                mutation(candidate)
                self.assertTrue(validate_pack(candidate))

    def test_unknown_root_word_and_opportunity_fields_fail(self):
        self.pack["unexpected_root"] = True
        self.pack["words"][0]["unexpected_word_field"] = True
        self.pack["words"][0]["opportunities"][0]["unexpected_unit_field"] = True
        errors = validate_pack(self.pack)
        self.assertGreaterEqual(sum("unsupported fields" in error for error in errors), 3)

    def test_opportunity_ids_must_be_contiguous(self):
        self.pack["words"][0]["opportunities"][0]["opportunity"] = 99
        self.assertRejected("contiguous from zero")

    def test_total_opportunities_and_coverage_recompute(self):
        self.pack["totals"]["opportunities"] += 1
        self.pack["coverage"]["p"] = []
        errors = validate_pack(self.pack)
        self.assertTrue(any("total opportunities" in error for error in errors))
        self.assertTrue(any("coverage does not recompute" in error for error in errors))

    def test_refusal_reason_must_follow_the_recorded_context(self):
        for entry in self.pack["words"]:
            for item in entry["opportunities"]:
                if item["state"] == "unscorable":
                    item["reason"] = "dental_fricative_variation"
                    self.assertRejected("does not follow its recorded context")
                    return
        self.fail("the pack carries no refused opportunity")

    def test_onboarding_identity_version_and_review_status_are_pinned(self):
        onboarding = {
            "word_pack": {
                "pack_id": "changed",
                "pack_version": "2.0.0",
                "status": "active",
                "stimuli": [],
            }
        }
        errors = validate_pack(self.pack, onboarding=onboarding)
        self.assertGreaterEqual(
            sum("onboarding pronunciation" in error for error in errors),
            3,
        )


if __name__ == "__main__":
    unittest.main()
