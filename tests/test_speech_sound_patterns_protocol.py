import copy
import hashlib
import unittest
from pathlib import Path

from speech_sound_patterns.contract import load_contract, validate_contract

from tests.research_data import (
    needs_repository_history,
    needs_research_data,
)


def changed(document, update):
    result = copy.deepcopy(document)
    update(result)
    return result


class SpeechSoundPatternProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = load_contract()

    @needs_research_data
    def test_committed_contract_is_valid(self):
        self.assertEqual(validate_contract(self.contract), [])

    def test_original_research_only_contract_remains_available(self):
        legacy_path = (
            Path(__file__).parents[1]
            / "speech_sound_patterns"
            / "research-contract-v1.0.0.json"
        )
        legacy = load_contract(legacy_path)

        self.assertEqual(legacy["schema_version"], "1.0.0")
        self.assertEqual(legacy["protocol_version"], "1.0.0")
        self.assertEqual(
            legacy["status"], "research_design_only_no_automatic_measurement"
        )

    def test_version_1_1_contract_remains_byte_for_byte_unchanged(self):
        legacy_path = (
            Path(__file__).parents[1]
            / "speech_sound_patterns"
            / "research-contract-v1.1.0.json"
        )
        self.assertEqual(
            hashlib.sha256(legacy_path.read_bytes()).hexdigest(),
            "fba9a9561a296f084309d31a3e0e93a6f0dc7800266ee300a63ac46fdf793534",
        )
        legacy = load_contract(legacy_path)
        self.assertEqual(legacy["schema_version"], "1.1.0")
        self.assertEqual(legacy["protocol_version"], "1.1.0")

    def test_active_contract_uses_the_validated_source_registry(self):
        sources = self.contract["research_sources"]
        self.assertEqual(self.contract["protocol_version"], "1.7.0")
        self.assertEqual(sources["source_registry_status"], "validated_release_locked")
        self.assertEqual(len(sources["recorded_sources"]), 10)

    def test_version_1_2_contract_remains_byte_for_byte_unchanged(self):
        legacy_path = (
            Path(__file__).parents[1]
            / "speech_sound_patterns"
            / "research-contract-v1.2.0.json"
        )
        self.assertEqual(
            hashlib.sha256(legacy_path.read_bytes()).hexdigest(),
            "66602f928ccadba3e66591f0cbd8a36c92a756cacbbe70e273467a8206755e24",
        )
        legacy = load_contract(legacy_path)
        self.assertEqual(legacy["schema_version"], "1.2.0")
        self.assertEqual(legacy["protocol_version"], "1.2.0")

    def test_version_1_3_contract_remains_byte_for_byte_unchanged(self):
        legacy_path = (
            Path(__file__).parents[1]
            / "speech_sound_patterns"
            / "research-contract-v1.3.0.json"
        )
        self.assertEqual(
            hashlib.sha256(legacy_path.read_bytes()).hexdigest(),
            "7d683caa3d65340de322f1bb7959e185be47a61743846f06b5d06becfb4a050c",
        )
        legacy = load_contract(legacy_path)
        self.assertEqual(legacy["schema_version"], "1.3.0")
        self.assertEqual(legacy["protocol_version"], "1.3.0")

    def test_version_1_4_contract_remains_byte_for_byte_unchanged(self):
        legacy_path = (
            Path(__file__).parents[1]
            / "speech_sound_patterns"
            / "research-contract-v1.4.0.json"
        )
        self.assertEqual(
            hashlib.sha256(legacy_path.read_bytes()).hexdigest(),
            "046be02a8ea5c1fdc328fdf6a35078a93fcf7448d62e6208d72aa259311290ee",
        )
        legacy = load_contract(legacy_path)
        self.assertEqual(legacy["schema_version"], "1.4.0")
        self.assertEqual(legacy["protocol_version"], "1.4.0")

    def test_version_1_5_contract_remains_byte_for_byte_unchanged(self):
        legacy_path = (
            Path(__file__).parents[1]
            / "speech_sound_patterns"
            / "research-contract-v1.5.0.json"
        )
        self.assertEqual(
            hashlib.sha256(legacy_path.read_bytes()).hexdigest(),
            "d3201a24c9bac7211aef96f8f4b9a1850e0c4bd9c2161d24de0cf879b80197ac",
        )
        legacy = load_contract(legacy_path)
        self.assertEqual(legacy["schema_version"], "1.5.0")
        self.assertEqual(legacy["protocol_version"], "1.5.0")
        self.assertEqual(
            legacy["engineering_policy"]["planned_artifact_status"],
            "not_implemented",
        )

    def test_version_1_6_contract_remains_byte_for_byte_unchanged(self):
        legacy_path = (
            Path(__file__).parents[1]
            / "speech_sound_patterns"
            / "research-contract-v1.6.0.json"
        )
        self.assertEqual(
            hashlib.sha256(legacy_path.read_bytes()).hexdigest(),
            "1541488efe1a8d1998bc8ca9b4322a7d849f670c574d1310413aabe392dde7fc",
        )
        legacy = load_contract(legacy_path)
        self.assertEqual(legacy["schema_version"], "1.6.0")
        self.assertEqual(legacy["protocol_version"], "1.6.0")
        self.assertEqual(
            legacy["developer_candidate_extractor"]["checkpoint"], "22G"
        )

    def test_final_acceptance_artifacts_are_bound(self):
        final = self.contract["final_repository_acceptance"]
        self.assertEqual(final["checkpoint"], "22H")
        self.assertEqual(final["selection_outcome"]["decision"], "no_selection")
        self.assertEqual(
            final["held_out_outcome"]["evaluation_status"], "not_performed"
        )
        self.assertEqual(
            final["held_out_outcome"]["result_availability"], "unavailable"
        )
        self.assertFalse(final["held_out_outcome"]["evidence_accessed"])
        self.assertFalse(final["completion"]["scientific_release"])
        self.assertFalse(final["completion"]["product_release"])

    def test_final_acceptance_boundary_cannot_be_rewritten(self):
        mutations = (
            lambda item: item["final_repository_acceptance"][
                "evidence_report"
            ].update(sha256="0" * 64),
            lambda item: item["final_repository_acceptance"][
                "selection_outcome"
            ].update(candidate_system="invented"),
            lambda item: item["final_repository_acceptance"][
                "held_out_outcome"
            ].update(evaluation_status="pass"),
            lambda item: item["final_repository_acceptance"][
                "held_out_outcome"
            ].update(evidence_accessed=True),
            lambda item: item["final_repository_acceptance"]["completion"].update(
                scientific_release=True
            ),
            lambda item: item["final_repository_acceptance"]["completion"].update(
                engineering_complete_after_repository_closure=False
            ),
        )
        for mutation in mutations:
            with self.subTest(mutation=repr(mutation)):
                self.assertTrue(validate_contract(changed(self.contract, mutation)))

    def test_local_feasibility_cannot_claim_accuracy_or_activate_extraction(self):
        def update(item):
            feasibility = item["local_feasibility"]
            feasibility["held_out_or_accuracy_evaluation_performed"] = True
            feasibility["candidate_extractor_implemented"] = True
            feasibility["raw_evidence_committed"] = True
            feasibility["report_sha256"] = "0" * 64
            feasibility["private_sample_manifest_sha256"] = "0" * 64

        errors = validate_contract(changed(self.contract, update))

        self.assertTrue(any("accuracy_evaluation" in error for error in errors))
        self.assertTrue(any("candidate_extractor" in error for error in errors))
        self.assertTrue(any("raw_evidence" in error for error in errors))
        self.assertTrue(any("checksum" in error for error in errors))
        self.assertTrue(any("private feasibility sample" in error for error in errors))

    def test_local_benchmark_cannot_touch_held_out_or_select_a_system(self):
        def update(item):
            benchmark = item["local_benchmark"]
            benchmark["held_out_evaluation_accessed_or_scored"] = True
            benchmark["selected_system"] = "phoneticxeus"
            benchmark["threshold_selected"] = True
            benchmark["candidate_extractor_implemented"] = True
            benchmark["private_sample_manifest_sha256"] = "0" * 64

        errors = validate_contract(changed(self.contract, update))

        self.assertTrue(any("held_out" in error for error in errors))
        self.assertTrue(any("select a candidate system" in error for error in errors))
        self.assertTrue(any("threshold_selected" in error for error in errors))
        self.assertTrue(any("candidate_extractor" in error for error in errors))
        self.assertTrue(any("private benchmark sample" in error for error in errors))

    def test_local_benchmark_files_and_next_checkpoint_are_pinned(self):
        def update(item):
            benchmark = item["local_benchmark"]
            benchmark["report_sha256"] = "0" * 64
            benchmark["benchmark_contract_sha256"] = "0" * 64
            benchmark["phone_map_sha256"] = "0" * 64
            benchmark["next_checkpoint"] = "22F"

        errors = validate_contract(changed(self.contract, update))

        self.assertGreaterEqual(sum("sha256" in error for error in errors), 3)
        self.assertTrue(any("next checkpoint" in error for error in errors))

    def test_local_benchmark_repair_cannot_claim_a_selection_or_touch_held_out(self):
        def update(item):
            repair = item["local_benchmark_repair"]
            repair["held_out_evaluation_accessed_or_scored"] = True
            repair["selected_system"] = "meta_wav2vec2_constrained_contextual"
            repair["threshold_selected"] = True
            repair["candidate_extractor_implemented"] = True
            repair["report_sha256"] = "0" * 64

        errors = validate_contract(changed(self.contract, update))

        self.assertTrue(any("held_out" in error for error in errors))
        self.assertTrue(any("cannot select" in error for error in errors))
        self.assertTrue(any("threshold_selected" in error for error in errors))
        self.assertTrue(any("candidate_extractor" in error for error in errors))
        self.assertTrue(any("report checksum" in error for error in errors))

    def test_source_states_and_independence_cannot_be_relabelled(self):
        def update(item):
            records = {
                record["source_id"]: record
                for record in item["research_sources"]["recorded_sources"]
            }
            records["timit_ldc93s1"]["access_state"] = "available"
            records["timit_ldc93s1"]["licence_state"] = (
                "verified_for_declared_role"
            )
            records["common_phone_1_0"]["independent_of_common_voice"] = True
            item["research_sources"]["truth_classes_may_be_pooled"] = True

        errors = validate_contract(changed(self.contract, update))

        self.assertTrue(any("timit_ldc93s1" in error for error in errors))
        self.assertTrue(any("Common Phone" in error for error in errors))
        self.assertTrue(any("truth_classes_may_be_pooled" in error for error in errors))

    def test_engineering_approval_cannot_silently_activate_work(self):
        def update(item):
            item["status"] = "engineering_active"
            item["engineering_policy"]["implementation_status"] = "active"
            item["engineering_policy"]["planned_artifact_status"] = "implemented"
            item["engineering_policy"]["gpu_rental_approved"] = True
            item["task_policy"]["active_developer_research_task"] = "unsafe_task"
            item["downstream_policy"]["developer_research_extractor_exists"] = True

        errors = validate_contract(changed(self.contract, update))

        self.assertTrue(
            any("no-selection" in error and "release-locked" in error for error in errors)
        )
        self.assertTrue(any("implementation_status" in error for error in errors))
        self.assertTrue(any("planned_artifact_status" in error for error in errors))
        self.assertTrue(any("gpu_rental_approved" in error for error in errors))
        self.assertTrue(any("no speech sound task" in error for error in errors))
        self.assertTrue(
            any("developer_research_extractor_exists" in error for error in errors)
        )

    def test_candidate_extractor_cannot_invent_a_rule_or_open_a_boundary(self):
        def update(item):
            extractor = item["developer_candidate_extractor"]
            extractor["candidate_rule"]["system"] = "segmentation_free_gop"
            extractor["candidate_rule"]["threshold"] = 1.0
            extractor["candidate_rule"][
                "possible_relation_candidate_emission_enabled"
            ] = True
            extractor["generic_repeated_relation"]["minimum_rule"] = {
                "minimum": 1
            }
            extractor["generic_repeated_relation"][
                "candidate_emission_enabled"
            ] = True
            extractor["evidence_boundaries"]["held_out_accessed"] = True
            extractor["downstream_boundaries"]["coaching"] = True

        errors = validate_contract(changed(self.contract, update))

        self.assertTrue(any("exact no-selection" in error for error in errors))
        self.assertTrue(any("repeated relation policy" in error for error in errors))
        self.assertTrue(any("evidence boundaries" in error for error in errors))
        self.assertTrue(any("downstream boundaries" in error for error in errors))

    def test_candidate_extractor_contract_shape_cannot_be_emptied(self):
        def update(item):
            extractor = item["developer_candidate_extractor"]
            del extractor["artifact"]
            del extractor["selection_record"]
            del extractor["offline_command"]
            extractor["evidence_boundaries"] = {}
            extractor["downstream_boundaries"] = {}

        errors = validate_contract(changed(self.contract, update))

        self.assertTrue(any("missing fields" in error for error in errors))
        self.assertTrue(any("evidence boundaries" in error for error in errors))
        self.assertTrue(any("downstream boundaries" in error for error in errors))

    def test_research_lane_cannot_enter_the_normal_pipeline(self):
        def update(item):
            item["engineering_policy"]["normal_pipeline_activation"] = "allowed"
            item["engineering_policy"][
                "current_solo_or_conversation_target_inference"
            ] = "allowed"
            item["task_policy"]["normal_pipeline_task_activation"] = "allowed"
            item["downstream_policy"]["normal_pipeline_extractor_exists"] = True

        errors = validate_contract(changed(self.contract, update))

        self.assertTrue(any("normal_pipeline_activation" in error for error in errors))
        self.assertTrue(
            any("current_solo_or_conversation" in error for error in errors)
        )
        self.assertTrue(
            any("normal pipeline speech sound tasks" in error for error in errors)
        )
        self.assertTrue(
            any("normal_pipeline_extractor_exists" in error for error in errors)
        )

    def test_asr_cannot_create_lexical_intent_or_phone_truth(self):
        def update(item):
            item["claim_boundaries"]["asr_text_is_lexical_intent"] = True
            item["claim_boundaries"]["asr_is_phone_truth"] = True
            item["task_policy"]["elicitation_modes"]["spontaneous_speech"][
                "intended_word_source"
            ] = "asr"

        errors = validate_contract(changed(self.contract, update))

        self.assertGreaterEqual(sum("asr" in error.lower() for error in errors), 3)

    def test_asr_alignment_and_llm_cannot_become_sound_truth(self):
        def update(item):
            separation = item["asr_and_alignment_separation"]
            separation["asr_disagreement_may_create_sound_concern"] = True
            separation["multiple_asr_agreement_is_truth"] = True
            separation["expected_text_forced_alignment_verifies_production"] = True
            separation["llm_may_infer_produced_phone"] = True

        errors = validate_contract(changed(self.contract, update))

        self.assertGreaterEqual(
            sum("asr_and_alignment_separation" in error for error in errors), 4
        )

    def test_language_or_dialect_difference_cannot_become_error(self):
        def update(item):
            policy = item["language_and_variety_policy"]
            policy["single_standard_accent_allowed"] = True
            policy["acceptable_variant_can_be_error"] = True
            policy["unsupported_or_unrepresented_form_behavior"] = "default_error"
            policy["cross_linguistic_transfer_is_disorder"] = True

        errors = validate_contract(changed(self.contract, update))

        self.assertGreaterEqual(
            sum("language_and_variety_policy" in error for error in errors), 4
        )

    def test_one_token_or_asr_error_cannot_create_a_pattern(self):
        def update(item):
            policy = item["pattern_policy"]
            policy["single_opportunity_can_create_pattern"] = True
            policy["asr_errors_can_create_pattern"] = True
            policy["pattern_requires_multiple_words_and_contexts"] = False
            policy["numeric_pattern_thresholds"] = {"minimum": 2}

        errors = validate_contract(changed(self.contract, update))

        self.assertGreaterEqual(sum("pattern_policy" in error for error in errors), 3)
        self.assertTrue(
            any("thresholds cannot be invented" in error for error in errors)
        )

    def test_automatic_relation_cannot_become_reviewed_or_named(self):
        def update(item):
            evidence = item["evidence_model"]
            evidence["automatic_candidate_is_reviewed_target_relation"] = True
            evidence["generic_repeated_relation_is_named_pattern"] = True
            policy = item["pattern_policy"]
            policy["automatic_named_pattern_allowed"] = True
            policy["named_pattern_requires_human_confirmed_target_relations"] = False

        errors = validate_contract(changed(self.contract, update))

        self.assertTrue(any("reviewed target relation" in error for error in errors))
        self.assertTrue(any("generic repeated relation" in error for error in errors))
        self.assertTrue(
            any("automatic_named_pattern_allowed" in error for error in errors)
        )
        self.assertTrue(any("human_confirmed" in error for error in errors))

    def test_human_reference_requires_two_blind_passes_and_disagreement(self):
        def update(item):
            review = item["reference_truth"]["two_pass_production_review"]
            review["independent_reviewers"] = 1
            review["pass_one_blind_to_expected_word"] = False
            review["reviewers_blind_to_automatic_outputs"] = False
            review["disagreements_retained"] = False

        errors = validate_contract(changed(self.contract, update))

        self.assertTrue(any("at least two" in error for error in errors))
        self.assertGreaterEqual(sum("two pass review" in error for error in errors), 3)

    def test_unresolved_variants_and_missing_evidence_remain_unavailable(self):
        def update(item):
            item["reference_truth"]["variant_reference"][
                "unresolved_form_behavior"
            ] = "use_default"
            item["evidence_model"]["missing_evidence_is_zero"] = True
            item["failure_policy"]["unsupported_or_unrepresented_variety"] = (
                "default_error"
            )
            item["failure_policy"]["fallback_to_llm_judgment"] = True

        errors = validate_contract(changed(self.contract, update))

        self.assertTrue(any("unresolved" in error for error in errors))
        self.assertTrue(any("missing_evidence_is_zero" in error for error in errors))
        self.assertTrue(any("unsupported_or_unrepresented_variety" in error
                            for error in errors))
        self.assertTrue(any("fallback_to_llm_judgment" in error for error in errors))

    def test_open_or_licensed_variants_are_engineering_evidence_only(self):
        def update(item):
            variant = item["reference_truth"]["variant_reference"]
            variant[
                "qualified_professional_review_required_for_scientific_or_"
                "product_release"
            ] = False
            variant["developer_reference_variant_role"] = "product_truth"
            benchmark = item["reference_truth"]["engineering_benchmark_reference"]
            benchmark["may_unlock_scientific_or_product_release"] = True
            benchmark["may_define_acceptable_language_or_variety_truth"] = True

        errors = validate_contract(changed(self.contract, update))

        self.assertTrue(any("professional review" in error for error in errors))
        self.assertTrue(any("engineering only" in error for error in errors))
        self.assertGreaterEqual(
            sum("engineering benchmark" in error for error in errors), 2
        )

    def test_unmanifested_or_restricted_sources_cannot_leak_in(self):
        def update(item):
            sources = item["research_sources"]
            sources["source_manifest_required_before_use"] = False
            sources["unmanifested_source_behavior"] = "allow"
            sources["restricted_source_data_may_be_committed"] = True
            sources["participant_exclusive_split_required"] = False
            sources["provider_processing_requires_source_and_provider_terms"] = False
            sources["owner_controls_accounts_purchases_and_terms"] = False
            sources["api_credentials_location"] = "source_code"

        errors = validate_contract(changed(self.contract, update))

        self.assertTrue(any("source_manifest_required" in error for error in errors))
        self.assertTrue(any("unmanifested" in error for error in errors))
        self.assertTrue(any("may not be committed" in error for error in errors))
        self.assertTrue(any("participant_exclusive" in error for error in errors))
        self.assertTrue(any("provider_processing" in error for error in errors))
        self.assertTrue(any("owner_controls" in error for error in errors))
        self.assertTrue(any("credentials" in error for error in errors))

    def test_paid_remote_providers_are_optional_support_not_truth(self):
        def update(item):
            candidates = item["candidate_systems"]
            candidates["remote_provider_required"] = True
            candidates["provider_agreement_is_reference_truth"] = True
            candidates["local_primary_evidence_required"] = False
            candidates["selected_supporting_systems"] = [
                "azure_pronunciation_assessment"
            ]
            candidates["provider_selection_requires_held_out_incremental_value"] = False
            candidates["planned_systems"][4]["state"] = (
                "selected_supporting_evidence"
            )

        errors = validate_contract(changed(self.contract, update))

        self.assertTrue(any("remote provider" in error for error in errors))
        self.assertTrue(any("provider agreement" in error for error in errors))
        self.assertTrue(any("local evidence" in error for error in errors))
        self.assertTrue(any("supporting candidate" in error for error in errors))
        self.assertTrue(any("held out incremental value" in error for error in errors))
        self.assertTrue(any("may not change" in error for error in errors))

    def test_owner_recordings_and_automatic_agreement_cannot_unlock_release(self):
        def update(item):
            item["validation_program"]["adam_recordings_role"] = "population_truth"
            item["validation_program"]["scientific_release_status"] = "passed"
            item["candidate_systems"]["selected_system"] = "current_asr"
            item["claim_boundaries"]["automatic_system_agreement_is_truth"] = True

        errors = validate_contract(changed(self.contract, update))

        self.assertTrue(any("Adam recordings" in error for error in errors))
        self.assertTrue(any("not evaluated" in error for error in errors))
        self.assertTrue(any("no candidate system" in error for error in errors))
        self.assertTrue(any("automatic_system_agreement" in error for error in errors))

    def test_every_product_and_clinical_use_remains_blocked(self):
        def update(item):
            for field in (
                "automatic_candidate_collection",
                "normal_coaching",
                "personal_progress",
                "screening",
                "diagnosis",
                "treatment",
            ):
                item["release_policy"][field] = "allowed"

        errors = validate_contract(changed(self.contract, update))

        self.assertTrue(any("candidate collection" in error for error in errors))
        self.assertGreaterEqual(sum("release_policy" in error for error in errors), 5)

    def test_release_requirements_cannot_drop_human_evidence_or_owner_approval(self):
        def update(item):
            release = item["release_policy"]
            release["engineering_requirements"] = []
            release["scientific_release_requirements"] = []
            release["product_release_requirements"] = []

        errors = validate_contract(changed(self.contract, update))

        self.assertTrue(
            any("engineering release requirements" in error for error in errors)
        )
        self.assertTrue(
            any("scientific release requirements" in error for error in errors)
        )
        self.assertTrue(
            any("product release requirements" in error for error in errors)
        )


if __name__ == "__main__":
    unittest.main()
