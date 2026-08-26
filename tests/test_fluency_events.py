import copy
import unittest

from fluency_events.contract import load_contract, validate_contract
from fluency_events.extract import (
    apply_review_packet,
    extract_candidates,
    validate_artifact,
)
from pipeline.claim_ledger import build_evidence_catalog, evaluation_model_input


def quality(status="pass", decision="continue"):
    return {
        "overall_status": status,
        "decision": decision,
        "checks": [],
    }


def master(task_profile="unknown_ad_hoc"):
    return {
        "meta": {
            "recording_type": "solo",
            "contamination": {"status": "clear"},
            "voice_prosody_context": {
                "task_profile": task_profile,
                "task_id": None,
                "task_comparability": "not_comparable",
            },
        },
        "turns": [],
        "computed_metrics": {},
        "measurement_metadata": {},
    }


def word(index, text, start, end, confidence=0.95,
         speaker="SPEAKER_00", speaker_confidence="high"):
    return {
        "i": index,
        "text": text,
        "start_s": start,
        "end_s": end,
        "speaker": speaker,
        "confidence": speaker_confidence,
        "asr_confidence": confidence,
    }


class FluencyEventContractTests(unittest.TestCase):
    def test_committed_contract_is_valid_and_keeps_uses_locked(self):
        contract = load_contract()
        self.assertEqual(validate_contract(contract), [])
        self.assertEqual(contract["release_limits"]["diagnosis"], "blocked")
        self.assertEqual(contract["release_limits"]["severity"], "blocked")
        self.assertFalse(
            contract["algorithm"]["possible_block"][
                "automatic_detection_enabled"
            ]
        )

    def test_validator_rejects_automatic_blocks_and_interpretation_release(self):
        changed = copy.deepcopy(load_contract())
        changed["event_types"]["possible_block"][
            "automated_state"
        ] = "candidate_only"
        changed["algorithm"]["possible_block"][
            "automatic_detection_enabled"
        ] = True
        changed["release_limits"]["released_interpretation"] = "approved"
        errors = validate_contract(changed)
        self.assertTrue(any("block" in error for error in errors))
        self.assertTrue(any("interpretation" in error for error in errors))

    def test_validator_rejects_candidate_absence_as_fluency(self):
        changed = copy.deepcopy(load_contract())
        changed["terminology"]["absence_is_not_fluency"] = False
        changed["downstream_policy"][
            "absence_used_as_positive_fluency_claim"
        ] = True
        errors = validate_contract(changed)
        self.assertTrue(any("fluency" in error for error in errors))


class CandidateExtractionTests(unittest.TestCase):
    def test_adjacent_word_repetition_is_unclassified_until_manual_review(self):
        words = [
            word(0, "I", 0.0, 0.15),
            word(1, "I", 0.18, 0.33),
            word(2, "agree", 0.4, 0.8),
        ]
        artifact = extract_candidates(words, {}, master(), quality())
        events = artifact["candidates"]
        self.assertEqual(len(events), 1)
        self.assertEqual(
            events[0]["candidate_type"],
            "whole_word_repetition_unclassified",
        )
        self.assertEqual(
            events[0]["evidence"]["syllable_classification"], "manual_only"
        )
        self.assertEqual(events[0]["review"]["state"], "unreviewed")

    def test_low_asr_confidence_repetition_is_suppressed(self):
        words = [
            word(0, "I", 0.0, 0.15, confidence=0.3),
            word(1, "I", 0.18, 0.33),
        ]
        artifact = extract_candidates(words, {}, master(), quality())
        self.assertEqual(artifact["candidate_count"], 0)
        self.assertTrue(
            artifact["claim_boundary"][
                "candidate_absence_does_not_establish_fluency"
            ]
        )

    def test_phrase_repetition_is_separate_context_not_word_event(self):
        words = [
            word(0, "I", 0.0, 0.1),
            word(1, "think", 0.12, 0.35),
            word(2, "I", 0.4, 0.5),
            word(3, "think", 0.52, 0.75),
        ]
        artifact = extract_candidates(words, {}, master(), quality())
        types = [event["candidate_type"] for event in artifact["candidates"]]
        self.assertEqual(types, ["phrase_repetition"])
        self.assertIn(
            "phrase_repetition_is_context_not_stuttering_like_class",
            artifact["candidates"][0]["uncertainty"]["reasons"],
        )

    def test_hyphenated_part_word_pattern_has_timestamp_and_alternatives(self):
        words = [word(0, "b-b-but", 1.0, 1.65)]
        artifact = extract_candidates(words, {}, master(), quality())
        event = artifact["candidates"][0]
        self.assertEqual(event["candidate_type"],
                         "sound_or_syllable_repetition")
        self.assertEqual(event["start_s"], 1.0)
        self.assertEqual(event["end_s"], 1.65)
        self.assertIn("false_start", event["alternatives"])
        self.assertTrue(event["review"]["manual_confirmation_required"])

    def test_alignment_duration_outlier_is_candidate_not_confirmed_sound(self):
        words = [word(0, "abcdefghijklmnopqrstuvwxy", 0.0, 2.0)]
        chars = []
        position = 0.0
        for index, character in enumerate("abcdefghijklmnopqrstuvwxy"):
            duration = 0.3 if index == 12 else 0.05
            chars.append({
                "char": character,
                "start": position,
                "end": position + duration,
                "score": 0.95,
            })
            position += duration
        alignment = {"segments": [{"chars": chars}]}
        artifact = extract_candidates(words, alignment, master(), quality())
        events = [
            event for event in artifact["candidates"]
            if event["candidate_type"] == "prolonged_sound"
        ]
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event["evidence"]["aligned_character"], "m")
        self.assertTrue(
            event["evidence"][
                "aligned_character_present_in_transcript_token"
            ]
        )
        self.assertEqual(event["evidence"]["aligned_character_duration_s"], 0.3)
        self.assertIn("forced_alignment_error", event["alternatives"])
        self.assertTrue(
            event["uncertainty"]["candidate_is_not_confirmed_event"]
        )

    def test_alignment_transcript_disagreement_is_explicit(self):
        words = [word(0, "aaaaaaaaaaaaaaaaaaaaaaaaa", 0.0, 2.0)]
        chars = []
        position = 0.0
        for index in range(25):
            duration = 0.3 if index == 12 else 0.05
            chars.append({
                "char": "z" if index == 12 else "a",
                "start": position,
                "end": position + duration,
                "score": 0.95,
            })
            position += duration
        artifact = extract_candidates(
            words, {"segments": [{"chars": chars}]}, master(), quality()
        )
        event = next(
            item for item in artifact["candidates"]
            if item["evidence"]["source"]
            == "forced_alignment_character_duration_outlier"
        )
        self.assertFalse(
            event["evidence"][
                "aligned_character_present_in_transcript_token"
            ]
        )
        self.assertIn(
            "aligned_character_not_present_in_transcript_token",
            event["uncertainty"]["reasons"],
        )

    def test_silence_never_becomes_an_automatic_block(self):
        words = [
            word(0, "hello", 0.0, 0.4),
            word(1, "there", 3.0, 3.4),
        ]
        artifact = extract_candidates(words, {}, master(), quality())
        self.assertNotIn(
            "possible_block",
            [event["candidate_type"] for event in artifact["candidates"]],
        )
        self.assertEqual(
            artifact["availability"]["possible_block_automation"],
            "unavailable",
        )

    def test_generated_artifact_validates_and_unsafe_mutations_fail(self):
        artifact = extract_candidates(
            [word(0, "go", 0.0, 0.2), word(1, "go", 0.25, 0.45)],
            {}, master(), quality(),
        )
        self.assertEqual(validate_artifact(artifact), [])
        changed = copy.deepcopy(artifact)
        changed["candidates"][0]["candidate_type"] = "possible_block"
        changed["claim_boundary"]["diagnosis"] = "approved"
        errors = validate_artifact(changed)
        self.assertTrue(any("possible blocks" in error for error in errors))
        self.assertTrue(any("diagnosis" in error for error in errors))

    def test_rejected_audio_and_ineligible_task_abstain(self):
        repeated = [word(0, "go", 0.0, 0.2), word(1, "go", 0.25, 0.45)]
        rejected = extract_candidates(
            repeated, {}, master(), quality(status="fail", decision="reject")
        )
        self.assertEqual(rejected["status"], "unavailable")
        self.assertEqual(rejected["candidate_count"], 0)
        excluded = extract_candidates(
            repeated, {}, master("sustained_vowel_research"), quality()
        )
        self.assertIn("task_profile_excluded",
                      excluded["availability"]["reasons"])
        repeated_task = extract_candidates(
            repeated, {}, master("repeated_phrase_research"), quality()
        )
        self.assertIn("task_profile_excluded",
                      repeated_task["availability"]["reasons"])


class ManualReviewTests(unittest.TestCase):
    def setUp(self):
        self.artifact = extract_candidates(
            [word(0, "I", 0.0, 0.1), word(1, "I", 0.15, 0.25)],
            {}, master(), quality(),
        )

    def packet(self):
        return {
            "review_id": "review_one",
            "reviewer": {
                "opaque_id": "reviewer_opaque_one",
                "role": "trained_fluency_annotator",
            },
            "reviewed_at_utc": "2026-07-20T00:00:00Z",
            "blind_to_automation": True,
            "decisions": [{
                "event_id": "FE0001",
                "state": "confirmed_observable_event",
                "observed_type": "single_syllable_whole_word_repetition",
            }],
            "additions": [{
                "observed_type": "possible_block",
                "start_s": 1.0,
                "end_s": 1.4,
                "speaker": "SPEAKER_00",
                "state": "uncertain",
            }],
        }

    def test_review_preserves_role_and_never_becomes_reference_truth(self):
        reviewed = apply_review_packet(self.artifact, self.packet())
        event = reviewed["candidates"][0]
        self.assertEqual(event["review"]["state"],
                         "confirmed_observable_event")
        self.assertEqual(event["review"]["reference_truth_status"],
                         "not_reference_truth")
        addition = reviewed["review_summary"]["manual_additions"][0]
        self.assertEqual(addition["observed_type"], "possible_block")
        self.assertEqual(addition["source"], "human_review")

    def test_review_rejects_diagnosis_or_severity_fields(self):
        packet = self.packet()
        packet["severity_score"] = 3
        with self.assertRaisesRegex(ValueError, "diagnosis or severity"):
            apply_review_packet(self.artifact, packet)

    def test_review_rejects_unknown_event_type(self):
        packet = self.packet()
        packet["decisions"][0]["observed_type"] = "nervous_speech"
        with self.assertRaisesRegex(ValueError, "allowed type"):
            apply_review_packet(self.artifact, packet)

    def test_review_requires_audit_fields_and_rejects_duplicate_application(self):
        packet = self.packet()
        missing_time = copy.deepcopy(packet)
        missing_time.pop("reviewed_at_utc")
        with self.assertRaisesRegex(ValueError, "reviewed_at_utc"):
            apply_review_packet(copy.deepcopy(self.artifact), missing_time)
        reviewed = apply_review_packet(copy.deepcopy(self.artifact), packet)
        with self.assertRaisesRegex(ValueError, "already been applied"):
            apply_review_packet(reviewed, packet)

    def test_review_rejects_empty_or_duplicate_decisions(self):
        packet = self.packet()
        packet["decisions"] = []
        packet["additions"] = []
        with self.assertRaisesRegex(ValueError, "decision or addition"):
            apply_review_packet(copy.deepcopy(self.artifact), packet)
        packet = self.packet()
        packet["decisions"].append(copy.deepcopy(packet["decisions"][0]))
        with self.assertRaisesRegex(ValueError, "same event twice"):
            apply_review_packet(copy.deepcopy(self.artifact), packet)

    def test_manual_addition_only_is_audited_as_partial_review(self):
        packet = self.packet()
        packet["decisions"] = []
        reviewed = apply_review_packet(copy.deepcopy(self.artifact), packet)
        self.assertEqual(reviewed["review_summary"]["state"],
                         "partially_reviewed")
        addition = reviewed["review_summary"]["manual_additions"][0]
        self.assertEqual(addition["reviewed_at_utc"],
                         packet["reviewed_at_utc"])
        self.assertTrue(addition["blind_to_automation"])
        self.assertEqual(validate_artifact(reviewed), [])


class DownstreamIsolationTests(unittest.TestCase):
    def test_event_artifact_is_not_citeable_or_sent_to_evaluator(self):
        document = master()
        document["meta"]["fluency_event_evidence"] = {
            "artifact": "fluency_events.json",
            "candidate_events_excluded_from_evaluation": True,
        }
        artifact = extract_candidates(
            [word(0, "I", 0.0, 0.1), word(1, "I", 0.15, 0.25)],
            {}, document, quality(),
        )
        document["_test_external_artifact"] = artifact
        catalog_document = copy.deepcopy(document)
        catalog_document.pop("_test_external_artifact")
        paths = {item["path"] for item in build_evidence_catalog(
            catalog_document, {"source": "inferred_from_recording"}
        )}
        self.assertFalse(any("fluency" in path for path in paths))
        model_input = evaluation_model_input(catalog_document)
        self.assertNotIn("candidates", str(model_input))


if __name__ == "__main__":
    unittest.main()


class TextDerivedFamilyAvailabilityTests(unittest.TestCase):
    """A transcript with no ASR confidence cannot be scored as if it had one."""

    def words(self, with_confidence):
        rows = [
            ("I", 0.0, 0.2), ("need", 0.25, 0.5), ("to", 0.55, 0.7),
            ("I", 0.8, 1.0), ("need", 1.05, 1.3), ("to", 1.35, 1.5),
            ("know", 1.6, 1.9),
        ]
        words = []
        for index, (text, start, end) in enumerate(rows):
            word = {
                "i": index,
                "text": text,
                "speaker": "SPEAKER_00",
                "start_s": start,
                "end_s": end,
                "confidence": "high",
            }
            if with_confidence:
                word["asr_confidence"] = 0.95
            words.append(word)
        return words

    def artifact(self, with_confidence):
        return extract_candidates(
            self.words(with_confidence),
            {"segments": []},
            {"meta": {"recording_type": "solo"}},
            {"decision": "continue"},
        )

    def test_a_repetition_is_found_when_confidence_is_present(self):
        artifact = self.artifact(True)
        kinds = {item["candidate_type"] for item in artifact["candidates"]}
        self.assertIn("phrase_repetition", kinds)
        self.assertEqual(
            artifact["availability"]["text_derived_families"],
            "available_for_engineering_review",
        )
        self.assertIsNone(
            artifact["availability"]["text_derived_families_reason"]
        )

    def test_no_confidence_reports_unavailable_and_never_zero_candidates(self):
        artifact = self.artifact(False)
        kinds = {item["candidate_type"] for item in artifact["candidates"]}
        self.assertNotIn("phrase_repetition", kinds)
        self.assertEqual(
            artifact["availability"]["text_derived_families"], "unavailable"
        )
        self.assertIn(
            "would read as none found",
            artifact["availability"]["text_derived_families_reason"],
        )

    def test_the_duration_family_does_not_need_ASR_confidence(self):
        """It reads timing, so it must survive a transcript without confidence."""
        artifact = self.artifact(False)
        self.assertEqual(
            artifact["availability"]["duration_derived_families"],
            "available_for_engineering_review",
        )

    def test_the_artifact_still_validates_without_confidence(self):
        self.assertEqual(validate_artifact(self.artifact(False)), [])
