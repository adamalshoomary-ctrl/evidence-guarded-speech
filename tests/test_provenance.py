import json
import os
import tempfile
import unittest
import wave
from pathlib import Path

from pipeline.provenance import (
    build_initial_provenance,
    sync_provenance_to_master,
)
from pipeline.run_context import create_manifest, update_manifest


def write_silent_wav(path, *, frames=8000, sample_rate=8000):
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(b"\0\0" * frames)


class ProvenanceTests(unittest.TestCase):
    def test_repeated_capture_has_the_same_input_hash_and_configuration(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            audio = root / "sample.wav"
            write_silent_wav(audio)
            configuration = {
                "speakers_expected": 2,
                "history_speaker_label": None,
                "isolated_output": True,
            }
            os.environ["GEMINI_API_KEY"] = "must_not_appear_in_provenance"

            first = build_initial_provenance(
                root, audio, "first", configuration, "2026-01-01T00:00:00.000Z"
            )
            second = build_initial_provenance(
                root, audio, "second", configuration, "2026-01-01T00:00:01.000Z"
            )

            self.assertEqual(
                first["input_audio"]["byte_sha256"],
                second["input_audio"]["byte_sha256"],
            )
            self.assertEqual(
                first["run"]["configuration"], second["run"]["configuration"]
            )
            self.assertEqual(first["input_audio"]["codec"], "pcm_s16le")
            self.assertEqual(first["input_audio"]["sample_rate_hz"], 8000)
            self.assertEqual(first["input_audio"]["channels"], 1)
            self.assertNotIn(
                "must_not_appear_in_provenance", json.dumps(first)
            )

    def test_manifest_models_and_stage_runtime_are_copied_into_master(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            audio = root / "sample.wav"
            write_silent_wav(audio)
            output = root / "output"
            provenance = build_initial_provenance(
                root,
                audio,
                "test_run",
                {"speakers_expected": 2},
                "2026-01-01T00:00:00.000Z",
            )
            manifest_path = create_manifest(
                output,
                "test_run",
                audio,
                ["transcript.json", "alignment.json", "master.json"],
                provenance=provenance,
            )
            (output / "transcript.json").write_text(
                json.dumps({"speech_model_used": "universal-3-5-pro"}),
                encoding="utf-8",
            )
            (output / "alignment.json").write_text(
                json.dumps({
                    "model_provenance": {
                        "language": "en",
                        "alignment_model_id": "WAV2VEC2_ASR_BASE_960H",
                        "alignment_model_version_policy": "package_pinned",
                    }
                }),
                encoding="utf-8",
            )
            (output / "master.json").write_text(
                json.dumps({"meta": {}}), encoding="utf-8"
            )
            update_manifest(
                manifest_path,
                stage="Verbatim transcript",
                stage_status="complete",
                duration_s=3.25,
                completed_outputs=[
                    "transcript.json", "alignment.json", "master.json"
                ],
                stage_script="transcribe.py",
                stage_arguments=["--speakers", "2"],
                stage_started_at_utc="2026-01-01T00:00:01.000Z",
                stage_completed_at_utc="2026-01-01T00:00:04.250Z",
            )

            sync_provenance_to_master(manifest_path)

            master = json.loads((output / "master.json").read_text())
            stored = master["meta"]["provenance"]
            self.assertEqual(
                stored["models"]["transcription"]["actual_model_id"],
                "universal-3-5-pro",
            )
            self.assertEqual(
                stored["models"]["alignment_timing"]["actual_model_id"],
                "WAV2VEC2_ASR_BASE_960H",
            )
            self.assertEqual(
                stored["stages"]["Verbatim transcript"]["duration_s"], 3.25
            )
            self.assertEqual(
                stored["stages"]["Verbatim transcript"]["status"], "complete"
            )


if __name__ == "__main__":
    unittest.main()
