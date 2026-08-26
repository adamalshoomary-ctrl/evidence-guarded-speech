import copy
import json
import unittest

from speech_sound_patterns.provider_register import (
    HISTORICAL_REGISTERS,
    HISTORICAL_REGISTER_CHECKPOINTS,
    ProviderRegisterValidationError,
    REQUIRED_OWNER_DECISION_IDS,
    assert_historical_register,
    assert_valid_register,
    audio_permitted,
    lane_status,
    load_register,
    validate_register,
)


class SpeechSoundProviderRegisterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.register = load_register()

    def changed(self, update):
        result = copy.deepcopy(self.register)
        update(result)
        return result

    def lane(self, register, lane_id):
        for lane in register["lanes"]:
            if lane["lane_id"] == lane_id:
                return lane
        raise AssertionError(f"missing lane {lane_id}")

    def test_committed_register_is_valid(self):
        self.assertEqual(validate_register(self.register), [])
        assert_valid_register(self.register)

    def test_unrecognised_fields_fail_closed(self):
        changed = self.changed(
            lambda register: self.lane(register, "azure_speech").update(
                {"unsafe_override": True}
            )
        )
        errors = validate_register(changed)
        self.assertTrue(any("Additional properties" in error for error in errors))

    def test_missing_lane_fails_closed(self):
        changed = self.changed(
            lambda register: register["lanes"].pop(
                register["lanes"].index(self.lane(register, "speechsuper"))
            )
        )
        errors = validate_register(changed)
        self.assertTrue(any("missing approved lanes" in error for error in errors))

    def test_unknown_lane_fails_closed(self):
        def update(register):
            extra = copy.deepcopy(self.lane(register, "speechsuper"))
            extra["lane_id"] = "surprise_vendor"
            register["lanes"].append(extra)

        errors = validate_register(self.changed(update))
        self.assertTrue(any("outside the approved plan" in error for error in errors))

    def test_lane_promotion_fails_closed(self):
        def update(register):
            lane = self.lane(register, "speechace")
            lane["status"] = "ready"
            lane["blocked_pending"] = []

        errors = validate_register(self.changed(update))
        self.assertTrue(any("approved plan requires 'blocked'" in error for error in errors))

    def test_zipa_cannot_be_promoted_by_licence_tag_alone(self):
        def update(register):
            self.lane(register, "zipa")["status"] = "ready"

        errors = validate_register(self.changed(update))
        self.assertTrue(any("zipa" in error and "'conditional'" in error for error in errors))

    def test_blocked_status_requires_blockers(self):
        def update(register):
            self.lane(register, "unsw_speech_attributes")["blocked_pending"] = []

        errors = validate_register(self.changed(update))
        self.assertTrue(any("non-empty blocked_pending" in error for error in errors))

    def test_publication_permission_cannot_be_weakened(self):
        def update(register):
            lane = self.lane(register, "elsa_scripted_v3")
            lane["permissions"]["benchmark_publication"] = "permitted_by_public_terms"

        errors = validate_register(self.changed(update))
        self.assertTrue(
            any("written_permission_required" in error for error in errors)
        )

    def test_common_voice_can_never_become_eligible_for_transfer(self):
        def update(register):
            self.lane(register, "azure_speech")["eligible_sources"].append(
                "common_voice_26_australian_english"
            )

        errors = validate_register(self.changed(update))
        self.assertTrue(any("blocks provider transfer" in error for error in errors))

    def test_unregistered_corpus_fails_closed(self):
        def update(register):
            self.lane(register, "iflytek_ise_global")["eligible_sources"].append(
                "mystery_corpus"
            )

        errors = validate_register(self.changed(update))
        self.assertTrue(any("not a registered corpus" in error for error in errors))

    def test_commonphone_source_overlap_cannot_be_weakened(self):
        def update(register):
            lane = self.lane(register, "wav2vec2_commonphone")
            lane["lineage"]["non_independent_sources"] = ["common_phone_1_0"]

        errors = validate_register(self.changed(update))
        self.assertTrue(any("cannot be weakened" in error for error in errors))

    def test_credential_env_names_are_pinned(self):
        def update(register):
            lane = self.lane(register, "azure_speech")
            lane["credentials"]["env_var_names"] = ["AZURE_SPEECH_KEY"]

        errors = validate_register(self.changed(update))
        self.assertTrue(any("env var names must be exactly" in error for error in errors))

    def test_secret_like_value_fails_closed(self):
        def update(register):
            lane = self.lane(register, "azure_speech")
            lane["reason"] += " deadbeefdeadbeefdeadbeefdeadbeefdeadbeef1234"

        errors = validate_register(self.changed(update))
        self.assertTrue(any("looks like a credential value" in error for error in errors))

    def test_ready_external_lane_requires_verified_credential(self):
        def update(register):
            self.lane(register, "iflytek_ise_global")["credentials"][
                "verified"
            ] = None

        errors = validate_register(self.changed(update))
        self.assertTrue(any("credential verification record" in error for error in errors))

    def test_gop_repo_and_gopt_prohibitions_must_survive(self):
        def update(register):
            lane = self.lane(register, "segmentation_free_gop")
            lane["prohibited_uses"] = ["claiming produced-phone identity from a goodness score"]

        errors = validate_register(self.changed(update))
        self.assertTrue(any("'frank613'" in error for error in errors))
        self.assertTrue(any("'GOPT'" in error for error in errors))

    def test_negative_findings_cannot_be_dropped(self):
        def update(register):
            register["recorded_rejections"] = [
                item
                for item in register["recorded_rejections"]
                if "Allosaurus" not in item["candidate"]
            ]

        errors = validate_register(self.changed(update))
        self.assertTrue(any("'Allosaurus'" in error for error in errors))

    def test_audio_permission_is_fail_closed(self):
        self.assertTrue(
            audio_permitted("azure_speech", "speechocean762", self.register)
        )
        # Adam declined the iFLYTEK lane on 2026-07-25, so it receives no
        # audio even though its account, quota and credential all work.
        self.assertFalse(
            audio_permitted("iflytek_ise_global", "speechocean762", self.register)
        )
        self.assertFalse(
            audio_permitted(
                "azure_speech", "common_voice_26_australian_english", self.register
            )
        )
        self.assertFalse(
            audio_permitted("elsa_scripted_v3", "speechocean762", self.register)
        )
        self.assertFalse(
            audio_permitted("soapbox", "speechocean762", self.register)
        )
        self.assertFalse(
            audio_permitted("unknown_lane", "speechocean762", self.register)
        )

    def test_lane_status_rejects_unknown_lane(self):
        self.assertEqual(lane_status("soapbox", self.register), "rejected")
        with self.assertRaises(ProviderRegisterValidationError):
            lane_status("surprise_vendor", self.register)

    def test_invalid_register_raises_on_status_query(self):
        changed = self.changed(
            lambda register: self.lane(register, "soapbox").update(
                {"status": "ready"}
            )
        )
        with self.assertRaises(ProviderRegisterValidationError):
            lane_status("soapbox", changed)


class DisprovedProvenanceTests(unittest.TestCase):
    """Checkpoint 22E6. A disproved claim must not decay back into an open one.

    The Bookbot lane named a WikiPron Australian dataset that does not exist.
    Recording that as merely unverified would leave a reopening condition
    nobody can ever satisfy, and would read like unfinished homework rather
    than a closed question.
    """

    @classmethod
    def setUpClass(cls):
        cls.register = load_register()

    def changed(self, update):
        result = copy.deepcopy(self.register)
        update(result)
        return result

    def lane(self, register, lane_id):
        for lane in register["lanes"]:
            if lane["lane_id"] == lane_id:
                return lane
        raise AssertionError(f"missing lane {lane_id}")

    def test_bookbot_records_a_disproved_training_source(self):
        lane = self.lane(self.register, "bookbot_au_g2p")
        self.assertEqual(lane["lineage"]["training_data_claim_state"], "disproved")
        self.assertTrue(lane["blocked_pending"])
        claims = " ".join(item["claim"] for item in lane["evidence"]).lower()
        self.assertIn("two dialects", claims)

    def test_a_disproved_claim_cannot_be_softened_back_to_unverified(self):
        changed = self.changed(
            lambda register: self.lane(register, "bookbot_au_g2p")["lineage"].update(
                {"training_data_claim_state": "unverified"}
            )
        )
        errors = validate_register(changed)
        self.assertTrue(
            any("a claim state is a finding" in error for error in errors), errors
        )

    def test_a_disproved_lane_cannot_become_ready(self):
        def update(register):
            lane = self.lane(register, "bookbot_au_g2p")
            lane["status"] = "ready"
            lane["blocked_pending"] = []

        errors = validate_register(self.changed(update))
        self.assertTrue(
            any("disproved training-data claim cannot be ready" in error for error in errors),
            errors,
        )

    def test_no_lane_still_claims_an_australian_wikipron_source(self):
        for lane in self.register["lanes"]:
            lineage = lane.get("lineage")
            if lineage is None:
                continue
            for entry in lineage["training_data"]:
                if "au-broad" in entry.lower() or "au_broad" in entry.lower():
                    self.fail(
                        f"{lane['lane_id']} still names a WikiPron Australian "
                        "dataset as though it existed"
                    )


class StandingOwnerDecisionTests(unittest.TestCase):
    """The decisions of 2026-07-28 live in the register, not only in prose."""

    @classmethod
    def setUpClass(cls):
        cls.register = load_register()

    def test_every_standing_decision_is_recorded(self):
        recorded = {
            decision["decision_id"] for decision in self.register["owner_decisions"]
        }
        self.assertTrue(REQUIRED_OWNER_DECISION_IDS.issubset(recorded))
        for decision in self.register["owner_decisions"]:
            self.assertTrue(decision["reopen_requires"])

    def test_dropping_a_standing_decision_fails_closed(self):
        changed = copy.deepcopy(self.register)
        changed["owner_decisions"] = [
            decision
            for decision in changed["owner_decisions"]
            if decision["decision_id"] != "no_isle_purchase"
        ]
        errors = validate_register(changed)
        self.assertTrue(
            any("missing standing owner decisions" in error for error in errors),
            errors,
        )

    def test_a_standing_decision_cannot_be_redated(self):
        changed = copy.deepcopy(self.register)
        changed["owner_decisions"][0]["date"] = "2026-07-29"
        errors = validate_register(changed)
        self.assertTrue(any("date cannot be moved" in error for error in errors), errors)


class SupersededRegisterTests(unittest.TestCase):
    """Every earlier register stays exactly as committed and still validates."""

    def test_each_superseded_register_matches_its_own_schema_and_checkpoint(self):
        for version, (register_path, _) in HISTORICAL_REGISTERS.items():
            with self.subTest(version=version):
                register = json.loads(register_path.read_text(encoding="utf-8"))
                self.assertEqual(register["schema_version"], version)
                self.assertEqual(
                    register["checkpoint"], HISTORICAL_REGISTER_CHECKPOINTS[version]
                )
                assert_historical_register(register)

    def test_a_relabelled_superseded_register_fails_closed(self):
        version, (register_path, _) = next(iter(HISTORICAL_REGISTERS.items()))
        register = json.loads(register_path.read_text(encoding="utf-8"))
        register["checkpoint"] = "22E6"
        with self.assertRaises(ProviderRegisterValidationError):
            assert_historical_register(register)


if __name__ == "__main__":
    unittest.main()
