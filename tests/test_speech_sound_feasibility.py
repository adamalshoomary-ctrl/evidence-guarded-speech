import copy
import json
import tempfile
import unittest
from pathlib import Path

from speech_sound_patterns.feasibility import (
    ALLOWED_SOURCES,
    PANPHON_FEATURES,
    SELECTION_SEED,
    canonical_json_bytes,
    classify_panphon_token,
    deterministic_key,
    validate_private_sample_manifest,
    validate_frozen_private_sample_manifest,
    validate_safe_feasibility_report,
)
from speech_sound_patterns.mfa_probe import _alignment_summary, _parse_time_metrics
from speech_sound_patterns.mfa_probe import _selected_clips as select_mfa_clips
from speech_sound_patterns.measure_feasibility_process import parse_elapsed_seconds
from speech_sound_patterns.phoneticxeus_probe import _selected_clips as select_xeus_clips
from speech_sound_patterns.summarize_feasibility import _percentile_middle


class FakeSegment:
    def __getitem__(self, name):
        return {feature: index % 3 - 1 for index, feature in enumerate(PANPHON_FEATURES)}[
            name
        ]


class FakeFeatureTable:
    def seg_known(self, value):
        return value in {"s", "ɡ", "ã"}

    def ipa_segs(self, value):
        if value in {"s", "ɡ", "ã"}:
            return [value]
        if value == "sil":
            return ["s", "i", "l"]
        return []

    def fts(self, value):
        if not self.seg_known(value):
            raise KeyError(value)
        return FakeSegment()


def manifest_fixture():
    sources = []
    for source_id in sorted(ALLOWED_SOURCES):
        known_text = source_id != "owner_controlled_integration"
        clip = {
            "safe_id": f"{source_id}_001",
            "source_state": (
                "owner_controlled_integration_only"
                if not known_text
                else "development"
            ),
            "canonical_audio_path": (
                f".research_data/speech_sound_patterns/feasibility/{source_id}.wav"
            ),
            "canonical_audio_sha256": "a" * 64,
            "sample_rate_hz": 16000,
            "channels": 1,
            "duration_s": 4.25,
            "intended_text_state": "source_transcript" if known_text else "unknown",
            "eligible_tools": (
                ["phoneticxeus", "mfa", "panphon"]
                if known_text
                else ["phoneticxeus", "panphon"]
            ),
        }
        if known_text:
            clip["intended_text_sha256"] = "b" * 64
        sources.append(
            {
                "source_id": source_id,
                "independent_accuracy_evidence": False,
                "clips": [clip],
            }
        )
    return {
        "schema_version": "1.0.0",
        "protocol_id": "speech_sound_local_feasibility_v1",
        "selection_seed": SELECTION_SEED,
        "development_only": True,
        "sources": sources,
    }


def safe_report_fixture():
    path = Path(__file__).parents[1] / "speech_sound_patterns" / "local-feasibility-v1.0.0.json"
    return json.loads(path.read_text(encoding="utf-8"))


class SpeechSoundFeasibilityTests(unittest.TestCase):
    def test_empty_clip_filter_selects_every_eligible_clip(self):
        document = manifest_fixture()
        self.assertEqual(len(select_xeus_clips(document, [])), 5)
        self.assertEqual(len(select_mfa_clips(document, [])), 4)

    def test_selection_key_is_stable_and_source_scoped(self):
        first = deterministic_key("source_a", "speaker_1")
        self.assertEqual(first, deterministic_key("source_a", "speaker_1"))
        self.assertNotEqual(first, deterministic_key("source_b", "speaker_1"))

    def test_even_sample_median_averages_the_two_middle_values(self):
        self.assertEqual(_percentile_middle([1, 2, 100, 101]), 51.0)

    def test_canonical_json_is_stable_and_rejects_nonfinite_numbers(self):
        self.assertEqual(canonical_json_bytes({"b": 2, "a": 1}), b'{"a":1,"b":2}\n')
        with self.assertRaises(ValueError):
            canonical_json_bytes({"bad": float("nan")})

    def test_private_manifest_accepts_only_frozen_development_shape(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(validate_private_sample_manifest(manifest_fixture(), directory), [])

    def test_probe_manifest_requires_the_exact_frozen_private_identity(self):
        errors = validate_frozen_private_sample_manifest(
            manifest_fixture(), "/tmp/repository"
        )
        self.assertTrue(any("frozen identity" in error for error in errors))

    def test_private_manifest_rejects_mfa_when_intended_text_is_unknown(self):
        document = manifest_fixture()
        owner = next(
            source
            for source in document["sources"]
            if source["source_id"] == "owner_controlled_integration"
        )["clips"][0]
        owner["eligible_tools"].append("mfa")
        errors = validate_private_sample_manifest(document, "/tmp/repository")
        self.assertTrue(any("cannot run MFA" in error for error in errors))

    def test_private_manifest_rejects_non_development_evidence(self):
        document = manifest_fixture()
        document["development_only"] = False
        document["sources"][0]["clips"][0]["source_state"] = "held_out"
        errors = validate_private_sample_manifest(document, "/tmp/repository")
        self.assertTrue(any("development only" in error for error in errors))
        self.assertTrue(any("development-only" in error for error in errors))

    def test_panphon_mapping_fails_closed_for_special_and_unknown_tokens(self):
        table = FakeFeatureTable()
        self.assertEqual(classify_panphon_token("sil", table)["decision"], "special_nonphone")
        self.assertEqual(classify_panphon_token("g", table)["decision"], "unsupported")
        supported = classify_panphon_token("ɡ", table)
        self.assertEqual(supported["decision"], "identity_nfd")
        self.assertEqual(list(supported["features"]), list(PANPHON_FEATURES))

    def test_panphon_mapping_uses_nfd_without_compatibility_normalization(self):
        result = classify_panphon_token("ã", FakeFeatureTable())
        self.assertTrue(result["normalization_changed"])
        self.assertEqual(result["nfd"], "ã")
        self.assertEqual(result["decision"], "identity_nfd")

    def test_mfa_summary_checks_tiers_and_preserves_nonphones(self):
        document = {
            "start": 0.0,
            "end": 1.0,
            "tiers": {
                "words": {"entries": [[0.0, 1.0, "word"]]},
                "phones": {
                    "entries": [
                        [0.0, 0.2, "sil"],
                        [0.2, 0.7, "W"],
                        [0.7, 0.8, ""],
                        [0.8, 1.0, "spn"],
                    ]
                },
            },
        }
        result = _alignment_summary(document)
        self.assertEqual(result["phone_interval_count"], 4)
        self.assertEqual(result["lexical_phone_interval_count"], 1)
        self.assertEqual(result["silence_interval_count"], 1)
        self.assertEqual(result["unknown_phone_interval_count"], 1)
        self.assertEqual(result["unlabeled_interval_count"], 1)

    def test_mfa_summary_rejects_overlapping_intervals(self):
        document = {
            "start": 0.0,
            "end": 1.0,
            "tiers": {
                "words": {"entries": [[0.0, 1.0, "word"]]},
                "phones": {"entries": [[0.0, 0.7, "W"], [0.6, 1.0, "ER"]]},
            },
        }
        with self.assertRaisesRegex(ValueError, "overlap"):
            _alignment_summary(document)

    def test_mfa_time_parser_uses_bytes_reported_by_macos(self):
        result = _parse_time_metrics(
            "  962445312  maximum resident set size\n  20 page faults\n  0 swaps\n"
            "  785778728 peak memory footprint\n"
        )
        self.assertEqual(result["maximum_resident_set_bytes"], 962445312)
        self.assertEqual(result["peak_memory_footprint_bytes"], 785778728)
        self.assertEqual(result["swaps"], 0)
        self.assertEqual(parse_elapsed_seconds("  15.93 real  1.0 user"), 15.93)
        with self.assertRaisesRegex(ValueError, "elapsed real time"):
            parse_elapsed_seconds("missing")

    def test_committed_report_must_keep_every_release_boundary_false(self):
        document = safe_report_fixture()
        self.assertEqual(validate_safe_feasibility_report(document), [])
        document["release_boundaries"]["coaching"] = True
        self.assertIn(
            "release boundary coaching must remain false",
            validate_safe_feasibility_report(document),
        )
        document = safe_report_fixture()
        document["status"] = "product_ready"
        self.assertIn(
            "feasibility report must remain release locked",
            validate_safe_feasibility_report(document),
        )

    def test_committed_report_rejects_private_or_clip_level_material(self):
        for key in ("private_participant_id", "transcript", "safe_id", "collapsed_tokens"):
            with self.subTest(key=key):
                document = copy.deepcopy(safe_report_fixture())
                document["mapping"][key] = "private"
                errors = validate_safe_feasibility_report(document)
                self.assertTrue(any("aggregate schema" in error for error in errors))
        document = safe_report_fixture()
        document["mapping"]["panphon"]["input"] = "/Users/private/audio.wav"
        self.assertTrue(
            any("absolute storage path" in error for error in validate_safe_feasibility_report(document))
        )

    def test_committed_report_rejects_unsafe_semantic_relabelling(self):
        mutations = (
            ("held out", lambda item: item["source_summary"].__setitem__("held_out_participants_or_labels_inspected", True)),
            ("accuracy", lambda item: item["mapping"].__setitem__("accuracy_or_relation_scoring_performed", True)),
            ("commercial", lambda item: item["tools"]["phoneticxeus"].__setitem__("commercial_release_status", "approved")),
            ("repeatability", lambda item: item["repeatability"]["phoneticxeus"].__setitem__("cpu_mps_frame_argmax_exact", False)),
        )
        for label, mutate in mutations:
            with self.subTest(label=label):
                document = safe_report_fixture()
                mutate(document)
                self.assertTrue(validate_safe_feasibility_report(document))


if __name__ == "__main__":
    unittest.main()
