import copy
import json
import unittest

from speech_sound_patterns.external_smoke import (
    EXPECTED_ONLY_MANIFEST_SHA256,
    ExternalSmokeValidationError,
    assert_valid_smoke_evidence,
    load_smoke_contract,
    load_smoke_report,
    load_transfer_review,
    owner_audio_permitted,
    transfer_permitted,
    validate_smoke_contract,
    validate_smoke_report,
    validate_transfer_review,
)
from speech_sound_patterns.provider_register import (
    audio_permitted,
    load_register,
)


class CorpusProviderTransferReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.review = load_transfer_review()

    def changed(self, update):
        result = copy.deepcopy(self.review)
        update(result)
        return result

    def decision(self, review, lane_id, source_id):
        for item in review["decisions"]:
            if (item["lane_id"], item["source_id"]) == (lane_id, source_id):
                return item
        raise AssertionError(f"missing decision for {lane_id}/{source_id}")

    def test_committed_review_is_valid(self):
        self.assertEqual(validate_transfer_review(self.review), [])

    def test_only_azure_received_audio_permission(self):
        permitted = {
            (item["lane_id"], item["source_id"])
            for item in self.review["decisions"]
            if item["decision"] == "permitted"
        }
        self.assertEqual({lane for lane, _ in permitted}, {"azure_speech"})

    def test_unlisted_pair_is_prohibited(self):
        self.assertFalse(transfer_permitted("azure_speech", "macquarie_australian_pronunciation_data"))
        self.assertFalse(transfer_permitted("speechace", "speechocean762"))

    def test_declined_and_blocked_lanes_are_not_permitted(self):
        self.assertFalse(transfer_permitted("iflytek_ise_global", "speechocean762"))
        self.assertFalse(transfer_permitted("elsa_scripted_v3", "speechocean762"))

    def test_transfer_blocked_corpus_can_never_be_permitted(self):
        changed = self.changed(
            lambda review: self.decision(
                review, "azure_speech", "common_voice_26_australian_english"
            ).update({"decision": "permitted"})
        )
        errors = validate_transfer_review(changed)
        self.assertTrue(
            any("can never be permitted" in error for error in errors), errors
        )

    def test_absence_cannot_become_permission(self):
        changed = self.changed(
            lambda review: review.update({"unlisted_pairs_are_prohibited": False})
        )
        errors = validate_transfer_review(changed)
        self.assertTrue(any("absence can never" in error for error in errors), errors)

    def test_personal_audio_exclusion_cannot_be_dropped(self):
        changed = self.changed(lambda review: review.pop("personal_audio_statement"))
        errors = validate_transfer_review(changed)
        self.assertTrue(
            any("owner and personal audio" in error for error in errors), errors
        )

    def test_a_decision_without_evidence_fails_closed(self):
        changed = self.changed(
            lambda review: self.decision(review, "azure_speech", "speechocean762").update(
                {"evidence": []}
            )
        )
        errors = validate_transfer_review(changed)
        self.assertTrue(any("evidence item is required" in error for error in errors))

    def test_register_audio_gate_requires_the_review(self):
        # Being an eligible source in the register is necessary but never
        # sufficient. Every source a lane lists as eligible must also carry a
        # permitting review decision, so adding an eligible source without
        # reviewing it shuts the upload gate rather than opening one.
        register = load_register()
        for lane in register["lanes"]:
            for source_id in lane["eligible_sources"]:
                with self.subTest(lane=lane["lane_id"], source=source_id):
                    self.assertEqual(
                        audio_permitted(lane["lane_id"], source_id),
                        lane["status"] == "ready"
                        and transfer_permitted(lane["lane_id"], source_id),
                    )
                    self.assertIn(
                        (lane["lane_id"], source_id),
                        {
                            (item["lane_id"], item["source_id"])
                            for item in self.review["decisions"]
                        },
                        f"{lane['lane_id']} lists {source_id} as eligible but the "
                        "transfer review records no decision for that pair",
                    )

    def test_an_unreviewed_eligible_source_fails_closed(self):
        changed = self.changed(
            lambda review: review["decisions"].remove(
                self.decision(review, "azure_speech", "common_phone_1_0")
            )
        )
        errors = validate_transfer_review(changed)
        self.assertTrue(
            any("records no decision" in error for error in errors), errors
        )


class OwnerAudioGrantTests(unittest.TestCase):
    """Owner audio leaves the machine only under an exact, scoped grant."""

    @classmethod
    def setUpClass(cls):
        cls.review = load_transfer_review()
        cls.digest = (
            "da530382502dafc3f27c0a9bb706df023a36eafe9f1d47dc1e33f413b277ecc4"
        )

    def changed(self, update):
        result = copy.deepcopy(self.review)
        update(result)
        return result

    def grant(self, review):
        return review["owner_audio_decisions"][0]

    def test_default_is_prohibited(self):
        self.assertEqual(self.review["owner_audio_policy"]["default"], "prohibited")
        changed = self.changed(
            lambda review: review["owner_audio_policy"].update({"default": "permitted"})
        )
        errors = validate_transfer_review(changed)
        self.assertTrue(any("must be prohibited" in error for error in errors), errors)

    def test_grant_is_pinned_to_one_exact_file(self):
        self.assertTrue(owner_audio_permitted("azure_speech", self.digest))
        self.assertFalse(owner_audio_permitted("azure_speech", "0" * 64))

    def test_grant_does_not_generalise_to_another_lane(self):
        self.assertFalse(owner_audio_permitted("elsa_scripted_v3", self.digest))
        self.assertFalse(owner_audio_permitted("iflytek_ise_global", self.digest))

    def test_a_grant_without_an_exact_hash_fails_closed(self):
        changed = self.changed(
            lambda review: self.grant(review).update({"file_sha256": "not-a-hash"})
        )
        errors = validate_transfer_review(changed)
        self.assertTrue(any("exact file by SHA256" in error for error in errors), errors)

    def test_a_standing_permission_fails_closed(self):
        changed = self.changed(
            lambda review: self.grant(review).update({"single_use": False})
        )
        errors = validate_transfer_review(changed)
        self.assertTrue(any("single use" in error for error in errors), errors)

    def test_owner_audio_cannot_be_promoted_beyond_demonstration(self):
        changed = self.changed(
            lambda review: self.grant(review).update(
                {"evidence_class": "accuracy_evidence"}
            )
        )
        errors = validate_transfer_review(changed)
        self.assertTrue(
            any("demonstration evidence only" in error for error in errors), errors
        )

    def test_a_grant_missing_its_reasoning_fails_closed(self):
        for field in ("purpose", "scope_note", "granted_by"):
            with self.subTest(field=field):
                changed = self.changed(
                    lambda review, field=field: self.grant(review).update({field: ""})
                )
                errors = validate_transfer_review(changed)
                self.assertTrue(
                    any(f"must record {field}" in error for error in errors), errors
                )

    def test_recording_still_matches_the_hash_the_grant_pins(self):
        # If the file is replaced, the runner must refuse rather than send a
        # recording the owner never approved.
        from speech_sound_patterns.accent_contrast import (
            RECORDING_PATH,
            RECORDING_SHA256,
        )
        from speech_sound_patterns.feasibility import file_sha256

        if not RECORDING_PATH.exists():
            self.skipTest("owner recording is not present in this checkout")
        self.assertEqual(file_sha256(RECORDING_PATH), RECORDING_SHA256)
        self.assertEqual(RECORDING_SHA256, self.digest)


class ExternalSmokeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = load_smoke_contract()

    def changed(self, update):
        result = copy.deepcopy(self.contract)
        update(result)
        return result

    def test_committed_contract_is_valid(self):
        self.assertEqual(validate_smoke_contract(self.contract), [])

    def test_contract_was_declared_before_any_request(self):
        self.assertIs(self.contract["declared_before_any_request"], True)
        changed = self.changed(
            lambda contract: contract.update({"declared_before_any_request": False})
        )
        errors = validate_smoke_contract(changed)
        self.assertTrue(any("before" in error for error in errors), errors)

    def test_sample_is_bound_to_the_label_blind_manifest(self):
        self.assertEqual(
            self.contract["input_policy"]["expected_only_manifest_sha256"],
            EXPECTED_ONLY_MANIFEST_SHA256,
        )
        changed = self.changed(
            lambda contract: contract["input_policy"].update(
                {"expected_only_manifest_sha256": "0" * 64}
            )
        )
        errors = validate_smoke_contract(changed)
        self.assertTrue(any("expert outcome" in error for error in errors), errors)

    def test_child_strata_are_excluded(self):
        changed = self.changed(
            lambda contract: contract["input_policy"]["permitted_strata"].append(
                "source_child_m"
            )
        )
        errors = validate_smoke_contract(changed)
        self.assertTrue(any("child strata" in error for error in errors), errors)

    def test_held_out_and_owner_audio_exclusions_cannot_be_dropped(self):
        changed = self.changed(
            lambda contract: contract["input_policy"]["never_transmitted_fields"].remove(
                "any owner or personal recording"
            )
        )
        errors = validate_smoke_contract(changed)
        self.assertTrue(any("owner or personal" in error for error in errors), errors)

    def test_prohibited_output_classes_cannot_be_dropped(self):
        changed = self.changed(
            lambda contract: contract["prohibited_outputs"].remove("PronScore")
        )
        errors = validate_smoke_contract(changed)
        self.assertTrue(any("PronScore" in error for error in errors), errors)

    def test_no_numeric_tolerance_may_be_granted(self):
        changed = self.changed(
            lambda contract: contract["repeatability_rules"].update(
                {"numeric_tolerance": 0.5}
            )
        )
        errors = validate_smoke_contract(changed)
        self.assertTrue(any("tolerance" in error for error in errors), errors)

    def test_marketing_cannot_qualify_a_lane(self):
        changed = self.changed(
            lambda contract: contract["advancement_rules"].pop(
                "no_lane_advances_on_marketing"
            )
        )
        errors = validate_smoke_contract(changed)
        self.assertTrue(any("marketing" in error for error in errors), errors)


class ExternalSmokeReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = load_smoke_report()

    def changed(self, update):
        result = copy.deepcopy(self.report)
        update(result)
        return result

    def configuration(self, report, configuration_id):
        for item in report["configurations"]:
            if item["configuration_id"] == configuration_id:
                return item
        raise AssertionError(f"missing configuration {configuration_id}")

    def test_committed_report_is_valid(self):
        self.assertEqual(validate_smoke_report(self.report), [])
        assert_valid_smoke_evidence(self.report)

    def test_every_request_succeeded_and_repeated_exactly(self):
        for configuration in self.report["configurations"]:
            self.assertEqual(
                configuration["requests_sent"], configuration["requests_succeeded"]
            )
            self.assertEqual(configuration["repeatability"], "exact")

    def test_australian_locale_is_score_only(self):
        australian = self.configuration(self.report, "azure_en_au")
        self.assertEqual(australian["advancement"], "score_only")
        self.assertEqual(australian["capabilities"]["phoneme_name"], "absent")
        # The key exists but is emitted empty. Recording that explicitly is the
        # point: a parser checking key presence would invent produced phones.
        self.assertIn("phoneme.Phoneme", australian["keys_present_but_empty"])

    def test_united_states_locale_is_exact_relation_capable(self):
        american = self.configuration(self.report, "azure_en_us")
        self.assertEqual(american["advancement"], "exact_relation_capable")
        self.assertEqual(american["capabilities"]["phoneme_name"], "present")
        self.assertEqual(
            american["capabilities"]["spoken_phoneme_candidates"], "present"
        )
        self.assertEqual(american["keys_present_but_empty"], [])

    def test_locales_are_never_pooled(self):
        self.assertIs(self.report["locales_pooled"], False)
        self.assertGreater(self.report["locale_distinctness"]["max_absolute_difference"], 0)
        changed = self.changed(lambda report: report.update({"locales_pooled": True}))
        errors = validate_smoke_report(changed)
        self.assertTrue(any("not pooled" in error for error in errors), errors)

    def test_overstated_advancement_fails_closed(self):
        changed = self.changed(
            lambda report: self.configuration(report, "azure_en_au").update(
                {"advancement": "exact_relation_capable"}
            )
        )
        errors = validate_smoke_report(changed)
        self.assertTrue(
            any("exact_relation_capable requires" in error for error in errors), errors
        )

    def test_understated_advancement_fails_closed(self):
        changed = self.changed(
            lambda report: self.configuration(report, "azure_en_us").update(
                {"advancement": "score_only"}
            )
        )
        errors = validate_smoke_report(changed)
        self.assertTrue(any("understated" in error for error in errors), errors)

    def test_configuration_cannot_be_added_after_seeing_results(self):
        def update(report):
            extra = copy.deepcopy(self.configuration(report, "azure_en_us"))
            extra["configuration_id"] = "azure_en_gb"
            extra["locale"] = "en-GB"
            report["configurations"].append(extra)

        errors = validate_smoke_report(self.changed(update))
        self.assertTrue(any("was not declared" in error for error in errors), errors)

    def test_configuration_without_a_permitted_transfer_fails_closed(self):
        changed = self.changed(
            lambda report: self.configuration(report, "azure_en_au").update(
                {"source_id": "common_voice_26_australian_english"}
            )
        )
        errors = validate_smoke_report(changed)
        self.assertTrue(
            any("does not permit sending" in error for error in errors), errors
        )

    def test_failed_configuration_cannot_advance(self):
        changed = self.changed(
            lambda report: self.configuration(report, "azure_en_au").update(
                {"requests_succeeded": 0}
            )
        )
        errors = validate_smoke_report(changed)
        self.assertTrue(any("advances nothing" in error for error in errors), errors)

    def test_prohibited_score_classes_never_reach_the_report(self):
        changed = self.changed(
            lambda report: self.configuration(report, "azure_en_us")[
                "field_presence"
            ].update({"PronScore": "present"})
        )
        errors = validate_smoke_report(changed)
        self.assertTrue(any("prohibited output class" in error for error in errors), errors)

    def test_report_carries_no_transcript_or_participant_identity(self):
        serialized = json.dumps(self.report)
        for leaked in ("private_participant_id", "private_utterance_id", "Lexical", "DisplayText"):
            self.assertNotIn(leaked, serialized)

    def test_invalid_evidence_raises(self):
        changed = self.changed(lambda report: report.update({"checkpoint": "22E4"}))
        with self.assertRaises(ExternalSmokeValidationError):
            assert_valid_smoke_evidence(changed)


if __name__ == "__main__":
    unittest.main()
