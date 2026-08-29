"""The credential preflight decides what a run needs before it spends anything.

The runner read no credential at all until 2026-08-28. Stages loaded their own
keys when they ran, and the stages that need one run last, so a missing key was
reported after a paid transcription rather than before it.

Nothing here uses a real key value, and no test writes one.
"""

import os
import unittest
from unittest import mock

from pipeline.credentials import (
    ASSEMBLYAI,
    GEMINI,
    GEMINI_REFEREE,
    HUGGING_FACE,
    check_credentials,
    required_credentials,
)

ALL_THREE = {
    "ASSEMBLYAI_API_KEY": "placeholder-not-a-key",
    "HF_TOKEN": "placeholder-not-a-key",
    "GEMINI_API_KEY": "placeholder-not-a-key",
}


def variables(records):
    return [record["variable"] for record in records]


class RequiredCredentialTests(unittest.TestCase):

    def test_the_local_solo_path_needs_nothing(self):
        blocking, advisory = required_credentials("solo", "local", False)
        self.assertEqual(blocking, [])
        self.assertEqual(advisory, [])

    def test_the_default_transcriber_needs_a_paid_key(self):
        blocking, _ = required_credentials("solo", "assemblyai", False)
        self.assertEqual(variables(blocking), [ASSEMBLYAI["variable"]])

    def test_conversation_needs_a_hugging_face_token_on_either_transcriber(self):
        for transcriber in ("assemblyai", "local"):
            with self.subTest(transcriber=transcriber):
                blocking, _ = required_credentials(
                    "conversation", transcriber, False
                )
                self.assertIn(HUGGING_FACE["variable"], variables(blocking))

    def test_interpret_makes_the_model_key_blocking(self):
        blocking, advisory = required_credentials("solo", "local", True)
        self.assertEqual(variables(blocking), [GEMINI["variable"]])
        self.assertEqual(advisory, [])

    def test_the_referee_key_only_advises_because_nobody_asked_for_it(self):
        """Conversation mode runs the referee without --interpret.

        Stopping the run for a stage the caller never requested would refuse
        work the pipeline is designed to complete by degrading.
        """
        blocking, advisory = required_credentials("conversation", "local", False)
        self.assertNotIn(GEMINI["variable"], variables(blocking))
        self.assertEqual(variables(advisory), [GEMINI_REFEREE["variable"]])


class CheckCredentialTests(unittest.TestCase):

    def check(self, environment, *arguments):
        with mock.patch.dict(os.environ, environment, clear=True):
            return check_credentials(*arguments, load=False)

    def test_a_complete_environment_does_not_stop_the_run(self):
        stop, warnings = self.check(ALL_THREE, "conversation", "assemblyai", True)
        self.assertIsNone(stop)
        self.assertEqual(warnings, [])

    def test_the_credential_free_path_never_stops_even_with_nothing_set(self):
        stop, warnings = self.check({}, "solo", "local", False)
        self.assertIsNone(stop)
        self.assertEqual(warnings, [])

    def test_a_missing_key_names_the_variable_and_where_to_get_it(self):
        stop, _ = self.check({}, "solo", "assemblyai", False)
        self.assertIn("ASSEMBLYAI_API_KEY", stop)
        self.assertIn("assemblyai.com", stop)

    def test_a_missing_paid_key_offers_the_free_path(self):
        stop, _ = self.check({}, "solo", "assemblyai", False)
        self.assertIn("--transcriber local", stop)

    def test_the_hugging_face_finding_carries_the_agreement_step(self):
        """A valid token still returns a bare 401 without the agreement."""
        stop, _ = self.check({}, "conversation", "local", False)
        self.assertIn("HF_TOKEN", stop)
        self.assertIn("pyannote/speaker-diarization-3.1", stop)

    def test_an_empty_string_counts_as_missing(self):
        stop, _ = self.check({"ASSEMBLYAI_API_KEY": "   "}, "solo",
                             "assemblyai", False)
        self.assertIn("ASSEMBLYAI_API_KEY", stop)

    def test_a_missing_referee_key_warns_and_lets_the_run_continue(self):
        environment = dict(ALL_THREE)
        del environment["GEMINI_API_KEY"]
        stop, warnings = self.check(environment, "conversation", "local", False)
        self.assertIsNone(stop)
        self.assertEqual(len(warnings), 1)
        self.assertIn("GEMINI_API_KEY", warnings[0])
        self.assertIn("continues", warnings[0])

    def test_the_same_missing_key_stops_the_run_once_interpret_is_asked_for(self):
        environment = dict(ALL_THREE)
        del environment["GEMINI_API_KEY"]
        stop, _ = self.check(environment, "conversation", "local", True)
        self.assertIsNotNone(stop)
        self.assertIn("GEMINI_API_KEY", stop)

    def test_every_missing_key_is_reported_together(self):
        """One run, one list. Fixing them one error at a time is the defect."""
        stop, _ = self.check({}, "conversation", "assemblyai", True)
        for variable in ("ASSEMBLYAI_API_KEY", "HF_TOKEN", "GEMINI_API_KEY"):
            with self.subTest(variable=variable):
                self.assertIn(variable, stop)

    def test_no_key_value_is_ever_echoed_back(self):
        environment = {"ASSEMBLYAI_API_KEY": "sensitive-value-abc123"}
        stop, warnings = self.check(environment, "conversation", "assemblyai", True)
        self.assertNotIn("sensitive-value-abc123", stop)
        for warning in warnings:
            self.assertNotIn("sensitive-value-abc123", warning)


if __name__ == "__main__":
    unittest.main()
