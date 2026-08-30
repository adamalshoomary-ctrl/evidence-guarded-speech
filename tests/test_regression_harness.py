import json
import tempfile
import unittest
from pathlib import Path

from regression.harness import (
    REPO_ROOT,
    SNAPSHOT_PATH,
    bless_snapshot,
    compare_recording_truth,
    compare_synthetic_truth,
    compare_snapshot,
    load_truth,
    protected_thresholds,
    run_harness,
    sha256_file,
    structural_diff,
)


def protected_file_hashes():
    paths = [REPO_ROOT / "history.json", REPO_ROOT / "progress.md"]
    paths.extend(sorted((REPO_ROOT / "output").glob("*")))
    return {
        path.relative_to(REPO_ROOT).as_posix(): sha256_file(path)
        for path in paths if path.is_file()
    }


class RegressionHarnessTests(unittest.TestCase):
    def test_wrong_synthetic_speaker_label_fails_truth_comparison(self):
        truth = {
            "fixture_id": "speaker_test",
            "reference": {
                "source": "designed fixture",
                "adjudication_status": "synthetic_ground_truth",
            },
            "expectations": {
                "words": [{
                    "index": 0,
                    "word": "hello",
                    "speaker": "SPEAKER_01",
                    "start_s": 0.0,
                    "end_s": 0.2,
                }],
                "renderer_events": [],
                "metrics": [],
                "conditions": [],
            },
        }
        actual = {
            "speaker_attribution": [{
                "index": 0,
                "word": "hello",
                "speaker": "SPEAKER_00",
                "start_s": 0.0,
                "end_s": 0.2,
            }],
            "renderer_events": [],
        }

        result = compare_synthetic_truth(actual, truth)

        self.assertEqual(result["status"], "fail")

    def test_blessing_then_rerunning_a_software_snapshot_passes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot_dir = Path(temp_dir) / "snapshots"
            snapshot = snapshot_dir / "contract.json"
            actual = {"schema_version": "test", "value": [1, 2, 3]}

            bless_snapshot(actual, snapshot, snapshot_dir)
            result = compare_snapshot(actual, snapshot)

            self.assertEqual(result["status"], "pass")

    def test_changed_protected_threshold_has_a_clear_diff(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            altered = Path(temp_dir) / "merge.py"
            source = (REPO_ROOT / "pipeline" / "merge.py").read_text(
                encoding="utf-8"
            )
            altered.write_text(
                source.replace("DRAG_RATIO = 2.6", "DRAG_RATIO = 9.9", 1),
                encoding="utf-8",
            )

            expected = {"protected_renderer_thresholds": protected_thresholds()}
            actual = {
                "protected_renderer_thresholds": protected_thresholds(altered)
            }
            differences = structural_diff(expected, actual)

            self.assertTrue(any(
                "DRAG_RATIO" in item and "expected 2.6, actual 9.9" in item
                for item in differences
            ))

    def test_bless_cannot_silently_replace_a_wrong_human_label(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            truth = json.loads(
                (REPO_ROOT / "regression" / "truth" / "fixture_conversation.json")
                .read_text(encoding="utf-8")
            )
            truth["expectations"]["artifact_checks"][0]["value"] = "solo"
            truth_path = root / "truth" / "wrong.json"
            truth_path.parent.mkdir()
            truth_path.write_text(json.dumps(truth), encoding="utf-8")
            before = truth_path.read_bytes()

            artifacts = root / "artifacts"
            artifacts.mkdir()
            (artifacts / "master.json").write_text(json.dumps({
                "meta": {
                    "recording_type": "conversation",
                    "num_speakers": 2,
                    "audio_duration_s": 123.89,
                }
            }), encoding="utf-8")
            (artifacts / "audio_quality.json").write_text(json.dumps({
                "audio": {
                    "byte_sha256": truth["audio"]["sha256"],
                }
            }), encoding="utf-8")
            result = compare_recording_truth(artifacts, load_truth(truth_path))

            snapshot_dir = root / "snapshots"
            bless_snapshot({"current": True}, snapshot_dir / "new.json",
                           snapshot_dir)

            self.assertEqual(result["status"], "fail")
            self.assertEqual(truth_path.read_bytes(), before)

    def test_synthetic_harness_is_isolated_and_reports_denominators(self):
        before = protected_file_hashes()
        with tempfile.TemporaryDirectory() as temp_dir:
            report = run_harness(
                synthetic_only=True,
                report_dir=Path(temp_dir) / "report",
            )

        self.assertEqual(report["status"], "pass")
        self.assertEqual(before, protected_file_hashes())
        self.assertEqual(report["software_snapshot"]["status"], "pass")
        synthetic = next(
            item for item in report["truth_results"]
            if item["fixture_id"] == "synthetic_controls"
        )
        for metric in synthetic["metrics"].values():
            self.assertIn("denominator", metric)
            self.assertIn("reference_source", metric)

    def test_committed_snapshot_matches_current_deterministic_contract(self):
        self.assertTrue(SNAPSHOT_PATH.is_file())


if __name__ == "__main__":
    unittest.main()
