"""Validate the fail-closed checkpoint 23B governance contract.

The active document is deliberately an in-progress contract.  It records the
owner's adults-first scope while refusing to imply that public research or an
agent can fill independent professional, participant, institutional, ethics,
privacy, legal, statistical or regulatory roles.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = MODULE_ROOT.parent
CONTRACT_PATH = MODULE_ROOT / "governance-contract-v1.0.0.json"
CURRENT_CONTRACT_CANONICAL_SHA256 = (
    "1e84398af146ac1c88911a569dc292697a3021a3eb25257f5f6e498530756475"
)

ACTIVE_PYTHON_ROOTS = (
    "pipeline",
)

ROOT_FIELDS = {
    "schema_version",
    "contract_id",
    "contract_version",
    "checkpoint",
    "status",
    "owner_scope",
    "intended_use",
    "lane_decisions",
    "candidate_questions",
    "role_requirements",
    "authority_status",
    "contact_and_spending",
    "research_data",
    "task_and_reference",
    "sampling_and_splits",
    "privacy_and_consent",
    "regulatory",
    "decision_rules",
    "release_boundaries",
    "downstream",
    "sources",
}

LANE_FIELDS = {
    "status",
    "selected_construct",
    "selected_task",
    "selected_measure",
    "selected_score",
    "selected_threshold",
    "reason",
}

EXPECTED_LANE_STATUSES = {
    "motor_speech": "pending_independent_governance",
    "general_speech": "pending_independent_governance",
    "voice": "pending_independent_governance",
    "participant_report": "not_applicable_until_intended_benefit_is_governed",
    "controlled_intelligibility": (
        "not_applicable_until_functional_relevance_is_governed"
    ),
    "clinical_laryngeal_reference": (
        "not_required_unless_a_future_voice_claim_needs_it"
    ),
}

EXPECTED_QUESTION_PROFILES = {
    "controlled_rapid_syllable_timing": {
        "lane": "motor_speech",
        "state": "governance_question_unselected",
    },
    "controlled_rapid_syllable_observable_accuracy": {
        "lane": "motor_speech",
        "state": "governance_question_unselected",
    },
    "controlled_connected_speech_timing": {
        "lane": "general_speech",
        "state": "governance_question_unselected",
    },
    "unfamiliar_listener_intelligibility": {
        "lane": "controlled_intelligibility",
        "state": "governance_question_unselected",
    },
    "existing_item_20_voice_primitives": {
        "lane": "voice",
        "state": "supporting_observations_only_not_selected_for_item_23",
    },
}
EXPECTED_QUESTION_IDS = set(EXPECTED_QUESTION_PROFILES)

EXPECTED_ROLE_PROFILES = {
    "product_owner": {
        "status": "filled_for_scope_only",
        "must_be_independent_of": [],
        "decision_right": "approve_scope_outreach_spending_and_any_later_release",
        "evidence_required": "dated_owner_decision",
    },
    "paid_lived_experience_governance_group": {
        "status": "unfilled",
        "must_be_independent_of": [
            "candidate_vendor_control",
            "developer_control",
            "selection_outcome",
        ],
        "decision_right": (
            "accept_reject_or_require_changes_to_benefit_burden_access_consent_"
            "wording_complaints_and_release_acceptability"
        ),
        "evidence_required": (
            "terms_of_reference_membership_access_plan_payment_and_signed_"
            "decision_record"
        ),
    },
    "independent_adult_motor_speech_cpsp": {
        "status": "unfilled",
        "must_be_independent_of": ["candidate_vendor", "reference_vendor"],
        "decision_right": (
            "accept_reject_or_require_changes_to_motor_construct_task_truth_"
            "manual_and_safety_route"
        ),
        "evidence_required": (
            "current_full_cpsp_status_recent_motor_speech_competence_for_the_"
            "exact_selected_adult_population_conflicts_and_signed_review"
        ),
    },
    "independent_adult_voice_cpsp": {
        "status": "unfilled",
        "must_be_independent_of": ["candidate_vendor", "reference_vendor"],
        "decision_right": (
            "accept_reject_or_require_changes_to_voice_construct_task_"
            "perceptual_reference_identity_and_safety_boundaries"
        ),
        "evidence_required": (
            "current_full_cpsp_status_recent_adult_voice_expertise_conflicts_"
            "and_signed_review"
        ),
    },
    "independent_clinical_reference_lead_if_required": {
        "status": "conditional_unfilled",
        "must_be_independent_of": [
            "candidate_vendor",
            "reference_vendor",
            "developer",
        ],
        "decision_right": (
            "own_any_prospective_clinical_reference_manual_adjudication_and_"
            "release_boundary"
        ),
        "evidence_required": (
            "claim_specific_current_qualifications_independence_conflicts_"
            "manual_and_signed_review"
        ),
    },
    "independent_ent_or_laryngologist_if_required": {
        "status": "conditional_unfilled",
        "must_be_independent_of": ["candidate_vendor", "developer"],
        "decision_right": (
            "review_any_laryngeal_pathology_structure_cause_or_medical_"
            "reference_proposal"
        ),
        "evidence_required": (
            "current_medical_registration_applicable_otolaryngology_head_and_"
            "neck_surgery_specialist_registration_separate_adult_laryngology_"
            "voice_expertise_conflicts_and_signed_review"
        ),
    },
    "independent_speech_measurement_scientist": {
        "status": "unfilled",
        "must_be_independent_of": ["candidate_vendor", "reference_vendor"],
        "decision_right": (
            "accept_reject_or_require_changes_to_construct_capture_algorithm_"
            "agreement_and_reproducibility_design"
        ),
        "evidence_required": (
            "relevant_measurement_record_conflicts_and_signed_review"
        ),
    },
    "biostatistician_or_measurement_specialist": {
        "status": "unfilled",
        "must_be_independent_of": ["candidate_vendor"],
        "decision_right": (
            "approve_prospective_endpoints_sample_plan_splits_missingness_"
            "agreement_and_analysis"
        ),
        "evidence_required": (
            "relevant_qualifications_conflicts_and_signed_statistical_review"
        ),
    },
    "independent_data_and_split_custodian": {
        "status": "unfilled",
        "must_be_independent_of": [
            "candidate_vendor",
            "reference_vendor",
            "developer",
        ],
        "decision_right": (
            "create_protect_and_audit_participant_exclusive_allocations_"
            "overlap_registers_and_held_out_access"
        ),
        "evidence_required": (
            "research_data_management_competence_conflicts_custody_plan_and_"
            "signed_access_record"
        ),
    },
    "responsible_research_institution": {
        "status": "unfilled",
        "must_be_independent_of": ["candidate_vendor"],
        "decision_right": (
            "determine_ethics_pathway_and_provide_institutional_and_site_"
            "governance_authority"
        ),
        "evidence_required": (
            "named_organisation_responsibility_acceptance_pathway_and_"
            "authorisation_records"
        ),
    },
    "human_research_ethics_committee_if_required": {
        "status": "conditional_unfilled",
        "must_be_independent_of": [
            "candidate_vendor_control",
            "developer_control",
            "sponsor_control_of_committee_decision",
        ],
        "decision_right": (
            "provide_prospective_ethical_review_and_decision_for_the_final_"
            "protocol"
        ),
        "evidence_required": (
            "registered_hrec_identity_scope_and_formally_issued_decision"
        ),
    },
    "privacy_security_and_australian_legal_review": {
        "status": "unfilled",
        "must_be_independent_of": ["candidate_vendor"],
        "decision_right": (
            "assess_entity_coverage_data_flow_recording_laws_consent_"
            "retention_transfer_security_and_contracts"
        ),
        "evidence_required": (
            "qualified_reviewers_conflicts_pia_legal_map_security_review_and_"
            "signed_advice"
        ),
    },
    "australian_medical_device_regulatory_specialist": {
        "status": "unfilled",
        "must_be_independent_of": ["candidate_vendor"],
        "decision_right": (
            "document_preliminary_classification_trial_and_future_supply_"
            "pathway_without_acting_as_approval_authority"
        ),
        "evidence_required": (
            "qualified_specialist_conflicts_and_written_assessment"
        ),
    },
    "independent_truth_and_release_group": {
        "status": "unfilled",
        "must_be_independent_of": [
            "candidate_vendor",
            "reference_vendor",
            "developer",
        ],
        "decision_right": (
            "protect_held_out_evidence_review_failures_and_make_a_non_vendor_"
            "release_recommendation"
        ),
        "evidence_required": (
            "terms_of_reference_paid_lived_experience_membership_conflicts_"
            "and_signed_decision_record"
        ),
    },
}
EXPECTED_ROLE_IDS = set(EXPECTED_ROLE_PROFILES)

EXPECTED_SOURCES = {
    "nhmrc_national_statement_2025": (
        "https://www.nhmrc.gov.au/about-us/publications/"
        "national-statement-ethical-conduct-human-research-2025"
    ),
    "nhmrc_hrec_routes": (
        "https://www.nhmrc.gov.au/research-policy/ethics/"
        "human-research-ethics-committees"
    ),
    "nhmrc_consumer_involvement_2026": (
        "https://www.nhmrc.gov.au/about-us/publications/"
        "statement-consumer-and-community-involvement-health-medical-research"
    ),
    "speech_pathology_australia_certification": (
        "https://www.speechpathologyaustralia.org.au/Public/Become/"
        "Certification-Program/Certification-program.aspx"
    ),
    "oaic_app_1_automated_decisions": (
        "https://www.oaic.gov.au/privacy/australian-privacy-principles/"
        "australian-privacy-principles-guidelines/chapter-1-app-1-open-and-"
        "transparent-management-of-personal-information"
    ),
    "oaic_app_3_collection": (
        "https://www.oaic.gov.au/privacy/australian-privacy-principles/"
        "australian-privacy-principles-guidelines/chapter-3-app-3-collection-"
        "of-solicited-personal-information"
    ),
    "oaic_app_5_collection_notice": (
        "https://www.oaic.gov.au/privacy/australian-privacy-principles/"
        "australian-privacy-principles-guidelines/chapter-5-app-5-notification-"
        "of-the-collection-of-personal-information"
    ),
    "oaic_app_6_use_disclosure": (
        "https://www.oaic.gov.au/privacy/australian-privacy-principles/"
        "australian-privacy-principles-guidelines/chapter-6-app-6-use-or-"
        "disclosure-of-personal-information"
    ),
    "oaic_app_8_overseas": (
        "https://www.oaic.gov.au/privacy/australian-privacy-principles/"
        "australian-privacy-principles-guidelines/chapter-8-app-8-cross-border-"
        "disclosure-of-personal-information"
    ),
    "oaic_app_11_security": (
        "https://www.oaic.gov.au/privacy/australian-privacy-principles/"
        "australian-privacy-principles-guidelines/chapter-11-app-11-security-"
        "of-personal-information"
    ),
    "queensland_recording_guide": (
        "https://www.oic.qld.gov.au/library/articles/"
        "qld-camera-surveillance-audio-recording-drones"
    ),
    "tga_software_medical_devices_2026": (
        "https://www.tga.gov.au/resources/guidance/"
        "understanding-how-we-regulate-software-based-medical-devices"
    ),
    "tga_software_exemptions_2026": (
        "https://www.tga.gov.au/products/medical-devices/"
        "software-and-artificial-intelligence-ai/overview/"
        "exempt-software-medical-device"
    ),
}
EXPECTED_SOURCE_IDS = set(EXPECTED_SOURCES)

RELEASE_FIELDS = {
    "measurement",
    "task",
    "score",
    "threshold",
    "normal_pipeline",
    "coaching",
    "history",
    "progress",
    "screening",
    "diagnosis",
    "clinical_interpretation",
    "scientific_release",
    "product_release",
}


class GovernanceValidationError(ValueError):
    """Raised when the governance document cannot be read safely."""


def load_governance_contract(path=CONTRACT_PATH):
    """Load one regular JSON file without following a final symlink."""
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise GovernanceValidationError(
            f"governance contract must be a regular file: {path}"
        )
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GovernanceValidationError(
            f"governance contract is unreadable: {path}"
        ) from exc


def _exact_object(value, fields, label, errors):
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return False
    missing = sorted(fields - set(value))
    extras = sorted(set(value) - fields)
    if missing:
        errors.append(f"{label} is missing: {', '.join(missing)}")
    if extras:
        errors.append(f"{label} has unsupported fields: {', '.join(extras)}")
    return not missing and not extras


def _all_false(value, fields, label, errors):
    if not _exact_object(value, fields, label, errors):
        return
    for field in sorted(fields):
        if value[field] is not False:
            errors.append(f"{label}.{field} must remain false")


def _expect(value, expected, label, errors):
    if value != expected or type(value) is not type(expected):
        errors.append(f"{label} changed")


def canonical_contract_sha256(document):
    """Return a stable digest for JSON-compatible contract content."""
    try:
        canonical = json.dumps(
            document,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError):
        return None
    return hashlib.sha256(canonical).hexdigest()


def validate_governance_contract(document):
    """Return every structural or safety error in the active 23B contract."""
    errors = []
    if not _exact_object(document, ROOT_FIELDS, "contract", errors):
        return errors
    if canonical_contract_sha256(document) != CURRENT_CONTRACT_CANONICAL_SHA256:
        return [
            "contract content changed; issue a new reviewed version and "
            "validator before changing this immutable in-progress record"
        ]

    for field, expected in {
        "schema_version": "1.0.0",
        "contract_id": "motor_speech_voice_governance",
        "contract_version": "1.0.0",
        "checkpoint": "23B",
        "status": "owner_scope_recorded_external_governance_pending",
    }.items():
        _expect(document[field], expected, field, errors)

    owner_fields = {
        "checkpoint_23b_approved",
        "approval_record",
        "research_age_scope",
        "minimum_participant_age_years",
        "child_lane_status",
        "adult_scope_creates_product_age_gate",
        "owner_signed_intended_use",
        "legal_sponsor_status",
    }
    owner = document["owner_scope"]
    if _exact_object(owner, owner_fields, "owner_scope", errors):
        expected_owner = {
            "checkpoint_23b_approved": True,
            "approval_record": "owner_continue_2026_08_14",
            "research_age_scope": "adults_first",
            "minimum_participant_age_years": 18,
            "child_lane_status": "not_in_scope_requires_separate_future_study",
            "adult_scope_creates_product_age_gate": False,
            "owner_signed_intended_use": False,
            "legal_sponsor_status": "unresolved_owner_input_required",
        }
        for field, expected in expected_owner.items():
            _expect(owner[field], expected, f"owner_scope.{field}", errors)

    intended_fields = {
        "status",
        "user",
        "population",
        "setting",
        "input",
        "action",
        "expected_benefit",
        "claim_level",
        "product_use",
        "screening_use",
        "clinical_use",
    }
    intended = document["intended_use"]
    if _exact_object(intended, intended_fields, "intended_use", errors):
        for field in ("product_use", "screening_use", "clinical_use"):
            if intended[field] is not False:
                errors.append(f"intended_use.{field} must remain false")
        if intended["status"] != "draft_requires_independent_governance":
            errors.append("intended_use.status must remain a draft")
        if intended["claim_level"] != "none_no_measurement_selected":
            errors.append("intended_use.claim_level must remain none")

    lanes = document["lane_decisions"]
    if _exact_object(
        lanes, set(EXPECTED_LANE_STATUSES), "lane_decisions", errors
    ):
        for lane_id, expected_status in EXPECTED_LANE_STATUSES.items():
            lane = lanes[lane_id]
            label = f"lane_decisions.{lane_id}"
            if not _exact_object(lane, LANE_FIELDS, label, errors):
                continue
            if lane["status"] != expected_status:
                errors.append(f"{label}.status changed")
            for field in (
                "selected_construct",
                "selected_task",
                "selected_measure",
                "selected_score",
                "selected_threshold",
            ):
                if lane[field] is not None:
                    errors.append(f"{label}.{field} must remain null")
            if not isinstance(lane["reason"], str) or not lane["reason"]:
                errors.append(f"{label}.reason must be explicit")

    questions = document["candidate_questions"]
    if not isinstance(questions, list):
        errors.append("candidate_questions must be an array")
    else:
        seen = set()
        question_fields = {"question_id", "lane", "state", "priority", "selected"}
        for index, question in enumerate(questions):
            label = f"candidate_questions[{index}]"
            if not _exact_object(question, question_fields, label, errors):
                continue
            question_id = question["question_id"]
            if question_id in seen:
                errors.append(f"candidate_questions repeats {question_id}")
            seen.add(question_id)
            if question["selected"] is not False:
                errors.append(f"{label}.selected must remain false")
            if question["priority"] != "unordered":
                errors.append(f"{label}.priority must remain unordered")
            expected_profile = EXPECTED_QUESTION_PROFILES.get(question_id)
            if expected_profile is not None:
                for field, expected in expected_profile.items():
                    _expect(question[field], expected, f"{label}.{field}", errors)
        if seen != EXPECTED_QUESTION_IDS:
            errors.append("candidate_questions set changed")

    roles = document["role_requirements"]
    if not isinstance(roles, list):
        errors.append("role_requirements must be an array")
    else:
        seen = set()
        role_fields = {
            "role_id",
            "status",
            "must_be_independent_of",
            "decision_right",
            "evidence_required",
        }
        for index, role in enumerate(roles):
            label = f"role_requirements[{index}]"
            if not _exact_object(role, role_fields, label, errors):
                continue
            role_id = role["role_id"]
            if role_id in seen:
                errors.append(f"role_requirements repeats {role_id}")
            seen.add(role_id)
            expected_profile = EXPECTED_ROLE_PROFILES.get(role_id)
            if expected_profile is not None:
                for field, expected in expected_profile.items():
                    _expect(role[field], expected, f"{label}.{field}", errors)
        if seen != EXPECTED_ROLE_IDS:
            errors.append("role_requirements set changed")

    authority = document["authority_status"]
    expected_authority = {
        "legal_sponsor": "unresolved",
        "responsible_institution": "unresolved",
        "ethics_pathway": "not_determined_no_self_exemption",
        "hrec_review": "not_started",
        "institutional_lower_risk_or_exemption_determination": (
            "not_started_no_self_exemption"
        ),
        "site_governance": "not_started",
        "privacy_impact_assessment": "draft_template_only",
        "recording_law_review": "not_started",
        "security_review": "not_started",
        "regulatory_assessment": "not_started",
        "research_contracts": "not_started",
    }
    if _exact_object(
        authority, set(expected_authority), "authority_status", errors
    ):
        for field, expected in expected_authority.items():
            _expect(authority[field], expected, f"authority_status.{field}", errors)

    contact_fields = {
        "external_contact_authorised",
        "external_contact_occurred",
        "account_creation_authorised",
        "account_created",
        "spending_authorised",
        "spending_occurred",
        "vendor_selected",
        "redenlab_contacted",
    }
    _all_false(
        document["contact_and_spending"],
        contact_fields,
        "contact_and_spending",
        errors,
    )

    data_fields = {
        "participant_recruitment_authorised",
        "participant_recording_authorised",
        "existing_owner_audio_accessed_for_item_23",
        "existing_audio_repurposed",
        "new_recording_collected",
        "private_research_data_accessed",
        "new_external_provider_transfer_authorised",
        "external_transfer_occurred",
        "normal_pipeline_integration",
        "final_picf_approved",
        "protocol_approved",
        "data_management_plan_approved",
        "complaints_contact_approved",
        "breach_plan_approved",
        "research_storage_location",
        "approved_data_dictionary",
    }
    data = document["research_data"]
    if _exact_object(data, data_fields, "research_data", errors):
        for field in data_fields - {
            "research_storage_location",
            "approved_data_dictionary",
        }:
            if data[field] is not False:
                errors.append(f"research_data.{field} must remain false")
        for field in ("research_storage_location", "approved_data_dictionary"):
            if data[field] is not None:
                errors.append(f"research_data.{field} must remain null")

    task_fields = {
        "task_selected",
        "prompt_selected",
        "protocol_selected",
        "perceptual_instrument_selected",
        "participant_report_instrument_selected",
        "listener_protocol_selected",
        "clinical_reference_selected",
        "annotation_manual_status",
        "voice_reference_manual_status",
        "listener_manual_status",
        "clinical_reference_manual_status",
        "task_burden_and_stop_protocol_status",
    }
    task = document["task_and_reference"]
    if _exact_object(task, task_fields, "task_and_reference", errors):
        for field in task_fields:
            if field.endswith("_selected") and task[field] is not False:
                errors.append(f"task_and_reference.{field} must remain false")
        for field in (
            "annotation_manual_status",
            "voice_reference_manual_status",
            "listener_manual_status",
            "task_burden_and_stop_protocol_status",
        ):
            if task[field] != "requirements_template_only":
                errors.append(f"task_and_reference.{field} changed")
        if task["clinical_reference_manual_status"] != (
            "not_applicable_without_clinical_claim"
        ):
            errors.append("task_and_reference.clinical_reference_manual_status changed")

    split_fields = {
        "prospective_plan_status",
        "numeric_participant_sample_size",
        "numeric_listener_sample_size",
        "numeric_rater_sample_size",
        "primary_endpoint",
        "participant_exclusive",
        "capture_exclusive_where_required",
        "planned_partitions",
        "allocation_method_status",
        "overlap_register_status",
        "held_out_accessed",
    }
    splits = document["sampling_and_splits"]
    if _exact_object(splits, split_fields, "sampling_and_splits", errors):
        for field in (
            "numeric_participant_sample_size",
            "numeric_listener_sample_size",
            "numeric_rater_sample_size",
            "primary_endpoint",
        ):
            if splits[field] is not None:
                errors.append(f"sampling_and_splits.{field} must remain null")
        for field in ("participant_exclusive", "capture_exclusive_where_required"):
            if splits[field] is not True:
                errors.append(f"sampling_and_splits.{field} must remain true")
        if splits["held_out_accessed"] is not False:
            errors.append("sampling_and_splits.held_out_accessed must remain false")
        if splits["planned_partitions"] != [
            "pilot_if_approved",
            "development",
            "tuning",
            "held_out",
        ]:
            errors.append("sampling_and_splits.planned_partitions changed")

    privacy_fields = {
        "responsible_entity_and_data_role_matrix",
        "privacy_act_coverage",
        "health_service_provider_coverage",
        "state_and_territory_health_records_map",
        "recording_and_listening_laws_map",
        "recording_law_review_scope",
        "incidental_speaker_controls_required",
        "app_5_collection_notice_status",
        "app_6_use_and_disclosure_map_status",
        "overseas_processing",
        "secondary_model_training",
        "retention_schedule",
        "withdrawal_and_deletion_rules",
        "breach_and_incident_plan",
        "required_core_consents",
        "optional_consent_choices_default_decline",
        "core_audio_is_required_for_audio_study_participation",
        "consent_may_be_inferred",
        "declining_optional_use_affects_product_access",
    }
    privacy = document["privacy_and_consent"]
    if _exact_object(privacy, privacy_fields, "privacy_and_consent", errors):
        if privacy["responsible_entity_and_data_role_matrix"] is not None:
            errors.append(
                "privacy_and_consent.responsible entity matrix is unresolved"
            )
        if privacy["retention_schedule"] is not None:
            errors.append("privacy_and_consent.retention_schedule is unresolved")
        if privacy["consent_may_be_inferred"] is not False:
            errors.append("privacy_and_consent.consent_may_be_inferred must be false")
        if privacy["declining_optional_use_affects_product_access"] is not False:
            errors.append(
                "privacy_and_consent.declining_optional_use_affects_product_access "
                "must be false"
            )
        required_consents = privacy["required_core_consents"]
        if (
            not isinstance(required_consents, list)
            or len(required_consents) != len(set(required_consents))
            or "research_participation" not in required_consents
            or "audio_recording" not in required_consents
        ):
            errors.append("privacy_and_consent core consents are invalid")
        if privacy["core_audio_is_required_for_audio_study_participation"] is not True:
            errors.append(
                "privacy_and_consent core audio requirement must remain true"
            )

    regulatory_fields = {
        "exact_intended_purpose_frozen",
        "medical_device_status",
        "manufacturer",
        "australian_sponsor",
        "ctn_or_cta_status",
        "exclusion_or_exemption_status",
        "artg_status",
        "candidate_software_use_authorised",
        "public_supply_authorised",
    }
    regulatory = document["regulatory"]
    if _exact_object(regulatory, regulatory_fields, "regulatory", errors):
        for field in (
            "exact_intended_purpose_frozen",
            "candidate_software_use_authorised",
            "public_supply_authorised",
        ):
            if regulatory[field] is not False:
                errors.append(f"regulatory.{field} must remain false")
        for field in ("manufacturer", "australian_sponsor"):
            if regulatory[field] is not None:
                errors.append(f"regulatory.{field} must remain null")

    decision_fields = {
        "checkpoint_state",
        "valid_final_decisions",
        "lane_decisions_are_independent",
        "global_selection_may_hide_lane_no_selection",
        "unresolved_required_authority_forces_no_selection",
        "selection_requires_all_applicable_signed_reviews",
        "checkpoint_complete",
        "current_decision",
    }
    decision = document["decision_rules"]
    if _exact_object(decision, decision_fields, "decision_rules", errors):
        if decision["checkpoint_state"] != (
            "in_progress_external_governance_not_started"
        ):
            errors.append("decision_rules.checkpoint_state changed")
        if decision["valid_final_decisions"] != ["selection", "no_selection"]:
            errors.append("decision_rules.valid_final_decisions changed")
        for field in (
            "lane_decisions_are_independent",
            "unresolved_required_authority_forces_no_selection",
            "selection_requires_all_applicable_signed_reviews",
        ):
            if decision[field] is not True:
                errors.append(f"decision_rules.{field} must remain true")
        for field in (
            "global_selection_may_hide_lane_no_selection",
            "checkpoint_complete",
        ):
            if decision[field] is not False:
                errors.append(f"decision_rules.{field} must remain false")
        if decision["current_decision"] is not None:
            errors.append("decision_rules.current_decision must remain null")

    _all_false(
        document["release_boundaries"],
        RELEASE_FIELDS,
        "release_boundaries",
        errors,
    )

    downstream_fields = {
        "checkpoint_23c_approved",
        "checkpoint_23d_approved",
        "checkpoint_23e_approved",
        "checkpoint_23f_approved",
        "participant_work_may_begin",
        "implementation_may_begin",
        "next_action",
    }
    downstream = document["downstream"]
    if _exact_object(downstream, downstream_fields, "downstream", errors):
        for field in downstream_fields - {"next_action"}:
            if downstream[field] is not False:
                errors.append(f"downstream.{field} must remain false")
        if not isinstance(downstream["next_action"], str) or not downstream[
            "next_action"
        ]:
            errors.append("downstream.next_action must be explicit")

    sources = document["sources"]
    if not isinstance(sources, list):
        errors.append("sources must be an array")
    else:
        seen = set()
        for index, source in enumerate(sources):
            label = f"sources[{index}]"
            if not _exact_object(source, {"source_id", "url"}, label, errors):
                continue
            source_id = source["source_id"]
            if source_id in seen:
                errors.append(f"sources repeats {source_id}")
            seen.add(source_id)
            expected_url = EXPECTED_SOURCES.get(source_id)
            if expected_url is not None:
                _expect(source["url"], expected_url, f"{label}.url", errors)
        if seen != EXPECTED_SOURCE_IDS:
            errors.append("sources set changed")

    return errors


def active_pipeline_leakage(repo_root=REPOSITORY_ROOT):
    """Return active Python files that import or bind the 23B contract."""
    repo_root = Path(repo_root)
    tokens = ("motor_speech_voice", CONTRACT_PATH.name)
    matches = []
    for root_name in ACTIVE_PYTHON_ROOTS:
        active_root = repo_root / root_name
        if not active_root.is_dir():
            matches.append(f"{root_name}/")
            continue
        for path in sorted(active_root.rglob("*.py")):
            try:
                source = path.read_text(encoding="utf-8")
            except OSError:
                matches.append(path.relative_to(repo_root).as_posix())
                continue
            if any(token in source for token in tokens):
                matches.append(path.relative_to(repo_root).as_posix())
    return sorted(set(matches))
