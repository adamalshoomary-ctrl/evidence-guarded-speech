import json
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np

from pipeline.audio_quality import analyze_audio


SAMPLE_RATE = 16000
REPO_ROOT = Path(__file__).resolve().parent.parent


def write_wav(path, samples, sample_rate=SAMPLE_RATE):
    samples = np.asarray(samples, dtype=np.float64)
    pcm = np.round(np.clip(samples, -1.0, 1.0) * 32767).astype("<i2")
    channels = 1 if pcm.ndim == 1 else pcm.shape[1]
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(pcm.tobytes())


def speech_bursts(*, seconds=10.0, amplitude=0.2):
    count = int(seconds * SAMPLE_RATE)
    time = np.arange(count) / SAMPLE_RATE
    tone = amplitude * np.sin(2 * np.pi * 180 * time)
    envelope = np.zeros(count)
    for start_s in (0.5, 2.5, 4.5, 6.5, 8.5):
        start = int(start_s * SAMPLE_RATE)
        end = min(count, start + int(1.2 * SAMPLE_RATE))
        envelope[start:end] = 1.0
    return tone * envelope


def by_id(report):
    return {item["id"]: item for item in report["checks"]}


class AudioQualityTests(unittest.TestCase):
    def test_generated_clean_audio_passes_both_policies(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            audio = Path(temp_dir) / "clean.wav"
            write_wav(audio, speech_bursts())

            lenient = analyze_audio(audio, "lenient")
            baseline = analyze_audio(audio, "baseline")

            self.assertEqual(lenient["decision"], "continue")
            self.assertEqual(lenient["overall_status"], "pass")
            self.assertEqual(baseline["decision"], "continue")
            self.assertEqual(baseline["overall_status"], "pass")
            self.assertTrue(lenient["analysis"]["full_file_analysed"])

    def test_clipping_warns_when_lenient_and_rejects_baseline(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            audio = Path(temp_dir) / "clipped.wav"
            clipped = np.sign(speech_bursts(amplitude=1.0))
            write_wav(audio, clipped)

            lenient = analyze_audio(audio, "lenient")
            baseline = analyze_audio(audio, "baseline")

            self.assertEqual(lenient["decision"], "continue")
            self.assertEqual(by_id(lenient)["clipping"]["status"], "warn")
            self.assertEqual(baseline["decision"], "reject")
            self.assertEqual(by_id(baseline)["clipping"]["status"], "fail")

    def test_near_silent_audio_is_rejected_for_both_policies(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            audio = Path(temp_dir) / "silent.wav"
            write_wav(audio, np.zeros(SAMPLE_RATE * 8))

            for policy in ("lenient", "baseline"):
                report = analyze_audio(audio, policy)
                self.assertEqual(report["decision"], "reject")
                self.assertEqual(
                    by_id(report)["rms_and_near_silence"]["status"], "fail"
                )

    def test_quiet_but_nonempty_audio_warns_when_lenient_and_rejects_baseline(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            audio = Path(temp_dir) / "quiet.wav"
            write_wav(audio, speech_bursts(amplitude=0.005))

            lenient = analyze_audio(audio, "lenient")
            baseline = analyze_audio(audio, "baseline")

            self.assertEqual(lenient["decision"], "continue")
            self.assertEqual(by_id(lenient)["peak_level"]["status"], "warn")
            self.assertEqual(baseline["decision"], "reject")
            self.assertEqual(by_id(baseline)["peak_level"]["status"], "fail")

    def test_unreadable_audio_returns_a_structured_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            audio = Path(temp_dir) / "broken.wav"
            audio.write_bytes(b"this is not audio")

            report = analyze_audio(audio)

            self.assertEqual(report["decision"], "reject")
            self.assertEqual(by_id(report)["file_readability"]["status"],
                             "fail")
            self.assertEqual(report["audio"]["filename"], "broken.wav")
            self.assertIsNotNone(report["audio"]["byte_sha256"])

    def test_stereo_is_handled_without_hiding_source_channel_count(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            audio = Path(temp_dir) / "stereo.wav"
            clean = speech_bursts()
            write_wav(audio, np.column_stack([clean, clean * 0.8]))

            report = analyze_audio(audio, "baseline")

            self.assertEqual(report["decision"], "continue")
            self.assertEqual(report["audio"]["channels"], 2)
            self.assertEqual(report["analysis"]["decoded_channels"], 2)
            self.assertEqual(by_id(report)["channel_handling"]["status"],
                             "pass")

    def test_generated_noise_warns_when_lenient_and_rejects_baseline(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            audio = Path(temp_dir) / "noisy.wav"
            rng = np.random.default_rng(7)
            noisy = speech_bursts(amplitude=0.03)
            noisy += rng.normal(0.0, 0.08, size=noisy.shape)
            write_wav(audio, noisy)

            lenient = analyze_audio(audio, "lenient")
            baseline = analyze_audio(audio, "baseline")

            self.assertEqual(lenient["decision"], "continue")
            self.assertEqual(
                by_id(lenient)["signal_to_noise_proxy"]["status"], "warn"
            )
            self.assertEqual(baseline["decision"], "reject")
            self.assertEqual(
                by_id(baseline)["signal_to_noise_proxy"]["status"], "fail"
            )

    def test_generated_short_and_long_inputs_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            short = root / "short.wav"
            write_wav(short, speech_bursts(seconds=2.0))
            self.assertEqual(analyze_audio(short)["decision"], "reject")
            self.assertEqual(by_id(analyze_audio(short))["duration"]["status"],
                             "fail")

            long_audio = root / "long.wav"
            with wave.open(str(long_audio), "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(1000)
                handle.writeframes(b"\0\0" * 1_801_000)
            long_report = analyze_audio(long_audio)
            self.assertEqual(long_report["decision"], "reject")
            self.assertIn("--long-ok", by_id(long_report)["duration"]["reason"])
            approved = analyze_audio(long_audio, long_ok=True)
            self.assertEqual(by_id(approved)["duration"]["status"], "warn")
            self.assertNotIn("requires explicit",
                             by_id(approved)["duration"]["reason"])

    def test_report_checks_keep_the_auditable_contract(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            audio = Path(temp_dir) / "clean.wav"
            write_wav(audio, speech_bursts())
            report = analyze_audio(audio)

            self.assertEqual(report["schema_version"], "1.0.0")
            self.assertEqual(report["audio"]["sample_rate_hz"], SAMPLE_RATE)
            self.assertEqual(by_id(report)["codec_support"]["status"], "pass")
            self.assertTrue(report["limitations"])
            for item in report["checks"]:
                self.assertTrue({
                    "id", "status", "value", "threshold",
                    "threshold_version", "reason", "affects",
                }.issubset(item))
                self.assertIn(item["status"], {"pass", "warn", "fail"})

    def test_runner_rejects_before_remote_stages_and_records_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            audio = root / "short.wav"
            output = root / "output"
            write_wav(audio, speech_bursts(seconds=2.0))

            result = subprocess.run(
                [
                    sys.executable, "pipeline/run_all.py",
                    "--mode", "solo", "--audio", str(audio),
                    "--output-dir", str(output), "--run-id", "quality_test",
                ],
                cwd=REPO_ROOT, capture_output=True, text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("audio quality preflight rejected", result.stderr)
            self.assertTrue((output / "audio_quality.json").is_file())
            manifest = json.loads(
                (output / "run_manifest.json").read_text(encoding="utf-8")
            )
            stage = manifest["stages"]["Audio quality preflight"]
            self.assertEqual(stage["status"], "failed")
            self.assertEqual(manifest["status"], "failed")
            self.assertIn("audio_quality.json", manifest["completed_outputs"])
            self.assertNotIn("transcript.json", manifest["completed_outputs"])


if __name__ == "__main__":
    unittest.main()
