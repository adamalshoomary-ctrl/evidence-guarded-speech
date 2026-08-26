import copy
import math
import unittest
from pathlib import Path

import numpy as np

from pipeline.acoustic_primitives import (
    FRAME_STEP_S,
    PRIMITIVE_NAMES,
    analysis_context,
    extract_voice_prosody,
)
from voice_prosody.contract import load_contract, validate_contract


REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_RATE = 48000


def clean_quality():
    return {
        "decision": "continue",
        "overall_status": "pass",
        "checks": [],
        "limitations": [],
    }


def default_context(profile="unknown_ad_hoc", *, consent=False):
    contract = load_contract()
    task_ids = contract["task_profiles"][profile]["task_ids"]
    return {
        "status": "declared" if task_ids else "context_missing",
        "task_id": task_ids[0] if task_ids else None,
        "task_version": "1.0.0" if task_ids else None,
        "prompt_id": "prompt_test" if task_ids else None,
        "prompt_version": "1.0.0" if task_ids else None,
        "language": "en" if task_ids else None,
        "preparation": None,
        "accommodations": [],
        "task_profile": profile,
        "task_comparability": contract["task_profiles"][profile]["comparability"],
        "supported_primitives": contract["task_profiles"][profile]["supports"],
        "requires_research_consent": bool(
            contract["task_profiles"][profile].get("requires_research_consent")
        ),
        "research_consent_granted": consent,
        "device": {
            "device_class": "phone",
            "platform": "test",
            "microphone": "built_in",
            "source": "user_declared",
        },
        "quality_policy": "baseline",
        "capture_processing": {
            "automatic_gain_control": "unknown",
            "noise_suppression": "unknown",
            "echo_cancellation": "unknown",
        },
    }


def tone(frequency, seconds=4.0, amplitude=0.2):
    time = np.arange(int(seconds * SAMPLE_RATE)) / SAMPLE_RATE
    return amplitude * np.sin(2 * np.pi * frequency * time)


def one_region(seconds, speaker="SPEAKER_00"):
    return {
        "turns": [{
            "speaker": speaker,
            "start_s": 0.0,
            "end_s": seconds,
            "duration_s": seconds,
        }]
    }


def extract(samples, diarization=None, *, context=None, vad=None,
            quality=None, recording_type="solo"):
    seconds = len(samples) / SAMPLE_RATE
    return extract_voice_prosody(
        samples,
        SAMPLE_RATE,
        diarization or one_region(seconds),
        vad or {"speech_chunks": [{"start": 0.0, "end": seconds}]},
        context or default_context(),
        quality or clean_quality(),
        recording_type,
        {"codec": "pcm_s16le", "sample_rate_hz": SAMPLE_RATE, "channels": 1},
    )


class VoiceProsodyContractTests(unittest.TestCase):
    def test_committed_contract_is_valid_and_keeps_all_dangerous_uses_locked(self):
        contract = load_contract()
        self.assertEqual(validate_contract(contract), [])
        self.assertFalse(
            contract["claim_boundaries"]["combined_voice_or_prosody_index_allowed"]
        )
        self.assertEqual(contract["release_limits"]["screening"], "blocked")
        self.assertEqual(contract["release_limits"]["personal_progress"], "blocked")

    def test_validator_rejects_combined_index_and_connected_speech_jitter(self):
        contract = load_contract()
        changed = copy.deepcopy(contract)
        changed["claim_boundaries"][
            "combined_voice_or_prosody_index_allowed"
        ] = True
        changed["task_profiles"]["spontaneous_speech"]["supports"].append(
            "jitter_local_pct"
        )
        errors = validate_contract(changed)
        self.assertTrue(any("combined" in error for error in errors))
        self.assertTrue(any("sustained vowel research only" in error
                            for error in errors))

    def test_validator_rejects_unknown_task_primitive_and_incomplete_frames(self):
        contract = load_contract()
        changed = copy.deepcopy(contract)
        changed["task_profiles"]["fixed_reading"]["supports"].append(
            "invented_voice_score"
        )
        changed["frame_contract"]["required_fields"].remove("region_id")
        errors = validate_contract(changed)
        self.assertTrue(any("unknown primitives" in error for error in errors))
        self.assertTrue(any("required fields" in error for error in errors))

    def test_context_free_run_is_explicitly_noncomparable(self):
        context = analysis_context(None, "solo", REPO_ROOT)
        self.assertEqual(context["task_profile"], "unknown_ad_hoc")
        self.assertEqual(context["task_comparability"], "not_comparable")
        self.assertEqual(context["device"]["source"], "not_declared")


class AcousticPrimitiveTests(unittest.TestCase):
    def test_known_steady_frequencies_are_recovered_without_identity_assumptions(self):
        for frequency in (90.0, 180.0, 420.0):
            with self.subTest(frequency=frequency):
                artifact = extract(tone(frequency))
                summary = artifact["speakers"]["SPEAKER_00"]
                self.assertAlmostEqual(
                    summary["values"]["f0_median_hz"], frequency, delta=0.6
                )
                self.assertEqual(
                    summary["availability"]["f0_median_hz"]["status"],
                    "available",
                )

    def test_pitch_glide_produces_ordered_robust_distribution_not_a_score(self):
        seconds = 5.0
        time = np.arange(int(seconds * SAMPLE_RATE)) / SAMPLE_RATE
        start_hz, end_hz = 120.0, 240.0
        rate = (end_hz - start_hz) / seconds
        phase = 2 * np.pi * (start_hz * time + 0.5 * rate * time ** 2)
        artifact = extract(0.2 * np.sin(phase))
        values = artifact["speakers"]["SPEAKER_00"]["values"]
        self.assertLess(values["f0_p05_hz"], values["f0_median_hz"])
        self.assertLess(values["f0_median_hz"], values["f0_p95_hz"])
        self.assertGreater(values["f0_distribution_span_st"], 8.0)
        self.assertNotIn("prosody_score", values)

    def test_recorder_level_is_dbfs_and_gain_change_is_visible(self):
        first = tone(180.0, seconds=2.5, amplitude=0.05)
        second = tone(180.0, seconds=2.5, amplitude=0.2)
        artifact = extract(np.concatenate([first, second]))
        summary = artifact["speakers"]["SPEAKER_00"]
        self.assertGreater(summary["values"]["recorder_level_span_db"], 10.0)
        self.assertLess(summary["values"]["recorder_level_median_dbfs"], 0.0)
        self.assertFalse(
            artifact["configuration"]["recorder_level_is_sound_pressure_level"]
        )

    def test_unvoiced_pitch_is_null_never_zero(self):
        samples = np.concatenate([tone(180.0, seconds=2.0),
                                  np.zeros(SAMPLE_RATE * 2)])
        artifact = extract(samples)
        unvoiced = [frame for frame in artifact["frames"] if not frame["voiced"]]
        self.assertTrue(unvoiced)
        self.assertTrue(all(frame["f0_hz"] is None for frame in unvoiced))

    def test_separated_regions_never_create_a_pitch_jump_across_the_join(self):
        samples = np.concatenate([
            tone(100.0, seconds=2.0),
            np.zeros(SAMPLE_RATE),
            tone(300.0, seconds=2.0),
        ])
        diarization = {"turns": [
            {"speaker": "SPEAKER_00", "start_s": 0.0, "end_s": 2.0,
             "duration_s": 2.0},
            {"speaker": "SPEAKER_00", "start_s": 3.0, "end_s": 5.0,
             "duration_s": 2.0},
        ]}
        artifact = extract(samples, diarization)
        summary = artifact["speakers"]["SPEAKER_00"]
        self.assertEqual(summary["sample"]["continuous_region_count"], 2)
        self.assertEqual(
            summary["diagnostics"]["suspected_octave_jump_count"], 0
        )

    def test_overlap_frames_are_excluded_from_both_speaker_summaries(self):
        samples = tone(180.0, seconds=4.0)
        diarization = {"turns": [
            {"speaker": "SPEAKER_00", "start_s": 0.0, "end_s": 3.0,
             "duration_s": 3.0},
            {"speaker": "SPEAKER_01", "start_s": 2.0, "end_s": 4.0,
             "duration_s": 2.0},
        ]}
        artifact = extract(
            samples, diarization, recording_type="conversation",
            context=default_context("conversation"),
        )
        self.assertGreater(artifact["overlap_excluded_frame_count"], 0)
        overlap_frames = [
            frame for frame in artifact["frames"]
            if "overlap" in frame["quality_flags"]
        ]
        self.assertTrue(all(frame["speaker"] is None for frame in overlap_frames))
        self.assertTrue(all(frame["f0_hz"] is None for frame in overlap_frames))
        self.assertEqual(
            artifact["whole_recording_person_level_use"],
            "unavailable_blended_speakers",
        )

    def test_pitch_frames_near_region_edges_are_not_attributed(self):
        artifact = extract(tone(180.0, seconds=4.0))
        edge_frames = [
            frame for frame in artifact["frames"]
            if "region_edge_excluded" in frame["quality_flags"]
        ]
        self.assertTrue(edge_frames)
        self.assertTrue(all(frame["speaker"] is None for frame in edge_frames))

    def test_adaptive_second_pass_rejects_a_distant_false_pitch_cluster(self):
        samples = np.concatenate([
            tone(150.0, seconds=4.5),
            tone(600.0, seconds=0.5),
        ])
        artifact = extract(samples)
        summary = artifact["speakers"]["SPEAKER_00"]
        pitch_range = artifact["configuration"]["pitch_ranges_by_speaker"][
            "SPEAKER_00"
        ]
        self.assertLess(pitch_range["adaptive_ceiling_hz"], 600.0)
        self.assertAlmostEqual(summary["values"]["f0_median_hz"], 150.0,
                               delta=0.6)
        self.assertIsNone(summary["values"]["f0_p95_hz"])
        self.assertEqual(
            summary["availability"]["f0_percentiles_hz"]["reason"],
            "possible_octave_error_cluster",
        )

    def test_audio_warning_limits_only_dependent_primitives(self):
        quality = clean_quality()
        quality["overall_status"] = "warn"
        quality["checks"] = [{
            "id": "signal_to_noise_proxy",
            "status": "warn",
            "reason": "Synthetic noise limitation.",
            "affects": ["pitch", "voice_quality"],
        }]
        artifact = extract(tone(180.0), quality=quality)
        state = artifact["speakers"]["SPEAKER_00"]["availability"]
        self.assertEqual(state["f0_median_hz"]["quality"], "low")
        self.assertEqual(
            state["recorder_level_percentiles_dbfs"]["quality"], "high"
        )

    def test_research_voice_measures_respect_audio_quality_failure(self):
        quality = clean_quality()
        quality["overall_status"] = "fail"
        quality["checks"] = [{
            "id": "digital_clipping",
            "status": "fail",
            "reason": "Synthetic clipping invalidates voice quality.",
            "affects": ["pitch", "voice_quality", "loudness"],
        }]
        fixed = extract(
            tone(180.0, seconds=6.0),
            context=default_context("fixed_reading"),
            quality=quality,
        )
        self.assertEqual(
            fixed["speakers"]["SPEAKER_00"]["availability"]["cpps_db"]["reason"],
            "audio_quality_failure",
        )
        vowel = extract(
            tone(180.0, seconds=12.0),
            context=default_context("sustained_vowel_research", consent=True),
            quality=quality,
        )
        for name in ("cpps_db", "jitter_local_pct", "shimmer_local_pct"):
            self.assertEqual(
                vowel["speakers"]["SPEAKER_00"]["availability"][name]["reason"],
                "audio_quality_failure",
            )

    def test_sustained_vowel_research_requires_explicit_consent(self):
        samples = tone(180.0, seconds=12.0)
        artifact = extract(
            samples,
            context=default_context("sustained_vowel_research", consent=False),
        )
        summary = artifact["speakers"]["SPEAKER_00"]
        for name in ("cpps_db", "jitter_local_pct", "shimmer_local_pct"):
            self.assertEqual(summary["availability"][name]["status"],
                             "unavailable")
            self.assertEqual(summary["availability"][name]["reason"],
                             "research_consent_not_granted")

    def test_three_vowel_repetitions_are_analysed_independently(self):
        gap = np.zeros(SAMPLE_RATE)
        vowel = tone(180.0, seconds=3.5)
        samples = np.concatenate([vowel, gap, vowel, gap, vowel])
        chunks = [
            {"start": 0.0, "end": 3.5},
            {"start": 4.5, "end": 8.0},
            {"start": 9.0, "end": 12.5},
        ]
        artifact = extract(
            samples,
            vad={"speech_chunks": chunks},
            context=default_context("sustained_vowel_research", consent=True),
        )
        summary = artifact["speakers"]["SPEAKER_00"]
        self.assertEqual(len(summary["research_trials"]), 3)
        self.assertTrue(all(trial["status"] == "valid"
                            for trial in summary["research_trials"]))
        self.assertEqual(summary["availability"]["jitter_local_pct"]["status"],
                         "available")
        self.assertEqual(summary["availability"]["shimmer_local_pct"]["status"],
                         "available")

    def test_frame_contract_is_complete_and_timestamps_are_monotonic(self):
        artifact = extract(tone(180.0))
        frames = artifact["frames"]
        required = set(load_contract()["frame_contract"]["required_fields"])
        self.assertTrue(all(required.issubset(frame) for frame in frames))
        times = [frame["time_s"] for frame in frames]
        self.assertEqual(times, sorted(times))
        self.assertAlmostEqual(times[1] - times[0], FRAME_STEP_S, places=3)
        values = artifact["speakers"]["SPEAKER_00"]["values"]
        self.assertEqual(set(values), set(PRIMITIVE_NAMES))


if __name__ == "__main__":
    unittest.main()
