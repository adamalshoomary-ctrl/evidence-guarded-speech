"""Guards on what the optional interpretation layer is allowed to produce.

Item R5 deleted five language model scores on 2026-08-24. They rated a person
0 to 99 on CLARITY, WIT, WARMTH, PRESENCE and STORY, they were parsed out of
prose by regular expression, they were never validated as measurement scales,
and they addressed an audience this project states it does not have.

These tests exist because that kind of thing comes back. Several of them read
source text rather than calling a function: `pipeline/evaluate.py` parses
arguments and reads credentials at import time, so it cannot be imported in a
test, and the prompt is the artifact that matters here.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))

from pipeline.claim_ledger import (
    SUPERSEDED_CLAIM_TYPES,
    CLAIM_LEDGER_SCHEMA_VERSION,
    CLAIM_VERIFICATION_VERSION,
)
from pipeline.personal_progress import HISTORY_RECORD_VERSION


REPO_ROOT = Path(__file__).resolve().parent.parent
DELETED_SCORES = ("Clarity", "Wit", "Warmth", "Presence", "Story")


def source(relative_path):
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


class DeletedScoreTests(unittest.TestCase):
    def test_the_evaluator_asks_for_no_score(self):
        text = source("pipeline/evaluate.py")

        for name in DELETED_SCORES:
            self.assertNotIn(name, text)
            self.assertNotIn(name.upper(), text)
        self.assertNotIn("extract_scores", text)
        self.assertNotIn("rubric", text.lower())
        self.assertNotIn("0-99", text)

    def test_the_evaluator_has_no_persona_and_prescribes_nothing(self):
        text = source("pipeline/evaluate.py")

        self.assertNotIn("You are an elite", text)
        self.assertNotIn("communication coach", text)
        self.assertNotIn("One drill", text)

    def test_history_records_no_language_model_output(self):
        text = source("pipeline/history.py")

        self.assertNotIn("stat_scores", text)
        self.assertNotIn("extract_scores", text)
        self.assertEqual(HISTORY_RECORD_VERSION, "3.0.0")

    def test_the_duplicated_score_parser_is_gone_from_both_modules(self):
        """It lived twice, and its own comment admitted the duplication."""
        for module in ("pipeline/evaluate.py", "pipeline/history.py"):
            with self.subTest(module=module):
                self.assertNotIn("Pull '- **Stats", source(module))


class ClaimVocabularyTests(unittest.TestCase):
    def test_the_coaching_claim_type_was_renamed_not_kept(self):
        self.assertEqual(
            SUPERSEDED_CLAIM_TYPES["coaching_interpretation"], "interpretation"
        )

    def test_the_prescription_claim_type_was_withdrawn(self):
        """It was the only type allowed to exist without evidence."""
        self.assertIsNone(SUPERSEDED_CLAIM_TYPES["prescription"])
        self.assertNotIn("prescription", source("pipeline/verify.py"))

    def test_the_schema_version_records_the_change(self):
        self.assertEqual(CLAIM_LEDGER_SCHEMA_VERSION, "1.1.0")

    def test_the_verification_version_moved_when_the_rules_did(self):
        """The ledger shape held still; the rules judging it did not.

        Tying a claim's type to the class of evidence beneath it rejects
        ledgers the previous verifier accepted, so a stored report has to say
        which rules produced it.
        """
        self.assertEqual(CLAIM_VERIFICATION_VERSION, "1.2.0")


class EnrichmentStatusTests(unittest.TestCase):
    def test_an_unrequested_stage_is_not_reported_as_pending(self):
        """A default run never calls them, so "pending" would be a lie."""
        from llm_contract import initial_enrichment_status

        status = initial_enrichment_status()

        self.assertEqual(status["listener"]["status"], "not_requested")
        self.assertEqual(status["evaluator"]["status"], "not_requested")
        self.assertEqual(status["referee"]["status"], "pending")


class VerificationHonestyTests(unittest.TestCase):
    def test_the_report_states_what_it_does_not_demonstrate(self):
        """A clean verification report must not imply more than it earned."""
        text = source("pipeline/verify.py")

        self.assertIn("What this report does not demonstrate", text)
        self.assertIn("freedom to be wrong", text)
        self.assertIn("never rejected a claim", text)


class QualityPolicyNameTests(unittest.TestCase):
    def test_the_lenient_policy_is_called_lenient(self):
        """It warns where baseline fails. It was called "coaching"."""
        text = source("pipeline/audio_quality.py")

        self.assertIn('"lenient"', text)
        self.assertNotIn('"coaching"', text)


if __name__ == "__main__":
    unittest.main()
