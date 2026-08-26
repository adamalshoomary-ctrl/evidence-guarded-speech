import copy
import unittest

from assessment.pronunciation_benchmark import (
    PronunciationBenchmarkError,
    summarise_candidate,
    validate_benchmark_records,
)


def fixture():
    return [
        {
            "trial_id": "trial_001",
            "participant_id": "participant_001",
            "split": "development",
            "human_reference": {
                "source": (
                    "blind_listeners_and_qualified_phonetic_adjudication"
                ),
                "listener_word_outcome": "understood_as_intended",
                "phonetic_slots": [
                    {"slot_id": "p1", "outcome": "accepted_variant"},
                    {"slot_id": "p2", "outcome": "substitution"},
                ],
            },
            "candidate_outputs": {
                "candidate_a": {
                    "status": "available",
                    "word_outcome": "understood_as_intended",
                    "phonetic_slots": [
                        {"slot_id": "p1", "outcome": "substitution"},
                        {"slot_id": "p2", "outcome": "substitution"},
                    ],
                }
            },
        },
        {
            "trial_id": "trial_002",
            "participant_id": "participant_002",
            "split": "development",
            "human_reference": {
                "source": (
                    "blind_listeners_and_qualified_phonetic_adjudication"
                ),
                "listener_word_outcome": "different_word_heard",
                "phonetic_slots": [
                    {"slot_id": "p1", "outcome": "accepted_variant"},
                    {"slot_id": "p2", "outcome": "deletion"},
                ],
            },
            "candidate_outputs": {
                "candidate_a": {
                    "status": "unavailable",
                    "reason": "poor_audio",
                }
            },
        },
    ]


class PronunciationBenchmarkTests(unittest.TestCase):
    def test_fixture_is_valid(self):
        self.assertEqual(validate_benchmark_records(fixture()), [])

    def test_summary_keeps_coverage_and_accuracy_separate(self):
        result = summarise_candidate(fixture(), "candidate_a")

        self.assertEqual(result["claim_scope"], "research_comparison_only")
        self.assertEqual(result["metrics"]["word_coverage"], 0.5)
        self.assertEqual(result["metrics"]["word_outcome_exact_agreement"], 1.0)
        self.assertEqual(result["metrics"]["phone_coverage"], 0.5)

    def test_accepted_variant_false_concern_is_visible(self):
        result = summarise_candidate(fixture(), "candidate_a")

        self.assertEqual(
            result["counts"]["accepted_variant_false_concerns"], 1
        )
        self.assertEqual(
            result["metrics"]["accepted_variant_false_concern_rate"], 1.0
        )

    def test_unavailable_issue_counts_against_end_to_end_recall(self):
        result = summarise_candidate(fixture(), "candidate_a")

        self.assertEqual(result["counts"]["phone_issue_true_positives"], 1)
        self.assertEqual(result["counts"]["phone_issue_false_negatives"], 1)
        self.assertEqual(result["metrics"]["phone_issue_recall"], 0.5)

    def test_automatic_output_cannot_be_reference_truth(self):
        records = fixture()
        records[0]["human_reference"]["source"] = "provider_consensus"

        errors = validate_benchmark_records(records)

        self.assertTrue(any("independent human truth" in error
                            for error in errors))

    def test_participant_cannot_cross_data_splits(self):
        records = fixture()
        records[1]["participant_id"] = "participant_001"
        records[1]["split"] = "held_out_evaluation"

        errors = validate_benchmark_records(records)

        self.assertTrue(any("multiple data splits" in error
                            for error in errors))

    def test_unknown_candidate_phone_slot_is_rejected(self):
        records = fixture()
        records[0]["candidate_outputs"]["candidate_a"][
            "phonetic_slots"
        ].append({"slot_id": "invented", "outcome": "insertion"})

        with self.assertRaises(PronunciationBenchmarkError):
            summarise_candidate(records, "candidate_a")

    def test_empty_benchmark_is_not_evidence(self):
        self.assertEqual(
            validate_benchmark_records([]),
            ["benchmark records must be a nonempty list"],
        )


if __name__ == "__main__":
    unittest.main()
