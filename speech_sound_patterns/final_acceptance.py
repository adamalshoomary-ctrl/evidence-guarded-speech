"""Final repository acceptance for speech sound engineering.

Checkpoint 22H closes the engineering work on the frozen no-selection path.
There is no eligible method to evaluate, so this module never opens the private
held-out split, participant identities, labels, audio, or derived rows. It
validates public historical bindings, private repository-acceptance evidence,
and the safe aggregate final report.

The normal pipeline does not import this module.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

from .feasibility import (
    REPOSITORY_ROOT,
    canonical_json_bytes,
    file_sha256,
)


MODULE_ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = MODULE_ROOT / "final-acceptance-contract-v1.0.0.json"
CONTRACT_SHA256 = "49ec6d04032121efbdd2ae89472f1e952a970a1958d34bf955eadadf1deaf558"
REPORT_PATH = MODULE_ROOT / "final-evidence-v1.0.0.json"
PRIVATE_ACCEPTANCE_ROOT = (
    REPOSITORY_ROOT / ".research_data" / "speech_sound_patterns"
    / "final_acceptance"
)

REPORT_ID = "speech_sound_patterns_final_evidence"
REPORT_VERSION = "1.0.0"
REPORT_STATUS = "final_repository_acceptance_complete_release_locked"
FINAL_DECISION = "engineering_acceptance_passed_no_selection_path"

HEX_64 = re.compile(r"^[0-9a-f]{64}$")
GIT_REVISION = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
RUN_ID = re.compile(r"^22h_[0-9]{8}T[0-9]{6}$")
TEST_COUNT = re.compile(r"Ran\s+(\d+)\s+tests?\s+in")
SKIPPED_COUNT = re.compile(r"skipped=(\d+)")
FAILURE_COUNT = re.compile(r"failures=(\d+)")
ERROR_COUNT = re.compile(r"errors=(\d+)")

RELEASE_BOUNDARY_KEYS = {
    "normal_pipeline",
    "listener",
    "evaluator",
    "claim_ledger",
    "coaching",
    "history",
    "personal_progress",
    "named_pattern",
    "screening",
    "diagnosis",
    "severity",
    "cause",
    "treatment",
    "scientific_release",
    "product_release",
}

CONTRACT_ROOT_FIELDS = {
    "schema_version",
    "contract_id",
    "contract_version",
    "checkpoint",
    "status",
    "purpose",
    "plan_resolution",
    "historical_inputs",
    "frozen_no_selection",
    "held_out_policy",
    "truth_class_policy",
    "definition_of_done_evidence",
    "metric_policy",
    "owner_integration_policy",
    "repository_acceptance_policy",
    "private_acceptance_manifest",
    "output_and_reproduction",
    "privacy_policy",
    "mandatory_limitations",
    "release_boundaries",
    "acceptance",
}

PRIVATE_MANIFEST_FIELDS = {
    "schema_version",
    "manifest_id",
    "manifest_version",
    "checkpoint",
    "status",
    "contract",
    "repository",
    "held_out_audit",
    "validations",
    "python_compilation",
    "tests",
    "owner_functional_integration",
    "normal_pipeline",
    "protected_state",
    "leakage_checks",
    "evidence_inventory",
}

REPORT_FIELDS = {
    "schema_version",
    "report_id",
    "report_version",
    "checkpoint",
    "status",
    "contract",
    "historical_inputs",
    "plan_resolution",
    "selection_outcome",
    "held_out_evaluation",
    "historical_results_by_truth_class",
    "definition_of_done_evidence",
    "owner_functional_integration",
    "repository_acceptance",
    "privacy_and_distribution",
    "limitations",
    "release_boundaries",
    "engineering_decision",
}

PRIVATE_IDENTIFIER_KEYS = {
    "private_participant_id",
    "private_utterance_id",
    "participant_id",
    "session_id",
    "attempt_id",
    "trial_id",
    "recording_id",
    "audio_path",
    "transcript",
    "provider_payload",
    "raw_output",
}


class FinalAcceptanceError(ValueError):
    """Raised when final acceptance cannot proceed safely."""


def _read_json(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise FinalAcceptanceError(f"required JSON is missing: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FinalAcceptanceError(f"required JSON is unreadable: {path}") from exc


def _required_fields(value, fields, label, errors, *, exact=False):
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return False
    missing = sorted(set(fields) - set(value))
    if missing:
        errors.append(f"{label} is missing: {', '.join(missing)}")
        return False
    if exact:
        extras = sorted(set(value) - set(fields))
        if extras:
            errors.append(f"{label} has unsupported fields: {', '.join(extras)}")
    return True


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _historical_path(relative):
    if not isinstance(relative, str) or not relative:
        raise FinalAcceptanceError("historical path is invalid")
    root = REPOSITORY_ROOT.resolve()
    path = Path(os.path.abspath(MODULE_ROOT / relative))
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise FinalAcceptanceError("historical path leaves the repository") from exc
    current = root
    for component in path.relative_to(root).parts:
        current = current / component
        if current.is_symlink():
            raise FinalAcceptanceError(
                "historical binding may not use a symlink"
            )
    resolved = path.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise FinalAcceptanceError("historical path leaves the repository") from exc
    if ".research_data" in path.parts:
        raise FinalAcceptanceError("historical binding may not enter private evidence")
    return path


def _validate_bindings(records, label, errors):
    if not isinstance(records, list) or not records:
        errors.append(f"{label} must be a nonempty list")
        return
    seen_paths = set()
    seen_roles = set()
    for index, record in enumerate(records):
        item_label = f"{label}[{index}]"
        if not isinstance(record, dict):
            errors.append(f"{item_label} must be an object")
            continue
        required = {"path", "sha256"}
        if label == "historical_inputs.exact_files":
            required.add("role")
        if label == "historical_inputs.corpus_manifest_bundle":
            required.add("source_id")
        if set(record) != required:
            errors.append(f"{item_label} fields changed")
            continue
        path_text = record.get("path")
        digest = record.get("sha256")
        if path_text in seen_paths:
            errors.append(f"{label} repeats path {path_text}")
        seen_paths.add(path_text)
        if label == "historical_inputs.exact_files":
            role = record.get("role")
            if not isinstance(role, str) or not role:
                errors.append(f"{item_label}.role is invalid")
            elif role in seen_roles:
                errors.append(f"{label} repeats role {role}")
            seen_roles.add(role)
        if not isinstance(digest, str) or not HEX_64.fullmatch(digest):
            errors.append(f"{item_label}.sha256 is invalid")
            continue
        try:
            path = _historical_path(path_text)
        except FinalAcceptanceError as exc:
            errors.append(f"{item_label}: {exc}")
            continue
        if not path.is_file():
            errors.append(f"{item_label} is missing")
        elif file_sha256(path) != digest:
            errors.append(f"{item_label} checksum changed")


def load_final_contract(path=CONTRACT_PATH):
    document = _read_json(path)
    errors = validate_final_contract(document, path=path)
    if errors:
        raise FinalAcceptanceError("\n".join(errors))
    return document


def _validate_final_contract(document, *, path=CONTRACT_PATH):
    """Return every structural, provenance, and release-boundary error."""
    errors = []
    if not _required_fields(
        document, CONTRACT_ROOT_FIELDS, "final acceptance contract", errors,
        exact=True,
    ):
        return errors
    exact = {
        "schema_version": "1.0.0",
        "contract_id": "speech_sound_patterns_final_acceptance_v1",
        "contract_version": "1.0.0",
        "checkpoint": "22H",
        "status": "rules_frozen_before_final_repository_acceptance",
    }
    for field, expected in exact.items():
        if document.get(field) != expected:
            errors.append(f"final acceptance contract {field} changed")

    path = Path(path)
    if path.resolve(strict=False) == CONTRACT_PATH.resolve(strict=False):
        if document != _read_json(CONTRACT_PATH):
            errors.append("final acceptance contract differs from the frozen document")
        if not path.is_file() or file_sha256(path) != CONTRACT_SHA256:
            errors.append("frozen final acceptance contract checksum changed")

    resolution = document.get("plan_resolution") or {}
    if resolution.get("resolution") != "held_out_remains_sealed_no_evaluation":
        errors.append("the approved sealed held-out resolution changed")
    if resolution.get("owner_approved") is not True:
        errors.append("final acceptance requires explicit owner approval")
    if resolution.get("owner_approval_date") != "2026-08-12":
        errors.append("owner approval date changed")

    historical = document.get("historical_inputs") or {}
    if set(historical) != {
        "exact_files", "corpus_manifest_bundle",
        "historical_contract_versions_unchanged",
    }:
        errors.append("historical input fields changed")
    else:
        _validate_bindings(historical["exact_files"],
                           "historical_inputs.exact_files", errors)
        _validate_bindings(historical["corpus_manifest_bundle"],
                           "historical_inputs.corpus_manifest_bundle", errors)
        expected_versions = [f"1.{minor}.0" for minor in range(7)]
        if historical["historical_contract_versions_unchanged"] != expected_versions:
            errors.append("historical research contract version list changed")
        registry_record = next(
            (item for item in historical["exact_files"]
             if item.get("role") == "source_registry"),
            None,
        )
        if registry_record:
            try:
                registry = _read_json(_historical_path(registry_record["path"]))
                expected_bundle = [
                    (item["source_id"], f"corpus_manifests/{item['path']}")
                    for item in registry.get("manifests", [])
                ]
                actual_bundle = [
                    (item.get("source_id"), item.get("path"))
                    for item in historical["corpus_manifest_bundle"]
                ]
                if actual_bundle != expected_bundle:
                    errors.append("corpus manifest bundle differs from the registry")
            except FinalAcceptanceError as exc:
                errors.append(str(exc))

    frozen = document.get("frozen_no_selection") or {}
    null_fields = {
        "candidate_system", "mapping", "feature_relation", "threshold",
        "provider_configuration", "repeated_relation_minimum",
    }
    if frozen.get("selection_decision") != "no_selection":
        errors.append("the frozen selection decision changed")
    for field in null_fields:
        if frozen.get(field) is not None:
            errors.append(f"frozen_no_selection.{field} must remain null")
    for field in (
        "further_threshold_search_authorised",
        "candidate_rule_search_authorised",
        "possible_relation_candidate_emission_enabled",
        "repeated_relation_candidate_emission_enabled",
    ):
        if frozen.get(field) is not False:
            errors.append(f"frozen_no_selection.{field} must remain false")
    expected_gates = {
        "minimum_precision_point_estimate": 0.75,
        "minimum_precision_wilson_95_lower": 0.5,
        "maximum_false_concerns_per_scorable_opportunity": 0.01,
        "minimum_recall": 0.2,
        "minimum_true_positives": 7,
        "development_and_tuning_both_required": True,
    }
    if frozen.get("selection_gates") != expected_gates:
        errors.append("the unchanged selection gates moved")
    prompt = frozen.get("prompt_pack") or {}
    if prompt != {
        "path": "research-prompt-pack-v1.0.0.json",
        "sha256": "c53522ee155628d6266c5494d7e9c45d9d06f4dc550abac82f9816e00f5b7d72",
        "word_count": 20,
        "status": "unreviewed_inactive_developer_research_only",
        "product_pack": False,
    }:
        errors.append("the frozen prompt pack binding changed")

    held_out = document.get("held_out_policy") or {}
    if held_out.get("evaluation_status") != "not_performed":
        errors.append("held-out evaluation status must remain not_performed")
    if held_out.get("result_availability") != "unavailable":
        errors.append("held-out results must remain unavailable")
    if held_out.get("reason_code") != "not_evaluated_no_selected_candidate":
        errors.append("held-out non-evaluation reason changed")
    if held_out.get("held_out_metric_gate_result") is not None:
        errors.append("held-out gate result must remain null")
    for field in (
        "private_assignment_path_may_be_opened",
        "identity_access_allowed",
        "label_access_allowed",
        "audio_access_allowed",
        "derived_row_access_allowed",
        "local_processing_allowed",
        "provider_transmission_allowed",
        "held_out_metrics_may_be_used_for_engineering_completion",
        "may_become_item_24_tuning_or_evaluation_silently",
    ):
        if held_out.get(field) is not False:
            errors.append(f"held_out_policy.{field} must remain false")
    if held_out.get("later_access_requires_new_contract_and_explicit_owner_approval") is not True:
        errors.append("later held-out access must require a new contract and approval")
    if held_out.get("held_out_adults_declared_sealed") != 26:
        errors.append("held-out adult declaration changed")
    if held_out.get("held_out_children_declared_sealed") != 24:
        errors.append("held-out child declaration changed")

    truth = document.get("truth_class_policy") or {}
    if truth.get("truth_classes_pooled") is not False:
        errors.append("truth classes may not be pooled")
    if truth.get("headline_score") is not None:
        errors.append("a headline score is prohibited")
    sections = truth.get("required_sections")
    expected_truth = {
        "source_specific_expert_phone_relations",
        "human_corrected_phone_boundaries",
        "automatic_phone_alignments",
        "validated_sentence_audio",
        "pronunciation_reference_lexicons",
        "owner_controlled_functional_integration",
    }
    if not isinstance(sections, list) or {
        item.get("truth_class") for item in sections if isinstance(item, dict)
    } != expected_truth:
        errors.append("required truth-class sections changed")

    done = document.get("definition_of_done_evidence") or {}
    expected_lineage = {
        "primary_relation_source": "speechocean762",
        "source_lineage_group": "speechocean762",
        "participant_split_cross_overlap_count": 0,
        "selected_candidate_model": None,
        "selected_candidate_model_overlap": (
            "not_applicable_no_selected_candidate"
        ),
        "historical_candidate_lineage_path": (
            "provider_register/provider-register-v1.2.0.json"
        ),
        "historical_candidate_lineage_sha256": (
            "7c70adef70b0d5a4ff27e98eb094c989359c0a700004e221b2441e40494eadb6"
        ),
        "historical_overlap_may_be_treated_as_independent_truth": False,
    }
    if done.get("source_lineage_and_model_overlap") != expected_lineage:
        errors.append("definition-of-done source lineage or overlap changed")
    else:
        lineage_path = _historical_path(
            expected_lineage["historical_candidate_lineage_path"]
        )
        if (
            not lineage_path.is_file()
            or file_sha256(lineage_path)
            != expected_lineage["historical_candidate_lineage_sha256"]
        ):
            errors.append("historical candidate lineage checksum changed")
    expected_strata = [
        ("source_adult_f", "adult", "female", 15),
        ("source_adult_m", "adult", "male", 11),
        ("source_child_f", "child", "female", 10),
        ("source_child_m", "child", "male", 14),
    ]
    strata = done.get("declared_sealed_population_strata")
    actual_strata = [
        (
            item.get("stratum"), item.get("age_group"),
            item.get("sex_stratum"), item.get("participants"),
            item.get("result_availability"),
        )
        for item in strata
    ] if isinstance(strata, list) else None
    if actual_strata != [(*item, "unavailable") for item in expected_strata]:
        errors.append("declared sealed population strata changed")
    if done.get("population_strata_pooled") is not False:
        errors.append("population strata may not be pooled")
    if done.get("provider_and_local_decision") != {
        "decision": "no_selection",
        "selected_provider": None,
        "selected_local_system": None,
        "local_only_decision_claimed": False,
        "historical_paid_provider_comparison_completed": True,
        "historical_provider_result_may_be_relabelled_as_selected": False,
    }:
        errors.append("provider and local no-selection decision changed")
    if done.get("australian_variant_strategy") != {
        "strategy": (
            "open_reference_forms_and_variety_stress_evidence_remain_separate_"
            "from_produced_relation_truth"
        ),
        "macquarie_pronunciation_data_status": (
            "not_licensed_owner_declined_acquisition_enquiry"
        ),
        "andosl_status": (
            "rejected_licence_incompatible_owner_declined_acquisition_enquiry"
        ),
        "equivalent_expert_australian_phone_relation_evidence_status": (
            "unavailable"
        ),
        "open_reference_sources": [
            "mfa_english_dictionary",
            "wikipron_eng_latn_uk_broad",
            "wikipron_eng_latn_us_broad",
            "wiktionary_australian_kaikki",
        ],
        "australian_sentence_audio_source": (
            "common_voice_26_australian_english"
        ),
        "australian_phone_relation_accuracy_established": False,
        "australian_fairness_established": False,
    }:
        errors.append("Australian variant evidence status changed")

    metric = document.get("metric_policy") or {}
    metrics = metric.get("held_out_metrics")
    if not isinstance(metrics, list) or len(metrics) != 40:
        errors.append("held-out metric declaration must contain forty metrics")
    else:
        metric_ids = [item.get("metric_id") for item in metrics
                      if isinstance(item, dict)]
        if len(metric_ids) != len(set(metric_ids)):
            errors.append("held-out metric identifiers must be unique")
        if any(set(item) != {"metric_id", "truth_class", "unit"}
               for item in metrics if isinstance(item, dict)):
            errors.append("held-out metric declaration fields changed")
        if any(item.get("truth_class") != "source_specific_expert_phone_relations"
               for item in metrics if isinstance(item, dict)):
            errors.append("held-out metrics changed truth class")
        required_metric_ids = {
            "true_positive_count", "false_positive_count",
            "false_negative_count", "true_negative_count",
            "phone_relation_precision", "precision_wilson_95_lower",
            "phone_relation_recall", "phone_relation_f1",
            "phone_relation_precision_by_outcome",
            "phone_relation_recall_by_outcome",
            "phone_relation_f1_by_outcome",
            "phone_relation_uncertainty_by_outcome",
            "accepted_variant_false_concern_rate", "asr_attribution_matrix",
            "false_concerns_per_scorable_opportunity", "abstention_rate",
            "unscorable_rate", "coverage", "calibration",
            "exact_same_input_repeatability",
            "repeated_human_production_reliability",
            "human_inter_reviewer_agreement",
            "human_intra_reviewer_agreement",
            "relation_metrics_with_uncertainty_source_adult_f",
            "relation_metrics_with_uncertainty_source_adult_m",
            "relation_metrics_with_uncertainty_source_child_f",
            "relation_metrics_with_uncertainty_source_child_m",
            "relation_metrics_with_uncertainty_by_language_variety",
            "relation_metrics_with_uncertainty_by_first_language_background",
            "relation_metrics_with_uncertainty_by_multilingual_status",
            "relation_metrics_with_uncertainty_by_task",
            "relation_metrics_with_uncertainty_by_phonetic_context",
            "relation_metrics_with_uncertainty_by_voice_range",
            "relation_metrics_with_uncertainty_by_device",
            "relation_metrics_with_uncertainty_by_audio_quality",
            "relation_metrics_with_uncertainty_by_speech_difference",
            "relation_metrics_with_uncertainty_by_consented_target_population",
            "provider_incremental_value", "unsupported_scope_rate",
            "pattern_level_metrics",
        }
        if set(metric_ids) != required_metric_ids:
            errors.append("held-out predeclared metric inventory changed")
    if metric.get("required_relation_outcomes") != [
        "exact", "substitution", "deletion", "insertion"
    ]:
        errors.append("required relation outcomes changed")
    if metric.get("required_uncertainty_strata") != [
        "source_adult_f", "source_adult_m",
        "source_child_f", "source_child_m", "language_variety",
        "first_language_background", "multilingual_status", "task",
        "phonetic_context", "voice_range", "device", "audio_quality",
        "speech_difference", "consented_target_population",
    ]:
        errors.append("required uncertainty strata changed")
    if metric.get("unavailable_record") != {
        "availability": "unavailable",
        "value": None,
        "numerator": None,
        "denominator": None,
        "interval_95": None,
        "reason_code": "not_evaluated_no_selected_candidate",
        "must_not_be_interpreted_as_zero": True,
        "gate_result": None,
    }:
        errors.append("unavailable metric record changed")
    for field in (
        "every_predeclared_metric_must_be_present",
    ):
        if metric.get(field) is not True:
            errors.append(f"metric_policy.{field} must remain true")
    for field in (
        "unavailable_may_be_encoded_as_zero",
        "historical_metrics_may_be_relabelled_as_held_out",
        "cross_truth_class_metric_pooling_allowed",
    ):
        if metric.get(field) is not False:
            errors.append(f"metric_policy.{field} must remain false")

    owner = document.get("owner_integration_policy") or {}
    expected_owner_statuses = {
        "not_performed_no_task_matched_owner_recording_available",
    }
    if set(owner.get("allowed_statuses") or []) != expected_owner_statuses:
        errors.append("owner integration statuses changed")
    for field in (
        "existing_solo_or_conversation_recording_is_task_matched",
        "may_fill_evidence_adequacy_gap",
        "may_enter_selection_or_accuracy",
        "may_support_fairness_or_population_claim",
        "external_transfer_allowed",
        "private_artifact_committed",
    ):
        if owner.get(field) is not False:
            errors.append(f"owner_integration_policy.{field} must remain false")
    if owner.get("optional_owner_input_path_enabled_for_checkpoint_22h") is not False:
        errors.append("optional owner input path must remain disabled")

    repository = document.get("repository_acceptance_policy") or {}
    pipeline = repository.get("normal_pipeline") or {}
    if pipeline.get("isolated_run_required") is not True:
        errors.append("normal pipeline acceptance must be isolated")
    if pipeline.get("caffeinate_required") is not True:
        errors.append("normal pipeline acceptance must use caffeinate")
    if pipeline.get("me_argument_allowed") is not False:
        errors.append("normal pipeline acceptance may not use --me")
    if pipeline.get("session_context_allowed") is not False:
        errors.append("normal pipeline acceptance may not use session context")
    if pipeline.get("expected_stage_count") != 14:
        errors.append("normal pipeline stage count changed")
    if repository.get("protected_state_must_be_byte_identical") is not True:
        errors.append("protected repository state must remain byte identical")
    if repository.get("normal_pipeline_source_may_import_speech_sound_patterns") is not False:
        errors.append("normal pipeline may not import speech sound code")
    if repository.get("normal_pipeline_may_emit_speech_sound_artifact") is not False:
        errors.append("normal pipeline may not emit speech sound evidence")
    if repository.get("acceptance_python_command_name") != "acceptance_python":
        errors.append("acceptance Python command name changed")
    if repository.get("required_test_minimums") != {
        "acceptance_python -m unittest tests.test_speech_sound_final_acceptance": 35,
        "acceptance_python -m unittest discover -s tests": 729,
    }:
        errors.append("required test minimums changed")
    if repository.get("maximum_skipped_tests_per_command") != 0:
        errors.append("skipped test policy changed")
    if repository.get(
        "public_repository_state_must_be_byte_identical_during_acceptance"
    ) is not True:
        errors.append("public repository state must remain byte identical")
    frozen_pipeline = {
        "frozen_pre_22h_git_commit": (
            "6d2b2055ef77861212297ffb1f9c63cbc09be217"
        ),
        "frozen_pre_22h_pipeline_version": "0.10.1",
        "frozen_pre_22h_active_source_tree_sha256": (
            "5efb674cc2e61a55cd610a6ec1a8957a97ee7a299818557e8cbf1decc3f744c6"
        ),
        "frozen_pre_22h_model_registry_sha256": (
            "b7fc893516bb4e509c5171d9a0556a1df2bafb55d4339435fcc69ca8a9e2bc45"
        ),
        "frozen_pre_22h_prompt_registry_sha256": (
            "4776ac8c707736117e236178662c2fc516eea0f58c5535f4948a4442960b721c"
        ),
    }
    for field, expected in frozen_pipeline.items():
        if pipeline.get(field) != expected:
            errors.append(f"normal pipeline baseline {field} changed")

    private = document.get("private_acceptance_manifest") or {}
    if private.get("allowed_root") != (
        ".research_data/speech_sound_patterns/final_acceptance"
    ):
        errors.append("private acceptance root changed")
    if private.get("no_overwrite") is not True:
        errors.append("private acceptance evidence must not overwrite")
    if private.get("held_out_access_counters_must_all_be_zero") is not True:
        errors.append("held-out access counters must remain zero")
    if private.get(
        "raw_evidence_must_be_checksum_linked_and_revalidated"
    ) is not True:
        errors.append("raw acceptance evidence must be checksum linked")
    if private.get("private_paths_or_audio_identity_may_enter_public_report") is not False:
        errors.append("private paths or audio identity may not enter the report")

    output = document.get("output_and_reproduction") or {}
    if output.get("report_path") != REPORT_PATH.name:
        errors.append("final report path changed")
    if output.get("repository_closure_path") != "repository-closure-v1.0.0.json":
        errors.append("repository closure path changed")
    if output.get("overwrite_allowed") is not False:
        errors.append("final report overwrite must remain prohibited")
    if output.get("aggregate_only") is not True:
        errors.append("final report must remain aggregate only")
    if output.get("reproduction_rebuilds_in_memory_and_requires_exact_bytes") is not True:
        errors.append("final report reproduction must require exact bytes")
    for field in (
        "post_report_changes_require_repository_closure",
        "repository_closure_excludes_only_its_own_path_from_public_snapshot",
        "repository_closure_must_bind_report_and_active_research_contract",
    ):
        if output.get(field) is not True:
            errors.append(f"output_and_reproduction.{field} must remain true")
    if output.get("repository_closure_overwrite_allowed") is not False:
        errors.append("repository closure overwrite must remain prohibited")

    privacy = document.get("privacy_policy") or {}
    if not isinstance(privacy, dict) or any(value is not False
                                               for value in privacy.values()):
        errors.append("every final acceptance privacy flag must remain false")

    limitations = document.get("mandatory_limitations")
    if not isinstance(limitations, list) or len(limitations) != 10:
        errors.append("ten mandatory limitations are required")
    elif any(not isinstance(item, str) or not item for item in limitations):
        errors.append("mandatory limitations must be nonempty text")

    release = document.get("release_boundaries") or {}
    if set(release) != RELEASE_BOUNDARY_KEYS:
        errors.append("release boundary fields changed")
    elif any(value is not False for value in release.values()):
        errors.append("every scientific, product, and downstream boundary must stay closed")

    acceptance = document.get("acceptance") or {}
    if acceptance.get("final_decision") != FINAL_DECISION:
        errors.append("final engineering decision changed")
    if acceptance.get("held_out_evaluation_required_for_this_path") is not False:
        errors.append("held-out evaluation cannot be required on the no-selection path")
    if acceptance.get("engineering_complete_only") is not True:
        errors.append("completion must remain engineering only")
    if acceptance.get("scientific_or_product_release_supported") is not False:
        errors.append("final acceptance cannot support scientific or product release")
    return errors


def validate_final_contract(document, *, path=CONTRACT_PATH):
    """Validate arbitrary JSON without leaking a Python exception."""
    try:
        return _validate_final_contract(document, path=path)
    except Exception as exc:  # noqa: BLE001 - malformed JSON must fail closed
        return [f"final acceptance contract is malformed: {type(exc).__name__}"]


def assert_valid_final_contract(document=None):
    document = load_final_contract() if document is None else document
    errors = validate_final_contract(document)
    if errors:
        raise FinalAcceptanceError("\n".join(errors))
    return document


def canonical_digest(value):
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _snapshot_entry(path, root):
    path = Path(path)
    if not path.exists() and not path.is_symlink():
        return {"path": str(path.relative_to(root)), "type": "missing"}
    if path.is_symlink():
        return {
            "path": str(path.relative_to(root)),
            "type": "symlink",
            "target": os.readlink(path),
        }
    if path.is_file():
        return {
            "path": str(path.relative_to(root)),
            "type": "file",
            "sha256": file_sha256(path),
            "size": path.stat().st_size,
        }
    if path.is_dir():
        return {"path": str(path.relative_to(root)), "type": "directory"}
    return {"path": str(path.relative_to(root)), "type": "other"}


def snapshot_protected_state(repo_root=REPOSITORY_ROOT):
    """Recursively snapshot personal files and the existing root output."""
    repo_root = Path(repo_root).resolve()
    wanted = [repo_root / "history.json", repo_root / "progress.md"]
    output = repo_root / "output"
    wanted.append(output)
    if output.is_dir() and not output.is_symlink():
        wanted.extend(sorted(output.rglob("*")))
    entries = [_snapshot_entry(path, repo_root) for path in wanted]
    return {"entries": entries, "sha256": canonical_digest(entries)}


def snapshot_public_repository(repo_root=REPOSITORY_ROOT, *, exclude_paths=()):
    """Snapshot every tracked or nonignored untracked repository file."""
    repo_root = Path(repo_root).resolve()
    try:
        result = subprocess.run(
            [
                "git", "ls-files", "-z", "--cached", "--others",
                "--exclude-standard",
            ],
            cwd=repo_root,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise FinalAcceptanceError("cannot enumerate public repository files") from exc
    excluded = {str(Path(item)) for item in exclude_paths}
    paths = sorted(
        item.decode("utf-8") for item in result.stdout.split(b"\0") if item
        and item.decode("utf-8") not in excluded
    )
    entries = [_snapshot_entry(repo_root / relative, repo_root) for relative in paths]
    return {"entries": entries, "sha256": canonical_digest(entries)}


def build_evidence_inventory(run_root):
    """Checksum every raw acceptance file present before the manifest write."""
    run_root = Path(run_root).resolve()
    if not run_root.is_dir() or run_root.is_symlink():
        raise FinalAcceptanceError("private acceptance run root is missing or unsafe")
    files = []
    for path in sorted(run_root.rglob("*")):
        if path.name in {"acceptance-manifest.json", "acceptance-failure.json"}:
            continue
        if path.is_symlink() or (not path.is_file() and not path.is_dir()):
            raise FinalAcceptanceError("private evidence contains an unsafe entry")
        if path.is_file():
            relative = str(path.relative_to(run_root))
            files.append({
                "path": relative,
                "sha256": file_sha256(path),
                "size": path.stat().st_size,
            })
    return {
        "snapshot_complete": True,
        "file_count": len(files),
        "files": files,
        "inventory_sha256": canonical_digest(files),
    }


def validate_evidence_inventory(inventory, run_root):
    """Re-enumerate and rehash raw private evidence from the supplied run root."""
    try:
        expected = build_evidence_inventory(run_root)
    except (FinalAcceptanceError, OSError) as exc:
        return [str(exc)]
    if inventory != expected:
        return ["private raw evidence inventory does not reproduce exactly"]
    required_paths = {
        "logs/normal_pipeline.stdout.log",
        "logs/normal_pipeline.stderr.log",
        "logs/regression.stdout.log",
        "logs/regression.stderr.log",
        "regression/regression_report.json",
    }
    actual = {item["path"] for item in inventory["files"]}
    if not required_paths <= actual:
        return ["private raw evidence inventory is missing required run evidence"]
    if not any(path.startswith("normal_pipeline/") for path in actual):
        return ["private raw evidence inventory has no normal pipeline artifacts"]
    return []


def _evidence_log_paths(label):
    safe = re.sub(r"[^a-zA-Z0-9]+", "_", label).strip("_").lower()
    return (
        f"logs/{safe}.stdout.log",
        f"logs/{safe}.stderr.log",
    )


def _inventory_map(inventory):
    return {item["path"]: item for item in inventory.get("files", [])}


def _evidence_file(run_root, relative):
    run_root = Path(run_root).resolve()
    path = (run_root / relative).resolve()
    try:
        path.relative_to(run_root)
    except ValueError as exc:
        raise FinalAcceptanceError("private evidence path leaves its run root") from exc
    if not path.is_file() or path.is_symlink():
        raise FinalAcceptanceError(f"private evidence file is missing: {relative}")
    return path


def _match_recorded_log_digests(record, label, inventory, run_root, errors):
    inventory_by_path = _inventory_map(inventory)
    for field, relative in zip(
        ("stdout_sha256", "stderr_sha256"), _evidence_log_paths(label)
    ):
        item = inventory_by_path.get(relative)
        if item is None:
            errors.append(f"raw command log is missing: {relative}")
            continue
        try:
            digest = file_sha256(_evidence_file(run_root, relative))
        except FinalAcceptanceError as exc:
            errors.append(str(exc))
            continue
        if item.get("sha256") != digest or record.get(field) != digest:
            errors.append(f"recorded command digest differs from {relative}")


def _parse_unittest_logs(run_root, index):
    stdout_path, stderr_path = _evidence_log_paths(f"tests_{index}")
    text = (
        _evidence_file(run_root, stdout_path).read_text(encoding="utf-8")
        + "\n"
        + _evidence_file(run_root, stderr_path).read_text(encoding="utf-8")
    )

    def count(pattern, default=0):
        match = pattern.search(text)
        return int(match.group(1)) if match else default

    return {
        "tests_run": count(TEST_COUNT),
        "failures": count(FAILURE_COUNT),
        "errors": count(ERROR_COUNT),
        "skipped": count(SKIPPED_COUNT),
    }


def validate_semantic_evidence(document, run_root, contract):
    """Link every manifest summary to the exact inventoried raw evidence."""
    errors = []
    inventory = document.get("evidence_inventory") or {}
    for item in document.get("validations") or []:
        if isinstance(item, dict) and isinstance(item.get("module"), str):
            _match_recorded_log_digests(
                item, f"validator_{item['module']}", inventory, run_root, errors
            )
    compilation = document.get("python_compilation") or {}
    _match_recorded_log_digests(
        compilation, "python_compilation", inventory, run_root, errors
    )
    for index, item in enumerate(document.get("tests") or [], start=1):
        if not isinstance(item, dict):
            continue
        _match_recorded_log_digests(
            item, f"tests_{index}", inventory, run_root, errors
        )
        try:
            parsed = _parse_unittest_logs(run_root, index)
        except (FinalAcceptanceError, OSError, UnicodeDecodeError) as exc:
            errors.append(f"cannot reparse test evidence: {exc}")
        else:
            for field, expected in parsed.items():
                if item.get(field) != expected:
                    errors.append(
                        f"test {index} {field} differs from its raw unittest log"
                    )

    pipeline = document.get("normal_pipeline") or {}
    pipeline_log_record = {
        "stdout_sha256": pipeline.get("process_stdout_sha256"),
        "stderr_sha256": pipeline.get("process_stderr_sha256"),
    }
    _match_recorded_log_digests(
        pipeline_log_record, "normal_pipeline", inventory, run_root, errors
    )
    regression = pipeline.get("regression") or {}
    _match_recorded_log_digests(
        regression, "regression", inventory, run_root, errors
    )
    try:
        regression_path = _evidence_file(
            run_root, "regression/regression_report.json"
        )
        regression_report = _read_json(regression_path)
    except FinalAcceptanceError as exc:
        errors.append(str(exc))
        regression_report = {}
    else:
        if regression.get("report_sha256") != file_sha256(regression_path):
            errors.append("regression report checksum differs from raw evidence")
    if regression.get("process_exit_code") != 0:
        errors.append("raw regression process did not pass")

    output_dir = Path(run_root) / "normal_pipeline" / str(pipeline.get("run_id", ""))
    recomputed, pipeline_errors = analyze_pipeline_output(
        output_dir, pipeline.get("run_id"), regression_report, contract
    )
    errors.extend(f"raw pipeline reanalysis: {item}" for item in pipeline_errors)
    derived_fields = {
        "status", "run_id", "fixture_id", "caffeinate_used", "configuration",
        "pipeline_version", "git_commit", "source_tree_sha256", "stage_count",
        "stages", "required_artifact_count", "optional_artifact_count",
        "missing_artifacts", "unexpected_artifacts", "enrichment",
        "verification_status", "duration_s",
    }
    for field in derived_fields:
        if pipeline.get(field) != recomputed.get(field):
            errors.append(f"normal pipeline {field} differs from raw artifact reanalysis")
    recomputed_regression = recomputed.get("regression") or {}
    for field in ("status", "fixture_id", "checks_passed"):
        if regression.get(field) != recomputed_regression.get(field):
            errors.append(f"regression {field} differs from raw report reanalysis")

    runtime = runtime_output_leakage(output_dir, contract)
    leakage = document.get("leakage_checks") or {}
    for field in (
        "forbidden_filename_matches", "forbidden_key_matches",
        "forbidden_content_matches", "unreadable_artifacts",
    ):
        if leakage.get(field) != runtime.get(field):
            errors.append(f"runtime leakage {field} differs from raw artifacts")
    static = static_pipeline_leakage(contract)
    for field in (
        "pipeline_import_matches", "dynamic_import_or_literal_matches",
        "stage_or_output_matches",
    ):
        if leakage.get(field) != static.get(field):
            errors.append(f"static leakage {field} differs from current pipeline")
    expected_status = (
        "pass" if runtime.get("status") == static.get("status") == "pass"
        else "fail"
    )
    if leakage.get("status") != expected_status:
        errors.append("combined leakage status differs from recomputed evidence")
    return errors


def _normalized(value):
    return re.sub(r"[^a-z0-9]+", "_", str(value).casefold()).strip("_")


def static_pipeline_leakage(contract):
    """AST-scan normal pipeline imports and planned stages for Item 22 leakage."""
    import_matches = []
    dynamic_matches = []
    pipeline_root = REPOSITORY_ROOT / "pipeline"
    content_tokens = contract["repository_acceptance_policy"][
        "forbidden_strong_content_tokens"
    ]
    for path in sorted(pipeline_root.rglob("*.py")):
        relative = str(path.relative_to(REPOSITORY_ROOT))
        source = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source, filename=relative)
        except SyntaxError as exc:
            import_matches.append({"file": relative, "reason": f"syntax_error:{exc.lineno}"})
            continue
        for node in ast.walk(tree):
            modules = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [node.module or ""]
            for module in modules:
                if module == "speech_sound_patterns" or module.startswith(
                    "speech_sound_patterns."
                ):
                    import_matches.append({"file": relative, "module": module})
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                normalized = _normalized(node.value)
                for token in content_tokens:
                    if _normalized(token) in normalized:
                        dynamic_matches.append({"file": relative, "token": token})

    from pipeline.recording_modes import build_stage_plan

    stage_1, later = build_stage_plan("conversation", 2, ["history.py"])
    forbidden = contract["repository_acceptance_policy"][
        "forbidden_normalized_output_keys_or_filenames"
    ]
    stage_matches = []
    for label, command, required, optional in stage_1 + later:
        for value in [label, *command, *required, *optional]:
            normalized = _normalized(value)
            for token in forbidden:
                if _normalized(token) in normalized:
                    stage_matches.append({"value": value, "token": token})
    return {
        "status": "pass" if not (
            import_matches or dynamic_matches or stage_matches
        ) else "fail",
        "pipeline_import_matches": import_matches,
        "dynamic_import_or_literal_matches": dynamic_matches,
        "stage_or_output_matches": stage_matches,
    }


def _walk_json_keys(value, prefix=""):
    if isinstance(value, dict):
        for key, child in value.items():
            location = f"{prefix}.{key}" if prefix else str(key)
            yield location, key
            yield from _walk_json_keys(child, location)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_json_keys(child, f"{prefix}[{index}]")


def _walk_strings(value, prefix=""):
    if isinstance(value, dict):
        for key, child in value.items():
            location = f"{prefix}.{key}" if prefix else str(key)
            if key == "output_dir":
                continue
            yield from _walk_strings(child, location)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_strings(child, f"{prefix}[{index}]")
    elif isinstance(value, str):
        yield prefix, value


def runtime_output_leakage(output_dir, contract):
    """Scan one isolated normal-pipeline output without exposing matched text."""
    output_dir = Path(output_dir)
    forbidden = contract["repository_acceptance_policy"][
        "forbidden_normalized_output_keys_or_filenames"
    ]
    strong = contract["repository_acceptance_policy"][
        "forbidden_strong_content_tokens"
    ]
    filename_matches = []
    key_matches = []
    content_matches = []
    unreadable = []
    for path in sorted(output_dir.rglob("*")):
        relative = str(path.relative_to(output_dir))
        normalized_name = _normalized(relative)
        for token in forbidden:
            if _normalized(token) in normalized_name:
                filename_matches.append({"path": relative, "token": token})
        if not path.is_file() or path.is_symlink():
            continue
        if path.suffix == ".json":
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                unreadable.append(relative)
                continue
            for location, key in _walk_json_keys(document):
                normalized_key = _normalized(key)
                for token in forbidden:
                    if _normalized(token) in normalized_key:
                        key_matches.append({
                            "path": relative, "location": location,
                            "token": token,
                        })
            strings = _walk_strings(document)
        else:
            try:
                strings = [("text", path.read_text(encoding="utf-8"))]
            except (OSError, UnicodeDecodeError):
                if path.name in {
                    "master_preview.txt", "evaluation.md", "verification.md"
                }:
                    unreadable.append(relative)
                continue
        for location, value in strings:
            normalized_value = _normalized(value)
            for token in strong:
                if _normalized(token) in normalized_value:
                    content_matches.append({
                        "path": relative, "location": location,
                        "token": token,
                    })
    return {
        "status": "pass" if not (
            filename_matches or key_matches or content_matches or unreadable
        ) else "fail",
        "forbidden_filename_matches": filename_matches,
        "forbidden_key_matches": key_matches,
        "forbidden_content_matches": content_matches,
        "unreadable_artifacts": unreadable,
    }


def _expected_stage_records():
    from pipeline.recording_modes import build_stage_plan

    stage_1, later = build_stage_plan("conversation", 2, ["history.py"])
    return [
        {
            "label": label,
            "script": command[0],
            "arguments": command[1:],
        }
        for label, command, _, _ in stage_1 + later
    ]


def analyze_pipeline_output(output_dir, run_id, regression_report, contract):
    """Validate a completed isolated conversation run and return safe facts."""
    errors = []
    output_dir = Path(output_dir).resolve()
    policy = contract["repository_acceptance_policy"]["normal_pipeline"]
    required = set(policy["required_artifacts"])
    optional = set(policy["optional_artifacts"])
    actual = set()
    if not output_dir.is_dir():
        return {}, ["normal pipeline output directory is missing"]
    for path in output_dir.iterdir():
        actual.add(path.name)
        if path.is_symlink() or not path.is_file():
            errors.append(f"normal pipeline output contains unsafe entry {path.name}")
        elif path.stat().st_size == 0:
            errors.append(f"normal pipeline artifact is empty: {path.name}")
    missing = sorted(required - actual)
    unexpected = sorted(actual - required - optional)
    if missing:
        errors.append("normal pipeline is missing required artifacts")
    if unexpected:
        errors.append("normal pipeline produced unexpected artifacts")

    documents = {}
    for name in sorted((required | optional) & actual):
        if name.endswith(".json"):
            try:
                documents[name] = _read_json(output_dir / name)
            except FinalAcceptanceError:
                errors.append(f"normal pipeline JSON is unreadable: {name}")

    manifest = documents.get("run_manifest.json") or {}
    if manifest.get("run_id") != run_id:
        errors.append("normal pipeline run id changed")
    if manifest.get("status") != "complete":
        errors.append("normal pipeline manifest is not complete")
    if Path(str(manifest.get("output_dir", ""))).resolve(strict=False) != output_dir:
        errors.append("normal pipeline manifest output path changed")
    expected_stages = _expected_stage_records()
    stages = manifest.get("stages") or {}
    safe_stages = []
    if len(stages) != policy["expected_stage_count"]:
        errors.append("normal pipeline stage count changed")
    for expected in expected_stages:
        stage = stages.get(expected["label"])
        if not isinstance(stage, dict):
            errors.append(f"normal pipeline stage is missing: {expected['label']}")
            continue
        if stage.get("status") != "complete":
            errors.append(f"normal pipeline stage failed: {expected['label']}")
        if stage.get("script") != expected["script"]:
            errors.append(f"normal pipeline stage script changed: {expected['label']}")
        if stage.get("arguments") != expected["arguments"]:
            errors.append(f"normal pipeline stage arguments changed: {expected['label']}")
        safe_stages.append({
            "label": expected["label"],
            "script": stage.get("script"),
            "arguments": copy.deepcopy(stage.get("arguments")),
            "status": stage.get("status"),
        })
    history = stages.get("History + progress tracking") or {}
    if history.get("arguments") != []:
        errors.append("normal pipeline history stage received an argument")

    completed = set(manifest.get("completed_outputs") or [])
    if not required <= completed:
        errors.append("normal pipeline manifest did not complete every required artifact")
    for name in optional & actual:
        if name not in completed:
            errors.append(f"optional artifact was not declared complete: {name}")

    provenance = manifest.get("provenance") or {}
    configuration = (provenance.get("run") or {}).get("configuration") or {}
    expected_configuration = {
        "recording_mode_requested": "conversation",
        "recording_mode": "conversation",
        "speakers_expected": 2,
        "transcription_speakers_expected": 2,
        "diarization_speakers_expected": 2,
        "history_speaker_label": None,
        "isolated_output": True,
        "quality_policy": "coaching",
        "long_audio_approved": False,
        "session_context_reference": None,
    }
    if configuration != expected_configuration:
        errors.append("normal pipeline run configuration changed")
    if (provenance.get("run") or {}).get("status") != "complete":
        errors.append("normal pipeline provenance is not complete")
    master = documents.get("master.json") or {}
    master_provenance = (master.get("meta") or {}).get("provenance")
    if master_provenance != provenance:
        errors.append("master and manifest provenance differ")

    enrichment = (master.get("meta") or {}).get("enrichment_status") or {}
    safe_categories = set(policy["safe_remote_error_categories"])
    safe_enrichment = {}
    any_degraded = False
    for stage_name in ("referee", "listener", "evaluator"):
        status = enrichment.get(stage_name) or {}
        state = status.get("status")
        attempts = status.get("attempts")
        category = status.get("error_category")
        if state == "complete":
            if attempts not in (1, 2) or category is not None:
                errors.append(f"{stage_name} completed with an invalid status record")
        elif state == "unavailable":
            any_degraded = True
            if attempts != 2 or category not in safe_categories:
                errors.append(f"{stage_name} degraded outside the safe contract")
        else:
            errors.append(f"{stage_name} did not complete or degrade safely")
        safe_enrichment[stage_name] = {
            "status": state,
            "attempts": attempts,
            "model_id": status.get("model_id"),
            "error_category": category,
        }

    if safe_enrichment.get("listener", {}).get("status") == "unavailable":
        if {"listener.json", "audit.md"} & actual:
            errors.append("unavailable listener left optional listener artifacts")
        if master.get("notable_moments") not in (None, []):
            errors.append("unavailable listener left notable moments")

    verification = documents.get("verification.json") or {}
    evaluator = safe_enrichment.get("evaluator") or {}
    if evaluator.get("status") == "complete":
        if verification.get("status") != "pass":
            errors.append("completed evaluator did not produce passing verification")
    elif evaluator.get("status") == "unavailable":
        if (
            verification.get("status") != "unavailable"
            or verification.get("error_category") != evaluator.get("error_category")
        ):
            errors.append("unavailable evaluator and verification disagree")
        claims = documents.get("evaluation_claims.json") or {}
        if claims.get("status") != "unavailable" or claims.get("claims") not in ([], None):
            errors.append("unavailable evaluator left coaching claims")
    if verification.get("status") == "fail":
        errors.append("verification explicitly failed")

    if not isinstance(regression_report, dict) or regression_report.get("status") != "pass":
        errors.append("independent regression report did not pass")
        regression_checks = 0
    else:
        real = next(
            (item for item in regression_report.get("truth_results", [])
             if item.get("fixture_id") == policy["fixture_id"]),
            None,
        )
        if not real or real.get("status") != "pass":
            errors.append("real conversation regression fixture did not pass")
            regression_checks = 0
        else:
            regression_checks = sum(
                int(metric.get("denominator") or 0)
                for metric in real.get("metrics", {}).values()
            )

    source = (provenance.get("pipeline") or {}).get("source") or {}
    record = {
        "status": (
            "pass_with_safe_remote_degradation" if any_degraded else "pass"
        ),
        "run_id": run_id,
        "fixture_id": policy["fixture_id"],
        "process_exit_code": 0,
        "caffeinate_used": True,
        "configuration": {
            "mode": "conversation",
            "speakers": 2,
            "isolated_run": True,
            "me": None,
            "session_context": None,
        },
        "pipeline_version": (provenance.get("pipeline") or {}).get("version"),
        "git_commit": source.get("git_commit"),
        "source_tree_sha256": source.get("source_tree_sha256"),
        "stage_count": len(stages),
        "stages": safe_stages,
        "required_artifact_count": len(required),
        "optional_artifact_count": len(optional & actual),
        "missing_artifacts": missing,
        "unexpected_artifacts": unexpected,
        "regression": {
            "status": regression_report.get("status")
            if isinstance(regression_report, dict) else "fail",
            "fixture_id": policy["fixture_id"],
            "checks_passed": regression_checks,
        },
        "enrichment": safe_enrichment,
        "verification_status": verification.get("status"),
        "duration_s": (provenance.get("run") or {}).get("duration_s"),
    }
    if errors:
        record["status"] = "fail"
    return record, errors


def _validate_private_manifest(document, *, contract=None, evidence_root=None):
    """Validate private evidence without opening any held-out source."""
    contract = contract or load_final_contract()
    errors = []
    if not _required_fields(
        document, PRIVATE_MANIFEST_FIELDS, "private acceptance manifest", errors,
        exact=True,
    ):
        return errors
    exact = {
        "schema_version": "1.0.0",
        "manifest_id": "speech_sound_patterns_final_acceptance_evidence_v1",
        "manifest_version": "1.0.0",
        "checkpoint": "22H",
        "status": "acceptance_complete",
    }
    for field, expected in exact.items():
        if document.get(field) != expected:
            errors.append(f"private acceptance manifest {field} changed")
    if document.get("contract") != {
        "path": CONTRACT_PATH.name,
        "sha256": CONTRACT_SHA256,
        "version": "1.0.0",
    }:
        errors.append("private acceptance contract binding changed")

    repository = document.get("repository") or {}
    if set(repository) != {
        "git_commit", "working_tree_dirty", "source_tree_sha256",
        "acceptance_source_sha256", "started_at_utc", "completed_at_utc",
        "acceptance_python", "public_repository_before_sha256",
        "public_repository_after_sha256",
    }:
        errors.append("repository evidence fields changed")
    if not isinstance(repository.get("git_commit"), str) or not GIT_REVISION.fullmatch(
        repository["git_commit"]
    ):
        errors.append("repository.git_commit is invalid")
    for field in ("source_tree_sha256", "acceptance_source_sha256"):
        if not isinstance(repository.get(field), str) or not HEX_64.fullmatch(
            repository[field]
        ):
            errors.append(f"repository.{field} is invalid")
    if not isinstance(repository.get("working_tree_dirty"), bool):
        errors.append("repository.working_tree_dirty must be boolean")
    for field in ("started_at_utc", "completed_at_utc"):
        if not isinstance(repository.get(field), str) or not repository[field]:
            errors.append(f"repository.{field} is invalid")
    python = repository.get("acceptance_python") or {}
    if set(python) != {
        "command_name", "implementation", "version", "executable_name",
        "executable_sha256",
    }:
        errors.append("acceptance Python identity fields changed")
    if python.get("command_name") != "acceptance_python":
        errors.append("acceptance Python command name changed")
    for field in ("implementation", "version", "executable_name"):
        if not isinstance(python.get(field), str) or not python[field]:
            errors.append(f"acceptance Python {field} is invalid")
    if not isinstance(python.get("executable_sha256"), str) or not HEX_64.fullmatch(
        python.get("executable_sha256", "")
    ):
        errors.append("acceptance Python executable checksum is invalid")
    for field in (
        "public_repository_before_sha256", "public_repository_after_sha256",
    ):
        if not isinstance(repository.get(field), str) or not HEX_64.fullmatch(
            repository.get(field, "")
        ):
            errors.append(f"repository.{field} is invalid")
    if repository.get("public_repository_before_sha256") != repository.get(
        "public_repository_after_sha256"
    ):
        errors.append("public repository changed during acceptance")

    held = document.get("held_out_audit") or {}
    required_held = {
        "status", "resolution", "access_audit_scope",
        "private_assignment_files_opened", "participant_identities_read",
        "labels_read", "audio_files_read", "derived_rows_read",
        "local_model_runs", "provider_transmissions",
    }
    if set(held) != required_held:
        errors.append("held-out audit fields changed")
    if held.get("status") != "sealed_no_access":
        errors.append("held-out audit must remain sealed_no_access")
    if held.get("resolution") != "held_out_remains_sealed_no_evaluation":
        errors.append("held-out audit resolution changed")
    for field in required_held - {"status", "resolution", "access_audit_scope"}:
        if held.get(field) != 0:
            errors.append(f"held_out_audit.{field} must be zero")
    if held.get("access_audit_scope") != (
        "procedure_and_code_path_without_operating_system_file_access_audit"
    ):
        errors.append("held-out access audit scope must remain explicit")

    validators = document.get("validations")
    required_modules = contract["repository_acceptance_policy"][
        "required_validators"
    ]
    if not isinstance(validators, list):
        errors.append("validations must be a list")
    else:
        if [item.get("module") for item in validators if isinstance(item, dict)] != required_modules:
            errors.append("required validator order or membership changed")
        for item in validators:
            if not isinstance(item, dict) or set(item) != {
                "module", "command", "status", "exit_code", "duration_s",
                "stdout_sha256", "stderr_sha256",
            }:
                errors.append("validator evidence fields changed")
                continue
            if item.get("status") != "pass" or item.get("exit_code") != 0:
                errors.append(f"validator did not pass: {item.get('module')}")
            module = item.get("module")
            expected_command = f"acceptance_python -m {module}"
            if module == "speech_sound_patterns.validate_final_acceptance":
                expected_command += " --contract-only"
            if item.get("command") != expected_command:
                errors.append(f"validator command changed: {module}")
            for field in ("stdout_sha256", "stderr_sha256"):
                if not isinstance(item.get(field), str) or not HEX_64.fullmatch(item[field]):
                    errors.append(f"validator {field} is invalid")
            if not _is_number(item.get("duration_s")) or item["duration_s"] < 0:
                errors.append("validator duration is invalid")

    compile_record = document.get("python_compilation") or {}
    if set(compile_record) != {
        "command", "roots", "status", "exit_code", "duration_s",
        "stdout_sha256", "stderr_sha256",
    }:
        errors.append("Python compilation evidence fields changed")
    if compile_record.get("status") != "pass" or compile_record.get("exit_code") != 0:
        errors.append("Python compilation did not pass")
    if compile_record.get("roots") != contract["repository_acceptance_policy"][
        "python_compile_roots"
    ]:
        errors.append("Python compilation roots changed")
    if compile_record.get("command") != (
        "acceptance_python -m compileall -q "
        + " ".join(contract["repository_acceptance_policy"]["python_compile_roots"])
    ):
        errors.append("Python compilation command changed")
    if not _is_number(compile_record.get("duration_s")) or (
        compile_record.get("duration_s", -1) < 0
    ):
        errors.append("Python compilation duration is invalid")
    for field in ("stdout_sha256", "stderr_sha256"):
        if not isinstance(compile_record.get(field), str) or not HEX_64.fullmatch(
            compile_record[field]
        ):
            errors.append(f"Python compilation {field} is invalid")

    tests = document.get("tests")
    required_commands = contract["repository_acceptance_policy"][
        "required_test_commands"
    ]
    if not isinstance(tests, list):
        errors.append("tests must be a list")
    else:
        if [item.get("command") for item in tests if isinstance(item, dict)] != required_commands:
            errors.append("required test command order or membership changed")
        for item in tests:
            if not isinstance(item, dict) or set(item) != {
                "command", "status", "exit_code", "duration_s", "tests_run",
                "failures", "errors", "skipped", "stdout_sha256",
                "stderr_sha256",
            }:
                errors.append("test evidence fields changed")
                continue
            if (
                item.get("status") != "pass"
                or item.get("exit_code") != 0
                or not isinstance(item.get("tests_run"), int)
                or isinstance(item.get("tests_run"), bool)
                or item.get("tests_run", 0) <= 0
                or item.get("failures") != 0
                or item.get("errors") != 0
            ):
                errors.append(f"test command did not pass: {item.get('command')}")
                continue
            if item["tests_run"] < contract["repository_acceptance_policy"][
                "required_test_minimums"
            ][item["command"]]:
                errors.append(f"test count fell below frozen minimum: {item['command']}")
            if item.get("skipped") != contract["repository_acceptance_policy"][
                "maximum_skipped_tests_per_command"
            ]:
                errors.append(f"test command skipped tests: {item['command']}")
            if not _is_number(item.get("duration_s")) or item["duration_s"] < 0:
                errors.append("test duration is invalid")
            for field in ("stdout_sha256", "stderr_sha256"):
                if not isinstance(item.get(field), str) or not HEX_64.fullmatch(
                    item[field]
                ):
                    errors.append(f"test {field} is invalid")

    owner = document.get("owner_functional_integration") or {}
    if set(owner) != {
        "status", "task_matched_recording_available", "used_for_selection",
        "used_for_accuracy", "used_for_fairness", "external_transfer",
        "private_artifact_committed",
    }:
        errors.append("owner functional integration evidence fields changed")
    allowed_owner = set(contract["owner_integration_policy"]["allowed_statuses"])
    if owner.get("status") not in allowed_owner:
        errors.append("owner functional integration status is invalid")
    expected_owner_flags = {
        "task_matched_recording_available": (
            owner.get("status") == "performed_private_manifest_backed"
        ),
        "used_for_selection": False,
        "used_for_accuracy": False,
        "used_for_fairness": False,
        "external_transfer": False,
        "private_artifact_committed": False,
    }
    for field, expected in expected_owner_flags.items():
        if owner.get(field) is not expected:
            errors.append(f"owner_functional_integration.{field} changed")

    pipeline = document.get("normal_pipeline") or {}
    if set(pipeline) != {
        "status", "run_id", "fixture_id", "process_exit_code",
        "caffeinate_used", "configuration", "pipeline_version", "git_commit",
        "source_tree_sha256", "stage_count", "stages",
        "required_artifact_count", "optional_artifact_count",
        "missing_artifacts", "unexpected_artifacts", "regression",
        "enrichment", "verification_status", "duration_s", "process_duration_s",
        "process_stdout_sha256", "process_stderr_sha256",
    }:
        errors.append("normal pipeline evidence fields changed")
    if pipeline.get("status") not in {"pass", "pass_with_safe_remote_degradation"}:
        errors.append("normal pipeline acceptance did not pass")
    if pipeline.get("process_exit_code") != 0:
        errors.append("normal pipeline process failed")
    for field in ("process_stdout_sha256", "process_stderr_sha256"):
        if not isinstance(pipeline.get(field), str) or not HEX_64.fullmatch(
            pipeline.get(field, "")
        ):
            errors.append(f"normal pipeline {field} is invalid")
    if pipeline.get("caffeinate_used") is not True:
        errors.append("normal pipeline did not use caffeinate")
    if pipeline.get("configuration") != {
        "mode": "conversation",
        "speakers": 2,
        "isolated_run": True,
        "me": None,
        "session_context": None,
    }:
        errors.append("normal pipeline acceptance configuration changed")
    if pipeline.get("stage_count") != 14:
        errors.append("normal pipeline acceptance stage count changed")
    expected_stages = [
        {**stage, "status": "complete"} for stage in _expected_stage_records()
    ]
    if pipeline.get("stages") != expected_stages:
        errors.append("normal pipeline stage evidence changed")
    if pipeline.get("missing_artifacts") != []:
        errors.append("normal pipeline acceptance is missing artifacts")
    if pipeline.get("unexpected_artifacts") != []:
        errors.append("normal pipeline acceptance has unexpected artifacts")
    expected_required_count = len(contract["repository_acceptance_policy"][
        "normal_pipeline"
    ]["required_artifacts"])
    if pipeline.get("required_artifact_count") != expected_required_count:
        errors.append("normal pipeline required artifact count changed")
    optional_count = pipeline.get("optional_artifact_count")
    if not isinstance(optional_count, int) or isinstance(optional_count, bool) or not (
        0 <= optional_count <= len(contract["repository_acceptance_policy"][
            "normal_pipeline"
        ]["optional_artifacts"])
    ):
        errors.append("normal pipeline optional artifact count is invalid")
    if (pipeline.get("regression") or {}).get("status") != "pass":
        errors.append("normal pipeline regression did not pass")
    if pipeline.get("regression") != {
        "status": "pass",
        "fixture_id": contract["repository_acceptance_policy"][
            "normal_pipeline"
        ]["fixture_id"],
        "checks_passed": (pipeline.get("regression") or {}).get("checks_passed"),
        "process_exit_code": 0,
        "stdout_sha256": (pipeline.get("regression") or {}).get("stdout_sha256"),
        "stderr_sha256": (pipeline.get("regression") or {}).get("stderr_sha256"),
        "report_sha256": (pipeline.get("regression") or {}).get("report_sha256"),
    }:
        errors.append("normal pipeline regression evidence fields changed")
    if not isinstance((pipeline.get("regression") or {}).get("checks_passed"), int) or (
        (pipeline.get("regression") or {}).get("checks_passed", 0) <= 0
    ):
        errors.append("normal pipeline regression check count is invalid")
    for field in ("stdout_sha256", "stderr_sha256", "report_sha256"):
        value = (pipeline.get("regression") or {}).get(field)
        if not isinstance(value, str) or not HEX_64.fullmatch(value):
            errors.append(f"normal pipeline regression {field} is invalid")
    if pipeline.get("verification_status") not in {"pass", "unavailable"}:
        errors.append("normal pipeline verification did not pass or degrade safely")
    if not isinstance(pipeline.get("run_id"), str) or not RUN_ID.fullmatch(
        pipeline["run_id"]
    ):
        errors.append("normal pipeline run id is invalid")
    if not isinstance(pipeline.get("git_commit"), str) or not GIT_REVISION.fullmatch(
        pipeline["git_commit"]
    ):
        errors.append("normal pipeline git_commit is invalid")
    if not isinstance(pipeline.get("source_tree_sha256"), str) or not HEX_64.fullmatch(
        pipeline["source_tree_sha256"]
    ):
        errors.append("normal pipeline source_tree_sha256 is invalid")
    if pipeline.get("git_commit") != repository.get("git_commit"):
        errors.append("normal pipeline Git revision differs from acceptance")
    if pipeline.get("source_tree_sha256") != repository.get("source_tree_sha256"):
        errors.append("normal pipeline source tree differs from acceptance")
    baseline = contract["repository_acceptance_policy"]["normal_pipeline"]
    if pipeline.get("git_commit") != baseline["frozen_pre_22h_git_commit"]:
        errors.append("normal pipeline Git revision differs from frozen baseline")
    if pipeline.get("source_tree_sha256") != baseline[
        "frozen_pre_22h_active_source_tree_sha256"
    ]:
        errors.append("normal pipeline active source differs from frozen baseline")
    if pipeline.get("pipeline_version") != baseline[
        "frozen_pre_22h_pipeline_version"
    ]:
        errors.append("normal pipeline version differs from frozen baseline")
    if not _is_number(pipeline.get("duration_s")) or pipeline.get("duration_s", -1) < 0:
        errors.append("normal pipeline provenance duration is invalid")
    if not _is_number(pipeline.get("process_duration_s")) or (
        pipeline.get("process_duration_s", -1) < 0
    ):
        errors.append("normal pipeline process duration is invalid")
    enrichment = pipeline.get("enrichment") or {}
    if set(enrichment) != {"referee", "listener", "evaluator"}:
        errors.append("normal pipeline enrichment evidence fields changed")
    for stage_name, item in enrichment.items():
        if not isinstance(item, dict) or set(item) != {
            "status", "attempts", "model_id", "error_category",
        }:
            errors.append(f"{stage_name} enrichment fields changed")
            continue
        if item.get("status") == "complete":
            if item.get("attempts") not in (1, 2) or item.get("error_category") is not None:
                errors.append(f"{stage_name} complete enrichment evidence is invalid")
        elif item.get("status") == "unavailable":
            if item.get("attempts") != 2 or item.get("error_category") not in set(
                contract["repository_acceptance_policy"]["normal_pipeline"][
                    "safe_remote_error_categories"
                ]
            ):
                errors.append(f"{stage_name} unavailable enrichment evidence is invalid")
        else:
            errors.append(f"{stage_name} enrichment status is invalid")

    protected = document.get("protected_state") or {}
    if set(protected) != {
        "before_sha256", "after_sha256", "unchanged",
        "history_unchanged", "progress_unchanged", "root_output_unchanged",
        "public_repository_unchanged",
    }:
        errors.append("protected state fields changed")
    if protected.get("before_sha256") != protected.get("after_sha256"):
        errors.append("protected state digests changed")
    for field in (
        "unchanged", "history_unchanged", "progress_unchanged",
        "root_output_unchanged", "public_repository_unchanged",
    ):
        if protected.get(field) is not True:
            errors.append(f"protected_state.{field} must be true")

    leakage = document.get("leakage_checks") or {}
    if set(leakage) != {
        "status", "pipeline_import_matches", "dynamic_import_or_literal_matches",
        "stage_or_output_matches", "forbidden_filename_matches",
        "forbidden_key_matches", "forbidden_content_matches", "unreadable_artifacts",
    }:
        errors.append("leakage evidence fields changed")
    if leakage.get("status") != "pass":
        errors.append("leakage checks did not pass")
    for field in (
        "pipeline_import_matches", "dynamic_import_or_literal_matches",
        "stage_or_output_matches", "forbidden_filename_matches",
        "forbidden_key_matches", "forbidden_content_matches",
        "unreadable_artifacts",
    ):
        if leakage.get(field) != []:
            errors.append(f"leakage_checks.{field} must be empty")
    inventory = document.get("evidence_inventory") or {}
    if set(inventory) != {
        "snapshot_complete", "file_count", "files", "inventory_sha256",
    }:
        errors.append("private evidence inventory fields changed")
    if inventory.get("snapshot_complete") is not True:
        errors.append("private evidence inventory must be complete")
    files = inventory.get("files")
    if not isinstance(files, list) or not files:
        errors.append("private evidence inventory must contain files")
    else:
        paths = []
        for item in files:
            if not isinstance(item, dict) or set(item) != {"path", "sha256", "size"}:
                errors.append("private evidence inventory file fields changed")
                continue
            path = item.get("path")
            if (
                not isinstance(path, str) or not path
                or Path(path).is_absolute() or ".." in Path(path).parts
            ):
                errors.append("private evidence inventory path is unsafe")
            paths.append(path)
            if not isinstance(item.get("sha256"), str) or not HEX_64.fullmatch(
                item.get("sha256", "")
            ):
                errors.append("private evidence inventory checksum is invalid")
            if not isinstance(item.get("size"), int) or isinstance(
                item.get("size"), bool
            ) or item.get("size", -1) < 0:
                errors.append("private evidence inventory size is invalid")
        if paths != sorted(paths) or len(paths) != len(set(paths)):
            errors.append("private evidence inventory paths are not unique and sorted")
        if inventory.get("file_count") != len(files):
            errors.append("private evidence inventory count changed")
        if inventory.get("inventory_sha256") != canonical_digest(files):
            errors.append("private evidence inventory digest changed")
    if evidence_root is not None:
        inventory_errors = validate_evidence_inventory(inventory, evidence_root)
        errors.extend(inventory_errors)
        if not inventory_errors:
            errors.extend(
                validate_semantic_evidence(document, evidence_root, contract)
            )
    return errors


def validate_private_manifest(document, *, contract=None, evidence_root=None):
    """Validate arbitrary private-manifest JSON without an uncaught exception."""
    try:
        return _validate_private_manifest(
            document, contract=contract, evidence_root=evidence_root
        )
    except Exception as exc:  # noqa: BLE001 - malformed JSON must fail closed
        return [f"private acceptance manifest is malformed: {type(exc).__name__}"]


def _unavailable_metrics(contract):
    unavailable = contract["metric_policy"]["unavailable_record"]
    return [
        {
            "metric_id": item["metric_id"],
            "truth_class": item["truth_class"],
            "availability": unavailable["availability"],
            "value": unavailable["value"],
            "numerator": unavailable["numerator"],
            "denominator": unavailable["denominator"],
            "interval_95": unavailable["interval_95"],
            "unit": item["unit"],
            "reason_code": unavailable["reason_code"],
            "must_not_be_interpreted_as_zero": unavailable[
                "must_not_be_interpreted_as_zero"
            ],
            "gate_result": unavailable["gate_result"],
        }
        for item in contract["metric_policy"]["held_out_metrics"]
    ]


def _public_historical_bindings(contract):
    historical = contract["historical_inputs"]
    return {
        "exact_file_count": len(historical["exact_files"]),
        "corpus_manifest_count": len(historical["corpus_manifest_bundle"]),
        "exact_files": copy.deepcopy(historical["exact_files"]),
        "corpus_manifest_bundle": copy.deepcopy(
            historical["corpus_manifest_bundle"]
        ),
        "historical_contract_versions_unchanged": copy.deepcopy(
            historical["historical_contract_versions_unchanged"]
        ),
    }


def build_final_report(manifest, *, contract=None):
    """Build the aggregate final report from validated private evidence."""
    contract = contract or load_final_contract()
    errors = validate_private_manifest(manifest, contract=contract)
    if errors:
        raise FinalAcceptanceError("\n".join(errors))
    pipeline = manifest["normal_pipeline"]
    leakage = manifest["leakage_checks"]
    protected = manifest["protected_state"]
    return {
        "schema_version": "1.0.0",
        "report_id": REPORT_ID,
        "report_version": REPORT_VERSION,
        "checkpoint": "22H",
        "status": REPORT_STATUS,
        "contract": {
            "path": CONTRACT_PATH.name,
            "sha256": CONTRACT_SHA256,
            "version": "1.0.0",
            "status": contract["status"],
        },
        "historical_inputs": _public_historical_bindings(contract),
        "plan_resolution": copy.deepcopy(contract["plan_resolution"]),
        "selection_outcome": {
            "decision": "no_selection",
            "candidate_system": None,
            "mapping": None,
            "feature_relation": None,
            "threshold": None,
            "provider_configuration": None,
            "repeated_relation_minimum": None,
            "possible_relation_candidate_emission_enabled": False,
            "repeated_relation_candidate_emission_enabled": False,
            "further_search_authorised": False,
        },
        "held_out_evaluation": {
            "status": "not_performed",
            "availability": "unavailable",
            "reason_code": "not_evaluated_no_selected_candidate",
            "declared_sealed_participants": {
                "adults": 26,
                "children": 24,
            },
            "access_counts": {
                "private_assignment_files_opened": 0,
                "participant_identities_read": 0,
                "labels_read": 0,
                "audio_files_read": 0,
                "derived_rows_read": 0,
                "local_model_runs": 0,
                "provider_transmissions": 0,
            },
            "access_audit_scope": manifest["held_out_audit"][
                "access_audit_scope"
            ],
            "metrics": _unavailable_metrics(contract),
            "gate_result": None,
            "must_not_be_interpreted_as_zero_pass_or_failure": True,
        },
        "historical_results_by_truth_class": copy.deepcopy(
            contract["truth_class_policy"]["required_sections"]
        ),
        "definition_of_done_evidence": copy.deepcopy(
            contract["definition_of_done_evidence"]
        ),
        "owner_functional_integration": {
            "status": manifest["owner_functional_integration"]["status"],
            "role": "functional_integration_only",
            "task_matched_recording_available": manifest[
                "owner_functional_integration"
            ]["task_matched_recording_available"],
            "used_for_selection": False,
            "used_for_accuracy": False,
            "used_for_fairness": False,
            "external_transfer": False,
            "private_artifact_committed": False,
        },
        "repository_acceptance": {
            "status": FINAL_DECISION,
            "git_commit": manifest["repository"]["git_commit"],
            "source_tree_sha256": manifest["repository"]["source_tree_sha256"],
            "acceptance_source_sha256": manifest["repository"][
                "acceptance_source_sha256"
            ],
            "acceptance_python": copy.deepcopy(
                manifest["repository"]["acceptance_python"]
            ),
            "validator_commands": len(manifest["validations"]),
            "validator_commands_passed": sum(
                item["status"] == "pass" for item in manifest["validations"]
            ),
            "python_compilation": manifest["python_compilation"]["status"],
            "test_commands": [
                {
                    "command": item["command"],
                    "status": item["status"],
                    "tests_run": item["tests_run"],
                    "failures": item["failures"],
                    "errors": item["errors"],
                    "skipped": item["skipped"],
                }
                for item in manifest["tests"]
            ],
            "normal_pipeline": {
                "status": pipeline["status"],
                "run_id": pipeline["run_id"],
                "fixture_id": pipeline["fixture_id"],
                "pipeline_version": pipeline["pipeline_version"],
                "stage_count": pipeline["stage_count"],
                "required_artifact_count": pipeline[
                    "required_artifact_count"
                ],
                "optional_artifact_count": pipeline[
                    "optional_artifact_count"
                ],
                "missing_artifact_count": len(pipeline["missing_artifacts"]),
                "unexpected_artifact_count": len(
                    pipeline["unexpected_artifacts"]
                ),
                "regression_status": pipeline["regression"]["status"],
                "regression_checks_passed": pipeline["regression"][
                    "checks_passed"
                ],
                "enrichment": copy.deepcopy(pipeline["enrichment"]),
                "verification_status": pipeline["verification_status"],
                "duration_s": pipeline["duration_s"],
                "process_duration_s": pipeline["process_duration_s"],
                "caffeinate_used": True,
                "isolated_run": True,
                "me": None,
                "session_context": None,
            },
            "protected_repository_state": {
                "unchanged": protected["unchanged"],
                "history_unchanged": protected["history_unchanged"],
                "progress_unchanged": protected["progress_unchanged"],
                "root_output_unchanged": protected["root_output_unchanged"],
                "public_repository_unchanged": protected[
                    "public_repository_unchanged"
                ],
            },
            "leakage": {
                "status": leakage["status"],
                "pipeline_import_matches": len(
                    leakage["pipeline_import_matches"]
                ),
                "dynamic_import_or_literal_matches": len(
                    leakage["dynamic_import_or_literal_matches"]
                ),
                "stage_or_output_matches": len(
                    leakage["stage_or_output_matches"]
                ),
                "forbidden_filename_matches": len(
                    leakage["forbidden_filename_matches"]
                ),
                "forbidden_key_matches": len(
                    leakage["forbidden_key_matches"]
                ),
                "forbidden_content_matches": len(
                    leakage["forbidden_content_matches"]
                ),
                "unreadable_artifacts": len(leakage["unreadable_artifacts"]),
            },
        },
        "privacy_and_distribution": {
            "aggregate_only": True,
            "private_acceptance_manifest_committed": False,
            "private_pipeline_output_committed": False,
            "private_owner_artifact_committed": False,
            "participant_or_recording_identifiers_committed": False,
            "audio_path_or_hash_committed": False,
            "transcript_or_row_level_evidence_committed": False,
            "provider_payload_committed": False,
        },
        "limitations": copy.deepcopy(contract["mandatory_limitations"]),
        "release_boundaries": copy.deepcopy(contract["release_boundaries"]),
        "engineering_decision": {
            "decision": FINAL_DECISION,
            "item_22_engineering_complete": True,
            "held_out_performance_established": False,
            "candidate_system_or_rule_selected": False,
            "normal_pipeline_behavior_changed": False,
            "scientific_release": False,
            "product_release": False,
            "next_roadmap_item_approved": False,
        },
    }


# Substrings that must never reach a published report. They are read from a
# gitignored file when one exists, so the deny list itself does not have to name
# the private material it is defending. The literal that used to sit inline here
# was the owner's recording filename, which meant the privacy check published
# the very string it existed to catch.
def _private_string_tokens():
    tokens = [".research_data/", "/users/"]
    override = REPOSITORY_ROOT / ".private-identifiers"
    if override.is_file():
        for line in override.read_text(encoding="utf-8").splitlines():
            line = line.strip().casefold()
            if line and not line.startswith("#"):
                tokens.append(line)
    return tuple(tokens)


PRIVATE_STRING_TOKENS = _private_string_tokens()


def _public_privacy_errors(value, errors, prefix="report"):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in PRIVATE_IDENTIFIER_KEYS:
                errors.append(f"{prefix} contains private key {key}")
            _public_privacy_errors(child, errors, f"{prefix}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _public_privacy_errors(child, errors, f"{prefix}[{index}]")
    elif isinstance(value, str):
        lowered = value.casefold()
        for token in PRIVATE_STRING_TOKENS:
            if token in lowered:
                errors.append(f"{prefix} contains a private path or audio identity")


def _validate_final_report(document, *, contract=None, manifest=None):
    """Validate the committed aggregate report, optionally by exact rebuild."""
    contract = contract or load_final_contract()
    errors = []
    if not _required_fields(
        document, REPORT_FIELDS, "final evidence report", errors, exact=True
    ):
        return errors
    exact = {
        "schema_version": "1.0.0",
        "report_id": REPORT_ID,
        "report_version": REPORT_VERSION,
        "checkpoint": "22H",
        "status": REPORT_STATUS,
    }
    for field, expected in exact.items():
        if document.get(field) != expected:
            errors.append(f"final evidence report {field} changed")
    if document.get("contract") != {
        "path": CONTRACT_PATH.name,
        "sha256": CONTRACT_SHA256,
        "version": "1.0.0",
        "status": contract["status"],
    }:
        errors.append("final evidence contract binding changed")
    if document.get("historical_inputs") != _public_historical_bindings(contract):
        errors.append("final evidence historical bindings changed")
    if document.get("plan_resolution") != contract["plan_resolution"]:
        errors.append("final evidence plan resolution changed")

    selection = document.get("selection_outcome") or {}
    if set(selection) != {
        "decision", "candidate_system", "mapping", "feature_relation",
        "threshold", "provider_configuration", "repeated_relation_minimum",
        "possible_relation_candidate_emission_enabled",
        "repeated_relation_candidate_emission_enabled",
        "further_search_authorised",
    }:
        errors.append("final evidence selection fields changed")
    for field in (
        "candidate_system", "mapping", "feature_relation", "threshold",
        "provider_configuration", "repeated_relation_minimum",
    ):
        if selection.get(field) is not None:
            errors.append(f"final evidence selection {field} must remain null")
    if selection.get("decision") != "no_selection":
        errors.append("final evidence selection decision changed")
    for field in (
        "possible_relation_candidate_emission_enabled",
        "repeated_relation_candidate_emission_enabled",
        "further_search_authorised",
    ):
        if selection.get(field) is not False:
            errors.append(f"final evidence selection {field} must remain false")

    held = document.get("held_out_evaluation") or {}
    if set(held) != {
        "status", "availability", "reason_code", "declared_sealed_participants",
        "access_counts", "access_audit_scope", "metrics", "gate_result",
        "must_not_be_interpreted_as_zero_pass_or_failure",
    }:
        errors.append("final held-out evidence fields changed")
    if held.get("status") != "not_performed":
        errors.append("final held-out evaluation must remain not_performed")
    if held.get("availability") != "unavailable":
        errors.append("final held-out availability must remain unavailable")
    if held.get("reason_code") != "not_evaluated_no_selected_candidate":
        errors.append("final held-out reason changed")
    if held.get("gate_result") is not None:
        errors.append("final held-out gate result must remain null")
    if held.get("metrics") != _unavailable_metrics(contract):
        errors.append("held-out unavailable metric set changed")
    if held.get("declared_sealed_participants") != {
        "adults": 26, "children": 24,
    }:
        errors.append("declared sealed participant counts changed")
    access = held.get("access_counts") or {}
    expected_access_fields = {
        "private_assignment_files_opened", "participant_identities_read",
        "labels_read", "audio_files_read", "derived_rows_read",
        "local_model_runs", "provider_transmissions",
    }
    if set(access) != expected_access_fields or any(
        value != 0 for value in access.values()
    ):
        errors.append("every held-out access count must remain zero")
    if held.get("access_audit_scope") != (
        "procedure_and_code_path_without_operating_system_file_access_audit"
    ):
        errors.append("held-out access audit scope changed")
    if held.get("must_not_be_interpreted_as_zero_pass_or_failure") is not True:
        errors.append("held-out unavailable interpretation safeguard changed")

    if document.get("historical_results_by_truth_class") != (
        contract["truth_class_policy"]["required_sections"]
    ):
        errors.append("historical truth classes were pooled or changed")
    if document.get("definition_of_done_evidence") != (
        contract["definition_of_done_evidence"]
    ):
        errors.append("definition-of-done evidence changed")
    if document.get("limitations") != contract["mandatory_limitations"]:
        errors.append("mandatory final limitations changed")
    if document.get("release_boundaries") != contract["release_boundaries"]:
        errors.append("final release boundaries changed")

    owner = document.get("owner_functional_integration") or {}
    if set(owner) != {
        "status", "role", "task_matched_recording_available",
        "used_for_selection", "used_for_accuracy", "used_for_fairness",
        "external_transfer", "private_artifact_committed",
    }:
        errors.append("public owner integration fields changed")
    if owner.get("status") not in contract["owner_integration_policy"]["allowed_statuses"]:
        errors.append("public owner integration status is invalid")
    for field in (
        "used_for_selection", "used_for_accuracy", "used_for_fairness",
        "external_transfer", "private_artifact_committed",
    ):
        if owner.get(field) is not False:
            errors.append(f"public owner integration {field} must remain false")
    if owner.get("role") != "functional_integration_only":
        errors.append("public owner integration role changed")
    if owner.get("task_matched_recording_available") is not False:
        errors.append("public owner task-matched availability changed")

    repository = document.get("repository_acceptance") or {}
    if set(repository) != {
        "status", "git_commit", "source_tree_sha256",
        "acceptance_source_sha256", "acceptance_python", "validator_commands",
        "validator_commands_passed", "python_compilation", "test_commands",
        "normal_pipeline", "protected_repository_state", "leakage",
    }:
        errors.append("public repository acceptance fields changed")
    if repository.get("status") != FINAL_DECISION:
        errors.append("repository acceptance decision changed")
    if repository.get("validator_commands") != len(
        contract["repository_acceptance_policy"]["required_validators"]
    ):
        errors.append("repository validator count changed")
    if repository.get("validator_commands_passed") != repository.get(
        "validator_commands"
    ):
        errors.append("not every repository validator passed")
    if repository.get("python_compilation") != "pass":
        errors.append("repository Python compilation did not pass")
    if not isinstance(repository.get("git_commit"), str) or not GIT_REVISION.fullmatch(
        repository.get("git_commit", "")
    ):
        errors.append("public repository Git revision is invalid")
    for field in ("source_tree_sha256", "acceptance_source_sha256"):
        if not isinstance(repository.get(field), str) or not HEX_64.fullmatch(
            repository.get(field, "")
        ):
            errors.append(f"public repository {field} is invalid")
    baseline = contract["repository_acceptance_policy"]["normal_pipeline"]
    if repository.get("git_commit") != baseline["frozen_pre_22h_git_commit"]:
        errors.append("public repository Git revision differs from frozen baseline")
    if repository.get("source_tree_sha256") != baseline[
        "frozen_pre_22h_active_source_tree_sha256"
    ]:
        errors.append("public repository source differs from frozen baseline")
    public_python = repository.get("acceptance_python") or {}
    if set(public_python) != {
        "command_name", "implementation", "version", "executable_name",
        "executable_sha256",
    }:
        errors.append("public acceptance Python identity fields changed")
    if public_python.get("command_name") != "acceptance_python":
        errors.append("public acceptance Python command name changed")
    for field in ("implementation", "version", "executable_name"):
        if not isinstance(public_python.get(field), str) or not public_python[field]:
            errors.append(f"public acceptance Python {field} is invalid")
    if not isinstance(public_python.get("executable_sha256"), str) or not HEX_64.fullmatch(
        public_python.get("executable_sha256", "")
    ):
        errors.append("public acceptance Python executable checksum is invalid")
    test_commands = repository.get("test_commands")
    required_commands = contract["repository_acceptance_policy"][
        "required_test_commands"
    ]
    if not isinstance(test_commands, list) or [
        item.get("command") for item in test_commands if isinstance(item, dict)
    ] != required_commands:
        errors.append("public test command order or membership changed")
    else:
        for item in test_commands:
            if not isinstance(item, dict) or set(item) != {
                "command", "status", "tests_run", "failures", "errors", "skipped",
            }:
                errors.append("public test evidence fields changed")
                continue
            if (
                item.get("status") != "pass" or item.get("failures") != 0
                or item.get("errors") != 0 or item.get("skipped") != 0
                or not isinstance(item.get("tests_run"), int)
                or isinstance(item.get("tests_run"), bool)
                or item["tests_run"] < contract["repository_acceptance_policy"][
                    "required_test_minimums"
                ][item["command"]]
            ):
                errors.append(f"public test command evidence is invalid: {item.get('command')}")
    pipeline = repository.get("normal_pipeline") or {}
    if set(pipeline) != {
        "status", "run_id", "fixture_id", "pipeline_version", "stage_count",
        "required_artifact_count", "optional_artifact_count",
        "missing_artifact_count", "unexpected_artifact_count",
        "regression_status", "regression_checks_passed", "enrichment",
        "verification_status", "duration_s", "process_duration_s",
        "caffeinate_used", "isolated_run", "me", "session_context",
    }:
        errors.append("public normal pipeline fields changed")
    if pipeline.get("status") not in {"pass", "pass_with_safe_remote_degradation"}:
        errors.append("public normal pipeline acceptance did not pass")
    if pipeline.get("stage_count") != 14:
        errors.append("public normal pipeline stage count changed")
    if not isinstance(pipeline.get("run_id"), str) or not RUN_ID.fullmatch(
        pipeline.get("run_id", "")
    ):
        errors.append("public normal pipeline run id is invalid")
    if pipeline.get("fixture_id") != contract["repository_acceptance_policy"][
        "normal_pipeline"
    ]["fixture_id"]:
        errors.append("public normal pipeline fixture changed")
    if pipeline.get("pipeline_version") != contract[
        "repository_acceptance_policy"
    ]["normal_pipeline"]["frozen_pre_22h_pipeline_version"]:
        errors.append("public normal pipeline version changed")
    if pipeline.get("missing_artifact_count") != 0:
        errors.append("public normal pipeline has missing artifacts")
    if pipeline.get("unexpected_artifact_count") != 0:
        errors.append("public normal pipeline has unexpected artifacts")
    if pipeline.get("required_artifact_count") != len(
        contract["repository_acceptance_policy"]["normal_pipeline"][
            "required_artifacts"
        ]
    ):
        errors.append("public normal pipeline required artifact count changed")
    optional_count = pipeline.get("optional_artifact_count")
    if not isinstance(optional_count, int) or isinstance(optional_count, bool) or not (
        0 <= optional_count <= len(contract["repository_acceptance_policy"][
            "normal_pipeline"
        ]["optional_artifacts"])
    ):
        errors.append("public normal pipeline optional artifact count is invalid")
    if pipeline.get("regression_status") != "pass":
        errors.append("public normal pipeline regression did not pass")
    if not isinstance(pipeline.get("regression_checks_passed"), int) or (
        pipeline.get("regression_checks_passed", 0) <= 0
    ):
        errors.append("public normal pipeline regression count is invalid")
    if pipeline.get("verification_status") not in {"pass", "unavailable"}:
        errors.append("public verification status is invalid")
    if pipeline.get("caffeinate_used") is not True:
        errors.append("public pipeline acceptance did not use caffeinate")
    if pipeline.get("isolated_run") is not True:
        errors.append("public pipeline acceptance was not isolated")
    if pipeline.get("me") is not None or pipeline.get("session_context") is not None:
        errors.append("public pipeline acceptance used personal longitudinal context")
    for field in ("duration_s", "process_duration_s"):
        if not _is_number(pipeline.get(field)) or pipeline.get(field, -1) < 0:
            errors.append(f"public normal pipeline {field} is invalid")
    enrichment = pipeline.get("enrichment") or {}
    if set(enrichment) != {"referee", "listener", "evaluator"}:
        errors.append("public normal pipeline enrichment fields changed")
    else:
        safe_categories = set(contract["repository_acceptance_policy"][
            "normal_pipeline"
        ]["safe_remote_error_categories"])
        for stage_name, item in enrichment.items():
            if not isinstance(item, dict) or set(item) != {
                "status", "attempts", "model_id", "error_category",
            }:
                errors.append(f"public {stage_name} enrichment fields changed")
            elif item.get("status") == "complete":
                if item.get("attempts") not in (1, 2) or item.get("error_category") is not None:
                    errors.append(f"public {stage_name} complete status is invalid")
            elif item.get("status") == "unavailable":
                if item.get("attempts") != 2 or item.get("error_category") not in safe_categories:
                    errors.append(f"public {stage_name} unavailable status is invalid")
            else:
                errors.append(f"public {stage_name} status is invalid")
    protected = repository.get("protected_repository_state") or {}
    if set(protected) != {
        "unchanged", "history_unchanged", "progress_unchanged",
        "root_output_unchanged", "public_repository_unchanged",
    } or any(value is not True for value in protected.values()):
        errors.append("protected repository state was not unchanged")
    leakage = repository.get("leakage") or {}
    expected_leakage_fields = {
        "status", "pipeline_import_matches", "dynamic_import_or_literal_matches",
        "stage_or_output_matches", "forbidden_filename_matches",
        "forbidden_key_matches", "forbidden_content_matches", "unreadable_artifacts",
    }
    if set(leakage) != expected_leakage_fields:
        errors.append("public leakage fields changed")
    if leakage.get("status") != "pass":
        errors.append("public leakage status did not pass")
    for field, value in leakage.items():
        if field != "status" and value != 0:
            errors.append(f"public leakage count {field} must be zero")

    privacy = document.get("privacy_and_distribution") or {}
    if set(privacy) != {
        "aggregate_only", "private_acceptance_manifest_committed",
        "private_pipeline_output_committed", "private_owner_artifact_committed",
        "participant_or_recording_identifiers_committed",
        "audio_path_or_hash_committed",
        "transcript_or_row_level_evidence_committed",
        "provider_payload_committed",
    }:
        errors.append("privacy and distribution fields changed")
    if privacy.get("aggregate_only") is not True:
        errors.append("final report must remain aggregate only")
    for field, value in privacy.items():
        if field != "aggregate_only" and value is not False:
            errors.append(f"privacy_and_distribution.{field} must remain false")

    decision = document.get("engineering_decision") or {}
    expected_decision = {
        "decision": FINAL_DECISION,
        "item_22_engineering_complete": True,
        "held_out_performance_established": False,
        "candidate_system_or_rule_selected": False,
        "normal_pipeline_behavior_changed": False,
        "scientific_release": False,
        "product_release": False,
        "next_roadmap_item_approved": False,
    }
    if decision != expected_decision:
        errors.append("final engineering decision changed")
    _public_privacy_errors(document, errors)

    if manifest is not None:
        manifest_errors = validate_private_manifest(manifest, contract=contract)
        errors.extend(manifest_errors)
        if not manifest_errors:
            try:
                expected = build_final_report(manifest, contract=contract)
            except FinalAcceptanceError as exc:
                errors.append(f"private manifest cannot rebuild report: {exc}")
            else:
                if document != expected:
                    errors.append("final report does not rebuild from private evidence")
    return errors


def validate_final_report(document, *, contract=None, manifest=None):
    """Validate arbitrary report JSON without an uncaught exception."""
    try:
        return _validate_final_report(
            document, contract=contract, manifest=manifest
        )
    except Exception as exc:  # noqa: BLE001 - malformed JSON must fail closed
        return [f"final evidence report is malformed: {type(exc).__name__}"]


def assert_valid_final_report(document, *, contract=None, manifest=None):
    errors = validate_final_report(document, contract=contract, manifest=manifest)
    if errors:
        raise FinalAcceptanceError("\n".join(errors))
    return document


def write_exclusive_atomic(path, payload):
    """Publish complete bytes atomically without replacing an existing file."""
    path = Path(path).resolve(strict=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise FinalAcceptanceError(f"refusing to overwrite existing output: {path}")
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temp_name, path)
        except FileExistsError as exc:
            raise FinalAcceptanceError(
                f"refusing to overwrite existing output: {path}"
            ) from exc
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def write_final_report(report, path=REPORT_PATH):
    errors = validate_final_report(report)
    if errors:
        raise FinalAcceptanceError("\n".join(errors))
    write_exclusive_atomic(path, canonical_json_bytes(report))
    return Path(path)
