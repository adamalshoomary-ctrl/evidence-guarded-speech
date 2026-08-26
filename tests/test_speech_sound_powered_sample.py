"""Checkpoint 22E4B: the powered sample, its truth, and the version registry.

These tests guard the three things that would silently invalidate a powered
replication: a redefined truth, a sample that is not actually a superset of the
first look, and a runner that reads the wrong frozen inputs because its private
copy of the identities drifted from the package.
"""

import importlib.util
import json
import unittest
from pathlib import Path

from speech_sound_patterns.benchmark import (
    FROZEN_BENCHMARK_MANIFEST_SHA256,
    FROZEN_SAMPLE_EXPECTATION,
    PRIVATE_BENCHMARK_ROOT,
    canonical_json_sha256,
    validate_frozen_private_benchmark_manifest,
)
from speech_sound_patterns.comparison import (
    ACTIVE_COMPARISON_VERSION,
    COMPARISON_VERSIONS,
    DEFAULT_COMPARISON_VERSION,
    FROZEN_SELECTION_GATES,
    load_comparison_contract,
    validate_comparison_contract,
    verify_frozen_inputs,
)
from speech_sound_patterns.feasibility import REPOSITORY_ROOT, file_sha256
from speech_sound_patterns.prepare_powered_benchmark import (
    POWERED_MANIFEST_PATH,
    assert_valid_sample_contract,
    load_sample_contract,
    sample_expectation,
    validate_sample_contract,
)

from tests.research_data import (
    needs_repository_history,
    needs_research_data,
)

POWERED_VERSION = "1.1.0"


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _standalone(name):
    spec = importlib.util.spec_from_file_location(
        name, REPOSITORY_ROOT / "speech_sound_patterns" / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PoweredSampleContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = load_sample_contract()

    def test_committed_sample_contract_is_valid(self):
        self.assertEqual(validate_sample_contract(self.contract), [])

    def test_the_sample_rules_were_declared_before_the_sample(self):
        self.assertIs(self.contract["declared_before_the_sample_existed"], True)
        self.assertEqual(
            self.contract["status"],
            "sample_rules_frozen_before_the_sample_was_built",
        )

    def test_the_declaration_binds_the_result(self):
        declaration = self.contract["declaration"]
        self.assertIs(declaration["this_replaces_an_underpowered_estimate"], True)
        self.assertIs(
            declaration["whatever_this_produces_is_the_reported_result"], True
        )
        self.assertIs(
            declaration["a_repeat_until_something_passes_is_prohibited"], True
        )
        self.assertIs(declaration["gates_may_be_changed"], False)

    def test_held_out_stays_sealed(self):
        self.assertIs(self.contract["held_out"]["held_out_access_allowed"], False)
        self.assertEqual(self.contract["held_out"]["unsealed_at"], "22H")

    def test_a_rebuilt_sample_cannot_be_used_to_change_a_result(self):
        document = json.loads(json.dumps(self.contract))
        document["selection_integrity"][
            "sample_may_be_rebuilt_to_change_a_result"
        ] = True
        self.assertIn(
            "the sample may not be rebuilt to change a result",
            validate_sample_contract(document),
        )

    def test_child_rows_cannot_reach_a_threshold(self):
        document = json.loads(json.dumps(self.contract))
        document["child_policy"][
            "child_rows_used_for_selection_or_thresholds"
        ] = True
        self.assertIn(
            "child rows may never enter selection or thresholds",
            validate_sample_contract(document),
        )

    def test_the_inherited_truth_rules_are_declared_unchanged(self):
        rules = self.contract["truth_and_metric_rules"]
        for field in (
            "expert_label_policy_changed",
            "phone_scope_changed",
            "alignment_changed",
            "metric_definitions_changed",
        ):
            self.assertIs(rules[field], False)


@needs_research_data
class PoweredManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = assert_valid_sample_contract()
        cls.expectation = sample_expectation(cls.contract)
        cls.manifest = _load(POWERED_MANIFEST_PATH)
        cls.frozen = _load(
            PRIVATE_BENCHMARK_ROOT / "benchmark-manifest-v1.0.0.json"
        )

    def _source(self, manifest, source_id):
        return next(
            source
            for source in manifest["sources"]
            if source["source_id"] == source_id
        )

    def test_the_powered_manifest_validates_against_its_expectation(self):
        errors = validate_frozen_private_benchmark_manifest(
            self.manifest,
            COMPARISON_VERSIONS[POWERED_VERSION]["benchmark_manifest_sha256"],
            expectation=self.expectation,
        )
        self.assertEqual(errors, [])

    def test_the_frozen_manifest_still_validates_unchanged(self):
        errors = validate_frozen_private_benchmark_manifest(
            self.frozen, FROZEN_BENCHMARK_MANIFEST_SHA256
        )
        self.assertEqual(errors, [])

    def test_the_powered_sample_is_a_superset_of_the_first_look(self):
        frozen_clips = self._source(self.frozen, "speechocean762")["clips"]
        powered_clips = self._source(self.manifest, "speechocean762")["clips"]
        frozen_records = {clip["private_record_id"] for clip in frozen_clips}
        powered_records = {clip["private_record_id"] for clip in powered_clips}
        self.assertTrue(frozen_records <= powered_records)
        self.assertEqual(len(frozen_records), 480)
        self.assertEqual(len(powered_records), 2280)

    def test_no_checkpoint_22e4_clip_moved_split_or_stratum(self):
        frozen_clips = self._source(self.frozen, "speechocean762")["clips"]
        powered = {
            clip["private_record_id"]: clip
            for clip in self._source(self.manifest, "speechocean762")["clips"]
        }
        for clip in frozen_clips:
            moved = powered[clip["private_record_id"]]
            self.assertEqual(moved["project_split"], clip["project_split"])
            self.assertEqual(moved["source_stratum"], clip["source_stratum"])

    def test_the_powered_sample_holds_every_non_held_out_adult(self):
        clips = self._source(self.manifest, "speechocean762")["clips"]
        adults = {
            (clip["project_split"], clip["private_participant_id"])
            for clip in clips
            if "adult" in clip["source_stratum"]
        }
        development = {item for item in adults if item[0] == "development"}
        tuning = {item for item in adults if item[0] == "threshold_tuning"}
        self.assertEqual(len(development), 77)
        self.assertEqual(len(tuning), 25)

    def test_the_child_sample_did_not_grow(self):
        powered = self._source(self.manifest, "speechocean762")["clips"]
        frozen = self._source(self.frozen, "speechocean762")["clips"]
        powered_children = {
            clip["private_participant_id"]
            for clip in powered
            if "child" in clip["source_stratum"]
        }
        frozen_children = {
            clip["private_participant_id"]
            for clip in frozen
            if "child" in clip["source_stratum"]
        }
        self.assertEqual(powered_children, frozen_children)

    def test_no_held_out_participant_entered_the_sample(self):
        assignments = _load(
            PRIVATE_BENCHMARK_ROOT.parent / "splits" / "speechocean762-v1.2.0.json"
        )["assignments"]
        held_out = {
            participant
            for participant, item in assignments.items()
            if item["project_split"] == "held_out_evaluation"
        }
        clips = self._source(self.manifest, "speechocean762")["clips"]
        used = {clip["private_participant_id"] for clip in clips}
        self.assertEqual(used & held_out, set())
        self.assertIs(self.manifest["held_out_evaluation_accessed"], False)

    def test_the_secondary_sources_are_the_identical_frozen_clips(self):
        for source_id in (
            "acted_clear_speech",
            "common_phone_1_0",
            "common_voice_26_australian_english",
        ):
            self.assertEqual(
                self._source(self.manifest, source_id),
                self._source(self.frozen, source_id),
            )

    def test_the_frozen_sample_expectation_is_unchanged(self):
        self.assertEqual(
            FROZEN_SAMPLE_EXPECTATION["clip_counts"]["speechocean762"], 480
        )
        self.assertEqual(
            FROZEN_SAMPLE_EXPECTATION["speechocean_participants"]["development"],
            {
                "source_adult_f": 4,
                "source_adult_m": 4,
                "source_child_f": 4,
                "source_child_m": 4,
            },
        )


class PoweredRelationTruthTests(unittest.TestCase):
    @needs_research_data
    def test_the_truth_extractor_reproduces_the_committed_22d_rows(self):
        from speech_sound_patterns.prepare_powered_relation_truth import (
            reproduce_frozen_truth,
        )

        self.assertEqual(reproduce_frozen_truth(), 5478)

    @needs_research_data
    def test_the_powered_truth_belongs_to_the_powered_manifest(self):
        document = _load(COMPARISON_VERSIONS[POWERED_VERSION]["relation_path"])
        self.assertIs(document["held_out_evaluation"], False)
        self.assertEqual(
            document["private_benchmark_manifest_sha256"],
            canonical_json_sha256(_load(POWERED_MANIFEST_PATH)),
        )
        self.assertEqual(document["frozen_rows_reproduced"], 5478)

    @needs_research_data
    def test_the_powered_truth_carries_no_candidate_prediction(self):
        document = _load(COMPARISON_VERSIONS[POWERED_VERSION]["relation_path"])
        for row in document["target_rows"][:200]:
            self.assertNotIn("prediction", row)
            self.assertNotIn("model_state", row)

    @needs_research_data
    def test_the_declared_adult_denominators_match_the_truth(self):
        document = _load(COMPARISON_VERSIONS[POWERED_VERSION]["relation_path"])
        counts = {}
        for row in document["target_rows"]:
            if row["age_stratum"] != "adult" or row["truth"] == "unscorable":
                continue
            counts[row["project_split"]] = counts.get(row["project_split"], 0) + 1
        self.assertEqual(
            counts, COMPARISON_VERSIONS[POWERED_VERSION]["adult_scorable_counts"]
        )


class ComparisonVersionRegistryTests(unittest.TestCase):
    def test_the_committed_record_remains_the_module_default(self):
        self.assertEqual(DEFAULT_COMPARISON_VERSION, "1.0.0")
        self.assertEqual(ACTIVE_COMPARISON_VERSION, POWERED_VERSION)

    @needs_research_data
    def test_both_contracts_validate_and_their_inputs_are_unchanged(self):
        for version in COMPARISON_VERSIONS:
            with self.subTest(version=version):
                contract = load_comparison_contract(version=version)
                self.assertEqual(validate_comparison_contract(contract), [])
                verify_frozen_inputs(version=version)

    def test_the_powered_contract_keeps_every_gate(self):
        contract = load_comparison_contract(version=POWERED_VERSION)
        for field, expected in FROZEN_SELECTION_GATES.items():
            self.assertEqual(contract["selection_gates"][field], expected)
        self.assertIs(
            contract["selection_gates"]["gates_may_be_changed_in_this_checkpoint"],
            False,
        )

    @needs_research_data
    def test_the_powered_contract_pins_the_files_on_disk(self):
        contract = load_comparison_contract(version=POWERED_VERSION)
        frozen = contract["frozen_inputs"]
        profile = COMPARISON_VERSIONS[POWERED_VERSION]
        self.assertEqual(
            frozen["expected_only_manifest_sha256"],
            file_sha256(profile["expected_manifest_path"]),
        )
        self.assertEqual(
            frozen["relation_evidence_sha256"],
            file_sha256(profile["relation_path"]),
        )
        self.assertEqual(
            frozen["private_benchmark_manifest_sha256"],
            file_sha256(POWERED_MANIFEST_PATH),
        )
        self.assertEqual(
            frozen["powered_sample_contract_sha256"],
            file_sha256(
                REPOSITORY_ROOT
                / "speech_sound_patterns"
                / "benchmark-powered-sample-contract-v1.0.0.json"
            ),
        )

    def test_the_powered_contract_pins_the_superseded_record(self):
        contract = load_comparison_contract(version=POWERED_VERSION)
        frozen = contract["frozen_inputs"]
        self.assertEqual(
            frozen["checkpoint_22e4_contract_sha256"],
            file_sha256(COMPARISON_VERSIONS["1.0.0"]["contract_path"]),
        )
        self.assertEqual(
            frozen["checkpoint_22e4_report_sha256"],
            file_sha256(COMPARISON_VERSIONS["1.0.0"]["report_path"]),
        )
        self.assertIs(
            contract["replication_declaration"]["version_1_0_0_files_edited"], False
        )

    def test_a_replication_cannot_drop_its_declaration(self):
        contract = load_comparison_contract(version=POWERED_VERSION)
        document = json.loads(json.dumps(contract))
        document["replication_declaration"][
            "whatever_this_produces_is_the_reported_result"
        ] = False
        self.assertIn(
            "replication_declaration.whatever_this_produces_is_the_reported_result "
            "must remain true",
            validate_comparison_contract(document),
        )

    def test_a_replication_cannot_claim_it_edited_the_first_look(self):
        contract = load_comparison_contract(version=POWERED_VERSION)
        document = json.loads(json.dumps(contract))
        document["replication_declaration"]["version_1_0_0_files_edited"] = True
        self.assertIn(
            "the superseded comparison version must not have been edited",
            validate_comparison_contract(document),
        )


class RefactorDidNotMoveTheFirstLookTests(unittest.TestCase):
    """Rebuild the committed checkpoint 22E4 report through the current code.

    Checkpoint 22E4B made the comparison code version aware. If that refactor had
    changed a metric, an alignment, an abstention or a denominator, the powered
    numbers would not be comparable with the numbers they replicate. Rebuilding
    the committed report from the committed private evidence and requiring an
    exact match is the check that rules that out.
    """

    @needs_research_data
    def test_the_committed_report_rebuilds_exactly(self):
        from speech_sound_patterns.summarize_comparison import build_report

        profile = COMPARISON_VERSIONS["1.0.0"]
        rebuilt = build_report(version="1.0.0")
        committed = _load(profile["report_path"])
        self.assertEqual(rebuilt, committed)


class StandaloneRunnerIdentityTests(unittest.TestCase):
    """The isolated runners restate the frozen identities; they must not drift."""

    SHARED_FIELDS = (
        "checkpoint",
        "expected_manifest_path",
        "expected_only_manifest_sha256",
        "expected_only_clip_count",
        "private_root",
    )

    def _assert_matches(self, module_name, extra_fields=()):
        module = _standalone(module_name)
        self.assertEqual(
            set(module.COMPARISON_VERSIONS), set(COMPARISON_VERSIONS), module_name
        )
        self.assertEqual(module.ACTIVE_COMPARISON_VERSION, ACTIVE_COMPARISON_VERSION)
        for version, package in COMPARISON_VERSIONS.items():
            runner = module.COMPARISON_VERSIONS[version]
            for field in self.SHARED_FIELDS + extra_fields:
                with self.subTest(module=module_name, version=version, field=field):
                    self.assertEqual(runner[field], package[field])

    def test_powsm_runner_identities_match_the_package(self):
        self._assert_matches(
            "comparison_powsm",
            extra_fields=("benchmark_manifest_sha256",),
        )

    def test_commonphone_runner_identities_match_the_package(self):
        self._assert_matches("comparison_commonphone")

    @needs_research_data
    def test_powsm_benchmark_manifest_path_matches_the_pinned_hash(self):
        module = _standalone("comparison_powsm")
        for version, runner in module.COMPARISON_VERSIONS.items():
            with self.subTest(version=version):
                self.assertEqual(
                    file_sha256(runner["benchmark_manifest_path"]),
                    runner["benchmark_manifest_sha256"],
                )

    @needs_research_data
    def test_each_runner_selects_the_right_number_of_gate_clips(self):
        for module_name in ("comparison_powsm", "comparison_commonphone"):
            module = _standalone(module_name)
            for version, profile in COMPARISON_VERSIONS.items():
                with self.subTest(module=module_name, version=version):
                    self.assertEqual(
                        len(module.gate_clips(version)),
                        profile["expected_only_clip_count"],
                    )


if __name__ == "__main__":
    unittest.main()
