import copy
import json
import tempfile
import unicodedata
import unittest
from pathlib import Path

from speech_sound_patterns.variety_probe import REPORTING_GROUPS, load_contract
from speech_sound_patterns.variety_probe_uncertainty import (
    SpeakerEvidence,
    Term,
    admitted_consonants,
    bca_interval,
    benjamini_hochberg,
    bonferroni,
    bootstrap_replicates,
    build_uncertainty,
    draw_strata,
    jackknife_values,
    load_uncertainty_contract,
    permutation_p_between_groups,
    point_estimate,
)
from speech_sound_patterns.variety_probe_score import (
    CONDITIONED_PALATALS,
    _consonant_rates,
    _speaker_rates,
    build_report,
)
from speech_sound_patterns.variety_probe_validate import (
    REPORT_PATH,
    RETRACTED_FINDINGS,
    SUPERSEDED_REPORT_PATHS,
    validate_report,
)
from speech_sound_patterns.variety_reference import (
    MAPPING_AMENDMENTS,
    MAPPING_VERSION,
    PHONE_SUBSTITUTIONS,
    POST_VOCALIC_RHOTIC_MERGES,
    SCORABLE_CONSONANTS,
    UNSCORABLE_PHONES,
    VarietyReferenceError,
    consonant_targets,
    expected_sequence,
    map_phone,
    merge_post_vocalic_rhotics,
    normalise,
    tokenise,
    vocabulary_index,
)


class VarietyReferenceTests(unittest.TestCase):
    """The reference must refuse to guess, and must say why when it refuses."""

    def setUp(self):
        self.index = vocabulary_index(
            {
                "a": 0, "b": 1, "ð": 2, "l": 3, "t": 4, "ç": 5, "ə": 6,
                "h": 7, "k": 8, "ɡ": 9, "n": 10, "ʔ": 11,
            }
        )

    def test_an_unmappable_phone_fails_closed(self):
        with self.assertRaises(VarietyReferenceError):
            map_phone("ʘ", self.index)

    def test_aligner_machinery_is_never_treated_as_a_sound(self):
        for token in ("spn", "<unk>", "[laughter]"):
            with self.subTest(token=token):
                with self.assertRaises(VarietyReferenceError):
                    map_phone(token, self.index)

    def test_a_precomposed_vocabulary_entry_is_still_found(self):
        # The frozen vocabulary is not written in one normal form. A lookup
        # assuming either form silently drops phones the model actually has.
        # ç was the only precomposed entry English ever reached, and mapping
        # version 1.2.0 now substitutes it, so the index is tested directly
        # rather than through a phone that no longer survives substitution.
        self.assertIsNotNone(self.index.get(normalise("ç")))
        self.assertIsNotNone(self.index.get(normalise(unicodedata.normalize("NFD", "ç"))))

    def test_the_conditioned_palatal_series_can_no_longer_be_expected(self):
        # Mapping version 1.2.0. Every one of these is in the model vocabulary
        # and the model never uses any of them for English, so expecting them
        # flagged at or near 100 percent of opportunities in every group,
        # including the American control. Same defect as dark l, five more times.
        for phone, expected in (
            ("c", "k"), ("cʰ", "k"), ("ɟ", "ɡ"), ("ɲ", "n"), ("ç", "h"), ("ʎ", "l"),
        ):
            with self.subTest(phone=phone):
                self.assertNotIn(phone, SCORABLE_CONSONANTS)
                self.assertEqual(PHONE_SUBSTITUTIONS[phone][0], expected)
                token, _ = map_phone(phone, self.index)
                self.assertEqual(token, expected)

    def test_the_labialised_palatals_no_longer_resolve_to_a_broken_token(self):
        # Before 1.2.0 these pointed at c and ɟ, which are themselves unusable,
        # so the entries inherited the defect instead of fixing it.
        self.assertEqual(PHONE_SUBSTITUTIONS["cʷ"][0], "k")
        self.assertEqual(PHONE_SUBSTITUTIONS["ɟʷ"][0], "ɡ")

    def test_the_glottal_stop_is_excluded_and_never_renamed(self):
        # Coda t glottalling is a real variety difference. Mapping ʔ to t would
        # subtract that difference; excluding the opportunity reports it.
        self.assertIn("ʔ", UNSCORABLE_PHONES)
        self.assertNotIn("ʔ", SCORABLE_CONSONANTS)
        self.assertNotIn("ʔ", PHONE_SUBSTITUTIONS)
        # It still resolves, so the expected sequence stays complete around it.
        token, _ = map_phone("ʔ", self.index)
        self.assertEqual(token, "ʔ")

    def test_an_unscorable_phone_stays_in_the_sequence_but_is_not_a_target(self):
        targets = consonant_targets(["ʔ", "t", "ə"])
        self.assertEqual([item["token"] for item in targets], ["t"])

    def test_post_vocalic_r_merges_into_the_model_s_own_token(self):
        # The dictionary writes arts as two segments; the model has one token
        # and emits it as one unit, so the standalone ɹ owned no frames and was
        # flagged 96.6 percent of the time in every group including the control.
        self.assertEqual(merge_post_vocalic_rhotics(("ɑ", "ɹ", "t", "s")), ("ɑːɹ", "t", "s"))
        # performed carries both r spellings; only the split one changes.
        self.assertEqual(
            merge_post_vocalic_rhotics(("pʰ", "ɚ", "f", "ɒ", "ɹ", "m", "d")),
            ("pʰ", "ɚ", "f", "ɔːɹ", "m", "d"),
        )

    def test_an_onset_r_is_never_merged(self):
        # Onset ɹ is not part of the defect; it flags at about 8 percent and
        # stays a scored target.
        self.assertEqual(merge_post_vocalic_rhotics(("ɹ", "æ", "t")), ("ɹ", "æ", "t"))
        targets = consonant_targets(["ɹ", "æ", "t"])
        self.assertEqual([item["token"] for item in targets], ["ɹ", "t"])

    def test_a_post_vocalic_r_with_no_combined_token_is_unscorable(self):
        # fire: the model has no combined token for a diphthong plus r, so the
        # opportunity is excluded rather than renamed.
        self.assertEqual(merge_post_vocalic_rhotics(("f", "aɪ", "ɹ")), ("f", "aɪ", "ɹ"))
        targets = consonant_targets(["f", "aɪ", "ɹ"])
        self.assertEqual([item["token"] for item in targets], ["f"])

    def test_every_merge_target_is_a_real_model_token(self):
        index = vocabulary_index({t: i for i, t in enumerate(
            ["ɑːɹ", "ɔːɹ", "ɛɹ", "ɪɹ", "ʊɹ"]
        )})
        for (vowel, rhotic), (combined, reason) in POST_VOCALIC_RHOTIC_MERGES.items():
            with self.subTest(pair=(vowel, rhotic)):
                self.assertEqual(rhotic, "ɹ")
                self.assertTrue(reason)
                self.assertIsNotNone(index.get(normalise(combined)))

    def test_a_merge_is_refused_when_the_vocabulary_lacks_the_token(self):
        # Fails closed rather than inventing a token the model does not carry.
        bare = vocabulary_index({"ɑ": 0, "ɹ": 1, "t": 2})
        self.assertEqual(
            merge_post_vocalic_rhotics(("ɑ", "ɹ", "t"), bare), ("ɑ", "ɹ", "t")
        )

    def test_an_unknown_word_refuses_the_whole_prompt(self):
        dictionary = {"the": [("ð", "ə")]}
        sequence, reason = expected_sequence("the zzzz", dictionary, self.index)
        self.assertIsNone(sequence)
        self.assertEqual(reason, "word_not_in_dictionary")

    def test_a_bare_apostrophe_is_not_looked_up_as_a_word(self):
        self.assertEqual(tokenise("'hello,' it's"), ["hello", "it's"])

    def test_only_consonants_become_targets(self):
        targets = consonant_targets(["ð", "ə", "t", "aɪ"])
        self.assertEqual([item["token"] for item in targets], ["ð", "t"])

    def test_dark_l_can_no_longer_be_expected(self):
        # The model never emits it, so expecting it flagged every opportunity.
        self.assertNotIn("ɫ", SCORABLE_CONSONANTS)
        self.assertEqual(PHONE_SUBSTITUTIONS["ɫ"][0], "l")
        self.assertEqual(PHONE_SUBSTITUTIONS["ɫ̩"][0], "l")

    def test_the_dental_stop_maps_to_the_fricative(self):
        # The aligner writes the consonant of "the" as a dental stop; the model
        # uses the fricative, and mapping on symbol shape mis-expected the most
        # frequent consonant context in English.
        self.assertEqual(PHONE_SUBSTITUTIONS["d̪"][0], "ð")

    def test_every_mapping_correction_records_its_evidence(self):
        self.assertEqual(MAPPING_VERSION, "1.2.0")
        self.assertIn(
            "report-mapping-v1.0.0.json", MAPPING_AMENDMENTS["1.1.0"]["prompted_by"]
        )
        self.assertIn(
            "report-mapping-v1.1.0.json", MAPPING_AMENDMENTS["1.2.0"]["prompted_by"]
        )
        # Every correction in every amendment, not only the newest one.
        for version, amendment in MAPPING_AMENDMENTS.items():
            for phone, record in amendment["corrections"].items():
                with self.subTest(version=version, phone=phone):
                    self.assertNotEqual(record["was"], record["now"])
                    self.assertTrue(record["evidence"])
                    self.assertEqual(PHONE_SUBSTITUTIONS[phone][0], record["now"])


class VarietyProbeContractTests(unittest.TestCase):
    def test_the_contract_keeps_every_release_boundary_closed(self):
        contract = load_contract()
        for flag, value in contract["release_boundaries"].items():
            with self.subTest(flag=flag):
                self.assertFalse(value)

    def test_the_contract_declares_its_predictions_before_running(self):
        contract = load_contract()
        predictions = contract["falsifiable_predictions"]
        self.assertTrue(predictions["declared_before_running"])
        self.assertTrue(predictions["under_the_american_reference"])
        self.assertTrue(predictions["under_the_british_reference"])

    def test_the_american_group_is_both_gender_subsets(self):
        self.assertEqual(len(REPORTING_GROUPS["american"]), 2)

    def test_more_than_one_threshold_is_reported(self):
        contract = load_contract()
        self.assertGreater(len(contract["scoring"]["reported_thresholds"]), 1)


class VarietyProbeScoringTests(unittest.TestCase):
    def _record(self, source_id, participant, targets):
        return {
            "source_id": source_id,
            "participant": participant,
            "clip": f"{participant}.mp3",
            "references": {
                "american": {"targets": targets},
                "british": {"targets": targets},
            },
        }

    def test_a_speaker_with_more_clips_cannot_dominate_a_group(self):
        # One loud speaker flagged on everything, one quiet speaker flagged on
        # nothing. Averaging per speaker gives 0.5; pooling opportunities would
        # give 0.9 and would be reporting the first speaker's voice.
        chatty = [
            self._record("common_voice_26_australian_english", "loud", [
                {"index": i, "token": "t", "gop_af_sd": -9.0} for i in range(9)
            ])
        ]
        quiet = [
            self._record("common_voice_26_australian_english", "quiet", [
                {"index": 0, "token": "t", "gop_af_sd": 0.0}
            ])
        ]
        rates = _speaker_rates(chatty + quiet, "american", -1.0)
        self.assertEqual(sorted(rates["australian"]), [0.0, 1.0])

    def test_the_palatal_series_can_be_excluded(self):
        records = [
            self._record("common_voice_26_australian_english", "one", [
                {"index": 0, "token": "ʎ", "gop_af_sd": -9.0},
                {"index": 1, "token": "t", "gop_af_sd": 0.0},
            ])
        ]
        complete = _speaker_rates(records, "american", -1.0)
        without = _speaker_rates(records, "american", -1.0, CONDITIONED_PALATALS)
        self.assertEqual(complete["australian"], [0.5])
        self.assertEqual(without["australian"], [0.0])

    def test_consonant_rates_report_their_own_opportunity_counts(self):
        records = [
            self._record("common_voice_26_british_english", "one", [
                {"index": 0, "token": "ɹ", "gop_af_sd": -9.0},
                {"index": 1, "token": "ɹ", "gop_af_sd": 0.0},
            ])
        ]
        rates = _consonant_rates(records, "american", -1.0)
        self.assertEqual(rates["british"]["ɹ"]["opportunities"], 2)
        self.assertEqual(rates["british"]["ɹ"]["rate"], 0.5)


class VarietyProbeReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))

    def changed(self, update):
        document = copy.deepcopy(self.report)
        update(document)
        return document

    def test_the_committed_report_is_valid(self):
        self.assertEqual(validate_report(self.report), [])

    def test_a_failed_prediction_cannot_be_recorded_as_held(self):
        errors = validate_report(
            self.changed(
                lambda item: item["predictions"].update(
                    {"held_at_every_threshold": True}
                )
            )
        )
        self.assertTrue(any("cannot be reported" in error for error in errors))

    def test_a_release_boundary_cannot_be_opened(self):
        errors = validate_report(
            self.changed(
                lambda item: item["release_boundaries"].update(
                    {"system_selected": True}
                )
            )
        )
        self.assertTrue(any("must stay closed" in error for error in errors))

    def test_a_retracted_finding_cannot_return(self):
        # The rhotic effect and the "repair only declines to score" mechanism
        # were both artifacts of scoring a segment the model never emits.
        for name in RETRACTED_FINDINGS:
            with self.subTest(finding=name):
                errors = validate_report(
                    self.changed(
                        lambda item, name=name: item["findings"].update(
                            {name: {"statement": "it is back"}}
                        )
                    )
                )
                self.assertTrue(any("may not return" in error for error in errors))

    def test_a_material_rhotic_effect_cannot_be_reasserted(self):
        def update(item):
            item["findings"]["the_rhotic_effect_was_a_segmentation_artifact"][
                "rhotic_australian_minus_american_under_the_american_reference"
            ] = 0.03

        errors = validate_report(self.changed(update))
        self.assertTrue(any("has not applied the mapping correction" in e for e in errors))

    def test_a_finding_cannot_lose_the_uncertainty_item_R2_computed(self):
        """The requirement inverted at item R2 and must stay inverted.

        Before R2 these two findings had to record their uncertainty as absent.
        Now that it exists, a regeneration that drops it would be describing a
        movement of a fifth of a percentage point as though its size were known.
        """
        for name in (
            "the_t_effect_survives_the_correction",
            "the_reference_swap_no_longer_moves_the_control_group",
        ):
            with self.subTest(finding=name):
                errors = validate_report(
                    self.changed(
                        lambda item, name=name: item["findings"][name].update(
                            {"uncertainty_state": "not_computed"}
                        )
                    )
                )
                self.assertTrue(any("carried no uncertainty" in e for e in errors))

    def test_a_report_built_on_the_superseded_mapping_is_refused(self):
        errors = validate_report(
            self.changed(lambda item: item.update({"phone_mapping_version": "1.1.0"}))
        )
        self.assertTrue(any("superseded" in error for error in errors))

    def test_every_superseded_report_no_longer_validates(self):
        for path in SUPERSEDED_REPORT_PATHS:
            with self.subTest(report=path.name):
                superseded = json.loads(path.read_text(encoding="utf-8"))
                self.assertTrue(validate_report(superseded))

    def test_the_limits_of_the_measurement_cannot_be_deleted(self):
        for field in ("declared_confounds", "what_this_cannot_establish"):
            with self.subTest(field=field):
                errors = validate_report(
                    self.changed(lambda item, field=field: item.update({field: []}))
                )
                self.assertTrue(errors)

    def test_every_required_finding_is_retained(self):
        errors = validate_report(
            self.changed(
                lambda item: item["findings"].pop(
                    "the_rhotic_effect_was_a_segmentation_artifact"
                )
            )
        )
        self.assertTrue(any("must retain" in error for error in errors))

    def test_the_report_rebuilds_from_the_private_evidence(self):
        """Findings must be a pure function of the evidence and the uncertainty.

        The committed uncertainty block is fed back in rather than recomputed,
        so this checks the prose and the derived fields, not the resampler.
        `VarietyProbeUncertaintyTests` checks the resampler separately.
        """
        try:
            rebuilt = build_report(uncertainty=self.report["uncertainty"])
        except Exception as error:  # noqa: BLE001
            self.skipTest(f"private probe evidence is not on this machine: {error}")
        self.assertEqual(rebuilt["analyses"], self.report["analyses"])
        self.assertEqual(rebuilt["findings"], self.report["findings"])

    def test_a_report_cannot_be_built_without_uncertainty(self):
        with self.assertRaises(Exception):
            build_report(uncertainty=None)


class VarietyProbeUncertaintyTests(unittest.TestCase):
    """The statistics, checked against cases whose answer is known in advance."""

    THRESHOLDS = (-1.0,)

    def evidence(self, plan):
        """Build probe evidence in the stored shape, from a compact plan.

        `plan` maps a source id to a list of speakers, each a list of clips,
        each a list of (token, american score, british score).
        """
        records = []
        for source_id, speakers in plan.items():
            for number, clips in enumerate(speakers):
                for index, clip in enumerate(clips):
                    records.append(
                        {
                            "source_id": source_id,
                            "participant": f"{source_id}_{number:04d}",
                            "clip": f"{number:04d}_{index}.mp3",
                            "references": {
                                "american": {
                                    "targets": [
                                        {"token": token, "gop_af_sd": american}
                                        for token, american, _ in clip
                                    ]
                                },
                                "british": {
                                    "targets": [
                                        {"token": token, "gop_af_sd": british}
                                        for token, _, british in clip
                                    ]
                                },
                            },
                        }
                    )
        return SpeakerEvidence(records, self.THRESHOLDS)

    def separated(self, flagged_group_size=40, clean_group_size=40):
        """One group always flagged, the other never. The answer is plus one."""
        flagged = [[[("t", -5.0, -5.0)]] for _ in range(flagged_group_size)]
        clean = [[[("t", 5.0, 5.0)]] for _ in range(clean_group_size)]
        half = clean_group_size // 2
        return self.evidence(
            {
                "common_voice_26_australian_english": flagged,
                "common_voice_26_american_english_male": clean[:half],
                "common_voice_26_american_english_female": clean[half:],
            }
        )

    def contrast_terms(self, evidence, left="australian", right="american"):
        values, present = evidence.speaker_rates("american", -1.0)
        return [Term(1, left, values, present), Term(-1, right, values, present)]

    # -- the engine ------------------------------------------------------

    def test_a_real_difference_produces_an_interval_clear_of_zero(self):
        evidence = self.separated()
        terms = self.contrast_terms(evidence)
        strata = draw_strata(evidence, 500, "test")
        observed = point_estimate(terms, evidence)
        self.assertAlmostEqual(observed, 1.0)
        interval = bca_interval(
            observed, bootstrap_replicates(terms, strata),
            jackknife_values(terms, evidence),
        )
        self.assertGreater(interval["low"], 0.0)

    def test_no_difference_produces_an_interval_containing_zero(self):
        speakers = [[[("t", -5.0, -5.0)]] for _ in range(40)]
        evidence = self.evidence(
            {
                "common_voice_26_australian_english": speakers[:20],
                "common_voice_26_american_english_male": speakers[20:30],
                "common_voice_26_american_english_female": speakers[30:],
            }
        )
        terms = self.contrast_terms(evidence)
        strata = draw_strata(evidence, 500, "test")
        observed = point_estimate(terms, evidence)
        interval = bca_interval(
            observed, bootstrap_replicates(terms, strata),
            jackknife_values(terms, evidence),
        )
        self.assertLessEqual(interval["low"], 0.0)
        self.assertGreaterEqual(interval["high"], 0.0)

    def test_two_clips_by_one_contributor_are_one_cluster(self):
        """The whole point of speaker clustering, checked rather than assumed."""
        one_clip = [[[("t", -5.0, -5.0)]] for _ in range(10)]
        many_clips = [[[("t", -5.0, -5.0)]] * 8 for _ in range(10)]
        for plan in (one_clip, many_clips):
            evidence = self.evidence(
                {"common_voice_26_australian_english": plan}
            )
            self.assertEqual(len(evidence.group_members("australian")), 10)

    def test_resampling_never_leaves_its_own_source(self):
        evidence = self.separated()
        strata = draw_strata(evidence, 50, "test")
        for source, drawn in strata.items():
            members = set(evidence.source_members(source).tolist())
            self.assertEqual(drawn.shape[1], len(members))
            self.assertTrue(set(drawn.ravel().tolist()) <= members)

    def test_the_same_seed_reproduces_the_same_resample(self):
        evidence = self.separated()
        first = draw_strata(evidence, 50, "same")
        second = draw_strata(evidence, 50, "same")
        other = draw_strata(evidence, 50, "different")
        source = "common_voice_26_australian_english"
        self.assertTrue((first[source] == second[source]).all())
        self.assertFalse((first[source] == other[source]).all())

    def test_a_permutation_p_value_can_never_be_zero(self):
        evidence = self.separated()
        values, present = evidence.speaker_rates("american", -1.0)
        result = permutation_p_between_groups(
            evidence, values, present, "australian", "american", 200, "test"
        )
        self.assertGreater(result["p_value"], 0.0)
        self.assertLess(result["p_value"], 0.05)

    def test_an_identical_pair_of_groups_is_never_significant(self):
        speakers = [[[("t", -5.0, -5.0)]] for _ in range(40)]
        evidence = self.evidence(
            {
                "common_voice_26_australian_english": speakers[:20],
                "common_voice_26_american_english_male": speakers[20:30],
                "common_voice_26_american_english_female": speakers[30:],
            }
        )
        values, present = evidence.speaker_rates("american", -1.0)
        result = permutation_p_between_groups(
            evidence, values, present, "australian", "american", 200, "test"
        )
        self.assertGreater(result["p_value"], 0.05)

    def test_a_speaker_with_no_opportunity_is_absent_and_never_a_zero(self):
        evidence = self.evidence(
            {
                "common_voice_26_australian_english": [
                    [[("t", -5.0, -5.0)]],
                    [[("s", -5.0, -5.0)]],
                ]
            }
        )
        _, present = evidence.token_rates("american", -1.0, "t")
        self.assertEqual(int(present.sum()), 1)

    def test_the_corrections_behave_as_their_definitions_require(self):
        raw = [0.001, 0.01, 0.03, 0.04, 0.2]
        adjusted = benjamini_hochberg(raw)
        strict = bonferroni(raw)
        self.assertEqual(len(adjusted), len(raw))
        for index in range(len(raw)):
            self.assertGreaterEqual(adjusted[index] + 1e-12, raw[index])
            self.assertGreaterEqual(strict[index] + 1e-12, adjusted[index])
        self.assertTrue(all(value <= 1.0 for value in strict))
        # Step up monotonicity: a larger raw p can never adjust to a smaller one.
        ordered = [adjusted[index] for index in sorted(range(len(raw)), key=raw.__getitem__)]
        self.assertEqual(ordered, sorted(ordered))

    def test_a_lone_test_is_not_penalised_by_a_correction(self):
        self.assertAlmostEqual(float(benjamini_hochberg([0.02])[0]), 0.02)
        self.assertAlmostEqual(float(bonferroni([0.02])[0]), 0.02)

    def test_the_inclusion_rule_refuses_a_thin_consonant(self):
        contract = load_uncertainty_contract()
        plenty = [[[("t", -5.0, -5.0)] * 4] for _ in range(60)]
        thin = [[[("t", -5.0, -5.0)] * 4, [("ʒ", -5.0, -5.0)]] for _ in range(60)]
        evidence = self.evidence(
            {
                "common_voice_26_australian_english": thin,
                "common_voice_26_american_english_male": plenty[:30],
                "common_voice_26_american_english_female": plenty[30:],
            }
        )
        admitted, untested = admitted_consonants(
            evidence, contract, "australian_minus_american"
        )
        self.assertIn("t", admitted)
        self.assertNotIn("ʒ", admitted)
        self.assertIn("ʒ", untested)

    # -- the committed record --------------------------------------------

    def test_the_committed_points_reproduce_from_the_evidence(self):
        """Point estimates do not depend on the resample, so they must match."""
        report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        try:
            recomputed = build_uncertainty(resamples=200, permutations=200)
        except Exception as error:  # noqa: BLE001
            self.skipTest(f"private probe evidence is not on this machine: {error}")
        committed = report["uncertainty"]["group_level"]["-1.0"]
        fresh = recomputed["group_level"]["-1.0"]
        for group in ("australian", "british"):
            self.assertEqual(
                fresh["differential_against_the_american_group"]["american"][group][
                    "point"
                ],
                committed["differential_against_the_american_group"]["american"][group][
                    "point"
                ],
            )

    def test_the_declared_families_are_the_committed_families(self):
        report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        families = report["uncertainty"]["families"]
        self.assertTrue(families["declared_before_computing"])
        self.assertGreater(
            families["S_sceptical_sensitivity"]["tests"],
            families["A_primary_per_consonant"]["tests"]
            + families["B_secondary_per_consonant"]["tests"],
        )
        for row in families["A_primary_per_consonant"]["members"]:
            self.assertTrue(row["name"].endswith("_american_reference_at_-1.0"))

    def test_the_one_surviving_result_is_the_only_one(self):
        report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        families = report["uncertainty"]["families"]
        self.assertEqual(families["G_pre_registered_group_level"]["survivors_uncorrected"], [])
        self.assertEqual(families["A_primary_per_consonant"]["survivors_benjamini_hochberg"], [])
        self.assertEqual(
            families["B_secondary_per_consonant"]["survivors_bonferroni"],
            ["british_minus_american_ð_american_reference_at_-1.0"],
        )


class VarietyProbeUncertaintyValidatorTests(unittest.TestCase):
    """Each check here guards a sentence that would be flattering if edited."""

    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))

    def changed(self, update):
        document = copy.deepcopy(self.report)
        update(document)
        return validate_report(document)

    def test_a_failed_consonant_cannot_be_recorded_as_surviving(self):
        errors = self.changed(
            lambda item: item["findings"][
                "the_t_differential_does_not_survive_correction"
            ].update({"survives_benjamini_hochberg": True})
        )
        self.assertTrue(any("does not survive correction" in e for e in errors))

    def test_a_group_level_survivor_cannot_be_invented(self):
        errors = self.changed(
            lambda item: item["findings"][
                "nothing_at_group_level_is_distinguishable_from_zero"
            ].update({"survivors_benjamini_hochberg": ["anything"]})
        )
        self.assertTrue(any("no group level comparison survived" in e for e in errors))

    def test_a_survivor_list_must_match_its_own_members(self):
        errors = self.changed(
            lambda item: item["uncertainty"]["families"][
                "A_primary_per_consonant"
            ].update({"survivors_benjamini_hochberg": ["australian_minus_american_t_american_reference_at_-1.0"]})
        )
        self.assertTrue(any("its own members do not support" in e for e in errors))

    def test_a_family_cannot_be_widened_after_the_fact(self):
        def widen(item):
            family = item["uncertainty"]["families"]["A_primary_per_consonant"]
            extra = copy.deepcopy(family["members"][0])
            extra["name"] = "australian_minus_american_t_british_reference_at_-1.0"
            family["members"].append(extra)
            family["tests"] += 1

        errors = self.changed(widen)
        self.assertTrue(any("widens it after the fact" in e for e in errors))

    def test_the_family_declaration_cannot_be_backdated_away(self):
        errors = self.changed(
            lambda item: item["uncertainty"]["families"].update(
                {"declared_before_computing": False}
            )
        )
        self.assertTrue(any("declared before they were" in e for e in errors))

    def test_a_correction_cannot_be_dropped_from_the_report(self):
        errors = self.changed(
            lambda item: item["uncertainty"]["method"].update(
                {"corrections": ["benjamini_hochberg"]}
            )
        )
        self.assertTrue(any("all three corrections" in e for e in errors))

    def test_the_uncertainty_cannot_be_recomputed_on_too_few_resamples(self):
        errors = self.changed(
            lambda item: item["uncertainty"]["method"].update({"resamples": 50})
        )
        self.assertTrue(any("may not fall below 1000" in e for e in errors))

    def test_pooling_tokens_again_is_refused(self):
        errors = self.changed(
            lambda item: item["uncertainty"]["method"].update(
                {"unit_of_analysis": "the token"}
            )
        )
        self.assertTrue(any("unit of analysis is the speaker" in e for e in errors))

    def test_the_surviving_result_keeps_its_confound(self):
        errors = self.changed(
            lambda item: item["findings"][
                "one_per_consonant_result_survives_correction_and_it_is_british"
            ].update({"statement": "British speakers are flagged more often on this sound."})
        )
        self.assertTrue(any("disjoint prompts" in e for e in errors))

    def test_the_lineage_overlap_cannot_be_declared_resolved(self):
        errors = self.changed(
            lambda item: item["uncertainty"]["training_lineage_declaration"].update(
                {"resolution": "resolved"}
            )
        )
        self.assertTrue(any("declared and not" in e for e in errors))

    def test_a_null_cannot_be_published_without_its_detectable_effect(self):
        errors = self.changed(lambda item: item["uncertainty"].pop("detectable_effect"))
        self.assertTrue(any("too small to tell" in e for e in errors))

    def test_a_report_without_uncertainty_is_refused(self):
        errors = self.changed(lambda item: item.pop("uncertainty"))
        self.assertTrue(any("missing uncertainty" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
