import copy
import json
import unittest
from pathlib import Path

from speech_sound_patterns.benchmark import (
    BenchmarkValidationError,
    align_phone_sequences,
    contains_private_material,
    expand_reference_phones,
    insertion_consensus,
    insertion_predictions,
    load_benchmark_contract,
    load_phone_map,
    parse_review_phone_string,
    reviewer_agreement,
    score_binary_rows,
    target_consensus,
    target_predictions,
    validate_benchmark_contract,
    validate_phone_map,
    validate_safe_benchmark_report,
    wilson_interval,
)


class SpeechSoundBenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = load_benchmark_contract()
        cls.phone_map = load_phone_map()

    def changed_contract(self, update):
        result = copy.deepcopy(self.contract)
        update(result)
        return result

    def changed_phone_map(self, update):
        result = copy.deepcopy(self.phone_map)
        update(result)
        return result

    def safe_report(self):
        path = (
            Path(__file__).parents[1]
            / "speech_sound_patterns"
            / "local-benchmark-v1.0.0.json"
        )
        return json.loads(path.read_text(encoding="utf-8"))

    def test_frozen_contract_and_phone_map_validate(self):
        self.assertEqual(validate_benchmark_contract(self.contract), [])
        self.assertEqual(validate_phone_map(self.phone_map), [])

    def test_held_out_or_release_mutations_fail_closed(self):
        def update(item):
            item["split_policy"]["allowed_splits"].append("held_out_evaluation")
            item["split_policy"]["held_out_evaluation_allowed"] = True
            item["release_state"]["product_release"] = "released"
            item["report_policy"]["held_out_results_allowed"] = True

        errors = validate_benchmark_contract(self.changed_contract(update))
        self.assertTrue(any("only development" in error for error in errors))
        self.assertTrue(any("held_out_evaluation_allowed" in error for error in errors))
        self.assertTrue(any("release state" in error for error in errors))
        self.assertTrue(any("held_out_results_allowed" in error for error in errors))

    def test_reference_and_candidate_outputs_cannot_be_promoted_to_truth(self):
        def update(item):
            item["phone_scope"]["alignment"]["model_output_is_reference_truth"] = True
            item["candidate_system_policy"]["cross_system_agreement_is_truth"] = True
            item["metrics_policy"]["one_combined_headline_score_allowed"] = True
            item["expert_label_policy"]["scalar_scores_are_relation_labels"] = True

        errors = validate_benchmark_contract(self.changed_contract(update))
        self.assertGreaterEqual(sum("truth" in error for error in errors), 2)
        self.assertTrue(any("combined" in error for error in errors))
        self.assertTrue(any("scalar" in error for error in errors))

    def test_phone_map_cannot_make_vowels_scorable_or_unknowns_correct(self):
        def update(item):
            item["reference_phones"]["AA"]["scorable"] = True
            item["claims"]["mapping_defines_acceptable_varieties"] = True
            item["claims"]["unknown_candidate_phone_behavior"] = "correct"

        errors = validate_phone_map(self.changed_phone_map(update))
        self.assertTrue(any("nonconsonant" in error for error in errors))
        self.assertTrue(any("acceptable" in error for error in errors))
        self.assertTrue(any("unknown" in error for error in errors))

    def test_reviewer_notation_preserves_every_original_state(self):
        parsed = parse_review_phone_string(
            "B EH0 R", "B (EH0) [L] {R}"
        )
        self.assertEqual(
            [item["state"] for item in parsed["targets"]],
            [
                "reviewer_confirmed_expected_phone",
                "incorrect_or_missed_relation_type_unresolved",
                "accent_marked_but_not_a_relation_concern",
            ],
        )
        self.assertEqual(
            parsed["insertions"],
            [{"boundary_index": 2, "phone": "L", "state": "explicit_inserted_phone"}],
        )

    def test_reviewer_parser_rejects_mismatches_and_unbalanced_notation(self):
        with self.assertRaisesRegex(BenchmarkValidationError, "does not match"):
            parse_review_phone_string("B EH0 R", "B IH0 R")
        with self.assertRaisesRegex(BenchmarkValidationError, "unbalanced"):
            parse_review_phone_string("B EH0 R", "B (EH0 R")
        with self.assertRaisesRegex(BenchmarkValidationError, "extra"):
            parse_review_phone_string("B", "B D")

    def test_four_of_five_consensus_is_scorable_and_three_is_disputed(self):
        positive = "incorrect_or_missed_relation_type_unresolved"
        negative = "reviewer_confirmed_expected_phone"
        self.assertEqual(
            target_consensus([positive] * 4 + [negative])["decision"],
            "coarse_relation_present",
        )
        self.assertEqual(
            target_consensus([positive] * 3 + [negative] * 2)["decision"],
            "disputed_unscorable",
        )
        self.assertEqual(
            target_consensus([negative] * 4 + [positive])["decision"],
            "no_relation_concern",
        )

    def test_insertion_consensus_retains_phone_and_disagreement(self):
        present = [[{"boundary_index": 1, "phone": "L"}]] * 4 + [[]]
        result = insertion_consensus(present, 1)
        self.assertEqual(result["decision"], "explicit_insertion_present")
        self.assertEqual(result["phones"], ["L"])
        disputed = [[{"boundary_index": 1, "phone": "L"}]] * 3 + [[], []]
        self.assertEqual(
            insertion_consensus(disputed, 1)["decision"],
            "disputed_unscorable",
        )

    def test_alignment_is_deterministic_and_declared_allophones_match(self):
        expected = expand_reference_phones(["P", "AE1", "T"], self.phone_map)
        first = align_phone_sequences(expected, ["pʰ", "æ", "t"], self.phone_map)
        second = align_phone_sequences(expected, ["pʰ", "æ", "t"], self.phone_map)
        self.assertEqual(first, second)
        self.assertEqual(first["edit_cost"], 0)
        self.assertTrue(all(item["kind"] == "match" for item in first["operations"]))

    def test_target_predictions_keep_vowels_and_post_vocalic_r_unscorable(self):
        result = target_predictions(
            ["K", "AA1", "R", "T"], ["k", "ɑ", "ɹ", "d"], self.phone_map
        )
        by_index = {item["target_index"]: item for item in result["targets"]}
        self.assertEqual(by_index[0]["state"], "no_relation_candidate")
        self.assertEqual(by_index[1]["reason"], "vowel_or_diphthong_unsupported")
        self.assertEqual(by_index[2]["reason"], "post_vocalic_r_unsupported")
        self.assertEqual(by_index[3]["state"], "coarse_relation_candidate")

    def test_candidate_insertions_keep_consonants_separate_from_vowels(self):
        expected = expand_reference_phones(["B", "AE1", "T"], self.phone_map)
        aligned = align_phone_sequences(
            expected, ["b", "l", "æ", "a", "t"], self.phone_map
        )
        observed = [
            {
                "decision": "identity_nfd",
                "features": {"syl": -1 if token in {"b", "l", "t"} else 1},
            }
            for token in ["b", "l", "æ", "a", "t"]
        ]
        insertions = insertion_predictions(aligned, observed, 3)
        states = [item["state"] for values in insertions.values() for item in values]
        self.assertIn("consonant_insertion_candidate", states)
        self.assertIn("vowel_insertion_unsupported", states)

    def test_unsupported_narrow_detail_causes_abstention(self):
        result = target_predictions(["D"], ["d̪"], self.phone_map)
        self.assertEqual(result["targets"][0]["state"], "abstain")
        self.assertEqual(
            result["targets"][0]["reason"], "unsupported_candidate_detail"
        )

    def test_metrics_show_every_denominator_and_do_not_turn_abstention_into_zero(self):
        result = score_binary_rows(
            [
                {"truth": "positive", "prediction": "positive"},
                {"truth": "positive", "prediction": "negative"},
                {"truth": "negative", "prediction": "positive"},
                {"truth": "negative", "prediction": "negative"},
                {"truth": "negative", "prediction": "abstain"},
                {"truth": "unscorable", "prediction": "positive"},
            ]
        )
        self.assertEqual(result["reference_scorable"], 5)
        self.assertEqual(result["covered"], 4)
        self.assertEqual(result["abstained"], 1)
        self.assertEqual(result["precision"]["denominator"], 2)
        self.assertEqual(result["recall"]["denominator"], 2)
        self.assertEqual(result["coverage"]["denominator"], 5)
        self.assertEqual(result["coverage"]["value"], 0.8)

    def test_zero_denominator_is_null_and_wilson_interval_is_bounded(self):
        result = score_binary_rows([])
        self.assertIsNone(result["precision"]["value"])
        self.assertEqual(result["precision"]["denominator"], 0)
        lower, upper = wilson_interval(3, 5)
        self.assertGreaterEqual(lower, 0)
        self.assertLessEqual(upper, 1)

    def test_reviewer_agreement_reports_raw_counts_and_kappa(self):
        negative = "reviewer_confirmed_expected_phone"
        accent = "accent_marked_but_not_a_relation_concern"
        positive = "incorrect_or_missed_relation_type_unresolved"
        result = reviewer_agreement(
            [[negative] * 5, [positive] * 4 + [accent]]
        )
        self.assertEqual(result["opportunities"], 2)
        self.assertEqual(result["reviewer_pairs"], 40)
        self.assertEqual(result["matching_pairs"], 32)
        self.assertIsNotNone(result["fleiss_kappa"])

    def test_committed_report_privacy_guard_rejects_rows_paths_and_transcripts(self):
        self.assertTrue(contains_private_material({"safe_id": "private"}))
        self.assertTrue(contains_private_material({"path": "/Users/private"}))
        self.assertTrue(contains_private_material({"transcript": "secret"}))
        self.assertFalse(
            contains_private_material(
                {"aggregate": {"participants": 24, "coverage": {"value": 0.7}}}
            )
        )

    def test_committed_benchmark_report_is_safe_and_split_separated(self):
        report = self.safe_report()
        self.assertEqual(validate_safe_benchmark_report(report), [])
        partitions = report["expert_phone_relations"]["partitions"]
        self.assertEqual(
            {
                (item["project_split"], item["age_stratum"])
                for item in partitions
            },
            {
                ("development", "adult"),
                ("development", "child"),
                ("threshold_tuning", "adult"),
                ("threshold_tuning", "child"),
            },
        )
        self.assertEqual(report["sample"]["held_out_participants"], 0)

    def test_benchmark_report_cannot_leak_private_rows_or_unlock_release(self):
        report = self.safe_report()
        report["private_evidence"]["audio_path"] = "/Users/private.wav"
        report["private_evidence"]["held_out_evaluation_accessed_or_scored"] = True
        report["system_decision"]["selected_system"] = "phoneticxeus"
        report["release_boundaries"]["coaching"] = True
        errors = validate_safe_benchmark_report(report)
        self.assertTrue(any("private" in error for error in errors))
        self.assertTrue(any("held out" in error for error in errors))
        self.assertTrue(any("select" in error for error in errors))
        self.assertTrue(any("release boundary" in error for error in errors))

    def test_benchmark_report_keeps_unsupported_denominators_visible(self):
        report = self.safe_report()
        partitions = report["expert_phone_relations"]["partitions"]
        for partition in partitions:
            metric = partition["coarse_target_relation"]
            self.assertGreater(metric["reference_scorable"], 0)
            self.assertIn("unscorable_reference", metric)
            self.assertIn("denominator", metric["precision"])
            self.assertIn("denominator", metric["recall"])


if __name__ == "__main__":
    unittest.main()
