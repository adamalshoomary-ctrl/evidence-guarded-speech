import copy
import unittest

from speech_sound_patterns.benchmark_meta_ctc import (
    _collapsed_tokens,
    load_meta_contract,
    validate_meta_contract,
)
from speech_sound_patterns.benchmark_phoneticxeus_ctc import (
    _ctc_spans,
    deterministic_ctc_viterbi,
)
from speech_sound_patterns.benchmark_repair import (
    RELEASE_BOUNDARIES,
    REPAIR_COMPARISON_IDS,
    load_repair_contract,
    selection_gate_results,
    validate_repair_contract,
    validate_repair_report,
)
from speech_sound_patterns.prepare_benchmark_repair import _assert_label_blind
from speech_sound_patterns.score_benchmark_repair_meta_threshold import (
    load_exact_threshold_contract,
    validate_exact_threshold_contract,
)


class SpeechSoundBenchmarkRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = load_repair_contract()
        cls.meta_contract = load_meta_contract()
        cls.exact_threshold_contract = load_exact_threshold_contract()

    def test_frozen_repair_contract_is_valid(self):
        self.assertEqual(validate_repair_contract(self.contract), [])

    def test_repair_cannot_read_held_out_or_expert_outcomes(self):
        changed = copy.deepcopy(self.contract)
        changed["input_policy"]["held_out_access_allowed"] = True
        changed["input_policy"]["candidate_runner_may_read_expert_outcomes"] = True
        changed["calibration_policy"]["held_out_labels_or_outputs_used"] = True

        errors = validate_repair_contract(changed)

        self.assertTrue(any("held_out_access" in error for error in errors))
        self.assertTrue(any("expert_outcomes" in error for error in errors))
        self.assertTrue(any("held_out_labels" in error for error in errors))

    def test_tuning_cannot_change_features_or_refit_coefficients(self):
        changed = copy.deepcopy(self.contract)
        changed["feature_extractor"]["numeric_features"].append("new_feature")
        changed["calibration_policy"][
            "tuning_labels_may_change_feature_set_or_regularization"
        ] = True
        changed["calibration_policy"]["coefficients_refit_after_tuning"] = True

        errors = validate_repair_contract(changed)

        self.assertTrue(any("numeric feature" in error for error in errors))
        self.assertTrue(any("tuning_labels" in error for error in errors))
        self.assertTrue(any("coefficients_refit" in error for error in errors))

    def test_release_boundaries_cannot_be_enabled(self):
        changed = copy.deepcopy(self.contract)
        changed["release_boundaries"]["normal_pipeline"] = True
        changed["release_boundaries"]["coaching"] = True

        self.assertTrue(
            any(
                "release boundary" in error
                for error in validate_repair_contract(changed)
            )
        )

    def test_expected_only_guard_rejects_expert_fields_at_any_depth(self):
        with self.assertRaisesRegex(ValueError, "expert result fields"):
            _assert_label_blind(
                {
                    "clips": [
                        {
                            "safe_id": "so_000001",
                            "nested": {"reference_decision": "positive"},
                        }
                    ]
                }
            )

    def test_deterministic_ctc_viterbi_preserves_target_order(self):
        log_probs = [
            [-0.01, -8.0, -8.0],
            [-8.0, -0.01, -8.0],
            [-0.01, -8.0, -8.0],
            [-8.0, -8.0, -0.01],
            [-0.01, -8.0, -8.0],
        ]
        path, score = deterministic_ctc_viterbi(
            log_probs, [1, 2]
        )

        self.assertEqual(
            [item["token_id"] for item in _ctc_spans(path, [1, 2])],
            [1, 2],
        )
        self.assertTrue(score < 0)

    def test_deterministic_ctc_viterbi_separates_repeated_tokens(self):
        log_probs = [
            [-8.0, -0.01],
            [-0.01, -8.0],
            [-8.0, -0.01],
        ]
        path, _ = deterministic_ctc_viterbi(
            log_probs, [1, 1]
        )

        spans = _ctc_spans(path, [1, 1])
        self.assertEqual(len(spans), 2)
        self.assertEqual(path, [1, 0, 1])

    def test_conservative_selection_gates_require_every_condition(self):
        gates = self.contract["selection_gates"]
        passing = selection_gate_results(
            {
                "true_positive": 12,
                "false_positive": 2,
                "false_negative": 28,
                "reference_scorable": 1000,
            },
            gates,
        )
        failing = selection_gate_results(
            {
                "true_positive": 6,
                "false_positive": 10,
                "false_negative": 34,
                "reference_scorable": 1000,
            },
            gates,
        )

        self.assertTrue(passing["passed"])
        self.assertFalse(failing["passed"])
        self.assertFalse(failing["checks"]["true_positives"])

    def test_meta_repair_contract_is_frozen_and_release_locked(self):
        self.assertEqual(validate_meta_contract(self.meta_contract), [])

        changed = copy.deepcopy(self.meta_contract)
        changed["selection_gates"]["minimum_precision_point_estimate"] = 0.5
        changed["release_boundaries"]["candidate_artifact"] = True

        errors = validate_meta_contract(changed)
        self.assertTrue(any("selection gates" in error for error in errors))
        self.assertTrue(any("release boundaries" in error for error in errors))

    def test_meta_repair_cannot_read_labels_or_held_out_evidence(self):
        changed = copy.deepcopy(self.meta_contract)
        changed["input_policy"]["held_out_access_allowed"] = True
        changed["input_policy"]["candidate_runner_may_read_expert_outcomes"] = True
        changed["calibration_policy"][
            "reviewer_outcome_feature_allowed"
        ] = True

        errors = validate_meta_contract(changed)
        self.assertTrue(any("held_out_access" in error for error in errors))
        self.assertTrue(any("expert_outcomes" in error for error in errors))
        self.assertTrue(any("reviewer_outcome" in error for error in errors))

    def test_meta_ctc_collapse_removes_blanks_and_repeated_frames(self):
        self.assertEqual(
            _collapsed_tokens(
                [0, 4, 4, 0, 4, 5, 5, 0],
                {0: "<pad>", 4: "n", 5: "s"},
            ),
            ["n", "n", "s"],
        )

    def test_exact_threshold_contract_is_frozen_and_release_locked(self):
        self.assertEqual(
            validate_exact_threshold_contract(self.exact_threshold_contract),
            [],
        )

        changed = copy.deepcopy(self.exact_threshold_contract)
        changed["selection_gates"]["minimum_recall"] = 0.18
        changed["threshold_policy"]["held_out_labels_or_outputs_used"] = True
        changed["release_boundaries"]["candidate_artifact"] = True

        errors = validate_exact_threshold_contract(changed)
        self.assertTrue(any("selection gates" in error for error in errors))
        self.assertTrue(any("held_out" in error for error in errors))
        self.assertTrue(any("release boundaries" in error for error in errors))

    def test_safe_repair_report_rejects_private_rows_and_release(self):
        report = {
            "schema_version": "1.0.0",
            "checkpoint": "22D",
            "status": "local_benchmark_repair_complete_release_locked",
            "purpose": "aggregate only",
            "sample": {
                "clips": 480,
                "development_adult_participants": 8,
                "threshold_tuning_adult_participants": 4,
                "held_out_participants": 0,
                "expert_outcomes_read_by_candidate_runners": False,
                "same_input_repeats": 2,
            },
            "positive_reference_distribution": {},
            "selection_gates": {
                "minimum_precision_point_estimate": 0.75,
                "minimum_precision_wilson_95_lower": 0.5,
                "maximum_false_concerns_per_scorable_opportunity": 0.01,
                "minimum_recall": 0.2,
                "minimum_true_positives": 7,
                "development_and_tuning_both_required": True,
            },
            "candidate_comparisons": [
                {"candidate_id": item, "held_out_used": False}
                for item in sorted(REPAIR_COMPARISON_IDS)
            ],
            "system_decision": {
                "decision": "no_system_or_threshold_selected",
                "selected_system": None,
                "selected_threshold": None,
                "paid_provider_evaluated": False,
            },
            "alternative_local_screen": [],
            "private_evidence": {},
            "release_boundaries": {
                item: False for item in RELEASE_BOUNDARIES
            },
            "limitations": [],
            "next_checkpoint": (
                "22E_paid_api_bake_off_after_owner_commit_and_explicit_approval"
            ),
        }
        self.assertEqual(validate_repair_report(report), [])

        report["candidate_comparisons"][0][
            "private_participant_id"
        ] = "private"
        report["release_boundaries"]["coaching"] = True
        errors = validate_repair_report(report)
        self.assertTrue(any("private or row-level" in error for error in errors))
        self.assertTrue(any("release boundaries" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
