import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pipeline.measurement_evidence import (
    ASR_CONFIDENCE_THRESHOLD,
    METRIC_DEFINITIONS,
    build_measurement_metadata,
)


REPO_ROOT = Path(__file__).resolve().parent.parent


def computed_metrics(*, words=60, talk_time=30.0):
    return {
        "talk_time_s": talk_time,
        "talk_share_pct": 50.0,
        "words": words,
        "wpm": round(words / (talk_time / 60), 1),
        "filled_pause_count": 1,
        "filled_pauses_per_min": 2.0,
        "lengthened_word_count": 1,
        "level_above_median_word_count": 1,
        "final_rise_count": 1,
        "final_rises_per_min": 2.0,
        "backchannels_given": 1,
        "mean_pause_before_turn_s": 0.8,
        "listed_phrase_counts": {"maybe": 1},
        "question_count": 1,
        "question_ratio": 0.25,
        "pronoun_counts": {"i_me_my": 2, "you_your": 2, "ratio": 1.0},
        "repetition_count": 0,
        "repetitions_per_min": 0.0,
        "type_token_ratio": 0.7,
    }


def words_for(count, *, low_asr=False):
    return [
        {
            "text": f"word{index}",
            "final_speaker": "SPEAKER_00",
            "speaker_confidence": "high",
            "confidence": 0.4 if low_asr and index == 0 else 0.99,
        }
        for index in range(count)
    ]


def turns_for(count):
    return [{"speaker": "SPEAKER_00"} for _ in range(count)]


def acoustics_fixture():
    voice = {
        "pitch_median_hz": 180.0,
        "pitch_variation_hz": 25.0,
        "jitter": 0.01,
        "shimmer": 0.03,
        "speech_analysed_s": 20.0,
    }
    values = {
        "f0_median_hz": 180.0,
        "f0_p05_hz": 150.0,
        "f0_p25_hz": 170.0,
        "f0_p75_hz": 195.0,
        "f0_p95_hz": 220.0,
        "f0_distribution_span_st": 6.63,
        "recorder_level_p05_dbfs": -30.0,
        "recorder_level_p25_dbfs": -24.0,
        "recorder_level_median_dbfs": -20.0,
        "recorder_level_p75_dbfs": -17.0,
        "recorder_level_p95_dbfs": -14.0,
        "recorder_level_span_db": 16.0,
        "cpps_db": None,
        "jitter_local_pct": None,
        "shimmer_local_pct": None,
    }
    available = {"status": "available", "reason": None,
                 "quality": "high", "warnings": []}
    unavailable = {"status": "unavailable", "reason": "research_only",
                   "quality": "unavailable", "warnings": []}
    return {
        "overall": {**voice, "duration_s": 30.0},
        "per_speaker": {"SPEAKER_00": voice},
        "timeline": [{"t": index, "loudness_db": -10, "pitch_hz": 180}
                     for index in range(10)],
        "pitch_track": [[index, 180] for index in range(10)],
        "voice_prosody": {"speakers": {"SPEAKER_00": {
            "task_id": "standard_reading_en_v1",
            "task_version": "1.0.0",
            "task_profile": "fixed_reading",
            "task_comparability": "same_task_only",
            "sample": {"voiced_frame_count": 200, "voiced_s": 2.0},
            "values": values,
            "availability": {
                "f0_median_hz": available,
                "f0_percentiles_hz": available,
                "f0_distribution_span_st": available,
                "recorder_level_percentiles_dbfs": available,
                "recorder_level_span_db": available,
                "cpps_db": unavailable,
                "jitter_local_pct": unavailable,
                "shimmer_local_pct": unavailable,
            },
        }}},
    }


def clean_quality():
    return {
        "decision": "continue",
        "overall_status": "pass",
        "checks": [],
        "limitations": [],
    }


class MeasurementEvidenceTests(unittest.TestCase):
    def test_every_computed_metric_has_the_full_evidence_contract(self):
        metrics = computed_metrics()
        metadata = build_measurement_metadata(
            {"SPEAKER_00": metrics}, words_for(60), turns_for(4),
            acoustics_fixture(), clean_quality(), "conversation",
            pitch_observation_counts={"SPEAKER_00": 10},
        )

        entries = metadata["speakers"]["SPEAKER_00"]["computed_metrics"]
        self.assertEqual(set(entries), set(METRIC_DEFINITIONS))
        for name, entry in entries.items():
            self.assertTrue({
                "construct", "unit", "source", "requirements",
                "availability", "quality", "sample", "warnings",
                "known_confounders", "algorithm_version", "threshold_version",
            }.issubset(entry))
            self.assertEqual(entry["value_path"],
                             f"computed_metrics.SPEAKER_00.{name}")
        self.assertEqual(metadata["schema_version"], "2.0.0")
        prosody = metadata["speakers"]["SPEAKER_00"]["voice_prosody"]
        self.assertEqual(prosody["f0_median_hz"]["availability"]["status"],
                         "available")
        self.assertEqual(prosody["cpps_db"]["availability"]["status"],
                         "unavailable")
        self.assertEqual(
            prosody["recorder_level_median_dbfs"]["unit"], "dBFS"
        )
        self.assertEqual(
            prosody["cpps_db"]["validation"]["reliability"]
            ["prespecified_analysis"]["error_unit"],
            "decibels",
        )
        self.assertEqual(
            prosody["jitter_local_pct"]["validation"]["reliability"]
            ["prespecified_analysis"]["error_unit"],
            "percent",
        )

    def test_short_sample_marks_precise_legacy_rate_unavailable(self):
        metrics = computed_metrics(words=5, talk_time=3.0)
        metadata = build_measurement_metadata(
            {"SPEAKER_00": metrics}, words_for(5), turns_for(1),
            acoustics_fixture(), clean_quality(), "solo",
        )
        evidence = (metadata["speakers"]["SPEAKER_00"]
                    ["computed_metrics"]["wpm"])

        self.assertEqual(metrics["wpm"], 100.0)
        self.assertEqual(evidence["availability"]["status"], "unavailable")
        self.assertEqual(evidence["availability"]["reason"],
                         "insufficient_sample")
        self.assertEqual(evidence["quality"]["category"], "unavailable")

    def test_new_metric_cannot_exist_without_an_evidence_definition(self):
        metrics = computed_metrics()
        metrics["mystery_score"] = 99

        with self.assertRaisesRegex(ValueError, "mystery_score"):
            build_measurement_metadata(
                {"SPEAKER_00": metrics}, words_for(60), turns_for(4),
                acoustics_fixture(), clean_quality(), "conversation",
            )

    def test_every_measurement_exposes_reliability_and_fairness_limits(self):
        metadata = build_measurement_metadata(
            {"SPEAKER_00": computed_metrics()}, words_for(60), turns_for(4),
            acoustics_fixture(), clean_quality(), "conversation",
            pitch_observation_counts={"SPEAKER_00": 10},
        )

        entries = metadata["speakers"]["SPEAKER_00"]["computed_metrics"]
        for evidence in entries.values():
            validation = evidence["validation"]
            self.assertEqual(validation["reliability"]["status"],
                             "experimental")
            # Item F7 replaced every progress field with one limit on
            # claims of change over time.
            for removed in ("progress_use", "minimum_baseline_observations",
                            "personal_progress_contract_version"):
                self.assertNotIn(removed, validation["reliability"])
            self.assertNotIn("individual_progress",
                             validation["release_limits"])
            self.assertEqual(
                validation["release_limits"]["change_over_time"], "blocked"
            )
            self.assertEqual(
                validation["reliability"]["natural_variation_status"],
                "not_established",
            )
            self.assertEqual(
                validation["reliability"]["meaningful_change_status"],
                "not_established",
            )
            self.assertEqual(validation["fairness"]["status"],
                             "not_evaluated")
            self.assertEqual(validation["release_limits"]["screening"],
                             "blocked")

    def test_audio_warning_only_limits_dependent_measurements(self):
        quality = clean_quality()
        quality["overall_status"] = "warn"
        quality["checks"] = [{
            "id": "speech_proportion", "status": "warn",
            "reason": "Very little speech-like energy was detected.",
            "affects": ["language", "rate"],
        }]
        metadata = build_measurement_metadata(
            {"SPEAKER_00": computed_metrics()}, words_for(60), turns_for(4),
            acoustics_fixture(), quality, "conversation",
            pitch_observation_counts={"SPEAKER_00": 10},
        )
        entries = metadata["speakers"]["SPEAKER_00"]["computed_metrics"]

        self.assertEqual(
            entries["listed_phrase_counts"]["quality"]["category"], "low"
        )
        self.assertEqual(
            entries["level_above_median_word_count"]["quality"]["category"],
            "high",
        )

    def test_low_asr_confidence_is_separate_transcription_uncertainty(self):
        metadata = build_measurement_metadata(
            {"SPEAKER_00": computed_metrics()}, words_for(60, low_asr=True),
            turns_for(4), acoustics_fixture(), clean_quality(), "conversation",
            pitch_observation_counts={"SPEAKER_00": 10},
        )
        evidence = (metadata["speakers"]["SPEAKER_00"]
                    ["computed_metrics"]["listed_phrase_counts"])

        self.assertEqual(metadata["asr_confidence"]["low_below"],
                         ASR_CONFIDENCE_THRESHOLD)
        self.assertIn("transcription_uncertainty",
                      {warning["category"] for warning in evidence["warnings"]})
        self.assertEqual(evidence["quality"]["category"], "moderate")

    def test_uncertainty_categories_remain_distinct(self):
        uncertain_words = words_for(60)
        uncertain_words[0]["speaker_confidence"] = "low-overlap"
        failed_quality = clean_quality()
        failed_quality["decision"] = "reject"
        failed_quality["overall_status"] = "fail"
        failed_quality["checks"] = [{
            "id": "decoded_audio", "status": "fail",
            "reason": "Audio could not be decoded.",
            "affects": ["all_measurements"],
        }]
        metadata = build_measurement_metadata(
            {"SPEAKER_00": computed_metrics()}, uncertain_words, turns_for(4),
            {"overall": {"duration_s": 30.0}, "per_speaker": {},
             "timeline": [], "pitch_track": []},
            failed_quality, "conversation",
            pitch_observation_counts={"SPEAKER_00": 10},
        )
        speaker = metadata["speakers"]["SPEAKER_00"]
        metric_categories = {
            warning["category"]
            for warning in speaker["computed_metrics"]["wpm"]["warnings"]
        }
        voice_categories = {
            warning["category"]
            for warning in speaker["voice_quality"]["jitter"]["warnings"]
        }

        self.assertIn("speaker_uncertainty", metric_categories)
        self.assertIn("audio_quality_failure", metric_categories)
        self.assertIn("acoustic_uncertainty", voice_categories)
        self.assertEqual(
            speaker["computed_metrics"]["wpm"]["availability"]["reason"],
            "audio_quality_failure",
        )

    def test_merge_exposes_low_asr_word_and_measurement_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir)
            transcript_words = [
                {"text": "hello", "start": 0, "end": 500,
                 "confidence": 0.99},
                {"text": "uncertain", "start": 600, "end": 1200,
                 "confidence": 0.4},
                {"text": "world.", "start": 1300, "end": 1900,
                 "confidence": 0.98},
            ]
            fixtures = {
                "diarization.json": {
                    "turns": [{"speaker": "SPEAKER_00", "start_s": 0.0,
                               "end_s": 2.0, "duration_s": 2.0}],
                    "account_holder_speaker": "SPEAKER_00",
                    "contamination": {"status": "clear", "warning": None},
                },
                "transcript.json": {"words": transcript_words},
                "vad.json": {
                    "audio_duration_s": 2.0, "speaking_time_s": 2.0,
                    "silence_time_s": 0.0,
                    "speech_chunks": [{"start": 0.0, "end": 2.0}],
                    "pauses": [],
                },
                "acoustics.json": {
                    "overall": {"duration_s": 2.0},
                    "per_speaker": {}, "timeline": [], "pitch_track": [],
                },
                "audio_quality.json": clean_quality(),
            }
            for name, value in fixtures.items():
                (output / name).write_text(json.dumps(value), encoding="utf-8")

            result = subprocess.run(
                [sys.executable, "pipeline/merge.py", "--output-dir", str(output)],
                cwd=REPO_ROOT, capture_output=True, text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            master = json.loads((output / "master.json").read_text())
            flags = [flag for turn in master["turns"]
                     for flag in turn["low_confidence_words"]]
            asr_flag = next(flag for flag in flags
                            if flag["why"] == "asr-low-confidence")
            self.assertEqual(asr_flag["word"], "uncertain")
            self.assertEqual(asr_flag["asr_confidence"], 0.4)
            wpm = (master["measurement_metadata"]["speakers"]["SPEAKER_00"]
                   ["computed_metrics"]["wpm"])
            self.assertEqual(wpm["availability"]["status"], "unavailable")


if __name__ == "__main__":
    unittest.main()
