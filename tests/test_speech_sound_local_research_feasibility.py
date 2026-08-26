import json
import unittest
from pathlib import Path

from speech_sound_patterns.provider_register import (
    lane_status,
    load_register,
)

REPORT_PATH = (
    Path(__file__).resolve().parent.parent
    / "speech_sound_patterns"
    / "local-research-feasibility-v1.0.0.json"
)

FEASIBLE_STATUSES = {"feasible", "feasible_supporting_only"}
BLOCKED_STATUSES = {"not_run_blocked"}


class LocalResearchFeasibilityReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        cls.register = load_register()

    def test_report_scope_and_no_selection(self):
        self.assertEqual(self.report["checkpoint"], "22E2")
        self.assertIn("no accuracy claim", self.report["scope_statement"].lower())
        self.assertIn("no_selection_notice", self.report)

    def test_every_candidate_has_a_valid_status(self):
        for name, candidate in self.report["candidates"].items():
            self.assertIn(
                candidate["status"],
                FEASIBLE_STATUSES | BLOCKED_STATUSES,
                msg=name,
            )
            if candidate["status"] in BLOCKED_STATUSES:
                self.assertTrue(candidate["reason"], msg=name)

    def test_feasible_candidates_prove_exact_repeats(self):
        for name, candidate in self.report["candidates"].items():
            if candidate["status"] in FEASIBLE_STATUSES:
                self.assertIs(candidate["all_repeats_exact"], True, msg=name)
                self.assertEqual(candidate["same_input_repeats"], 2, msg=name)

    def test_report_agrees_with_the_provider_register(self):
        expectations = {
            "segmentation_free_gop": "ready",
            "powsm": "ready",
            "wav2vec2_commonphone": "supporting_only",
            "zipa": "conditional",
            "unsw_speech_attributes": "blocked",
            "child_phoneme_model": "blocked",
        }
        for lane_id, expected in expectations.items():
            self.assertEqual(
                lane_status(lane_id, self.register), expected, msg=lane_id
            )
        for lane_id in ("zipa", "unsw_speech_attributes", "child_phoneme_model"):
            self.assertIn(
                self.report["candidates"][lane_id]["status"],
                BLOCKED_STATUSES,
                msg=lane_id,
            )

    def test_blocked_candidates_downloaded_nothing(self):
        for lane_id in ("zipa", "unsw_speech_attributes", "child_phoneme_model"):
            candidate = self.report["candidates"][lane_id]
            self.assertNotIn("model_files_sha256", candidate, msg=lane_id)

    def test_feasible_candidates_pin_their_files(self):
        for name in ("powsm", "wav2vec2_commonphone"):
            files = self.report["candidates"][name]["model_files_sha256"]
            self.assertTrue(files, msg=name)
            for digest in files.values():
                self.assertRegex(digest, r"^[0-9a-f]{64}$", msg=name)

    def test_commonphone_independence_limits_recorded(self):
        candidate = self.report["candidates"]["wav2vec2_commonphone"]
        limits = candidate["independence_limits"].lower()
        self.assertIn("common phone", limits)
        self.assertIn("common voice", limits)
        self.assertIn("never count", limits)


if __name__ == "__main__":
    unittest.main()
