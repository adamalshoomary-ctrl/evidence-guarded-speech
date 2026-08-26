"""Load and validate the speech sound pattern research contract."""

from __future__ import annotations

import copy
import json
import hashlib
import re
from pathlib import Path

from .feasibility import (
    FROZEN_SAMPLE_MANIFEST_SHA256,
    canonical_json_bytes,
    file_sha256,
    validate_safe_feasibility_report,
)
from .benchmark import (
    BENCHMARK_CONTRACT_PATH,
    BENCHMARK_REPORT_PATH,
    FROZEN_BENCHMARK_MANIFEST_SHA256,
    FROZEN_BENCHMARK_REPORT_SHA256,
    PHONE_MAP_PATH,
    validate_benchmark_contract,
    validate_phone_map,
    validate_safe_benchmark_report,
)
from .benchmark_repair import (
    FROZEN_EXPECTED_MANIFEST_SHA256,
    REPAIR_REPORT_PATH,
    validate_repair_report,
)

MODULE_ROOT = Path(__file__).parent
CONTRACT_PATH = MODULE_ROOT / "research-contract-v1.7.0.json"
PREVIOUS_CONTRACT_PATH = MODULE_ROOT / "research-contract-v1.6.0.json"
V1_5_CONTRACT_PATH = MODULE_ROOT / "research-contract-v1.5.0.json"
BASE_CONTRACT_PATH = MODULE_ROOT / "research-contract-v1.4.0.json"
SUPPORTED_SCHEMA_VERSION = "1.7.0"
FROZEN_PREVIOUS_CONTRACT_SHA256 = (
    "1541488efe1a8d1998bc8ca9b4322a7d849f670c574d1310413aabe392dde7fc"
)
FROZEN_V1_5_CONTRACT_SHA256 = (
    "d3201a24c9bac7211aef96f8f4b9a1850e0c4bd9c2161d24de0cf879b80197ac"
)
FROZEN_BASE_CONTRACT_SHA256 = (
    "046be02a8ea5c1fdc328fdf6a35078a93fcf7448d62e6208d72aa259311290ee"
)
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")

TARGET_RELATION_OUTCOMES = {
    "accepted_variant",
    "observed_substitution",
    "observed_deletion",
    "observed_insertion",
    "observed_distortion",
    "uncertain",
    "unscorable",
}
AUTOMATIC_CANDIDATE_STATES = {
    "possible_relation_candidate",
    "asr_only_disagreement",
    "candidate_system_conflict",
    "known_reference_variant",
    "insufficient_evidence",
    "unsupported",
    "unavailable",
}
REQUIRED_PRODUCT_RELEASE_BLOCKS = {
    "normal_pipeline_activation",
    "normal_coaching",
    "personal_progress",
    "ranking",
    "screening",
    "diagnosis",
    "severity",
    "treatment",
}
REQUIRED_UNAVAILABLE_FAILURES = {
    "poor_audio",
    "unsupported_language",
    "unsupported_or_unrepresented_variety",
    "unknown_intended_word",
    "missing_versioned_research_variant_set",
    "insufficient_opportunities",
    "unresolved_human_disagreement",
    "missing_required_local_model_or_version",
}
REQUIRED_VALIDATION_METRICS = {
    "phone_relation_precision_recall_and_f1_by_outcome",
    "accepted_variant_false_concern_rate",
    "asr_error_attribution_matrix",
    "false_concerns_per_scorable_opportunity",
    "abstention_and_unscorable_rate",
    "exact_same_input_repeatability",
    "repeated_human_production_reliability",
    "human_inter_and_intra_reviewer_agreement",
    "subgroup_results_with_uncertainty",
    "source_and_licence_compliance",
    "provider_incremental_value_if_compared",
    "unsupported_scope_rate",
}


class SpeechSoundResearchValidationError(ValueError):
    """Raised when the research design violates a required safety boundary."""


def _expand_v1_5(document):
    base_path = MODULE_ROOT / document["base_contract"]["path"]
    base = json.loads(base_path.read_text(encoding="utf-8"))
    merged = copy.deepcopy(base)
    updates = document["updates"]
    merged.update(
        {
            "schema_version": document["schema_version"],
            "protocol_id": document["protocol_id"],
            "protocol_version": document["protocol_version"],
            "status": document["status"],
            "contract_amendment": copy.deepcopy(document["base_contract"]),
            "local_benchmark_repair": copy.deepcopy(
                document["local_benchmark_repair"]
            ),
        }
    )
    merged["engineering_policy"]["implementation_status"] = updates[
        "engineering_implementation_status"
    ]
    merged["pattern_policy"]["threshold_status"] = updates[
        "pattern_threshold_status"
    ]
    merged["candidate_systems"]["comparison_status"] = updates[
        "candidate_comparison_status"
    ]
    merged["candidate_systems"]["planned_systems"].append(
        copy.deepcopy(updates["candidate_system_record"])
    )
    merged["validation_program"]["engineering_evaluation_status"] = updates[
        "engineering_evaluation_status"
    ]
    merged["release_policy"]["developer_offline_candidate_engineering"] = updates[
        "developer_release_status"
    ]
    return merged


def _expand_v1_6(document):
    base_path = MODULE_ROOT / document["base_contract"]["path"]
    base_document = json.loads(base_path.read_text(encoding="utf-8"))
    merged = _expand_v1_5(base_document)
    updates = document["updates"]
    merged.update(
        {
            "schema_version": document["schema_version"],
            "protocol_id": document["protocol_id"],
            "protocol_version": document["protocol_version"],
            "status": document["status"],
            "contract_amendment": copy.deepcopy(document["base_contract"]),
            "developer_candidate_extractor": copy.deepcopy(
                document["developer_candidate_extractor"]
            ),
        }
    )
    merged["engineering_policy"]["implementation_status"] = updates[
        "engineering_implementation_status"
    ]
    merged["engineering_policy"]["planned_artifact_status"] = updates[
        "planned_artifact_status"
    ]
    merged["task_policy"]["developer_research_task_status"] = updates[
        "developer_research_task_status"
    ]
    merged["pattern_policy"]["generic_repeated_relation_status"] = updates[
        "generic_repeated_relation_status"
    ]
    merged["pattern_policy"]["threshold_status"] = updates[
        "pattern_threshold_status"
    ]
    merged["candidate_systems"]["comparison_status"] = updates[
        "candidate_comparison_status"
    ]
    merged["validation_program"]["engineering_evaluation_status"] = updates[
        "engineering_evaluation_status"
    ]
    merged["release_policy"]["developer_offline_candidate_engineering"] = updates[
        "developer_release_status"
    ]
    return merged


def load_contract(path=CONTRACT_PATH):
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if document.get("schema_version") == "1.5.0":
        return _expand_v1_5(document)
    if document.get("schema_version") == "1.6.0":
        return _expand_v1_6(document)
    if document.get("schema_version") != SUPPORTED_SCHEMA_VERSION:
        return document

    base_path = MODULE_ROOT / document["base_contract"]["path"]
    base_document = json.loads(base_path.read_text(encoding="utf-8"))
    merged = _expand_v1_6(base_document)
    updates = document["updates"]
    merged.update(
        {
            "schema_version": document["schema_version"],
            "protocol_id": document["protocol_id"],
            "protocol_version": document["protocol_version"],
            "status": document["status"],
            "contract_amendment": copy.deepcopy(document["base_contract"]),
            "final_repository_acceptance": copy.deepcopy(
                document["final_repository_acceptance"]
            ),
        }
    )
    merged["engineering_policy"]["implementation_status"] = updates[
        "engineering_implementation_status"
    ]
    merged["validation_program"]["engineering_evaluation_status"] = updates[
        "engineering_evaluation_status"
    ]
    return merged


def _require_fields(value, fields, label, errors):
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return False
    missing = sorted(set(fields) - set(value))
    if missing:
        errors.append(f"{label} missing fields: {', '.join(missing)}")
        return False
    return True


def validate_contract(document):
    """Return all structural and safety errors in the research contract."""
    errors = []
    required_root = {
        "schema_version",
        "protocol_id",
        "protocol_version",
        "status",
        "language",
        "purpose",
        "engineering_policy",
        "research_sources",
        "claim_boundaries",
        "constructs",
        "task_policy",
        "evidence_model",
        "reference_truth",
        "asr_and_alignment_separation",
        "language_and_variety_policy",
        "pattern_policy",
        "consent_policy",
        "candidate_systems",
        "local_feasibility",
        "local_benchmark",
        "contract_amendment",
        "local_benchmark_repair",
        "developer_candidate_extractor",
        "final_repository_acceptance",
        "validation_program",
        "failure_policy",
        "downstream_policy",
        "release_policy",
        "out_of_scope",
        "sources",
    }
    if not _require_fields(document, required_root, "contract", errors):
        return errors

    if document["schema_version"] != SUPPORTED_SCHEMA_VERSION:
        errors.append("schema_version is unsupported")
    if not SEMVER.fullmatch(str(document["protocol_version"])):
        errors.append("protocol_version must use semantic versioning")
    if document["protocol_version"] != "1.7.0":
        errors.append("the active protocol_version must be 1.7.0")
    if document["status"] != (
        "item_22_engineering_complete_no_selection_held_out_not_performed_release_locked"
    ):
        errors.append(
            "item 22 must remain engineering complete only on the no-selection, "
            "held-out-not-performed, release-locked path"
        )
    if document["language"] != "en":
        errors.append("version 1 must remain English only")

    engineering = document["engineering_policy"]
    if _require_fields(
        engineering,
        {
            "approval_scope",
            "implementation_status",
            "normal_pipeline_activation",
            "explicit_research_command_required",
            "known_presented_stimulus_required",
            "current_solo_or_conversation_target_inference",
            "planned_artifact",
            "planned_artifact_status",
            "scientific_release_status",
            "product_release_status",
            "gpu_rental_approved",
            "allowed_initial_scope",
            "explicitly_unsupported_initial_scope",
        },
        "engineering_policy",
        errors,
    ):
        exact_values = {
            "approval_scope": "developer_only_offline_candidate_engineering",
            "implementation_status": (
                "item_22_engineering_complete_no_selection_release_locked"
            ),
            "normal_pipeline_activation": "blocked",
            "current_solo_or_conversation_target_inference": "blocked",
            "planned_artifact": "speech_sound_candidates.json",
            "planned_artifact_status": "implemented_private_developer_only",
            "scientific_release_status": "locked",
            "product_release_status": "locked",
        }
        for field, expected in exact_values.items():
            if engineering[field] != expected:
                errors.append(f"engineering_policy.{field} must remain {expected}")
        for field in (
            "explicit_research_command_required",
            "known_presented_stimulus_required",
        ):
            if engineering[field] is not True:
                errors.append(f"engineering_policy.{field} must remain true")
        if engineering["gpu_rental_approved"] is not False:
            errors.append("engineering_policy.gpu_rental_approved must remain false")
        required_unsupported = {
            "vowel_or_diphthong_judgment",
            "distortion_judgment",
            "spontaneous_or_connected_speech_target_relations",
            "named_articulation_or_phonological_patterns",
            "disorder_severity_cause_or_treatment",
        }
        if not required_unsupported.issubset(
            engineering["explicitly_unsupported_initial_scope"]
        ):
            errors.append("engineering_policy unsupported initial scope is incomplete")

    research_sources = document["research_sources"]
    if _require_fields(
        research_sources,
        {
            "source_manifest_required_before_use",
            "unmanifested_source_behavior",
            "required_manifest_fields",
            "allowed_access_states",
            "allowed_licence_states",
            "restricted_source_data_may_be_committed",
            "participant_exclusive_split_required",
            "provider_processing_requires_source_and_provider_terms",
            "owner_controls_accounts_purchases_and_terms",
            "api_credentials_location",
            "source_registry_path",
            "source_registry_status",
            "manifest_schema_path",
            "source_manifest_validator",
            "duplicate_participant_or_clip_across_splits",
            "related_sources_count_as_independent",
            "model_seen_data_count_as_independent",
            "truth_classes_may_be_pooled",
            "unknown_licence_access_or_lineage_behavior",
            "recorded_sources",
        },
        "research_sources",
        errors,
    ):
        required_true = (
            "source_manifest_required_before_use",
            "participant_exclusive_split_required",
            "provider_processing_requires_source_and_provider_terms",
            "owner_controls_accounts_purchases_and_terms",
        )
        for field in required_true:
            if research_sources[field] is not True:
                errors.append(f"research_sources.{field} must remain true")
        if research_sources["unmanifested_source_behavior"] != "blocked":
            errors.append("unmanifested research sources must remain blocked")
        if research_sources["restricted_source_data_may_be_committed"] is not False:
            errors.append("restricted source data may not be committed")
        if research_sources["api_credentials_location"] != ".env":
            errors.append("API credentials must remain in .env")
        required_manifest_fields = {
            "canonical_source",
            "version",
            "archive_checksum",
            "citation",
            "access_and_terms",
            "licence_and_commercial_use",
            "permitted_and_prohibited_roles",
            "population_and_annotation_construct",
            "participant_split",
            "lineage_and_independence",
            "candidate_model_overlap",
            "privacy_and_transfer_duties",
        }
        if not required_manifest_fields.issubset(
            research_sources["required_manifest_fields"]
        ):
            errors.append("source manifest fields are incomplete")
        allowed_access_states = {
            "access_pending",
            "available",
            "rejected",
            "unavailable",
        }
        if set(research_sources["allowed_access_states"]) != allowed_access_states:
            errors.append("research source access states must remain explicit")
        allowed_licence_states = {
            "pending_review",
            "verified_for_declared_role",
            "restricted_role_only",
            "rejected",
        }
        if set(research_sources["allowed_licence_states"]) != allowed_licence_states:
            errors.append("research source licence states must remain explicit")
        source_records = {
            item.get("source_id"): item
            for item in research_sources["recorded_sources"]
            if isinstance(item, dict)
        }
        required_source_ids = {
            "speechocean762",
            "acted_clear_speech",
            "common_phone_1_0",
            "common_voice_26_australian_english",
            "librispeech_slr12_small",
            "l2_arctic",
            "talkbank_research",
            "macquarie_australian_pronunciation_data",
            "timit_ldc93s1",
            "adam_controlled_recordings",
        }
        if not required_source_ids.issubset(source_records):
            errors.append("research_sources is missing a required recorded source")
        for source_id, record in source_records.items():
            if record.get("access_state") not in allowed_access_states:
                errors.append(
                    f"research source {source_id} has an invalid access state"
                )
            if record.get("licence_state") not in allowed_licence_states:
                errors.append(
                    f"research source {source_id} has an invalid licence state"
                )
        source_guards = {
            "speechocean762": ("may_define_acceptable_variety_truth", False),
            "acted_clear_speech": ("may_establish_population_performance", False),
            "common_phone_1_0": ("may_be_phone_relation_truth", False),
            "common_voice_26_australian_english": (
                "may_be_phone_or_australian_variant_truth",
                False,
            ),
            "librispeech_slr12_small": ("may_be_phone_production_truth", False),
            "l2_arctic": (
                "may_enter_commercial_training_or_evaluation",
                False,
            ),
            "talkbank_research": ("may_validate_adult_product", False),
            "macquarie_australian_pronunciation_data": (
                "blocks_initial_engineering",
                False,
            ),
            "timit_ldc93s1": ("blocks_initial_engineering", False),
            "adam_controlled_recordings": (
                "may_establish_population_performance",
                False,
            ),
        }
        for source_id, (field, expected) in source_guards.items():
            record = source_records.get(source_id, {})
            if record.get(field) is not expected:
                errors.append(f"research source {source_id} must preserve {field}")
        if source_records.get("adam_controlled_recordings", {}).get("planned_role") != (
            "functional_integration_only"
        ):
            errors.append("Adam recordings must remain functional integration only")
        expected_source_states = {
            "speechocean762": ("available", "verified_for_declared_role"),
            "acted_clear_speech": ("available", "verified_for_declared_role"),
            "common_phone_1_0": ("available", "verified_for_declared_role"),
            "common_voice_26_australian_english": (
                "available",
                "verified_for_declared_role",
            ),
            "librispeech_slr12_small": (
                "available",
                "verified_for_declared_role",
            ),
            "macquarie_australian_pronunciation_data": (
                "access_pending",
                "pending_review",
            ),
            "timit_ldc93s1": ("rejected", "rejected"),
            "l2_arctic": ("unavailable", "restricted_role_only"),
            "talkbank_research": ("unavailable", "restricted_role_only"),
            "adam_controlled_recordings": (
                "available",
                "verified_for_declared_role",
            ),
        }
        for source_id, expected in expected_source_states.items():
            record = source_records.get(source_id, {})
            actual = (record.get("access_state"), record.get("licence_state"))
            if actual != expected:
                errors.append(
                    f"research source {source_id} must preserve its approved state"
                )
        for source_id, record in source_records.items():
            manifest_path = record.get("manifest_path")
            if source_id == "adam_controlled_recordings":
                if manifest_path is not None:
                    errors.append("Adam recordings cannot masquerade as a public corpus")
            elif not isinstance(manifest_path, str) or not manifest_path.startswith(
                "corpus_manifests/"
            ):
                errors.append(f"research source {source_id} must name its manifest")
            if not isinstance(record.get("manifest_status"), str):
                errors.append(f"research source {source_id} must record manifest status")
        exact_source_policy = {
            "source_registry_path": "corpus_manifests/registry-v1.0.0.json",
            "source_registry_status": "validated_release_locked",
            "manifest_schema_path": (
                "corpus_manifests/corpus-manifest-schema-v1.0.0.json"
            ),
            "source_manifest_validator": (
                "python3 -m speech_sound_patterns.validate_corpora"
            ),
            "duplicate_participant_or_clip_across_splits": "blocked",
            "related_sources_count_as_independent": False,
            "model_seen_data_count_as_independent": False,
            "truth_classes_may_be_pooled": False,
            "unknown_licence_access_or_lineage_behavior": "blocked",
        }
        for field, expected in exact_source_policy.items():
            if research_sources[field] != expected:
                errors.append(f"research_sources.{field} must remain {expected}")
        common_phone = source_records.get("common_phone_1_0", {})
        if common_phone.get("independent_of_common_voice") is not False:
            errors.append("Common Phone cannot be independent of Common Voice")

    boundaries = document["claim_boundaries"]
    if _require_fields(
        boundaries,
        {
            "allowed_claim_levels",
            "forbidden_outputs",
            "asr_text_is_lexical_intent",
            "asr_is_phone_truth",
            "automatic_system_agreement_is_truth",
            "automatic_absence_establishes_typical_speech",
        },
        "claim_boundaries",
        errors,
    ):
        if boundaries["allowed_claim_levels"] != ["measured_observation"]:
            errors.append("research may create measured observations only")
        for field in (
            "asr_text_is_lexical_intent",
            "asr_is_phone_truth",
            "automatic_system_agreement_is_truth",
            "automatic_absence_establishes_typical_speech",
        ):
            if boundaries[field] is not False:
                errors.append(f"claim_boundaries.{field} must remain false")
        required_forbidden = {
            "articulation_score",
            "phonology_score",
            "accent_quality",
            "native_likeness",
            "disorder_label",
            "screening_result",
            "diagnosis",
            "severity",
            "personal_progress",
        }
        if not required_forbidden.issubset(boundaries["forbidden_outputs"]):
            errors.append("claim boundaries are missing forbidden outputs")

    tasks = document["task_policy"]
    if _require_fields(
        tasks,
        {
            "active_task",
            "active_stimulus_pack",
            "active_developer_research_task",
            "active_product_task",
            "primary_future_task",
            "primary_task_contract",
            "developer_research_task_status",
            "product_task_status",
            "developer_research_pack_may_use_versioned_open_or_licensed_variants",
            "product_task_activation_requires_professionally_reviewed_word_pack",
            "normal_pipeline_task_activation",
            "developer_research_activation_requirements",
            "elicitation_modes",
            "elicitation_modes_are_comparable",
            "cross_task_pooling",
            "repeated_productions_required",
            "pattern_minimum_opportunities",
            "pattern_minimum_rule_status",
        },
        "task_policy",
        errors,
    ):
        inactive_fields = (
            "active_task",
            "active_stimulus_pack",
            "active_developer_research_task",
            "active_product_task",
        )
        if any(tasks[field] is not None for field in inactive_fields):
            errors.append("no speech sound task or stimulus pack may be active")
        if tasks["developer_research_task_status"] != (
            "evidence_assembly_implemented_no_candidate_rule_selected"
        ):
            errors.append(
                "the developer research task may assemble evidence only, with no "
                "candidate rule selected"
            )
        if tasks["product_task_status"] != "locked":
            errors.append("the product task must remain locked")
        if (
            tasks[
                "developer_research_pack_may_use_versioned_open_or_licensed_variants"
            ]
            is not True
        ):
            errors.append(
                "developer research variants must remain versioned and licensed"
            )
        if (
            tasks[
                "product_task_activation_requires_professionally_reviewed_word_pack"
            ]
            is not True
        ):
            errors.append(
                "product activation requires a professionally reviewed word pack"
            )
        if tasks["normal_pipeline_task_activation"] != "blocked":
            errors.append("normal pipeline speech sound tasks must remain blocked")
        required_activation = {
            "validated_engineering_contract",
            "verified_source_and_licence_manifests",
            "versioned_controlled_word_research_pack",
            "explicit_research_command",
        }
        if not required_activation.issubset(
            tasks["developer_research_activation_requirements"]
        ):
            errors.append("developer research activation requirements are incomplete")
        if tasks["elicitation_modes_are_comparable"] is not False:
            errors.append("elicitation modes cannot be declared comparable")
        if tasks["cross_task_pooling"] != "blocked":
            errors.append("cross task pooling must remain blocked")
        if tasks["repeated_productions_required"] is not True:
            errors.append("research must require repeated productions")
        if tasks["pattern_minimum_opportunities"] is not None:
            errors.append("a pattern minimum cannot be invented before evidence")
        spontaneous = (tasks.get("elicitation_modes") or {}).get(
            "spontaneous_speech", {}
        )
        if spontaneous.get("intended_word_source") != "asr_forbidden":
            errors.append("ASR cannot create lexical intent in spontaneous speech")

    evidence = document["evidence_model"]
    if _require_fields(
        evidence,
        {
            "layers_kept_separate",
            "production_units",
            "target_relation_outcomes",
            "automatic_candidate_states",
            "automatic_candidate_is_reviewed_target_relation",
            "generic_repeated_relation_state",
            "generic_repeated_relation_is_named_pattern",
            "pattern_outcomes",
            "required_primitive_fields",
            "denominators",
            "missing_evidence_is_zero",
            "production_transcription_is_infallible",
            "combined_score_allowed",
        },
        "evidence_model",
        errors,
    ):
        if set(evidence["target_relation_outcomes"]) != TARGET_RELATION_OUTCOMES:
            errors.append("target relation outcomes must preserve every approved state")
        if set(evidence["automatic_candidate_states"]) != AUTOMATIC_CANDIDATE_STATES:
            errors.append(
                "automatic candidate states must preserve every approved state"
            )
        if evidence["automatic_candidate_is_reviewed_target_relation"] is not False:
            errors.append(
                "an automatic candidate cannot become a reviewed target relation"
            )
        if evidence["generic_repeated_relation_state"] != "repeated_relation_candidate":
            errors.append("the generic repeated relation state must remain a candidate")
        if evidence["generic_repeated_relation_is_named_pattern"] is not False:
            errors.append("a generic repeated relation cannot become a named pattern")
        required_layers = {
            "source_audio_and_quality",
            "task_prompt_and_intended_word",
            "blind_listener_word_transcriptions",
            "blind_human_production_transcriptions",
            "reviewed_variant_set",
            "raw_asr_outputs",
            "reviewer_disagreements_and_adjudication",
        }
        if not required_layers.issubset(evidence["layers_kept_separate"]):
            errors.append("evidence layers are missing required separation")
        for field in (
            "missing_evidence_is_zero",
            "production_transcription_is_infallible",
            "combined_score_allowed",
        ):
            if evidence[field] is not False:
                errors.append(f"evidence_model.{field} must remain false")

    truth = document["reference_truth"]
    if _require_fields(
        truth,
        {
            "blind_listener_reference",
            "two_pass_production_review",
            "variant_reference",
            "engineering_benchmark_reference",
            "single_reviewer_is_reference_truth",
            "automatic_system_is_reference_truth",
        },
        "reference_truth",
        errors,
    ):
        review = truth["two_pass_production_review"]
        if review.get("independent_reviewers", 0) < 2:
            errors.append("reference truth needs at least two independent reviewers")
        for field in (
            "reviewers_blind_to_automatic_outputs",
            "pass_one_blind_to_expected_word",
            "original_records_retained",
            "disagreements_retained",
            "documented_adjudication",
            "broad_ipa_default",
            "narrow_transcription_requires_separate_protocol_and_reliability",
            "reviewer_language_and_variety_competence_recorded",
        ):
            if review.get(field) is not True:
                errors.append(f"two pass review must require {field}")
        if truth["single_reviewer_is_reference_truth"] is not False:
            errors.append("one reviewer cannot create reference truth")
        if truth["automatic_system_is_reference_truth"] is not False:
            errors.append("an automatic system cannot create reference truth")
        variant = truth["variant_reference"]
        if variant.get("unresolved_form_behavior") != "unscorable":
            errors.append("unresolved language or variety forms must be unscorable")
        if (
            variant.get(
                "qualified_professional_review_required_for_scientific_or_"
                "product_release"
            )
            is not True
        ):
            errors.append("scientific and product variants require professional review")
        if (
            variant.get(
                "developer_reference_variants_may_use_versioned_open_or_"
                "licensed_sources"
            )
            is not True
        ):
            errors.append("developer variants must remain versioned and licensed")
        if variant.get("developer_reference_variant_role") != (
            "candidate_exclusion_prompt_design_and_engineering_benchmark_only"
        ):
            errors.append("developer reference variants may support engineering only")
        benchmark = truth["engineering_benchmark_reference"]
        if benchmark.get("allowed_reference") != (
            "documented_existing_expert_annotations"
        ):
            errors.append(
                "engineering benchmarks require documented expert annotations"
            )
        for field in (
            "source_specific_construct_and_disagreement_retained",
            "source_limitations_required",
        ):
            if benchmark.get(field) is not True:
                errors.append(f"engineering benchmark must require {field}")
        for field in (
            "may_unlock_scientific_or_product_release",
            "may_define_acceptable_language_or_variety_truth",
        ):
            if benchmark.get(field) is not False:
                errors.append(f"engineering benchmark {field} must remain false")

    separation = document["asr_and_alignment_separation"]
    required_false = {
        "asr_disagreement_may_create_sound_concern",
        "asr_confidence_is_phone_probability",
        "multiple_asr_agreement_is_truth",
        "expected_text_forced_alignment_verifies_production",
        "llm_may_infer_produced_phone",
    }
    if _require_fields(
        separation,
        required_false
        | {
            "raw_asr_retained_as_system_evidence",
            "asr_may_trigger_manual_review",
            "forced_alignment_role",
            "phone_recognizer_role",
            "provider_pronunciation_score_role",
            "required_error_attribution_states",
        },
        "asr_and_alignment_separation",
        errors,
    ):
        for field in required_false:
            if separation[field] is not False:
                errors.append(f"asr_and_alignment_separation.{field} must remain false")
        if separation["forced_alignment_role"] != (
            "candidate_interval_localisation_only"
        ):
            errors.append("forced alignment may only localise a candidate interval")

    variety = document["language_and_variety_policy"]
    if isinstance(variety, dict):
        for field in (
            "single_standard_accent_allowed",
            "acceptable_variant_can_be_error",
            "language_history_may_be_inferred_from_voice",
            "cross_linguistic_transfer_is_disorder",
            "listener_bias_is_speaker_impairment",
        ):
            if variety.get(field) is not False:
                errors.append(f"language_and_variety_policy.{field} must remain false")
        if variety.get("unsupported_or_unrepresented_form_behavior") != "unscorable":
            errors.append(
                "language_and_variety_policy unrepresented forms must remain "
                "unscorable"
            )
        if (
            variety.get("self_reported_language_or_variety_is_context_not_truth")
            is not True
        ):
            errors.append("self reported language or variety must remain context")
    else:
        errors.append("language_and_variety_policy must be an object")

    pattern = document["pattern_policy"]
    if isinstance(pattern, dict):
        if pattern.get("active_pattern_registry") != []:
            errors.append("the unreviewed pattern registry must remain empty")
        for field in (
            "single_opportunity_can_create_pattern",
            "asr_errors_can_create_pattern",
            "pattern_label_is_disorder",
        ):
            if pattern.get(field) is not False:
                errors.append(f"pattern_policy.{field} must remain false")
        for field in (
            "pattern_requires_multiple_words_and_contexts",
            "support_and_opportunity_counts_required",
            "consistency_must_be_reported",
            "language_and_variety_explanation_checked_first",
            "named_pattern_requires_human_confirmed_target_relations",
            "generic_repeated_relation_candidate_allowed_after_validation",
            "generic_repeated_relation_requires_multiple_words_and_contexts",
        ):
            if pattern.get(field) is not True:
                errors.append(f"pattern_policy.{field} must remain true")
        for field in (
            "automatic_named_pattern_allowed",
            "generic_repeated_relation_is_disorder",
        ):
            if pattern.get(field) is not False:
                errors.append(f"pattern_policy.{field} must remain false")
        if pattern.get("generic_repeated_relation_status") != (
            "structure_implemented_emission_disabled_no_rule_selected"
        ):
            errors.append(
                "generic repeated relation structure must remain implemented with "
                "emission disabled"
            )
        if pattern.get("numeric_pattern_thresholds") is not None:
            errors.append("numeric pattern thresholds cannot be invented")
        if pattern.get("threshold_status") != (
            "not_selected_task_matched_evidence_unavailable"
        ):
            errors.append(
                "pattern thresholds must remain unselected after the evidence stop"
            )
        if pattern.get("threshold_selection_rule") != (
            "select_on_development_and_tuning_participants_then_freeze_before_held_out"
        ):
            errors.append(
                "pattern thresholds must be selected before held out evaluation"
            )
    else:
        errors.append("pattern_policy must be an object")

    candidates = document["candidate_systems"]
    if isinstance(candidates, dict):
        if candidates.get("selected_system") is not None:
            errors.append("no candidate system may be selected before evaluation")
        if candidates.get("comparison_status") != (
            "candidate_evidence_adequacy_failed_no_system_selected"
        ):
            errors.append(
                "candidate comparison must record the adequacy failure with no "
                "selected system"
            )
        if (
            candidates.get("candidate_outputs_hidden_from_reference_reviewers")
            is not True
        ):
            errors.append("reference reviewers must remain blind to candidate systems")
        if candidates.get("selected_supporting_systems") != []:
            errors.append(
                "no supporting candidate system may be selected before evaluation"
            )
        if candidates.get("local_primary_evidence_required") is not True:
            errors.append("local evidence must remain primary")
        if candidates.get("remote_provider_required") is not False:
            errors.append("a remote provider cannot be required")
        if candidates.get("provider_agreement_is_reference_truth") is not False:
            errors.append("provider agreement cannot become reference truth")
        if (
            candidates.get(
                "provider_selection_requires_held_out_incremental_value"
            )
            is not True
        ):
            errors.append("provider selection requires held out incremental value")
        allowed_provider_states = {
            "planned",
            "terms_pending",
            "configured",
            "evaluated",
            "local_feasibility_passed_timing_only",
            "local_feasibility_passed_release_blocked",
            "local_feasibility_passed_strict_identity_only",
            "development_timing_benchmark_complete_release_locked",
            "development_relation_benchmark_failed_selection_release_blocked",
            "development_benchmark_strict_mapping_complete",
            "selected_supporting_evidence",
            "rejected",
            "unavailable",
        }
        if set(candidates.get("provider_states", [])) != allowed_provider_states:
            errors.append("candidate provider states must remain explicit")
        planned_systems = {
            item.get("system_id"): item
            for item in candidates.get("planned_systems", [])
            if isinstance(item, dict)
        }
        required_planned_ids = {
            "current_asr_word_baseline",
            "montreal_forced_aligner",
            "phoneticxeus",
            "meta_wav2vec2_constrained_contextual",
            "panphon",
            "azure_pronunciation_assessment",
            "speechace",
            "speechsuper",
        }
        if not required_planned_ids.issubset(planned_systems):
            errors.append("candidate systems are missing a planned comparison")
        expected_system_states = {
            "current_asr_word_baseline": "planned",
            "montreal_forced_aligner": "development_timing_benchmark_complete_release_locked",
            "phoneticxeus": "development_relation_benchmark_failed_selection_release_blocked",
            "meta_wav2vec2_constrained_contextual": (
                "development_relation_benchmark_failed_selection_release_blocked"
            ),
            "panphon": "development_benchmark_strict_mapping_complete",
            "azure_pronunciation_assessment": "terms_pending",
            "speechace": "terms_pending",
            "speechsuper": "terms_pending",
        }
        for system_id, system in planned_systems.items():
            if system.get("state") not in allowed_provider_states:
                errors.append(f"candidate system {system_id} has an invalid state")
            if system_id in expected_system_states and system.get("state") != (
                expected_system_states[system_id]
            ):
                errors.append(
                    f"candidate system {system_id} may not change from its checkpoint 22D state"
                )
    else:
        errors.append("candidate_systems must be an object")

    feasibility = document["local_feasibility"]
    if _require_fields(
        feasibility,
        {
            "status",
            "report_path",
            "report_sha256",
            "private_sample_manifest_sha256",
            "raw_evidence_committed",
            "development_sample_only",
            "held_out_or_accuracy_evaluation_performed",
            "normal_pipeline_used_as_input",
            "gpu_rental_used",
            "local_stack_fits_current_machine",
            "candidate_extractor_implemented",
            "research_artifact_implemented",
            "next_checkpoint",
        },
        "local_feasibility",
        errors,
    ):
        if feasibility["status"] != "complete_release_locked":
            errors.append("local feasibility must remain complete and release locked")
        expected_true = ("development_sample_only", "local_stack_fits_current_machine")
        for field in expected_true:
            if feasibility[field] is not True:
                errors.append(f"local_feasibility.{field} must remain true")
        expected_false = (
            "raw_evidence_committed",
            "held_out_or_accuracy_evaluation_performed",
            "normal_pipeline_used_as_input",
            "gpu_rental_used",
            "candidate_extractor_implemented",
            "research_artifact_implemented",
        )
        for field in expected_false:
            if feasibility[field] is not False:
                errors.append(f"local_feasibility.{field} must remain false")
        if feasibility["report_path"] != "local-feasibility-v1.0.0.json":
            errors.append("local feasibility report path is not pinned")
        else:
            report_path = Path(__file__).with_name(feasibility["report_path"])
            if not report_path.is_file():
                errors.append("local feasibility report is missing")
            else:
                if file_sha256(report_path) != feasibility["report_sha256"]:
                    errors.append("local feasibility report checksum changed")
                report = json.loads(report_path.read_text(encoding="utf-8"))
                errors.extend(validate_safe_feasibility_report(report))
        if feasibility["private_sample_manifest_sha256"] != (
            FROZEN_SAMPLE_MANIFEST_SHA256
        ):
            errors.append("private feasibility sample checksum changed")
        if feasibility["next_checkpoint"] != (
            "completed_checkpoint_22C"
        ):
            errors.append("local feasibility completion marker changed")

    amendment = document["contract_amendment"]
    if _require_fields(
        amendment,
        {
            "path",
            "sha256",
            "protocol_version",
            "unchanged_historical_contract",
        },
        "contract_amendment",
        errors,
    ):
        if amendment != {
            "path": PREVIOUS_CONTRACT_PATH.name,
            "sha256": FROZEN_PREVIOUS_CONTRACT_SHA256,
            "protocol_version": "1.6.0",
            "unchanged_historical_contract": True,
        }:
            errors.append("the version 1.6 base contract binding changed")
        if (
            not PREVIOUS_CONTRACT_PATH.is_file()
            or file_sha256(PREVIOUS_CONTRACT_PATH)
            != FROZEN_PREVIOUS_CONTRACT_SHA256
        ):
            errors.append("the version 1.6 base contract checksum changed")

    benchmark = document["local_benchmark"]
    if _require_fields(
        benchmark,
        {
            "status",
            "report_path",
            "report_sha256",
            "benchmark_contract_path",
            "benchmark_contract_sha256",
            "phone_map_path",
            "phone_map_sha256",
            "private_sample_manifest_sha256",
            "raw_or_row_level_evidence_committed",
            "development_and_tuning_only",
            "held_out_evaluation_accessed_or_scored",
            "selected_system",
            "threshold_selected",
            "candidate_extractor_implemented",
            "research_artifact_implemented",
            "normal_pipeline_used_as_input",
            "paid_provider_evaluated",
            "next_checkpoint",
        },
        "local_benchmark",
        errors,
    ):
        if benchmark["status"] != "complete_release_locked":
            errors.append("local benchmark must remain complete and release locked")
        if benchmark["development_and_tuning_only"] is not True:
            errors.append("local benchmark must remain development and tuning only")
        for field in (
            "raw_or_row_level_evidence_committed",
            "held_out_evaluation_accessed_or_scored",
            "threshold_selected",
            "candidate_extractor_implemented",
            "research_artifact_implemented",
            "normal_pipeline_used_as_input",
            "paid_provider_evaluated",
        ):
            if benchmark[field] is not False:
                errors.append(f"local_benchmark.{field} must remain false")
        if benchmark["selected_system"] is not None:
            errors.append("local benchmark cannot select a candidate system")
        pinned_files = (
            (
                "report_path",
                "report_sha256",
                BENCHMARK_REPORT_PATH,
                FROZEN_BENCHMARK_REPORT_SHA256,
                validate_safe_benchmark_report,
            ),
            (
                "benchmark_contract_path",
                "benchmark_contract_sha256",
                BENCHMARK_CONTRACT_PATH,
                None,
                validate_benchmark_contract,
            ),
            (
                "phone_map_path",
                "phone_map_sha256",
                PHONE_MAP_PATH,
                None,
                validate_phone_map,
            ),
        )
        for path_field, hash_field, expected_path, frozen_hash, validator in pinned_files:
            if benchmark[path_field] != expected_path.name:
                errors.append(f"local benchmark {path_field} is not pinned")
                continue
            if not expected_path.is_file():
                errors.append(f"local benchmark file is missing: {expected_path.name}")
                continue
            pinned_document = json.loads(expected_path.read_text(encoding="utf-8"))
            actual_hash = hashlib.sha256(
                canonical_json_bytes(pinned_document)
            ).hexdigest()
            if benchmark[hash_field] != actual_hash:
                errors.append(f"local benchmark {hash_field} changed")
            if frozen_hash is not None and actual_hash != frozen_hash:
                errors.append(f"local benchmark frozen checksum changed: {expected_path.name}")
            errors.extend(validator(pinned_document))
        if benchmark["private_sample_manifest_sha256"] != (
            FROZEN_BENCHMARK_MANIFEST_SHA256
        ):
            errors.append("private benchmark sample checksum changed")
        if benchmark["next_checkpoint"] != (
            "22E_paid_api_bake_off_after_owner_commit_and_explicit_approval"
        ):
            errors.append("local benchmark next checkpoint is not safely gated")

    repair = document["local_benchmark_repair"]
    if _require_fields(
        repair,
        {
            "status",
            "report_path",
            "report_sha256",
            "repair_contracts",
            "expected_only_manifest_sha256",
            "raw_or_row_level_evidence_committed",
            "development_and_tuning_only",
            "held_out_evaluation_accessed_or_scored",
            "selected_system",
            "threshold_selected",
            "candidate_extractor_implemented",
            "research_artifact_implemented",
            "normal_pipeline_used_as_input",
            "paid_provider_evaluated",
            "exact_meta_thresholds_evaluated",
            "next_checkpoint",
        },
        "local_benchmark_repair",
        errors,
    ):
        if repair["status"] != "complete_release_locked":
            errors.append("local benchmark repair must remain complete and release locked")
        if repair["development_and_tuning_only"] is not True:
            errors.append(
                "local benchmark repair must remain development and tuning only"
            )
        for field in (
            "raw_or_row_level_evidence_committed",
            "held_out_evaluation_accessed_or_scored",
            "threshold_selected",
            "candidate_extractor_implemented",
            "research_artifact_implemented",
            "normal_pipeline_used_as_input",
            "paid_provider_evaluated",
        ):
            if repair[field] is not False:
                errors.append(f"local_benchmark_repair.{field} must remain false")
        if repair["selected_system"] is not None:
            errors.append("local benchmark repair cannot select a candidate system")
        if repair["expected_only_manifest_sha256"] != (
            FROZEN_EXPECTED_MANIFEST_SHA256
        ):
            errors.append("private expected-only benchmark checksum changed")
        if repair["exact_meta_thresholds_evaluated"] != 2957:
            errors.append("the exact Meta threshold evaluation count changed")
        if repair["next_checkpoint"] != (
            "22E_paid_api_bake_off_after_owner_commit_and_explicit_approval"
        ):
            errors.append("local benchmark repair next checkpoint is not safely gated")

        if repair["report_path"] != REPAIR_REPORT_PATH.name:
            errors.append("local benchmark repair report path is not pinned")
        elif not REPAIR_REPORT_PATH.is_file():
            errors.append("local benchmark repair report is missing")
        else:
            if file_sha256(REPAIR_REPORT_PATH) != repair["report_sha256"]:
                errors.append("local benchmark repair report checksum changed")
            repair_report = json.loads(REPAIR_REPORT_PATH.read_text(encoding="utf-8"))
            errors.extend(validate_repair_report(repair_report))

        expected_repair_contracts = {
            "numeric": (
                "benchmark-repair-contract-v1.0.0.json",
                "3da9d53ccde6b5ba6155522077db7df4dd09f1164616216c04b5dab9b63d1a18",
            ),
            "contextual": (
                "benchmark-repair-context-contract-v1.0.0.json",
                "38add2aa66357da73b6aca36f5993125032d4e280c17336c18c290bc4fad7c96",
            ),
            "repeated": (
                "benchmark-repair-repeated-contract-v1.0.0.json",
                "57062400c6b484b8d34bf9cfdae29dd1174d4c00b200164fd1c5476a63146a3f",
            ),
            "meta_model": (
                "benchmark-repair-meta-contract-v1.0.0.json",
                "f3f7fcf0b49e7b3ae84fb0578856f4c7bbd59e8305c985cd78905da26f37f446",
            ),
            "meta_exact_threshold": (
                "benchmark-repair-meta-threshold-contract-v1.0.0.json",
                "9063be3af105b6409b3f7fb3e1ffd5ddaa85faf998f0ef937df0dfb704584774",
            ),
        }
        repair_contracts = repair["repair_contracts"]
        if not isinstance(repair_contracts, dict) or set(repair_contracts) != set(
            expected_repair_contracts
        ):
            errors.append("local benchmark repair contracts are incomplete")
        else:
            for contract_id, (expected_name, expected_hash) in (
                expected_repair_contracts.items()
            ):
                record = repair_contracts.get(contract_id)
                if record != {"path": expected_name, "sha256": expected_hash}:
                    errors.append(
                        f"local benchmark repair contract {contract_id} binding changed"
                    )
                    continue
                repair_contract_path = MODULE_ROOT / expected_name
                if (
                    not repair_contract_path.is_file()
                    or file_sha256(repair_contract_path) != expected_hash
                ):
                    errors.append(
                        f"local benchmark repair contract {contract_id} checksum changed"
                    )

    validation = document["validation_program"]
    if isinstance(validation, dict):
        if validation.get("scientific_release_status") != "not_evaluated":
            errors.append("scientific release must remain not evaluated")
        if validation.get("engineering_evaluation_status") != (
            "final_repository_acceptance_passed_no_selected_method_held_out_not_performed"
        ):
            errors.append(
                "engineering evaluation must record final repository acceptance "
                "with no selected method and no held-out evaluation"
            )
        if validation.get("adam_recordings_role") != "functional_integration_only":
            errors.append("Adam recordings must remain integration evidence only")
        if validation.get("participant_exclusive_splits") is not True:
            errors.append("evaluation splits must be participant exclusive")
        if validation.get("thresholds_frozen_before_held_out_evaluation") is not True:
            errors.append("thresholds must be frozen before held out evaluation")
        if not REQUIRED_VALIDATION_METRICS.issubset(
            validation.get("required_metrics", [])
        ):
            errors.append("validation metrics are incomplete")
        if validation.get("release_thresholds") is not None:
            errors.append("release thresholds cannot exist before evidence")
        if validation.get("engineering_thresholds") is not None:
            errors.append("engineering thresholds cannot exist before evidence")
        if validation.get("scientific_release_thresholds") is not None:
            errors.append("scientific thresholds cannot exist before evidence")
    else:
        errors.append("validation_program must be an object")

    failures = document["failure_policy"]
    if isinstance(failures, dict):
        for field in REQUIRED_UNAVAILABLE_FAILURES:
            if failures.get(field) != "unavailable":
                errors.append(f"failure_policy.{field} must become unavailable")
        if (
            failures.get(
                "missing_professionally_reviewed_variant_set_for_product_release"
            )
            != "blocked"
        ):
            errors.append("product release must block without professional variants")
        if failures.get("missing_source_or_licence_manifest") != "blocked":
            errors.append("research must block without a source and licence manifest")
        if failures.get("optional_provider_unavailable") != (
            "record_provider_unavailable_and_continue_with_local_evidence"
        ):
            errors.append(
                "an unavailable optional provider must fall back to local evidence"
            )
        for field in (
            "fallback_to_default_accent",
            "fallback_to_zero",
            "fallback_to_llm_judgment",
        ):
            if failures.get(field) is not False:
                errors.append(f"failure_policy.{field} must remain false")
    else:
        errors.append("failure_policy must be an object")

    downstream = document["downstream_policy"]
    if isinstance(downstream, dict):
        for field, value in downstream.items():
            if value is not False:
                errors.append(f"downstream_policy.{field} must remain false")
    else:
        errors.append("downstream_policy must be an object")

    extractor = document["developer_candidate_extractor"]
    if isinstance(extractor, dict):
        from .candidate_artifact import (
            ALLOWED_CANDIDATE_STATES,
            CONTRACT_PATH as CANDIDATE_CONTRACT_PATH,
            CONTRACT_SHA256 as CANDIDATE_CONTRACT_SHA256,
            RULE_STATUS,
            load_candidate_contract,
        )
        from .candidate_evidence import (
            REPORT_PATH as CANDIDATE_REPORT_PATH,
            validate_candidate_evidence_report,
        )

        extractor_fields = {
            "checkpoint",
            "status",
            "candidate_artifact_contract",
            "candidate_evidence_report",
            "prompt_pack",
            "selection_record",
            "artifact",
            "offline_command",
            "allowed_automatic_states",
            "candidate_rule",
            "generic_repeated_relation",
            "evidence_boundaries",
            "downstream_boundaries",
            "next_checkpoint",
        }
        missing_extractor = sorted(extractor_fields - set(extractor))
        extra_extractor = sorted(set(extractor) - extractor_fields)
        if missing_extractor:
            errors.append(
                "candidate extractor missing fields: "
                + ", ".join(missing_extractor)
            )
        if extra_extractor:
            errors.append(
                "candidate extractor has unsupported fields: "
                + ", ".join(extra_extractor)
            )
        if extractor.get("checkpoint") != "22G":
            errors.append("candidate extractor checkpoint changed")
        if extractor.get("status") != "implemented_private_release_locked":
            errors.append("candidate extractor must remain private and release locked")
        expected_files = (
            (
                "candidate_artifact_contract",
                CANDIDATE_CONTRACT_PATH,
                CANDIDATE_CONTRACT_SHA256,
            ),
            (
                "candidate_evidence_report",
                CANDIDATE_REPORT_PATH,
                "4f2a68eb2492679d50c828aef99c422d5536555b522ee55ec61ebf0311f5068d",
            ),
        )
        for field, path, expected_sha in expected_files:
            binding = extractor.get(field) or {}
            if binding.get("path") != path.name or binding.get("sha256") != expected_sha:
                errors.append(f"candidate extractor {field} binding changed")
            if not path.is_file() or file_sha256(path) != expected_sha:
                errors.append(f"candidate extractor {field} checksum changed")
        if extractor.get("candidate_artifact_contract") != {
            "path": CANDIDATE_CONTRACT_PATH.name,
            "sha256": CANDIDATE_CONTRACT_SHA256,
            "status": "rules_frozen_before_candidate_extractor_implementation",
        }:
            errors.append("candidate artifact contract record changed")
        if extractor.get("candidate_evidence_report") != {
            "path": CANDIDATE_REPORT_PATH.name,
            "sha256": (
                "4f2a68eb2492679d50c828aef99c422d5536555b522ee55ec61ebf0311f5068d"
            ),
            "status": "adequacy_failed_before_any_rule_search",
            "decision": RULE_STATUS,
        }:
            errors.append("candidate evidence report record changed")
        prompt_path = MODULE_ROOT / "research-prompt-pack-v1.0.0.json"
        expected_prompt = {
            "path": prompt_path.name,
            "sha256": (
                "c53522ee155628d6266c5494d7e9c45d9d06f4dc550abac82f9816e00f5b7d72"
            ),
            "status": "unreviewed_inactive_developer_research_only",
        }
        if extractor.get("prompt_pack") != expected_prompt:
            errors.append("candidate extractor prompt pack binding changed")
        if (
            not prompt_path.is_file()
            or file_sha256(prompt_path) != expected_prompt["sha256"]
        ):
            errors.append("candidate extractor prompt pack checksum changed")
        selection_path = MODULE_ROOT / "selection-record-v1.1.0.json"
        expected_selection = {
            "path": selection_path.name,
            "sha256": (
                "528e2a07c733bb4f456f422765589d362f3fe242f08909b011f30ce8bc6dbe66"
            ),
            "decision": "no_selection",
        }
        if extractor.get("selection_record") != expected_selection:
            errors.append("candidate extractor selection record binding changed")
        if (
            not selection_path.is_file()
            or file_sha256(selection_path) != expected_selection["sha256"]
        ):
            errors.append("candidate extractor selection record checksum changed")
        if extractor.get("artifact") != {
            "filename": "speech_sound_candidates.json",
            "committed": False,
            "private_gitignored_output_only": True,
            "normal_pipeline_artifact": False,
            "review_state": "unreviewed",
            "automatic_error_or_correctness_output": False,
        }:
            errors.append("candidate artifact privacy or review boundary changed")
        if extractor.get("offline_command") != (
            "SPEECH_SOUND_OFFLINE=1 python3 -m "
            "speech_sound_patterns.extract_candidates --manifest MANIFEST "
            "--output-dir OUTPUT --acknowledge-developer-only"
        ):
            errors.append("candidate extractor offline command changed")
        try:
            candidate_contract = load_candidate_contract()
            report = json.loads(CANDIDATE_REPORT_PATH.read_text(encoding="utf-8"))
            errors.extend(
                validate_candidate_evidence_report(
                    report,
                    contract=candidate_contract,
                )
            )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"candidate extractor evidence is invalid: {exc}")
        if set(extractor.get("allowed_automatic_states") or []) != (
            ALLOWED_CANDIDATE_STATES
        ):
            errors.append("candidate extractor automatic states changed")
        rule = extractor.get("candidate_rule") or {}
        expected_rule = {
            "system": None,
            "threshold": None,
            "mapping": None,
            "feature_relation": None,
            "provider_configuration": None,
            "possible_relation_candidate_emission_enabled": False,
        }
        if rule != expected_rule:
            errors.append("candidate extractor rule must remain the exact no-selection")
        evidence = extractor.get("evidence_boundaries") or {}
        downstream_extract = extractor.get("downstream_boundaries") or {}
        expected_evidence_boundaries = {
            "threshold_search_after_failed_adequacy": False,
            "held_out_accessed": False,
            "owner_recordings_used_for_selection": False,
            "synthetic_fixtures_used_for_selection": False,
            "network_requests_allowed": False,
            "provider_request_made": False,
            "raw_or_row_level_evidence_committed": False,
        }
        if evidence != expected_evidence_boundaries:
            errors.append("candidate extractor evidence boundaries changed")
        expected_downstream_boundaries = {
            "normal_pipeline": False,
            "listener": False,
            "evaluator": False,
            "claim_ledger": False,
            "coaching": False,
            "history": False,
            "progress": False,
            "screening": False,
            "diagnosis": False,
        }
        if downstream_extract != expected_downstream_boundaries:
            errors.append("candidate extractor downstream boundaries changed")
        repeated = extractor.get("generic_repeated_relation") or {}
        if repeated != {
            "structure_implemented": True,
            "minimum_rule": None,
            "candidate_emission_enabled": False,
            "named_pattern": False,
            "one_token_can_qualify": False,
            "one_word_can_qualify": False,
        }:
            errors.append("generic repeated relation policy changed")
        report_binding = extractor.get("candidate_evidence_report") or {}
        if report_binding.get("decision") != RULE_STATUS:
            errors.append("candidate evidence stop decision changed")
        if extractor.get("next_checkpoint") != (
            "22H_after_owner_commit_and_explicit_instruction"
        ):
            errors.append("candidate extractor next checkpoint is not safely gated")
    else:
        errors.append("developer_candidate_extractor must be an object")

    final = document["final_repository_acceptance"]
    if isinstance(final, dict):
        expected_fields = {
            "checkpoint", "status", "acceptance_contract", "evidence_report",
            "selection_outcome", "held_out_outcome", "completion",
        }
        if set(final) != expected_fields:
            errors.append("final repository acceptance fields changed")
        if final.get("checkpoint") != "22H":
            errors.append("final repository acceptance checkpoint changed")
        if final.get("status") != (
            "final_repository_acceptance_complete_release_locked"
        ):
            errors.append("final repository acceptance status changed")

        from .final_acceptance import (
            CONTRACT_PATH as FINAL_CONTRACT_PATH,
            CONTRACT_SHA256 as FINAL_CONTRACT_SHA256,
            FINAL_DECISION,
            REPORT_PATH as FINAL_REPORT_PATH,
            load_final_contract,
            validate_final_report,
        )

        expected_acceptance_contract = {
            "path": FINAL_CONTRACT_PATH.name,
            "sha256": FINAL_CONTRACT_SHA256,
            "status": "rules_frozen_before_final_repository_acceptance",
        }
        if final.get("acceptance_contract") != expected_acceptance_contract:
            errors.append("final acceptance contract binding changed")
        if (
            not FINAL_CONTRACT_PATH.is_file()
            or file_sha256(FINAL_CONTRACT_PATH) != FINAL_CONTRACT_SHA256
        ):
            errors.append("final acceptance contract checksum changed")

        expected_report_sha = (
            "68d3e92cececfa2e4a9050ce4eab704afa8c1664fb65fb21764bf27104a5199a"
        )
        expected_evidence_report = {
            "path": FINAL_REPORT_PATH.name,
            "sha256": expected_report_sha,
            "status": "final_repository_acceptance_complete_release_locked",
            "decision": FINAL_DECISION,
        }
        if final.get("evidence_report") != expected_evidence_report:
            errors.append("final evidence report binding changed")
        if (
            not FINAL_REPORT_PATH.is_file()
            or file_sha256(FINAL_REPORT_PATH) != expected_report_sha
        ):
            errors.append("final evidence report checksum changed")
        else:
            try:
                final_contract = load_final_contract()
                final_report = json.loads(
                    FINAL_REPORT_PATH.read_text(encoding="utf-8")
                )
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                errors.append(f"final acceptance artifacts are invalid: {exc}")
            else:
                errors.extend(
                    validate_final_report(final_report, contract=final_contract)
                )

        if final.get("selection_outcome") != {
            "decision": "no_selection",
            "candidate_system": None,
            "candidate_output_mapping": None,
            "feature_relation": None,
            "threshold": None,
            "provider_configuration": None,
            "repeated_relation_minimum": None,
            "further_search_authorised": False,
        }:
            errors.append("final no-selection outcome changed")
        if final.get("held_out_outcome") != {
            "evaluation_status": "not_performed",
            "result_availability": "unavailable",
            "reason_code": "not_evaluated_no_selected_candidate",
            "evidence_accessed": False,
            "performance_established": False,
            "metric_gate_result": None,
            "predeclared_metric_count": 40,
            "all_predeclared_metrics_explicitly_unavailable": True,
            "later_access_requires_new_contract_and_explicit_owner_approval": True,
            "silent_item_24_reuse_authorised": False,
        }:
            errors.append("final held-out non-evaluation outcome changed")
        if final.get("completion") != {
            "engineering_complete_after_repository_closure": True,
            "truth_classes_pooled": False,
            "normal_pipeline_speech_sound_activation": False,
            "scientific_release": False,
            "product_release": False,
            "next_roadmap_item_approved": False,
        }:
            errors.append("final engineering-only completion boundary changed")
    else:
        errors.append("final_repository_acceptance must be an object")

    release = document["release_policy"]
    if isinstance(release, dict):
        if release.get("developer_offline_candidate_engineering") != (
            "approved_candidate_artifact_implemented_private_release_locked"
        ):
            errors.append(
                "developer candidate extractor must remain private and release locked"
            )
        if release.get("automatic_candidate_collection") != (
            "blocked_until_validated_manifests_and_research_task"
        ):
            errors.append("automatic candidate collection must remain gated")
        for field in REQUIRED_PRODUCT_RELEASE_BLOCKS:
            if release.get(field) != "blocked":
                errors.append(f"release_policy.{field} must remain blocked")
        engineering_requirements = set(release.get("engineering_requirements") or [])
        if not {
            "validated_engineering_contract",
            "verified_source_and_licence_manifests",
            "versioned_controlled_word_research_pack",
            "participant_exclusive_engineering_benchmark",
        }.issubset(engineering_requirements):
            errors.append("engineering release requirements are incomplete")
        scientific_requirements = set(
            release.get("scientific_release_requirements") or []
        )
        if not {
            "qualified speech pathology and phonetic review",
            "active professionally reviewed task and word specific variant pack",
            "representative independent participant labelled data",
            "acceptable held out performance including variant false concerns",
            "separate owner approval",
        }.issubset(scientific_requirements):
            errors.append("scientific release requirements are incomplete")
        product_requirements = set(release.get("product_release_requirements") or [])
        if not {
            "scientific release requirements satisfied",
            "separate owner approval for product release",
        }.issubset(product_requirements):
            errors.append("product release requirements are incomplete")
    else:
        errors.append("release_policy must be an object")

    if not isinstance(document["sources"], list) or not document["sources"]:
        errors.append("the research contract must retain its sources")
    return errors


def assert_valid_contract(document):
    errors = validate_contract(document)
    if errors:
        raise SpeechSoundResearchValidationError("\n".join(errors))
    return document
