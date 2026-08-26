import unittest

from pipeline.local_transcript import timed_words
from pipeline.pipeline_config import model_registry
from pipeline.recording_modes import build_stage_plan, resolve_recording_mode
from pipeline.solo_timing import build_solo_diarization


class RecordingModeTests(unittest.TestCase):
    def test_interpretation_layer_is_off_unless_asked_for(self):
        """master.json is the output. The model layer is a separate request.

        Item R5 made this the default on 2026-08-24. A run with no flag
        produces measurements, provenance, uncertainty and abstention, and
        stops.
        """
        for mode, speakers in (("solo", None), ("conversation", 2)):
            with self.subTest(mode=mode):
                _, later = build_stage_plan(mode, speakers, ["history.py"])
                scripts = [spec[1][0] for spec in later]

                self.assertNotIn("listener.py", scripts)
                self.assertNotIn("evaluate.py", scripts)
                self.assertNotIn("verify.py", scripts)
                self.assertIn("merge.py", scripts)
                self.assertIn("fluency_events.py", scripts)
                self.assertEqual(scripts[-1], "history.py")

    def test_referee_is_measurement_and_stays_on_by_default(self):
        """The referee uses the same provider but corrects master.json itself.

        It rewrites speaker attribution rather than commenting on it, so it
        belongs to the measurement and not to the optional interpretation.
        """
        _, later = build_stage_plan("conversation", 2, ["history.py"])
        commands = [spec[1] for spec in later]

        self.assertIn(["referee.py"], commands)
        self.assertIn(["merge.py", "--rebuild"], commands)

    def test_interpretation_outputs_are_only_declared_when_requested(self):
        from pipeline.recording_modes import INTERPRETATION_OUTPUTS

        _, plain = build_stage_plan("solo", None, ["history.py"])
        _, asked = build_stage_plan("solo", None, ["history.py"],
                                    interpret=True)
        declared = {name for spec in asked for name in spec[2] + spec[3]}
        plain_declared = {name for spec in plain for name in spec[2] + spec[3]}

        self.assertTrue(set(INTERPRETATION_OUTPUTS) <= declared)
        self.assertFalse(set(INTERPRETATION_OUTPUTS) & plain_declared)

    def test_solo_plan_skips_pyannote_and_referee(self):
        stage_1, later = build_stage_plan(
            "solo", None, ["history.py"], interpret=True
        )
        scripts = [spec[1][0] for spec in stage_1 + later]

        self.assertNotIn("diarize.py", scripts)
        self.assertNotIn("referee.py", scripts)
        self.assertNotIn(["merge.py", "--rebuild"],
                         [spec[1] for spec in later])
        self.assertEqual(scripts[0:3], ["transcribe.py", "align.py", "pauses.py"])
        self.assertEqual(
            stage_1[1][1], ["align.py", "--vad-method", "silero"]
        )
        self.assertIn("solo_timing.py", scripts)
        self.assertLess(scripts.index("merge.py"),
                        scripts.index("fluency_events.py"))
        self.assertLess(scripts.index("fluency_events.py"),
                        scripts.index("listener.py"))

    def test_conversation_plan_preserves_diarization_and_referee(self):
        stage_1, later = build_stage_plan(
            "conversation", 2, ["history.py"], interpret=True
        )
        scripts = [spec[1][0] for spec in stage_1 + later]

        self.assertEqual(stage_1[0][1], ["diarize.py", "--speakers", "2"])
        align_command = next(
            spec[1] for spec in stage_1 if spec[1][0] == "align.py"
        )
        self.assertEqual(align_command, ["align.py"])
        self.assertIn("referee.py", scripts)
        self.assertIn(["merge.py", "--rebuild"],
                      [spec[1] for spec in later])
        rebuild_index = next(
            index for index, spec in enumerate(later)
            if spec[1] == ["merge.py", "--rebuild"]
        )
        event_index = next(
            index for index, spec in enumerate(later)
            if spec[1] == ["fluency_events.py"]
        )
        listener_index = next(
            index for index, spec in enumerate(later)
            if spec[1] == ["listener.py"]
        )
        self.assertLess(rebuild_index, event_index)
        self.assertLess(event_index, listener_index)
        evaluator = next(spec for spec in later if spec[1][0] == "evaluate.py")
        verifier = next(spec for spec in later if spec[1][0] == "verify.py")
        self.assertIn("evaluation_claims.json", evaluator[2])
        self.assertIn("verification.json", verifier[2])

    def test_auto_with_one_declared_speaker_uses_solo_execution(self):
        self.assertEqual(resolve_recording_mode("auto", 1), "solo")

    def test_conflicting_mode_and_speaker_count_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "solo mode"):
            resolve_recording_mode("solo", 2)
        with self.assertRaisesRegex(ValueError, "conversation mode"):
            resolve_recording_mode("conversation", 1)


class SoloTimingTests(unittest.TestCase):
    def test_clean_solo_assigns_every_region_to_speaker_zero(self):
        transcript = {
            "utterances": [{
                "speaker": "A", "start": 100, "end": 2100,
                "words": [{"text": "hello"}, {"text": "there"}],
            }]
        }
        vad = {"speech_chunks": [
            {"start": 0.1, "end": 2.1},
            {"start": 3.0, "end": 4.0},
        ]}

        result = build_solo_diarization(transcript, vad)

        self.assertEqual(set(result["speakers"]), {"SPEAKER_00"})
        self.assertEqual(
            {turn["speaker"] for turn in result["turns"]}, {"SPEAKER_00"}
        )
        self.assertEqual(result["contamination"]["status"], "clear")

    def test_multiple_provider_clusters_create_an_explicit_warning(self):
        transcript = {"utterances": [
            {"speaker": "A", "start": 0, "end": 5000,
             "words": [{"text": "a"}] * 10},
            {"speaker": "B", "start": 6000, "end": 10000,
             "words": [{"text": "b"}] * 8},
        ]}
        vad = {"speech_chunks": [{"start": 0.0, "end": 10.0}]}

        result = build_solo_diarization(transcript, vad)
        contamination = result["contamination"]

        self.assertEqual(contamination["status"], "warn")
        self.assertEqual(contamination["provider_speaker_count"], 2)
        self.assertIn("should not be treated as a clean personal baseline",
                      contamination["warning"])
        self.assertEqual(set(result["speakers"]), {"SPEAKER_00"})


if __name__ == "__main__":
    unittest.main()


class TranscriberRoutingTests(unittest.TestCase):
    """The choice of transcriber is explicit, and there is no fallback."""

    def test_the_default_is_the_provider_path(self):
        stage_1, _ = build_stage_plan("conversation", 2, ["history.py"])
        self.assertEqual(stage_1[1][1], ["transcribe.py", "--speakers", "2"])

    def test_the_local_path_replaces_the_transcription_stage_only(self):
        provider, _ = build_stage_plan("conversation", 2, ["history.py"])
        local, _ = build_stage_plan(
            "conversation", 2, ["history.py"], transcriber="local"
        )
        self.assertEqual(local[1][1], ["transcribe_local.py"])
        self.assertEqual(
            [spec[1][0] for spec in provider][:1],
            [spec[1][0] for spec in local][:1],
        )
        self.assertEqual(
            [spec[0] for spec in provider], [spec[0] for spec in local]
        )

    def test_the_speaker_hint_is_not_passed_to_a_path_that_cannot_use_it(self):
        local, _ = build_stage_plan(
            "conversation", 2, ["history.py"], transcriber="local"
        )
        self.assertNotIn("--speakers", local[1][1])

    def test_an_unknown_transcriber_is_refused_rather_than_defaulted(self):
        with self.assertRaises(ValueError):
            build_stage_plan("solo", None, ["history.py"], transcriber="whisper")


class SoloContaminationEvidenceTests(unittest.TestCase):
    """A check with no evidence must say so, and must not be named for evidence
    it never had."""

    VAD = {"speech_chunks": [{"start": 0.0, "end": 5.0}]}

    def test_the_local_path_records_the_check_as_unavailable(self):
        result = build_solo_diarization(
            {"transcriber": "local",
             "words": [{"text": "hi", "start": 0, "end": 500}]},
            self.VAD,
        )
        contamination = result["contamination"]
        self.assertEqual(contamination["status"], "unavailable")
        self.assertEqual(contamination["method"], "no_speaker_clusters_available_v1")
        self.assertIn("not a clean result", contamination["warning"])

    def test_the_provider_path_keeps_its_own_method_name(self):
        result = build_solo_diarization(
            {"words": [{"text": "hi", "start": 0, "end": 500, "speaker": "A"}]},
            self.VAD,
        )
        self.assertEqual(result["contamination"]["status"], "clear")
        self.assertEqual(
            result["contamination"]["method"], "assemblyai_speaker_clusters_v1"
        )

    def test_a_second_voice_still_warns_on_the_provider_path(self):
        result = build_solo_diarization(
            {"words": [
                {"text": "hi", "start": 0, "end": 500, "speaker": "A"},
                {"text": "yo", "start": 600, "end": 900, "speaker": "B"},
            ]},
            self.VAD,
        )
        self.assertEqual(result["contamination"]["status"], "warn")


class LocalTranscriptShapeTests(unittest.TestCase):
    """A word must never disappear because the aligner could not time it."""

    def test_an_untimed_word_keeps_its_place_and_is_counted(self):
        aligned = {
            "segments": [
                {
                    "start": 0.0,
                    "end": 2.0,
                    "words": [
                        {"word": "one", "start": 0.0, "end": 0.5, "score": 0.9},
                        {"word": "two"},
                        {"word": "three", "start": 1.5, "end": 2.0},
                    ],
                }
            ]
        }
        words, borrowed = timed_words(aligned, (0.0, 2.0))
        self.assertEqual([word["text"] for word in words], ["one", "two", "three"])
        self.assertEqual(borrowed, 1)
        for word in words:
            self.assertIsInstance(word["start"], int)
            self.assertIsInstance(word["end"], int)
            self.assertGreater(word["end"], word["start"])

    def test_a_segment_with_no_timing_at_all_still_yields_words(self):
        aligned = {"segments": [{"words": [{"word": "hello"}, {"word": "there"}]}]}
        words, borrowed = timed_words(aligned, (1.0, 3.0))
        self.assertEqual(len(words), 2)
        self.assertEqual(borrowed, 2)
        self.assertGreaterEqual(words[0]["start"], 1000)

    def test_empty_tokens_are_dropped_but_real_ones_are_not(self):
        aligned = {
            "segments": [
                {"start": 0.0, "end": 1.0,
                 "words": [{"word": "  "}, {"word": "kept", "start": 0.1,
                                            "end": 0.4}]}
            ]
        }
        words, _ = timed_words(aligned, (0.0, 1.0))
        self.assertEqual([word["text"] for word in words], ["kept"])

    def test_a_missing_score_becomes_no_value_rather_than_a_number(self):
        aligned = {
            "segments": [
                {"start": 0.0, "end": 1.0,
                 "words": [{"word": "x", "start": 0.0, "end": 0.5}]}
            ]
        }
        words, _ = timed_words(aligned, (0.0, 1.0))
        self.assertIsNone(words[0]["alignment_score"])

    def test_an_alignment_score_is_never_written_as_an_asr_confidence(self):
        """Two different quantities on two different scales.

        Downstream contracts threshold `confidence` at values calibrated
        against a provider's ASR posterior. A forced alignment score placed
        there would be compared against a threshold that does not describe it.
        """
        aligned = {
            "segments": [
                {"start": 0.0, "end": 1.0,
                 "words": [{"word": "x", "start": 0.0, "end": 0.5,
                            "score": 0.31}]}
            ]
        }
        words, _ = timed_words(aligned, (0.0, 1.0))
        self.assertNotIn("confidence", words[0])
        self.assertEqual(words[0]["alignment_score"], 0.31)


class TranscriberProvenanceTests(unittest.TestCase):
    """A record may never describe a provider that did not produce it."""

    def test_the_registry_follows_the_chosen_transcriber(self):
        provider = model_registry("assemblyai")["transcription"]
        local = model_registry("local")["transcription"]
        self.assertEqual(provider["provider"], "AssemblyAI")
        self.assertEqual(provider["kind"], "provider")
        self.assertEqual(local["kind"], "local")
        self.assertIs(local["configuration"]["speaker_labels"], False)
        self.assertEqual(local["transcriber"], "local")

    def test_an_unknown_transcriber_cannot_reach_provenance(self):
        with self.assertRaises(ValueError):
            model_registry("whisper")
