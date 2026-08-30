import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from reliability.audit import (
    compare_repeat_artifacts,
    run_audit,
)
from regression.harness import REPO_ROOT, sha256_file


def protected_hashes():
    paths = [REPO_ROOT / "history.json", REPO_ROOT / "progress.md"]
    paths.extend(sorted((REPO_ROOT / "output").glob("*")))
    return {
        path.relative_to(REPO_ROOT).as_posix(): sha256_file(path)
        for path in paths if path.is_file()
    }


def artifact(label, *, audio_hash="same", source_hash="source", words=None):
    words = words or [
        {"text": "hello", "speaker": "SPEAKER_00"},
        {"text": "world", "speaker": "SPEAKER_00"},
    ]
    return {
        "label": label,
        "directory": f"/isolated/{label}",
        "manifest": {
            "status": "complete",
            "provenance": {
                "pipeline": {
                    "version": "test",
                    "source": {"source_tree_sha256": source_hash},
                },
                "input_audio": {
                    "byte_sha256": audio_hash,
                    "duration_s": 10.0,
                    "codec": "wav",
                    "sample_rate_hz": 16000,
                    "channels": 1,
                },
            },
        },
        "master": {
            "meta": {"recording_type": "solo"},
            "computed_metrics": {
                "SPEAKER_00": {"wpm": 120.0, "filler_count": 1},
            },
        },
        "transcript": {"language_code": "en"},
        "words": words,
        "quality": {"overall_status": "pass"},
    }


def exact_result(status="pass"):
    return {
        "status": status,
        "requirement": "exact",
        "runs": 2,
        "differences": [] if status == "pass" else ["$.metric changed"],
        "stages_exercised": [],
        "deliberate_change_controls": {
            "status": "pass", "metrics": {}, "failures": [],
        },
    }


class ReliabilityAuditTests(unittest.TestCase):
    def test_same_recording_comparison_names_disagreement_not_error(self):
        left = artifact("left")
        right = artifact("right", words=[
            {"text": "hello", "speaker": "SPEAKER_00"},
            {"text": "there", "speaker": "SPEAKER_00"},
        ])

        result = compare_repeat_artifacts(left, right)

        self.assertEqual(result["status"], "observed")
        self.assertEqual(result["word_disagreement"]["edit_count"], 1)
        self.assertIn("not word error rate",
                      result["word_disagreement"]["interpretation"])

    def test_changed_source_invalidates_repeat_comparison(self):
        result = compare_repeat_artifacts(
            artifact("left"), artifact("right", source_hash="different")
        )

        self.assertEqual(result["status"], "invalid_comparison")
        self.assertFalse(result["protocol_conditions"]["same_source_tree"])

    def test_audit_is_isolated_and_missing_groups_make_no_fairness_claim(self):
        before = protected_hashes()
        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir) / "report"
            report = run_audit(
                repeat_artifacts=[artifact("first"), artifact("second")],
                report_dir=report_dir,
            )
            self.assertTrue((report_dir / "reliability_fairness.json").is_file())
            self.assertTrue((report_dir / "reliability_fairness.md").is_file())

        self.assertEqual(before, protected_hashes())
        self.assertEqual(report["status"], "pass_with_limits")
        self.assertEqual(
            report["repeatability"]["deterministic_exact"]["status"], "pass"
        )
        self.assertEqual(report["fairness"]["status"], "not_evaluated")
        self.assertIn("No fairness conclusion", report["fairness"]["claim"])
        self.assertEqual(report["release_gates"]["individual_progress"]
                         ["status"], "block")
        self.assertFalse(report["diagnostic_claims"]["made"])

    def test_exact_repeatability_failure_blocks_the_audit(self):
        with patch("reliability.audit._exact_repeatability",
                   return_value=exact_result("fail")):
            report = run_audit()

        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["release_gates"]
                         ["phase_a_exact_repeatability"]["status"], "block")

    def test_one_output_used_in_two_comparisons_counts_once(self):
        shared = artifact("repeat_name")
        alias = {**shared, "label": "encoding_name"}
        with patch("reliability.audit._exact_repeatability",
                   return_value=exact_result()):
            report = run_audit(
                repeat_artifacts=[shared], encoding_artifacts=[alias]
            )

        self.assertEqual(report["fairness"]["recordings"], 1)

    def test_subgroup_metadata_needs_source_and_consent(self):
        sample = artifact("sample")
        without_consent = {
            "sample": {
                "participant_id": "participant_001",
                "language": "en",
                "source": "participant self report",
            }
        }
        with_consent = {
            "sample": {
                **without_consent["sample"],
                "consent_for_fairness_audit": True,
            }
        }
        with patch("reliability.audit._exact_repeatability",
                   return_value=exact_result()):
            blocked = run_audit(
                other_artifacts=[sample], study_metadata=without_consent
            )
            eligible = run_audit(
                other_artifacts=[sample], study_metadata=with_consent
            )

        self.assertEqual(blocked["fairness"]["dimensions"]["language"]
                         ["eligible_independent_participants"], 0)
        self.assertEqual(eligible["fairness"]["dimensions"]["language"]
                         ["eligible_independent_participants"], 1)


if __name__ == "__main__":
    unittest.main()
