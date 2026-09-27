"""Item F7: every computed metric is named for what it counts.

On 2026-09-27 eleven metrics were renamed, three removed and three defects
fixed. These tests hold each decision in place.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from fluency_events.contract import load_contract as load_fluency_contract
from fluency_events.contract import validate_contract as validate_fluency_contract
from pipeline.claim_ledger import numeric_mentions
from pipeline.measurement_evidence import METRIC_DEFINITIONS
from pipeline.reliability_policy import (
    COUNT_METRICS,
    PITCH_METRICS,
    PROPORTION_METRICS,
    RATE_METRICS,
    TIME_METRICS,
    measurement_validation,
)


REPO_ROOT = Path(__file__).resolve().parent.parent

OLD_NAMES = {
    "filler_count", "fillers_per_min", "drag_count", "loud_spike_count",
    "uptalk_count", "uptalk_per_min", "avg_response_pause_s",
    "median_pitch_hz", "hedge_count", "hedges_per_min", "hedge_breakdown",
    "pronoun_balance", "repetition_rate", "vocab_variety",
}


def clean_quality():
    return {"decision": "continue", "overall_status": "pass", "checks": [],
            "limitations": []}


def run_merge(fixtures):
    """Run the merge stage on fixture inputs and return master.json."""
    with tempfile.TemporaryDirectory() as temp_dir:
        output = Path(temp_dir)
        for name, value in fixtures.items():
            (output / name).write_text(json.dumps(value), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "pipeline/merge.py", "--output-dir", str(output)],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise AssertionError(result.stderr)
        return json.loads((output / "master.json").read_text(encoding="utf-8"))


def solo_fixtures():
    """Six words from one speaker; the pitch rises across the last one."""
    timings = [("Like", 0.0, 0.4), ("maybe", 0.5, 0.9), ("this", 1.0, 1.3),
               ("literally", 1.4, 2.0), ("works", 2.1, 2.5),
               ("fine.", 2.6, 3.4)]
    words = [{"text": text, "start": int(start * 1000),
              "end": int(end * 1000), "confidence": 0.99}
             for text, start, end in timings]
    pitch_track = [[round(step * 0.02, 2),
                    130.0 if step * 0.02 >= 3.08 else 100.0]
                   for step in range(171)]
    return {
        "diarization.json": {
            "turns": [{"speaker": "SPEAKER_00", "start_s": 0.0,
                       "end_s": 3.4, "duration_s": 3.4}],
            "account_holder_speaker": "SPEAKER_00",
            "contamination": {"status": "clear", "warning": None},
        },
        "transcript.json": {"words": words},
        "vad.json": {
            "audio_duration_s": 3.4, "speaking_time_s": 3.4,
            "silence_time_s": 0.0,
            "speech_chunks": [{"start": 0.0, "end": 3.4}],
            "pauses": [],
        },
        "acoustics.json": {
            "overall": {"duration_s": 3.4}, "per_speaker": {},
            "timeline": [], "pitch_track": pitch_track,
        },
        "audio_quality.json": clean_quality(),
    }


def conversation_fixtures():
    """Two speakers alternate three times each with no pause between turns."""
    turns = []
    words = []
    for index in range(6):
        speaker = f"SPEAKER_0{index % 2}"
        start = index * 2.0
        turns.append({"speaker": speaker, "start_s": start,
                      "end_s": start + 2.0, "duration_s": 2.0})
        for offset, text in ((0.0, "we"), (1.0, "talked.")):
            words.append({"text": text,
                          "start": int((start + offset) * 1000),
                          "end": int((start + offset + 0.9) * 1000),
                          "confidence": 0.99})
    return {
        "diarization.json": {"turns": turns},
        "transcript.json": {"words": words},
        "vad.json": {
            "audio_duration_s": 12.0, "speaking_time_s": 12.0,
            "silence_time_s": 0.0,
            "speech_chunks": [{"start": 0.0, "end": 12.0}],
            "pauses": [],
        },
        "acoustics.json": {
            "overall": {"duration_s": 12.0}, "per_speaker": {},
            "timeline": [], "pitch_track": [],
        },
        "audio_quality.json": clean_quality(),
    }


class MetricNameTests(unittest.TestCase):
    def test_old_names_are_gone_from_every_definition(self):
        defined = {path.split(".")[0] for path in METRIC_DEFINITIONS}
        registered = {path.split(".")[0] for path in (
            COUNT_METRICS | RATE_METRICS | PROPORTION_METRICS
            | TIME_METRICS | PITCH_METRICS)}
        self.assertEqual(defined & OLD_NAMES, set())
        self.assertEqual(registered & OLD_NAMES, set())

    def test_one_limit_on_change_over_time_replaces_the_progress_fields(self):
        validation = measurement_validation("wpm")
        self.assertNotIn("progress_use", validation["reliability"])
        self.assertNotIn("minimum_baseline_observations",
                         validation["reliability"])
        self.assertNotIn("individual_progress", validation["release_limits"])
        self.assertEqual(validation["release_limits"]["change_over_time"],
                         "blocked")

    def test_fluency_contract_keeps_change_over_time_blocked(self):
        contract = load_fluency_contract()
        self.assertEqual(validate_fluency_contract(contract), [])
        self.assertEqual(contract["contract_version"], "1.2.0")
        self.assertEqual(contract["release_limits"]["change_over_time"],
                         "blocked")
        self.assertIs(contract["downstream_policy"][
            "included_in_change_over_time_comparison"], False)
        self.assertNotIn("personal_progress", contract["release_limits"])

    def test_solo_final_rise_is_gated_on_counted_pitch_and_keeps_the_statement(self):
        master = run_merge(solo_fixtures())
        metrics = master["computed_metrics"]["SPEAKER_00"]
        entries = (master["measurement_metadata"]["speakers"]["SPEAKER_00"]
                   ["computed_metrics"])

        self.assertEqual(metrics["final_rise_count"], 1)
        # Before 2026-09-27 a solo run counted no pitch observations, so this
        # gate always failed while the count was still reported.
        self.assertEqual(entries["final_rise_count"]["sample"]
                         ["pitch_observation_count"], 6)
        self.assertEqual(entries["final_rise_count"]["availability"]
                         ["status"], "available")
        text = master["turns"][0]["expressive_text"]
        self.assertNotIn("?", text)
        self.assertTrue(text.endswith("fine."), text)
        effects = master["turns"][0]["word_effects"]
        self.assertEqual(
            [effect["rising_pitch_hz"] for effect in effects
             if "rising_pitch_hz" in effect],
            [[100.0, 130.0]],
        )
        self.assertEqual(set(metrics) & OLD_NAMES, set())

    def test_listed_phrases_are_counted_one_by_one_with_no_total(self):
        master = run_merge(solo_fixtures())
        metrics = master["computed_metrics"]["SPEAKER_00"]

        self.assertEqual(metrics["listed_phrase_counts"],
                         {"like (discourse)": 1, "maybe": 1, "literally": 1})
        self.assertNotIn("hedge_count", metrics)
        self.assertNotIn("hedges_per_min", metrics)

    def test_pause_mean_is_absent_when_no_pause_qualifies(self):
        master = run_merge(conversation_fixtures())
        for speaker in ("SPEAKER_00", "SPEAKER_01"):
            metrics = master["computed_metrics"][speaker]
            entry = (master["measurement_metadata"]["speakers"][speaker]
                     ["computed_metrics"]["mean_pause_before_turn_s"])
            # Before 2026-09-27 this read 0.0 and passed its gate.
            self.assertIsNone(metrics["mean_pause_before_turn_s"])
            self.assertEqual(entry["sample"]["response_opportunity_count"], 2)
            self.assertEqual(entry["availability"],
                             {"status": "unavailable",
                              "reason": "measurement_missing"})

    def test_pause_mean_applies_to_conversations_only(self):
        master = run_merge(solo_fixtures())
        entry = (master["measurement_metadata"]["speakers"]["SPEAKER_00"]
                 ["computed_metrics"]["mean_pause_before_turn_s"])
        self.assertEqual(entry["availability"]["reason"],
                         "recording_mode_not_applicable")

    def test_level_names_say_recorder_level_and_median(self):
        master = run_merge(solo_fixtures())
        self.assertIn("median_level_db",
                      master["speaker_baselines"]["SPEAKER_00"])
        self.assertIn("level_vs_own_median_db",
                      master["turns"][0]["acoustics"])
        self.assertNotIn("uptalk", master["meta"]["notes"])
        self.assertIn("recorder level", master["meta"]["notes"])

    def test_claim_checker_reads_new_and_old_rate_words(self):
        values = numeric_mentions(
            "2.5 filled pauses per minute, 1.2 final rises per min, "
            "4 repetitions per min, and an old 3 fillers/min."
        )["values"]
        self.assertEqual(
            [(item["value"], item["kind"]) for item in values],
            [(2.5, "per_minute"), (1.2, "per_minute"), (4.0, "per_minute"),
             (3.0, "per_minute")],
        )


if __name__ == "__main__":
    unittest.main()
