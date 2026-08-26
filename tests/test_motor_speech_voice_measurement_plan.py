import copy
import unittest

from motor_speech_voice.measurement_plan import (
    OPEN_CANDIDATE_DECISION,
    REGISTRY_PATH,
    REQUIRED_BLOCKER_CLASSES,
    REQUIRED_GOVERNANCE_LANES,
    SCHEMA_PATH,
    is_live_candidate,
    load_json,
    numeric_locations,
    record_paths,
    survey_source_states,
    validate_plan,
    validate_record,
    validate_registry,
)


class MeasurementPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = load_json(SCHEMA_PATH)
        cls.registry = load_json(REGISTRY_PATH)
        cls.records = [load_json(path) for path in record_paths()]
        cls.by_id = {record["candidate_id"]: record for record in cls.records}
        cls.survey_states = survey_source_states()

    def record(self, candidate_id, update):
        document = copy.deepcopy(self.by_id[candidate_id])
        update(document)
        return document

    def assert_record_rejected(self, candidate_id, update, fragment=None):
        errors = validate_record(
            self.record(candidate_id, update),
            self.schema,
            f"{candidate_id}.json",
            self.survey_states,
        )
        self.assertTrue(errors, "the mutated record should have been rejected")
        if fragment is not None:
            self.assertTrue(
                any(fragment in error for error in errors),
                f"expected an error mentioning {fragment!r}, got {errors}",
            )

    def assert_registry_rejected(self, update, fragment=None):
        registry = copy.deepcopy(self.registry)
        update(registry)
        errors = validate_registry(registry, self.records)
        self.assertTrue(errors, "the mutated registry should have been rejected")
        if fragment is not None:
            self.assertTrue(
                any(fragment in error for error in errors),
                f"expected an error mentioning {fragment!r}, got {errors}",
            )

    # -- the committed state ------------------------------------------------

    def test_the_committed_package_is_valid(self):
        self.assertEqual(validate_plan(), [])

    def test_every_record_validates_and_selects_nothing(self):
        for record in self.records:
            with self.subTest(candidate=record["candidate_id"]):
                self.assertEqual(
                    validate_record(
                        record, self.schema, record["candidate_id"], self.survey_states
                    ),
                    [],
                )
                self.assertIs(record["selected"], False)
                self.assertIsNone(record["sample_size"]["computed_value"])
                self.assertEqual(
                    record["estimand_shape"]["status"], "candidate_shape_not_selected"
                )

    def test_every_provisional_construct_is_covered(self):
        self.assertEqual(len(self.records), 12)

    def test_every_governance_lane_has_a_summary(self):
        self.assertEqual(
            REQUIRED_GOVERNANCE_LANES, set(self.registry["lane_summaries"])
        )

    # -- the no numbers rule ------------------------------------------------

    def test_no_committed_record_contains_a_number(self):
        for record in self.records:
            with self.subTest(candidate=record["candidate_id"]):
                self.assertEqual(numeric_locations(record), [])

    # Two layers refuse a number, and which one fires depends on where the
    # number is put.  The schema blocks every location it currently defines, and
    # the numeric scan is the backstop for any location a later schema version
    # adds.  These tests assert the property rather than the layer.

    def test_a_number_added_to_a_record_is_refused(self):
        self.assert_record_rejected(
            "rapid_syllable_timing",
            lambda document: document.update({"participants_required": 30}),
        )

    def test_a_number_buried_deep_in_a_record_is_refused(self):
        def bury(document):
            document["agreement_and_reliability"]["form_selection_inputs"] = [0.75]

        self.assert_record_rejected("rapid_syllable_timing", bury)

    def test_the_numeric_backstop_catches_what_a_looser_schema_would_allow(self):
        # A record shaped like a future schema version that added a free form
        # object.  The schema would pass it; the numeric scan must not.
        document = copy.deepcopy(self.by_id["rapid_syllable_timing"])
        document["sample_size"]["computed_value"] = 30
        self.assertEqual(
            numeric_locations(document), ["sample_size/computed_value"]
        )

    def test_booleans_are_not_treated_as_numbers(self):
        self.assertEqual(numeric_locations({"flag": True, "other": False}), [])

    def test_the_numeric_scan_finds_floats_and_reports_where(self):
        found = numeric_locations({"a": {"b": [1, "x", 2.5]}})
        self.assertEqual(found, ["a/b[0]", "a/b[2]"])

    # -- selection and claim level -----------------------------------------

    def test_a_selected_construct_is_refused(self):
        self.assert_record_rejected(
            "rapid_syllable_timing",
            lambda document: document.update({"selected": True}),
        )

    def test_a_selected_estimand_is_refused(self):
        def select(document):
            document["estimand_shape"]["status"] = "selected"

        self.assert_record_rejected("controlled_intelligibility", select)

    def test_a_raised_claim_level_is_refused(self):
        def raise_claim(document):
            document["observation"]["claim_level"] = "screening_hypothesis"

        self.assert_record_rejected("rapid_syllable_timing", raise_claim)

    def test_a_computed_sample_size_is_refused(self):
        def size(document):
            document["sample_size"]["computed_value"] = 100

        self.assert_record_rejected("rapid_syllable_timing", size)

    def test_a_settled_sample_size_state_is_refused(self):
        def settle(document):
            document["sample_size"]["state"] = "computed"

        self.assert_record_rejected("rapid_syllable_timing", settle)

    # -- the honest blockers ------------------------------------------------

    def test_every_record_keeps_every_required_blocker(self):
        for record in self.records:
            with self.subTest(candidate=record["candidate_id"]):
                present = {item["blocker_class"] for item in record["blockers"]}
                self.assertTrue(REQUIRED_BLOCKER_CLASSES <= present)

    def test_dropping_a_blocker_is_refused(self):
        def drop(document):
            document["blockers"] = [
                item
                for item in document["blockers"]
                if item["blocker_class"] != "no_legal_entity"
            ]

        self.assert_record_rejected(
            "rapid_syllable_timing", drop, "dropped required blockers"
        )

    # -- measurement error, abstention and splits ---------------------------

    def test_dropping_the_measurement_error_requirement_is_refused(self):
        def drop(document):
            document["agreement_and_reliability"]["measurement_error_required"] = False

        self.assert_record_rejected("rapid_syllable_timing", drop)

    def test_pooling_abstention_is_refused(self):
        def pool(document):
            document["missingness_and_abstention"]["reported_separately"] = False

        self.assert_record_rejected("rapid_syllable_timing", pool)

    def test_weakening_the_split_unit_is_refused(self):
        def weaken(document):
            document["split_and_clustering"]["minimum_split_unit"] = "recording"

        self.assert_record_rejected("rapid_syllable_timing", weaken)

    # -- agreement with the source survey -----------------------------------

    def test_only_one_source_is_a_live_candidate(self):
        live = sorted(
            source
            for source, state in self.survey_states.items()
            if is_live_candidate(state)
        )
        self.assertEqual(live, ["pvqd"])

    def test_an_unresolved_source_that_cannot_be_obtained_is_not_a_candidate(self):
        for source in ("younger_nt_adults", "alois_db", "osf_slp_intelligibility_estimations"):
            with self.subTest(source=source):
                state = self.survey_states[source]
                self.assertEqual(state["requirement_status"], "unresolved")
                self.assertFalse(is_live_candidate(state))

    def test_citing_a_source_outside_the_survey_is_refused(self):
        def invent(document):
            document["reference_requirement"]["source_survey_basis"] = ["invented_corpus"]

        self.assert_record_rejected(
            "rapid_syllable_timing", invent, "not in the checkpoint 23B source survey"
        )

    def test_claiming_nothing_exists_while_citing_the_open_candidate_is_refused(self):
        def contradict(document):
            document["reference_requirement"]["source_survey_basis"] = ["pvqd"]

        self.assert_record_rejected(
            "rapid_syllable_timing", contradict, "claims nothing usable exists"
        )

    def test_claiming_an_open_candidate_without_one_is_refused(self):
        def strip(document):
            document["reference_requirement"]["source_survey_basis"] = ["ewa_db"]

        self.assert_record_rejected(
            "voice_perceptual_judgement", strip, "claims an open candidate"
        )

    def test_a_surveyed_outcome_must_name_its_basis(self):
        def strip(document):
            document["reference_requirement"]["source_survey_basis"] = []

        self.assert_record_rejected(
            "controlled_intelligibility", strip, "without naming the source survey"
        )

    def test_an_unsurveyed_question_may_not_cite_survey_records(self):
        def cite(document):
            document["reference_requirement"]["source_survey_basis"] = ["pvqd"]

        self.assert_record_rejected(
            "articulation_rate", cite, "claiming the question was not surveyed"
        )

    def test_the_open_candidate_decision_is_the_surveys_own_value(self):
        self.assertEqual(OPEN_CANDIDATE_DECISION, "open_but_truth_class_unresolved")

    # -- the registry -------------------------------------------------------

    def test_a_registry_that_hides_a_record_is_refused(self):
        self.assert_registry_rejected(
            lambda registry: registry["records"].pop(),
            "records on disk are not listed",
        )

    def test_a_registry_that_invents_a_record_is_refused(self):
        def invent(registry):
            registry["records"].append(
                {
                    "candidate_id": "invented",
                    "record_id": "invented_measurement_inputs_v1",
                    "register_lane": "motor_task",
                    "governance_lane": "motor_speech",
                    "public_availability": "no_qualifying_public_source",
                }
            )

        self.assert_registry_rejected(invent, "listed records do not exist")

    def test_a_registry_claiming_a_selection_is_refused(self):
        def claim(registry):
            registry["counts"]["selected"] = 1

        self.assert_registry_rejected(claim, "non zero selected")

    def test_a_registry_claiming_a_computed_sample_size_is_refused(self):
        def claim(registry):
            registry["counts"]["sample_sizes_computed"] = 12

        self.assert_registry_rejected(claim, "non zero sample_sizes_computed")

    def test_a_registry_that_relabels_a_lane_is_refused(self):
        def relabel(registry):
            registry["records"][0]["governance_lane"] = "voice"

        self.assert_registry_rejected(relabel, "different governance lane")

    def test_a_registry_that_softens_a_lane_availability_is_refused(self):
        def soften(registry):
            registry["records"][0]["public_availability"] = "one_candidate_unresolved"

        self.assert_registry_rejected(soften, "different reference availability")

    def test_a_lane_summary_that_disagrees_with_its_records_is_refused(self):
        def disagree(registry):
            registry["lane_summaries"]["motor_speech"]["questions"] = ["articulation_rate"]

        self.assert_registry_rejected(disagree, "do not match the records assigned")

    def test_removing_the_method_notes_is_refused(self):
        self.assert_registry_rejected(
            lambda registry: registry.update({"method_notes": []}),
            "method_notes was removed",
        )

    def test_removing_what_this_is_not_is_refused(self):
        self.assert_registry_rejected(
            lambda registry: registry.update({"what_this_is_not": []}),
            "what_this_is_not was removed",
        )

    def test_softening_the_status_is_refused(self):
        self.assert_registry_rejected(
            lambda registry: registry.update({"status": "plan_complete"}),
            "nothing was selected",
        )


if __name__ == "__main__":
    unittest.main()
