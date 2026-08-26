import copy
import unittest

from pipeline.history_identity import durable_history_scope, records_for_scope
from pipeline.pipeline_config import ACTIVE_SOURCE_FILES
from pipeline.session_context import (
    CONSENT_PURPOSES,
    load_data_model_contract,
    session_context_reference,
    validate_context_for_run,
    validate_data_model_contract,
    validate_session_context,
)


def consent_decisions(participant_id, suffix="01"):
    result = []
    for index, purpose in enumerate(sorted(CONSENT_PURPOSES), 1):
        result.append({
            "consent_event_id": f"consent_{suffix}{index:06d}",
            "participant_id": participant_id,
            "purpose": purpose,
            "decision": (
                "granted" if purpose == "speech_measurement_processing" else "declined"
            ),
            "notice_version": "1.0.0",
            "recorded_at_utc": "2026-07-19T10:00:00+10:00",
            "source": "user_explicit",
        })
    return result


def session_fixture():
    participant_id = "participant_00000001"
    return {
        "schema_version": "1.1.0",
        "account": {
            "account_id": "acct_00000001",
            "status": "active",
        },
        "session": {
            "session_id": "sess_00000001",
            "account_id": "acct_00000001",
            "context_id": "ctx_00000001",
            "language": "en",
            "recording_mode": "solo",
            "started_at_utc": "2026-07-19T10:01:00+10:00",
        },
        "context": {
            "context_id": "ctx_00000001",
            "account_id": "acct_00000001",
            "category": "interview",
            "declared_goal": "Prepare a clear answer for a university interview.",
            "audience": "university interviewer",
            "environment": {
                "setting": "home",
                "noise": "quiet",
                "source": "user_declared",
            },
        },
        "task": {
            "task_id": "goal_specific_response_en_v1",
            "task_version": "1.0.0",
            "prompt_id": "interview_problem_example",
            "prompt_version": "1.0.0",
            "language": "en",
            "preparation": {"allowed_s": 60, "actual_s": 42},
            "accommodations": [],
        },
        "attempt": {
            "attempt_id": "attempt_00000001",
            "account_id": "acct_00000001",
            "session_id": "sess_00000001",
            "context_id": "ctx_00000001",
            "attempt_role": "first",
            "progress_intent": "baseline_observation",
            "sequence_index": 1,
            "parent_attempt_id": None,
            "exercise_id": None,
            "recording_id": "recording_00000001",
        },
        "participants": [{
            "participant_id": participant_id,
            "role": "account_holder",
            "account_id": "acct_00000001",
            "speaker_label": "SPEAKER_00",
        }],
        "capture": {
            "recording_id": "recording_00000001",
            "device": {
                "device_class": "phone",
                "platform": "unknown",
                "microphone": "built_in",
                "source": "user_declared",
            },
            "environment": {
                "source": "technical_observation",
                "observations": [],
            },
            "quality_policy": "baseline",
            "speaker_mapping_source": "account_holder_only_capture",
        },
        "self_report": {
            "source": "user_declared",
            "representativeness": "typical",
            "difficulty": "moderate",
            "confidence": "prefer_not_to_answer",
            "temporary_context": [],
        },
        "consent_snapshot": {
            "as_of_utc": "2026-07-19T10:01:00+10:00",
            "decisions": consent_decisions(participant_id),
        },
    }


class DataModelContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = load_data_model_contract()

    def test_committed_contract_is_valid(self):
        self.assertEqual(validate_data_model_contract(self.contract), [])

    def test_speaker_label_cannot_become_durable_identity(self):
        changed = copy.deepcopy(self.contract)
        changed["identity"]["speaker_label_is_durable_identity"] = True

        errors = validate_data_model_contract(changed)

        self.assertTrue(any("durable identity" in error for error in errors))

    def test_attempts_cannot_be_overwritten_or_merge_retention_with_transfer(self):
        changed = copy.deepcopy(self.contract)
        changed["attempt_model"]["attempts_are_overwritten"] = True
        changed["attempt_model"]["retention_and_transfer_are_distinct"] = False

        errors = validate_data_model_contract(changed)

        self.assertTrue(any("cannot be overwritten" in error for error in errors))
        self.assertTrue(any("must remain distinct" in error for error in errors))

    def test_consent_cannot_be_bundled_or_inferred(self):
        changed = copy.deepcopy(self.contract)
        changed["consent"]["every_choice_separate"] = False
        changed["consent"]["consent_may_be_inferred_from_audio"] = True

        errors = validate_data_model_contract(changed)

        self.assertTrue(any("every_choice_separate" in error for error in errors))
        self.assertTrue(any("consent_may_be_inferred" in error for error in errors))

    def test_export_and_deletion_keep_full_account_scope(self):
        changed = copy.deepcopy(self.contract)
        changed["export_model"]["includes"].remove("consent_events")
        changed["deletion_model"]["targets"].remove("provider_copies")

        errors = validate_data_model_contract(changed)

        self.assertTrue(any("export model" in error for error in errors))
        self.assertTrue(any("deletion model" in error for error in errors))

    def test_contract_does_not_invent_retention_or_collect_exact_age(self):
        changed = copy.deepcopy(self.contract)
        changed["deletion_model"]["retention_periods_defined_here"] = True
        changed["context_and_evidence_boundaries"]["exact_age_collected"] = True

        errors = validate_data_model_contract(changed)

        self.assertTrue(any("retention periods" in error for error in errors))
        self.assertTrue(any("exact age" in error for error in errors))

    def test_runtime_identity_rules_are_in_pipeline_source_fingerprint(self):
        self.assertIn("data_model/contract-v1.1.0.json", ACTIVE_SOURCE_FILES)
        self.assertIn("pipeline/history_identity.py", ACTIVE_SOURCE_FILES)
        self.assertIn("pipeline/session_context.py", ACTIVE_SOURCE_FILES)


class SessionContextTests(unittest.TestCase):
    def test_valid_solo_context(self):
        self.assertEqual(validate_session_context(session_fixture()), [])

    def test_stable_ids_must_match_across_records(self):
        context = session_fixture()
        context["session"]["account_id"] = "acct_99999999"
        context["attempt"]["context_id"] = "ctx_99999999"

        errors = validate_session_context(context)

        self.assertTrue(any("session.account_id" in error for error in errors))
        self.assertTrue(any("attempt.context_id" in error for error in errors))

    def test_account_holder_is_speaker_zero_only_within_recording(self):
        context = session_fixture()
        context["participants"][0]["speaker_label"] = "SPEAKER_01"

        errors = validate_session_context(context)

        self.assertTrue(any("must be SPEAKER_00 locally" in error
                            for error in errors))

    def test_conversation_requires_other_consent_and_confirmed_mapping(self):
        context = session_fixture()
        context["session"]["recording_mode"] = "conversation"
        context["context"]["category"] = "conversation"
        context["capture"]["speaker_mapping_source"] = (
            "user_confirmed_after_recording"
        )
        other_id = "participant_00000002"
        context["participants"].append({
            "participant_id": other_id,
            "role": "other_consented_speaker",
            "account_id": None,
            "speaker_label": "SPEAKER_01",
        })
        context["consent_snapshot"]["decisions"].extend(
            consent_decisions(other_id, suffix="02")
        )

        self.assertEqual(validate_session_context(context), [])

        context["consent_snapshot"]["decisions"] = [
            item for item in context["consent_snapshot"]["decisions"]
            if item["participant_id"] != other_id
        ]
        errors = validate_session_context(context)
        self.assertTrue(any("one separate effective choice" in error
                            for error in errors))

    def test_optional_consent_can_be_declined_without_blocking_the_session(self):
        context = session_fixture()
        optional = [
            item for item in context["consent_snapshot"]["decisions"]
            if item["purpose"] != "speech_measurement_processing"
        ]

        self.assertTrue(optional)
        self.assertEqual({item["decision"] for item in optional}, {"declined"})
        self.assertEqual(validate_session_context(context), [])

    def test_speech_measurement_processing_must_be_explicitly_granted(self):
        context = session_fixture()
        processing = next(
            item for item in context["consent_snapshot"]["decisions"]
            if item["purpose"] == "speech_measurement_processing"
        )
        processing["decision"] = "declined"

        errors = validate_session_context(context)

        self.assertTrue(any("has not granted speech measurement processing" in error
                            for error in errors))

    def test_every_consent_purpose_has_a_separate_event(self):
        context = session_fixture()
        context["consent_snapshot"]["decisions"].pop()

        errors = validate_session_context(context)

        self.assertTrue(any("one separate effective choice" in error
                            for error in errors))

    def test_first_attempt_cannot_have_parent_and_later_attempt_requires_one(self):
        context = session_fixture()
        context["attempt"]["parent_attempt_id"] = "attempt_99999999"
        errors = validate_session_context(context)
        self.assertTrue(any("first attempt cannot have a parent" in error
                            for error in errors))

        context = session_fixture()
        context["attempt"]["attempt_role"] = "retention"
        errors = validate_session_context(context)
        self.assertTrue(any("later attempt must link" in error
                            for error in errors))

    def test_post_exercise_repeat_requires_versioned_exercise_link(self):
        context = session_fixture()
        context["attempt"]["attempt_role"] = "post_exercise_repeat"
        context["attempt"]["parent_attempt_id"] = "attempt_99999999"

        errors = validate_session_context(context)

        self.assertTrue(any("must link to an exercise" in error
                            for error in errors))

    def test_progress_intent_must_match_attempt_role(self):
        context = session_fixture()
        context["attempt"]["progress_intent"] = "retention"

        errors = validate_session_context(context)

        self.assertTrue(any("retention intent" in error for error in errors))

    def test_durable_history_requires_explicit_progress_intent(self):
        context = session_fixture()
        del context["attempt"]["progress_intent"]

        errors = validate_context_for_run(context, "solo", "SPEAKER_00")

        self.assertTrue(any("explicit attempt.progress_intent" in error
                            for error in errors))

    def test_context_must_match_pipeline_recording_mode(self):
        errors = validate_context_for_run(session_fixture(), "conversation")

        self.assertTrue(any("does not match the pipeline run" in error
                            for error in errors))

    def test_capture_quality_policy_must_match_pipeline_run(self):
        context = session_fixture()
        errors = validate_context_for_run(
            context, "solo", quality_policy="lenient"
        )
        self.assertTrue(any("quality policy" in error for error in errors))
        self.assertEqual(
            validate_context_for_run(
                context, "solo", quality_policy="baseline"
            ),
            [],
        )

    def test_hardware_fingerprint_and_exact_age_are_rejected(self):
        context = session_fixture()
        context["capture"]["device"]["serial_number"] = "private"
        context["self_report"]["exact_age"] = 22

        errors = validate_session_context(context)

        self.assertTrue(any("hardware fingerprint" in error for error in errors))
        self.assertTrue(any("forbidden field exact_age" in error
                            for error in errors))

    def test_optional_outcome_report_must_remain_user_declared(self):
        context = session_fixture()
        context["outcome_report"] = {
            "source": "model_inferred",
            "question_version": "1.0.0",
            "real_world_outcome": "achieved",
        }

        errors = validate_session_context(context)

        self.assertTrue(any("outcome report must remain user declared" in error
                            for error in errors))

    def test_context_reference_is_stable_and_keeps_run_and_session_separate(self):
        context = session_fixture()

        first = session_context_reference(context)
        second = session_context_reference(copy.deepcopy(context))

        self.assertEqual(first, second)
        self.assertEqual(first["session_id"], "sess_00000001")
        self.assertNotIn("run_id", first)


class HistoryIdentityTests(unittest.TestCase):
    def test_history_uses_account_and_context_not_speaker_label(self):
        current = {
            "account_id": "acct_00000001",
            "context_id": "ctx_00000001",
            "speaker_label": "SPEAKER_00",
        }
        records = [
            current,
            {
                "account_id": "acct_00000001",
                "context_id": "ctx_00000002",
                "speaker_label": "SPEAKER_00",
            },
            {
                "account_id": "acct_00000002",
                "context_id": "ctx_00000001",
                "speaker_label": "SPEAKER_00",
            },
            {"speaker_label": "SPEAKER_00"},
        ]

        self.assertEqual(durable_history_scope(current), (
            "acct_00000001", "ctx_00000001"
        ))
        self.assertEqual(records_for_scope(records, current), [current])


if __name__ == "__main__":
    unittest.main()
