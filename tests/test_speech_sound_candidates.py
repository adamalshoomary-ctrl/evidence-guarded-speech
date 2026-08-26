import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from speech_sound_patterns.candidate_artifact import (
    ALLOWED_CANDIDATE_STATES,
    CONTRACT_PATH,
    CONTRACT_SHA256,
    RULE_STATUS,
    CandidateArtifactError,
    _state_for_opportunity,
    build_artifact,
    load_candidate_contract,
    summarize_repeated_relations,
    validate_candidate_artifact,
    validate_candidate_contract,
    validate_trial_manifest,
    write_artifact,
)
from speech_sound_patterns.candidate_evidence import (
    REPORT_PATH,
    _assert_source_bindings,
    _load_frozen,
    build_candidate_evidence_report,
    validate_candidate_evidence_report,
)
from speech_sound_patterns.extract_candidates import (
    CANDIDATE_ROOT,
    MANIFEST_ROOT,
    PRIVATE_RESEARCH_ROOT,
    extract,
)
from speech_sound_patterns.feasibility import canonical_json_bytes, file_sha256
from speech_sound_patterns.prompt_pack_validate import PACK_PATH
from speech_sound_patterns.validate_candidates import (
    validate_artifact_against_manifest,
)

from tests.research_data import (
    needs_repository_history,
    needs_research_data,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PROMPT_PACK = json.loads(PACK_PATH.read_text(encoding="utf-8"))
PACK_OPPORTUNITY_COUNTS = {
    item["word"]: len(item["opportunities"]) for item in PROMPT_PACK["words"]
}


def changed(document, update):
    result = copy.deepcopy(document)
    update(result)
    return result


def proposal(
    opportunity_index=0,
    relation_type="substitution",
    alternative_phone="b",
    *,
    status="proposal",
):
    return {
        "opportunity_index": opportunity_index,
        "status": status,
        "relation_type": relation_type if status == "proposal" else None,
        "alternative_phone": (
            alternative_phone
            if status == "proposal" and relation_type == "substitution"
            else None
        ),
        "feature_delta": (
            [
                {
                    "feature": "voi",
                    "expected": -1,
                    "alternative": 1,
                }
            ]
            if status == "proposal" and relation_type == "substitution"
            else []
        ),
        "score": -3.25 if status == "proposal" else None,
        "uncertainty": {
            "confidence_is_probability": False,
            "value": None,
            "basis": "synthetic_structure_only",
        },
        "raw_output_ref": None,
    }


def local_system(system_id="local_a", *, status="available", proposals=None):
    return {
        "system_id": system_id,
        "status": status,
        "system_version": "fixture_v1",
        "mapping_version": None,
        "raw_output_ref": None,
        "opportunities": list(proposals or []),
    }


def trial(
    *,
    word="pumpkin",
    quality="pass",
    systems=None,
    asr_word=None,
    providers=None,
    insertions=None,
):
    reasons = [] if quality == "pass" else [f"fixture_{quality}"]
    expanded_systems = copy.deepcopy(
        [local_system()] if systems is None else systems
    )
    for system in expanded_systems:
        if system["status"] != "available":
            continue
        recorded = {
            item["opportunity_index"] for item in system["opportunities"]
        }
        for opportunity_index in range(PACK_OPPORTUNITY_COUNTS[word]):
            if opportunity_index not in recorded:
                system["opportunities"].append(
                    proposal(opportunity_index, status="no_proposal")
                )
        system["opportunities"].sort(key=lambda item: item["opportunity_index"])
    return {
        "identifiers": {
            "participant_id": "fixture_participant",
            "session_id": "fixture_session",
            "attempt_id": "fixture_attempt",
            "trial_id": f"fixture_trial_{word}",
            "stimulus_id": word,
        },
        "elicitation_mode": "written_word",
        "intended_word": word,
        "intended_word_source": "versioned_presented_stimulus",
        "audio": {
            "recording_id": f"fixture_recording_{word}",
            "content_sha256": "a" * 64,
            "duration_s": 1.0,
            "path": None,
        },
        "audio_quality": {
            "status": quality,
            "reasons": reasons,
            "evidence_ref": None,
        },
        "source": {
            "source_id": "synthetic_fixture",
            "project_split": "functional_integration",
        },
        "raw_evidence": {
            "asr": {
                "status": "available",
                "system_id": "fixture_asr",
                "system_version": "fixture_v1",
                "word_hypothesis": word if asr_word is None else asr_word,
                "raw_output_ref": None,
            },
            "alignment": {
                "status": "unavailable",
                "system_id": "fixture_alignment",
                "system_version": "fixture_v1",
                "source_interval": None,
                "opportunity_intervals": [],
                "raw_output_ref": None,
            },
            "local_phone_systems": (
                expanded_systems
            ),
            "cached_providers": list(providers or []),
            "insertions": list(insertions or []),
        },
    }


def manifest(**trial_changes):
    return {
        "schema_version": "1.0.0",
        "manifest_id": "speech_sound_candidate_trials_v1",
        "manifest_version": "1.0.0",
        "scope": {
            "developer_only": True,
            "normal_pipeline": False,
            "network_access": False,
            "held_out_access": False,
        },
        "project_split": "functional_integration",
        "prompt_pack": {
            "pack_id": "speech_sound_patterns_research_prompt_pack_v1",
            "pack_version": "1.0.0",
            "sha256": file_sha256(PACK_PATH),
        },
        "task": {
            "task_id": "controlled_word_research_en_v1",
            "status": "developer_research_only_not_product",
            "elicitation_mode": "written_word",
            "product_task_active": False,
        },
        "source": {
            "source_id": "synthetic_fixture",
            "manifest_state": "synthetic_fixture",
            "licence_state": "not_applicable_synthetic",
            "role": "structural_testing_only",
            "external_transfer": False,
        },
        "trials": [trial(**trial_changes)],
    }


def adam_manifest(evidence_path, *, evidence_sha=None):
    evidence_path = Path(evidence_path)
    digest = evidence_sha or file_sha256(evidence_path)
    try:
        path_text = str(evidence_path.resolve().relative_to(REPOSITORY_ROOT))
    except ValueError:
        path_text = str(evidence_path.resolve())
    reference = {"path": path_text, "sha256": digest}
    document = manifest()
    document["source"] = {
        "source_id": "adam_controlled_recordings",
        "manifest_state": "owner_controlled_local",
        "licence_state": "owner_authorised_local_functional_integration",
        "role": "functional_integration_only",
        "external_transfer": False,
    }
    candidate_trial = document["trials"][0]
    candidate_trial["source"]["source_id"] = "adam_controlled_recordings"
    candidate_trial["audio"]["path"] = path_text
    candidate_trial["audio"]["content_sha256"] = digest
    candidate_trial["audio_quality"]["evidence_ref"] = copy.deepcopy(reference)
    raw = candidate_trial["raw_evidence"]
    raw["asr"]["raw_output_ref"] = copy.deepcopy(reference)
    raw["alignment"]["raw_output_ref"] = copy.deepcopy(reference)
    for system in raw["local_phone_systems"]:
        system["raw_output_ref"] = copy.deepcopy(reference)
    return document


@needs_research_data
class CandidateContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = load_candidate_contract()

    def test_frozen_candidate_contract_is_valid_and_checksum_bound(self):
        self.assertEqual(file_sha256(CONTRACT_PATH), CONTRACT_SHA256)
        self.assertEqual(validate_candidate_contract(self.contract), [])

    def test_no_model_mapping_feature_threshold_or_provider_is_carried_forward(self):
        barred = " ".join(self.contract["carried_forward"]["not_carried_forward"])
        for phrase in (
            "operating point",
            "score threshold",
            "expected to produced phone mapping",
            "feature relation rule",
            "provider configuration",
            "selected candidate system",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, barred)

    def test_contract_cannot_enable_relation_or_repeated_emission(self):
        unsafe = changed(
            self.contract,
            lambda item: item["state_resolution"].update(
                {"possible_relation_candidate_emission_enabled": True}
            ),
        )
        unsafe["generic_repeated_relation_policy"]["emission_enabled"] = True
        unsafe["generic_repeated_relation_policy"]["minimum_rule"] = {
            "minimum_support": 1
        }

        errors = validate_candidate_contract(unsafe)

        self.assertTrue(any("possible relation" in error for error in errors))
        self.assertTrue(any("repeated relation emission" in error for error in errors))
        self.assertTrue(any("minimum cannot be invented" in error for error in errors))

    def test_held_out_owner_and_synthetic_evidence_cannot_fill_the_gap(self):
        unsafe = copy.deepcopy(self.contract)
        gate = unsafe["evidence_adequacy_gate"]
        gate["held_out_access_after_failure"] = True
        gate["owner_recordings_may_fill_the_evidence_gap"] = True
        gate["synthetic_fixtures_may_fill_the_evidence_gap"] = True

        errors = validate_candidate_contract(unsafe)

        self.assertGreaterEqual(sum("evidence adequacy" in error for error in errors), 3)

    def test_manifest_rejects_pipeline_held_out_and_asr_intent(self):
        unsafe = manifest()
        unsafe["scope"]["normal_pipeline"] = True
        unsafe["scope"]["held_out_access"] = True
        unsafe["project_split"] = "held_out"
        unsafe["trials"][0]["intended_word_source"] = "asr"

        errors = validate_trial_manifest(unsafe)

        self.assertTrue(any("normal_pipeline" in error for error in errors))
        self.assertTrue(any("held_out" in error or "held-out" in error for error in errors))
        self.assertTrue(any("ASR" in error for error in errors))

    def test_source_profiles_are_exact_and_cannot_claim_selection_splits(self):
        unsafe = manifest()
        unsafe["project_split"] = "development"
        unsafe["trials"][0]["source"]["project_split"] = "development"
        unsafe["source"]["licence_state"] = "trust_me"

        errors = validate_trial_manifest(unsafe)

        self.assertTrue(any("source profile changed" in error for error in errors))
        self.assertTrue(any("cannot claim this project split" in error for error in errors))

    def test_sentence_corpus_cannot_masquerade_as_controlled_word_trials(self):
        unsafe = manifest()
        unsafe["source"]["source_id"] = "speechocean762"
        unsafe["trials"][0]["source"]["source_id"] = "speechocean762"

        errors = validate_trial_manifest(unsafe)

        self.assertTrue(any("source is not registered" in error for error in errors))

    def test_synthetic_fixture_cannot_reference_real_evidence(self):
        unsafe = manifest()
        unsafe["trials"][0]["audio"]["path"] = "private.wav"

        errors = validate_trial_manifest(unsafe)

        self.assertTrue(any("cannot reference real evidence" in error for error in errors))

    def test_real_recording_requires_checksum_bound_evidence(self):
        unsafe = manifest()
        unsafe["source"] = {
            "source_id": "adam_controlled_recordings",
            "manifest_state": "owner_controlled_local",
            "licence_state": "owner_authorised_local_functional_integration",
            "role": "functional_integration_only",
            "external_transfer": False,
        }
        unsafe["trials"][0]["source"][
            "source_id"
        ] = "adam_controlled_recordings"

        errors = validate_trial_manifest(unsafe)

        self.assertTrue(any("private audio path" in error for error in errors))
        self.assertTrue(any("checksum bound private reference" in error for error in errors))


class CandidateStateTests(unittest.TestCase):
    @needs_research_data
    def test_substitution_proposal_is_preserved_but_not_promoted(self):
        artifact = build_artifact(
            manifest(
                systems=[
                    local_system(proposals=[proposal(relation_type="substitution")])
                ]
            )
        )
        item = artifact["trials"][0]["opportunities"][0]

        self.assertEqual(item["candidate_state"], "insufficient_evidence")
        self.assertEqual(item["candidate_relation"]["relation_type"], None)
        self.assertEqual(
            item["candidate_relation"]["raw_proposals"][0]["relation_type"],
            "substitution",
        )

    @needs_research_data
    def test_deletion_proposal_is_preserved_but_not_promoted(self):
        artifact = build_artifact(
            manifest(
                systems=[
                    local_system(
                        proposals=[
                            proposal(
                                relation_type="deletion",
                                alternative_phone=None,
                            )
                        ]
                    )
                ]
            )
        )
        item = artifact["trials"][0]["opportunities"][0]

        self.assertEqual(item["candidate_state"], "insufficient_evidence")
        self.assertEqual(
            item["candidate_relation"]["raw_proposals"][0]["relation_type"],
            "deletion",
        )
        self.assertIsNone(item["candidate_relation"]["relation_type"])

    @needs_research_data
    def test_insertion_stays_separate_unsupported_and_out_of_the_denominator(self):
        insertion = {
            "relation_type": "insertion",
            "between_opportunities": [0, 1],
            "alternative_phone": "s",
            "source_interval": {"start_s": 0.2, "end_s": 0.3},
            "raw_output_ref": None,
        }
        artifact = build_artifact(manifest(insertions=[insertion]))
        built = artifact["trials"][0]["insertions"][0]

        self.assertEqual(built["candidate_state"], "unsupported")
        self.assertIsNone(built["candidate_relation"]["relation_type"])
        self.assertEqual(artifact["denominators"]["insertion_observations"], 1)
        self.assertEqual(
            artifact["denominators"]["insertions_in_expected_sound_denominator"],
            0,
        )
        self.assertEqual(
            artifact["denominators"]["expected_sound_opportunities"],
            5,
        )

    @needs_research_data
    def test_documented_reference_disagreement_is_a_known_variant(self):
        variant_pack = copy.deepcopy(PROMPT_PACK)
        child = next(
            item for item in variant_pack["words"] if item["word"] == "child"
        )
        child["opportunities"][1] = {
            "opportunity": 1,
            "phonemes_documented": ["l", "w"],
            "state": "unscorable",
            "reason": "documented_variant_disagreement",
        }

        state, reason = _state_for_opportunity(
            trial(word="child"),
            child["opportunities"][1],
            [],
        )

        self.assertEqual(state, "known_reference_variant")
        self.assertEqual(reason, "documented_reference_variant")
        with self.assertRaisesRegex(
            CandidateArtifactError, "differs from the frozen prompt pack"
        ):
            build_artifact(manifest(word="child"), pack=variant_pack)

    @needs_research_data
    def test_static_unsupported_context_never_becomes_zero_or_normal(self):
        artifact = build_artifact(manifest(word="child"))
        refused = artifact["trials"][0]["opportunities"][1]

        self.assertEqual(refused["candidate_state"], "unsupported")
        self.assertEqual(refused["abstention_reason"], "coda_l_vocalisation")
        self.assertNotIn(refused["candidate_state"], {"normal", "correct", "zero"})

    @needs_research_data
    def test_materially_different_system_proposals_become_conflict_without_voting(self):
        systems = [
            local_system(
                "local_a",
                proposals=[proposal(relation_type="substitution", alternative_phone="b")],
            ),
            local_system(
                "local_b",
                proposals=[proposal(relation_type="deletion", alternative_phone=None)],
            ),
        ]
        item = build_artifact(manifest(systems=systems))["trials"][0][
            "opportunities"
        ][0]

        self.assertEqual(item["candidate_state"], "candidate_system_conflict")
        self.assertEqual(len(item["candidate_relation"]["raw_proposals"]), 2)
        self.assertIsNone(item["candidate_relation"]["relation_type"])

    @needs_research_data
    def test_bad_audio_makes_sound_and_word_evidence_unavailable(self):
        artifact = build_artifact(manifest(quality="fail"))

        self.assertEqual(
            artifact["trials"][0]["word_evidence"]["candidate_state"],
            "unavailable",
        )
        self.assertTrue(
            all(
                item["candidate_state"] == "unavailable"
                for item in artifact["trials"][0]["opportunities"]
            )
        )

    @needs_research_data
    def test_missing_local_model_is_unavailable_and_preserved(self):
        artifact = build_artifact(
            manifest(systems=[local_system(status="unavailable")])
        )
        opportunity = artifact["trials"][0]["opportunities"][0]

        self.assertEqual(opportunity["candidate_state"], "unavailable")
        self.assertEqual(
            opportunity["raw_evidence"]["local_phone_systems"][0]["status"],
            "unavailable",
        )

    @needs_research_data
    def test_per_opportunity_unsupported_and_unavailable_stay_distinct(self):
        unsupported = build_artifact(
            manifest(
                systems=[
                    local_system(
                        proposals=[proposal(status="unsupported")]
                    )
                ]
            )
        )
        unavailable = build_artifact(
            manifest(
                systems=[
                    local_system(
                        proposals=[proposal(status="unavailable")]
                    )
                ]
            )
        )

        self.assertEqual(
            unsupported["trials"][0]["opportunities"][0]["candidate_state"],
            "unsupported",
        )
        self.assertEqual(
            unavailable["trials"][0]["opportunities"][0]["candidate_state"],
            "unavailable",
        )

    @needs_research_data
    def test_cached_provider_failure_cannot_erase_usable_local_evidence(self):
        provider = {
            "system_id": "cached_optional_provider",
            "status": "provider_failure",
            "request_made_in_this_run": False,
            "raw_output_ref": None,
        }
        artifact = build_artifact(manifest(providers=[provider]))
        opportunity = artifact["trials"][0]["opportunities"][0]

        self.assertEqual(opportunity["candidate_state"], "insufficient_evidence")
        self.assertEqual(
            opportunity["raw_evidence"]["cached_providers"][0]["status"],
            "provider_failure",
        )
        self.assertIn(
            "optional cached provider evidence was unavailable",
            opportunity["alternative_explanations"],
        )

    @needs_research_data
    def test_provider_request_in_this_run_is_rejected(self):
        provider = {
            "system_id": "unsafe_provider",
            "status": "provider_failure",
            "request_made_in_this_run": True,
            "raw_output_ref": None,
        }
        errors = validate_trial_manifest(manifest(providers=[provider]))

        self.assertTrue(any("provider request" in error for error in errors))

    @needs_research_data
    def test_orphan_proposal_and_alignment_indices_are_rejected(self):
        unsafe = manifest(
            systems=[local_system(proposals=[proposal(opportunity_index=99)])]
        )
        unsafe["trials"][0]["raw_evidence"]["alignment"][
            "opportunity_intervals"
        ] = [{"opportunity_index": 99, "start_s": 0.1, "end_s": 0.2}]

        errors = validate_trial_manifest(unsafe)

        self.assertTrue(any("proposal opportunity index leaves" in error for error in errors))
        self.assertTrue(any("alignment interval index" in error for error in errors))

    @needs_research_data
    def test_unavailable_system_cannot_smuggle_a_relation_proposal(self):
        unsafe = manifest(
            systems=[
                local_system(
                    status="unavailable",
                    proposals=[proposal()],
                )
            ]
        )

        errors = validate_trial_manifest(unsafe)

        self.assertTrue(
            any("unavailable system cannot carry a proposal" in error for error in errors)
        )

    @needs_research_data
    def test_available_system_must_record_every_pack_opportunity(self):
        unsafe = manifest()
        unsafe["trials"][0]["raw_evidence"]["local_phone_systems"][0][
            "opportunities"
        ].pop()

        errors = validate_trial_manifest(unsafe)

        self.assertTrue(
            any("must record every prompt pack opportunity" in error for error in errors)
        )

    @needs_research_data
    def test_malformed_raw_proposal_is_rejected_without_crashing(self):
        unsafe = manifest(
            systems=[local_system(proposals=[proposal()])]
        )
        raw_proposal = unsafe["trials"][0]["raw_evidence"][
            "local_phone_systems"
        ][0]["opportunities"][0]
        raw_proposal["feature_delta"] = [[]]
        raw_proposal["score"] = True

        errors = validate_trial_manifest(unsafe)

        self.assertTrue(any("feature delta" in error for error in errors))
        self.assertTrue(any("score" in error for error in errors))

    @needs_research_data
    def test_malformed_local_system_is_rejected_without_crashing(self):
        unsafe = manifest()
        unsafe["trials"][0]["raw_evidence"]["local_phone_systems"] = [
            "not an object"
        ]

        errors = validate_trial_manifest(unsafe)

        self.assertTrue(any("local system" in error for error in errors))

    @needs_research_data
    def test_non_json_and_non_finite_manifest_values_fail_closed(self):
        unsafe_values = []

        bad_identifier = manifest()
        bad_identifier["trials"][0]["identifiers"]["trial_id"] = []
        unsafe_values.append(bad_identifier)

        bad_index = manifest()
        bad_index["trials"][0]["raw_evidence"]["local_phone_systems"][0][
            "opportunities"
        ][0]["opportunity_index"] = []
        unsafe_values.append(bad_index)

        bad_duration = manifest()
        bad_duration["trials"][0]["audio"]["duration_s"] = float("nan")
        unsafe_values.append(bad_duration)

        bad_uncertainty = manifest()
        bad_uncertainty["trials"][0]["raw_evidence"][
            "local_phone_systems"
        ][0]["opportunities"][0]["uncertainty"]["probability"] = 0.99
        unsafe_values.append(bad_uncertainty)

        for unsafe in unsafe_values:
            with self.subTest(unsafe=unsafe):
                self.assertTrue(validate_trial_manifest(unsafe))

    @needs_research_data
    def test_cached_provider_record_cannot_add_uncontracted_fields(self):
        provider = {
            "system_id": "cached_provider",
            "status": "provider_failure",
            "request_made_in_this_run": False,
            "raw_output_ref": None,
            "fresh_network_response": {"unsafe": True},
        }

        errors = validate_trial_manifest(manifest(providers=[provider]))

        self.assertTrue(any("provider evidence changed shape" in error for error in errors))

    @needs_research_data
    def test_asr_disagreement_stays_one_word_level_unit(self):
        artifact = build_artifact(manifest(asr_word="something_else"))
        built = artifact["trials"][0]

        self.assertEqual(
            built["word_evidence"]["candidate_state"],
            "asr_only_disagreement",
        )
        self.assertFalse(built["word_evidence"]["sound_attribution_allowed"])
        self.assertTrue(built["word_evidence"]["manual_review_trigger"])
        self.assertNotIn(
            "asr_only_disagreement",
            {item["candidate_state"] for item in built["opportunities"]},
        )

    @needs_research_data
    def test_no_selected_rule_means_zero_relation_candidates(self):
        artifact = build_artifact(
            manifest(systems=[local_system(proposals=[proposal()])])
        )

        self.assertEqual(artifact["candidate_rule"]["status"], RULE_STATUS)
        self.assertFalse(
            artifact["candidate_rule"][
                "possible_relation_candidate_emission_enabled"
            ]
        )
        self.assertEqual(
            artifact["denominators"]["automatic_state_counts"][
                "possible_relation_candidate"
            ],
            0,
        )
        self.assertEqual(artifact["repeated_relation_summary"]["candidates"], [])


def repeated_unit(
    unit_id,
    word,
    context,
    audio_sha,
    *,
    recording=None,
    opportunity_index=0,
    state="possible_relation_candidate",
    reference_state="scorable",
    feature_relation=None,
):
    return {
        "opportunity_id": unit_id,
        "participant_id": "participant_a",
        "session_id": f"session_{unit_id}",
        "attempt_id": f"attempt_{unit_id}",
        "trial_id": f"trial_{unit_id}",
        "recording_id": recording or f"recording_{unit_id}",
        "audio_content_sha256": audio_sha,
        "opportunity_index": opportunity_index,
        "task_id": "controlled_word_research_en_v1",
        "pack_id": "speech_sound_patterns_research_prompt_pack_v1",
        "elicitation_mode": "written_word",
        "stimulus_id": word,
        "position": context,
        "context": {"position": context},
        "expected_phone": "p",
        "reference_variants": {
            "pack_opportunity_state": reference_state,
        },
        "candidate_state": state,
        "candidate_relation": {
            "relation_type": "substitution",
            "expected_phone": "p",
            "alternative_phone": "b",
            "feature_relation": (
                [
                    {
                        "feature": "voi",
                        "expected": -1,
                        "alternative": 1,
                    }
                ]
                if feature_relation is None
                else feature_relation
            ),
        },
    }


class RepeatedRelationTests(unittest.TestCase):
    def test_one_token_never_creates_repeated_relation(self):
        summary = summarize_repeated_relations(
            [repeated_unit("one", "pumpkin", "initial", "a" * 64)],
            rule=None,
        )

        self.assertEqual(summary["candidates"], [])
        self.assertFalse(
            summary["audited_groups"][0]["minimum_shape_satisfied"]
        )

    def test_one_word_never_creates_repeated_relation(self):
        units = [
            repeated_unit("one", "pumpkin", "initial", "a" * 64),
            repeated_unit("two", "pumpkin", "medial", "b" * 64),
        ]
        summary = summarize_repeated_relations(units, rule=None)

        self.assertEqual(summary["candidates"], [])
        self.assertEqual(summary["audited_groups"][0]["distinct_words"], 1)

    def test_duplicate_same_token_counts_once(self):
        units = [
            repeated_unit("one", "pumpkin", "initial", "a" * 64),
            repeated_unit("two", "safe", "final", "a" * 64),
        ]
        summary = summarize_repeated_relations(units, rule=None)

        self.assertEqual(summary["audited_groups"][0]["support_count"], 1)
        self.assertEqual(summary["candidates"], [])

    def test_distinct_tokens_in_one_recording_remain_distinct(self):
        units = [
            repeated_unit(
                "one",
                "pumpkin",
                "initial",
                "a" * 64,
                recording="shared",
                opportunity_index=0,
            ),
            repeated_unit(
                "two",
                "safe",
                "final",
                "a" * 64,
                recording="shared",
                opportunity_index=1,
            ),
        ]

        group = summarize_repeated_relations(
            units, rule=None
        )["audited_groups"][0]

        self.assertEqual(group["support_count"], 2)
        self.assertEqual(group["distinct_recordings"], 1)
        self.assertFalse(group["minimum_shape_satisfied"])

    def test_two_words_and_contexts_are_audited_but_cannot_emit(self):
        units = [
            repeated_unit("one", "pumpkin", "initial", "a" * 64),
            repeated_unit("two", "safe", "final", "b" * 64),
        ]
        summary = summarize_repeated_relations(units, rule=None)

        self.assertEqual(summary["candidates"], [])
        self.assertFalse(summary["emission_enabled"])
        self.assertTrue(
            summary["audited_groups"][0]["minimum_shape_satisfied"]
        )

    def test_arbitrary_rule_dictionary_is_rejected(self):
        with self.assertRaises(CandidateArtifactError):
            summarize_repeated_relations(
                [repeated_unit("one", "pumpkin", "initial", "a" * 64)],
                rule={"minimum_support": 1},
            )

    def test_asr_conflict_unsupported_and_unavailable_never_count_as_support(self):
        units = [
            repeated_unit(
                state,
                f"word_{state}",
                state,
                str(index) * 64,
                state=state,
            )
            for index, state in enumerate(
                (
                    "asr_only_disagreement",
                    "candidate_system_conflict",
                    "unsupported",
                    "unavailable",
                ),
                start=1,
            )
        ]

        summary = summarize_repeated_relations(units, rule=None)

        self.assertEqual(summary["audited_groups"], [])
        self.assertEqual(summary["candidates"], [])

    def test_missing_feature_relation_cannot_form_a_group(self):
        unit = repeated_unit(
            "one",
            "pumpkin",
            "initial",
            "a" * 64,
            feature_relation=[],
        )

        summary = summarize_repeated_relations([unit], rule=None)

        self.assertEqual(summary["audited_groups"], [])

    def test_distinct_feature_relations_never_merge(self):
        first = repeated_unit("one", "pumpkin", "initial", "a" * 64)
        second = repeated_unit(
            "two",
            "safe",
            "final",
            "b" * 64,
            feature_relation=[
                {"feature": "cont", "expected": -1, "alternative": 1}
            ],
        )

        summary = summarize_repeated_relations([first, second], rule=None)

        self.assertEqual(len(summary["audited_groups"]), 2)

    def test_consistency_uses_the_same_token_identity_for_both_sides(self):
        units = [
            repeated_unit("support_one", "pumpkin", "initial", "a" * 64),
            repeated_unit("support_duplicate", "pumpkin", "initial", "a" * 64),
            repeated_unit("support_two", "safe", "final", "b" * 64),
            repeated_unit(
                "eligible_no_support",
                "path",
                "medial",
                "c" * 64,
                state="insufficient_evidence",
            ),
        ]

        group = summarize_repeated_relations(
            units, rule=None
        )["audited_groups"][0]

        self.assertEqual(group["support_count"], 2)
        self.assertEqual(group["eligible_opportunity_count"], 3)
        self.assertEqual(group["consistency"]["numerator"], 2)
        self.assertEqual(group["consistency"]["denominator"], 3)
        self.assertAlmostEqual(group["consistency"]["value"], 2 / 3)

    def test_unscorable_known_variant_is_excluded_from_denominator(self):
        units = [
            repeated_unit("support", "pumpkin", "initial", "a" * 64),
            repeated_unit(
                "variant",
                "safe",
                "final",
                "b" * 64,
                state="known_reference_variant",
                reference_state="unscorable",
            ),
        ]

        group = summarize_repeated_relations(
            units, rule=None
        )["audited_groups"][0]

        self.assertEqual(group["eligible_opportunity_count"], 1)
        self.assertEqual(
            group["denominator_exclusion_counts"]["known_reference_variant"],
            1,
        )

    def test_unscorable_possible_relation_never_counts_as_support(self):
        unit = repeated_unit(
            "unsafe",
            "pumpkin",
            "initial",
            "a" * 64,
            reference_state="unscorable",
        )

        summary = summarize_repeated_relations([unit], rule=None)

        self.assertEqual(summary["audited_groups"], [])

    def test_relation_expected_phone_must_match_the_opportunity(self):
        unit = repeated_unit("unsafe", "pumpkin", "initial", "a" * 64)
        unit["candidate_relation"]["expected_phone"] = "t"

        summary = summarize_repeated_relations([unit], rule=None)

        self.assertEqual(summary["audited_groups"], [])

    def test_feature_relation_order_is_canonical(self):
        first = repeated_unit(
            "one",
            "pumpkin",
            "initial",
            "a" * 64,
            feature_relation=[
                {"feature": "voi", "expected": -1, "alternative": 1},
                {"feature": "cont", "expected": -1, "alternative": 1},
            ],
        )
        second = repeated_unit(
            "two",
            "safe",
            "final",
            "b" * 64,
            feature_relation=[
                {"feature": "cont", "expected": -1, "alternative": 1},
                {"feature": "voi", "expected": -1, "alternative": 1},
            ],
        )

        summary = summarize_repeated_relations([first, second], rule=None)

        self.assertEqual(len(summary["audited_groups"]), 1)
        self.assertEqual(summary["audited_groups"][0]["support_count"], 2)

    def test_deletion_groups_without_fake_feature_values(self):
        unit = repeated_unit("one", "pumpkin", "initial", "a" * 64)
        relation = unit["candidate_relation"]
        relation["relation_type"] = "deletion"
        relation["alternative_phone"] = None
        relation["feature_relation"] = []

        group = summarize_repeated_relations(
            [unit], rule=None
        )["audited_groups"][0]

        self.assertEqual(group["relation_key"]["relation_type"], "deletion")
        self.assertEqual(group["relation_key"]["feature_relation"], [])

    def test_insertion_never_enters_expected_sound_repetition(self):
        unit = repeated_unit("one", "pumpkin", "initial", "a" * 64)
        unit["candidate_relation"]["relation_type"] = "insertion"

        summary = summarize_repeated_relations([unit], rule=None)

        self.assertEqual(summary["audited_groups"], [])

    def test_generator_input_is_materialized_once(self):
        units = (
            unit
            for unit in [
                repeated_unit("one", "pumpkin", "initial", "a" * 64),
                repeated_unit("two", "safe", "final", "b" * 64),
            ]
        )

        group = summarize_repeated_relations(
            units, rule=None
        )["audited_groups"][0]

        self.assertEqual(group["support_count"], 2)
        self.assertEqual(group["eligible_opportunity_count"], 2)

    def test_malformed_token_identity_fails_deliberately(self):
        unit = repeated_unit("one", "pumpkin", "initial", "a" * 64)
        unit["opportunity_index"] = []

        with self.assertRaises(CandidateArtifactError):
            summarize_repeated_relations([unit], rule=None)


class ArtifactValidationTests(unittest.TestCase):
    def setUp(self):
        self.artifact = build_artifact(
            manifest(systems=[local_system(proposals=[proposal()])])
        )

    @needs_research_data
    def test_built_artifact_is_valid_and_deterministic(self):
        rebuilt = build_artifact(
            manifest(systems=[local_system(proposals=[proposal()])])
        )

        self.assertEqual(validate_candidate_artifact(self.artifact), [])
        self.assertEqual(
            canonical_json_bytes(self.artifact),
            canonical_json_bytes(rebuilt),
        )

    @needs_research_data
    def test_artifact_write_is_complete_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "speech_sound_candidates.json"
            write_artifact(self.artifact, path)
            original = path.read_bytes()

            with self.assertRaises(CandidateArtifactError):
                write_artifact(
                    changed(
                        self.artifact,
                        lambda item: item.update({"status": "unsafe"}),
                    ),
                    path,
                )

            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(
                sorted(item.name for item in Path(directory).iterdir()),
                ["speech_sound_candidates.json"],
            )

    @needs_research_data
    def test_validator_recomputes_state_and_raw_proposals(self):
        unsafe = copy.deepcopy(self.artifact)
        opportunity = unsafe["trials"][0]["opportunities"][0]
        opportunity["candidate_state"] = "possible_relation_candidate"
        opportunity["raw_evidence"]["local_phone_proposals"] = []

        errors = validate_candidate_artifact(unsafe)

        self.assertTrue(any("possible relation" in error for error in errors))
        self.assertTrue(any("proposals do not match" in error for error in errors))
        self.assertTrue(any("frozen precedence" in error for error in errors))

    @needs_research_data
    def test_validator_rejects_inconsistent_trial_and_opportunity_raw_evidence(self):
        unsafe = copy.deepcopy(self.artifact)
        unsafe["trials"][0]["opportunities"][1]["raw_evidence"][
            "local_phone_systems"
        ][0]["status"] = "unavailable"

        errors = validate_candidate_artifact(unsafe)

        self.assertTrue(
            any("differs from trial raw evidence" in error for error in errors)
        )

    @needs_research_data
    def test_manifest_backed_validation_rejects_self_consistent_raw_evidence_edit(self):
        unsafe = copy.deepcopy(self.artifact)
        changed_asr = copy.deepcopy(
            unsafe["trials"][0]["raw_evidence"]["asr"]
        )
        changed_asr["word_hypothesis"] = "changed"
        unsafe["trials"][0]["raw_evidence"]["asr"] = changed_asr
        unsafe["trials"][0]["word_evidence"]["raw_asr"] = copy.deepcopy(
            changed_asr
        )
        for opportunity in unsafe["trials"][0]["opportunities"]:
            opportunity["raw_evidence"]["asr"] = copy.deepcopy(changed_asr)

        self.assertEqual(validate_candidate_artifact(unsafe), [])
        errors = validate_artifact_against_manifest(
            unsafe,
            manifest(systems=[local_system(proposals=[proposal()])]),
        )

        self.assertTrue(any("supplied manifest" in error for error in errors))

    @needs_research_data
    def test_validator_recomputes_denominators(self):
        unsafe = copy.deepcopy(self.artifact)
        unsafe["denominators"]["expected_sound_opportunities"] = 999
        unsafe["denominators"]["automatic_state_counts"][
            "possible_relation_candidate"
        ] = 1

        errors = validate_candidate_artifact(unsafe)

        self.assertTrue(any("denominators do not recompute" in error for error in errors))

    @needs_research_data
    def test_artifact_validator_rejects_malformed_raw_proposal_without_crashing(self):
        unsafe = copy.deepcopy(self.artifact)
        unsafe["trials"][0]["raw_evidence"]["local_phone_systems"][0][
            "opportunities"
        ][0]["feature_delta"] = [[]]

        errors = validate_candidate_artifact(unsafe)

        self.assertTrue(any("feature delta" in error for error in errors))

    @needs_research_data
    def test_artifact_validator_rejects_malformed_identifiers_without_crashing(self):
        unsafe = copy.deepcopy(self.artifact)
        unsafe["trials"][0]["identifiers"]["trial_id"] = []

        errors = validate_candidate_artifact(unsafe)

        self.assertTrue(any("identifiers" in error for error in errors))

    @needs_research_data
    def test_artifact_validator_turns_nested_type_errors_into_invalid_results(self):
        malformed_trial = copy.deepcopy(self.artifact)
        malformed_trial["trials"][0] = None
        malformed_relation = copy.deepcopy(self.artifact)
        malformed_relation["trials"][0]["opportunities"][0][
            "candidate_relation"
        ] = "not an object"

        for unsafe in (malformed_trial, malformed_relation):
            with self.subTest(unsafe=unsafe):
                errors = validate_candidate_artifact(unsafe)
                self.assertTrue(errors)
                self.assertTrue(
                    any("structurally invalid" in error for error in errors)
                )

    @needs_research_data
    def test_validator_rejects_selected_rule_named_output_and_reviewed_truth(self):
        unsafe = copy.deepcopy(self.artifact)
        unsafe["candidate_rule"]["selected_threshold"] = 1.0
        unsafe["repeated_relation_summary"]["candidates"] = [
            {"state": "repeated_relation_candidate"}
        ]
        item = unsafe["trials"][0]["opportunities"][0]
        item["candidate_relation"]["is_error"] = True
        item["candidate_relation"]["is_reviewed_target_relation"] = True
        item["review"]["state"] = "reviewed"

        errors = validate_candidate_artifact(unsafe)

        self.assertTrue(any("selected_threshold" in error for error in errors))
        self.assertTrue(any("no repeated relation" in error for error in errors))
        self.assertTrue(any("into an error" in error for error in errors))
        self.assertTrue(any("reviewed truth" in error for error in errors))
        self.assertTrue(any("review state changed" in error for error in errors))

    @needs_research_data
    def test_every_release_boundary_and_downstream_exclusion_stays_closed(self):
        unsafe = copy.deepcopy(self.artifact)
        unsafe["release_boundaries"]["coaching"] = True
        unsafe["trials"][0]["opportunities"][0][
            "downstream_exclusions"
        ].remove("personal_progress")

        errors = validate_candidate_artifact(unsafe)

        self.assertTrue(any("release boundaries changed" in error for error in errors))
        self.assertTrue(any("downstream exclusions" in error for error in errors))

    @needs_research_data
    def test_artifact_has_no_score_correctness_clinical_or_coaching_output(self):
        def output_keys(value, parent=None):
            if parent in {"release_boundaries", "downstream_exclusions"}:
                return set()
            if isinstance(value, dict):
                found = set(value)
                for key, nested in value.items():
                    found.update(output_keys(nested, key))
                return found
            if isinstance(value, list):
                found = set()
                for nested in value:
                    found.update(output_keys(nested, parent))
                return found
            return set()

        keys = output_keys(self.artifact)
        for forbidden in (
            "articulation_score",
            "phonology_score",
            "pronunciation_score",
            "correctness",
            "diagnosis",
            "severity",
            "treatment",
            "coaching_text",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, keys)


@needs_research_data
class EvidenceAdequacyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        cls.contract = load_candidate_contract()
        cls.expected = _load_frozen(cls.contract, "powered_expected_manifest")
        cls.relations = _load_frozen(cls.contract, "powered_expert_relations")
        cls.source = _load_frozen(cls.contract, "powered_source_reference")
        cls.registry = _load_frozen(cls.contract, "corpus_registry")
        cls.corpus = _load_frozen(
            cls.contract, "speechocean762_corpus_manifest"
        )

    def test_committed_report_recomputes_exactly(self):
        self.assertEqual(validate_candidate_evidence_report(self.report), [])
        self.assertEqual(self.report, build_candidate_evidence_report())

    def test_report_records_the_actual_sparse_overlap(self):
        partitions = {
            item["project_split"]: item for item in self.report["partitions"]
        }
        self.assertEqual(
            partitions["development"]["adult_prompt_pack_word_occurrences"],
            12,
        )
        self.assertEqual(
            partitions["threshold_tuning"]["adult_prompt_pack_word_occurrences"],
            8,
        )
        self.assertEqual(
            self.report["totals"][
                "participants_with_two_distinct_prompt_pack_words"
            ],
            0,
        )
        self.assertEqual(
            self.report["totals"]["expert_target_truth"],
            {"positive": 1, "negative": 44, "unscorable": 3},
        )
        self.assertEqual(
            self.report["totals"]["prompt_pack_expected_sound_opportunities"],
            49,
        )
        self.assertEqual(
            self.report["totals"]["prompt_pack_scorable_sound_opportunities"],
            45,
        )
        self.assertEqual(
            self.report["totals"]["prompt_pack_unscorable_sound_opportunities"],
            4,
        )
        self.assertFalse(
            self.report["totals"][
                "repeated_support_denominator_available"
            ]
        )

    def test_report_does_not_overstate_repeated_support_visibility(self):
        checks = {
            item["check"]: item
            for item in self.report["evidence_adequacy"]["checks"]
        }

        self.assertFalse(
            checks["support_and_opportunity_denominators_visible"]["passed"]
        )
        self.assertIn(
            "support_and_opportunity_denominators_visible",
            self.report["evidence_adequacy"]["failed_checks"],
        )

    def test_report_stops_before_search_and_keeps_held_out_sealed(self):
        decision = self.report["decision"]
        self.assertEqual(decision["status"], RULE_STATUS)
        self.assertFalse(decision["threshold_search_performed"])
        self.assertFalse(decision["repeated_rule_search_performed"])
        self.assertFalse(decision["held_out_evaluation_performed"])
        self.assertEqual(
            self.report["sample"]["held_out_participants_or_labels_accessed"],
            0,
        )

    def test_report_contains_no_private_or_row_level_identifiers(self):
        encoded = json.dumps(self.report, sort_keys=True)
        for forbidden in (
            "private_participant_id",
            "private_utterance_id",
            "safe_id",
            "canonical_audio_path",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, encoded)

    def test_report_mutation_fails_recomputation(self):
        unsafe = copy.deepcopy(self.report)
        unsafe["totals"]["expert_target_truth"]["positive"] = 7

        errors = validate_candidate_evidence_report(unsafe)

        self.assertTrue(any("does not match" in error for error in errors))

    def test_non_object_report_is_invalid_without_crashing(self):
        for unsafe in (None, [], "not an object"):
            with self.subTest(unsafe=unsafe):
                self.assertEqual(
                    validate_candidate_evidence_report(unsafe),
                    ["candidate evidence report must be an object"],
                )

    def test_private_source_participant_and_split_joins_are_exact(self):
        expected = copy.deepcopy(self.expected)
        expected["clips"][0]["private_participant_id"] = "wrong"

        with self.assertRaises(CandidateArtifactError):
            _assert_source_bindings(
                expected,
                self.relations,
                self.source,
                self.registry,
                self.corpus,
            )

    def test_private_relation_word_and_target_indexes_are_exact(self):
        relations = copy.deepcopy(self.relations)
        relations["target_rows"][0]["word_index"] = 999

        with self.assertRaises(CandidateArtifactError):
            _assert_source_bindings(
                self.expected,
                relations,
                self.source,
                self.registry,
                self.corpus,
            )

    def test_registry_and_licence_bindings_are_exact(self):
        registry = copy.deepcopy(self.registry)
        registry["manifests"] = [
            item
            for item in registry["manifests"]
            if item["source_id"] != "speechocean762"
        ]

        with self.assertRaises(CandidateArtifactError):
            _assert_source_bindings(
                self.expected,
                self.relations,
                self.source,
                registry,
                self.corpus,
            )


class StandaloneCommandAndIsolationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        MANIFEST_ROOT.mkdir(parents=True, exist_ok=True)
        CANDIDATE_ROOT.mkdir(parents=True, exist_ok=True)

    @needs_research_data
    def test_explicit_offline_command_writes_only_the_private_artifact(self):
        with tempfile.TemporaryDirectory(dir=MANIFEST_ROOT) as manifest_dir:
            manifest_path = Path(manifest_dir) / "fixture.json"
            manifest_path.write_text(json.dumps(manifest()), encoding="utf-8")
            with tempfile.TemporaryDirectory(dir=CANDIDATE_ROOT) as output_parent:
                output_dir = Path(output_parent) / "new_run"
                with mock.patch.dict(
                    os.environ,
                    {"SPEECH_SOUND_OFFLINE": "1"},
                    clear=False,
                ):
                    artifact, path = extract(
                        manifest_path,
                        output_dir,
                        acknowledged=True,
                    )

                self.assertEqual(path.name, "speech_sound_candidates.json")
                self.assertEqual(
                    sorted(item.name for item in output_dir.iterdir()),
                    ["speech_sound_candidates.json"],
                )
                self.assertEqual(validate_candidate_artifact(artifact), [])

    @needs_research_data
    def test_real_owner_recording_can_only_use_checksum_bound_private_evidence(self):
        with tempfile.TemporaryDirectory(dir=PRIVATE_RESEARCH_ROOT) as evidence_dir:
            evidence_path = Path(evidence_dir) / "owner_evidence.bin"
            evidence_path.write_bytes(b"private functional integration fixture")
            document = adam_manifest(evidence_path)
            with tempfile.TemporaryDirectory(dir=MANIFEST_ROOT) as manifest_dir:
                manifest_path = Path(manifest_dir) / "owner.json"
                manifest_path.write_text(json.dumps(document), encoding="utf-8")
                with tempfile.TemporaryDirectory(
                    dir=CANDIDATE_ROOT
                ) as output_parent:
                    output_dir = Path(output_parent) / "new_run"
                    with mock.patch.dict(
                        os.environ,
                        {"SPEECH_SOUND_OFFLINE": "1"},
                        clear=False,
                    ):
                        artifact, _ = extract(
                            manifest_path,
                            output_dir,
                            acknowledged=True,
                        )

            self.assertEqual(
                artifact["source"]["role"], "functional_integration_only"
            )
            self.assertEqual(validate_candidate_artifact(artifact), [])

    def test_command_requires_acknowledgement_and_offline_environment(self):
        with self.assertRaises(CandidateArtifactError):
            extract("missing.json", CANDIDATE_ROOT / "run", acknowledged=False)
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(CandidateArtifactError):
                extract("missing.json", CANDIDATE_ROOT / "run", acknowledged=True)

    def test_command_refuses_normal_pipeline_or_outside_output_paths(self):
        with tempfile.TemporaryDirectory(dir=MANIFEST_ROOT) as manifest_dir:
            manifest_path = Path(manifest_dir) / "fixture.json"
            manifest_path.write_text(json.dumps(manifest()), encoding="utf-8")
            with mock.patch.dict(
                os.environ,
                {"SPEECH_SOUND_OFFLINE": "1"},
                clear=False,
            ):
                with self.assertRaises(CandidateArtifactError):
                    extract(
                        manifest_path,
                        REPOSITORY_ROOT / "output" / "unsafe_candidate",
                        acknowledged=True,
                    )

    def test_manifest_outside_private_root_is_rejected_before_reading(self):
        with mock.patch.dict(
            os.environ,
            {"SPEECH_SOUND_OFFLINE": "1"},
            clear=False,
        ), mock.patch("pathlib.Path.read_text") as read_text:
            with self.assertRaises(CandidateArtifactError):
                extract(
                    REPOSITORY_ROOT / "outside.json",
                    CANDIDATE_ROOT / "new_run",
                    acknowledged=True,
                )

        read_text.assert_not_called()

    def test_forbidden_scope_is_rejected_before_evidence_hashing(self):
        unsafe = manifest()
        unsafe["scope"]["held_out_access"] = True
        unsafe["trials"][0]["audio"]["path"] = "forbidden.wav"
        with tempfile.TemporaryDirectory(dir=MANIFEST_ROOT) as manifest_dir:
            manifest_path = Path(manifest_dir) / "held_out.json"
            manifest_path.write_text(json.dumps(unsafe), encoding="utf-8")
            with mock.patch.dict(
                os.environ,
                {"SPEECH_SOUND_OFFLINE": "1"},
                clear=False,
            ), mock.patch(
                "speech_sound_patterns.extract_candidates._validate_private_inputs"
            ) as validate_refs:
                with self.assertRaises(CandidateArtifactError):
                    extract(
                        manifest_path,
                        CANDIDATE_ROOT / "new_run",
                        acknowledged=True,
                    )

        validate_refs.assert_not_called()

    @needs_research_data
    def test_outside_and_bad_checksum_evidence_are_rejected(self):
        with tempfile.TemporaryDirectory(dir=MANIFEST_ROOT) as manifest_dir:
            manifest_path = Path(manifest_dir) / "owner.json"
            outside = REPOSITORY_ROOT / "README.md"
            manifest_path.write_text(
                json.dumps(adam_manifest(outside)),
                encoding="utf-8",
            )
            with mock.patch.dict(
                os.environ,
                {"SPEECH_SOUND_OFFLINE": "1"},
                clear=False,
            ):
                with self.assertRaisesRegex(
                    CandidateArtifactError, "leaves the private research root"
                ):
                    extract(
                        manifest_path,
                        CANDIDATE_ROOT / "outside_evidence",
                        acknowledged=True,
                    )

            with tempfile.TemporaryDirectory(
                dir=PRIVATE_RESEARCH_ROOT
            ) as evidence_dir:
                evidence_path = Path(evidence_dir) / "evidence.bin"
                evidence_path.write_bytes(b"evidence")
                manifest_path.write_text(
                    json.dumps(
                        adam_manifest(
                            evidence_path,
                            evidence_sha="0" * 64,
                        )
                    ),
                    encoding="utf-8",
                )
                with mock.patch.dict(
                    os.environ,
                    {"SPEECH_SOUND_OFFLINE": "1"},
                    clear=False,
                ):
                    with self.assertRaisesRegex(
                        CandidateArtifactError, "checksum changed"
                    ):
                        extract(
                            manifest_path,
                            CANDIDATE_ROOT / "bad_checksum",
                            acknowledged=True,
                        )

    @needs_research_data
    def test_output_cannot_overlap_manifests_exist_or_follow_pipeline_sentinels(self):
        with tempfile.TemporaryDirectory(dir=MANIFEST_ROOT) as manifest_dir:
            manifest_path = Path(manifest_dir) / "fixture.json"
            manifest_path.write_text(json.dumps(manifest()), encoding="utf-8")
            with mock.patch.dict(
                os.environ,
                {"SPEECH_SOUND_OFFLINE": "1"},
                clear=False,
            ):
                with self.assertRaises(CandidateArtifactError):
                    extract(
                        manifest_path,
                        Path(manifest_dir) / "output",
                        acknowledged=True,
                    )
                with tempfile.TemporaryDirectory(
                    dir=CANDIDATE_ROOT
                ) as existing:
                    with self.assertRaisesRegex(
                        CandidateArtifactError, "must be new"
                    ):
                        extract(
                            manifest_path,
                            existing,
                            acknowledged=True,
                        )
                with tempfile.TemporaryDirectory(
                    dir=CANDIDATE_ROOT
                ) as sentinel_parent:
                    (Path(sentinel_parent) / "master.json").write_text(
                        "{}",
                        encoding="utf-8",
                    )
                    with self.assertRaisesRegex(
                        CandidateArtifactError, "pipeline artifacts"
                    ):
                        extract(
                            manifest_path,
                            Path(sentinel_parent) / "child",
                            acknowledged=True,
                        )

    def test_normal_pipeline_source_has_no_candidate_import_stage_or_output(self):
        pipeline_files = [
            REPOSITORY_ROOT / "pipeline" / "run_all.py",
            REPOSITORY_ROOT / "pipeline" / "recording_modes.py",
            REPOSITORY_ROOT / "pipeline" / "pipeline_config.py",
            REPOSITORY_ROOT / "pipeline" / "merge.py",
            REPOSITORY_ROOT / "pipeline" / "listener.py",
            REPOSITORY_ROOT / "pipeline" / "evaluate.py",
            REPOSITORY_ROOT / "pipeline" / "claim_ledger.py",
            REPOSITORY_ROOT / "pipeline" / "history.py",
            REPOSITORY_ROOT / "pipeline" / "personal_progress.py",
        ]
        joined = "\n".join(path.read_text(encoding="utf-8") for path in pipeline_files)

        self.assertNotIn("speech_sound_candidates", joined)
        self.assertNotIn("speech_sound_patterns", joined)
        self.assertNotIn("candidate_artifact", joined)

    def test_extractor_has_no_pipeline_or_network_provider_import(self):
        source = (
            REPOSITORY_ROOT
            / "speech_sound_patterns"
            / "extract_candidates.py"
        ).read_text(encoding="utf-8")

        self.assertNotIn("from pipeline", source)
        self.assertNotIn("import pipeline", source)
        self.assertNotIn("requests", source)
        self.assertNotIn("httpx", source)
        self.assertNotIn("socket", source)


if __name__ == "__main__":
    unittest.main()
