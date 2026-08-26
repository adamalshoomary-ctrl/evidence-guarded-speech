import copy
import json
import unittest

from speech_sound_patterns.benchmark import load_phone_map
from speech_sound_patterns.comparison import (
    ADULT_SCORABLE_COUNTS,
    CANDIDATE_PROFILES,
    COMPARISON_REPORT_PATH,
    ComparisonError,
    FROZEN_SELECTION_GATES,
    assert_valid_comparison_contract,
    average_precision,
    azure_word_alignment,
    candidate_inventory,
    candidate_thresholds,
    coverage_record,
    free_phone_target_states,
    load_comparison_contract,
    load_relation_rows,
    normalized_ipa,
    partition_metrics,
    predictions_at_threshold,
    reference_ipa_string,
    threshold_search,
    validate_comparison_contract,
    validate_comparison_report,
    verify_frozen_inputs,
)
from speech_sound_patterns.benchmark_repair import REPAIR_REPORT_PATH

from tests.research_data import (
    needs_repository_history,
    needs_research_data,
)


def _rows(scores_and_labels):
    rows = []
    for index, (score, label) in enumerate(scores_and_labels):
        rows.append(
            {
                "safe_id": f"so_{index:06d}",
                "private_participant_id": "p1",
                "word_index": 0,
                "target_index": index,
                "state": "scored" if score is not None else "abstain",
                "abstention_reason": None if score is not None else "test",
                "concern_score": score,
                "label": label,
                "truth": "positive" if label == 1 else "negative",
            }
        )
    return rows


class ComparisonContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = load_comparison_contract()

    def changed(self, update):
        result = copy.deepcopy(self.contract)
        update(result)
        return result

    def test_committed_contract_is_valid(self):
        self.assertEqual(validate_comparison_contract(self.contract), [])

    @needs_research_data
    def test_frozen_private_inputs_are_unchanged(self):
        verify_frozen_inputs()

    def test_contract_was_declared_before_any_run(self):
        self.assertIs(self.contract["declared_before_any_run"], True)
        self.assertEqual(
            self.contract["status"], "rules_frozen_before_any_lane_scoring"
        )

    def test_gates_match_the_frozen_twenty_two_d_values(self):
        for field, expected in FROZEN_SELECTION_GATES.items():
            self.assertEqual(self.contract["selection_gates"][field], expected)

    def test_a_weakened_gate_is_rejected(self):
        for field in FROZEN_SELECTION_GATES:
            document = self.changed(
                lambda item, field=field: item["selection_gates"].__setitem__(
                    field, 0.0
                )
            )
            self.assertIn(
                f"selection_gates.{field} changed",
                validate_comparison_contract(document),
            )

    def test_held_out_access_cannot_be_enabled(self):
        document = self.changed(
            lambda item: item["input_policy"].__setitem__(
                "held_out_access_allowed", True
            )
        )
        self.assertIn(
            "input_policy.held_out_access_allowed must remain false",
            validate_comparison_contract(document),
        )

    def test_child_rows_cannot_reach_a_threshold(self):
        document = self.changed(
            lambda item: item["input_policy"].__setitem__(
                "child_rows_used_for_selection_or_thresholds", True
            )
        )
        self.assertIn(
            "input_policy.child_rows_used_for_selection_or_thresholds must "
            "remain false",
            validate_comparison_contract(document),
        )

    def test_a_candidate_cannot_be_added(self):
        document = self.changed(
            lambda item: item["candidates"].append(
                {"candidate_id": "an_unapproved_lane"}
            )
        )
        self.assertIn(
            "'an_unapproved_lane' is not a candidate the approved plan permits",
            validate_comparison_contract(document),
        )

    def test_a_candidate_cannot_be_dropped(self):
        document = self.changed(lambda item: item["candidates"].pop())
        self.assertTrue(
            any(
                error.startswith("comparison contract is missing candidates")
                for error in validate_comparison_contract(document)
            )
        )

    def test_supporting_only_candidate_cannot_become_selection_eligible(self):
        def promote(item):
            for candidate in item["candidates"]:
                if candidate["candidate_id"] == (
                    "wav2vec2_commonphone_free_phone_relation"
                ):
                    candidate["selection_eligible"] = True

        errors = validate_comparison_contract(self.changed(promote))
        self.assertTrue(
            any("selection_eligible" in error for error in errors), errors
        )

    def test_child_and_australian_transmission_stay_false(self):
        for field in (
            "child_strata_transmitted",
            "held_out_clips_transmitted",
            "owner_or_personal_audio_transmitted",
            "australian_common_voice_transmitted",
        ):
            document = self.changed(
                lambda item, field=field: item[
                    "external_transmission_policy"
                ].__setitem__(field, True)
            )
            self.assertIn(
                f"external_transmission_policy.{field} must remain false",
                validate_comparison_contract(document),
            )

    def test_release_boundaries_cannot_open(self):
        document = self.changed(
            lambda item: item["release_boundaries"].__setitem__(
                "normal_pipeline", True
            )
        )
        self.assertIn(
            "every comparison release boundary must remain false",
            validate_comparison_contract(document),
        )

    def test_no_selection_must_remain_a_valid_outcome(self):
        document = self.changed(
            lambda item: item["acceptance"].__setitem__(
                "documented_no_selection_is_a_valid_outcome", False
            )
        )
        self.assertIn(
            "a documented no-selection must remain a valid outcome",
            validate_comparison_contract(document),
        )

    def test_assert_raises_on_an_invalid_contract(self):
        document = self.changed(lambda item: item.pop("selection_gates"))
        with self.assertRaises(ComparisonError):
            assert_valid_comparison_contract(document)


@needs_research_data
class FrozenMetricReproductionTests(unittest.TestCase):
    """The 22E4 metric path must be the 22D metric path, not a lookalike.

    The private relation evidence still carries the checkpoint 22D greedy
    PhoneticXEUS prediction for every target. Scoring those predictions through
    this checkpoint's own code must reproduce the committed 22D report exactly.
    If it ever does not, the new code has quietly redefined precision, recall,
    a denominator or an abstention, and no later comparison could be trusted.
    """

    @classmethod
    def setUpClass(cls):
        cls.rows = load_relation_rows()
        cls.report = json.loads(REPAIR_REPORT_PATH.read_text(encoding="utf-8"))
        cls.frozen = next(
            item
            for item in cls.report["candidate_comparisons"]
            if item["candidate_id"] == "frozen_greedy_phoneticxeus"
        )["closest_reported_operating_point"]

    def adults(self, split):
        return [
            row
            for row in self.rows
            if row["project_split"] == split and row["age_stratum"] == "adult"
        ]

    def test_adult_opportunity_counts_are_unchanged(self):
        for split, expected in ADULT_SCORABLE_COUNTS.items():
            metrics = partition_metrics(self.adults(split))
            self.assertEqual(metrics["reference_scorable"], expected)

    def test_greedy_baseline_reproduces_the_committed_report(self):
        for split, key in (
            ("development", "development"),
            ("threshold_tuning", "threshold_tuning"),
        ):
            metrics = partition_metrics(self.adults(split))
            expected = self.frozen[key]
            for field in (
                "true_positive",
                "false_positive",
                "false_negative",
                "true_negative",
                "reference_scorable",
            ):
                self.assertEqual(metrics[field], expected[field], f"{split}.{field}")
            for field in (
                "precision",
                "recall",
                "false_concerns_per_scorable_opportunity",
            ):
                self.assertEqual(
                    metrics[field]["value"],
                    expected[field]["value"],
                    f"{split}.{field}",
                )
                self.assertEqual(
                    metrics[field]["wilson_95_percent"],
                    expected[field]["wilson_95_percent"],
                    f"{split}.{field} interval",
                )

    def test_greedy_baseline_fails_the_frozen_gates(self):
        for split in ADULT_SCORABLE_COUNTS:
            metrics = partition_metrics(self.adults(split))
            self.assertFalse(metrics["selection_gates"]["passed"])

    def test_unscorable_rows_never_enter_a_denominator(self):
        development = self.adults("development")
        unscorable = sum(1 for row in development if row["truth"] == "unscorable")
        metrics = partition_metrics(development)
        self.assertEqual(unscorable, 84)
        self.assertEqual(metrics["unscorable_reference"], unscorable)
        self.assertEqual(
            metrics["reference_scorable"] + unscorable,
            metrics["total_opportunities"],
        )


class ThresholdProcedureTests(unittest.TestCase):
    def test_threshold_grid_includes_an_empty_positive_set(self):
        rows = _rows([(0.1, 0), (0.9, 1)])
        thresholds = candidate_thresholds(rows)
        self.assertEqual(thresholds[:2], [0.1, 0.9])
        self.assertGreater(thresholds[-1], 0.9)
        empty = predictions_at_threshold(rows, thresholds[-1])
        self.assertTrue(all(row["prediction"] == "negative" for row in empty))

    def test_abstained_rows_stay_out_of_the_confusion_but_count_as_opportunities(
        self,
    ):
        rows = _rows([(None, 1), (0.9, 1), (0.1, 0)])
        metrics = partition_metrics(predictions_at_threshold(rows, 0.5))
        self.assertEqual(metrics["reference_scorable"], 3)
        self.assertEqual(metrics["abstained"], 1)
        self.assertEqual(metrics["true_positive"], 1)
        self.assertEqual(metrics["recall"]["denominator"], 1)
        self.assertEqual(
            metrics["false_concerns_per_scorable_opportunity"]["denominator"], 3
        )

    def test_selection_requires_both_partitions_to_pass(self):
        strong = _rows([(0.9, 1)] * 10 + [(0.1, 0)] * 990)
        weak = _rows([(0.9, 1)] * 2 + [(0.9, 0)] * 50 + [(0.1, 0)] * 948)
        result = threshold_search(strong, weak)
        self.assertIsNone(result["selected"])
        self.assertIsNotNone(result["closest"])

    def test_selection_picks_the_highest_tuning_recall_that_passes(self):
        rows = _rows([(0.9, 1)] * 12 + [(0.5, 1)] * 4 + [(0.1, 0)] * 1000)
        result = threshold_search(rows, rows)
        self.assertIsNotNone(result["selected"])
        self.assertEqual(result["selected"]["threshold"], 0.5)

    def test_closest_point_is_never_a_selection(self):
        rows = _rows([(0.9, 1), (0.9, 0), (0.1, 0)])
        result = threshold_search(rows, rows)
        self.assertIsNone(result["selected"])
        self.assertIn("threshold", result["closest"])

    def test_average_precision_is_perfect_when_positives_rank_first(self):
        rows = _rows([(0.9, 1), (0.8, 1), (0.1, 0), (0.0, 0)])
        self.assertEqual(average_precision(rows), 1.0)

    def test_average_precision_is_none_without_a_positive(self):
        self.assertIsNone(average_precision(_rows([(0.9, 0)])))


class AlignmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.phone_map = load_phone_map()
        cls.inventory = candidate_inventory(cls.phone_map)

    def clip(self):
        return {
            "reference_phones": ["S", "IH0", "T"],
            "word_starts": [0],
        }

    def test_matching_free_phone_output_raises_no_concern(self):
        states = free_phone_target_states(
            self.clip(), ["s", "ɪ", "t"], self.phone_map, self.inventory
        )
        self.assertEqual(states[0]["state"], "no_relation_candidate")
        self.assertEqual(states[2]["state"], "no_relation_candidate")

    def test_substituted_free_phone_output_raises_a_concern(self):
        states = free_phone_target_states(
            self.clip(), ["ʃ", "ɪ", "t"], self.phone_map, self.inventory
        )
        self.assertEqual(states[0]["state"], "coarse_relation_candidate")
        self.assertEqual(states[0]["observed_phone"], "ʃ")

    def test_out_of_inventory_token_abstains_instead_of_inventing_a_relation(self):
        states = free_phone_target_states(
            self.clip(), ["ʂ", "ɪ", "t"], self.phone_map, self.inventory
        )
        self.assertEqual(states[0]["state"], "abstain")
        self.assertEqual(states[0]["reason"], "out_of_inventory_candidate_token")

    def test_vowel_targets_are_never_scored(self):
        states = free_phone_target_states(
            self.clip(), ["s", "æ", "t"], self.phone_map, self.inventory
        )
        self.assertEqual(states[1]["state"], "abstain")

    def test_provider_alignment_matches_identical_reference_phones(self):
        matched = azure_word_alignment(
            ["DH", "AE1", "T"], ["ð", "æ", "t"], self.phone_map
        )
        self.assertEqual(matched, {0: 0, 1: 1, 2: 2})

    def test_provider_alignment_abstains_when_the_lexicons_disagree(self):
        matched = azure_word_alignment(
            ["K", "AA1", "R"], ["k", "ɑ"], self.phone_map
        )
        self.assertNotIn(2, matched)

    def test_empty_provider_phone_names_never_match(self):
        matched = azure_word_alignment(
            ["DH", "AE1", "T"], ["", "", ""], self.phone_map
        )
        self.assertEqual(matched, {})

    def test_tie_bars_and_length_marks_do_not_block_a_match(self):
        self.assertEqual(normalized_ipa("d͡ʒ"), reference_ipa_string("JH", self.phone_map))
        self.assertEqual(normalized_ipa("iː"), "i")

    def test_coverage_record_reports_every_abstention_reason(self):
        rows = _rows([(0.5, 0), (None, 1)])
        record = coverage_record(rows)
        self.assertEqual(record["reference_scorable_opportunities"], 2)
        self.assertEqual(record["scored"], 1)
        self.assertEqual(record["abstention_reasons"], {"test": 1})

    def test_unscorable_reference_rows_leave_coverage_and_ranking(self):
        rows = _rows([(0.9, 1), (0.1, 0)])
        rows.append({**rows[0], "truth": "unscorable", "label": 0, "concern_score": 0.5})
        self.assertEqual(coverage_record(rows)["reference_scorable_opportunities"], 2)
        # The disputed row would otherwise rank as a negative between the two
        # real rows and quietly depress average precision.
        self.assertEqual(average_precision(rows), 1.0)
        self.assertNotIn(0.5, candidate_thresholds(rows))


class ComparisonReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(
            COMPARISON_REPORT_PATH.read_text(encoding="utf-8")
        )

    def changed(self, update):
        result = copy.deepcopy(self.report)
        update(result)
        return result

    def candidate(self, report, candidate_id):
        return next(
            item
            for item in report["candidates"]
            if item["candidate_id"] == candidate_id
        )

    def test_committed_report_is_valid(self):
        self.assertEqual(validate_comparison_report(self.report), [])

    def test_report_carries_every_approved_candidate(self):
        self.assertEqual(
            {item["candidate_id"] for item in self.report["candidates"]},
            set(CANDIDATE_PROFILES),
        )

    def test_report_gates_match_the_frozen_values(self):
        for field, expected in FROZEN_SELECTION_GATES.items():
            self.assertEqual(self.report["selection_gates"][field], expected)

    def test_a_weakened_reported_gate_is_rejected(self):
        document = self.changed(
            lambda item: item["selection_gates"].__setitem__(
                "minimum_precision_point_estimate", 0.6
            )
        )
        self.assertIn(
            "comparison report selection_gates.minimum_precision_point_estimate "
            "changed",
            validate_comparison_report(document),
        )

    def test_no_candidate_may_claim_a_pass_it_did_not_earn(self):
        def forge(item):
            candidate = self.candidate(item, "sfgop_af_sd")
            candidate["reported_operating_point"]["is_a_selection"] = True

        self.assertIn(
            "sfgop_af_sd: an operating point cannot be a selection unless both "
            "partitions passed",
            validate_comparison_report(self.changed(forge)),
        )

    def test_decision_must_match_the_candidate_outcomes(self):
        def forge(item):
            item["decision"]["decision"] = "candidates_passed_every_unchanged_gate"
            item["decision"]["candidates_passing_every_unchanged_gate"] = [
                "sfgop_af_sd"
            ]

        errors = validate_comparison_report(self.changed(forge))
        self.assertIn(
            "the decision does not match the reported candidate outcomes", errors
        )

    def test_a_selection_cannot_be_recorded_in_this_checkpoint(self):
        document = self.changed(
            lambda item: item["decision"].__setitem__(
                "selection_recorded_in_this_checkpoint", True
            )
        )
        self.assertIn(
            "checkpoint 22E4 measures; the selection record is 22E5",
            validate_comparison_report(document),
        )

    def test_supporting_only_candidate_carries_no_gate_result(self):
        candidate = self.candidate(
            self.report, "wav2vec2_commonphone_free_phone_relation"
        )
        self.assertIs(candidate["gates_evaluated"], False)
        self.assertIsNone(candidate["any_operating_point_passes_both_partitions"])
        point = candidate["reported_operating_point"]
        self.assertNotIn("selection_gates", point["development"])
        self.assertNotIn("selection_gates", point["threshold_tuning"])

    def test_a_prohibited_provider_score_cannot_appear(self):
        document = self.changed(
            lambda item: item["candidates"][0].__setitem__("PronScore", 91.0)
        )
        self.assertIn(
            "PronScore is a prohibited output class and cannot be reported",
            validate_comparison_report(document),
        )

    def test_private_row_level_evidence_cannot_appear(self):
        document = self.changed(
            lambda item: item["candidates"][0].__setitem__("safe_id", "so_000001")
        )
        self.assertIn(
            "comparison report contains private or row-level evidence",
            validate_comparison_report(document),
        )

    def test_report_records_no_selection(self):
        self.assertEqual(self.report["decision"]["decision"], "no_selection")
        self.assertEqual(
            self.report["decision"]["candidates_passing_every_unchanged_gate"], []
        )
        self.assertIs(
            self.report["decision"]["no_selection_is_a_valid_completed_outcome"],
            True,
        )

    def test_australian_locale_produced_no_scorable_evidence(self):
        candidate = self.candidate(self.report, "azure_en_au_phone_score")
        self.assertIs(candidate["evidence_available"], False)
        self.assertIsNone(candidate["reported_operating_point"])
        for partition in ("development_adult", "threshold_tuning_adult"):
            self.assertEqual(candidate["coverage"][partition]["scored"], 0)
        self.assertIs(
            self.report["decision"][
                "australian_variety_exact_relation_evidence_available"
            ],
            False,
        )

    def test_no_child_or_held_out_clip_was_transmitted(self):
        transmission = self.report["external_transmission"]
        self.assertIs(transmission["child_strata_transmitted"], False)
        self.assertIs(transmission["held_out_clips_transmitted"], False)
        self.assertIs(transmission["owner_or_personal_audio_transmitted"], False)
        self.assertIs(transmission["australian_common_voice_transmitted"], False)

    def test_every_denominator_is_visible(self):
        for candidate in self.report["candidates"]:
            point = candidate["reported_operating_point"]
            if point is None:
                continue
            for partition in ("development", "threshold_tuning"):
                metrics = point[partition]
                self.assertIn("reference_scorable", metrics)
                self.assertEqual(
                    metrics["reference_scorable"],
                    ADULT_SCORABLE_COUNTS[
                        "development"
                        if partition == "development"
                        else "threshold_tuning"
                    ],
                )
                for name in ("precision", "recall"):
                    self.assertIn("denominator", metrics[name])

    def test_release_boundaries_are_all_closed(self):
        self.assertTrue(
            all(value is False for value in self.report["release_boundaries"].values())
        )


class CandidateRoleTests(unittest.TestCase):
    def test_only_azure_and_the_local_lanes_carry_candidates(self):
        self.assertEqual(
            {profile["lane_id"] for profile in CANDIDATE_PROFILES.values()},
            {
                "segmentation_free_gop",
                "powsm",
                "azure_speech",
                "wav2vec2_commonphone",
            },
        )

    def test_the_australian_locale_can_never_be_exact_relation_capable(self):
        contract = load_comparison_contract()
        australian = next(
            candidate
            for candidate in contract["candidates"]
            if candidate["candidate_id"] == "azure_en_au_phone_score"
        )
        self.assertIs(australian["exact_relation_capable"], False)
        self.assertIn("empty string", australian["locale_limitation"])


if __name__ == "__main__":
    unittest.main()
