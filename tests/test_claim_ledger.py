import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pipeline.claim_ledger import (
    RECORD_BLOCK_END,
    RECORD_BLOCK_START,
    build_evidence_catalog,
    canonicalize_package_claim_order,
    canonicalize_package_claim_text,
    canonicalize_package_references,
    claim_ledger,
    evaluation_model_input,
    normalise_report_newlines,
    render_measurement_record,
    scenario_record,
    strip_measurement_record,
    validate_package_semantics,
    verify_claim_ledger,
    withheld_measurements,
)


REPO_ROOT = Path(__file__).resolve().parent.parent


def metric_evidence(path, *, available=True, quality="high"):
    return {
        "value_path": path,
        "availability": {
            "status": "available" if available else "unavailable",
            "reason": None if available else "insufficient_sample",
        },
        "quality": {"category": quality},
    }


def master_fixture():
    return {
        "meta": {
            "enrichment_status": {
                "listener": {"status": "complete"},
                "evaluator": {"status": "complete"},
            }
        },
        "computed_metrics": {
            "SPEAKER_00": {"wpm": 120.0, "avg_response_pause_s": 1.2},
            "SPEAKER_01": {"wpm": 90.0},
        },
        "measurement_metadata": {
            "speakers": {
                "SPEAKER_00": {
                    "computed_metrics": {
                        "wpm": metric_evidence(
                            "computed_metrics.SPEAKER_00.wpm"
                        ),
                        "avg_response_pause_s": metric_evidence(
                            "computed_metrics.SPEAKER_00.avg_response_pause_s",
                            available=False,
                            quality="unavailable",
                        ),
                    },
                    "voice_quality": {},
                },
                "SPEAKER_01": {
                    "computed_metrics": {
                        "wpm": metric_evidence(
                            "computed_metrics.SPEAKER_01.wpm"
                        ),
                    },
                    "voice_quality": {},
                },
            },
            "overall_voice_quality": {},
        },
        "turns": [
            {
                "turn_id": 1,
                "speaker": "SPEAKER_00",
                "start_s": 1.0,
                "end_s": 20.12,
                "expressive_text": "A measured example.",
                "acoustics": {"loudness_vs_own_avg_db": -4.2},
                "word_effects": [{
                    "word": "example", "t": 4.0,
                    "speaker": "SPEAKER_00", "held_s": 0.8,
                }],
                "listener_note": "The delivery sounded careful.",
            },
            {
                "turn_id": 2,
                "speaker": "SPEAKER_01",
                "start_s": 21.0,
                "end_s": 25.0,
                "expressive_text": "Another speaker.",
                "acoustics": {"loudness_vs_own_avg_db": 2.0},
                "word_effects": [],
            },
        ],
        "notable_moments": [],
        "listener_contradictions": [],
        "speaker_overall_impressions": {},
    }


def reference(source, path, **values):
    return {
        "source": source,
        "path": path,
        "speaker": values.get("speaker"),
        "turn_id": values.get("turn_id"),
        "timestamp_s": values.get("timestamp_s"),
        "claimed_value": values.get("claimed_value"),
        "direction": values.get("direction", "none"),
    }


def ledger_for(text, references, *, claim_type="measured_observation",
               speaker="SPEAKER_00"):
    scenario = scenario_record("Interview practice", declared=True)
    package = {
        "report_markdown": f"{text} [C001]",
        "claims": [{
            "claim_id": "C001",
            "claim_type": claim_type,
            "text": text,
            "speaker": speaker,
            "references": references,
        }],
    }
    return package["report_markdown"], claim_ledger(package, scenario)


def issue_codes(result):
    return {issue["code"] for issue in result["issues"]}


class ClaimLedgerTests(unittest.TestCase):
    def test_a_report_returned_as_one_escaped_line_is_repaired(self):
        """Seen twice on real runs on 2026-08-24, with a different placeholder.

        The provider returned the whole document as a single line carrying a
        written stand in for its line breaks. It renders as a wall of text and
        still passes claim checking, because every marker is present and in
        order.
        """
        for placeholder in ("\\n", "/n"):
            with self.subTest(placeholder=placeholder):
                package = {"report_markdown":
                           f"# Title{placeholder}{placeholder}- One. [C001]"}

                repair = normalise_report_newlines(package)

                self.assertIsNotNone(repair)
                self.assertEqual(package["report_markdown"],
                                 "# Title\n\n- One. [C001]")

    def test_a_normal_report_is_never_rewritten(self):
        """The repair is narrow: no real line break, and escaped ones present."""
        for report in (
            "# Title\n\n- A statement. [C001]",
            "# Title\n\n- A path like C:\\name was quoted. [C001]",
            "One line and no escapes. [C001]",
            "A single rate of 5 km/n was quoted once. [C001]",
        ):
            with self.subTest(report=report):
                package = {"report_markdown": report}

                self.assertIsNone(normalise_report_newlines(package))
                self.assertEqual(package["report_markdown"], report)

    def test_the_ledger_records_that_a_repair_happened(self):
        scenario = scenario_record("Interview practice", declared=True)

        repaired = claim_ledger({"claims": []}, scenario, "a repair note")
        untouched = claim_ledger({"claims": []}, scenario)

        self.assertEqual(repaired["report_repair"], "a repair note")
        self.assertIsNone(untouched["report_repair"])

    def test_pipeline_run_record_is_excluded_from_claim_checking(self):
        """Uncited prose written by code is not uncited prose from the model.

        The block is rendered from master.json, so checking it against
        master.json would check the renderer against itself.
        """
        master = master_fixture()
        report, ledger = ledger_for(
            "The speaker spoke at 120 wpm.",
            [reference("metric", "computed_metrics.SPEAKER_00.wpm",
                       speaker="SPEAKER_00", claimed_value=120.0)],
        )
        with_record = render_measurement_record(master) + report

        self.assertEqual(
            verify_claim_ledger(master, ledger, with_record)["status"], "pass"
        )

    def test_a_report_cannot_smuggle_prose_inside_the_record_markers(self):
        """Stripping the block must not become a way to hide uncited text.

        The evaluator rejects any model report containing an HTML comment, so
        the only block reaching this function is the one the pipeline wrote.
        This test records what stripping does, so that guard is never dropped
        without someone noticing what it protects.
        """
        report, ledger = ledger_for(
            "The speaker spoke at 120 wpm.",
            [reference("metric", "computed_metrics.SPEAKER_00.wpm",
                       speaker="SPEAKER_00", claimed_value=120.0)],
        )
        hidden = (f"{RECORD_BLOCK_START}\nAn unverified assertion.\n"
                  f"{RECORD_BLOCK_END}\n{report}")

        self.assertNotIn("An unverified assertion.",
                         strip_measurement_record(hidden))

    def test_the_record_does_not_promise_an_interpretation_that_failed(self):
        master = master_fixture()

        with_report = render_measurement_record(master)
        degraded = render_measurement_record(
            master, interpretation_follows=False
        )

        self.assertIn("The interpretation below", with_report)
        self.assertNotIn("The interpretation below", degraded)
        self.assertIn("Measurements withheld from the interpretation",
                      degraded)

    def test_run_record_names_every_withheld_measurement(self):
        master = master_fixture()
        master["measurement_metadata"]["speakers"]["SPEAKER_00"]["computed_metrics"][
            "hidden"
        ] = metric_evidence(
            "computed_metrics.SPEAKER_00.hidden", available=False
        )

        withheld = {item["path"] for item in withheld_measurements(master)}
        rendered = render_measurement_record(master)

        self.assertIn("computed_metrics.SPEAKER_00.hidden", withheld)
        self.assertIn("computed_metrics.SPEAKER_00.hidden", rendered)
        self.assertIn("Measurements withheld from the interpretation: "
                      f"{len(withheld)}", rendered)

    def test_claim_ids_are_renumbered_by_report_order(self):
        package = {
            "report_markdown": "First. [C002] Second. [C001]",
            "claims": [
                {"claim_id": "C001", "text": "Second."},
                {"claim_id": "C002", "text": "First."},
            ],
        }

        canonicalize_package_claim_order(package)

        self.assertEqual(
            package["report_markdown"], "First. [C001] Second. [C002]"
        )
        self.assertEqual(
            [claim["claim_id"] for claim in package["claims"]],
            ["C001", "C002"],
        )
        self.assertEqual(
            [claim["text"] for claim in package["claims"]],
            ["First.", "Second."],
        )

    def test_reference_ownership_and_missing_timestamp_come_from_local_data(self):
        package = {
            "report_markdown": "A moment at 4 seconds was careful. [C001]",
            "claims": [{
                "claim_id": "C001",
                "claim_type": "interpretation",
                "text": "A moment at 4 seconds was careful.",
                "speaker": "SPEAKER_00",
                "references": [reference(
                    "user_context", "turns_by_id.1.expressive_text",
                    speaker="SPEAKER_01", turn_id=99,
                )],
            }],
        }

        canonicalize_package_references(
            package, master_fixture(),
            scenario_record("Interview", declared=True),
        )
        fixed = package["claims"][0]["references"][0]

        self.assertEqual(fixed["source"], "turn")
        self.assertEqual(fixed["speaker"], "SPEAKER_00")
        self.assertEqual(fixed["turn_id"], 1)
        self.assertEqual(fixed["timestamp_s"], 4.0)

    def test_evaluator_cannot_see_unavailable_or_low_quality_legacy_values(self):
        master = master_fixture()
        low = (master["measurement_metadata"]["speakers"]["SPEAKER_00"]
               ["computed_metrics"]["wpm"])
        low["quality"]["category"] = "low"

        safe = evaluation_model_input(master)
        catalog = build_evidence_catalog(
            master,
            scenario_record("Interview", declared=True),
            usable_metrics_only=True,
        )
        paths = {item["path"] for item in catalog}

        self.assertIsNone(safe["computed_metrics"]["SPEAKER_00"]["wpm"])
        self.assertIsNone(
            safe["computed_metrics"]["SPEAKER_00"]["avg_response_pause_s"]
        )
        self.assertNotIn("computed_metrics.SPEAKER_00.wpm", paths)
        self.assertNotIn(
            "computed_metrics.SPEAKER_00.avg_response_pause_s", paths
        )
        self.assertIn("computed_metrics.SPEAKER_01.wpm", paths)
        safe["turns"][0]["expressive_text"] = (
            "A measured example ... [1.5s] continued."
        )
        safe = evaluation_model_input(safe)
        self.assertIn("[measured pause]", safe["turns"][0]["expressive_text"])

    def test_evaluator_cannot_see_observation_with_released_interpretation_blocked(self):
        master = master_fixture()
        master["meta"]["per_speaker_voice_prosody"] = {
            "SPEAKER_00": {"f0_median_hz": 180.0}
        }
        master["measurement_metadata"]["speakers"]["SPEAKER_00"][
            "voice_prosody"
        ] = {
            "f0_median_hz": {
                "value_path": (
                    "meta.per_speaker_voice_prosody.SPEAKER_00.f0_median_hz"
                ),
                "availability": {"status": "available", "reason": None},
                "quality": {"category": "high"},
                "validation": {"release_limits": {
                    "released_interpretation": "blocked"
                }},
            }
        }

        safe = evaluation_model_input(master)
        catalog = build_evidence_catalog(
            master,
            scenario_record("Interview", declared=True),
            usable_metrics_only=True,
        )
        paths = {item["path"] for item in catalog}

        self.assertIsNone(
            safe["meta"]["per_speaker_voice_prosody"]["SPEAKER_00"]
            ["f0_median_hz"]
        )
        self.assertNotIn(
            "meta.per_speaker_voice_prosody.SPEAKER_00.f0_median_hz",
            paths,
        )

    def test_valid_metric_claim_passes_with_quality_summary(self):
        report, ledger = ledger_for(
            "Speaking rate was 120 wpm.",
            [reference(
                "metric", "computed_metrics.SPEAKER_00.wpm",
                speaker="SPEAKER_00", claimed_value=120.0,
            )],
        )

        result = verify_claim_ledger(master_fixture(), ledger, report)

        self.assertEqual(result["status"], "pass")
        self.assertEqual(
            result["summary"]["measurement_references_by_quality"]["high"], 1
        )

    def test_objective_claim_passes_when_listener_is_unavailable(self):
        master = master_fixture()
        master["meta"]["enrichment_status"]["listener"] = {
            "status": "unavailable"
        }
        report, ledger = ledger_for(
            "Speaking rate was 120 wpm.",
            [reference(
                "metric", "computed_metrics.SPEAKER_00.wpm",
                speaker="SPEAKER_00", claimed_value=120.0,
            )],
        )

        result = verify_claim_ledger(master, ledger, report)

        self.assertEqual(result["status"], "pass")

    def test_wrong_speaker_reference_is_caught(self):
        report, ledger = ledger_for(
            "Speaking rate was 120 wpm.",
            [reference(
                "metric", "computed_metrics.SPEAKER_00.wpm",
                speaker="SPEAKER_01", claimed_value=120.0,
            )],
            speaker="SPEAKER_01",
        )

        result = verify_claim_ledger(master_fixture(), ledger, report)

        self.assertIn("wrong_speaker", issue_codes(result))

    def test_nonexistent_turn_is_caught(self):
        report, ledger = ledger_for(
            "A moment at 4 seconds showed careful delivery.",
            [reference(
                "turn", "turns_by_id.99.expressive_text",
                speaker="SPEAKER_00", turn_id=99, timestamp_s=4.0,
            )],
        )

        result = verify_claim_ledger(master_fixture(), ledger, report)

        self.assertIn("reference_not_found", issue_codes(result))

    def test_unavailable_metric_is_caught(self):
        report, ledger = ledger_for(
            "Average response pause was 1.2 seconds.",
            [reference(
                "metric", "computed_metrics.SPEAKER_00.avg_response_pause_s",
                speaker="SPEAKER_00", claimed_value=1.2,
            )],
        )

        result = verify_claim_ledger(master_fixture(), ledger, report)

        self.assertIn("measurement_unavailable", issue_codes(result))

    def test_low_quality_metric_is_caught(self):
        master = master_fixture()
        evidence = (master["measurement_metadata"]["speakers"]["SPEAKER_00"]
                    ["computed_metrics"]["wpm"])
        evidence["quality"]["category"] = "low"
        report, ledger = ledger_for(
            "Speaking rate was 120 wpm.",
            [reference(
                "metric", "computed_metrics.SPEAKER_00.wpm",
                speaker="SPEAKER_00", claimed_value=120.0,
            )],
        )

        result = verify_claim_ledger(master, ledger, report)

        self.assertIn("measurement_low_quality", issue_codes(result))

    def test_flipped_db_direction_is_caught(self):
        report, ledger = ledger_for(
            "The turn was 4.2 dB above the speaker baseline.",
            [reference(
                "metric",
                "turns_by_id.1.acoustics.loudness_vs_own_avg_db",
                speaker="SPEAKER_00", turn_id=1,
                claimed_value=-4.2, direction="above",
            )],
        )

        result = verify_claim_ledger(master_fixture(), ledger, report)

        self.assertIn("wrong_direction", issue_codes(result))

    def test_explicit_db_sign_cannot_be_reversed(self):
        report, ledger = ledger_for(
            "The turn was +4.2 dB relative to the speaker baseline.",
            [reference(
                "metric",
                "turns_by_id.1.acoustics.loudness_vs_own_avg_db",
                speaker="SPEAKER_00", turn_id=1,
                claimed_value=-4.2, direction="below",
            )],
        )

        result = verify_claim_ledger(master_fixture(), ledger, report)

        self.assertIn("numeric_claim_without_direct_value", issue_codes(result))

    def test_duration_derived_from_two_timestamps_is_caught(self):
        report, ledger = ledger_for(
            "The turn lasted 19.12 seconds.",
            [
                reference(
                    "turn", "turns_by_id.1.start_s", speaker="SPEAKER_00",
                    turn_id=1, timestamp_s=1.0, claimed_value=1.0,
                ),
                reference(
                    "turn", "turns_by_id.1.end_s", speaker="SPEAKER_00",
                    turn_id=1, timestamp_s=20.12, claimed_value=20.12,
                ),
            ],
        )

        result = verify_claim_ledger(master_fixture(), ledger, report)

        self.assertIn("numeric_claim_without_direct_value", issue_codes(result))

    def test_listener_perception_cannot_be_labelled_user_context(self):
        report, ledger = ledger_for(
            "The delivery sounded careful.",
            [reference(
                "user_context", "turns_by_id.1.listener_note",
                speaker="SPEAKER_00", turn_id=1,
            )],
            claim_type="interpretation",
        )

        result = verify_claim_ledger(master_fixture(), ledger, report)

        self.assertIn("evidence_source_mismatch", issue_codes(result))

    def test_timestamp_outside_its_turn_is_caught(self):
        report, ledger = ledger_for(
            "A moment at 30 seconds sounded careful.",
            [reference(
                "turn", "turns_by_id.1.expressive_text",
                speaker="SPEAKER_00", turn_id=1, timestamp_s=30.0,
            )],
        )

        result = verify_claim_ledger(master_fixture(), ledger, report)

        self.assertIn("timestamp_outside_turn", issue_codes(result))

    def test_timestamp_written_as_seconds_is_recognised(self):
        report, ledger = ledger_for(
            "A moment at 4 seconds showed careful delivery.",
            [reference(
                "turn", "turns_by_id.1.expressive_text",
                speaker="SPEAKER_00", turn_id=1, timestamp_s=4.0,
            )],
        )

        result = verify_claim_ledger(master_fixture(), ledger, report)

        self.assertEqual(result["status"], "pass")

    def test_a_listener_impression_cannot_be_typed_a_measurement(self):
        """The exact case published in findings.md section 5, from a real run.

        The model typed a listener's impression of how somebody sounded as a
        measured observation, and its only evidence was a reference of source
        listener_perception. Nothing compared the claim's type against the
        class of evidence beneath it, so a subjective impression reached the
        machine readable ledger in the same truth class as a timestamp. The
        prose was honest and the prompt permitted it. Found 2026-08-27.
        """
        master = master_fixture()
        master["speaker_overall_impressions"] = {
            "SPEAKER_00": "A very soft, breathy whisper."
        }
        report, ledger = ledger_for(
            "A listener's overall impression describes the speaker's delivery "
            "as a very soft, breathy whisper with extremely low energy and a "
            "slow pace punctuated by long silences.",
            [reference(
                "listener_perception",
                "speaker_overall_impressions.SPEAKER_00",
                speaker="SPEAKER_00",
            )],
        )

        result = verify_claim_ledger(master, ledger, report)

        self.assertIn("claim_type_evidence_mismatch", issue_codes(result))

    def test_the_same_listener_claim_passes_as_an_interpretation(self):
        master = master_fixture()
        master["speaker_overall_impressions"] = {
            "SPEAKER_00": "A very soft, breathy whisper."
        }
        report, ledger = ledger_for(
            "A listener's overall impression describes the speaker's delivery "
            "as a very soft, breathy whisper with extremely low energy and a "
            "slow pace punctuated by long silences.",
            [reference(
                "listener_perception",
                "speaker_overall_impressions.SPEAKER_00",
                speaker="SPEAKER_00",
            )],
            claim_type="interpretation",
        )

        result = verify_claim_ledger(master, ledger, report)

        self.assertEqual(result["status"], "pass")

    def test_a_listener_note_cannot_be_typed_a_measurement(self):
        report, ledger = ledger_for(
            "The delivery sounded careful.",
            [reference(
                "listener_perception", "turns_by_id.1.listener_note",
                speaker="SPEAKER_00", turn_id=1,
            )],
        )

        result = verify_claim_ledger(master_fixture(), ledger, report)

        self.assertIn("claim_type_evidence_mismatch", issue_codes(result))

    def test_an_inferred_scenario_cannot_be_typed_a_measurement(self):
        scenario = scenario_record("An ad hoc solo recording", declared=False)
        package = {
            "report_markdown": "The setting is an ad hoc solo recording. [C001]",
            "claims": [{
                "claim_id": "C001",
                "claim_type": "measured_observation",
                "text": "The setting is an ad hoc solo recording.",
                "speaker": None,
                "references": [reference(
                    "inferred_context", "scenario.inferred"
                )],
            }],
        }
        ledger = claim_ledger(package, scenario)

        result = verify_claim_ledger(
            master_fixture(), ledger, package["report_markdown"]
        )

        self.assertIn("claim_type_evidence_mismatch", issue_codes(result))

    def test_a_declared_scenario_cannot_be_typed_a_measurement(self):
        """A person's own account of the setting is context, not measurement."""
        report, ledger = ledger_for(
            "The speaker described the setting as interview practice.",
            [reference("user_context", "scenario.declared")],
            speaker=None,
        )

        result = verify_claim_ledger(master_fixture(), ledger, report)

        self.assertIn("claim_type_evidence_mismatch", issue_codes(result))

    def test_one_listener_reference_taints_an_otherwise_measured_claim(self):
        """Mixing the classes inside one claim is the same defect."""
        report, ledger = ledger_for(
            "Speaking rate was 120 wpm and the delivery sounded careful.",
            [
                reference(
                    "metric", "computed_metrics.SPEAKER_00.wpm",
                    speaker="SPEAKER_00", claimed_value=120.0,
                ),
                reference(
                    "listener_perception", "turns_by_id.1.listener_note",
                    speaker="SPEAKER_00", turn_id=1,
                ),
            ],
        )

        result = verify_claim_ledger(master_fixture(), ledger, report)

        self.assertIn("claim_type_evidence_mismatch", issue_codes(result))

    def test_a_listener_path_declared_as_a_metric_is_still_refused(self):
        """Relabelling the source must not buy the claim its type back."""
        report, ledger = ledger_for(
            "The delivery sounded careful.",
            [reference(
                "metric", "turns_by_id.1.listener_note",
                speaker="SPEAKER_00", turn_id=1,
            )],
        )

        result = verify_claim_ledger(master_fixture(), ledger, report)

        self.assertIn("claim_type_evidence_mismatch", issue_codes(result))
        self.assertIn("evidence_source_mismatch", issue_codes(result))

    def test_turn_and_pause_evidence_remain_measurements(self):
        """The rule must not quietly shrink what a measurement may rest on."""
        master = master_fixture()
        master["turns"][1]["pause_before_s"] = 0.9
        report, ledger = ledger_for(
            "The turn began at 1.0 seconds.",
            [reference(
                "turn", "turns_by_id.1.start_s",
                speaker="SPEAKER_00", turn_id=1,
                timestamp_s=1.0, claimed_value=1.0,
            )],
        )

        result = verify_claim_ledger(master, ledger, report)

        self.assertEqual(result["status"], "pass")

    def test_screening_hypothesis_is_not_authorized(self):
        report, ledger = ledger_for(
            "This pattern may indicate a speech disorder.",
            [reference(
                "metric", "computed_metrics.SPEAKER_00.wpm",
                speaker="SPEAKER_00", claimed_value=120.0,
            )],
            claim_type="screening_hypothesis",
        )

        result = verify_claim_ledger(master_fixture(), ledger, report)

        self.assertIn("claim_level_not_authorized", issue_codes(result))

    def test_every_claim_needs_evidence_with_no_exempt_type(self):
        """The prescription type was withdrawn in schema 1.1.0.

        It was the only claim type allowed to exist with no evidence, and it
        existed so the report could tell a person what to practise. Nothing
        may do that now, so a claim without evidence fails whatever it calls
        itself.
        """
        for claim_type in ("measured_observation", "interpretation"):
            with self.subTest(claim_type=claim_type):
                report, ledger = ledger_for(
                    "Practise this opening for 60 seconds.", [],
                    claim_type=claim_type,
                )

                result = verify_claim_ledger(master_fixture(), ledger, report)

                self.assertEqual(result["status"], "fail")
                self.assertIn("missing_evidence", issue_codes(result))

    def test_package_requires_matching_report_markers(self):
        with self.assertRaisesRegex(ValueError, "markers"):
            validate_package_semantics({
                "report_markdown": "A statement without its marker.",
                "claims": [{
                    "claim_id": "C001",
                    "claim_type": "measured_observation",
                    "text": "A statement without its marker.",
                    "speaker": "SPEAKER_00",
                    "references": [reference(
                        "metric", "computed_metrics.SPEAKER_00.wpm",
                        claimed_value=120.0,
                    )],
                }],
            })

    def test_uncited_report_line_is_caught(self):
        report, ledger = ledger_for(
            "Speaking rate was 120 wpm.",
            [reference(
                "metric", "computed_metrics.SPEAKER_00.wpm",
                speaker="SPEAKER_00", claimed_value=120.0,
            )],
        )
        report += "\nThis extra factual line has no evidence marker."

        result = verify_claim_ledger(master_fixture(), ledger, report)

        self.assertIn("uncited_report_line", issue_codes(result))

    def test_wrapped_claim_paragraph_is_one_cited_block(self):
        text = "Speaking rate was 120 wpm and the delivery remained\nsteady."
        report, ledger = ledger_for(
            text,
            [reference(
                "metric", "computed_metrics.SPEAKER_00.wpm",
                speaker="SPEAKER_00", claimed_value=120.0,
            )],
        )
        ledger["claims"][0]["text"] = (
            "Speaking rate was 120 wpm and the delivery remained steady."
        )

        result = verify_claim_ledger(master_fixture(), ledger, report)

        self.assertEqual(result["status"], "pass")

    def test_two_cited_statements_may_share_one_paragraph(self):
        scenario = scenario_record("Interview practice", declared=True)
        report = "Rate was 120 wpm. [C001] Delivery was steady. [C002]"
        ledger = claim_ledger({
            "report_markdown": report,
            "claims": [
                {
                    "claim_id": "C001",
                    "claim_type": "measured_observation",
                    "text": "Rate was 120 wpm.",
                    "speaker": "SPEAKER_00",
                    "references": [reference(
                        "metric", "computed_metrics.SPEAKER_00.wpm",
                        speaker="SPEAKER_00", claimed_value=120.0,
                    )],
                },
                {
                    "claim_id": "C002",
                    "claim_type": "interpretation",
                    "text": "Delivery was steady.",
                    "speaker": "SPEAKER_00",
                    "references": [reference(
                        "turn", "turns_by_id.1.expressive_text",
                        speaker="SPEAKER_00", turn_id=1,
                    )],
                },
            ],
        }, scenario)

        result = verify_claim_ledger(master_fixture(), ledger, report)

        self.assertEqual(result["status"], "pass")

    def test_claim_text_is_derived_from_the_marked_report(self):
        package = {
            "report_markdown": "**Context:** Interview practice. [C001].",
            "claims": [{
                "claim_id": "C001",
                "claim_type": "interpretation",
                "text": "Interview practice.",
                "speaker": None,
                "references": [reference(
                    "user_context", "scenario.declared",
                )],
            }],
        }

        canonicalize_package_claim_text(package)

        self.assertEqual(
            package["claims"][0]["text"],
            "Context: Interview practice.",
        )

    def test_claim_marker_may_appear_inside_bold_markdown(self):
        report, ledger = ledger_for(
            "Clarity was supported by a rate of 120 wpm.",
            [reference(
                "metric", "computed_metrics.SPEAKER_00.wpm",
                speaker="SPEAKER_00", claimed_value=120.0,
            )],
        )
        report = f"**{report}**"

        result = verify_claim_ledger(master_fixture(), ledger, report)

        self.assertEqual(result["status"], "pass")

    def test_bold_factual_line_cannot_avoid_a_marker(self):
        report, ledger = ledger_for(
            "Speaking rate was 120 wpm.",
            [reference(
                "metric", "computed_metrics.SPEAKER_00.wpm",
                speaker="SPEAKER_00", claimed_value=120.0,
            )],
        )
        report += "\n**The speaker was consistently clear.**"

        result = verify_claim_ledger(master_fixture(), ledger, report)

        self.assertIn("uncited_report_line", issue_codes(result))

    def test_verify_stage_writes_human_and_machine_reports(self):
        report, ledger = ledger_for(
            "Speaking rate was 120 wpm.",
            [reference(
                "metric", "computed_metrics.SPEAKER_00.wpm",
                speaker="SPEAKER_00", claimed_value=120.0,
            )],
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir)
            (output / "master.json").write_text(
                json.dumps(master_fixture()), encoding="utf-8"
            )
            (output / "evaluation.md").write_text(report, encoding="utf-8")
            (output / "evaluation_claims.json").write_text(
                json.dumps(ledger), encoding="utf-8"
            )

            result = subprocess.run(
                [sys.executable, "pipeline/verify.py",
                 "--output-dir", str(output)],
                cwd=REPO_ROOT, capture_output=True, text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            machine = json.loads((output / "verification.json").read_text())
            readable = (output / "verification.md").read_text()
            self.assertEqual(machine["status"], "pass")
            self.assertIn("Claims verified: 1 of 1", readable)
            self.assertIn("Measurement references by quality", readable)


if __name__ == "__main__":
    unittest.main()
