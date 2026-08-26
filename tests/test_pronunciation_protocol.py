import copy
import unittest

from assessment.pronunciation import load_protocol, validate_protocol


def changed(document, update):
    result = copy.deepcopy(document)
    update(result)
    return result


class PronunciationProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol = load_protocol()

    def test_committed_protocol_is_valid(self):
        self.assertEqual(validate_protocol(self.protocol), [])

    def test_task_and_word_pack_remain_research_only(self):
        self.assertEqual(
            self.protocol["task"]["status"], "research_protocol_only"
        )
        self.assertEqual(
            self.protocol["word_pack"]["status"],
            "awaiting_professional_review",
        )
        self.assertEqual(self.protocol["word_pack"]["stimuli"], [])
        self.assertIsNone(
            self.protocol["candidate_systems"]["selected_provider"]
        )

    def test_unreviewed_stimuli_cannot_be_activated(self):
        def update(item):
            item["word_pack"]["stimuli"] = [
                {"stimulus_id": "unsafe", "word": "example"}
            ]

        errors = validate_protocol(changed(self.protocol, update))

        self.assertTrue(any("cannot contain active stimuli" in error
                            for error in errors))

    def test_provider_cannot_be_selected_before_human_evaluation(self):
        def update(item):
            item["candidate_systems"]["selected_provider"] = (
                "azure_pronunciation_assessment"
            )

        errors = validate_protocol(changed(self.protocol, update))

        self.assertTrue(any("no pronunciation provider" in error
                            for error in errors))

    def test_acceptable_accent_variant_cannot_become_an_error(self):
        def update(item):
            item["variant_policy"]["acceptable_variant_is_error"] = True
            item["variant_policy"][
                "single_canonical_native_target_allowed"
            ] = True

        errors = validate_protocol(changed(self.protocol, update))

        self.assertTrue(any("acceptable accent or dialect" in error
                            for error in errors))
        self.assertTrue(any("single canonical native target" in error
                            for error in errors))

    def test_intelligibility_listener_must_not_see_the_prompt(self):
        def update(item):
            item["task"]["listener_can_see_expected_word"] = True
            item["task"][
                "prompt_audio_must_be_excluded_from_trial_audio"
            ] = False

        errors = validate_protocol(changed(self.protocol, update))

        self.assertTrue(any("listeners must remain blind" in error
                            for error in errors))
        self.assertTrue(any("prompts must be excluded" in error
                            for error in errors))

    def test_listener_and_phonetic_truth_stay_independent(self):
        def update(item):
            item["reference_truth"][
                "listener_intelligibility_and_phonetic_reference_are_separate"
            ] = False
            item["reference_truth"]["phonetic_reference"][
                "automatic_system_allowed_as_truth"
            ] = True

        errors = validate_protocol(changed(self.protocol, update))

        self.assertTrue(any("phonetic truth" in error for error in errors))
        self.assertTrue(any("must remain separate" in error
                            for error in errors))

    def test_provider_agreement_cannot_replace_reference_truth(self):
        def update(item):
            item["claim_boundaries"]["provider_agreement_is_truth"] = True
            item["evaluation_plan"][
                "provider_agreement_counts_as_reference_truth"
            ] = True

        errors = validate_protocol(changed(self.protocol, update))

        self.assertGreaterEqual(
            sum("provider agreement" in error for error in errors), 2
        )

    def test_word_and_phone_outcomes_cannot_be_silently_collapsed(self):
        def update(item):
            item["observation_model"]["word_outcomes"].remove("uncertain")
            item["observation_model"]["phone_outcomes"].remove("insertion")

        errors = validate_protocol(changed(self.protocol, update))

        self.assertGreaterEqual(
            sum("approved values exactly" in error for error in errors), 2
        )

    def test_missing_evidence_cannot_become_zero_or_an_llm_guess(self):
        def update(item):
            item["observation_model"]["missing_evidence_is_zero"] = True
            item["failure_policy"]["fallback_to_zero"] = True
            item["failure_policy"]["fallback_to_llm_judgment"] = True

        errors = validate_protocol(changed(self.protocol, update))

        self.assertTrue(any("missing pronunciation evidence" in error
                            for error in errors))
        self.assertTrue(any("fall back to zero" in error for error in errors))
        self.assertTrue(any("LLM judgment" in error for error in errors))

    def test_bad_audio_and_unsupported_variety_must_be_unavailable(self):
        def update(item):
            item["failure_policy"]["poor_audio"] = "score_anyway"
            item["failure_policy"][
                "unsupported_or_unrepresented_variety"
            ] = "use_default_accent"

        errors = validate_protocol(changed(self.protocol, update))

        self.assertTrue(any("poor_audio must become unavailable" in error
                            for error in errors))
        self.assertTrue(any("unsupported_or_unrepresented_variety" in error
                            for error in errors))

    def test_participants_cannot_cross_evaluation_splits(self):
        def update(item):
            item["evaluation_plan"]["participant_exclusive_splits"] = False
            item["evaluation_plan"][
                "thresholds_fixed_before_held_out_evaluation"
            ] = False

        errors = validate_protocol(changed(self.protocol, update))

        self.assertTrue(any("participant_exclusive_splits" in error
                            for error in errors))
        self.assertTrue(any("thresholds_fixed" in error for error in errors))

    def test_normal_coaching_progress_and_diagnosis_remain_blocked(self):
        def update(item):
            item["release_policy"]["normal_coaching"] = "allowed"
            item["release_policy"]["individual_progress"] = "allowed"
            item["release_policy"]["diagnosis"] = "allowed"

        errors = validate_protocol(changed(self.protocol, update))

        self.assertTrue(any("normal_coaching must remain blocked" in error
                            for error in errors))
        self.assertTrue(any("individual_progress must remain blocked" in error
                            for error in errors))
        self.assertTrue(any("diagnosis must remain blocked" in error
                            for error in errors))


if __name__ == "__main__":
    unittest.main()
