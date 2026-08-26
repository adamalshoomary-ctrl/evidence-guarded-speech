import copy
import json
import unittest

from speech_sound_patterns.comparison import comparison_profile
from speech_sound_patterns.provider_register import REGISTER_PATH, REQUIRED_LANE_IDS
from speech_sound_patterns.selection_record import (
    DECISIONS,
    LANE_DECISION_PROFILES,
    REQUIRED_LIMITATION_CLASSES,
    SelectionRecordError,
    assert_valid_selection_record,
    lane_decision,
    load_selection_record,
    selected_lane_ids,
    validate_selection_record,
)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


class SpeechSoundSelectionRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = load_selection_record()
        cls.register = _load(REGISTER_PATH)
        cls.comparisons = {
            "1.0.0": _load(comparison_profile("1.0.0")["report_path"]),
            "1.1.0": _load(comparison_profile("1.1.0")["report_path"]),
        }

    def validate(self, record, register=None, comparisons=None):
        return validate_selection_record(
            record,
            register=self.register if register is None else register,
            comparisons=self.comparisons if comparisons is None else comparisons,
        )

    def changed(self, update):
        result = copy.deepcopy(self.record)
        update(result)
        return result

    def changed_comparisons(self, update):
        result = copy.deepcopy(self.comparisons)
        update(result)
        return result

    def lane(self, record, lane_id):
        for lane in record["lanes"]:
            if lane["lane_id"] == lane_id:
                return lane
        raise AssertionError(f"missing lane {lane_id}")

    def test_committed_record_is_valid(self):
        self.assertEqual(self.validate(self.record), [])
        assert_valid_selection_record(self.record)

    def test_every_register_lane_has_exactly_one_decision(self):
        decided = [lane["lane_id"] for lane in self.record["lanes"]]
        self.assertEqual(sorted(decided), sorted(REQUIRED_LANE_IDS))
        self.assertEqual(len(decided), len(set(decided)))
        for lane in self.record["lanes"]:
            self.assertIn(lane["decision"], DECISIONS)

    def test_the_committed_outcome_is_no_selection(self):
        self.assertEqual(self.record["decision"]["decision"], "no_selection")
        self.assertEqual(self.record["decision"]["selected_lane_ids"], [])
        self.assertEqual(selected_lane_ids(self.record), [])
        self.assertEqual(lane_decision("segmentation_free_gop", self.record), "research_only")

    def test_missing_lane_fails_closed(self):
        changed = self.changed(
            lambda record: record["lanes"].pop(
                record["lanes"].index(self.lane(record, "speechsuper"))
            )
        )
        errors = self.validate(changed)
        self.assertTrue(any("missing a decision" in error for error in errors))

    def test_lane_outside_the_register_fails_closed(self):
        def update(record):
            extra = copy.deepcopy(self.lane(record, "speechsuper"))
            extra["lane_id"] = "surprise_vendor"
            record["lanes"].append(extra)

        errors = self.validate(self.changed(update))
        self.assertTrue(any("outside the register" in error for error in errors))

    def test_a_verdict_cannot_be_rewritten_in_the_record_alone(self):
        def update(record):
            self.lane(record, "powsm")["decision"] = "research_only"

        errors = self.validate(self.changed(update))
        self.assertTrue(
            any("committed checkpoint 22E5 verdict" in error for error in errors)
        )

    def test_nothing_can_be_selected_while_no_candidate_passes(self):
        def update(record):
            lane = self.lane(record, "segmentation_free_gop")
            lane["decision"] = "selected_candidate"
            record["decision"]["decision"] = "selection_recorded"
            record["decision"]["selected_lane_ids"] = ["segmentation_free_gop"]

        errors = self.validate(self.changed(update))
        self.assertTrue(
            any("passes every unchanged gate" in error for error in errors)
        )

    def test_a_blocked_lane_can_never_be_promoted(self):
        def update(record):
            lane = self.lane(record, "speechace")
            lane["decision"] = "research_only"
            lane["decision_basis"] = "measured_evidence"

        errors = self.validate(self.changed(update))
        self.assertTrue(
            any("register status is 'blocked'" in error for error in errors)
        )

    def test_an_unmeasured_lane_cannot_claim_measured_evidence(self):
        def update(record):
            lane = self.lane(record, "zipa")
            lane["decision_basis"] = "measured_evidence"

        errors = self.validate(self.changed(update))
        self.assertTrue(any("no gate eligible candidate ran" in error for error in errors))

    def test_an_unmeasured_lane_cannot_report_a_gate_count(self):
        def update(record):
            lane = self.lane(record, "elsa_scripted_v3")
            lane["incremental_value_beyond_22d_baseline"][
                "gate_checks_passed_of_ten"
            ] = 10

        errors = self.validate(self.changed(update))
        self.assertTrue(
            any("unmeasured lane cannot report" in error for error in errors)
        )

    def test_the_record_disagreeing_with_the_register_fails_closed(self):
        def update(record):
            self.lane(record, "iflytek_ise_global")["register_status"] = "ready"

        errors = self.validate(self.changed(update))
        self.assertTrue(
            any("disagrees with the provider register" in error for error in errors)
        )

    def test_dropping_a_blocker_fails_closed(self):
        def update(record):
            self.lane(record, "unsw_speech_attributes")["blocked_pending"] = []

        errors = self.validate(self.changed(update))
        self.assertTrue(
            any("disagrees with the provider register" in error for error in errors)
        )

    def test_every_limitation_class_is_required(self):
        for name in REQUIRED_LIMITATION_CLASSES:
            with self.subTest(limitation=name):
                changed = self.changed(
                    lambda record, name=name: self.lane(record, "azure_speech")[
                        "limitations"
                    ].pop(name)
                )
                errors = self.validate(changed)
                self.assertTrue(
                    any("every limitation class" in error for error in errors)
                )

    def test_a_reopenable_verdict_must_say_what_reopens_it(self):
        def update(record):
            self.lane(record, "elsa_scripted_v3")["reopen_requires"] = []

        errors = self.validate(self.changed(update))
        self.assertTrue(any("what would reopen it" in error for error in errors))

    def test_a_permanent_role_cannot_be_reopened(self):
        def update(record):
            self.lane(record, "wav2vec2_commonphone")["reopen_requires"] = [
                "better numbers"
            ]

        errors = self.validate(self.changed(update))
        self.assertTrue(
            any("permanent role" in error for error in errors)
        )

    def test_a_gate_cannot_be_moved_in_this_checkpoint(self):
        changed = self.changed(
            lambda record: record["selection_gates"].update(
                {"minimum_precision_point_estimate": 0.6}
            )
        )
        errors = self.validate(changed)
        self.assertTrue(
            any("minimum_precision_point_estimate changed" in error for error in errors)
        )

    def test_further_threshold_searching_cannot_be_authorised(self):
        changed = self.changed(
            lambda record: record["decision"].update(
                {"further_threshold_search_authorised": True}
            )
        )
        errors = self.validate(changed)
        self.assertTrue(
            any("further_threshold_search_authorised" in error for error in errors)
        )

    def test_the_australian_and_child_limits_cannot_be_softened(self):
        for field in (
            "australian_variety_exact_relation_evidence_available",
            "children_supported",
            "held_out_set_accessed",
        ):
            with self.subTest(field=field):
                changed = self.changed(
                    lambda record, field=field: record["decision"].update({field: True})
                )
                errors = self.validate(changed)
                self.assertTrue(any(field in error for error in errors))

    def test_nothing_may_be_frozen_forward_when_nothing_was_selected(self):
        changed = self.changed(
            lambda record: record["frozen_for_later_checkpoints"].update(
                {"selected_threshold": 9.6176706}
            )
        )
        errors = self.validate(changed)
        self.assertTrue(any("must be null" in error for error in errors))

    def test_a_measured_outcome_cannot_be_restated(self):
        changed = self.changed(
            lambda record: record["measured_candidate_outcomes"][0].update(
                {"gate_checks_passed_of_ten": 10}
            )
        )
        errors = self.validate(changed)
        self.assertTrue(
            any("does not match the committed powered comparison" in error for error in errors)
        )

    def test_editing_the_cited_evidence_invalidates_the_record(self):
        changed = self.changed(
            lambda record: record["evidence_sources"]["frozen_comparison_22e4b"].update(
                {"sha256": "0" * 64}
            )
        )
        errors = self.validate(changed)
        self.assertTrue(
            any("no longer agree" in error for error in errors)
        )

    def test_a_release_boundary_cannot_be_opened(self):
        changed = self.changed(
            lambda record: record["release_boundaries"].update({"coaching": True})
        )
        errors = self.validate(changed)
        self.assertTrue(any("release boundary" in error for error in errors))

    def test_the_next_checkpoint_cannot_bypass_owner_approval(self):
        changed = self.changed(
            lambda record: record.update({"next_checkpoint": "22F"})
        )
        errors = self.validate(changed)
        self.assertTrue(any("bypasses owner approval" in error for error in errors))

    def test_private_and_prohibited_material_is_rejected(self):
        changed = self.changed(
            lambda record: self.lane(record, "azure_speech").update(
                {"limitations": {"PronScore": "0.9"}}
            )
        )
        errors = self.validate(changed)
        self.assertTrue(any("prohibited output class" in error for error in errors))

        changed = self.changed(
            lambda record: record["lanes"][0].update(
                {"private_participant_id": "someone"}
            )
        )
        errors = self.validate(changed)
        self.assertTrue(
            any("private or row level evidence" in error for error in errors)
        )

    def test_a_passing_candidate_would_be_required_before_a_selection(self):
        """The one path to a selection runs through the committed comparison."""
        comparisons = self.changed_comparisons(
            lambda reports: [
                candidate.update({"any_operating_point_passes_both_partitions": True})
                for candidate in reports["1.1.0"]["candidates"]
                if candidate["candidate_id"] == "sfgop_af_sd"
            ]
        )
        # Even then the committed verdict still governs: the record says
        # research_only, so claiming a selection remains an error.
        def update(record):
            lane = self.lane(record, "segmentation_free_gop")
            lane["decision"] = "selected_candidate"
            record["decision"]["decision"] = "selection_recorded"
            record["decision"]["selected_lane_ids"] = ["segmentation_free_gop"]

        errors = self.validate(self.changed(update), comparisons=comparisons)
        self.assertFalse(
            any("passes every unchanged gate" in error for error in errors)
        )
        self.assertTrue(
            any("committed checkpoint 22E5 verdict" in error for error in errors)
        )

    def test_assert_raises_on_an_invalid_record(self):
        changed = self.changed(
            lambda record: record["lanes"].pop()
        )
        with self.assertRaises(SelectionRecordError):
            assert_valid_selection_record(changed)

    def test_lane_decision_rejects_an_unknown_lane(self):
        with self.assertRaises(SelectionRecordError):
            lane_decision("surprise_vendor", self.record)

    def test_every_pinned_verdict_is_recorded(self):
        self.assertEqual(
            sorted(LANE_DECISION_PROFILES), sorted(REQUIRED_LANE_IDS)
        )

    def test_the_committed_record_is_reproducible_from_its_evidence(self):
        """The record is derived from committed evidence, not typed by hand."""
        from speech_sound_patterns.build_selection_record import build_record
        from speech_sound_patterns.feasibility import canonical_json_bytes
        from speech_sound_patterns.selection_record import SELECTION_RECORD_PATH

        self.assertEqual(
            canonical_json_bytes(build_record()),
            SELECTION_RECORD_PATH.read_bytes(),
        )


class SelectionRecordVersionTests(unittest.TestCase):
    """Checkpoint 22E6 restated the record; it did not rewrite the old one.

    Version 1.0.0 stays exactly as committed and stays pinned to the register
    it was written against, so the correction is visible as a second document
    rather than as an edit nobody can see.
    """

    def test_every_issued_version_validates_and_rebuilds_exactly(self):
        from speech_sound_patterns.build_selection_record import build_record
        from speech_sound_patterns.feasibility import canonical_json_bytes
        from speech_sound_patterns.selection_record import SELECTION_VERSIONS

        for version, profile in SELECTION_VERSIONS.items():
            with self.subTest(version=version):
                record = load_selection_record(version=version)
                self.assertEqual(validate_selection_record(record), [])
                self.assertEqual(record["record_version"], version)
                self.assertEqual(record["checkpoint"], profile["checkpoint"])
                self.assertEqual(
                    canonical_json_bytes(build_record(version)),
                    profile["record_path"].read_bytes(),
                )

    def test_each_version_pins_the_register_it_was_written_against(self):
        from speech_sound_patterns.selection_record import SELECTION_VERSIONS

        pinned = {
            version: load_selection_record(version=version)["evidence_sources"][
                "provider_register"
            ]["path"]
            for version in SELECTION_VERSIONS
        }
        self.assertEqual(len(set(pinned.values())), len(pinned))
        self.assertTrue(pinned["1.0.0"].endswith("provider-register-v1.1.0.json"))
        self.assertTrue(pinned["1.1.0"].endswith("provider-register-v1.2.0.json"))

    def test_no_verdict_moved_between_versions(self):
        earlier = load_selection_record(version="1.0.0")
        later = load_selection_record(version="1.1.0")
        for record in (earlier, later):
            self.assertEqual(record["decision"]["decision"], "no_selection")
        verdicts = [
            {
                lane["lane_id"]: (lane["decision"], lane["decision_basis"])
                for lane in record["lanes"]
            }
            for record in (earlier, later)
        ]
        self.assertEqual(verdicts[0], verdicts[1])

    def test_only_the_bookbot_reason_changed(self):
        earlier = {
            lane["lane_id"]: lane["reason"]
            for lane in load_selection_record(version="1.0.0")["lanes"]
        }
        later = {
            lane["lane_id"]: lane["reason"]
            for lane in load_selection_record(version="1.1.0")["lanes"]
        }
        changed = {
            lane_id for lane_id in earlier if earlier[lane_id] != later[lane_id]
        }
        self.assertEqual(changed, {"bookbot_au_g2p"})
        self.assertIn("disproved", later["bookbot_au_g2p"])
        self.assertNotIn("disproved", earlier["bookbot_au_g2p"])

    def test_an_unissued_record_version_fails_closed(self):
        record = load_selection_record(version="1.1.0")
        record["record_version"] = "9.9.9"
        errors = validate_selection_record(record)
        self.assertTrue(
            any("cannot introduce itself" in error for error in errors), errors
        )

    def test_the_next_checkpoint_is_the_one_the_plan_ordered(self):
        self.assertEqual(
            load_selection_record(version="1.1.0")["next_checkpoint"],
            "22E7_acquire_the_open_stack_after_owner_commit",
        )


if __name__ == "__main__":
    unittest.main()
