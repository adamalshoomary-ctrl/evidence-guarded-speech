import copy
import unittest

from assessment.manifest import load_manifest, validate_manifest


def changed(document, update):
    result = copy.deepcopy(document)
    update(result)
    return result


class AssessmentManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = load_manifest()

    def test_committed_manifest_is_valid(self):
        self.assertEqual(validate_manifest(self.manifest), [])

    def test_core_is_a_ten_minute_english_solo_assessment(self):
        session = self.manifest["session"]

        self.assertEqual(self.manifest["eligibility"]["launch_languages"],
                         ["en"])
        self.assertEqual(self.manifest["protocol_scope"]["recording_mode"],
                         "solo")
        self.assertGreaterEqual(session["target_duration_s"], 480)
        self.assertLessEqual(session["target_duration_s"], 660)
        self.assertEqual(len(session["core_sequence"]), 7)

    def test_age_is_not_collected_gated_or_scored(self):
        age = self.manifest["eligibility"]["age"]

        self.assertEqual(age["gate"], "none")
        self.assertFalse(age["exact_age_collected"])
        self.assertFalse(age["age_norms_used"])
        document = changed(
            self.manifest,
            lambda item: item["eligibility"]["age"].update({"gate": "18_plus"}),
        )
        self.assertTrue(any("age gate" in error
                            for error in validate_manifest(document)))

    def test_unknown_measurement_is_rejected(self):
        def update(item):
            item["tasks"][1]["measurements_enabled"].append(
                "computed_metrics.magic_score"
            )

        errors = validate_manifest(changed(self.manifest, update))

        self.assertTrue(any("unknown measurements" in error for error in errors))

    def test_unvalidated_progress_release_is_rejected(self):
        def update(item):
            item["tasks"][2]["measurement_use"]["progress"] = "approved"

        errors = validate_manifest(changed(self.manifest, update))

        self.assertTrue(any("unsafe progress policy" in error
                            for error in errors))

    def test_ranking_and_diagnosis_must_stay_blocked(self):
        def update(item):
            item["tasks"][2]["measurement_use"]["ranking"] = "allowed"
            item["tasks"][2]["measurement_use"]["diagnosis"] = "allowed"

        errors = validate_manifest(changed(self.manifest, update))

        self.assertTrue(any("must block ranking" in error for error in errors))
        self.assertTrue(any("must block diagnosis" in error for error in errors))

    def test_claim_authority_cannot_expand_to_clinical_claims(self):
        def update(item):
            item["protocol_scope"]["claim_authority"].append(
                "clinical_conclusion"
            )

        errors = validate_manifest(changed(self.manifest, update))

        self.assertTrue(any("claim authority" in error for error in errors))

    def test_research_task_cannot_enter_core_sequence(self):
        def update(item):
            item["session"]["core_sequence"][2]["task_options"] = [
                "comfortable_vowel_research_en_v1"
            ]

        errors = validate_manifest(changed(self.manifest, update))

        self.assertTrue(any("includes noncore task" in error for error in errors))

    def test_accessibility_alternative_cannot_silently_extend_session(self):
        def update(item):
            task = next(task for task in item["tasks"]
                        if task["task_id"]
                        == "spoken_repetition_alternative_en_v1")
            task["duration_s"]["target"] = 150

        errors = validate_manifest(changed(self.manifest, update))

        self.assertTrue(any("equal target duration" in error for error in errors))

    def test_each_standard_sample_has_its_matching_repeat(self):
        rules = self.manifest["session"]["paired_task_rules"]

        self.assertEqual(
            rules,
            {
                "standard_reading_en_v1": "anchor_repeat_en_v1",
                "spoken_repetition_alternative_en_v1":
                    "spoken_anchor_repeat_alternative_en_v1",
            },
        )

    def test_spoken_alternative_cannot_be_paired_with_reading(self):
        def update(item):
            item["session"]["paired_task_rules"][
                "spoken_repetition_alternative_en_v1"
            ] = "anchor_repeat_en_v1"

        errors = validate_manifest(changed(self.manifest, update))

        self.assertTrue(any("every repeat sample option" in error
                            for error in errors))

    def test_repeat_text_must_come_from_its_source_task(self):
        def update(item):
            item["content_assets"]["spoken_repeat_excerpt_en_001"][
                "text"
            ] = "This sentence was never used in the source task."
            item["content_assets"]["spoken_repeat_excerpt_en_001"][
                "declared_word_count"
            ] = 9

        errors = validate_manifest(changed(self.manifest, update))

        self.assertTrue(any("not a segment of its source task" in error
                            for error in errors))

    def test_repeat_cannot_claim_text_from_a_different_source_task(self):
        def update(item):
            repeat = next(
                task for task in item["tasks"]
                if task["task_id"] == "anchor_repeat_en_v1"
            )
            repeat["comparison"]["source_task_text_asset"] = (
                "spoken_alternative_en_001"
            )

        errors = validate_manifest(changed(self.manifest, update))

        self.assertTrue(any("must use the expected text" in error
                            for error in errors))

    def test_optional_research_needs_separate_consent_and_cannot_affect_interpretation(self):
        research = next(
            task for task in self.manifest["tasks"]
            if task["task_id"] == "comfortable_vowel_research_en_v1"
        )
        self.assertEqual(research["required_consent"], "research_collection")
        self.assertEqual(
            research["measurement_use"]["single_session_interpretation"], "blocked"
        )

        def update(item):
            task = next(task for task in item["tasks"]
                        if task["task_id"] == research["task_id"])
            task["required_consent"] = "speech_measurement_processing"
            task["measurement_use"]["single_session_interpretation"] = "allowed"

        errors = validate_manifest(changed(self.manifest, update))
        self.assertTrue(any("separate research consent" in error
                            for error in errors))
        self.assertTrue(any("cannot affect the released interpretation" in error
                            for error in errors))

    def test_future_task_cannot_record_or_enable_measurements(self):
        def update(item):
            task = next(task for task in item["tasks"]
                        if task["status"] == "future_locked")
            task["recording"]["required"] = True
            task["recording"]["quality_policy"] = "baseline"
            task["measurements_enabled"] = ["computed_metrics.wpm"]

        errors = validate_manifest(changed(self.manifest, update))

        self.assertTrue(any("locked but requires recording" in error
                            for error in errors))
        self.assertTrue(any("locked but enables measurements" in error
                            for error in errors))

    def test_content_word_counts_are_checked(self):
        def update(item):
            item["content_assets"]["reading_anchor_en_001"][
                "declared_word_count"
            ] = 999

        errors = validate_manifest(changed(self.manifest, update))

        self.assertTrue(any("declared_word_count is wrong" in error
                            for error in errors))

    def test_consent_choices_are_separate_and_default_off(self):
        for consent in self.manifest["consent"].values():
            if isinstance(consent, dict):
                self.assertTrue(consent["separate_choice"])
                self.assertFalse(consent["default"])

    def test_mastery_requires_later_day_retention_and_new_prompt_transfer(self):
        rule = self.manifest["progression_handoff"]["mastery_rule"]

        self.assertIn("later day", rule)
        self.assertIn("new prompt", rule)
        self.assertFalse(
            self.manifest["progression_handoff"]["overall_score_allowed"]
        )

    def test_reading_alternative_is_not_declared_equivalent(self):
        alternative = next(
            task for task in self.manifest["tasks"]
            if task["task_id"] == "spoken_repetition_alternative_en_v1"
        )

        self.assertNotIn("standard_reading_en_v1",
                         alternative["comparison"]["comparable_with"])
        self.assertIn("never be compared directly",
                      alternative["comparison"]["limitations"])

    def test_prompts_avoid_unsafe_maximum_voice_tasks(self):
        instructions = " ".join(
            task["prompt"]["instruction"].lower()
            for task in self.manifest["tasks"]
        )

        self.assertNotIn("as loud as possible", instructions)
        self.assertNotIn("as high as possible", instructions)
        self.assertNotIn("maximum breath", instructions)


if __name__ == "__main__":
    unittest.main()
