import copy
import json
import unittest
from pathlib import Path

from motor_speech_voice.source_survey import (
    OBTAINABLE_WITHOUT_CONTACT,
    OPEN_DECISION,
    REGISTRY_PATH,
    REQUIRED_CROSS_SOURCE_RULES,
    REQUIRED_LANES,
    SCHEMA_PATH,
    load_json,
    record_paths,
    validate_record,
    validate_registry,
    validate_survey,
)


class SourceSurveyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = load_json(SCHEMA_PATH)
        cls.registry = load_json(REGISTRY_PATH)
        cls.records = [load_json(path) for path in record_paths()]
        cls.by_id = {record["source_id"]: record for record in cls.records}

    def record(self, source_id, update):
        document = copy.deepcopy(self.by_id[source_id])
        update(document)
        return document

    def assert_record_rejected(self, source_id, update):
        errors = validate_record(
            self.record(source_id, update), self.schema, f"{source_id}.json"
        )
        self.assertTrue(errors, "the mutated record should have been rejected")

    def assert_registry_rejected(self, update):
        registry = copy.deepcopy(self.registry)
        update(registry)
        self.assertTrue(validate_registry(registry, self.records))

    # -- the committed state ------------------------------------------------

    def test_the_committed_survey_is_valid(self):
        self.assertEqual(validate_survey(), [])

    def test_every_record_validates_and_selects_nothing(self):
        for record in self.records:
            with self.subTest(source=record["source_id"]):
                self.assertEqual(
                    validate_record(record, self.schema, record["source_id"]), []
                )
                self.assertIs(record["eligibility"]["selected"], False)
                self.assertIs(record["governance"]["acquisition_authorised"], False)
                self.assertIs(record["governance"]["raw_data_committed"], False)

    def test_no_record_claims_a_truth_requirement_is_met(self):
        for record in self.records:
            with self.subTest(source=record["source_id"]):
                self.assertIn(
                    record["reference_truth"]["requirement_status"],
                    {"fails", "unresolved"},
                )
        self.assertEqual(
            self.registry["counts"]["recorded_as_meeting_an_item_23_truth_requirement"],
            0,
        )
        self.assertEqual(self.registry["counts"]["selected"], 0)

    def test_the_survey_directory_holds_records_only(self):
        for path in Path(SCHEMA_PATH).parent.rglob("*"):
            if path.is_file():
                with self.subTest(path=path.name):
                    self.assertEqual(path.suffix, ".json")

    def test_every_lane_conclusion_is_present(self):
        self.assertEqual(REQUIRED_LANES, set(self.registry["lane_conclusions"]))

    # -- a schema is not enough --------------------------------------------

    def test_a_meeting_status_cannot_even_be_expressed(self):
        enum = self.schema["properties"]["reference_truth"]["properties"][
            "requirement_status"
        ]["enum"]
        self.assertEqual(sorted(enum), ["fails", "unresolved"])

    def test_a_record_may_not_record_a_selection(self):
        self.assert_record_rejected(
            "pvqd", lambda doc: doc["eligibility"].__setitem__("selected", True)
        )

    def test_a_record_may_not_authorise_acquisition(self):
        self.assert_record_rejected(
            "pvqd",
            lambda doc: doc["governance"].__setitem__("acquisition_authorised", True),
        )

    def test_a_record_may_not_unblock_provider_transfer(self):
        self.assert_record_rejected(
            "pvqd",
            lambda doc: doc["governance"].__setitem__(
                "transfer_to_any_provider", "permitted"
            ),
        )

    # -- the specific ways this survey could be softened --------------------

    def test_a_non_commercial_source_may_not_be_called_open(self):
        self.assert_record_rejected(
            "torgo",
            lambda doc: doc["eligibility"].__setitem__("decision", OPEN_DECISION),
        )

    def test_an_unlicensed_source_may_not_be_called_open(self):
        self.assert_record_rejected(
            "osf_slp_intelligibility_estimations",
            lambda doc: doc["eligibility"].__setitem__("decision", OPEN_DECISION),
        )

    def test_a_source_needing_an_agreement_may_not_be_called_open(self):
        def update(document):
            document["licence"]["commercial_use_permitted"] = True
            document["eligibility"]["decision"] = OPEN_DECISION

        self.assert_record_rejected("ewa_db", update)

    def test_no_contact_and_a_required_signature_cannot_both_be_true(self):
        self.assert_record_rejected(
            "pvqd",
            lambda doc: doc["access"].__setitem__(
                "organisation_signatory_required", True
            ),
        )

    def test_direct_verification_needs_a_dated_inspected_material(self):
        self.assert_record_rejected(
            "pvqd",
            lambda doc: doc["capability_audit"].__setitem__(
                "inspected_materials", ["a page was looked at"]
            ),
        )

    def test_an_unverified_report_may_not_become_an_open_route(self):
        def update(document):
            document["licence"]["commercial_use_permitted"] = True
            document["access"]["state"] = OBTAINABLE_WITHOUT_CONTACT
            document["access"]["contact_with_a_person_required"] = False
            document["access"]["account_required"] = False
            document["access"]["agreement_signature_required"] = False
            document["eligibility"]["decision"] = OPEN_DECISION

        self.assert_record_rejected("nki_ccrt", update)

    # -- the registry may not drift from its records -----------------------

    def test_the_registry_may_not_hide_a_record(self):
        self.assert_registry_rejected(lambda reg: reg["records"].pop())

    def test_the_registry_may_not_invent_a_record(self):
        self.assert_registry_rejected(
            lambda reg: reg["records"].append(
                {"source_id": "imaginary", "path": "imaginary.json"}
            )
        )

    def test_the_registry_may_not_overstate_what_is_open(self):
        self.assert_registry_rejected(
            lambda reg: reg["obtainable_without_contact"].append("torgo")
        )

    def test_the_registry_may_not_overstate_commercial_permission(self):
        self.assert_registry_rejected(
            lambda reg: reg["commercial_use_permitted"].append("neurovoz")
        )

    def test_the_registry_may_not_claim_a_selection(self):
        self.assert_registry_rejected(
            lambda reg: reg["counts"].__setitem__("selected", 1)
        )

    def test_the_registry_may_not_claim_a_truth_requirement_is_met(self):
        self.assert_registry_rejected(
            lambda reg: reg["counts"].__setitem__(
                "recorded_as_meeting_an_item_23_truth_requirement", 1
            )
        )

    def test_the_registry_may_not_authorise_acquisition(self):
        self.assert_registry_rejected(
            lambda reg: reg.__setitem__("acquisition_authorised", True)
        )

    def test_no_cross_source_rule_may_be_weakened(self):
        for name in REQUIRED_CROSS_SOURCE_RULES:
            with self.subTest(rule=name):
                self.assert_registry_rejected(
                    lambda reg, key=name: reg["cross_source_rules"].__setitem__(
                        key, True
                    )
                )

    def test_a_lane_conclusion_may_not_be_dropped(self):
        for lane in REQUIRED_LANES:
            with self.subTest(lane=lane):
                self.assert_registry_rejected(
                    lambda reg, key=lane: reg["lane_conclusions"].pop(key)
                )

    def test_limitations_may_not_be_removed(self):
        self.assert_registry_rejected(lambda reg: reg.__setitem__("limitations", []))

    # -- the findings this checkpoint must not lose ------------------------

    def test_the_motor_lane_records_that_no_source_qualifies(self):
        lane = self.registry["lane_conclusions"]["motor_task_timing_and_accuracy"]
        self.assertEqual(lane["answer"], "no_qualifying_source_located")

    def test_the_intelligibility_lane_records_that_none_is_lawfully_usable(self):
        lane = self.registry["lane_conclusions"]["intelligibility"]
        self.assertEqual(lane["answer"], "no_lawfully_usable_source_located")

    def test_australian_english_remains_unavailable(self):
        self.assertEqual(
            self.registry["lane_conclusions"]["australian_english"]["answer"],
            "none_located",
        )
        austalk = self.by_id["austalk_alveo"]
        self.assertEqual(austalk["access"]["state"], "unobtainable")

    def test_the_only_open_perceptual_source_stays_unresolved(self):
        open_records = [
            record
            for record in self.records
            if record["eligibility"]["decision"] == OPEN_DECISION
        ]
        self.assertEqual([record["source_id"] for record in open_records], ["pvqd"])
        self.assertEqual(open_records[0]["reference_truth"]["requirement_status"], "unresolved")

    def test_single_rater_sources_fail(self):
        for source_id in ("saarbruecken_grb_labels", "neurovoz"):
            with self.subTest(source=source_id):
                truth = self.by_id[source_id]["reference_truth"]
                self.assertEqual(truth["offered_truth_class"], "perceptual_voice_single_rater")
                self.assertEqual(truth["requirement_status"], "fails")

    def test_the_organisation_blocker_is_recorded(self):
        access = self.by_id["speech_accessibility_project"]["access"]
        self.assertTrue(access["organisation_signatory_required"])
        self.assertEqual(
            self.by_id["speech_accessibility_project"]["eligibility"]["decision"],
            "blocked_access_requires_organisation",
        )


if __name__ == "__main__":
    unittest.main()
