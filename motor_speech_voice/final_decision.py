"""Fail-closed schema for a future final checkpoint 23B decision.

No final decision artifact exists.  This validator defines what a later human
governance closure must prove without storing names, signatures, private paths
or professional advice in the public repository.  It accepts only typed public
evidence metadata, scopes role decisions to their domains, and never authorises
participant work, a score, a threshold, product release, implementation or 23C.
"""

from __future__ import annotations

from datetime import date
import hashlib
import json
from pathlib import Path
import re

from .governance import (
    CONTRACT_PATH,
    CURRENT_CONTRACT_CANONICAL_SHA256,
    EXPECTED_LANE_STATUSES,
    EXPECTED_QUESTION_PROFILES,
    EXPECTED_ROLE_IDS,
    RELEASE_FIELDS,
    canonical_contract_sha256,
    load_governance_contract,
    validate_governance_contract,
)


CURRENT_PARENT_APPROVAL_DATE = date(2026, 8, 14)


FINAL_ROOT_FIELDS = {
    "schema_version",
    "contract_id",
    "record_version",
    "checkpoint",
    "parent_contract",
    "decision_date",
    "evidence_manifest",
    "actor_register",
    "duty_assignments",
    "owner_decision",
    "intended_use",
    "authority_outcomes",
    "role_decisions",
    "deliverable_evidence",
    "lane_decisions",
    "data_access",
    "overall_decision",
    "downstream",
    "release_boundaries",
}

EVIDENCE_FIELDS = {
    "evidence_type",
    "issuer_role_id",
    "subject_assignment_id",
    "version",
    "issued_date",
    "artifact_sha256",
    "sha256",
    "institution_issued_id",
    "storage_class",
    "scope",
    "candidate_question_id",
    "dependency_sha256",
    "status",
}

DUTY_ASSIGNMENT_FIELDS = {
    "construct_control_assignment_id",
    "task_control_assignment_id",
    "reference_truth_assignment_id",
    "threshold_assignment_id",
    "data_custody_assignment_id",
    "release_assignment_id",
    "reference_truth_decision_evidence_id",
}

EVIDENCE_TYPES = {
    "owner_decision",
    "signed_intended_use",
    "prohibited_use_statement",
    "legal_sponsor_identity",
    "responsible_institution_authority",
    "ethics_decision",
    "site_applicability_determination",
    "site_authorisation",
    "privacy_impact_assessment",
    "entity_data_role_matrix",
    "recording_law_review",
    "security_review",
    "statistical_analysis_plan",
    "regulatory_pathway_assessment",
    "source_commercial_rights_review",
    "retention_withdrawal_deletion_plan",
    "manufacturer_identity",
    "australian_trial_sponsor_identity",
    "competence_appointment",
    "conflict_record",
    "role_domain_decision",
    "construct_specification",
    "task_protocol",
    "measure_specification",
    "access_burden_stop_safety_protocol",
    "task_fidelity_manual",
    "annotation_manual",
    "listener_manual",
    "clinical_reference_manual",
    "participant_report_protocol",
    "representation_acquisition_plan",
    "split_allocation_overlap_plan",
    "privacy_consent_data_governance_plan",
    "complaints_incident_plan",
    "lane_decision",
    "overall_decision",
}

SPECIAL_EVIDENCE_ISSUERS = {
    "owner",
    "responsible_institution_authority",
    "institution_review_body",
    "qualified_external_authority",
}

ACTOR_FIELDS = {
    "organisation_id",
    "appointment_evidence_id",
    "classes",
}

ACTOR_CLASSES = {
    "product_owner",
    "developer",
    "candidate_vendor",
    "lived_experience",
    "professional",
    "measurement",
    "statistician",
    "institution",
    "ethics",
    "privacy",
    "australian_legal",
    "security",
    "regulatory",
    "reference_truth",
    "data_custodian",
    "release_decision",
}

ROLE_FIELDS = {
    "role_id",
    "specialty",
    "assignment_id",
    "scope",
    "applicability",
    "outcome",
    "competence_evidence_id",
    "decision_evidence_id",
    "conflict_evidence_id",
    "recused",
    "eligible_to_decide",
    "reason_codes",
}

ROLE_SPECIALTIES = {
    "generic",
    "privacy",
    "australian_legal",
    "security",
}

ROLE_ACTOR_CLASS = {
    "product_owner": "product_owner",
    "paid_lived_experience_governance_group": "lived_experience",
    "independent_adult_motor_speech_cpsp": "professional",
    "independent_adult_voice_cpsp": "professional",
    "independent_clinical_reference_lead_if_required": "professional",
    "independent_ent_or_laryngologist_if_required": "professional",
    "independent_speech_measurement_scientist": "measurement",
    "biostatistician_or_measurement_specialist": "statistician",
    "independent_data_and_split_custodian": "data_custodian",
    "responsible_research_institution": "institution",
    "human_research_ethics_committee_if_required": "ethics",
    "privacy_security_and_australian_legal_review": "privacy",
    "australian_medical_device_regulatory_specialist": "regulatory",
    "independent_truth_and_release_group": "release_decision",
}

DELIVERABLE_FIELDS = {
    "applicability",
    "evidence_id",
    "lane_scope",
    "reason_code",
}

DELIVERABLE_TYPES = {
    "signed_intended_use": "signed_intended_use",
    "prohibited_use_statement": "prohibited_use_statement",
    "access_burden_stop_safety_protocol": (
        "access_burden_stop_safety_protocol"
    ),
    "task_fidelity_manual": "task_fidelity_manual",
    "annotation_manual": "annotation_manual",
    "listener_manual": "listener_manual",
    "clinical_reference_manual": "clinical_reference_manual",
    "participant_report_protocol": "participant_report_protocol",
    "representation_acquisition_plan": "representation_acquisition_plan",
    "statistical_analysis_plan": "statistical_analysis_plan",
    "split_allocation_overlap_plan": "split_allocation_overlap_plan",
    "privacy_consent_data_governance_plan": (
        "privacy_consent_data_governance_plan"
    ),
    "complaints_incident_plan": "complaints_incident_plan",
    "source_commercial_rights_review": "source_commercial_rights_review",
    "regulatory_pathway_assessment": "regulatory_pathway_assessment",
}

DELIVERABLE_ISSUERS = {
    "signed_intended_use": {"owner"},
    "prohibited_use_statement": {"owner"},
    "access_burden_stop_safety_protocol": {"responsible_research_institution"},
    "task_fidelity_manual": {"independent_speech_measurement_scientist"},
    "annotation_manual": {"independent_speech_measurement_scientist"},
    "listener_manual": {"independent_speech_measurement_scientist"},
    "clinical_reference_manual": {
        "independent_clinical_reference_lead_if_required"
    },
    "participant_report_protocol": {"paid_lived_experience_governance_group"},
    "representation_acquisition_plan": {"responsible_research_institution"},
    "statistical_analysis_plan": {"biostatistician_or_measurement_specialist"},
    "split_allocation_overlap_plan": {"independent_data_and_split_custodian"},
    "privacy_consent_data_governance_plan": {
        "privacy_security_and_australian_legal_review"
    },
    "complaints_incident_plan": {"responsible_research_institution"},
    "source_commercial_rights_review": {
        "privacy_security_and_australian_legal_review"
    },
    "regulatory_pathway_assessment": {
        "australian_medical_device_regulatory_specialist"
    },
}

DELIVERABLE_ISSUER_SPECIALTY = {
    "signed_intended_use": ("product_owner", "generic"),
    "prohibited_use_statement": ("product_owner", "generic"),
    "access_burden_stop_safety_protocol": (
        "responsible_research_institution",
        "generic",
    ),
    "task_fidelity_manual": (
        "independent_speech_measurement_scientist",
        "generic",
    ),
    "annotation_manual": (
        "independent_speech_measurement_scientist",
        "generic",
    ),
    "listener_manual": (
        "independent_speech_measurement_scientist",
        "generic",
    ),
    "clinical_reference_manual": (
        "independent_clinical_reference_lead_if_required",
        "generic",
    ),
    "participant_report_protocol": (
        "paid_lived_experience_governance_group",
        "generic",
    ),
    "representation_acquisition_plan": (
        "responsible_research_institution",
        "generic",
    ),
    "statistical_analysis_plan": (
        "biostatistician_or_measurement_specialist",
        "generic",
    ),
    "split_allocation_overlap_plan": (
        "independent_data_and_split_custodian",
        "generic",
    ),
    "privacy_consent_data_governance_plan": (
        "privacy_security_and_australian_legal_review",
        "privacy",
    ),
    "complaints_incident_plan": ("responsible_research_institution", "generic"),
    "source_commercial_rights_review": (
        "privacy_security_and_australian_legal_review",
        "australian_legal",
    ),
    "regulatory_pathway_assessment": (
        "australian_medical_device_regulatory_specialist",
        "generic",
    ),
}

AUTHORITY_EVIDENCE_ISSUERS = {
    "legal_sponsor_evidence_id": {"owner", "qualified_external_authority"},
    "responsible_institution_evidence_id": {"responsible_research_institution"},
    "ethics_decision_evidence_id": {"institution_review_body"},
    "site_applicability_determination_evidence_id": {
        "responsible_research_institution"
    },
    "site_authorisation_evidence_id": {"responsible_research_institution"},
    "entity_data_role_matrix_evidence_id": {
        "privacy_security_and_australian_legal_review"
    },
    "privacy_pia_evidence_id": {
        "privacy_security_and_australian_legal_review"
    },
    "recording_law_evidence_id": {
        "privacy_security_and_australian_legal_review"
    },
    "security_review_evidence_id": {
        "privacy_security_and_australian_legal_review"
    },
    "retention_withdrawal_deletion_evidence_id": {
        "privacy_security_and_australian_legal_review",
        "responsible_research_institution",
    },
    "statistical_plan_evidence_id": {
        "biostatistician_or_measurement_specialist"
    },
    "source_rights_evidence_id": {
        "privacy_security_and_australian_legal_review"
    },
    "manufacturer_evidence_id": {"owner", "qualified_external_authority"},
    "australian_trial_sponsor_evidence_id": {
        "owner",
        "qualified_external_authority",
    },
    "regulatory_assessment_evidence_id": {
        "australian_medical_device_regulatory_specialist"
    },
}

AUTHORITY_ISSUER_SPECIALTY = {
    "legal_sponsor_evidence_id": ("product_owner", "generic"),
    "responsible_institution_evidence_id": (
        "responsible_research_institution",
        "generic",
    ),
    "site_applicability_determination_evidence_id": (
        "responsible_research_institution",
        "generic",
    ),
    "site_authorisation_evidence_id": (
        "responsible_research_institution",
        "generic",
    ),
    "entity_data_role_matrix_evidence_id": (
        "privacy_security_and_australian_legal_review",
        "privacy",
    ),
    "privacy_pia_evidence_id": (
        "privacy_security_and_australian_legal_review",
        "privacy",
    ),
    "recording_law_evidence_id": (
        "privacy_security_and_australian_legal_review",
        "australian_legal",
    ),
    "security_review_evidence_id": (
        "privacy_security_and_australian_legal_review",
        "security",
    ),
    "retention_withdrawal_deletion_evidence_id": (
        "privacy_security_and_australian_legal_review",
        "privacy",
    ),
    "statistical_plan_evidence_id": (
        "biostatistician_or_measurement_specialist",
        "generic",
    ),
    "source_rights_evidence_id": (
        "privacy_security_and_australian_legal_review",
        "australian_legal",
    ),
    "manufacturer_evidence_id": ("product_owner", "generic"),
    "australian_trial_sponsor_evidence_id": ("product_owner", "generic"),
    "regulatory_assessment_evidence_id": (
        "australian_medical_device_regulatory_specialist",
        "generic",
    ),
}

LANE_FIELDS = {
    "decision",
    "candidate_question_id",
    "truth_class",
    "selected_construct_evidence_id",
    "selected_task_evidence_id",
    "selected_measure_evidence_id",
    "selected_score",
    "selected_threshold",
    "required_role_decision_ids",
    "decision_evidence_id",
    "reason_codes",
    "evidence_needed_to_reopen",
}

CORE_CANDIDATE_LANES = {
    "motor_speech",
    "general_speech",
    "voice",
    "controlled_intelligibility",
}

CONDITIONAL_REFERENCE_LANES = {
    "participant_report",
    "clinical_laryngeal_reference",
}

SELECTABLE_CURRENT_QUESTIONS = {
    "controlled_rapid_syllable_timing": (
        "motor_speech",
        "temporal_task_observation",
    ),
    "controlled_rapid_syllable_observable_accuracy": (
        "motor_speech",
        "observable_task_accuracy",
    ),
    "controlled_connected_speech_timing": (
        "general_speech",
        "general_speech_timing",
    ),
    "unfamiliar_listener_intelligibility": (
        "controlled_intelligibility",
        "unfamiliar_listener_transcription",
    ),
}

GLOBAL_SELECTION_DELIVERABLES = {
    "signed_intended_use",
    "prohibited_use_statement",
    "access_burden_stop_safety_protocol",
    "task_fidelity_manual",
    "representation_acquisition_plan",
    "statistical_analysis_plan",
    "split_allocation_overlap_plan",
    "privacy_consent_data_governance_plan",
    "complaints_incident_plan",
    "source_commercial_rights_review",
    "regulatory_pathway_assessment",
}

LANE_SELECTION_DELIVERABLES = {
    "motor_speech": {"annotation_manual"},
    "general_speech": {"annotation_manual"},
    "voice": {"annotation_manual", "participant_report_protocol"},
    "controlled_intelligibility": {"annotation_manual", "listener_manual"},
}

GLOBAL_SELECTION_ROLE_SPECS = {
    ("product_owner", "generic"),
    ("responsible_research_institution", "generic"),
    ("privacy_security_and_australian_legal_review", "privacy"),
    ("privacy_security_and_australian_legal_review", "australian_legal"),
    ("privacy_security_and_australian_legal_review", "security"),
    ("australian_medical_device_regulatory_specialist", "generic"),
    ("independent_data_and_split_custodian", "generic"),
}

LANE_SELECTION_ROLE_SPECS = {
    "motor_speech": {
        ("paid_lived_experience_governance_group", "generic"),
        ("independent_adult_motor_speech_cpsp", "generic"),
        ("independent_speech_measurement_scientist", "generic"),
        ("biostatistician_or_measurement_specialist", "generic"),
        ("independent_truth_and_release_group", "generic"),
    },
    "general_speech": {
        ("paid_lived_experience_governance_group", "generic"),
        ("independent_adult_motor_speech_cpsp", "generic"),
        ("independent_speech_measurement_scientist", "generic"),
        ("biostatistician_or_measurement_specialist", "generic"),
        ("independent_truth_and_release_group", "generic"),
    },
    "voice": {
        ("paid_lived_experience_governance_group", "generic"),
        ("independent_adult_voice_cpsp", "generic"),
        ("independent_speech_measurement_scientist", "generic"),
        ("biostatistician_or_measurement_specialist", "generic"),
        ("independent_truth_and_release_group", "generic"),
    },
    "controlled_intelligibility": {
        ("paid_lived_experience_governance_group", "generic"),
        ("independent_adult_motor_speech_cpsp", "generic"),
        ("independent_speech_measurement_scientist", "generic"),
        ("biostatistician_or_measurement_specialist", "generic"),
        ("independent_truth_and_release_group", "generic"),
    },
}

COMMON_BLOCKING_ROLE_SPECS = set(GLOBAL_SELECTION_ROLE_SPECS) | {
    ("paid_lived_experience_governance_group", "generic"),
    ("independent_speech_measurement_scientist", "generic"),
    ("biostatistician_or_measurement_specialist", "generic"),
    ("independent_truth_and_release_group", "generic"),
    ("human_research_ethics_committee_if_required", "generic"),
}

LANE_BLOCKING_ROLE_SPECS = {
    "motor_speech": COMMON_BLOCKING_ROLE_SPECS
    | {
        ("independent_adult_motor_speech_cpsp", "generic"),
        ("independent_clinical_reference_lead_if_required", "generic"),
        ("independent_ent_or_laryngologist_if_required", "generic"),
    },
    "general_speech": COMMON_BLOCKING_ROLE_SPECS
    | {("independent_adult_motor_speech_cpsp", "generic")},
    "voice": COMMON_BLOCKING_ROLE_SPECS
    | {
        ("independent_adult_voice_cpsp", "generic"),
        ("independent_clinical_reference_lead_if_required", "generic"),
        ("independent_ent_or_laryngologist_if_required", "generic"),
    },
    "controlled_intelligibility": COMMON_BLOCKING_ROLE_SPECS
    | {("independent_adult_motor_speech_cpsp", "generic")},
    "participant_report": {
        ("paid_lived_experience_governance_group", "generic"),
        ("independent_speech_measurement_scientist", "generic"),
        ("responsible_research_institution", "generic"),
        ("human_research_ethics_committee_if_required", "generic"),
    },
    "clinical_laryngeal_reference": {
        ("independent_clinical_reference_lead_if_required", "generic"),
        ("independent_ent_or_laryngologist_if_required", "generic"),
        ("responsible_research_institution", "generic"),
        ("human_research_ethics_committee_if_required", "generic"),
    },
}

PROHIBITED_USE_FIELDS = {
    "product_use",
    "coaching_use",
    "screening_use",
    "clinical_use",
    "diagnosis_use",
    "pathology_use",
    "cause_use",
    "severity_use",
    "prognosis_use",
    "health_or_normality_use",
    "identity_or_conformity_use",
    "combined_score_use",
    "employment_education_insurance_or_eligibility_use",
}

TOKEN_PATTERNS = {
    "evidence": re.compile(r"^evidence:[a-z0-9][a-z0-9._-]{2,80}$"),
    "assignment": re.compile(r"^assignment:[a-z0-9][a-z0-9._-]{2,80}$"),
    "organisation": re.compile(r"^org:[a-z0-9][a-z0-9._-]{2,80}$"),
    "role_decision": re.compile(r"^roledec:[a-z0-9][a-z0-9._-]{2,80}$"),
    "institution": re.compile(r"^institution:[a-z0-9][a-z0-9._-]{2,80}$"),
    "reason": re.compile(r"^[a-z][a-z0-9_]{2,100}$"),
    "version": re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$"),
    "sha256": re.compile(r"^[0-9a-f]{64}$"),
}


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


def _token(value, kind, label, errors, optional=False):
    if optional and value is None:
        return False
    if not isinstance(value, str) or not TOKEN_PATTERNS[kind].fullmatch(value):
        errors.append(f"{label} is not a safe {kind} token")
        return False
    return True


def _choice(value, choices, label, errors):
    if not isinstance(value, str) or value not in choices:
        errors.append(f"{label} is invalid")
        return False
    return True


def _iso_date(value, label, errors, latest=None):
    if not isinstance(value, str):
        errors.append(f"{label} must be an ISO date")
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        errors.append(f"{label} must be an ISO date")
        return None
    if parsed > date.today():
        errors.append(f"{label} cannot be in the future")
    if latest is not None and parsed > latest:
        errors.append(f"{label} cannot be after the decision date")
    return parsed


def _reason_list(value, label, errors, allow_empty=False):
    if not isinstance(value, list):
        errors.append(f"{label} must be an array")
        return False
    if not allow_empty and not value:
        errors.append(f"{label} cannot be empty")
        return False
    if len(value) != len(set(item for item in value if isinstance(item, str))):
        errors.append(f"{label} cannot contain duplicates")
        return False
    valid = True
    for index, item in enumerate(value):
        if not isinstance(item, str) or not TOKEN_PATTERNS["reason"].fullmatch(item):
            errors.append(f"{label}[{index}] is not a reason code")
            valid = False
    return valid


def _scope(value, label, errors, allow_empty=False):
    if not isinstance(value, list):
        errors.append(f"{label} must be an array")
        return False
    if not allow_empty and not value:
        errors.append(f"{label} cannot be empty")
        return False
    if any(not isinstance(item, str) for item in value):
        errors.append(f"{label} must contain strings")
        return False
    if len(value) != len(set(value)):
        errors.append(f"{label} cannot contain duplicates")
        return False
    allowed = set(EXPECTED_LANE_STATUSES) | {"global"}
    if any(item not in allowed for item in value):
        errors.append(f"{label} contains an unknown scope")
        return False
    if "global" in value and len(value) != 1:
        errors.append(f"{label} cannot mix global and lane scopes")
        return False
    return True


def _scope_covers(evidence_scope, declared_scope):
    if not isinstance(evidence_scope, list) or not isinstance(declared_scope, list):
        return False
    if any(not isinstance(item, str) for item in evidence_scope + declared_scope):
        return False
    if "global" in evidence_scope:
        return True
    if "global" in declared_scope:
        return False
    return set(declared_scope).issubset(set(evidence_scope))


def evidence_node_sha256(evidence):
    """Hash one public evidence node, including its issued-artifact digest.

    The node hash is the identity used by the dependency graph.  The referenced
    issued artifact must itself attest the same claims; verifying that private
    signature and substance remains an authorised human responsibility.
    """
    payload = {
        field: evidence.get(field)
        for field in sorted(EVIDENCE_FIELDS - {"sha256"})
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _evidence_reference(
    evidence_id,
    expected_type,
    label,
    errors,
    evidence_manifest,
    required=True,
    lane=None,
    issuer_role_id=None,
    subject_assignment_id=None,
):
    if not required and evidence_id is None:
        return None
    if not _token(evidence_id, "evidence", label, errors):
        return None
    evidence = evidence_manifest.get(evidence_id)
    if evidence is None:
        errors.append(f"{label} references unknown evidence")
        return None
    if evidence.get("evidence_type") != expected_type:
        errors.append(f"{label} references the wrong evidence type")
    if lane is not None:
        scope = evidence.get("scope")
        if isinstance(scope, list) and "global" not in scope and lane not in scope:
            errors.append(f"{label} evidence does not cover {lane}")
    if issuer_role_id is not None and evidence.get("issuer_role_id") != issuer_role_id:
        errors.append(f"{label} has the wrong issuing role")
    if (
        subject_assignment_id is not None
        and evidence.get("subject_assignment_id") != subject_assignment_id
    ):
        errors.append(f"{label} has the wrong assignment subject")
    return evidence


def _candidate_binding(evidence, question_id, dependency_hashes, label, errors):
    if evidence is None:
        return
    if evidence.get("candidate_question_id") != question_id:
        errors.append(f"{label} is not bound to the selected candidate")
    dependencies = evidence.get("dependency_sha256")
    actual = {
        item for item in dependencies if isinstance(item, str)
    } if isinstance(dependencies, list) else set()
    if not isinstance(dependencies, list) or actual != set(dependency_hashes):
        errors.append(f"{label} does not exactly bind its permitted dependencies")


def _safe_record_lookup(records, record_id):
    if not isinstance(record_id, str):
        return None
    return records.get(record_id)


def _explicit_evidence_ids(document):
    """Return evidence IDs cited by semantic fields, excluding hash-only links."""
    evidence_ids = set()

    def add(value):
        if isinstance(value, str):
            evidence_ids.add(value)

    owner = document.get("owner_decision")
    if isinstance(owner, dict):
        add(owner.get("owner_decision_evidence_id"))
    intended = document.get("intended_use")
    if isinstance(intended, dict):
        add(intended.get("evidence_id"))
    authority = document.get("authority_outcomes")
    if isinstance(authority, dict):
        for field, value in authority.items():
            if field.endswith("_evidence_id"):
                add(value)
    actors = document.get("actor_register")
    if isinstance(actors, dict):
        for actor in actors.values():
            if isinstance(actor, dict):
                add(actor.get("appointment_evidence_id"))
    duties = document.get("duty_assignments")
    if isinstance(duties, dict):
        add(duties.get("reference_truth_decision_evidence_id"))
    roles = document.get("role_decisions")
    if isinstance(roles, dict):
        for record in roles.values():
            if not isinstance(record, dict):
                continue
            for field in (
                "competence_evidence_id",
                "decision_evidence_id",
                "conflict_evidence_id",
            ):
                add(record.get(field))
    deliverables = document.get("deliverable_evidence")
    if isinstance(deliverables, dict):
        for record in deliverables.values():
            if isinstance(record, dict):
                add(record.get("evidence_id"))
    lanes = document.get("lane_decisions")
    if isinstance(lanes, dict):
        for lane in lanes.values():
            if not isinstance(lane, dict):
                continue
            for field in (
                "selected_construct_evidence_id",
                "selected_task_evidence_id",
                "selected_measure_evidence_id",
                "decision_evidence_id",
            ):
                add(lane.get(field))
    overall = document.get("overall_decision")
    if isinstance(overall, dict):
        add(overall.get("decision_evidence_id"))
    return evidence_ids


def _validate_dependency_graph(valid_manifest, errors):
    """Require a closed, acyclic and chronological evidence dependency graph."""
    digest_to_id = {
        evidence.get("sha256"): evidence_id
        for evidence_id, evidence in valid_manifest.items()
        if isinstance(evidence.get("sha256"), str)
    }
    dependency_ids = {}
    for evidence_id, evidence in valid_manifest.items():
        dependency_ids[evidence_id] = []
        issued = None
        issued_value = evidence.get("issued_date")
        if isinstance(issued_value, str):
            try:
                issued = date.fromisoformat(issued_value)
            except ValueError:
                pass
        dependencies = evidence.get("dependency_sha256")
        if not isinstance(dependencies, list):
            continue
        for dependency in dependencies:
            if dependency == CURRENT_CONTRACT_CANONICAL_SHA256:
                dependency_date = CURRENT_PARENT_APPROVAL_DATE
            else:
                dependency_id = digest_to_id.get(dependency)
                if dependency_id is None:
                    errors.append(
                        f"evidence_manifest.{evidence_id} has an unknown dependency hash"
                    )
                    continue
                dependency_ids[evidence_id].append(dependency_id)
                dependency_date = None
                dependency_value = valid_manifest[dependency_id].get("issued_date")
                if isinstance(dependency_value, str):
                    try:
                        dependency_date = date.fromisoformat(dependency_value)
                    except ValueError:
                        pass
            if (
                issued is not None
                and dependency_date is not None
                and dependency_date > issued
            ):
                errors.append(
                    f"evidence_manifest.{evidence_id} predates one of its dependencies"
                )

    visiting = set()
    visited = set()

    def visit(evidence_id):
        if evidence_id in visiting:
            errors.append("evidence dependency graph contains a cycle")
            return
        if evidence_id in visited:
            return
        visiting.add(evidence_id)
        for dependency_id in dependency_ids.get(evidence_id, []):
            visit(dependency_id)
        visiting.remove(evidence_id)
        visited.add(evidence_id)

    for evidence_id in valid_manifest:
        visit(evidence_id)


def _role_records_for(role_decisions, role_id, specialty, lane):
    records = []
    for record_id, record in role_decisions.items():
        if not isinstance(record, dict):
            continue
        scope = record.get("scope")
        if (
            record.get("role_id") == role_id
            and record.get("specialty") == specialty
            and isinstance(scope, list)
            and ("global" in scope or lane in scope)
        ):
            records.append((record_id, record))
    return records


def validate_final_governance_decision(document):
    """Return errors in one proposed final 23B artifact without raising."""
    errors = []
    if not _exact_object(document, FINAL_ROOT_FIELDS, "final_decision", errors):
        return errors

    for field, expected in {
        "schema_version": "1.0.0",
        "contract_id": "motor_speech_voice_governance_final",
        "checkpoint": "23B",
    }.items():
        if document[field] != expected or type(document[field]) is not type(expected):
            errors.append(f"{field} changed")
    _token(document["record_version"], "version", "record_version", errors)
    decision_date = _iso_date(document["decision_date"], "decision_date", errors)
    if (
        decision_date is not None
        and decision_date < CURRENT_PARENT_APPROVAL_DATE
    ):
        errors.append("decision_date cannot predate the approved parent contract")

    parent_fields = {"contract_id", "contract_version", "canonical_sha256"}
    parent = document["parent_contract"]
    if _exact_object(parent, parent_fields, "parent_contract", errors):
        expected_parent = {
            "contract_id": "motor_speech_voice_governance",
            "contract_version": "1.0.0",
            "canonical_sha256": CURRENT_CONTRACT_CANONICAL_SHA256,
        }
        for field, expected in expected_parent.items():
            if parent[field] != expected:
                errors.append(f"parent_contract.{field} changed")

    manifest = document["evidence_manifest"]
    valid_manifest = {}
    if not isinstance(manifest, dict):
        errors.append("evidence_manifest must be an object")
    else:
        for evidence_id, evidence in manifest.items():
            label = f"evidence_manifest.{evidence_id}"
            if not _token(evidence_id, "evidence", label, errors):
                continue
            if not _exact_object(evidence, EVIDENCE_FIELDS, label, errors):
                continue
            _choice(
                evidence["evidence_type"],
                EVIDENCE_TYPES,
                f"{label}.evidence_type",
                errors,
            )
            issuer = evidence["issuer_role_id"]
            if not isinstance(issuer, str) or issuer not in (
                EXPECTED_ROLE_IDS | SPECIAL_EVIDENCE_ISSUERS
            ):
                errors.append(f"{label}.issuer_role_id is invalid")
            _token(
                evidence["subject_assignment_id"],
                "assignment",
                f"{label}.subject_assignment_id",
                errors,
                optional=True,
            )
            _token(evidence["version"], "version", f"{label}.version", errors)
            evidence_date = _iso_date(
                evidence["issued_date"],
                f"{label}.issued_date",
                errors,
                latest=decision_date,
            )
            if (
                evidence_date is not None
                and evidence_date < CURRENT_PARENT_APPROVAL_DATE
            ):
                errors.append(
                    f"{label}.issued_date cannot predate the approved parent contract"
                )
            _token(
                evidence["artifact_sha256"],
                "sha256",
                f"{label}.artifact_sha256",
                errors,
            )
            _token(evidence["sha256"], "sha256", f"{label}.sha256", errors)
            _token(
                evidence["institution_issued_id"],
                "institution",
                f"{label}.institution_issued_id",
                errors,
                optional=True,
            )
            _choice(
                evidence["storage_class"],
                {"approved_private_governance", "institution_system", "public_record"},
                f"{label}.storage_class",
                errors,
            )
            _scope(evidence["scope"], f"{label}.scope", errors)
            candidate_question_id = evidence["candidate_question_id"]
            if candidate_question_id is not None and (
                not isinstance(candidate_question_id, str)
                or candidate_question_id not in EXPECTED_QUESTION_PROFILES
            ):
                errors.append(f"{label}.candidate_question_id is invalid")
            if (
                evidence["evidence_type"] == "competence_appointment"
                and candidate_question_id is not None
            ):
                errors.append(
                    f"{label}.candidate_question_id must be null for reusable competence evidence"
                )
            dependencies = evidence["dependency_sha256"]
            if (
                not isinstance(dependencies, list)
                or any(
                    not isinstance(item, str)
                    or not TOKEN_PATTERNS["sha256"].fullmatch(item)
                    for item in dependencies
                )
                or len(dependencies) != len(set(dependencies))
            ):
                errors.append(f"{label}.dependency_sha256 is invalid")
            if evidence["status"] != "issued_final":
                errors.append(f"{label}.status must be issued_final")
            evidence_shape_is_safe = (
                isinstance(evidence["evidence_type"], str)
                and isinstance(evidence["issuer_role_id"], str)
                and (
                    evidence["subject_assignment_id"] is None
                    or isinstance(evidence["subject_assignment_id"], str)
                )
                and isinstance(evidence["version"], str)
                and isinstance(evidence["issued_date"], str)
                and isinstance(evidence["artifact_sha256"], str)
                and isinstance(evidence["sha256"], str)
                and (
                    evidence["institution_issued_id"] is None
                    or isinstance(evidence["institution_issued_id"], str)
                )
                and isinstance(evidence["storage_class"], str)
                and isinstance(evidence["scope"], list)
                and all(isinstance(item, str) for item in evidence["scope"])
                and (
                    evidence["candidate_question_id"] is None
                    or isinstance(evidence["candidate_question_id"], str)
                )
                and isinstance(evidence["dependency_sha256"], list)
                and all(
                    isinstance(item, str)
                    for item in evidence["dependency_sha256"]
                )
                and isinstance(evidence["status"], str)
            )
            if evidence_shape_is_safe:
                if evidence["sha256"] != evidence_node_sha256(evidence):
                    errors.append(
                        f"{label}.sha256 does not bind the complete evidence node"
                    )
                valid_manifest[evidence_id] = evidence

        digest_ids = {}
        artifact_digest_ids = {}
        for evidence_id, evidence in valid_manifest.items():
            digest = evidence.get("sha256")
            if not isinstance(digest, str):
                continue
            if digest == CURRENT_CONTRACT_CANONICAL_SHA256:
                errors.append(
                    f"evidence_manifest.{evidence_id} cannot reuse the parent contract digest"
                )
            previous_id = digest_ids.get(digest)
            if previous_id is not None and previous_id != evidence_id:
                errors.append(
                    f"evidence_manifest.{evidence_id} duplicates the digest of {previous_id}; shared evidence must reuse one ID"
                )
            digest_ids[digest] = evidence_id
            artifact_digest = evidence.get("artifact_sha256")
            if artifact_digest == CURRENT_CONTRACT_CANONICAL_SHA256:
                errors.append(
                    f"evidence_manifest.{evidence_id} cannot reuse the parent contract as its issued artifact"
                )
            previous_artifact_id = artifact_digest_ids.get(artifact_digest)
            if (
                previous_artifact_id is not None
                and previous_artifact_id != evidence_id
            ):
                errors.append(
                    f"evidence_manifest.{evidence_id} duplicates the issued artifact digest of {previous_artifact_id}; shared evidence must reuse one ID"
                )
            artifact_digest_ids[artifact_digest] = evidence_id

            if (
                evidence.get("candidate_question_id") is None
                and evidence.get("evidence_type")
                not in {"lane_decision", "overall_decision"}
                and not set(evidence.get("dependency_sha256", [])).issubset(
                    {CURRENT_CONTRACT_CANONICAL_SHA256}
                )
            ):
                errors.append(
                    f"evidence_manifest.{evidence_id} candidate-neutral evidence has unrelated dependencies"
                )

        explicit_evidence_ids = _explicit_evidence_ids(document)
        for evidence_id in valid_manifest:
            if evidence_id not in explicit_evidence_ids:
                errors.append(
                    f"evidence_manifest.{evidence_id} is not cited by a semantic record"
                )
        _validate_dependency_graph(valid_manifest, errors)

    actors = document["actor_register"]
    valid_actors = {}
    if not isinstance(actors, dict):
        errors.append("actor_register must be an object")
    else:
        for assignment_id, actor in actors.items():
            label = f"actor_register.{assignment_id}"
            if not _token(assignment_id, "assignment", label, errors):
                continue
            if not _exact_object(actor, ACTOR_FIELDS, label, errors):
                continue
            _token(
                actor["organisation_id"],
                "organisation",
                f"{label}.organisation_id",
                errors,
            )
            _evidence_reference(
                actor["appointment_evidence_id"],
                "competence_appointment",
                f"{label}.appointment_evidence_id",
                errors,
                valid_manifest,
                subject_assignment_id=assignment_id,
            )
            classes = actor["classes"]
            if (
                not isinstance(classes, list)
                or not classes
                or any(not isinstance(item, str) or item not in ACTOR_CLASSES for item in classes)
                or len(classes) != len(set(classes))
            ):
                errors.append(f"{label}.classes are invalid")
            elif len(classes) > 1 and frozenset(classes) not in {
                frozenset({"product_owner", "developer"}),
                frozenset({"candidate_vendor", "developer"}),
            }:
                errors.append(f"{label}.classes silently combine independent duties")
            if (
                isinstance(actor["organisation_id"], str)
                and isinstance(actor["appointment_evidence_id"], str)
                and isinstance(classes, list)
                and all(isinstance(item, str) for item in classes)
            ):
                valid_actors[assignment_id] = actor

    for evidence_id, evidence in valid_manifest.items():
        subject = evidence.get("subject_assignment_id")
        if subject is not None and subject not in valid_actors:
            errors.append(f"evidence_manifest.{evidence_id} has an unknown subject")

    duties = document["duty_assignments"]
    valid_duties = {}
    if _exact_object(
        duties,
        DUTY_ASSIGNMENT_FIELDS,
        "duty_assignments",
        errors,
    ):
        duty_classes = {
            "reference_truth_assignment_id": "reference_truth",
            "data_custody_assignment_id": "data_custodian",
            "release_assignment_id": "release_decision",
        }
        for field in DUTY_ASSIGNMENT_FIELDS:
            value = duties[field]
            if value is None:
                valid_duties[field] = None
                continue
            if field == "reference_truth_decision_evidence_id":
                if _token(
                    value,
                    "evidence",
                    f"duty_assignments.{field}",
                    errors,
                ):
                    valid_duties[field] = value
                continue
            assignment_id = value
            if not _token(
                assignment_id,
                "assignment",
                f"duty_assignments.{field}",
                errors,
            ):
                continue
            actor = valid_actors.get(assignment_id)
            if actor is None:
                errors.append(
                    f"duty_assignments.{field} references an unknown assignment"
                )
                continue
            required_class = duty_classes.get(field)
            if required_class is not None and required_class not in actor.get(
                "classes", []
            ):
                errors.append(
                    f"duty_assignments.{field} has the wrong actor class"
                )
            valid_duties[field] = assignment_id

    owner_fields = {
        "owner_decision_evidence_id",
        "adults_first_confirmed",
        "children_excluded",
    }
    owner = document["owner_decision"]
    accountable_owner_assignment = None
    if _exact_object(owner, owner_fields, "owner_decision", errors):
        owner_decision_evidence = _evidence_reference(
            owner["owner_decision_evidence_id"],
            "owner_decision",
            "owner_decision.owner_decision_evidence_id",
            errors,
            valid_manifest,
            issuer_role_id="owner",
        )
        owner_actor = (
            _safe_record_lookup(
                valid_actors,
                owner_decision_evidence.get("subject_assignment_id"),
            )
            if isinstance(owner_decision_evidence, dict)
            else None
        )
        if owner_actor is None or "product_owner" not in owner_actor.get(
            "classes", []
        ):
            errors.append("owner decision must identify a product-owner assignment")
        elif isinstance(owner_decision_evidence, dict):
            accountable_owner_assignment = owner_decision_evidence.get(
                "subject_assignment_id"
            )
        if owner["adults_first_confirmed"] is not True:
            errors.append("owner_decision.adults_first_confirmed must be true")
        if owner["children_excluded"] is not True:
            errors.append("owner_decision.children_excluded must be true")
    product_owner_assignments = {
        assignment_id
        for assignment_id, actor in valid_actors.items()
        if "product_owner" in actor.get("classes", [])
    }
    if len(product_owner_assignments) != 1:
        errors.append("final decision requires exactly one product-owner assignment")
    elif (
        accountable_owner_assignment is not None
        and accountable_owner_assignment not in product_owner_assignments
    ):
        errors.append("accountable owner does not match the sole product-owner assignment")

    intended_fields = {
        "status",
        "evidence_id",
        "user",
        "population",
        "setting",
        "input_source",
        "action",
        "claim_level",
    } | PROHIBITED_USE_FIELDS
    intended = document["intended_use"]
    if _exact_object(intended, intended_fields, "intended_use", errors):
        _choice(
            intended["status"],
            {"unsigned_no_selection_draft", "signed_selection_use"},
            "intended_use.status",
            errors,
        )
        _evidence_reference(
            intended["evidence_id"],
            "signed_intended_use",
            "intended_use.evidence_id",
            errors,
            valid_manifest,
            required=intended["status"] == "signed_selection_use",
        )
        expected_values = {
            "user": "firewalled_developer_research_team",
            "population": "consenting_adults_18_and_over",
            "setting": "offline_controlled_research",
            "input_source": "new_task_specific_recording_under_approved_protocol",
            "action": "isolated_checkpoint_23c_feasibility_only",
            "claim_level": "nonclinical_task_specific_observation",
        }
        for field, expected in expected_values.items():
            if intended[field] != expected:
                errors.append(f"intended_use.{field} changed")
        for field in PROHIBITED_USE_FIELDS:
            if intended[field] is not False:
                errors.append(f"intended_use.{field} must remain false")
    else:
        intended = {}

    authority_fields = {
        "legal_sponsor_evidence_id",
        "responsible_institution_evidence_id",
        "ethics_pathway",
        "ethics_decision_evidence_id",
        "site_governance_applicability",
        "site_applicability_determination_evidence_id",
        "site_authorisation_evidence_id",
        "privacy_act_coverage",
        "health_service_provider_coverage",
        "entity_data_role_matrix_evidence_id",
        "privacy_pia_evidence_id",
        "recording_law_evidence_id",
        "security_review_evidence_id",
        "retention_withdrawal_deletion_evidence_id",
        "app_5_collection_notice_status",
        "app_6_use_and_disclosure_status",
        "incidental_speaker_controls_status",
        "consent_materials_status",
        "overseas_processing",
        "secondary_model_training",
        "statistical_plan_evidence_id",
        "source_rights_evidence_id",
        "medical_device_status",
        "clinical_trial_pathway_status",
        "manufacturer_evidence_id",
        "australian_trial_sponsor_evidence_id",
        "regulatory_assessment_evidence_id",
    }
    authority = document["authority_outcomes"]
    if _exact_object(authority, authority_fields, "authority_outcomes", errors):
        evidence_types = {
            "legal_sponsor_evidence_id": "legal_sponsor_identity",
            "responsible_institution_evidence_id": (
                "responsible_institution_authority"
            ),
            "ethics_decision_evidence_id": "ethics_decision",
            "site_applicability_determination_evidence_id": (
                "site_applicability_determination"
            ),
            "site_authorisation_evidence_id": "site_authorisation",
            "entity_data_role_matrix_evidence_id": "entity_data_role_matrix",
            "privacy_pia_evidence_id": "privacy_impact_assessment",
            "recording_law_evidence_id": "recording_law_review",
            "security_review_evidence_id": "security_review",
            "retention_withdrawal_deletion_evidence_id": (
                "retention_withdrawal_deletion_plan"
            ),
            "statistical_plan_evidence_id": "statistical_analysis_plan",
            "source_rights_evidence_id": "source_commercial_rights_review",
            "manufacturer_evidence_id": "manufacturer_identity",
            "australian_trial_sponsor_evidence_id": (
                "australian_trial_sponsor_identity"
            ),
            "regulatory_assessment_evidence_id": (
                "regulatory_pathway_assessment"
            ),
        }
        for field, evidence_type in evidence_types.items():
            linked_evidence = _evidence_reference(
                authority[field],
                evidence_type,
                f"authority_outcomes.{field}",
                errors,
                valid_manifest,
                required=False,
            )
            if (
                linked_evidence is not None
                and linked_evidence.get("issuer_role_id")
                not in AUTHORITY_EVIDENCE_ISSUERS[field]
            ):
                errors.append(f"authority_outcomes.{field} has the wrong issuer")
        _choice(
            authority["ethics_pathway"],
            {"unresolved", "hrec", "institutional_lower_risk", "institutional_exemption"},
            "authority_outcomes.ethics_pathway",
            errors,
        )
        _choice(
            authority["site_governance_applicability"],
            {"unresolved", "required", "not_applicable"},
            "authority_outcomes.site_governance_applicability",
            errors,
        )
        _choice(
            authority["privacy_act_coverage"],
            {"unresolved", "one_or_more_app_entities", "no_app_entity_qualified_determination"},
            "authority_outcomes.privacy_act_coverage",
            errors,
        )
        _choice(
            authority["health_service_provider_coverage"],
            {"unresolved", "applies", "does_not_apply_qualified_determination"},
            "authority_outcomes.health_service_provider_coverage",
            errors,
        )
        _choice(
            authority["overseas_processing"],
            {"unresolved", "prohibited"},
            "authority_outcomes.overseas_processing",
            errors,
        )
        for field in (
            "app_5_collection_notice_status",
            "app_6_use_and_disclosure_status",
            "incidental_speaker_controls_status",
            "consent_materials_status",
        ):
            _choice(
                authority[field],
                {"unresolved", "approved_for_exact_protocol"},
                f"authority_outcomes.{field}",
                errors,
            )
        _choice(
            authority["secondary_model_training"],
            {"unresolved", "prohibited"},
            "authority_outcomes.secondary_model_training",
            errors,
        )
        _choice(
            authority["medical_device_status"],
            {"unresolved", "outside_definition", "excluded", "exempt", "medical_device"},
            "authority_outcomes.medical_device_status",
            errors,
        )
        _choice(
            authority["clinical_trial_pathway_status"],
            {"unresolved", "not_applicable", "ctn_required", "cta_required"},
            "authority_outcomes.clinical_trial_pathway_status",
            errors,
        )
        if (
            authority["health_service_provider_coverage"] == "applies"
            and authority["privacy_act_coverage"] != "one_or_more_app_entities"
        ):
            errors.append(
                "health service provider coverage requires one or more APP entities"
            )
        if (
            authority["privacy_act_coverage"]
            == "no_app_entity_qualified_determination"
            and authority["health_service_provider_coverage"]
            != "does_not_apply_qualified_determination"
        ):
            errors.append(
                "a no APP entity determination requires health service provider non-coverage"
            )
        if (
            authority["medical_device_status"]
            in ("outside_definition", "excluded", "exempt")
            and authority["clinical_trial_pathway_status"] != "not_applicable"
        ):
            errors.append(
                "an outside-definition, excluded or exempt device path cannot require CTN or CTA"
            )
        if (
            authority["clinical_trial_pathway_status"]
            in ("ctn_required", "cta_required")
            and authority["medical_device_status"] != "medical_device"
        ):
            errors.append("CTN or CTA requires a medical-device determination")
        if authority["clinical_trial_pathway_status"] in (
            "ctn_required",
            "cta_required",
        ):
            if authority["ethics_pathway"] != "hrec":
                errors.append("CTN or CTA requires HREC ethics approval")
            if authority["site_governance_applicability"] != "required":
                errors.append("CTN or CTA requires site governance authorisation")
    else:
        authority = {}

    role_decisions = document["role_decisions"]
    valid_roles = {}
    if not isinstance(role_decisions, dict):
        errors.append("role_decisions must be an object")
    else:
        for record_id, record in role_decisions.items():
            label = f"role_decisions.{record_id}"
            if not _token(record_id, "role_decision", label, errors):
                continue
            if not _exact_object(record, ROLE_FIELDS, label, errors):
                continue
            role_id = record["role_id"]
            if not isinstance(role_id, str) or role_id not in EXPECTED_ROLE_IDS:
                errors.append(f"{label}.role_id is invalid")
                continue
            specialty = record["specialty"]
            if not _choice(
                specialty,
                ROLE_SPECIALTIES,
                f"{label}.specialty",
                errors,
            ):
                specialty = None
            if role_id == "privacy_security_and_australian_legal_review":
                if specialty not in {"privacy", "australian_legal", "security"}:
                    errors.append(f"{label} requires a privacy, legal or security specialty")
            elif specialty != "generic":
                errors.append(f"{label}.specialty must be generic for this role")
            assignment_id = record["assignment_id"]
            _token(assignment_id, "assignment", f"{label}.assignment_id", errors)
            actor = (
                valid_actors.get(assignment_id)
                if isinstance(assignment_id, str)
                else None
            )
            if actor is None:
                errors.append(f"{label}.assignment_id is not in the actor register")
            elif ROLE_ACTOR_CLASS.get(role_id) not in actor.get("classes", []):
                if not (
                    role_id == "privacy_security_and_australian_legal_review"
                    and specialty in actor.get("classes", [])
                ):
                    errors.append(f"{label}.assignment has the wrong actor class")
            _scope(record["scope"], f"{label}.scope", errors)
            _choice(
                record["applicability"],
                {"required", "not_applicable"},
                f"{label}.applicability",
                errors,
            )
            outcome = record["outcome"]
            signed = isinstance(outcome, str) and outcome in {
                "signed_no_unresolved_block",
                "signed_block",
            }
            _choice(
                outcome,
                {
                    "signed_no_unresolved_block",
                    "signed_block",
                    "unfilled_blocks_selection",
                    "not_applicable",
                },
                f"{label}.outcome",
                errors,
            )
            for field, evidence_type in {
                "competence_evidence_id": "competence_appointment",
                "decision_evidence_id": "role_domain_decision",
                "conflict_evidence_id": "conflict_record",
            }.items():
                linked_evidence = _evidence_reference(
                    record[field],
                    evidence_type,
                    f"{label}.{field}",
                    errors,
                    valid_manifest,
                    required=signed,
                    issuer_role_id=role_id if field == "decision_evidence_id" else None,
                    subject_assignment_id=assignment_id,
                )
                if (
                    signed
                    and linked_evidence is not None
                    and not _scope_covers(linked_evidence.get("scope"), record["scope"])
                ):
                    errors.append(f"{label}.{field} does not cover the role scope")
                if not signed and record[field] is not None:
                    errors.append(f"{label}.{field} must be null without a signed outcome")
            if record["applicability"] == "not_applicable" and record[
                "outcome"
            ] != "not_applicable":
                errors.append(f"{label} not-applicable role has an outcome")
            if record["applicability"] == "required" and record[
                "outcome"
            ] == "not_applicable":
                errors.append(f"{label} required role cannot be not applicable")
            if signed:
                if record["recused"] is not False:
                    errors.append(f"{label} signed outcome cannot be recused")
                if record["eligible_to_decide"] is not True:
                    errors.append(f"{label} signed outcome must be eligible to decide")
            elif not isinstance(record["recused"], bool) or not isinstance(
                record["eligible_to_decide"], bool
            ):
                errors.append(f"{label} recusal and eligibility must be boolean")
            _reason_list(record["reason_codes"], f"{label}.reason_codes", errors)
            role_shape_is_safe = (
                isinstance(record["role_id"], str)
                and isinstance(record["specialty"], str)
                and isinstance(record["assignment_id"], str)
                and isinstance(record["scope"], list)
                and all(isinstance(item, str) for item in record["scope"])
                and isinstance(record["applicability"], str)
                and isinstance(record["outcome"], str)
                and all(
                    record[field] is None or isinstance(record[field], str)
                    for field in (
                        "competence_evidence_id",
                        "decision_evidence_id",
                        "conflict_evidence_id",
                    )
                )
                and isinstance(record["recused"], bool)
                and isinstance(record["eligible_to_decide"], bool)
                and isinstance(record["reason_codes"], list)
                and all(
                    isinstance(item, str) for item in record["reason_codes"]
                )
            )
            if role_shape_is_safe:
                valid_roles[record_id] = record

    deliverables = document["deliverable_evidence"]
    valid_deliverables = {}
    if not _exact_object(
        deliverables,
        set(DELIVERABLE_TYPES),
        "deliverable_evidence",
        errors,
    ):
        deliverables = {}
    else:
        for deliverable_id, record in deliverables.items():
            label = f"deliverable_evidence.{deliverable_id}"
            if not _exact_object(record, DELIVERABLE_FIELDS, label, errors):
                continue
            _choice(
                record["applicability"],
                {"required", "not_applicable", "unresolved"},
                f"{label}.applicability",
                errors,
            )
            _scope(record["lane_scope"], f"{label}.lane_scope", errors, allow_empty=True)
            _reason_list([record["reason_code"]], f"{label}.reason_code", errors)
            required = record["applicability"] == "required"
            linked_evidence = _evidence_reference(
                record["evidence_id"],
                DELIVERABLE_TYPES[deliverable_id],
                f"{label}.evidence_id",
                errors,
                valid_manifest,
                required=required,
            )
            if (
                required
                and linked_evidence is not None
                and not _scope_covers(
                    linked_evidence.get("scope"), record["lane_scope"]
                )
            ):
                errors.append(f"{label}.evidence_id does not cover its lane scope")
            if (
                required
                and linked_evidence is not None
                and linked_evidence.get("issuer_role_id")
                not in DELIVERABLE_ISSUERS[deliverable_id]
            ):
                errors.append(f"{label}.evidence_id has the wrong issuing role")
            if not required and record["evidence_id"] is not None:
                errors.append(f"{label}.evidence_id must be null unless required")
            deliverable_shape_is_safe = (
                isinstance(record["applicability"], str)
                and (
                    record["evidence_id"] is None
                    or isinstance(record["evidence_id"], str)
                )
                and isinstance(record["lane_scope"], list)
                and all(isinstance(item, str) for item in record["lane_scope"])
                and isinstance(record["reason_code"], str)
            )
            if deliverable_shape_is_safe:
                valid_deliverables[deliverable_id] = record

    lanes = document["lane_decisions"]
    valid_lanes = {}
    selected_lanes = []
    if _exact_object(lanes, set(EXPECTED_LANE_STATUSES), "lane_decisions", errors):
        for lane_id, lane in lanes.items():
            label = f"lane_decisions.{lane_id}"
            if not _exact_object(lane, LANE_FIELDS, label, errors):
                continue
            lane_shape_is_safe = (
                isinstance(lane["decision"], str)
                and (
                    lane["candidate_question_id"] is None
                    or isinstance(lane["candidate_question_id"], str)
                )
                and (
                    lane["truth_class"] is None
                    or isinstance(lane["truth_class"], str)
                )
                and all(
                    lane[field] is None or isinstance(lane[field], str)
                    for field in (
                        "selected_construct_evidence_id",
                        "selected_task_evidence_id",
                        "selected_measure_evidence_id",
                    )
                )
                and isinstance(lane["required_role_decision_ids"], list)
                and all(
                    isinstance(item, str)
                    for item in lane["required_role_decision_ids"]
                )
                and isinstance(lane["decision_evidence_id"], str)
                and isinstance(lane["reason_codes"], list)
                and all(isinstance(item, str) for item in lane["reason_codes"])
                and isinstance(lane["evidence_needed_to_reopen"], list)
                and all(
                    isinstance(item, str)
                    for item in lane["evidence_needed_to_reopen"]
                )
            )
            decision = lane["decision"]
            if lane_id in CORE_CANDIDATE_LANES:
                allowed_decisions = {"selection", "no_selection"}
            else:
                allowed_decisions = {
                    "required_reference",
                    "not_required",
                    "unavailable",
                }
            if not _choice(decision, allowed_decisions, f"{label}.decision", errors):
                continue
            role_ids = lane["required_role_decision_ids"]
            if (
                not isinstance(role_ids, list)
                or any(
                    not isinstance(item, str)
                    or not TOKEN_PATTERNS["role_decision"].fullmatch(item)
                    for item in role_ids
                )
                or len(role_ids) != len(set(role_ids))
            ):
                errors.append(f"{label}.required_role_decision_ids are invalid")
                role_ids = []
            for record_id in role_ids:
                if record_id not in valid_roles:
                    errors.append(f"{label} references an unknown role decision")
            lane_decision_evidence = _evidence_reference(
                lane["decision_evidence_id"],
                "lane_decision",
                f"{label}.decision_evidence_id",
                errors,
                valid_manifest,
                lane=lane_id,
            )
            expected_lane_issuer = (
                "independent_truth_and_release_group"
                if decision in {"selection", "required_reference"}
                else "owner"
            )
            if (
                lane_decision_evidence is not None
                and lane_decision_evidence.get("issuer_role_id")
                != expected_lane_issuer
            ):
                errors.append(f"{label}.decision_evidence_id has the wrong issuer")
            expected_actor_class = (
                "release_decision"
                if decision in {"selection", "required_reference"}
                else "product_owner"
            )
            lane_decision_actor = (
                _safe_record_lookup(
                    valid_actors,
                    lane_decision_evidence.get("subject_assignment_id"),
                )
                if isinstance(lane_decision_evidence, dict)
                else None
            )
            if lane_decision_actor is None or expected_actor_class not in (
                lane_decision_actor.get("classes", [])
            ):
                errors.append(
                    f"{label}.decision_evidence_id has the wrong responsible assignment"
                )
            _reason_list(lane["reason_codes"], f"{label}.reason_codes", errors)
            _reason_list(
                lane["evidence_needed_to_reopen"],
                f"{label}.evidence_needed_to_reopen",
                errors,
                allow_empty=decision in {"selection", "not_required", "required_reference"},
            )
            if lane["selected_score"] is not None:
                errors.append(f"{label}.selected_score must be null")
            if lane["selected_threshold"] is not None:
                errors.append(f"{label}.selected_threshold must be null")
            selected_fields = {
                "selected_construct_evidence_id": "construct_specification",
                "selected_task_evidence_id": "task_protocol",
                "selected_measure_evidence_id": "measure_specification",
            }
            if decision == "selection":
                if lane_shape_is_safe:
                    selected_lanes.append(lane_id)
                question_id = lane["candidate_question_id"]
                if not isinstance(question_id, str):
                    errors.append(f"{label}.candidate_question_id is invalid")
                    expected_question = None
                else:
                    expected_question = SELECTABLE_CURRENT_QUESTIONS.get(question_id)
                if expected_question is None or expected_question[0] != lane_id:
                    errors.append(f"{label} candidate is not selectable from this parent contract")
                elif lane["truth_class"] != expected_question[1]:
                    errors.append(f"{label}.truth_class does not match the candidate")
                selected_evidence = {}
                for field, evidence_type in selected_fields.items():
                    selected_evidence[field] = _evidence_reference(
                        lane[field],
                        evidence_type,
                        f"{label}.{field}",
                        errors,
                        valid_manifest,
                        lane=lane_id,
                    )
                expected_issuers = {
                    "selected_construct_evidence_id": {
                        "independent_speech_measurement_scientist"
                    },
                    "selected_measure_evidence_id": {
                        "independent_speech_measurement_scientist"
                    },
                    "selected_task_evidence_id": {
                        "independent_adult_voice_cpsp"
                        if lane_id == "voice"
                        else "independent_adult_motor_speech_cpsp"
                    },
                }
                for field, linked_evidence in selected_evidence.items():
                    if (
                        linked_evidence is not None
                        and linked_evidence.get("issuer_role_id")
                        not in expected_issuers[field]
                    ):
                        errors.append(f"{label}.{field} has the wrong issuing role")
                    _candidate_binding(
                        linked_evidence,
                        question_id,
                        [CURRENT_CONTRACT_CANONICAL_SHA256],
                        f"{label}.{field}",
                        errors,
                    )
                if lane["evidence_needed_to_reopen"] != []:
                    errors.append(f"{label} selection cannot have reopening evidence")
            elif decision == "required_reference":
                if lane["candidate_question_id"] is not None:
                    errors.append(f"{label}.candidate_question_id must be null")
                expected_truth = (
                    "participant_report"
                    if lane_id == "participant_report"
                    else "clinical_reference"
                )
                if lane["truth_class"] != expected_truth:
                    errors.append(f"{label}.truth_class is invalid")
                for field, evidence_type in selected_fields.items():
                    _evidence_reference(
                        lane[field],
                        evidence_type,
                        f"{label}.{field}",
                        errors,
                        valid_manifest,
                        lane=lane_id,
                    )
            else:
                for field in {"candidate_question_id", "truth_class"} | set(selected_fields):
                    if lane[field] is not None:
                        errors.append(f"{label}.{field} must be null")
                if decision in {"no_selection", "unavailable"} and not lane[
                    "evidence_needed_to_reopen"
                ]:
                    errors.append(f"{label} closure needs evidence to reopen")
                if decision in {"no_selection", "unavailable"}:
                    for record_id in role_ids:
                        record = valid_roles.get(record_id)
                        if not isinstance(record, dict):
                            continue
                        if not _scope_covers(record.get("scope"), [lane_id]):
                            errors.append(
                                f"{label} cites a blocker outside the lane scope"
                            )
                        role_spec = (record.get("role_id"), record.get("specialty"))
                        if role_spec not in LANE_BLOCKING_ROLE_SPECS[lane_id]:
                            errors.append(
                                f"{label} cites a role that cannot block this lane"
                            )
                        if record.get("outcome") not in (
                            "signed_block",
                            "unfilled_blocks_selection",
                        ):
                            errors.append(
                                f"{label} nonselection may cite only blocking roles"
                            )
                        for field in ("decision_evidence_id", "conflict_evidence_id"):
                            evidence = _safe_record_lookup(
                                valid_manifest, record.get(field)
                            )
                            if not isinstance(evidence, dict):
                                continue
                            candidate_id = evidence.get("candidate_question_id")
                            candidate_profile = (
                                SELECTABLE_CURRENT_QUESTIONS.get(candidate_id)
                                if isinstance(candidate_id, str)
                                else None
                            )
                            if candidate_id is not None and (
                                candidate_profile is None
                                or candidate_profile[0] != lane_id
                            ):
                                errors.append(
                                    f"{label} cites blocker evidence bound to another lane"
                                )
                elif decision == "not_required" and role_ids:
                    errors.append(f"{label} nonselected lane cannot claim required approving roles")

            if lane_shape_is_safe:
                valid_lanes[lane_id] = lane

        cited_role_ids = {
            record_id
            for lane in valid_lanes.values()
            for record_id in lane.get("required_role_decision_ids", [])
            if isinstance(record_id, str)
        }
        for record_id in valid_roles:
            if record_id not in cited_role_ids:
                errors.append(f"role_decisions.{record_id} is not cited by a lane decision")
        developer_or_vendor_organisations = {
            actor.get("organisation_id")
            for actor in valid_actors.values()
            if set(actor.get("classes", [])) & {"developer", "candidate_vendor"}
        }
        for record_id, record in valid_roles.items():
            if record.get("role_id") == "product_owner":
                continue
            actor = valid_actors.get(record.get("assignment_id"), {})
            if actor.get("organisation_id") in developer_or_vendor_organisations:
                errors.append(
                    f"role_decisions.{record_id} is controlled by the developer or vendor organisation"
                )
        used_assignments = {
            record.get("assignment_id")
            for record in valid_roles.values()
            if isinstance(record.get("assignment_id"), str)
        } | {
            assignment_id
            for field, assignment_id in valid_duties.items()
            if field.endswith("_assignment_id")
            if isinstance(assignment_id, str)
        }
        for assignment_id in valid_actors:
            actor_classes = set(valid_actors[assignment_id].get("classes", []))
            if assignment_id not in used_assignments and not actor_classes & {
                "product_owner",
                "candidate_vendor",
            }:
                errors.append(
                    f"actor_register.{assignment_id} is not assigned to a role decision"
                )

    data_fields = {
        "participant_or_study_recording_accessed",
        "existing_owner_audio_accessed",
        "private_participant_data_accessed",
        "new_recording_collected",
        "held_out_accessed",
        "private_governance_evidence_accessed",
    }
    data_access = document["data_access"]
    if _exact_object(data_access, data_fields, "data_access", errors):
        for field in data_fields - {"private_governance_evidence_accessed"}:
            if data_access[field] is not False:
                errors.append(f"data_access.{field} must remain false")
        if not isinstance(data_access["private_governance_evidence_accessed"], bool):
            errors.append("private governance evidence access must be boolean")
        else:
            referenced_ids = _explicit_evidence_ids(document)
            external_private_evidence = any(
                evidence_id in referenced_ids
                and evidence.get("storage_class")
                in {"approved_private_governance", "institution_system"}
                for evidence_id, evidence in valid_manifest.items()
            )
            if (
                data_access["private_governance_evidence_accessed"]
                is not external_private_evidence
            ):
                errors.append(
                    "private governance evidence access must match cited external private evidence"
                )
    else:
        data_access = {}

    overall_fields = {
        "decision",
        "checkpoint_complete",
        "decision_evidence_id",
        "reason_codes",
        "evidence_needed_to_reopen",
    }
    overall = document["overall_decision"]
    overall_decision = None
    if _exact_object(overall, overall_fields, "overall_decision", errors):
        if _choice(
            overall["decision"],
            {"selection", "no_selection"},
            "overall_decision.decision",
            errors,
        ):
            overall_decision = overall["decision"]
        if overall["checkpoint_complete"] is not True:
            errors.append("overall_decision.checkpoint_complete must be true")
        overall_decision_evidence = _evidence_reference(
            overall["decision_evidence_id"],
            "overall_decision",
            "overall_decision.decision_evidence_id",
            errors,
            valid_manifest,
            issuer_role_id="owner",
        )
        overall_actor = (
            _safe_record_lookup(
                valid_actors,
                overall_decision_evidence.get("subject_assignment_id"),
            )
            if isinstance(overall_decision_evidence, dict)
            else None
        )
        if overall_actor is None or "product_owner" not in overall_actor.get(
            "classes", []
        ):
            errors.append("overall decision must identify a product-owner assignment")
        if (
            isinstance(overall_decision_evidence, dict)
            and accountable_owner_assignment is not None
            and overall_decision_evidence.get("subject_assignment_id")
            != accountable_owner_assignment
        ):
            errors.append(
                "overall decision must use the accountable owner assignment"
            )
        _reason_list(overall["reason_codes"], "overall_decision.reason_codes", errors)
        _reason_list(
            overall["evidence_needed_to_reopen"],
            "overall_decision.evidence_needed_to_reopen",
            errors,
            allow_empty=overall_decision == "selection",
        )
    else:
        overall = {}

    if accountable_owner_assignment is not None:
        for evidence_id, evidence in valid_manifest.items():
            if (
                evidence.get("issuer_role_id") == "owner"
                and evidence.get("subject_assignment_id")
                != accountable_owner_assignment
            ):
                errors.append(
                    f"evidence_manifest.{evidence_id} owner-issued evidence must use the accountable owner assignment"
                )
        for record_id, record in valid_roles.items():
            if (
                record.get("role_id") == "product_owner"
                and record.get("assignment_id")
                != accountable_owner_assignment
            ):
                errors.append(
                    f"role_decisions.{record_id} must use the accountable owner assignment"
                )
        for lane_id, lane in valid_lanes.items():
            lane_evidence = _safe_record_lookup(
                valid_manifest, lane.get("decision_evidence_id")
            )
            if (
                isinstance(lane_evidence, dict)
                and lane_evidence.get("issuer_role_id") == "owner"
                and lane_evidence.get("subject_assignment_id")
                != accountable_owner_assignment
            ):
                errors.append(
                    f"lane_decisions.{lane_id} owner closure must use the accountable owner assignment"
                )

    downstream_fields = {
        "checkpoint_23c",
        "checkpoint_23c_eligible_lanes",
        "checkpoint_23d",
        "checkpoint_23e",
        "checkpoint_23f",
        "participant_work_may_begin",
        "implementation_may_begin",
    }
    downstream = document["downstream"]
    if _exact_object(downstream, downstream_fields, "downstream", errors):
        if downstream["participant_work_may_begin"] is not False:
            errors.append("participant work must remain false")
        if downstream["implementation_may_begin"] is not False:
            errors.append("implementation must remain false")
        eligible = downstream["checkpoint_23c_eligible_lanes"]
        if not isinstance(eligible, list) or len(eligible) != len(
            set(item for item in eligible if isinstance(item, str))
        ):
            errors.append("checkpoint_23c_eligible_lanes must be a unique array")
        elif eligible != selected_lanes:
            errors.append("checkpoint_23c_eligible_lanes must equal selected lanes")
        expected_downstream = None
        if overall_decision == "selection":
            expected_downstream = {
                "checkpoint_23c": "pending_separate_owner_approval",
                "checkpoint_23d": "locked",
                "checkpoint_23e": "locked",
                "checkpoint_23f": "locked",
            }
        elif overall_decision == "no_selection":
            expected_downstream = {
                "checkpoint_23c": "not_applicable",
                "checkpoint_23d": "not_applicable",
                "checkpoint_23e": "not_applicable",
                "checkpoint_23f": "not_applicable",
            }
            if eligible != []:
                errors.append("no selection cannot have a 23C eligible lane")
        if expected_downstream is not None:
            for field, expected in expected_downstream.items():
                if downstream[field] != expected:
                    errors.append(f"downstream.{field} changed")

    releases = document["release_boundaries"]
    if _exact_object(releases, RELEASE_FIELDS, "release_boundaries", errors):
        for field, value in releases.items():
            if value is not False:
                errors.append(f"release_boundaries.{field} must remain false")

    selected_question_id = None
    if overall_decision == "selection":
        if len(selected_lanes) != 1:
            errors.append("overall selection requires exactly one selected candidate lane")
        selected_lane = selected_lanes[0] if len(selected_lanes) == 1 else None
        if intended.get("status") != "signed_selection_use":
            errors.append("selection requires a signed intended use")

        required_authority_fields = {
            "legal_sponsor_evidence_id",
            "responsible_institution_evidence_id",
            "ethics_decision_evidence_id",
            "site_applicability_determination_evidence_id",
            "entity_data_role_matrix_evidence_id",
            "privacy_pia_evidence_id",
            "recording_law_evidence_id",
            "security_review_evidence_id",
            "retention_withdrawal_deletion_evidence_id",
            "statistical_plan_evidence_id",
            "source_rights_evidence_id",
            "regulatory_assessment_evidence_id",
        }
        device = authority.get("medical_device_status") == "medical_device"
        trial = authority.get("clinical_trial_pathway_status") in (
            "ctn_required",
            "cta_required",
        )
        if authority.get("site_governance_applicability") == "required":
            required_authority_fields.add("site_authorisation_evidence_id")
        if device or trial:
            required_authority_fields.add("manufacturer_evidence_id")
        if trial:
            required_authority_fields.add("australian_trial_sponsor_evidence_id")
        for field in required_authority_fields:
            if authority.get(field) is None:
                errors.append(f"selection requires authority_outcomes.{field}")
        for field in (
            "ethics_pathway",
            "site_governance_applicability",
            "privacy_act_coverage",
            "health_service_provider_coverage",
            "app_5_collection_notice_status",
            "app_6_use_and_disclosure_status",
            "incidental_speaker_controls_status",
            "consent_materials_status",
            "medical_device_status",
            "clinical_trial_pathway_status",
        ):
            if authority.get(field) == "unresolved":
                errors.append(f"selection cannot leave authority_outcomes.{field} unresolved")
        if authority.get("overseas_processing") != "prohibited":
            errors.append("selection requires overseas processing to remain prohibited")
        if authority.get("secondary_model_training") != "prohibited":
            errors.append("selection requires secondary model training to remain prohibited")
        if data_access.get("private_governance_evidence_accessed") is not True:
            errors.append("selection requires recorded private governance evidence access")

        if selected_lane is not None:
            selected_lane_record = valid_lanes[selected_lane]
            selected_question_id = selected_lane_record.get("candidate_question_id")
            required_reference_lanes = {
                lane_id
                for lane_id in CONDITIONAL_REFERENCE_LANES
                if valid_lanes.get(lane_id, {}).get("decision")
                == "required_reference"
            }
            required_deliverables = (
                set(GLOBAL_SELECTION_DELIVERABLES)
                | set(LANE_SELECTION_DELIVERABLES[selected_lane])
            )
            if "participant_report" in required_reference_lanes:
                required_deliverables.add("participant_report_protocol")
            if "clinical_laryngeal_reference" in required_reference_lanes:
                required_deliverables.add("clinical_reference_manual")
            for deliverable_id in required_deliverables:
                record = valid_deliverables.get(deliverable_id)
                if record is None or record.get("applicability") != "required":
                    errors.append(f"selection requires deliverable {deliverable_id}")
                elif not _scope_covers(record.get("lane_scope"), [selected_lane]):
                    errors.append(f"deliverable {deliverable_id} does not cover selected lane")
            for deliverable_id, record in valid_deliverables.items():
                if (
                    deliverable_id not in required_deliverables
                    and record.get("applicability") == "required"
                ):
                    errors.append(
                        f"selection has an unexplained required deliverable {deliverable_id}"
                    )

            required_specs = (
                set(GLOBAL_SELECTION_ROLE_SPECS)
                | set(LANE_SELECTION_ROLE_SPECS[selected_lane])
            )
            if authority.get("ethics_pathway") == "hrec":
                required_specs.add(
                    ("human_research_ethics_committee_if_required", "generic")
                )
            if "clinical_laryngeal_reference" in required_reference_lanes:
                required_specs.update(
                    {
                        ("independent_clinical_reference_lead_if_required", "generic"),
                        ("independent_ent_or_laryngologist_if_required", "generic"),
                    }
                )
            required_record_ids = set()
            required_assignments = []
            accepted_by_spec = {}
            accepted_record_id_by_spec = {}
            for role_id, specialty in required_specs:
                records = _role_records_for(
                    valid_roles, role_id, specialty, selected_lane
                )
                accepted = [
                    (record_id, record)
                    for record_id, record in records
                    if record.get("applicability") == "required"
                    and record.get("outcome") == "signed_no_unresolved_block"
                    and record.get("recused") is False
                    and record.get("eligible_to_decide") is True
                ]
                if len(accepted) != 1:
                    errors.append(
                        f"selection requires exactly one eligible no-block decision from {role_id}:{specialty}"
                    )
                else:
                    required_record_ids.add(accepted[0][0])
                    required_assignments.append(accepted[0][1].get("assignment_id"))
                    accepted_by_spec[(role_id, specialty)] = accepted[0][1]
                    accepted_record_id_by_spec[(role_id, specialty)] = accepted[0][0]
                if any(
                    record.get("outcome")
                    in ("signed_block", "unfilled_blocks_selection")
                    for _, record in records
                ):
                    errors.append(f"{role_id}:{specialty} blocks the selected lane")
            for record_id, record in valid_roles.items():
                if (
                    record.get("outcome")
                    in ("signed_block", "unfilled_blocks_selection")
                    and _scope_covers(record.get("scope"), [selected_lane])
                ):
                    errors.append(
                        f"role decision {record_id} blocks the selected lane"
                    )
            lane_role_ids = set(
                selected_lane_record.get("required_role_decision_ids", [])
            )
            if lane_role_ids != required_record_ids:
                errors.append("selected lane must cite exactly its required role decisions")
            if len(required_assignments) != len(set(required_assignments)):
                errors.append("required selection roles must use distinct assignments")

            conditional_role_specs = {
                "participant_report": {
                    ("paid_lived_experience_governance_group", "generic"),
                    ("independent_speech_measurement_scientist", "generic"),
                },
                "clinical_laryngeal_reference": {
                    ("independent_clinical_reference_lead_if_required", "generic"),
                    ("independent_ent_or_laryngologist_if_required", "generic"),
                },
            }
            for reference_lane in required_reference_lanes:
                exact_reference_scope = {selected_lane, reference_lane}
                expected_reference_role_ids = set()
                for role_spec in conditional_role_specs[reference_lane]:
                    role_record = accepted_by_spec.get(role_spec)
                    role_record_id = accepted_record_id_by_spec.get(role_spec)
                    if role_record_id is not None:
                        expected_reference_role_ids.add(role_record_id)
                    if role_record is not None:
                        if set(role_record.get("scope", [])) != exact_reference_scope:
                            errors.append(
                                f"required role {role_spec[0]}:{role_spec[1]} must have the exact selected and reference lane scope"
                            )
                        for field in (
                            "decision_evidence_id",
                            "conflict_evidence_id",
                        ):
                            evidence = _safe_record_lookup(
                                valid_manifest, role_record.get(field)
                            )
                            if isinstance(evidence, dict) and set(
                                evidence.get("scope", [])
                            ) != exact_reference_scope:
                                errors.append(
                                    f"required role {role_spec[0]}:{role_spec[1]} {field} must have the exact selected and reference lane scope"
                                )
                actual_reference_role_ids = set(
                    valid_lanes[reference_lane].get(
                        "required_role_decision_ids", []
                    )
                )
                if actual_reference_role_ids != expected_reference_role_ids:
                    errors.append(
                        f"lane_decisions.{reference_lane} must cite exactly its accountable role decisions"
                    )
                deliverable_id = (
                    "participant_report_protocol"
                    if reference_lane == "participant_report"
                    else "clinical_reference_manual"
                )
                deliverable = valid_deliverables.get(deliverable_id)
                if isinstance(deliverable, dict):
                    if set(deliverable.get("lane_scope", [])) != exact_reference_scope:
                        errors.append(
                            f"deliverable {deliverable_id} must have the exact selected and reference lane scope"
                        )
                    deliverable_evidence = _safe_record_lookup(
                        valid_manifest, deliverable.get("evidence_id")
                    )
                    if isinstance(deliverable_evidence, dict) and set(
                        deliverable_evidence.get("scope", [])
                    ) != exact_reference_scope:
                        errors.append(
                            f"deliverable {deliverable_id} evidence must have the exact selected and reference lane scope"
                        )

            developer_or_vendor_organisations = {
                actor.get("organisation_id")
                for actor in valid_actors.values()
                if set(actor.get("classes", []))
                & {"developer", "candidate_vendor"}
            }
            for role_spec, role_record in accepted_by_spec.items():
                if role_spec == ("product_owner", "generic"):
                    continue
                actor = valid_actors.get(role_record.get("assignment_id"), {})
                if actor.get("organisation_id") in developer_or_vendor_organisations:
                    errors.append(
                        f"required role {role_spec[0]}:{role_spec[1]} is controlled by the developer or vendor organisation"
                    )
            task_role_spec = (
                ("independent_adult_voice_cpsp", "generic")
                if selected_lane == "voice"
                else ("independent_adult_motor_speech_cpsp", "generic")
            )

            def accepted_assignment(role_spec):
                record = accepted_by_spec.get(role_spec)
                return (
                    record.get("assignment_id")
                    if isinstance(record, dict)
                    else None
                )

            expected_duties = {
                "construct_control_assignment_id": accepted_assignment(
                    ("independent_speech_measurement_scientist", "generic")
                ),
                "task_control_assignment_id": accepted_assignment(task_role_spec),
                "reference_truth_assignment_id": valid_duties.get(
                    "reference_truth_assignment_id"
                ),
                "threshold_assignment_id": accepted_assignment(
                    ("biostatistician_or_measurement_specialist", "generic")
                ),
                "data_custody_assignment_id": accepted_assignment(
                    ("independent_data_and_split_custodian", "generic")
                ),
                "release_assignment_id": accepted_assignment(
                    ("independent_truth_and_release_group", "generic")
                ),
            }
            for field, expected_assignment in expected_duties.items():
                if valid_duties.get(field) != expected_assignment:
                    errors.append(
                        f"duty_assignments.{field} does not match its accountable role"
                    )
            duty_assignment_ids = list(expected_duties.values())
            if any(value is None for value in duty_assignment_ids):
                errors.append("selection requires every separation-of-duties assignment")
            elif len(set(duty_assignment_ids)) != len(duty_assignment_ids):
                errors.append("independent duties must use distinct assignments")
            else:
                duty_organisations = [
                    valid_actors.get(assignment_id, {}).get("organisation_id")
                    for assignment_id in duty_assignment_ids
                ]
                if (
                    any(value is None for value in duty_organisations)
                    or len(set(duty_organisations)) != len(duty_organisations)
                ):
                    errors.append(
                        "construct, task, truth, threshold, data custody and release duties must use distinct organisations"
                    )
            release_organisation = valid_actors.get(
                expected_duties.get("release_assignment_id"), {}
            ).get("organisation_id")
            for reference_lane in required_reference_lanes:
                reference_organisations = []
                for role_spec in conditional_role_specs[reference_lane]:
                    assignment_id = accepted_assignment(role_spec)
                    organisation_id = valid_actors.get(assignment_id, {}).get(
                        "organisation_id"
                    )
                    if organisation_id is not None:
                        reference_organisations.append(organisation_id)
                if (
                    len(reference_organisations)
                    != len(set(reference_organisations))
                    or release_organisation in reference_organisations
                ):
                    errors.append(
                        f"{reference_lane} accountable reference roles must be organisationally independent of each other and release"
                    )
            separated_assignments = {
                assignment_id
                for assignment_id in expected_duties.values()
                if isinstance(assignment_id, str)
            }
            for reference_lane in required_reference_lanes:
                for role_spec in conditional_role_specs[reference_lane]:
                    assignment_id = accepted_assignment(role_spec)
                    if isinstance(assignment_id, str):
                        separated_assignments.add(assignment_id)
            separated_organisations = [
                valid_actors.get(assignment_id, {}).get("organisation_id")
                for assignment_id in separated_assignments
            ]
            if (
                any(value is None for value in separated_organisations)
                or len(set(separated_organisations))
                != len(separated_organisations)
            ):
                errors.append(
                    "main and conditional truth-control duties must use distinct organisations"
                )

            selected_fields = (
                "selected_construct_evidence_id",
                "selected_task_evidence_id",
                "selected_measure_evidence_id",
            )
            selected_evidence = {
                field: _safe_record_lookup(valid_manifest, selected_lane_record.get(field))
                for field in selected_fields
            }
            reference_evidence = {}
            for reference_lane in required_reference_lanes:
                reference_record = valid_lanes[reference_lane]
                reference_evidence[reference_lane] = {
                    field: _safe_record_lookup(valid_manifest, reference_record.get(field))
                    for field in selected_fields
                }
                for field, evidence in reference_evidence[reference_lane].items():
                    if isinstance(evidence, dict) and set(
                        evidence.get("scope", [])
                    ) != {reference_lane}:
                        errors.append(
                            f"{reference_lane} {field} must have exact reference-lane scope"
                        )
                reference_lane_evidence = _safe_record_lookup(
                    valid_manifest, reference_record.get("decision_evidence_id")
                )
                if isinstance(reference_lane_evidence, dict) and set(
                    reference_lane_evidence.get("scope", [])
                ) != {selected_lane, reference_lane}:
                    errors.append(
                        f"{reference_lane} decision evidence must have exact selected and reference lane scope"
                    )
            selected_evidence_ids = {
                selected_lane_record.get(field) for field in selected_fields
            }
            for reference_lane in required_reference_lanes:
                reference_evidence_ids = {
                    valid_lanes[reference_lane].get(field)
                    for field in selected_fields
                }
                if selected_evidence_ids & reference_evidence_ids:
                    errors.append(
                        f"{reference_lane} cannot reuse selected-lane construct, task or measure evidence"
                    )
            selected_hashes = {CURRENT_CONTRACT_CANONICAL_SHA256}
            for evidence in list(selected_evidence.values()) + [
                evidence
                for lane_evidence in reference_evidence.values()
                for evidence in lane_evidence.values()
            ]:
                if isinstance(evidence, dict) and isinstance(
                    evidence.get("sha256"), str
                ):
                    selected_hashes.add(evidence["sha256"])

            task_role = (
                "independent_adult_voice_cpsp"
                if selected_lane == "voice"
                else "independent_adult_motor_speech_cpsp"
            )
            selected_subject_specs = {
                "selected_construct_evidence_id": (
                    "independent_speech_measurement_scientist",
                    "generic",
                ),
                "selected_task_evidence_id": (task_role, "generic"),
                "selected_measure_evidence_id": (
                    "independent_speech_measurement_scientist",
                    "generic",
                ),
            }
            for field, role_spec in selected_subject_specs.items():
                evidence = selected_evidence.get(field)
                role_record = accepted_by_spec.get(role_spec)
                if (
                    evidence is not None
                    and role_record is not None
                    and evidence.get("subject_assignment_id")
                    != role_record.get("assignment_id")
                ):
                    errors.append(
                        f"selected lane {field} has the wrong responsible assignment"
                    )

            reference_subject_specs = {
                "participant_report": {
                    "selected_construct_evidence_id": (
                        "independent_speech_measurement_scientist",
                        "generic",
                    ),
                    "selected_task_evidence_id": (
                        "paid_lived_experience_governance_group",
                        "generic",
                    ),
                    "selected_measure_evidence_id": (
                        "independent_speech_measurement_scientist",
                        "generic",
                    ),
                },
                "clinical_laryngeal_reference": {
                    field: (
                        "independent_clinical_reference_lead_if_required",
                        "generic",
                    )
                    for field in selected_fields
                },
            }
            for reference_lane, lane_evidence in reference_evidence.items():
                for field, evidence in lane_evidence.items():
                    role_spec = reference_subject_specs[reference_lane][field]
                    role_record = accepted_by_spec.get(role_spec)
                    if evidence is not None:
                        if evidence.get("issuer_role_id") != role_spec[0]:
                            errors.append(
                                f"{reference_lane} {field} has the wrong issuing role"
                            )
                        if (
                            role_record is not None
                            and evidence.get("subject_assignment_id")
                            != role_record.get("assignment_id")
                        ):
                            errors.append(
                                f"{reference_lane} {field} has the wrong responsible assignment"
                            )
                        _candidate_binding(
                            evidence,
                            selected_question_id,
                            [CURRENT_CONTRACT_CANONICAL_SHA256],
                            f"{reference_lane} {field}",
                            errors,
                        )

            selection_package_hashes = set(selected_hashes)
            truth_assignment = valid_duties.get(
                "reference_truth_assignment_id"
            )
            truth_decision = _evidence_reference(
                valid_duties.get("reference_truth_decision_evidence_id"),
                "role_domain_decision",
                "duty_assignments.reference_truth_decision_evidence_id",
                errors,
                valid_manifest,
                lane=selected_lane,
                issuer_role_id="independent_truth_and_release_group",
                subject_assignment_id=truth_assignment,
            )
            truth_actor = valid_actors.get(truth_assignment, {})
            truth_appointment = _safe_record_lookup(
                valid_manifest, truth_actor.get("appointment_evidence_id")
            )
            if isinstance(truth_appointment, dict):
                if truth_appointment.get("storage_class") not in {
                    "approved_private_governance",
                    "institution_system",
                }:
                    errors.append(
                        "reference truth appointment must be privately or institutionally verified"
                    )
                if truth_appointment.get("scope") != ["global"]:
                    errors.append(
                        "reference truth appointment must have exact reusable global scope"
                    )
                if truth_appointment.get("candidate_question_id") is not None:
                    errors.append(
                        "reference truth appointment must remain candidate neutral"
                    )
                if truth_appointment.get("dependency_sha256"):
                    errors.append(
                        "reference truth appointment cannot import project dependencies"
                    )
            if isinstance(truth_decision, dict):
                if truth_decision.get("storage_class") not in {
                    "approved_private_governance",
                    "institution_system",
                }:
                    errors.append(
                        "reference truth decision must be privately or institutionally verified"
                    )
                if set(truth_decision.get("scope", [])) != {selected_lane}:
                    errors.append(
                        "reference truth decision must have exact selected-lane scope"
                    )
                truth_dependencies = set(selected_hashes)
                if isinstance(truth_appointment, dict):
                    truth_dependencies.add(truth_appointment.get("sha256"))
                _candidate_binding(
                    truth_decision,
                    selected_question_id,
                    truth_dependencies,
                    "duty_assignments.reference_truth_decision_evidence_id",
                    errors,
                )
                selection_package_hashes.add(truth_decision.get("sha256"))
            if isinstance(truth_appointment, dict):
                selection_package_hashes.add(truth_appointment.get("sha256"))
            owner_evidence = _safe_record_lookup(
                valid_manifest,
                owner.get("owner_decision_evidence_id")
                if isinstance(owner, dict)
                else None
            )
            if isinstance(owner_evidence, dict):
                selection_package_hashes.add(owner_evidence.get("sha256"))

            intended_evidence = _safe_record_lookup(
                valid_manifest, intended.get("evidence_id")
            )
            owner_role = accepted_by_spec.get(("product_owner", "generic"))
            owner_assignment = (
                owner_role.get("assignment_id")
                if isinstance(owner_role, dict)
                else None
            )
            if (
                owner_evidence is not None
                and owner_evidence.get("subject_assignment_id")
                != owner_assignment
            ):
                errors.append(
                    "owner decision is not owned by the accepted product owner"
                )
            if (
                intended_evidence is not None
                and owner_role is not None
                and intended_evidence.get("subject_assignment_id")
                != owner_assignment
            ):
                errors.append("intended use is not owned by the accepted product owner")
            overall_evidence_for_owner = _safe_record_lookup(
                valid_manifest, overall.get("decision_evidence_id")
            )
            if (
                overall_evidence_for_owner is not None
                and overall_evidence_for_owner.get("subject_assignment_id")
                != owner_assignment
            ):
                errors.append(
                    "overall decision is not owned by the accepted product owner"
                )
            _candidate_binding(
                intended_evidence,
                selected_question_id,
                selected_hashes,
                "intended_use.evidence_id",
                errors,
            )
            if isinstance(intended_evidence, dict):
                selection_package_hashes.add(intended_evidence.get("sha256"))

            for deliverable_id in required_deliverables:
                record = valid_deliverables.get(deliverable_id)
                if not isinstance(record, dict):
                    continue
                evidence = _safe_record_lookup(
                    valid_manifest, record.get("evidence_id")
                )
                role_spec = DELIVERABLE_ISSUER_SPECIALTY[deliverable_id]
                role_record = accepted_by_spec.get(role_spec)
                if (
                    evidence is not None
                    and role_record is not None
                    and evidence.get("subject_assignment_id")
                    != role_record.get("assignment_id")
                ):
                    errors.append(
                        f"deliverable {deliverable_id} is not owned by its accepted issuing assignment"
                    )
                _candidate_binding(
                    evidence,
                    selected_question_id,
                    selected_hashes,
                    f"deliverable {deliverable_id}",
                    errors,
                )
                if isinstance(evidence, dict):
                    selection_package_hashes.add(evidence.get("sha256"))

            for record_id in required_record_ids:
                record = valid_roles.get(record_id)
                if not isinstance(record, dict):
                    continue
                competence = _safe_record_lookup(
                    valid_manifest, record.get("competence_evidence_id")
                )
                conflict = _safe_record_lookup(
                    valid_manifest, record.get("conflict_evidence_id")
                )
                decision = _safe_record_lookup(
                    valid_manifest, record.get("decision_evidence_id")
                )
                _candidate_binding(
                    conflict,
                    selected_question_id,
                    selected_hashes,
                    f"role decision {record_id}.conflict_evidence_id",
                    errors,
                )
                decision_dependencies = set(selected_hashes)
                for evidence in (competence, conflict):
                    if isinstance(evidence, dict):
                        decision_dependencies.add(evidence.get("sha256"))
                        selection_package_hashes.add(evidence.get("sha256"))
                role_spec = (record.get("role_id"), record.get("specialty"))
                conditional_deliverable_ids = set()
                if (
                    "participant_report" in required_reference_lanes
                    and role_spec
                    in {
                        ("paid_lived_experience_governance_group", "generic"),
                        ("independent_speech_measurement_scientist", "generic"),
                    }
                ):
                    conditional_deliverable_ids.add("participant_report_protocol")
                if (
                    "clinical_laryngeal_reference" in required_reference_lanes
                    and role_spec
                    in {
                        (
                            "independent_clinical_reference_lead_if_required",
                            "generic",
                        ),
                        ("independent_ent_or_laryngologist_if_required", "generic"),
                    }
                ):
                    conditional_deliverable_ids.add("clinical_reference_manual")
                for deliverable_id in conditional_deliverable_ids:
                    deliverable_record = valid_deliverables.get(deliverable_id)
                    deliverable_evidence = (
                        _safe_record_lookup(
                            valid_manifest, deliverable_record.get("evidence_id")
                        )
                        if isinstance(deliverable_record, dict)
                        else None
                    )
                    if isinstance(deliverable_evidence, dict):
                        decision_dependencies.add(
                            deliverable_evidence.get("sha256")
                        )
                _candidate_binding(
                    decision,
                    selected_question_id,
                    decision_dependencies,
                    f"role decision {record_id}.decision_evidence_id",
                    errors,
                )
                if isinstance(decision, dict):
                    selection_package_hashes.add(decision.get("sha256"))

            for field in required_authority_fields:
                evidence = _safe_record_lookup(valid_manifest, authority.get(field))
                if evidence is not None and not _scope_covers(
                    evidence.get("scope"), [selected_lane]
                ):
                    errors.append(
                        f"authority_outcomes.{field} does not cover selected lane"
                    )
                if field == "ethics_decision_evidence_id":
                    role_spec = (
                        ("human_research_ethics_committee_if_required", "generic")
                        if authority.get("ethics_pathway") == "hrec"
                        else ("responsible_research_institution", "generic")
                    )
                else:
                    role_spec = AUTHORITY_ISSUER_SPECIALTY[field]
                role_record = accepted_by_spec.get(role_spec)
                if (
                    evidence is not None
                    and role_record is not None
                    and evidence.get("subject_assignment_id")
                    != role_record.get("assignment_id")
                ):
                    errors.append(
                        f"authority_outcomes.{field} is not owned by its accepted responsible assignment"
                    )
                authority_dependencies = set(selected_hashes)
                if (
                    field == "site_authorisation_evidence_id"
                    and authority.get("site_governance_applicability") == "required"
                ):
                    for prerequisite_field in (
                        "ethics_decision_evidence_id",
                        "site_applicability_determination_evidence_id",
                    ):
                        prerequisite = _safe_record_lookup(
                            valid_manifest, authority.get(prerequisite_field)
                        )
                        if isinstance(prerequisite, dict):
                            authority_dependencies.add(prerequisite.get("sha256"))
                _candidate_binding(
                    evidence,
                    selected_question_id,
                    authority_dependencies,
                    f"authority_outcomes.{field}",
                    errors,
                )
                if isinstance(evidence, dict):
                    selection_package_hashes.add(evidence.get("sha256"))

            release_role = accepted_by_spec.get(
                ("independent_truth_and_release_group", "generic")
            )
            release_assignment = (
                release_role.get("assignment_id")
                if isinstance(release_role, dict)
                else None
            )
            for lane_id in {selected_lane} | required_reference_lanes:
                lane_evidence = _safe_record_lookup(
                    valid_manifest,
                    valid_lanes[lane_id].get("decision_evidence_id"),
                )
                if (
                    lane_evidence is not None
                    and lane_evidence.get("subject_assignment_id")
                    != release_assignment
                ):
                    errors.append(
                        f"lane_decisions.{lane_id}.decision_evidence_id is not owned by the accepted release assignment"
                    )
                _candidate_binding(
                    lane_evidence,
                    selected_question_id,
                    selection_package_hashes,
                    f"lane_decisions.{lane_id}.decision_evidence_id",
                    errors,
                )

        for assignment_id, actor in valid_actors.items():
            classes = set(actor.get("classes", []))
            if classes & {"developer", "candidate_vendor"} and classes & {
                "reference_truth",
                "data_custodian",
                "release_decision",
            }:
                errors.append(f"{assignment_id} violates separation of duties")
        actor_classes = [
            set(actor.get("classes", [])) for actor in valid_actors.values()
        ]
        for required_class in (
            "developer",
            "reference_truth",
            "data_custodian",
            "release_decision",
        ):
            if not any(required_class in classes for classes in actor_classes):
                errors.append(f"selection requires an actor class {required_class}")
        if sum("reference_truth" in classes for classes in actor_classes) != 1:
            errors.append("selection requires exactly one reference truth owner")
        developer_or_vendor_organisations = {
            actor.get("organisation_id")
            for actor in valid_actors.values()
            if set(actor.get("classes", [])) & {"developer", "candidate_vendor"}
        }
        protected_organisations = {
            actor.get("organisation_id")
            for actor in valid_actors.values()
            if set(actor.get("classes", []))
            & {"reference_truth", "data_custodian", "release_decision"}
        }
        if developer_or_vendor_organisations & protected_organisations:
            errors.append(
                "developer or vendor organisations cannot control reference truth, data custody or release"
            )
    elif overall_decision == "no_selection":
        if selected_lanes:
            errors.append("overall no selection cannot contain a lane selection")
        if any(value is not None for value in valid_duties.values()):
            errors.append("overall no selection cannot assign selection duties")
        for lane_id in CORE_CANDIDATE_LANES:
            if valid_lanes.get(lane_id, {}).get("decision") != "no_selection":
                errors.append(f"no selection requires explicit {lane_id} no_selection")
        for lane_id in CONDITIONAL_REFERENCE_LANES:
            if valid_lanes.get(lane_id, {}).get("decision") not in (
                "not_required",
                "unavailable",
            ):
                errors.append(
                    f"no selection cannot require the conditional lane {lane_id}"
                )
        if not overall.get("evidence_needed_to_reopen"):
            errors.append("overall no selection needs evidence to reopen")

    for lane_id, lane in valid_lanes.items():
        if lane.get("decision") not in (
            "no_selection",
            "not_required",
            "unavailable",
        ):
            continue
        lane_evidence = _safe_record_lookup(
            valid_manifest, lane.get("decision_evidence_id")
        )
        expected_dependencies = {CURRENT_CONTRACT_CANONICAL_SHA256}
        for record_id in lane.get("required_role_decision_ids", []):
            record = valid_roles.get(record_id)
            if not isinstance(record, dict):
                continue
            for field in (
                "competence_evidence_id",
                "decision_evidence_id",
                "conflict_evidence_id",
            ):
                evidence = _safe_record_lookup(valid_manifest, record.get(field))
                if isinstance(evidence, dict):
                    expected_dependencies.add(evidence.get("sha256"))
                    if set(evidence.get("dependency_sha256", [])) != {
                        CURRENT_CONTRACT_CANONICAL_SHA256
                    }:
                        errors.append(
                            f"role decision {record_id}.{field} must bind exactly the parent contract"
                        )
        if isinstance(lane_evidence, dict):
            if lane_evidence.get("candidate_question_id") is not None:
                errors.append(
                    f"lane_decisions.{lane_id}.decision_evidence_id must be candidate neutral"
                )
            if set(lane_evidence.get("dependency_sha256", [])) != expected_dependencies:
                errors.append(
                    f"lane_decisions.{lane_id}.decision_evidence_id does not exactly bind its closure evidence"
                )

    overall_evidence_id = overall.get("decision_evidence_id")
    overall_evidence = _safe_record_lookup(valid_manifest, overall_evidence_id)
    if isinstance(overall_evidence, dict):
        expected_overall_dependencies = {CURRENT_CONTRACT_CANONICAL_SHA256} | {
            evidence.get("sha256")
            for evidence_id, evidence in valid_manifest.items()
            if evidence_id != overall_evidence_id
            and isinstance(evidence.get("sha256"), str)
        }
        if set(overall_evidence.get("dependency_sha256", [])) != expected_overall_dependencies:
            errors.append(
                "overall decision evidence must exactly bind the complete cited evidence package"
            )
        if overall_evidence.get("candidate_question_id") != selected_question_id:
            errors.append(
                "overall decision evidence candidate binding does not match the outcome"
            )

    return errors


def validate_final_decision_against_repository(document, parent_path=CONTRACT_PATH):
    """Validate the final artifact and the exact parent file in this checkout."""
    errors = []
    try:
        parent = load_governance_contract(Path(parent_path))
    except Exception as exc:  # converted to a fail-closed public validation error
        return [f"parent contract cannot be loaded: {type(exc).__name__}"]
    errors.extend(f"parent: {error}" for error in validate_governance_contract(parent))
    if canonical_contract_sha256(parent) != CURRENT_CONTRACT_CANONICAL_SHA256:
        errors.append("parent contract canonical SHA 256 does not match")
    errors.extend(validate_final_governance_decision(document))
    return errors
