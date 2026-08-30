import copy
import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from speech_sound_patterns.feasibility import REPOSITORY_ROOT, file_sha256
from speech_sound_patterns.final_acceptance import (
    CONTRACT_PATH,
    CONTRACT_SHA256,
    FINAL_DECISION,
    FinalAcceptanceError,
    _expected_stage_records,
    build_evidence_inventory,
    build_final_report,
    canonical_digest,
    load_final_contract,
    runtime_output_leakage,
    snapshot_protected_state,
    snapshot_public_repository,
    static_pipeline_leakage,
    validate_final_contract,
    validate_final_report,
    validate_private_manifest,
    validate_semantic_evidence,
    write_exclusive_atomic,
)
from speech_sound_patterns import repository_closure
from speech_sound_patterns import validate_final_acceptance

from tests.research_data import (
    needs_repository_history,
    needs_research_data,
)


# The private manifest below describes the frozen pre-22H acceptance run, so
# every field it carries is that run's historical value. None of them may be
# read from live pipeline configuration, which is free to move on afterwards.
FROZEN_ENRICHMENT_MODEL_ID = "gemini-3.5-flash"


def _digest(char="a"):
    return char * 64


def private_manifest(contract):
    baseline = contract["repository_acceptance_policy"]["normal_pipeline"]
    repo = {
        "git_commit": baseline["frozen_pre_22h_git_commit"],
        "source_tree_sha256": baseline[
            "frozen_pre_22h_active_source_tree_sha256"
        ],
    }
    validators = []
    for module in contract["repository_acceptance_policy"]["required_validators"]:
        command = f"acceptance_python -m {module}"
        if module == "speech_sound_patterns.validate_final_acceptance":
            command += " --contract-only"
        validators.append({
            "module": module,
            "command": command,
            "status": "pass",
            "exit_code": 0,
            "duration_s": 0.1,
            "stdout_sha256": _digest("a"),
            "stderr_sha256": _digest("b"),
        })
    tests = [
        {
            "command": command,
            "status": "pass",
            "exit_code": 0,
            "duration_s": 0.1,
            "tests_run": contract["repository_acceptance_policy"][
                "required_test_minimums"
            ][command],
            "failures": 0,
            "errors": 0,
            "skipped": 0,
            "stdout_sha256": _digest("c"),
            "stderr_sha256": _digest("d"),
        }
        for index, command in enumerate(
            contract["repository_acceptance_policy"]["required_test_commands"]
        )
    ]
    enrichment = {
        stage: {
            "status": "complete",
            "attempts": 1,
            "model_id": FROZEN_ENRICHMENT_MODEL_ID,
            "error_category": None,
        }
        for stage in ("referee", "listener", "evaluator")
    }
    return {
        "schema_version": "1.0.0",
        "manifest_id": "speech_sound_patterns_final_acceptance_evidence_v1",
        "manifest_version": "1.0.0",
        "checkpoint": "22H",
        "status": "acceptance_complete",
        "contract": {
            "path": CONTRACT_PATH.name,
            "sha256": CONTRACT_SHA256,
            "version": "1.0.0",
        },
        "repository": {
            "git_commit": repo["git_commit"],
            "working_tree_dirty": True,
            "source_tree_sha256": repo["source_tree_sha256"],
            "acceptance_source_sha256": _digest("e"),
            "started_at_utc": "2026-08-12T00:00:00.000Z",
            "completed_at_utc": "2026-08-12T00:05:00.000Z",
            "acceptance_python": {
                "command_name": "acceptance_python",
                "implementation": "CPython",
                "version": "3.12.12",
                "executable_name": "python",
                "executable_sha256": _digest("9"),
            },
            "public_repository_before_sha256": _digest("8"),
            "public_repository_after_sha256": _digest("8"),
        },
        "held_out_audit": {
            "status": "sealed_no_access",
            "resolution": "held_out_remains_sealed_no_evaluation",
            "access_audit_scope": (
                "procedure_and_code_path_without_operating_system_file_access_audit"
            ),
            "private_assignment_files_opened": 0,
            "participant_identities_read": 0,
            "labels_read": 0,
            "audio_files_read": 0,
            "derived_rows_read": 0,
            "local_model_runs": 0,
            "provider_transmissions": 0,
        },
        "validations": validators,
        "python_compilation": {
            "command": "acceptance_python -m compileall -q pipeline regression speech_sound_patterns tests",
            "roots": contract["repository_acceptance_policy"][
                "python_compile_roots"
            ],
            "status": "pass",
            "exit_code": 0,
            "duration_s": 0.1,
            "stdout_sha256": _digest("f"),
            "stderr_sha256": _digest("0"),
        },
        "tests": tests,
        "owner_functional_integration": {
            "status": "not_performed_no_task_matched_owner_recording_available",
            "task_matched_recording_available": False,
            "used_for_selection": False,
            "used_for_accuracy": False,
            "used_for_fairness": False,
            "external_transfer": False,
            "private_artifact_committed": False,
        },
        "normal_pipeline": {
            "status": "pass",
            "run_id": "22h_20260812T000000",
            "fixture_id": "real_conversation",
            "process_exit_code": 0,
            "process_stdout_sha256": _digest("2"),
            "process_stderr_sha256": _digest("3"),
            "caffeinate_used": True,
            "configuration": {
                "mode": "conversation",
                "speakers": 2,
                "isolated_run": True,
                "me": None,
                "session_context": None,
            },
            "pipeline_version": baseline["frozen_pre_22h_pipeline_version"],
            "git_commit": repo["git_commit"],
            "source_tree_sha256": repo["source_tree_sha256"],
            "stage_count": 14,
            "stages": [
                {**stage, "status": "complete"}
                for stage in _expected_stage_records()
            ],
            "required_artifact_count": 15,
            "optional_artifact_count": 2,
            "missing_artifacts": [],
            "unexpected_artifacts": [],
            "regression": {
                "status": "pass",
                "fixture_id": "real_conversation",
                "checks_passed": 4,
                "process_exit_code": 0,
                "stdout_sha256": _digest("4"),
                "stderr_sha256": _digest("5"),
                "report_sha256": _digest("6"),
            },
            "enrichment": enrichment,
            "verification_status": "pass",
            "duration_s": 300.0,
            "process_duration_s": 301.0,
        },
        "protected_state": {
            "before_sha256": _digest("1"),
            "after_sha256": _digest("1"),
            "unchanged": True,
            "history_unchanged": True,
            "progress_unchanged": True,
            "root_output_unchanged": True,
            "public_repository_unchanged": True,
        },
        "leakage_checks": {
            "status": "pass",
            "pipeline_import_matches": [],
            "dynamic_import_or_literal_matches": [],
            "stage_or_output_matches": [],
            "forbidden_filename_matches": [],
            "forbidden_key_matches": [],
            "forbidden_content_matches": [],
            "unreadable_artifacts": [],
        },
        "evidence_inventory": {
            "snapshot_complete": True,
            "file_count": 1,
            "files": [{
                "path": "logs/validator.log",
                "sha256": _digest("7"),
                "size": 1,
            }],
            "inventory_sha256": canonical_digest([{
                "path": "logs/validator.log",
                "sha256": _digest("7"),
                "size": 1,
            }]),
        },
    }


class FinalAcceptanceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = load_final_contract()

    def changed(self, update):
        document = copy.deepcopy(self.contract)
        update(document)
        return document

    def test_frozen_contract_is_valid_and_checksum_bound(self):
        self.assertEqual(file_sha256(CONTRACT_PATH), CONTRACT_SHA256)
        self.assertEqual(validate_final_contract(self.contract), [])

    def test_contract_binds_every_registry_manifest_in_order(self):
        registry = json.loads(
            (REPOSITORY_ROOT / "speech_sound_patterns" / "corpus_manifests"
             / "registry-v1.0.0.json").read_text(encoding="utf-8")
        )
        expected = [
            (item["source_id"], f"corpus_manifests/{item['path']}")
            for item in registry["manifests"]
        ]
        actual = [
            (item["source_id"], item["path"])
            for item in self.contract["historical_inputs"][
                "corpus_manifest_bundle"
            ]
        ]
        self.assertEqual(actual, expected)

    def test_historical_bindings_reject_internal_external_and_dangling_symlinks(self):
        original = self.contract["historical_inputs"]["exact_files"][0]
        with tempfile.TemporaryDirectory(dir=CONTRACT_PATH.parent) as directory:
            root = Path(directory)
            external = root.parent.parent / (root.name + "-external.json")
            external.write_text("{}", encoding="utf-8")
            try:
                links = []
                for name, target in (
                    ("internal.json", CONTRACT_PATH),
                    ("external.json", external),
                    ("dangling.json", root / "missing.json"),
                ):
                    link = root / name
                    link.symlink_to(target)
                    links.append(link)
                for link in links:
                    with self.subTest(link=link.name):
                        changed = self.changed(
                            lambda document, link=link: document[
                                "historical_inputs"
                            ]["exact_files"][0].update({
                                "path": link.relative_to(CONTRACT_PATH.parent).as_posix(),
                                "sha256": original["sha256"],
                            })
                        )
                        errors = validate_final_contract(changed)
                        self.assertTrue(
                            any("may not use a symlink" in error for error in errors),
                            errors,
                        )
            finally:
                external.unlink(missing_ok=True)

    def test_no_selection_fields_cannot_be_populated(self):
        for field in (
            "candidate_system", "mapping", "feature_relation", "threshold",
            "provider_configuration", "repeated_relation_minimum",
        ):
            with self.subTest(field=field):
                changed = self.changed(
                    lambda document, field=field: document[
                        "frozen_no_selection"
                    ].update({field: "invented"})
                )
                self.assertTrue(validate_final_contract(changed))

    def test_rule_search_and_emission_cannot_be_enabled(self):
        for field in (
            "further_threshold_search_authorised",
            "candidate_rule_search_authorised",
            "possible_relation_candidate_emission_enabled",
            "repeated_relation_candidate_emission_enabled",
        ):
            with self.subTest(field=field):
                changed = self.changed(
                    lambda document, field=field: document[
                        "frozen_no_selection"
                    ].update({field: True})
                )
                self.assertTrue(validate_final_contract(changed))

    def test_held_out_access_and_result_cannot_be_opened(self):
        for field in (
            "private_assignment_path_may_be_opened",
            "identity_access_allowed",
            "label_access_allowed",
            "audio_access_allowed",
            "derived_row_access_allowed",
            "local_processing_allowed",
            "provider_transmission_allowed",
        ):
            with self.subTest(field=field):
                changed = self.changed(
                    lambda document, field=field: document[
                        "held_out_policy"
                    ].update({field: True})
                )
                self.assertTrue(validate_final_contract(changed))

    def test_every_release_boundary_stays_closed(self):
        for field in self.contract["release_boundaries"]:
            with self.subTest(field=field):
                changed = self.changed(
                    lambda document, field=field: document[
                        "release_boundaries"
                    ].update({field: True})
                )
                self.assertTrue(validate_final_contract(changed))

    def test_truth_classes_cannot_be_pooled_or_headlined(self):
        pooled = self.changed(
            lambda document: document["truth_class_policy"].update(
                {"truth_classes_pooled": True}
            )
        )
        headline = self.changed(
            lambda document: document["truth_class_policy"].update(
                {"headline_score": 0.99}
            )
        )
        self.assertTrue(validate_final_contract(pooled))
        self.assertTrue(validate_final_contract(headline))

    def test_contract_type_mutations_always_fail_closed(self):
        mutations = (None, [], {}, "wrong", 0, True)
        for field in self.contract:
            for value in mutations:
                with self.subTest(field=field, value=repr(value)):
                    changed = copy.deepcopy(self.contract)
                    changed[field] = value
                    self.assertTrue(validate_final_contract(changed))


class FinalAcceptanceEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = load_final_contract()

    def setUp(self):
        self.manifest = private_manifest(self.contract)
        self.report = build_final_report(self.manifest, contract=self.contract)

    def test_valid_private_manifest_builds_a_valid_report(self):
        self.assertEqual(
            validate_private_manifest(self.manifest, contract=self.contract), []
        )
        self.assertEqual(
            validate_final_report(
                self.report, contract=self.contract, manifest=self.manifest
            ),
            [],
        )

    def test_all_held_out_metrics_are_explicitly_unavailable(self):
        metrics = self.report["held_out_evaluation"]["metrics"]
        self.assertEqual(len(metrics), 40)
        self.assertIn(
            "true_positive_count",
            {metric["metric_id"] for metric in metrics},
        )
        for metric in metrics:
            self.assertEqual(metric["availability"], "unavailable")
            self.assertIsNone(metric["value"])
            self.assertIsNone(metric["numerator"])
            self.assertIsNone(metric["denominator"])
            self.assertIsNone(metric["interval_95"])
            self.assertTrue(metric["must_not_be_interpreted_as_zero"])
            self.assertIsNone(metric["gate_result"])

    def test_unavailable_metric_cannot_become_zero_pass_or_disappear(self):
        for mutation in ("zero", "pass", "missing"):
            with self.subTest(mutation=mutation):
                changed = copy.deepcopy(self.report)
                if mutation == "zero":
                    changed["held_out_evaluation"]["metrics"][0]["value"] = 0
                elif mutation == "pass":
                    changed["held_out_evaluation"]["metrics"][0][
                        "availability"
                    ] = "pass"
                else:
                    changed["held_out_evaluation"]["metrics"].pop()
                self.assertTrue(
                    validate_final_report(changed, contract=self.contract)
                )

    def test_any_held_out_access_count_fails(self):
        for field in self.manifest["held_out_audit"]:
            if field in {"status", "resolution", "access_audit_scope"}:
                continue
            with self.subTest(field=field):
                changed = copy.deepcopy(self.manifest)
                changed["held_out_audit"][field] = 1
                self.assertTrue(
                    validate_private_manifest(changed, contract=self.contract)
                )

    def test_missing_validator_test_or_pipeline_pass_fails(self):
        changed = copy.deepcopy(self.manifest)
        changed["validations"].pop()
        self.assertTrue(validate_private_manifest(changed, contract=self.contract))
        changed = copy.deepcopy(self.manifest)
        changed["tests"][0]["status"] = "fail"
        self.assertTrue(validate_private_manifest(changed, contract=self.contract))
        changed = copy.deepcopy(self.manifest)
        changed["normal_pipeline"]["status"] = "fail"
        self.assertTrue(validate_private_manifest(changed, contract=self.contract))

    def test_me_session_context_or_nonisolated_run_fails(self):
        for field, value in (
            ("me", "SPEAKER_00"),
            ("session_context", "context.json"),
            ("isolated_run", False),
        ):
            with self.subTest(field=field):
                changed = copy.deepcopy(self.manifest)
                changed["normal_pipeline"]["configuration"][field] = value
                self.assertTrue(
                    validate_private_manifest(changed, contract=self.contract)
                )

    def test_protected_state_and_leakage_must_pass(self):
        changed = copy.deepcopy(self.manifest)
        changed["protected_state"]["history_unchanged"] = False
        self.assertTrue(validate_private_manifest(changed, contract=self.contract))
        changed = copy.deepcopy(self.manifest)
        changed["leakage_checks"]["forbidden_key_matches"] = [
            {"token": "speech_sound"}
        ]
        self.assertTrue(validate_private_manifest(changed, contract=self.contract))

    def test_owner_integration_cannot_become_evidence_or_transfer(self):
        for field in (
            "used_for_selection", "used_for_accuracy", "used_for_fairness",
            "external_transfer", "private_artifact_committed",
        ):
            with self.subTest(field=field):
                changed = copy.deepcopy(self.manifest)
                changed["owner_functional_integration"][field] = True
                self.assertTrue(
                    validate_private_manifest(changed, contract=self.contract)
                )

    def test_definition_of_done_evidence_is_explicit_and_immutable(self):
        done = self.report["definition_of_done_evidence"]
        self.assertEqual(
            done["source_lineage_and_model_overlap"][
                "selected_candidate_model_overlap"
            ],
            "not_applicable_no_selected_candidate",
        )
        self.assertEqual(
            sum(
                item["participants"]
                for item in done["declared_sealed_population_strata"]
                if item["age_group"] == "adult"
            ),
            26,
        )
        self.assertEqual(
            sum(
                item["participants"]
                for item in done["declared_sealed_population_strata"]
                if item["age_group"] == "child"
            ),
            24,
        )
        self.assertFalse(done["population_strata_pooled"])
        self.assertEqual(
            done["australian_variant_strategy"][
                "equivalent_expert_australian_phone_relation_evidence_status"
            ],
            "unavailable",
        )
        changed = copy.deepcopy(self.report)
        changed["definition_of_done_evidence"][
            "population_strata_pooled"
        ] = True
        self.assertTrue(validate_final_report(changed, contract=self.contract))

    def test_report_rebuild_detects_any_dynamic_edit(self):
        changed = copy.deepcopy(self.report)
        changed["repository_acceptance"]["normal_pipeline"]["run_id"] = "other"
        errors = validate_final_report(
            changed, contract=self.contract, manifest=self.manifest
        )
        self.assertTrue(any("rebuild" in error for error in errors))

    def test_public_report_rejects_private_paths_and_identifiers_recursively(self):
        changed = copy.deepcopy(self.report)
        changed["repository_acceptance"]["private_participant_id"] = "secret"
        self.assertTrue(validate_final_report(changed, contract=self.contract))
        changed = copy.deepcopy(self.report)
        changed["owner_functional_integration"]["role"] = (
            ".research_data/speech_sound_patterns/private.json"
        )
        self.assertTrue(validate_final_report(changed, contract=self.contract))

    def test_report_type_mutations_never_raise(self):
        mutations = (None, [], {}, "wrong", 0, True)
        for field in self.report:
            for value in mutations:
                with self.subTest(field=field, value=repr(value)):
                    changed = copy.deepcopy(self.report)
                    changed[field] = value
                    errors = validate_final_report(
                        changed, contract=self.contract, manifest=self.manifest
                    )
                    self.assertTrue(errors)

    def test_public_report_rejects_every_audit_corruption(self):
        mutations = (
            lambda value: value["held_out_evaluation"][
                "declared_sealed_participants"
            ].update(adults=999),
            lambda value: value["held_out_evaluation"]["access_counts"].pop(
                "audio_files_read"
            ),
            lambda value: value["repository_acceptance"].update(
                git_commit="invalid"
            ),
            lambda value: value["repository_acceptance"].update(
                test_commands={"anything": "goes"}
            ),
            lambda value: value["owner_functional_integration"].update(
                task_matched_recording_available=True
            ),
            lambda value: value["repository_acceptance"][
                "normal_pipeline"
            ].update(run_id="adam"),
        )
        for mutation in mutations:
            with self.subTest(mutation=repr(mutation)):
                changed = copy.deepcopy(self.report)
                mutation(changed)
                self.assertTrue(validate_final_report(changed, contract=self.contract))

    def test_private_manifest_rejects_every_audit_corruption(self):
        mutations = (
            lambda value: value["normal_pipeline"].update(stages=[]),
            lambda value: value["normal_pipeline"].update(
                regression={
                    "status": "pass", "fixture_id": "wrong", "checks_passed": 0,
                }
            ),
            lambda value: value["tests"][0].update(skipped="private text"),
            lambda value: value["tests"][0].update(tests_run=1),
            lambda value: value["repository"].update(
                public_repository_after_sha256=_digest("6")
            ),
            lambda value: value["normal_pipeline"].update(
                pipeline_version="99.0.0"
            ),
        )
        for mutation in mutations:
            with self.subTest(mutation=repr(mutation)):
                changed = copy.deepcopy(self.manifest)
                mutation(changed)
                self.assertTrue(
                    validate_private_manifest(changed, contract=self.contract)
                )

    @needs_repository_history
    def test_frozen_normal_pipeline_baseline_is_historical_and_reachable(self):
        policy = self.contract["repository_acceptance_policy"]["normal_pipeline"]
        revision = policy["frozen_pre_22h_git_commit"]
        exists = subprocess.run(
            ["git", "cat-file", "-e", f"{revision}^{{commit}}"],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
        )
        self.assertEqual(exists.returncode, 0)
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", revision, "HEAD"],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
        )
        self.assertEqual(ancestor.returncode, 0)
        self.assertRegex(
            policy["frozen_pre_22h_active_source_tree_sha256"], r"^[0-9a-f]{64}$"
        )
        self.assertEqual(
            repository_closure.historical_active_source_digest(revision),
            policy["frozen_pre_22h_active_source_tree_sha256"],
        )
        self.assertEqual(
            repository_closure.historical_pipeline_version(revision),
            policy["frozen_pre_22h_pipeline_version"],
        )


class FinalAcceptanceBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = load_final_contract()

    def test_static_normal_pipeline_boundary_passes(self):
        result = static_pipeline_leakage(self.contract)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["pipeline_import_matches"], [])
        self.assertEqual(result["stage_or_output_matches"], [])

    def test_runtime_scanner_detects_filename_key_and_content_leakage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "speech_sound_candidates.json").write_text(
                '{"ok": true}', encoding="utf-8"
            )
            (root / "ordinary.json").write_text(
                '{"prompt_pack": true}', encoding="utf-8"
            )
            (root / "ordinary.md").write_text(
                "candidate_artifact", encoding="utf-8"
            )
            result = runtime_output_leakage(root, self.contract)
        self.assertEqual(result["status"], "fail")
        self.assertTrue(result["forbidden_filename_matches"])
        self.assertTrue(result["forbidden_key_matches"])
        self.assertTrue(result["forbidden_content_matches"])

    def test_runtime_scanner_allows_normal_output_directory_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "run_manifest.json").write_text(json.dumps({
                "output_dir": (
                    "/tmp/.research_data/speech_sound_patterns/"
                    "final_acceptance/run"
                ),
                "status": "complete",
            }), encoding="utf-8")
            result = runtime_output_leakage(root, self.contract)
        self.assertEqual(result["status"], "pass")

    def test_runtime_scanner_rejects_unreadable_required_text(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "evaluation.md").write_bytes(b"\xff\xfe")
            result = runtime_output_leakage(root, self.contract)
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["unreadable_artifacts"], ["evaluation.md"])

    def test_private_evidence_inventory_rehashes_exact_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "logs").mkdir()
            (root / "logs" / "one.log").write_text("proof", encoding="utf-8")
            inventory = build_evidence_inventory(root)
            self.assertEqual(inventory["file_count"], 1)
            self.assertEqual(inventory["files"][0]["path"], "logs/one.log")
            (root / "logs" / "one.log").write_text("changed", encoding="utf-8")
            self.assertNotEqual(inventory, build_evidence_inventory(root))

    def test_semantic_revalidation_reads_raw_regression_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            logs = root / "logs"
            logs.mkdir()
            for label in ("normal_pipeline", "regression"):
                (logs / f"{label}.stdout.log").write_text("", encoding="utf-8")
                (logs / f"{label}.stderr.log").write_text("", encoding="utf-8")
            regression_dir = root / "regression"
            regression_dir.mkdir()
            regression_path = regression_dir / "regression_report.json"
            regression_path.write_text(
                json.dumps({"status": "fail", "truth_results": []}),
                encoding="utf-8",
            )
            output_dir = root / "normal_pipeline" / "22h_20260812T000000"
            output_dir.mkdir(parents=True)
            (output_dir / "dummy.txt").write_text("ordinary", encoding="utf-8")
            inventory = build_evidence_inventory(root)
            by_path = {item["path"]: item for item in inventory["files"]}
            document = {
                "validations": [],
                "python_compilation": {},
                "tests": [],
                "normal_pipeline": {
                    "run_id": "22h_20260812T000000",
                    "process_stdout_sha256": by_path[
                        "logs/normal_pipeline.stdout.log"
                    ]["sha256"],
                    "process_stderr_sha256": by_path[
                        "logs/normal_pipeline.stderr.log"
                    ]["sha256"],
                    "regression": {
                        "status": "pass",
                        "fixture_id": "real_conversation",
                        "checks_passed": 999,
                        "process_exit_code": 0,
                        "stdout_sha256": by_path[
                            "logs/regression.stdout.log"
                        ]["sha256"],
                        "stderr_sha256": by_path[
                            "logs/regression.stderr.log"
                        ]["sha256"],
                        "report_sha256": by_path[
                            "regression/regression_report.json"
                        ]["sha256"],
                    },
                },
                "leakage_checks": {},
                "evidence_inventory": inventory,
            }
            errors = validate_semantic_evidence(document, root, self.contract)
        self.assertTrue(
            any("regression status differs" in error for error in errors),
            errors,
        )

    def test_exclusive_writer_never_overwrites(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "evidence.json"
            write_exclusive_atomic(target, b"first")
            with self.assertRaises(FinalAcceptanceError):
                write_exclusive_atomic(target, b"second")
            self.assertEqual(target.read_bytes(), b"first")

    def test_protected_snapshot_is_read_only_and_deterministic(self):
        before = snapshot_protected_state()
        after = snapshot_protected_state()
        self.assertEqual(before, after)
        self.assertEqual(len(before["sha256"]), 64)
        public_before = snapshot_public_repository()
        public_after = snapshot_public_repository()
        self.assertEqual(public_before, public_after)

    def test_final_decision_is_engineering_only(self):
        manifest = private_manifest(self.contract)
        report = build_final_report(manifest, contract=self.contract)
        decision = report["engineering_decision"]
        self.assertEqual(decision["decision"], FINAL_DECISION)
        self.assertTrue(decision["item_22_engineering_complete"])
        self.assertFalse(decision["held_out_performance_established"])
        self.assertFalse(decision["scientific_release"])
        self.assertFalse(decision["product_release"])
        self.assertFalse(decision["next_roadmap_item_approved"])


class RepositoryClosureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = load_final_contract()
        cls.manifest = private_manifest(cls.contract)
        cls.report = build_final_report(cls.manifest, contract=cls.contract)

    def _closure(self, directory):
        root = Path(directory)
        report_path = root / "final-evidence-v1.0.0.json"
        research_path = root / "research-contract-v1.7.0.json"
        report_path.write_text(json.dumps(self.report), encoding="utf-8")
        research_path.write_text(json.dumps({
            "protocol_version": "1.7.0",
            "status": (
                "item_22_engineering_complete_no_selection_held_out_"
                "not_performed_release_locked"
            ),
        }), encoding="utf-8")
        evidence = {
            "public_repository": {
                "closure_excluded_path": repository_closure.CLOSURE_RELATIVE_PATH,
                "only_exclusion": True,
                "snapshot_sha256": _digest("a"),
                "file_count": 1,
            },
            "verification": {
                "private_acceptance_evidence_revalidated": True,
                "validator_commands": len(
                    self.contract["repository_acceptance_policy"][
                        "required_validators"
                    ]
                ) + 1,
                "validator_commands_passed": len(
                    self.contract["repository_acceptance_policy"][
                        "required_validators"
                    ]
                ) + 1,
                "python_compilation": "pass",
                "test_commands": copy.deepcopy(
                    self.report["repository_acceptance"]["test_commands"]
                ),
                "protected_state_unchanged": True,
                "public_state_unchanged_during_closure": True,
                "acceptance_source_sha256": self.report[
                    "repository_acceptance"
                ]["acceptance_source_sha256"],
                "acceptance_python": copy.deepcopy(
                    self.report["repository_acceptance"]["acceptance_python"]
                ),
            },
        }
        with (
            mock.patch.object(repository_closure, "REPORT_PATH", report_path),
            mock.patch.object(
                repository_closure, "ACTIVE_RESEARCH_CONTRACT_PATH", research_path
            ),
        ):
            closure = repository_closure.build_repository_closure(evidence)
            errors = repository_closure.validate_repository_closure(
                closure, check_public_snapshot=False
            )
        self.assertEqual(errors, [])
        return closure, report_path, research_path

    def test_closure_validates_exact_final_bindings(self):
        with tempfile.TemporaryDirectory() as directory:
            self._closure(directory)

    @needs_repository_history
    def test_committed_closure_validates_as_a_historical_snapshot(self):
        closure = json.loads(repository_closure.CLOSURE_PATH.read_text())
        revision = repository_closure.find_historical_closure_commit(closure)
        self.assertIsNotNone(revision)
        self.assertEqual(
            subprocess.run(
                ["git", "merge-base", "--is-ancestor", revision, "HEAD"],
                cwd=REPOSITORY_ROOT,
                capture_output=True,
            ).returncode,
            0,
        )
        with mock.patch.object(
            repository_closure,
            "find_historical_closure_commit",
            return_value=revision,
        ):
            self.assertEqual(
                repository_closure.validate_repository_closure(closure), []
            )

    def test_historical_fallback_uses_real_git_bytes_and_direct_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            def git(*arguments):
                return subprocess.run(
                    ["git", "-C", str(root), *arguments],
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip()

            git("init", "-q")
            git("config", "user.name", "Closure Test")
            git("config", "user.email", "closure@example.invalid")
            (root / "baseline.txt").write_text("frozen\n", encoding="utf-8")
            git("add", "baseline.txt")
            git("commit", "-qm", "baseline")
            baseline = git("rev-parse", "HEAD")
            snapshot = repository_closure.snapshot_git_repository(baseline, root)
            closure = {
                "public_repository": {
                    "snapshot_sha256": snapshot["sha256"],
                    "file_count": len(snapshot["entries"]),
                }
            }
            closure_path = root / repository_closure.CLOSURE_RELATIVE_PATH
            closure_path.parent.mkdir(parents=True)
            closure_bytes = json.dumps(
                closure, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
            closure_path.write_bytes(closure_bytes)
            git("add", repository_closure.CLOSURE_RELATIVE_PATH)
            git("commit", "-qm", "closure")
            closure_commit = git("rev-parse", "HEAD")
            (root / "later.txt").write_text("later roadmap\n", encoding="utf-8")
            git("add", "later.txt")
            git("commit", "-qm", "later")

            self.assertEqual(
                repository_closure.find_historical_closure_commit(
                    closure, root, frozen_revision=baseline
                ),
                closure_commit,
            )
            self.assertIsNone(
                repository_closure.find_historical_closure_commit(
                    closure, root, frozen_revision=closure_commit
                )
            )
            closure_path.write_bytes(closure_bytes + b"\n")
            self.assertIsNone(
                repository_closure.find_historical_closure_commit(
                    closure, root, frozen_revision=baseline
                )
            )

    def test_frozen_live_bindings_reject_symlinks(self):
        closure = json.loads(repository_closure.CLOSURE_PATH.read_text())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            external = root / "contract-copy.json"
            external.write_bytes(repository_closure.CONTRACT_PATH.read_bytes())
            links = []
            for name, target in (
                ("external.json", external),
                ("internal.json", repository_closure.REPORT_PATH),
                ("dangling.json", root / "missing.json"),
            ):
                link = root / name
                link.symlink_to(target)
                links.append(link)
            for link in links:
                with self.subTest(link=link.name), mock.patch.object(
                    repository_closure, "CONTRACT_PATH", link
                ):
                    errors = repository_closure.validate_repository_closure(
                        closure, check_public_snapshot=False
                    )
                self.assertIn(
                    "final acceptance contract must be a regular repository file",
                    errors,
                )

    def test_later_files_need_a_matching_historical_closure_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            closure, report_path, research_path = self._closure(directory)
            with (
                mock.patch.object(repository_closure, "REPORT_PATH", report_path),
                mock.patch.object(
                    repository_closure,
                    "ACTIVE_RESEARCH_CONTRACT_PATH",
                    research_path,
                ),
                mock.patch.object(
                    repository_closure,
                    "snapshot_public_repository",
                    return_value={"sha256": _digest("f"), "entries": [1, 2]},
                ),
                mock.patch.object(
                    repository_closure,
                    "find_historical_closure_commit",
                    return_value=None,
                ),
            ):
                errors = repository_closure.validate_repository_closure(closure)
            self.assertTrue(
                any("no matching historical closure commit" in error for error in errors),
                errors,
            )

    def test_closure_rejects_validator_test_and_release_corruption(self):
        with tempfile.TemporaryDirectory() as directory:
            closure, report_path, research_path = self._closure(directory)
            mutations = (
                lambda value: value["verification"].update(validator_commands=1),
                lambda value: value["verification"]["test_commands"][0].update(
                    tests_run=1
                ),
                lambda value: value["verification"].update(
                    acceptance_python={"wrong": True}
                ),
                lambda value: value["release_boundaries"].update(product_release=True),
            )
            for mutation in mutations:
                with self.subTest(mutation=repr(mutation)):
                    changed = copy.deepcopy(closure)
                    mutation(changed)
                    with (
                        mock.patch.object(
                            repository_closure, "REPORT_PATH", report_path
                        ),
                        mock.patch.object(
                            repository_closure,
                            "ACTIVE_RESEARCH_CONTRACT_PATH",
                            research_path,
                        ),
                    ):
                        self.assertTrue(
                            repository_closure.validate_repository_closure(
                                changed, check_public_snapshot=False
                            )
                        )

    def test_default_final_validation_requires_repository_closure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report_path = root / "final-evidence-v1.0.0.json"
            report_path.write_text(json.dumps(self.report), encoding="utf-8")
            missing_closure = root / "missing-closure.json"
            output = io.StringIO()
            with (
                mock.patch.object(
                    repository_closure, "CLOSURE_PATH", missing_closure
                ),
                contextlib.redirect_stdout(output),
                self.assertRaises(SystemExit) as raised,
            ):
                validate_final_acceptance.main(["--report", str(report_path)])
            self.assertEqual(raised.exception.code, 1)
            self.assertIn("repository closure is missing", output.getvalue())


if __name__ == "__main__":
    unittest.main()
