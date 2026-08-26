import copy
import unittest

from motor_speech_voice.regulatory_reading import (
    LADDER_ORDER,
    REGISTRY_PATH,
    REQUIRED_TOP_RUNG_POSITION,
    SCHEMA_PATH,
    load_json,
    record_paths,
    validate_ladder,
    validate_reading,
    validate_record,
    validate_registry,
)


class RegulatoryReadingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = load_json(SCHEMA_PATH)
        cls.registry = load_json(REGISTRY_PATH)
        cls.records = [load_json(path) for path in record_paths()]
        cls.by_id = {record["question_id"]: record for record in cls.records}

    def record(self, question_id, update):
        document = copy.deepcopy(self.by_id[question_id])
        update(document)
        return document

    def assert_record_rejected(self, question_id, update, fragment=None):
        errors = validate_record(
            self.record(question_id, update), self.schema, f"{question_id}.json"
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

    def assert_ladder_rejected(self, update, fragment=None):
        ladder = copy.deepcopy(self.registry["purpose_ladder"])
        update(ladder)
        errors = validate_ladder(ladder)
        self.assertTrue(errors, "the mutated ladder should have been rejected")
        if fragment is not None:
            self.assertTrue(
                any(fragment in error for error in errors),
                f"expected an error mentioning {fragment!r}, got {errors}",
            )

    # -- the committed state ------------------------------------------------

    def test_the_committed_reading_is_valid(self):
        self.assertEqual(validate_reading(), [])

    def test_every_record_validates_and_determines_nothing(self):
        for record in self.records:
            with self.subTest(question=record["question_id"]):
                self.assertEqual(
                    validate_record(record, self.schema, record["question_id"]), []
                )
                self.assertIs(record["is_legal_or_regulatory_advice"], False)
                self.assertIs(record["creates_any_authority"], False)
                self.assertEqual(
                    record["status"], "documented_reading_not_a_determination"
                )

    def test_every_record_rests_on_something_read_at_source(self):
        for record in self.records:
            with self.subTest(question=record["question_id"]):
                self.assertTrue(
                    any(
                        source["read_at_source"]
                        for source in record["primary_sources"]
                    )
                )

    def test_every_record_names_someone_who_must_settle_it(self):
        for record in self.records:
            with self.subTest(question=record["question_id"]):
                self.assertTrue(record["decided_by"])

    def test_no_record_names_a_condition(self):
        # Checkpoint 23A prohibits selecting a named motor speech condition or
        # voice disorder. The reading discusses regulation, never a diagnosis.
        forbidden = ("dysarthria", "apraxia", "parkinson", "dysphonia", "aphasia")
        for record in self.records:
            blob = repr(record).lower()
            for term in forbidden:
                with self.subTest(question=record["question_id"], term=term):
                    self.assertNotIn(term, blob)

    # -- what a record may not become ---------------------------------------

    def test_a_record_claiming_to_be_advice_is_refused(self):
        self.assert_record_rejected(
            "medical_device_definition",
            lambda document: document.update({"is_legal_or_regulatory_advice": True}),
        )

    def test_a_record_claiming_authority_is_refused(self):
        self.assert_record_rejected(
            "medical_device_definition",
            lambda document: document.update({"creates_any_authority": True}),
        )

    def test_a_record_claiming_to_be_a_determination_is_refused(self):
        self.assert_record_rejected(
            "medical_device_definition",
            lambda document: document.update({"status": "determination"}),
        )

    def test_a_record_resting_only_on_secondary_description_is_refused(self):
        def secondary(document):
            for source in document["primary_sources"]:
                source["read_at_source"] = False

        self.assert_record_rejected(
            "medical_device_definition", secondary, "read directly"
        )

    def test_uncertainty_without_an_open_question_is_refused(self):
        def hide(document):
            document["unresolved"] = []

        self.assert_record_rejected(
            "wellness_and_coaching_exclusions", hide, "without naming a single"
        )

    def test_the_owner_cannot_be_the_only_decider_of_a_legal_question(self):
        def claim(document):
            document["decided_by"] = ["owner"]

        self.assert_record_rejected(
            "queensland_recording_and_publication", claim, "only decider"
        )

    # -- the purpose ladder -------------------------------------------------

    def test_the_ladder_has_three_rungs_in_order(self):
        self.assertEqual(list(self.registry["purpose_ladder"]), LADDER_ORDER)

    def test_only_the_research_rung_is_occupied(self):
        occupied = [
            name
            for name, body in self.registry["purpose_ladder"].items()
            if body["occupied_today"]
        ]
        self.assertEqual(occupied, [LADDER_ORDER[0]])

    def test_the_screening_rung_is_pinned_as_a_device_with_no_exclusion(self):
        self.assertEqual(
            self.registry["purpose_ladder"][LADDER_ORDER[2]][
                "medical_device_position"
            ],
            REQUIRED_TOP_RUNG_POSITION,
        )

    def test_softening_the_screening_rung_is_refused(self):
        def soften(ladder):
            ladder[LADDER_ORDER[2]][
                "medical_device_position"
            ] = "may_be_a_device_and_may_be_excluded"

        self.assert_ladder_rejected(soften, "no longer records")

    def test_a_ladder_that_stops_getting_stricter_is_refused(self):
        def flatten(ladder):
            ladder[LADDER_ORDER[1]][
                "medical_device_position"
            ] = "likely_outside_the_definition"

        self.assert_ladder_rejected(flatten, "strictly stricter")

    def test_claiming_a_product_rung_is_occupied_is_refused(self):
        def occupy(ladder):
            ladder[LADDER_ORDER[1]]["occupied_today"] = True

        self.assert_ladder_rejected(occupy, "occupied rung")

    def test_a_rung_that_lists_nothing_still_applying_is_refused(self):
        def strip(ladder):
            ladder[LADDER_ORDER[0]]["what_still_applies"] = []

        self.assert_ladder_rejected(strip, "nothing that still applies")

    def test_removing_a_rung_is_refused(self):
        self.assert_ladder_rejected(
            lambda ladder: ladder.pop(LADDER_ORDER[2]), "missing rungs"
        )

    # -- the registry -------------------------------------------------------

    def test_removing_the_standing_disclaimer_is_refused(self):
        self.assert_registry_rejected(
            lambda registry: registry.update({"standing_disclaimer": "A reading."}),
            "standing disclaimer",
        )

    def test_a_registry_claiming_a_determination_is_refused(self):
        self.assert_registry_rejected(
            lambda registry: registry["counts"].update({"determinations_made": 1}),
            "non zero determinations_made",
        )

    def test_a_registry_claiming_advice_was_received_is_refused(self):
        self.assert_registry_rejected(
            lambda registry: registry["counts"].update({"advice_received": 1}),
            "non zero advice_received",
        )

    def test_a_registry_that_hides_an_open_question_is_refused(self):
        self.assert_registry_rejected(
            lambda registry: registry["counts"].update({"open_questions_recorded": 0}),
            "open question count",
        )

    def test_a_registry_that_hides_a_source_conflict_is_refused(self):
        self.assert_registry_rejected(
            lambda registry: registry["counts"].update({"source_conflicts_recorded": 0}),
            "source conflict count",
        )

    def test_a_registry_that_hides_a_record_is_refused(self):
        self.assert_registry_rejected(
            lambda registry: registry["records"].pop(),
            "records on disk are not listed",
        )

    def test_a_registry_that_relabels_a_confidence_is_refused(self):
        def relabel(registry):
            for entry in registry["records"]:
                entry["confidence"] = "clear_on_the_face_of_the_source"

        self.assert_registry_rejected(relabel, "different confidence")

    def test_softening_the_status_is_refused(self):
        self.assert_registry_rejected(
            lambda registry: registry.update({"status": "assessment_complete"}),
            "no determination was made",
        )

    def test_removing_what_this_is_not_is_refused(self):
        self.assert_registry_rejected(
            lambda registry: registry.update({"what_this_is_not": []}),
            "what_this_is_not was removed",
        )


if __name__ == "__main__":
    unittest.main()
