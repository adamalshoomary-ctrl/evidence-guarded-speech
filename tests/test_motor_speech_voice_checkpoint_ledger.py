import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from motor_speech_voice import checkpoint_ledger
from motor_speech_voice.checkpoint_ledger import (
    BLOCKED,
    COMPLETE,
    EXPECTED_NUMBERS,
    KNOWN_ROLES,
    LEDGER_PATH,
    PARTIAL,
    load_json,
    validate_ledger,
)


class CheckpointLedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = load_json(LEDGER_PATH)

    def assert_rejected(self, update, fragment=None):
        """Validate a mutated ledger by pointing the validator at a temporary copy."""
        ledger = copy.deepcopy(self.ledger)
        update(ledger)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint-23b-ledger-v1.0.0.json"
            path.write_text(json.dumps(ledger))
            with mock.patch.object(checkpoint_ledger, "LEDGER_PATH", path):
                errors = validate_ledger()
        self.assertTrue(errors, "the mutated ledger should have been rejected")
        if fragment is not None:
            self.assertTrue(
                any(fragment in error for error in errors),
                f"expected an error mentioning {fragment!r}, got {errors}",
            )

    # -- the committed state ------------------------------------------------

    def test_the_committed_ledger_is_valid(self):
        self.assertEqual(validate_ledger(), [])

    def test_all_thirteen_deliverables_are_recorded_in_order(self):
        self.assertEqual(
            [item["number"] for item in self.ledger["deliverables"]], EXPECTED_NUMBERS
        )

    def test_the_checkpoint_is_still_in_progress(self):
        self.assertEqual(self.ledger["checkpoint_status"], "in_progress")

    def test_nothing_was_selected_contacted_spent_or_acquired(self):
        for flag in (
            "selection_recorded",
            "external_party_contacted",
            "money_spent",
            "data_acquired",
        ):
            with self.subTest(flag=flag):
                self.assertIs(self.ledger[flag], False)

    def test_most_deliverables_are_blocked_on_a_person(self):
        statuses = [item["status"] for item in self.ledger["deliverables"]]
        self.assertIn(BLOCKED, statuses)
        self.assertGreater(statuses.count(BLOCKED), statuses.count(COMPLETE))

    def test_every_incomplete_deliverable_names_a_known_role(self):
        for item in self.ledger["deliverables"]:
            if item["status"] == COMPLETE:
                continue
            with self.subTest(deliverable=item["number"]):
                self.assertTrue(item["who_supplies_it"])
                self.assertTrue(set(item["who_supplies_it"]) <= KNOWN_ROLES)

    def test_every_completed_deliverable_cites_evidence_that_exists(self):
        root = Path(__file__).resolve().parent.parent
        for item in self.ledger["deliverables"]:
            if item["status"] != COMPLETE:
                continue
            with self.subTest(deliverable=item["number"]):
                self.assertTrue(item["evidence"])
                for path in item["evidence"]:
                    self.assertTrue((root / path).exists(), path)

    def test_the_partial_deliverables_are_the_ones_this_work_advanced(self):
        partial = {
            item["number"]
            for item in self.ledger["deliverables"]
            if item["status"] == PARTIAL
        }
        self.assertEqual(partial, {"seven", "nine", "twelve"})

    # -- what the ledger may not become -------------------------------------

    def test_closing_the_checkpoint_is_refused(self):
        self.assert_rejected(
            lambda ledger: ledger.update({"checkpoint_status": "complete"}),
            "no longer recorded as in progress",
        )

    def test_claiming_a_selection_is_refused(self):
        self.assert_rejected(
            lambda ledger: ledger.update({"selection_recorded": True}),
            "selection_recorded is no longer false",
        )

    def test_claiming_someone_was_contacted_is_refused(self):
        self.assert_rejected(
            lambda ledger: ledger.update({"external_party_contacted": True}),
            "external_party_contacted",
        )

    def test_marking_everything_complete_is_refused(self):
        def complete_all(ledger):
            for item in ledger["deliverables"]:
                item["status"] = COMPLETE
                item["who_supplies_it"] = []
                item["evidence"] = ["motor_speech_voice/engineering-plan.md"]

        self.assert_rejected(complete_all, "nothing is blocked")

    def test_marking_a_deliverable_complete_without_evidence_is_refused(self):
        def fake(ledger):
            ledger["deliverables"][0]["status"] = COMPLETE
            ledger["deliverables"][0]["who_supplies_it"] = []

        self.assert_rejected(fake, "complete with no evidence")

    def test_citing_evidence_that_does_not_exist_is_refused(self):
        def invent(ledger):
            ledger["deliverables"][1]["evidence"] = [
                "motor_speech_voice/imaginary-approval.json"
            ]

        self.assert_rejected(invent, "cites evidence that does not exist")

    def test_a_complete_deliverable_that_still_needs_someone_is_refused(self):
        def contradict(ledger):
            ledger["deliverables"][1]["who_supplies_it"] = ["owner"]

        self.assert_rejected(contradict, "still naming someone")

    def test_an_unfinished_deliverable_naming_nobody_is_refused(self):
        def orphan(ledger):
            ledger["deliverables"][0]["who_supplies_it"] = []

        self.assert_rejected(orphan, "names nobody who has to finish it")

    def test_an_unknown_role_is_refused(self):
        def invent(ledger):
            ledger["deliverables"][0]["who_supplies_it"] = ["a_helpful_agent"]

        self.assert_rejected(invent, "unknown role")

    def test_dropping_a_deliverable_is_refused(self):
        self.assert_rejected(
            lambda ledger: ledger["deliverables"].pop(), "expected 13 deliverables"
        )

    def test_reordering_the_deliverables_is_refused(self):
        def reorder(ledger):
            ledger["deliverables"].reverse()

        self.assert_rejected(reorder, "in order")

    def test_counts_that_disagree_with_the_deliverables_are_refused(self):
        self.assert_rejected(
            lambda ledger: ledger["counts"].update({BLOCKED: 1}),
            "counts do not match",
        )

    def test_weakening_the_acceptance_rule_is_refused(self):
        self.assert_rejected(
            lambda ledger: ledger.update(
                {"acceptance_rule": "Acceptance is finishing the deliverables."}
            ),
            "acceptance is written review",
        )

    def test_removing_what_public_research_changed_is_refused(self):
        self.assert_rejected(
            lambda ledger: ledger.update({"what_public_research_changed": []}),
            "what public research changed was removed",
        )


if __name__ == "__main__":
    unittest.main()
