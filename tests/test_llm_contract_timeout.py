"""A hung remote enrichment call must become a failure, not a stalled run.

One checkpoint 22E5 acceptance attempt hung in the listener stage for 3 hours
54 minutes on a single request. ``run_with_retry`` caught exceptions and
retried once, but nothing ever raised, so the documented safe degrade never
fired and the stopped stage halted the run instead of degrading it.
"""

import sys
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))

from llm_contract import (  # noqa: E402
    EnrichmentTimeoutError,
    SemanticValidationError,
    call_with_deadline,
    classify_failure,
    run_with_retry,
)
from pipeline_config import (  # noqa: E402
    ENRICHMENT_ATTEMPT_DEADLINE_S,
    ENRICHMENT_REQUEST_TIMEOUT_S,
)


class EnrichmentDeadlineTests(unittest.TestCase):
    def test_a_hung_request_becomes_a_timeout(self):
        started = threading.Event()

        def never_returns():
            started.set()
            time.sleep(30)
            return "unreachable"

        began = time.monotonic()
        with self.assertRaises(EnrichmentTimeoutError):
            call_with_deadline(never_returns, deadline_s=0.2)
        self.assertTrue(started.wait(timeout=5))
        self.assertLess(time.monotonic() - began, 10)

    def test_a_hung_stage_degrades_with_an_explicit_status(self):
        def never_returns():
            time.sleep(30)

        value, status = run_with_retry(
            "listener", "test-model", never_returns, deadline_s=0.2
        )
        self.assertIsNone(value)
        self.assertEqual(status["status"], "unavailable")
        self.assertEqual(status["error_category"], "timeout")
        self.assertEqual(status["attempts"], 2)

    def test_a_normal_response_is_unaffected(self):
        value, status = run_with_retry(
            "referee", "test-model", lambda: {"ok": True}
        )
        self.assertEqual(value, {"ok": True})
        self.assertEqual(status["status"], "complete")
        self.assertEqual(status["attempts"], 1)

    def test_a_real_failure_still_reaches_its_own_category(self):
        # The deadline must not swallow or relabel the failures the pipeline
        # already classified correctly.
        def semantic_failure():
            raise SemanticValidationError("claim ledger failed verification")

        value, status = run_with_retry(
            "evaluator", "test-model", semantic_failure, deadline_s=5
        )
        self.assertIsNone(value)
        self.assertEqual(status["error_category"], "semantic_validation_failure")

    def test_a_slow_but_successful_call_is_not_cut_off(self):
        def slow():
            time.sleep(0.3)
            return "done"

        self.assertEqual(call_with_deadline(slow, deadline_s=5), "done")

    def test_the_timeout_classifies_as_a_timeout(self):
        self.assertEqual(
            classify_failure(EnrichmentTimeoutError("no response")), "timeout"
        )

    def test_the_client_aborts_before_the_backstop_does(self):
        # The provider client must get the chance to raise its own clean,
        # connection-freeing timeout first; the wall clock deadline exists for
        # what the client cannot see.
        self.assertLess(
            ENRICHMENT_REQUEST_TIMEOUT_S, ENRICHMENT_ATTEMPT_DEADLINE_S
        )


if __name__ == "__main__":
    unittest.main()
