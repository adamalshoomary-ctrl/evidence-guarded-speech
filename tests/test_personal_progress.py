import copy
import unittest

from pipeline.personal_progress import (
    CORE_COMPARISON_FIELDS,
    evaluate_personal_progress,
    load_progress_contract,
    load_reliability_registry,
    records_are_comparable,
    render_progress_markdown,
    validate_progress_contract,
    validate_reliability_registry,
)
from pipeline.pipeline_config import ACTIVE_SOURCE_FILES


def comparison(prompt_id="prompt_001", device_class="phone"):
    return {
        "account_id": "acct_00000001",
        "context_id": "ctx_00000001",
        "task_id": "task_001",
        "task_version": "1.0.0",
        "prompt_id": prompt_id,
        "prompt_version": "1.0.0",
        "language": "en",
        "recording_mode": "solo",
        "quality_policy": "baseline",
        "device_class": device_class,
        "platform": "ios",
        "microphone": "built_in",
        "environment_setting": "home",
        "environment_noise": "quiet",
        "preparation_allowed_s": 60,
        "accommodations": [],
    }


def evidence(progress_use="approved", algorithm="merge-metrics-1.0.0"):
    return {
        "availability": {"status": "available"},
        "quality": {"category": "high"},
        "algorithm_version": algorithm,
        "validation": {"reliability": {"progress_use": progress_use}},
    }


def record(index, value, intent="baseline_observation", *,
           prompt_id="prompt_001", device_class="phone",
           representativeness="typical", attempt_role="first"):
    return {
        "history_record_version": "2.0.0",
        "recorded_at_utc": f"2026-07-{index:02d}T10:00:00+10:00",
        "account_id": "acct_00000001",
        "session_id": f"sess_{index:08d}",
        "context_id": "ctx_00000001",
        "task_attempt_id": f"attempt_{index:08d}",
        "attempt_role": attempt_role,
        "progress_intent": intent,
        "exercise_id": None,
        "comparison": comparison(prompt_id, device_class),
        "computed_metrics": {"wpm": value},
        "measurement_metadata": {
            "computed_metrics": {"wpm": evidence()},
        },
        "user_report": {
            "source": "user_declared",
            "representativeness": representativeness,
            "difficulty": "moderate",
            "confidence": "moderate",
            "usefulness": "not_yet_known",
        },
        "real_world_outcome": None,
        "run_quality": {
            "audio_quality": {"overall_status": "pass"},
            "verification_pct": 100,
        },
    }


def released_registry():
    return {
        "schema_version": "1.1.0",
        "registry_version": "99.0.0",
        "progress_contract_version": "1.1.0",
        "status": "metrics_released",
        "approved_metric_profiles": [{
            "metric_path": "wpm",
            "construct": "speaking rate",
            "unit": "words per minute",
            "release_status": "approved_for_personal_change",
            "eligible_attempt_roles": ["first"],
            "comparison_fields": sorted(CORE_COMPARISON_FIELDS),
            "minimum_baseline_observations": 3,
            "minimum_distinct_sessions": 3,
            "minimum_distinct_days": 3,
            "measurement_error": {
                "method": "individual_sdc95_agreement",
                "boundary": 3.0,
            },
            "natural_variation": {
                "method": "stable_repeated_production_distribution",
                "boundary": 5.0,
            },
            "meaningful_change": {
                "method": "anchor_based",
                "boundary": 10.0,
                "distribution_only": False,
                "anchor_references": ["test_user_anchor"],
            },
            "validated_algorithm_versions": ["merge-metrics-1.0.0"],
            "evidence": {
                "development_participants": 20,
                "evaluation_participants": 20,
                "participants_separated": True,
                "independent_held_out_evaluation": True,
                "representative_conditions": True,
                "subgroups_reported": True,
                "study_reference": "synthetic test fixture only",
                "sample_size_justification": "synthetic test fixture only",
                "development_protocol_reference": "synthetic development fixture",
                "held_out_results_reference": "synthetic evaluation fixture",
                "measurement_review_role": "synthetic measurement specialist",
                "owner_release_approved": True,
            },
        }],
        "current_blockers": [],
        "owner_recordings_may_unlock_metrics": False,
    }


class PersonalProgressContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = load_progress_contract()
        cls.registry = load_reliability_registry()

    def test_committed_contract_and_locked_registry_are_valid(self):
        self.assertEqual(validate_progress_contract(self.contract), [])
        self.assertEqual(
            validate_reliability_registry(self.registry, self.contract), []
        )
        self.assertEqual(self.registry["approved_metric_profiles"], [])

    def test_progress_rules_are_in_pipeline_source_fingerprint(self):
        self.assertIn(
            "progress_model/contract-v1.1.0.json", ACTIVE_SOURCE_FILES
        )
        self.assertIn(
            "progress_model/reliability-registry-v1.1.0.json",
            ACTIVE_SOURCE_FILES,
        )
        self.assertIn("pipeline/personal_progress.py", ACTIVE_SOURCE_FILES)

    def test_one_recording_and_global_percentage_rule_cannot_be_enabled(self):
        changed = copy.deepcopy(self.contract)
        changed["claim_boundaries"]["one_observation_is_a_baseline"] = True
        changed["baseline_model"]["one_recording_default_allowed"] = True
        changed["change_model"]["global_percentage_rule"] = 5

        errors = validate_progress_contract(changed)

        self.assertTrue(any("one_observation" in error for error in errors))
        self.assertTrue(any("one recording" in error for error in errors))
        self.assertTrue(any("global percentage" in error for error in errors))

    def test_confidence_practice_and_detectable_change_stay_bounded(self):
        changed = copy.deepcopy(self.contract)
        changed["claim_boundaries"]["confidence_inferred_from_voice"] = True
        changed["evidence_streams"]["practice"]["proves_mastery"] = True
        changed["claim_boundaries"][
            "detectable_change_is_automatically_improvement"
        ] = True

        errors = validate_progress_contract(changed)

        self.assertTrue(any("confidence_inferred" in error for error in errors))
        self.assertTrue(any("practice cannot prove" in error for error in errors))
        self.assertTrue(any("detectable_change" in error for error in errors))

    def test_synthetic_release_profile_needs_full_independent_evidence(self):
        registry = released_registry()
        self.assertEqual(
            validate_reliability_registry(registry, self.contract), []
        )

        registry["approved_metric_profiles"][0]["evidence"][
            "participants_separated"
        ] = False
        registry["approved_metric_profiles"][0]["meaningful_change"][
            "distribution_only"
        ] = True

        errors = validate_reliability_registry(registry, self.contract)

        self.assertTrue(any("participants_separated" in error for error in errors))
        self.assertTrue(any("distribution only" in error for error in errors))


class PersonalProgressEvaluationTests(unittest.TestCase):
    def baseline_records(self):
        return [record(1, 98), record(2, 100), record(3, 102)]

    def test_current_registry_returns_explicit_metric_not_released(self):
        result = evaluate_personal_progress([record(1, 100)])

        self.assertEqual(
            result["baseline_status"]["status"], "metric_not_released"
        )
        self.assertEqual(result["speech_change"]["metrics"], [])
        self.assertFalse(result["speech_change"]["called_overall_improvement"])

    def test_released_fixture_models_range_and_credible_change(self):
        records = self.baseline_records()
        records.append(record(4, 112, intent="change_check"))

        result = evaluate_personal_progress(
            records, registry=released_registry()
        )
        metric = result["speech_change"]["metrics"][0]

        self.assertEqual(metric["baseline"]["status"], "established")
        self.assertEqual(metric["baseline"]["median"], 100)
        self.assertEqual(metric["baseline"]["observed_minimum"], 98)
        self.assertEqual(metric["baseline"]["observed_maximum"], 102)
        self.assertEqual(metric["change"]["status"], "credible_change")
        self.assertEqual(metric["change"]["direction"], "increased")
        self.assertFalse(metric["change"]["called_improvement"])

    def test_change_must_strictly_exceed_largest_boundary(self):
        records = self.baseline_records()
        records.append(record(4, 110, intent="change_check"))

        result = evaluate_personal_progress(
            records, registry=released_registry()
        )

        self.assertEqual(
            result["speech_change"]["metrics"][0]["change"]["status"],
            "detectable_not_proven_meaningful",
        )

    def test_device_mismatch_and_unrepresentative_samples_do_not_join_baseline(self):
        records = self.baseline_records()
        records[1]["comparison"]["device_class"] = "laptop"
        records[2]["user_report"]["representativeness"] = "atypical"
        current = record(4, 112, intent="change_check")
        records.append(current)

        result = evaluate_personal_progress(
            records, registry=released_registry()
        )
        baseline = result["speech_change"]["metrics"][0]["baseline"]

        self.assertEqual(baseline["observation_count"], 1)
        self.assertEqual(
            baseline["status"], "insufficient_comparable_observations"
        )

    def test_unreleased_measurement_metadata_cannot_be_used(self):
        records = self.baseline_records()
        records[0]["measurement_metadata"]["computed_metrics"]["wpm"] = (
            evidence(progress_use="blocked")
        )
        records.append(record(4, 112, intent="change_check"))

        result = evaluate_personal_progress(
            records, registry=released_registry()
        )

        self.assertEqual(
            result["speech_change"]["metrics"][0]["baseline"][
                "observation_count"
            ],
            2,
        )

    def test_user_report_practice_mastery_and_quality_remain_separate(self):
        records = self.baseline_records()
        practice = record(
            4, 104, intent="practice", attempt_role="matched_repeat"
        )
        practice["exercise_id"] = "exercise_00000001"
        retention = record(
            5, 112, intent="retention", attempt_role="retention"
        )
        transfer = record(
            6, 113, intent="transfer", attempt_role="transfer",
            prompt_id="prompt_002",
        )
        transfer["real_world_outcome"] = {
            "source": "user_declared",
            "real_world_outcome": "partly_achieved",
        }
        records.extend([practice, retention, transfer])

        result = evaluate_personal_progress(records, registry=released_registry())

        self.assertTrue(result["user_reports"][
            "kept_separate_from_speech_change"])
        self.assertTrue(result["real_world_outcomes"][
            "kept_separate_from_speech_change"])
        self.assertEqual(result["practice"]["attempt_count"], 1)
        self.assertEqual(
            result["mastery"]["status"],
            "blocked_until_skill_specific_policy",
        )
        self.assertTrue(result["mastery"]["later_day_retention_present"])
        self.assertTrue(result["mastery"]["new_prompt_transfer_present"])
        self.assertFalse(result["run_quality"]["is_skill_progress"])

    def test_comparability_requires_every_profile_field(self):
        left = record(1, 100)
        right = record(2, 100)
        self.assertTrue(records_are_comparable(
            left, right, CORE_COMPARISON_FIELDS
        ))
        del right["comparison"]["microphone"]
        self.assertFalse(records_are_comparable(
            left, right, CORE_COMPARISON_FIELDS
        ))

    def test_markdown_never_calls_locked_metrics_progress(self):
        markdown = render_progress_markdown(
            evaluate_personal_progress([record(1, 100)])
        )

        self.assertIn("No improvement claim is available", markdown)
        self.assertIn("Practice is not treated as mastery", markdown)
        self.assertNotIn("improving", markdown.lower())
        self.assertNotIn("slipping", markdown.lower())


if __name__ == "__main__":
    unittest.main()
