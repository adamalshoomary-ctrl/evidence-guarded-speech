import copy
import hashlib
import tempfile
import unittest
from pathlib import Path

from motor_speech_voice.final_decision import (
    AUTHORITY_EVIDENCE_ISSUERS,
    AUTHORITY_ISSUER_SPECIALTY,
    DELIVERABLE_ISSUERS,
    DELIVERABLE_ISSUER_SPECIALTY,
    DELIVERABLE_TYPES,
    GLOBAL_SELECTION_DELIVERABLES,
    GLOBAL_SELECTION_ROLE_SPECS,
    LANE_SELECTION_DELIVERABLES,
    LANE_SELECTION_ROLE_SPECS,
    PROHIBITED_USE_FIELDS,
    evidence_node_sha256,
    validate_final_decision_against_repository,
    validate_final_governance_decision,
)
from motor_speech_voice.governance import (
    CURRENT_CONTRACT_CANONICAL_SHA256,
    EXPECTED_LANE_STATUSES,
    RELEASE_FIELDS,
    load_governance_contract,
)


DECISION_DATE = "2026-08-14"


def evidence_record(
    evidence_id,
    evidence_type,
    issuer="qualified_external_authority",
    subject=None,
    scope=None,
    institution_id=None,
    candidate_question_id=None,
    dependency_sha256=None,
    storage_class="approved_private_governance",
):
    record = {
        "evidence_type": evidence_type,
        "issuer_role_id": issuer,
        "subject_assignment_id": subject,
        "version": "1.0.0",
        "issued_date": DECISION_DATE,
        "artifact_sha256": hashlib.sha256(
            f"{evidence_id}:issued-artifact".encode("utf-8")
        ).hexdigest(),
        "sha256": "0" * 64,
        "institution_issued_id": institution_id,
        "storage_class": storage_class,
        "scope": scope or ["global"],
        "candidate_question_id": candidate_question_id,
        "dependency_sha256": dependency_sha256 or [],
        "status": "issued_final",
    }
    record["sha256"] = evidence_node_sha256(record)
    return record


def exact_intended_use(status="unsigned_no_selection_draft", evidence_id=None):
    intended = {
        "status": status,
        "evidence_id": evidence_id,
        "user": "firewalled_developer_research_team",
        "population": "consenting_adults_18_and_over",
        "setting": "offline_controlled_research",
        "input_source": "new_task_specific_recording_under_approved_protocol",
        "action": "isolated_checkpoint_23c_feasibility_only",
        "claim_level": "nonclinical_task_specific_observation",
    }
    intended.update({field: False for field in PROHIBITED_USE_FIELDS})
    return intended


def unresolved_authority():
    return {
        "legal_sponsor_evidence_id": None,
        "responsible_institution_evidence_id": None,
        "ethics_pathway": "unresolved",
        "ethics_decision_evidence_id": None,
        "site_governance_applicability": "unresolved",
        "site_applicability_determination_evidence_id": None,
        "site_authorisation_evidence_id": None,
        "privacy_act_coverage": "unresolved",
        "health_service_provider_coverage": "unresolved",
        "entity_data_role_matrix_evidence_id": None,
        "privacy_pia_evidence_id": None,
        "recording_law_evidence_id": None,
        "security_review_evidence_id": None,
        "retention_withdrawal_deletion_evidence_id": None,
        "app_5_collection_notice_status": "unresolved",
        "app_6_use_and_disclosure_status": "unresolved",
        "incidental_speaker_controls_status": "unresolved",
        "consent_materials_status": "unresolved",
        "overseas_processing": "unresolved",
        "secondary_model_training": "unresolved",
        "statistical_plan_evidence_id": None,
        "source_rights_evidence_id": None,
        "medical_device_status": "unresolved",
        "clinical_trial_pathway_status": "unresolved",
        "manufacturer_evidence_id": None,
        "australian_trial_sponsor_evidence_id": None,
        "regulatory_assessment_evidence_id": None,
    }


def empty_deliverables():
    return {
        deliverable_id: {
            "applicability": "unresolved",
            "evidence_id": None,
            "lane_scope": [],
            "reason_code": "not_resolved_for_no_selection",
        }
        for deliverable_id in DELIVERABLE_TYPES
    }


def lane_record(decision, evidence_id):
    closed = decision in {"no_selection", "unavailable"}
    return {
        "decision": decision,
        "candidate_question_id": None,
        "truth_class": None,
        "selected_construct_evidence_id": None,
        "selected_task_evidence_id": None,
        "selected_measure_evidence_id": None,
        "selected_score": None,
        "selected_threshold": None,
        "required_role_decision_ids": [],
        "decision_evidence_id": evidence_id,
        "reason_codes": ["required_governance_unresolved"],
        "evidence_needed_to_reopen": (
            ["complete_required_governance"] if closed else []
        ),
    }


def no_selection_fixture():
    manifest = {
        "evidence:owner-decision": evidence_record(
            "evidence:owner-decision",
            "owner_decision",
            issuer="owner",
            storage_class="public_record",
        ),
        "evidence:overall-decision": evidence_record(
            "evidence:overall-decision",
            "overall_decision",
            issuer="owner",
            storage_class="public_record",
        ),
    }
    lanes = {}
    for lane_id in EXPECTED_LANE_STATUSES:
        evidence_id = f"evidence:lane-{lane_id.replace('_', '.')}"
        manifest[evidence_id] = evidence_record(
            evidence_id,
            "lane_decision",
            issuer="owner",
            scope=[lane_id],
            storage_class="public_record",
        )
        decision = (
            "no_selection"
            if lane_id
            in {
                "motor_speech",
                "general_speech",
                "voice",
                "controlled_intelligibility",
            }
            else "not_required"
        )
        lanes[lane_id] = lane_record(decision, evidence_id)

    document = {
        "schema_version": "1.0.0",
        "contract_id": "motor_speech_voice_governance_final",
        "record_version": "1.0.0",
        "checkpoint": "23B",
        "parent_contract": {
            "contract_id": "motor_speech_voice_governance",
            "contract_version": "1.0.0",
            "canonical_sha256": CURRENT_CONTRACT_CANONICAL_SHA256,
        },
        "decision_date": DECISION_DATE,
        "evidence_manifest": manifest,
        "actor_register": {},
        "duty_assignments": {
            field: None
            for field in (
                "construct_control_assignment_id",
                "task_control_assignment_id",
                "reference_truth_assignment_id",
                "threshold_assignment_id",
                "data_custody_assignment_id",
                "release_assignment_id",
                "reference_truth_decision_evidence_id",
            )
        },
        "owner_decision": {
            "owner_decision_evidence_id": "evidence:owner-decision",
            "adults_first_confirmed": True,
            "children_excluded": True,
        },
        "intended_use": exact_intended_use(),
        "authority_outcomes": unresolved_authority(),
        "role_decisions": {},
        "deliverable_evidence": empty_deliverables(),
        "lane_decisions": lanes,
        "data_access": {
            "participant_or_study_recording_accessed": False,
            "existing_owner_audio_accessed": False,
            "private_participant_data_accessed": False,
            "new_recording_collected": False,
            "held_out_accessed": False,
            "private_governance_evidence_accessed": False,
        },
        "overall_decision": {
            "decision": "no_selection",
            "checkpoint_complete": True,
            "decision_evidence_id": "evidence:overall-decision",
            "reason_codes": ["required_governance_unresolved"],
            "evidence_needed_to_reopen": ["complete_required_governance"],
        },
        "downstream": {
            "checkpoint_23c": "not_applicable",
            "checkpoint_23c_eligible_lanes": [],
            "checkpoint_23d": "not_applicable",
            "checkpoint_23e": "not_applicable",
            "checkpoint_23f": "not_applicable",
            "participant_work_may_begin": False,
            "implementation_may_begin": False,
        },
        "release_boundaries": {field: False for field in RELEASE_FIELDS},
    }
    owner_assignment = add_actor(
        document, "owner", ["product_owner", "developer"]
    )
    appointment_id = document["actor_register"][owner_assignment][
        "appointment_evidence_id"
    ]
    document["evidence_manifest"][appointment_id].update(
        {
            "issuer_role_id": "owner",
            "storage_class": "public_record",
        }
    )
    document["evidence_manifest"]["evidence:owner-decision"][
        "subject_assignment_id"
    ] = owner_assignment
    document["evidence_manifest"]["evidence:overall-decision"][
        "subject_assignment_id"
    ] = owner_assignment
    for lane in document["lane_decisions"].values():
        document["evidence_manifest"][lane["decision_evidence_id"]][
            "subject_assignment_id"
        ] = owner_assignment
    bind_closed_lane_evidence(document)
    bind_overall_evidence(document)
    return document


def add_evidence(
    document,
    evidence_id,
    evidence_type,
    issuer="qualified_external_authority",
    subject=None,
    scope=None,
    institution_id=None,
    candidate_question_id=None,
    dependency_sha256=None,
    storage_class="approved_private_governance",
):
    document["evidence_manifest"][evidence_id] = evidence_record(
        evidence_id,
        evidence_type,
        issuer=issuer,
        subject=subject,
        scope=scope,
        institution_id=institution_id,
        candidate_question_id=candidate_question_id,
        dependency_sha256=dependency_sha256,
        storage_class=storage_class,
    )
    return evidence_id


def add_actor(document, short_id, classes):
    assignment_id = f"assignment:{short_id}"
    appointment_id = f"evidence:appointment-{short_id}"
    add_evidence(
        document,
        appointment_id,
        "competence_appointment",
        subject=assignment_id,
    )
    document["actor_register"][assignment_id] = {
        "organisation_id": f"org:{short_id}",
        "appointment_evidence_id": appointment_id,
        "classes": classes,
    }
    return assignment_id


def add_role(
    document,
    short_id,
    role_id,
    assignment_id,
    scope,
    specialty="generic",
    outcome="signed_no_unresolved_block",
):
    record_id = f"roledec:{short_id}"
    decision_id = f"evidence:role-decision-{short_id}"
    conflict_id = f"evidence:conflict-{short_id}"
    appointment_id = document["actor_register"][assignment_id][
        "appointment_evidence_id"
    ]
    add_evidence(
        document,
        decision_id,
        "role_domain_decision",
        issuer=role_id,
        subject=assignment_id,
        scope=scope,
    )
    add_evidence(
        document,
        conflict_id,
        "conflict_record",
        subject=assignment_id,
        scope=scope,
    )
    document["role_decisions"][record_id] = {
        "role_id": role_id,
        "specialty": specialty,
        "assignment_id": assignment_id,
        "scope": scope,
        "applicability": "required",
        "outcome": outcome,
        "competence_evidence_id": appointment_id,
        "decision_evidence_id": decision_id,
        "conflict_evidence_id": conflict_id,
        "recused": False,
        "eligible_to_decide": True,
        "reason_codes": ["domain_review_complete"],
    }
    return record_id


def bind_closed_lane_evidence(document):
    for lane in document["lane_decisions"].values():
        if lane["decision"] not in {"no_selection", "not_required", "unavailable"}:
            continue
        dependencies = {CURRENT_CONTRACT_CANONICAL_SHA256}
        for record_id in lane["required_role_decision_ids"]:
            role = document["role_decisions"][record_id]
            for field in (
                "competence_evidence_id",
                "decision_evidence_id",
                "conflict_evidence_id",
            ):
                evidence = document["evidence_manifest"][role[field]]
                evidence["dependency_sha256"] = [
                    CURRENT_CONTRACT_CANONICAL_SHA256
                ]
                dependencies.add(evidence["sha256"])
        lane_evidence = document["evidence_manifest"][lane["decision_evidence_id"]]
        lane_evidence["candidate_question_id"] = None
        lane_evidence["dependency_sha256"] = sorted(dependencies)


def seal_evidence_graph(document):
    manifest = document["evidence_manifest"]
    old_digest_to_id = {
        evidence["sha256"]: evidence_id
        for evidence_id, evidence in manifest.items()
    }
    sealed = {}
    visiting = set()

    def seal(evidence_id):
        if evidence_id in sealed:
            return sealed[evidence_id]
        if evidence_id in visiting:
            return manifest[evidence_id]["sha256"]
        visiting.add(evidence_id)
        evidence = manifest[evidence_id]
        dependencies = []
        for dependency in evidence["dependency_sha256"]:
            dependency_id = old_digest_to_id.get(dependency)
            dependencies.append(
                seal(dependency_id) if dependency_id is not None else dependency
            )
        evidence["dependency_sha256"] = sorted(dependencies)
        evidence["sha256"] = evidence_node_sha256(evidence)
        visiting.remove(evidence_id)
        sealed[evidence_id] = evidence["sha256"]
        return evidence["sha256"]

    for evidence_id in manifest:
        seal(evidence_id)


def bind_overall_evidence(document, candidate_question_id=None):
    overall_id = document["overall_decision"]["decision_evidence_id"]
    overall_evidence = document["evidence_manifest"][overall_id]
    overall_evidence["candidate_question_id"] = candidate_question_id
    overall_evidence["dependency_sha256"] = sorted(
        {CURRENT_CONTRACT_CANONICAL_SHA256}
        | {
            evidence["sha256"]
            for evidence_id, evidence in document["evidence_manifest"].items()
            if evidence_id != overall_id
        }
    )
    seal_evidence_graph(document)


def selected_spec_dependencies(document):
    selected_lane = next(
        lane
        for lane in document["lane_decisions"].values()
        if lane["decision"] == "selection"
    )
    return {CURRENT_CONTRACT_CANONICAL_SHA256} | {
        document["evidence_manifest"][selected_lane[field]]["sha256"]
        for field in (
            "selected_construct_evidence_id",
            "selected_task_evidence_id",
            "selected_measure_evidence_id",
        )
    }


def add_conditional_authority_evidence(
    document,
    field,
    evidence_id,
    evidence_type,
    issuer,
    subject,
):
    question_id = "controlled_rapid_syllable_timing"
    dependencies = selected_spec_dependencies(document)
    if field == "site_authorisation_evidence_id":
        for prerequisite_field in (
            "ethics_decision_evidence_id",
            "site_applicability_determination_evidence_id",
        ):
            prerequisite_id = document["authority_outcomes"].get(
                prerequisite_field
            )
            if prerequisite_id is not None:
                dependencies.add(
                    document["evidence_manifest"][prerequisite_id]["sha256"]
                )
    add_evidence(
        document,
        evidence_id,
        evidence_type,
        issuer=issuer,
        subject=subject,
        scope=["motor_speech"],
        candidate_question_id=question_id,
        dependency_sha256=sorted(dependencies),
    )
    document["authority_outcomes"][field] = evidence_id
    lane_evidence = document["evidence_manifest"][
        document["lane_decisions"]["motor_speech"]["decision_evidence_id"]
    ]
    lane_evidence["dependency_sha256"] = sorted(
        set(lane_evidence["dependency_sha256"])
        | {document["evidence_manifest"][evidence_id]["sha256"]}
    )
    bind_overall_evidence(document, question_id)
    return evidence_id


def add_participant_reference(document):
    question_id = "controlled_rapid_syllable_timing"
    reference_lane = "participant_report"
    field_specs = {
        "selected_construct_evidence_id": (
            "participant-construct",
            "construct_specification",
            "independent_speech_measurement_scientist",
            "assignment:measurement",
        ),
        "selected_task_evidence_id": (
            "participant-task",
            "task_protocol",
            "paid_lived_experience_governance_group",
            "assignment:lived",
        ),
        "selected_measure_evidence_id": (
            "participant-measure",
            "measure_specification",
            "independent_speech_measurement_scientist",
            "assignment:measurement",
        ),
    }
    reference_ids = {}
    for field, (short_id, evidence_type, issuer, subject) in field_specs.items():
        evidence_id = add_evidence(
            document,
            f"evidence:{short_id}",
            evidence_type,
            issuer=issuer,
            subject=subject,
            scope=[reference_lane],
            candidate_question_id=question_id,
            dependency_sha256=[CURRENT_CONTRACT_CANONICAL_SHA256],
        )
        reference_ids[field] = evidence_id

    reference_role_ids = []
    for record_id, role in document["role_decisions"].items():
        if role["role_id"] not in {
            "paid_lived_experience_governance_group",
            "independent_speech_measurement_scientist",
        }:
            continue
        reference_role_ids.append(record_id)
        role["scope"] = ["motor_speech", reference_lane]
        for field in ("decision_evidence_id", "conflict_evidence_id"):
            document["evidence_manifest"][role[field]]["scope"] = [
                "motor_speech",
                reference_lane,
            ]

    protocol_id = add_evidence(
        document,
        "evidence:participant-report-protocol",
        DELIVERABLE_TYPES["participant_report_protocol"],
        issuer="paid_lived_experience_governance_group",
        subject="assignment:lived",
        scope=["motor_speech", reference_lane],
    )
    document["deliverable_evidence"]["participant_report_protocol"] = {
        "applicability": "required",
        "evidence_id": protocol_id,
        "lane_scope": ["motor_speech", reference_lane],
        "reason_code": "required_for_selected_lane",
    }
    lane = document["lane_decisions"][reference_lane]
    lane.update(
        {
            "decision": "required_reference",
            "candidate_question_id": None,
            "truth_class": "participant_report",
            **reference_ids,
            "required_role_decision_ids": sorted(reference_role_ids),
            "reason_codes": ["required_reference_approved"],
            "evidence_needed_to_reopen": [],
        }
    )

    selected_dependencies = selected_spec_dependencies(document) | {
        document["evidence_manifest"][evidence_id]["sha256"]
        for evidence_id in reference_ids.values()
    }
    for evidence in document["evidence_manifest"].values():
        if (
            evidence["candidate_question_id"] == question_id
            and evidence["evidence_type"]
            not in {
                "construct_specification",
                "task_protocol",
                "measure_specification",
                "lane_decision",
                "overall_decision",
            }
        ):
            evidence["dependency_sha256"] = sorted(
                set(evidence["dependency_sha256"]) | selected_dependencies
            )
    protocol = document["evidence_manifest"][protocol_id]
    protocol["candidate_question_id"] = question_id
    protocol["dependency_sha256"] = sorted(selected_dependencies)
    for record_id in reference_role_ids:
        decision = document["evidence_manifest"][
            document["role_decisions"][record_id]["decision_evidence_id"]
        ]
        decision["dependency_sha256"] = sorted(
            set(decision["dependency_sha256"]) | {protocol["sha256"]}
        )

    main_lane_evidence = document["evidence_manifest"][
        document["lane_decisions"]["motor_speech"]["decision_evidence_id"]
    ]
    main_lane_evidence["dependency_sha256"] = sorted(
        set(main_lane_evidence["dependency_sha256"])
        | selected_dependencies
        | {protocol["sha256"]}
    )
    reference_lane_evidence = document["evidence_manifest"][
        lane["decision_evidence_id"]
    ]
    reference_lane_evidence["issuer_role_id"] = (
        "independent_truth_and_release_group"
    )
    reference_lane_evidence["subject_assignment_id"] = "assignment:release"
    reference_lane_evidence["scope"] = ["motor_speech", reference_lane]
    reference_lane_evidence["candidate_question_id"] = question_id
    reference_lane_evidence["dependency_sha256"] = list(
        main_lane_evidence["dependency_sha256"]
    )
    bind_overall_evidence(document, question_id)


def add_hrec_path(document):
    question_id = "controlled_rapid_syllable_timing"
    actor = add_actor(document, "hrec", ["ethics"])
    record_id = add_role(
        document,
        "hrec",
        "human_research_ethics_committee_if_required",
        actor,
        ["motor_speech"],
    )
    document["lane_decisions"]["motor_speech"][
        "required_role_decision_ids"
    ].append(record_id)
    document["lane_decisions"]["motor_speech"][
        "required_role_decision_ids"
    ].sort()
    document["authority_outcomes"]["ethics_pathway"] = "hrec"
    ethics_id = document["authority_outcomes"]["ethics_decision_evidence_id"]
    document["evidence_manifest"][ethics_id]["subject_assignment_id"] = actor

    selected_dependencies = selected_spec_dependencies(document)
    role = document["role_decisions"][record_id]
    competence = document["evidence_manifest"][role["competence_evidence_id"]]
    conflict = document["evidence_manifest"][role["conflict_evidence_id"]]
    decision = document["evidence_manifest"][role["decision_evidence_id"]]
    conflict["candidate_question_id"] = question_id
    conflict["dependency_sha256"] = sorted(selected_dependencies)
    decision["candidate_question_id"] = question_id
    decision["dependency_sha256"] = sorted(
        selected_dependencies | {competence["sha256"], conflict["sha256"]}
    )
    lane_evidence = document["evidence_manifest"][
        document["lane_decisions"]["motor_speech"]["decision_evidence_id"]
    ]
    lane_evidence["dependency_sha256"] = sorted(
        set(lane_evidence["dependency_sha256"])
        | {competence["sha256"], conflict["sha256"], decision["sha256"]}
    )
    bind_overall_evidence(document, question_id)


def add_ctn_path(document):
    add_hrec_path(document)
    document["authority_outcomes"]["site_governance_applicability"] = "required"
    site_id = add_conditional_authority_evidence(
        document,
        "site_authorisation_evidence_id",
        "evidence:site-authorisation",
        "site_authorisation",
        "responsible_research_institution",
        "assignment:institution",
    )
    site_evidence = document["evidence_manifest"][site_id]
    site_evidence["dependency_sha256"] = sorted(
        set(site_evidence["dependency_sha256"])
        | {
            document["evidence_manifest"][
                document["authority_outcomes"]["ethics_decision_evidence_id"]
            ]["sha256"],
            document["evidence_manifest"][
                document["authority_outcomes"][
                    "site_applicability_determination_evidence_id"
                ]
            ]["sha256"],
        }
    )
    document["authority_outcomes"]["medical_device_status"] = "medical_device"
    document["authority_outcomes"]["clinical_trial_pathway_status"] = "ctn_required"
    manufacturer_id = add_conditional_authority_evidence(
        document,
        "manufacturer_evidence_id",
        "evidence:manufacturer",
        "manufacturer_identity",
        "owner",
        "assignment:owner",
    )
    sponsor_id = add_conditional_authority_evidence(
        document,
        "australian_trial_sponsor_evidence_id",
        "evidence:trial-sponsor",
        "australian_trial_sponsor_identity",
        "owner",
        "assignment:owner",
    )
    return manufacturer_id, sponsor_id


def add_clinical_reference(document):
    question_id = "controlled_rapid_syllable_timing"
    reference_lane = "clinical_laryngeal_reference"
    lead_actor = add_actor(document, "clinical-lead", ["professional"])
    ent_actor = add_actor(document, "ent", ["professional"])
    lead_record_id = add_role(
        document,
        "clinical-lead",
        "independent_clinical_reference_lead_if_required",
        lead_actor,
        ["motor_speech", reference_lane],
    )
    ent_record_id = add_role(
        document,
        "ent",
        "independent_ent_or_laryngologist_if_required",
        ent_actor,
        ["motor_speech", reference_lane],
    )
    document["lane_decisions"]["motor_speech"][
        "required_role_decision_ids"
    ].extend([lead_record_id, ent_record_id])
    document["lane_decisions"]["motor_speech"][
        "required_role_decision_ids"
    ].sort()

    field_specs = {
        "selected_construct_evidence_id": (
            "clinical-construct",
            "construct_specification",
        ),
        "selected_task_evidence_id": ("clinical-task", "task_protocol"),
        "selected_measure_evidence_id": (
            "clinical-measure",
            "measure_specification",
        ),
    }
    reference_ids = {}
    for field, (short_id, evidence_type) in field_specs.items():
        reference_ids[field] = add_evidence(
            document,
            f"evidence:{short_id}",
            evidence_type,
            issuer="independent_clinical_reference_lead_if_required",
            subject=lead_actor,
            scope=[reference_lane],
            candidate_question_id=question_id,
            dependency_sha256=[CURRENT_CONTRACT_CANONICAL_SHA256],
        )
    manual_id = add_evidence(
        document,
        "evidence:clinical-reference-manual",
        DELIVERABLE_TYPES["clinical_reference_manual"],
        issuer="independent_clinical_reference_lead_if_required",
        subject=lead_actor,
        scope=["motor_speech", reference_lane],
    )
    document["deliverable_evidence"]["clinical_reference_manual"] = {
        "applicability": "required",
        "evidence_id": manual_id,
        "lane_scope": ["motor_speech", reference_lane],
        "reason_code": "required_for_selected_lane",
    }
    lane = document["lane_decisions"][reference_lane]
    lane.update(
        {
            "decision": "required_reference",
            "candidate_question_id": None,
            "truth_class": "clinical_reference",
            **reference_ids,
            "required_role_decision_ids": sorted(
                [lead_record_id, ent_record_id]
            ),
            "reason_codes": ["required_reference_approved"],
            "evidence_needed_to_reopen": [],
        }
    )

    selected_dependencies = selected_spec_dependencies(document) | {
        document["evidence_manifest"][evidence_id]["sha256"]
        for evidence_id in reference_ids.values()
    }
    for evidence in document["evidence_manifest"].values():
        if (
            evidence["candidate_question_id"] == question_id
            and evidence["evidence_type"]
            not in {
                "construct_specification",
                "task_protocol",
                "measure_specification",
                "lane_decision",
                "overall_decision",
            }
        ):
            evidence["dependency_sha256"] = sorted(
                set(evidence["dependency_sha256"]) | selected_dependencies
            )
    manual = document["evidence_manifest"][manual_id]
    manual["candidate_question_id"] = question_id
    manual["dependency_sha256"] = sorted(selected_dependencies)

    new_role_hashes = set()
    for record_id in (lead_record_id, ent_record_id):
        role = document["role_decisions"][record_id]
        competence = document["evidence_manifest"][role["competence_evidence_id"]]
        conflict = document["evidence_manifest"][role["conflict_evidence_id"]]
        decision = document["evidence_manifest"][role["decision_evidence_id"]]
        conflict["candidate_question_id"] = question_id
        conflict["dependency_sha256"] = sorted(selected_dependencies)
        decision["candidate_question_id"] = question_id
        decision["dependency_sha256"] = sorted(
            selected_dependencies
            | {competence["sha256"], conflict["sha256"], manual["sha256"]}
        )
        new_role_hashes.update(
            {competence["sha256"], conflict["sha256"], decision["sha256"]}
        )

    main_lane_evidence = document["evidence_manifest"][
        document["lane_decisions"]["motor_speech"]["decision_evidence_id"]
    ]
    main_lane_evidence["dependency_sha256"] = sorted(
        set(main_lane_evidence["dependency_sha256"])
        | selected_dependencies
        | {manual["sha256"]}
        | new_role_hashes
    )
    reference_lane_evidence = document["evidence_manifest"][
        lane["decision_evidence_id"]
    ]
    reference_lane_evidence["issuer_role_id"] = (
        "independent_truth_and_release_group"
    )
    reference_lane_evidence["subject_assignment_id"] = "assignment:release"
    reference_lane_evidence["scope"] = ["motor_speech", reference_lane]
    reference_lane_evidence["candidate_question_id"] = question_id
    reference_lane_evidence["dependency_sha256"] = list(
        main_lane_evidence["dependency_sha256"]
    )
    bind_overall_evidence(document, question_id)


def selection_fixture():
    document = no_selection_fixture()
    lane_id = "motor_speech"

    intended_id = add_evidence(
        document,
        "evidence:signed-intended-use",
        "signed_intended_use",
        issuer="owner",
        scope=[lane_id],
    )
    document["intended_use"] = exact_intended_use(
        "signed_selection_use", intended_id
    )

    authority_spec = {
        "legal_sponsor_evidence_id": ("legal-sponsor", "legal_sponsor_identity"),
        "responsible_institution_evidence_id": (
            "institution-authority",
            "responsible_institution_authority",
        ),
        "ethics_decision_evidence_id": ("ethics", "ethics_decision"),
        "site_applicability_determination_evidence_id": (
            "site-applicability",
            "site_applicability_determination",
        ),
        "entity_data_role_matrix_evidence_id": (
            "entity-matrix",
            "entity_data_role_matrix",
        ),
        "privacy_pia_evidence_id": ("pia", "privacy_impact_assessment"),
        "recording_law_evidence_id": (
            "recording-law",
            "recording_law_review",
        ),
        "security_review_evidence_id": ("security", "security_review"),
        "retention_withdrawal_deletion_evidence_id": (
            "retention",
            "retention_withdrawal_deletion_plan",
        ),
        "statistical_plan_evidence_id": (
            "statistics",
            "statistical_analysis_plan",
        ),
        "source_rights_evidence_id": (
            "source-rights",
            "source_commercial_rights_review",
        ),
        "regulatory_assessment_evidence_id": (
            "regulatory",
            "regulatory_pathway_assessment",
        ),
    }
    authority = unresolved_authority()
    for field, (short_id, evidence_type) in authority_spec.items():
        authority[field] = add_evidence(
            document,
            f"evidence:{short_id}",
            evidence_type,
            issuer=sorted(AUTHORITY_EVIDENCE_ISSUERS[field])[0],
            scope=[lane_id],
            institution_id=(
                f"institution:{short_id}"
                if evidence_type
                in {
                    "responsible_institution_authority",
                    "ethics_decision",
                    "site_applicability_determination",
                }
                else None
            ),
        )
    authority.update(
        {
            "ethics_pathway": "institutional_lower_risk",
            "site_governance_applicability": "not_applicable",
            "privacy_act_coverage": "one_or_more_app_entities",
            "health_service_provider_coverage": "applies",
            "app_5_collection_notice_status": "approved_for_exact_protocol",
            "app_6_use_and_disclosure_status": "approved_for_exact_protocol",
            "incidental_speaker_controls_status": "approved_for_exact_protocol",
            "consent_materials_status": "approved_for_exact_protocol",
            "overseas_processing": "prohibited",
            "secondary_model_training": "prohibited",
            "medical_device_status": "outside_definition",
            "clinical_trial_pathway_status": "not_applicable",
        }
    )
    document["authority_outcomes"] = authority

    actor_specs = {
        "owner": ["product_owner", "developer"],
        "institution": ["institution"],
        "privacy": ["privacy"],
        "legal": ["australian_legal"],
        "security": ["security"],
        "regulatory": ["regulatory"],
        "custodian": ["data_custodian"],
        "lived": ["lived_experience"],
        "motor": ["professional"],
        "measurement": ["measurement"],
        "statistics": ["statistician"],
        "truth": ["reference_truth"],
        "release": ["release_decision"],
    }
    assignments = {
        short_id: add_actor(document, short_id, classes)
        for short_id, classes in actor_specs.items()
    }
    document["duty_assignments"] = {
        "construct_control_assignment_id": assignments["measurement"],
        "task_control_assignment_id": assignments["motor"],
        "reference_truth_assignment_id": assignments["truth"],
        "threshold_assignment_id": assignments["statistics"],
        "data_custody_assignment_id": assignments["custodian"],
        "release_assignment_id": assignments["release"],
        "reference_truth_decision_evidence_id": None,
    }
    role_specs = {
        ("product_owner", "generic"): "owner",
        ("responsible_research_institution", "generic"): "institution",
        ("privacy_security_and_australian_legal_review", "privacy"): "privacy",
        (
            "privacy_security_and_australian_legal_review",
            "australian_legal",
        ): "legal",
        ("privacy_security_and_australian_legal_review", "security"): "security",
        (
            "australian_medical_device_regulatory_specialist",
            "generic",
        ): "regulatory",
        ("independent_data_and_split_custodian", "generic"): "custodian",
        ("paid_lived_experience_governance_group", "generic"): "lived",
        ("independent_adult_motor_speech_cpsp", "generic"): "motor",
        ("independent_speech_measurement_scientist", "generic"): "measurement",
        ("biostatistician_or_measurement_specialist", "generic"): "statistics",
        ("independent_truth_and_release_group", "generic"): "release",
    }
    document["evidence_manifest"][intended_id]["subject_assignment_id"] = assignments[
        "owner"
    ]
    document["evidence_manifest"]["evidence:owner-decision"][
        "subject_assignment_id"
    ] = assignments["owner"]
    document["evidence_manifest"]["evidence:overall-decision"][
        "subject_assignment_id"
    ] = assignments["owner"]
    for lane in document["lane_decisions"].values():
        document["evidence_manifest"][lane["decision_evidence_id"]][
            "subject_assignment_id"
        ] = assignments["owner"]

    for field in authority_spec:
        if field == "ethics_decision_evidence_id":
            role_spec = ("responsible_research_institution", "generic")
        else:
            role_spec = AUTHORITY_ISSUER_SPECIALTY[field]
        actor_short_id = role_specs[role_spec]
        document["evidence_manifest"][authority[field]][
            "subject_assignment_id"
        ] = assignments[actor_short_id]
    global_specs = set(GLOBAL_SELECTION_ROLE_SPECS)
    role_record_ids = []
    for (role_id, specialty), actor_short_id in role_specs.items():
        record_short_id = f"{actor_short_id}-{specialty.replace('_', '.')}"
        record_id = add_role(
            document,
            record_short_id,
            role_id,
            assignments[actor_short_id],
            ["global"] if (role_id, specialty) in global_specs else [lane_id],
            specialty=specialty,
        )
        role_record_ids.append(record_id)

    required_deliverables = GLOBAL_SELECTION_DELIVERABLES | LANE_SELECTION_DELIVERABLES[
        lane_id
    ]
    shared_evidence = {
        "signed_intended_use": intended_id,
        "statistical_analysis_plan": authority["statistical_plan_evidence_id"],
        "source_commercial_rights_review": authority["source_rights_evidence_id"],
        "regulatory_pathway_assessment": authority[
            "regulatory_assessment_evidence_id"
        ],
    }
    for deliverable_id in DELIVERABLE_TYPES:
        if deliverable_id in required_deliverables:
            evidence_id = shared_evidence.get(deliverable_id)
            if evidence_id is None:
                evidence_id = add_evidence(
                    document,
                    f"evidence:deliverable-{deliverable_id.replace('_', '.')}",
                    DELIVERABLE_TYPES[deliverable_id],
                    issuer=sorted(DELIVERABLE_ISSUERS[deliverable_id])[0],
                    scope=[lane_id],
                )
            role_spec = DELIVERABLE_ISSUER_SPECIALTY[deliverable_id]
            document["evidence_manifest"][evidence_id][
                "subject_assignment_id"
            ] = assignments[role_specs[role_spec]]
            document["deliverable_evidence"][deliverable_id] = {
                "applicability": "required",
                "evidence_id": evidence_id,
                "lane_scope": [lane_id],
                "reason_code": "required_for_selected_lane",
            }
        else:
            document["deliverable_evidence"][deliverable_id] = {
                "applicability": "not_applicable",
                "evidence_id": None,
                "lane_scope": [],
                "reason_code": "not_required_for_selected_lane",
            }

    construct_id = add_evidence(
        document,
        "evidence:selected-construct",
        "construct_specification",
        issuer="independent_speech_measurement_scientist",
        subject=assignments["measurement"],
        scope=[lane_id],
    )
    task_id = add_evidence(
        document,
        "evidence:selected-task",
        "task_protocol",
        issuer="independent_adult_motor_speech_cpsp",
        subject=assignments["motor"],
        scope=[lane_id],
    )
    measure_id = add_evidence(
        document,
        "evidence:selected-measure",
        "measure_specification",
        issuer="independent_speech_measurement_scientist",
        subject=assignments["measurement"],
        scope=[lane_id],
    )
    document["lane_decisions"][lane_id] = {
        "decision": "selection",
        "candidate_question_id": "controlled_rapid_syllable_timing",
        "truth_class": "temporal_task_observation",
        "selected_construct_evidence_id": construct_id,
        "selected_task_evidence_id": task_id,
        "selected_measure_evidence_id": measure_id,
        "selected_score": None,
        "selected_threshold": None,
        "required_role_decision_ids": sorted(role_record_ids),
        "decision_evidence_id": document["lane_decisions"][lane_id][
            "decision_evidence_id"
        ],
        "reason_codes": ["all_required_governance_complete"],
        "evidence_needed_to_reopen": [],
    }
    document["data_access"]["private_governance_evidence_accessed"] = True
    document["overall_decision"].update(
        {
            "decision": "selection",
            "reason_codes": ["one_candidate_governed_for_feasibility"],
            "evidence_needed_to_reopen": [],
        }
    )
    document["downstream"].update(
        {
            "checkpoint_23c": "pending_separate_owner_approval",
            "checkpoint_23c_eligible_lanes": [lane_id],
            "checkpoint_23d": "locked",
            "checkpoint_23e": "locked",
            "checkpoint_23f": "locked",
        }
    )
    question_id = "controlled_rapid_syllable_timing"
    selected_ids = {construct_id, task_id, measure_id}
    selected_hashes = {CURRENT_CONTRACT_CANONICAL_SHA256} | {
        document["evidence_manifest"][evidence_id]["sha256"]
        for evidence_id in selected_ids
    }
    for evidence_id in selected_ids:
        evidence = document["evidence_manifest"][evidence_id]
        evidence["candidate_question_id"] = question_id
        evidence["dependency_sha256"] = [CURRENT_CONTRACT_CANONICAL_SHA256]

    truth_appointment_id = document["actor_register"][assignments["truth"]][
        "appointment_evidence_id"
    ]
    truth_decision_id = add_evidence(
        document,
        "evidence:reference-truth-decision",
        "role_domain_decision",
        issuer="independent_truth_and_release_group",
        subject=assignments["truth"],
        scope=[lane_id],
        candidate_question_id=question_id,
        dependency_sha256=sorted(
            selected_hashes
            | {
                document["evidence_manifest"][truth_appointment_id]["sha256"]
            }
        ),
    )
    document["duty_assignments"][
        "reference_truth_decision_evidence_id"
    ] = truth_decision_id

    selection_package_ids = {
        "evidence:owner-decision",
        intended_id,
        truth_appointment_id,
        truth_decision_id,
        *(
            evidence_id
            for field in authority_spec
            if (evidence_id := authority[field]) is not None
        ),
        *(
            record["evidence_id"]
            for record in document["deliverable_evidence"].values()
            if record["applicability"] == "required"
        ),
    }
    document["evidence_manifest"][intended_id]["candidate_question_id"] = question_id
    document["evidence_manifest"][intended_id]["dependency_sha256"] = sorted(
        selected_hashes
    )
    for field in authority_spec:
        evidence = document["evidence_manifest"][authority[field]]
        evidence["candidate_question_id"] = question_id
        evidence["dependency_sha256"] = sorted(selected_hashes)
    for deliverable in document["deliverable_evidence"].values():
        if deliverable["applicability"] != "required":
            continue
        evidence = document["evidence_manifest"][deliverable["evidence_id"]]
        evidence["candidate_question_id"] = question_id
        evidence["dependency_sha256"] = sorted(selected_hashes)

    for role in document["role_decisions"].values():
        competence_id = role["competence_evidence_id"]
        conflict_id = role["conflict_evidence_id"]
        decision_id = role["decision_evidence_id"]
        conflict = document["evidence_manifest"][conflict_id]
        conflict["candidate_question_id"] = question_id
        conflict["dependency_sha256"] = sorted(selected_hashes)
        decision_dependencies = selected_hashes | {
            document["evidence_manifest"][competence_id]["sha256"],
            conflict["sha256"],
        }
        decision = document["evidence_manifest"][decision_id]
        decision["candidate_question_id"] = question_id
        decision["dependency_sha256"] = sorted(decision_dependencies)
        selection_package_ids.update({competence_id, conflict_id, decision_id})

    selection_package_hashes = selected_hashes | {
        document["evidence_manifest"][evidence_id]["sha256"]
        for evidence_id in selection_package_ids
    }
    lane_decision_id = document["lane_decisions"][lane_id]["decision_evidence_id"]
    lane_decision = document["evidence_manifest"][lane_decision_id]
    lane_decision["issuer_role_id"] = "independent_truth_and_release_group"
    lane_decision["subject_assignment_id"] = assignments["release"]
    lane_decision["candidate_question_id"] = question_id
    lane_decision["dependency_sha256"] = sorted(selection_package_hashes)

    bind_closed_lane_evidence(document)
    bind_overall_evidence(document, question_id)
    return document


def rebind_complete_selection_package(document):
    selected_lane_id = next(
        lane_id
        for lane_id, lane in document["lane_decisions"].items()
        if lane["decision"] == "selection"
    )
    question_id = document["lane_decisions"][selected_lane_id][
        "candidate_question_id"
    ]
    active_lane_ids = {
        selected_lane_id,
        *(
            lane_id
            for lane_id, lane in document["lane_decisions"].items()
            if lane["decision"] == "required_reference"
        ),
    }
    selected_fields = (
        "selected_construct_evidence_id",
        "selected_task_evidence_id",
        "selected_measure_evidence_id",
    )
    selected_spec_ids = {
        document["lane_decisions"][lane_id][field]
        for lane_id in active_lane_ids
        for field in selected_fields
    }
    for evidence_id in selected_spec_ids:
        evidence = document["evidence_manifest"][evidence_id]
        evidence["candidate_question_id"] = question_id
        evidence["dependency_sha256"] = [CURRENT_CONTRACT_CANONICAL_SHA256]
    selected_hashes = {CURRENT_CONTRACT_CANONICAL_SHA256} | {
        document["evidence_manifest"][evidence_id]["sha256"]
        for evidence_id in selected_spec_ids
    }

    intended_id = document["intended_use"]["evidence_id"]
    candidate_package_ids = {"evidence:owner-decision", intended_id}
    document["evidence_manifest"][intended_id]["candidate_question_id"] = question_id
    document["evidence_manifest"][intended_id]["dependency_sha256"] = sorted(
        selected_hashes
    )

    for field, evidence_id in document["authority_outcomes"].items():
        if not field.endswith("_evidence_id") or evidence_id is None:
            continue
        evidence = document["evidence_manifest"][evidence_id]
        evidence["candidate_question_id"] = question_id
        dependencies = set(selected_hashes)
        if field == "site_authorisation_evidence_id":
            for prerequisite_field in (
                "ethics_decision_evidence_id",
                "site_applicability_determination_evidence_id",
            ):
                prerequisite_id = document["authority_outcomes"][
                    prerequisite_field
                ]
                dependencies.add(
                    document["evidence_manifest"][prerequisite_id]["sha256"]
                )
        evidence["dependency_sha256"] = sorted(dependencies)
        candidate_package_ids.add(evidence_id)

    for deliverable in document["deliverable_evidence"].values():
        if deliverable["applicability"] != "required":
            continue
        evidence_id = deliverable["evidence_id"]
        evidence = document["evidence_manifest"][evidence_id]
        evidence["candidate_question_id"] = question_id
        evidence["dependency_sha256"] = sorted(selected_hashes)
        candidate_package_ids.add(evidence_id)

    selected_role_ids = document["lane_decisions"][selected_lane_id][
        "required_role_decision_ids"
    ]
    for record_id in selected_role_ids:
        role = document["role_decisions"][record_id]
        competence_id = role["competence_evidence_id"]
        conflict_id = role["conflict_evidence_id"]
        decision_id = role["decision_evidence_id"]
        conflict = document["evidence_manifest"][conflict_id]
        conflict["candidate_question_id"] = question_id
        conflict["dependency_sha256"] = sorted(selected_hashes)
        decision_dependencies = set(selected_hashes) | {
            document["evidence_manifest"][competence_id]["sha256"],
            conflict["sha256"],
        }
        if role["role_id"] in {
            "paid_lived_experience_governance_group",
            "independent_speech_measurement_scientist",
        } and document["lane_decisions"]["participant_report"][
            "decision"
        ] == "required_reference":
            protocol_id = document["deliverable_evidence"][
                "participant_report_protocol"
            ]["evidence_id"]
            decision_dependencies.add(
                document["evidence_manifest"][protocol_id]["sha256"]
            )
        if role["role_id"] in {
            "independent_clinical_reference_lead_if_required",
            "independent_ent_or_laryngologist_if_required",
        } and document["lane_decisions"]["clinical_laryngeal_reference"][
            "decision"
        ] == "required_reference":
            manual_id = document["deliverable_evidence"][
                "clinical_reference_manual"
            ]["evidence_id"]
            decision_dependencies.add(
                document["evidence_manifest"][manual_id]["sha256"]
            )
        decision = document["evidence_manifest"][decision_id]
        decision["candidate_question_id"] = question_id
        decision["dependency_sha256"] = sorted(decision_dependencies)
        candidate_package_ids.update(
            {competence_id, conflict_id, decision_id}
        )

    truth_assignment = document["duty_assignments"][
        "reference_truth_assignment_id"
    ]
    truth_appointment_id = document["actor_register"][truth_assignment][
        "appointment_evidence_id"
    ]
    truth_decision_id = document["duty_assignments"][
        "reference_truth_decision_evidence_id"
    ]
    truth_decision = document["evidence_manifest"][truth_decision_id]
    truth_decision["candidate_question_id"] = question_id
    truth_decision["dependency_sha256"] = sorted(
        selected_hashes
        | {document["evidence_manifest"][truth_appointment_id]["sha256"]}
    )
    candidate_package_ids.update({truth_appointment_id, truth_decision_id})

    selection_package_hashes = selected_hashes | {
        document["evidence_manifest"][evidence_id]["sha256"]
        for evidence_id in candidate_package_ids
    }
    for lane_id in active_lane_ids:
        decision_id = document["lane_decisions"][lane_id]["decision_evidence_id"]
        evidence = document["evidence_manifest"][decision_id]
        evidence["candidate_question_id"] = question_id
        evidence["dependency_sha256"] = sorted(selection_package_hashes)

    bind_closed_lane_evidence(document)
    bind_overall_evidence(document, question_id)


class MotorSpeechVoiceFinalDecisionTests(unittest.TestCase):
    def assert_invalid(self, document):
        errors = validate_final_governance_decision(document)
        self.assertTrue(errors, "unsafe document unexpectedly validated")

    def test_in_progress_contract_is_not_a_final_decision(self):
        self.assert_invalid(load_governance_contract())

    def test_no_selection_fixture_is_valid_and_matches_repository_parent(self):
        document = no_selection_fixture()
        self.assertEqual(validate_final_governance_decision(document), [])
        self.assertEqual(validate_final_decision_against_repository(document), [])

    def test_selection_fixture_is_structurally_valid(self):
        self.assertEqual(validate_final_governance_decision(selection_fixture()), [])

    def test_nonselectable_voice_primitive_and_prohibited_use_cannot_validate(self):
        document = selection_fixture()
        motor = document["lane_decisions"]["motor_speech"]
        motor["decision"] = "no_selection"
        motor["candidate_question_id"] = None
        motor["truth_class"] = None
        motor["selected_construct_evidence_id"] = None
        motor["selected_task_evidence_id"] = None
        motor["selected_measure_evidence_id"] = None
        motor["required_role_decision_ids"] = []
        motor["evidence_needed_to_reopen"] = ["complete_voice_governance"]
        voice = document["lane_decisions"]["voice"]
        voice.update(
            {
                "decision": "selection",
                "candidate_question_id": "existing_item_20_voice_primitives",
                "truth_class": "clinical_voice_health",
                "selected_construct_evidence_id": "evidence:selected-construct",
                "selected_task_evidence_id": "evidence:selected-task",
                "selected_measure_evidence_id": "evidence:selected-measure",
                "evidence_needed_to_reopen": [],
            }
        )
        document["downstream"]["checkpoint_23c_eligible_lanes"] = ["voice"]
        self.assert_invalid(document)

        document = selection_fixture()
        document["intended_use"]["diagnosis_use"] = True
        self.assert_invalid(document)
        document = selection_fixture()
        document["intended_use"]["input_source"] = "existing_owner_audio"
        self.assert_invalid(document)

    def test_exactly_one_candidate_lane_may_be_selected(self):
        document = selection_fixture()
        general = document["lane_decisions"]["general_speech"]
        general.update(
            {
                "decision": "selection",
                "candidate_question_id": "controlled_connected_speech_timing",
                "truth_class": "general_speech_timing",
                "selected_construct_evidence_id": "evidence:selected-construct",
                "selected_task_evidence_id": "evidence:selected-task",
                "selected_measure_evidence_id": "evidence:selected-measure",
                "evidence_needed_to_reopen": [],
            }
        )
        document["downstream"]["checkpoint_23c_eligible_lanes"] = [
            "motor_speech",
            "general_speech",
        ]
        self.assert_invalid(document)

    def test_core_lanes_cannot_disappear_into_not_applicable(self):
        for fixture in (no_selection_fixture, selection_fixture):
            document = fixture()
            document["lane_decisions"]["voice"]["decision"] = "not_applicable"
            self.assert_invalid(document)

    def test_evidence_must_be_typed_hashed_safe_and_cross_linked(self):
        for mutation in (
            lambda d: d["owner_decision"].update(
                {"owner_decision_evidence_id": "anything"}
            ),
            lambda d: d["evidence_manifest"]["evidence:owner-decision"].update(
                {"sha256": "not-a-hash"}
            ),
            lambda d: d["lane_decisions"]["motor_speech"].update(
                {"decision_evidence_id": "evidence:owner-decision"}
            ),
        ):
            document = selection_fixture()
            mutation(document)
            self.assert_invalid(document)

    def test_evidence_dependencies_are_closed_acyclic_and_fully_bound(self):
        document = selection_fixture()
        document["evidence_manifest"]["evidence:owner-decision"][
            "dependency_sha256"
        ] = ["c" * 64]
        self.assert_invalid(document)

        document = selection_fixture()
        owner = document["evidence_manifest"]["evidence:owner-decision"]
        lane = document["evidence_manifest"][
            document["lane_decisions"]["voice"]["decision_evidence_id"]
        ]
        owner["dependency_sha256"] = [lane["sha256"]]
        lane["dependency_sha256"].append(owner["sha256"])
        self.assert_invalid(document)

        document = selection_fixture()
        overall = document["evidence_manifest"]["evidence:overall-decision"]
        pia_id = document["authority_outcomes"]["privacy_pia_evidence_id"]
        overall["dependency_sha256"].remove(
            document["evidence_manifest"][pia_id]["sha256"]
        )
        self.assert_invalid(document)

        document = selection_fixture()
        lane = document["evidence_manifest"][
            document["lane_decisions"]["motor_speech"]["decision_evidence_id"]
        ]
        pia_id = document["authority_outcomes"]["privacy_pia_evidence_id"]
        lane["dependency_sha256"].remove(
            document["evidence_manifest"][pia_id]["sha256"]
        )
        self.assert_invalid(document)

    def test_duplicate_and_parent_alias_digests_are_rejected(self):
        document = selection_fixture()
        document["evidence_manifest"]["evidence:selected-task"]["sha256"] = (
            document["evidence_manifest"]["evidence:selected-construct"]["sha256"]
        )
        self.assert_invalid(document)

        document = selection_fixture()
        document["evidence_manifest"]["evidence:selected-task"][
            "sha256"
        ] = CURRENT_CONTRACT_CANONICAL_SHA256
        self.assert_invalid(document)

        document = selection_fixture()
        document["evidence_manifest"]["evidence:selected-task"][
            "artifact_sha256"
        ] = document["evidence_manifest"]["evidence:selected-construct"][
            "artifact_sha256"
        ]
        bind_overall_evidence(
            document, "controlled_rapid_syllable_timing"
        )
        errors = validate_final_governance_decision(document)
        self.assertTrue(
            any("duplicates the issued artifact digest" in error for error in errors),
            errors,
        )

        document = selection_fixture()
        document["evidence_manifest"]["evidence:selected-task"][
            "artifact_sha256"
        ] = CURRENT_CONTRACT_CANONICAL_SHA256
        bind_overall_evidence(
            document, "controlled_rapid_syllable_timing"
        )
        self.assert_invalid(document)

    def test_final_dates_cannot_predate_the_approved_parent(self):
        document = no_selection_fixture()
        document["decision_date"] = "2000-01-01"
        for evidence in document["evidence_manifest"].values():
            evidence["issued_date"] = "1900-01-01"
        self.assert_invalid(document)

    def test_closure_authority_and_private_evidence_reporting_are_exact(self):
        document = no_selection_fixture()
        document["evidence_manifest"]["evidence:overall-decision"][
            "issuer_role_id"
        ] = "australian_medical_device_regulatory_specialist"
        self.assert_invalid(document)

        document = no_selection_fixture()
        document["data_access"]["private_governance_evidence_accessed"] = True
        self.assert_invalid(document)

        document = no_selection_fixture()
        actor = add_actor(document, "motor-blocker", ["professional"])
        record_id = add_role(
            document,
            "motor-blocker",
            "independent_adult_motor_speech_cpsp",
            actor,
            ["motor_speech"],
            outcome="signed_block",
        )
        document["lane_decisions"]["motor_speech"][
            "required_role_decision_ids"
        ] = [record_id]
        document["data_access"]["private_governance_evidence_accessed"] = True
        bind_closed_lane_evidence(document)
        bind_overall_evidence(document)
        self.assertEqual(validate_final_governance_decision(document), [])
        document["data_access"]["private_governance_evidence_accessed"] = False
        self.assert_invalid(document)

    def test_same_decision_evidence_cannot_impersonate_different_roles(self):
        document = selection_fixture()
        roles = list(document["role_decisions"].values())
        roles[1]["decision_evidence_id"] = roles[0]["decision_evidence_id"]
        self.assert_invalid(document)

    def test_evidence_scope_must_match_deliverable_and_role_scope(self):
        document = selection_fixture()
        evidence_id = document["deliverable_evidence"]["annotation_manual"][
            "evidence_id"
        ]
        document["evidence_manifest"][evidence_id]["scope"] = ["voice"]
        self.assert_invalid(document)

        document = selection_fixture()
        motor_role = next(
            record
            for record in document["role_decisions"].values()
            if record["role_id"] == "independent_adult_motor_speech_cpsp"
        )
        document["evidence_manifest"][motor_role["decision_evidence_id"]][
            "scope"
        ] = ["voice"]
        self.assert_invalid(document)

        document = selection_fixture()
        document["evidence_manifest"][motor_role["competence_evidence_id"]][
            "scope"
        ] = ["voice"]
        self.assert_invalid(document)

        document = selection_fixture()
        pia_id = document["authority_outcomes"]["privacy_pia_evidence_id"]
        document["evidence_manifest"][pia_id]["scope"] = ["voice"]
        self.assert_invalid(document)

    def test_selected_artifacts_and_authorities_belong_to_accepted_people(self):
        for mutation in (
            lambda d: d["evidence_manifest"]["evidence:selected-construct"].update(
                {"issuer_role_id": "owner"}
            ),
            lambda d: d["evidence_manifest"]["evidence:selected-task"].update(
                {"subject_assignment_id": "assignment:owner"}
            ),
            lambda d: d["evidence_manifest"]["evidence:selected-measure"].update(
                {"candidate_question_id": None}
            ),
            lambda d: d["evidence_manifest"]["evidence:selected-measure"].update(
                {"dependency_sha256": []}
            ),
            lambda d: d["evidence_manifest"][
                d["authority_outcomes"]["privacy_pia_evidence_id"]
            ].update({"subject_assignment_id": "assignment:owner"}),
        ):
            document = selection_fixture()
            mutation(document)
            self.assert_invalid(document)

    def test_separation_of_duties_is_enforced(self):
        document = selection_fixture()
        motor_actor = document["actor_register"]["assignment:motor"]
        motor_actor["classes"].append("developer")
        self.assert_invalid(document)

        document = selection_fixture()
        for actor in document["actor_register"].values():
            actor["organisation_id"] = "org:same"
        self.assert_invalid(document)

        document = selection_fixture()
        document["actor_register"]["assignment:truth"]["classes"] = ["professional"]
        self.assert_invalid(document)

        document = selection_fixture()
        document["actor_register"]["assignment:motor"]["organisation_id"] = (
            document["actor_register"]["assignment:owner"]["organisation_id"]
        )
        self.assert_invalid(document)

        document = selection_fixture()
        add_actor(document, "candidate-vendor", ["candidate_vendor", "developer"])
        bind_overall_evidence(document, "controlled_rapid_syllable_timing")
        self.assertEqual(validate_final_governance_decision(document), [])
        document["actor_register"]["assignment:candidate-vendor"][
            "organisation_id"
        ] = document["actor_register"]["assignment:measurement"][
            "organisation_id"
        ]
        self.assert_invalid(document)

    def test_owner_closure_records_require_the_owner_assignment(self):
        for evidence_id in (
            "evidence:owner-decision",
            "evidence:overall-decision",
            no_selection_fixture()["lane_decisions"]["voice"][
                "decision_evidence_id"
            ],
        ):
            document = no_selection_fixture()
            document["evidence_manifest"][evidence_id][
                "subject_assignment_id"
            ] = None
            self.assert_invalid(document)

    def test_unrelated_voice_block_does_not_block_motor_selection(self):
        document = selection_fixture()
        voice_actor = add_actor(document, "voice", ["professional"])
        record_id = add_role(
            document,
            "voice-block",
            "independent_adult_voice_cpsp",
            voice_actor,
            ["voice"],
            outcome="signed_block",
        )
        document["lane_decisions"]["voice"][
            "required_role_decision_ids"
        ] = [record_id]
        bind_closed_lane_evidence(document)
        bind_overall_evidence(
            document, "controlled_rapid_syllable_timing"
        )
        self.assertEqual(validate_final_governance_decision(document), [])

    def test_lane_closures_accept_only_lane_appropriate_blockers(self):
        document = selection_fixture()
        actor = add_actor(document, "wrong-voice-blocker", ["professional"])
        record_id = add_role(
            document,
            "wrong-voice-blocker",
            "independent_adult_motor_speech_cpsp",
            actor,
            ["voice"],
            outcome="signed_block",
        )
        document["lane_decisions"]["voice"][
            "required_role_decision_ids"
        ] = [record_id]
        bind_closed_lane_evidence(document)
        bind_overall_evidence(document, "controlled_rapid_syllable_timing")
        self.assert_invalid(document)

        document = selection_fixture()
        actor = add_actor(document, "voice-candidate-blocker", ["professional"])
        record_id = add_role(
            document,
            "voice-candidate-blocker",
            "independent_adult_voice_cpsp",
            actor,
            ["voice"],
            outcome="signed_block",
        )
        document["lane_decisions"]["voice"][
            "required_role_decision_ids"
        ] = [record_id]
        bind_closed_lane_evidence(document)
        for field in ("decision_evidence_id", "conflict_evidence_id"):
            evidence = document["evidence_manifest"][
                document["role_decisions"][record_id][field]
            ]
            evidence["candidate_question_id"] = (
                "controlled_rapid_syllable_timing"
            )
        bind_overall_evidence(document, "controlled_rapid_syllable_timing")
        self.assert_invalid(document)

        for lane_id, role_id, actor_class in (
            (
                "participant_report",
                "paid_lived_experience_governance_group",
                "lived_experience",
            ),
            (
                "clinical_laryngeal_reference",
                "independent_ent_or_laryngologist_if_required",
                "professional",
            ),
        ):
            document = no_selection_fixture()
            actor = add_actor(document, f"{lane_id}-blocker", [actor_class])
            record_id = add_role(
                document,
                f"{lane_id}-blocker",
                role_id,
                actor,
                [lane_id],
                outcome="signed_block",
            )
            lane = document["lane_decisions"][lane_id]
            lane["decision"] = "unavailable"
            lane["required_role_decision_ids"] = [record_id]
            lane["evidence_needed_to_reopen"] = ["resolve_signed_block"]
            document["data_access"]["private_governance_evidence_accessed"] = True
            bind_closed_lane_evidence(document)
            bind_overall_evidence(document)
            self.assertEqual(validate_final_governance_decision(document), [])

    def test_selection_requires_every_governed_deliverable_and_role(self):
        document = selection_fixture()
        document["deliverable_evidence"]["annotation_manual"].update(
            {"applicability": "unresolved", "evidence_id": None}
        )
        self.assert_invalid(document)

        document = selection_fixture()
        record_id = next(
            record_id
            for record_id, record in document["role_decisions"].items()
            if record["role_id"] == "independent_adult_motor_speech_cpsp"
        )
        document["role_decisions"][record_id]["outcome"] = "signed_block"
        self.assert_invalid(document)

        document = selection_fixture()
        add_participant_reference(document)
        actor = add_actor(document, "hidden-hrec-block", ["ethics"])
        record_id = add_role(
            document,
            "hidden-hrec-block",
            "human_research_ethics_committee_if_required",
            actor,
            ["motor_speech"],
            outcome="signed_block",
        )
        document["lane_decisions"]["participant_report"][
            "required_role_decision_ids"
        ] = [record_id]
        bind_overall_evidence(document, "controlled_rapid_syllable_timing")
        self.assert_invalid(document)

    def test_hrec_and_clinical_reference_dependencies_activate_roles(self):
        document = selection_fixture()
        document["authority_outcomes"]["ethics_pathway"] = "hrec"
        self.assert_invalid(document)

        document = selection_fixture()
        add_hrec_path(document)
        self.assertEqual(validate_final_governance_decision(document), [])
        document["evidence_manifest"][
            document["authority_outcomes"]["ethics_decision_evidence_id"]
        ]["subject_assignment_id"] = "assignment:institution"
        self.assert_invalid(document)

        document = selection_fixture()
        clinical = document["lane_decisions"]["clinical_laryngeal_reference"]
        clinical.update(
            {
                "decision": "required_reference",
                "truth_class": "clinical_reference",
                "selected_construct_evidence_id": "evidence:selected-construct",
                "selected_task_evidence_id": "evidence:selected-task",
                "selected_measure_evidence_id": "evidence:selected-measure",
            }
        )
        self.assert_invalid(document)

        document = selection_fixture()
        add_clinical_reference(document)
        self.assertEqual(validate_final_governance_decision(document), [])
        manual_id = document["deliverable_evidence"]["clinical_reference_manual"][
            "evidence_id"
        ]
        document["evidence_manifest"][manual_id]["subject_assignment_id"] = (
            "assignment:owner"
        )
        self.assert_invalid(document)

        document = selection_fixture()
        add_clinical_reference(document)
        manual_id = document["deliverable_evidence"]["clinical_reference_manual"][
            "evidence_id"
        ]
        manual_hash = document["evidence_manifest"][manual_id]["sha256"]
        ent_record = next(
            role
            for role in document["role_decisions"].values()
            if role["role_id"]
            == "independent_ent_or_laryngologist_if_required"
        )
        decision = document["evidence_manifest"][
            ent_record["decision_evidence_id"]
        ]
        decision["dependency_sha256"].remove(manual_hash)
        self.assert_invalid(document)

    def test_participant_reference_is_representable_and_exactly_bound(self):
        document = selection_fixture()
        add_participant_reference(document)
        self.assertEqual(validate_final_governance_decision(document), [])

        document = selection_fixture()
        add_participant_reference(document)
        evidence_id = document["lane_decisions"]["participant_report"][
            "selected_task_evidence_id"
        ]
        document["evidence_manifest"][evidence_id]["candidate_question_id"] = None
        self.assert_invalid(document)

        document = selection_fixture()
        add_participant_reference(document)
        lane_evidence_id = document["lane_decisions"]["participant_report"][
            "decision_evidence_id"
        ]
        document["evidence_manifest"][lane_evidence_id][
            "subject_assignment_id"
        ] = "assignment:owner"
        self.assert_invalid(document)

        document = selection_fixture()
        add_participant_reference(document)
        participant_lane = document["lane_decisions"]["participant_report"]
        motor_lane = document["lane_decisions"]["motor_speech"]
        participant_lane["selected_construct_evidence_id"] = motor_lane[
            "selected_construct_evidence_id"
        ]
        errors = validate_final_governance_decision(document)
        self.assertTrue(
            any("cannot reuse selected-lane" in error for error in errors)
        )

        document = selection_fixture()
        add_participant_reference(document)
        lived_record = next(
            role
            for role in document["role_decisions"].values()
            if role["role_id"] == "paid_lived_experience_governance_group"
        )
        lived_record["scope"] = ["motor_speech"]
        for field in ("decision_evidence_id", "conflict_evidence_id"):
            document["evidence_manifest"][lived_record[field]]["scope"] = [
                "motor_speech"
            ]
        self.assert_invalid(document)

        document = selection_fixture()
        add_participant_reference(document)
        protocol_id = document["deliverable_evidence"][
            "participant_report_protocol"
        ]["evidence_id"]
        protocol_hash = document["evidence_manifest"][protocol_id]["sha256"]
        lived_record = next(
            role
            for role in document["role_decisions"].values()
            if role["role_id"] == "paid_lived_experience_governance_group"
        )
        decision = document["evidence_manifest"][
            lived_record["decision_evidence_id"]
        ]
        decision["dependency_sha256"].remove(protocol_hash)
        self.assert_invalid(document)

    def test_conditional_authority_evidence_is_representable_and_bound(self):
        document = selection_fixture()
        document["authority_outcomes"]["site_governance_applicability"] = (
            "required"
        )
        site_id = add_conditional_authority_evidence(
            document,
            "site_authorisation_evidence_id",
            "evidence:site-authorisation",
            "site_authorisation",
            "responsible_research_institution",
            "assignment:institution",
        )
        self.assertEqual(validate_final_governance_decision(document), [])
        document["evidence_manifest"][site_id]["subject_assignment_id"] = (
            "assignment:owner"
        )
        self.assert_invalid(document)

        document = selection_fixture()
        manufacturer_id, sponsor_id = add_ctn_path(document)
        self.assertEqual(validate_final_governance_decision(document), [])
        document["evidence_manifest"][manufacturer_id]["scope"] = ["voice"]
        self.assert_invalid(document)

        document = selection_fixture()
        _, sponsor_id = add_ctn_path(document)
        document["evidence_manifest"][sponsor_id]["dependency_sha256"] = [
            CURRENT_CONTRACT_CANONICAL_SHA256
        ]
        self.assert_invalid(document)

    def test_evidence_node_hashes_prevent_candidate_relabelling(self):
        document = selection_fixture()
        original_artifact_hashes = {
            evidence_id: evidence["artifact_sha256"]
            for evidence_id, evidence in document["evidence_manifest"].items()
        }
        for evidence in document["evidence_manifest"].values():
            if (
                evidence["candidate_question_id"]
                == "controlled_rapid_syllable_timing"
            ):
                evidence["candidate_question_id"] = (
                    "controlled_rapid_syllable_observable_accuracy"
                )
        motor = document["lane_decisions"]["motor_speech"]
        motor["candidate_question_id"] = (
            "controlled_rapid_syllable_observable_accuracy"
        )
        motor["truth_class"] = "observable_task_accuracy"
        errors = validate_final_governance_decision(document)
        self.assertTrue(
            any("complete evidence node" in error for error in errors)
        )
        self.assertEqual(
            original_artifact_hashes,
            {
                evidence_id: evidence["artifact_sha256"]
                for evidence_id, evidence in document["evidence_manifest"].items()
            },
        )

    def test_candidate_evidence_rejects_unrelated_lane_dependencies(self):
        def measurement_role(document):
            return next(
                role
                for role in document["role_decisions"].values()
                if role["role_id"]
                == "independent_speech_measurement_scientist"
            )

        for evidence_id_getter in (
            lambda d: "evidence:selected-construct",
            lambda d: "evidence:selected-task",
            lambda d: "evidence:selected-measure",
            lambda d: measurement_role(d)["conflict_evidence_id"],
            lambda d: measurement_role(d)["decision_evidence_id"],
        ):
            document = selection_fixture()
            unrelated_hash = document["evidence_manifest"][
                document["lane_decisions"]["voice"]["decision_evidence_id"]
            ]["sha256"]
            evidence_id = evidence_id_getter(document)
            document["evidence_manifest"][evidence_id][
                "dependency_sha256"
            ].append(unrelated_hash)
            bind_overall_evidence(
                document, "controlled_rapid_syllable_timing"
            )
            errors = validate_final_governance_decision(document)
            self.assertTrue(
                any("permitted dependencies" in error for error in errors),
                errors,
            )

    def test_candidate_neutral_evidence_cannot_import_lane_dependencies(self):
        for evidence_id_getter in (
            lambda d: "evidence:owner-decision",
            lambda d: next(
                role["competence_evidence_id"]
                for role in d["role_decisions"].values()
                if role["role_id"]
                == "independent_speech_measurement_scientist"
            ),
        ):
            document = selection_fixture()
            unrelated_hash = document["evidence_manifest"][
                document["lane_decisions"]["voice"]["decision_evidence_id"]
            ]["sha256"]
            document["evidence_manifest"][evidence_id_getter(document)][
                "dependency_sha256"
            ].append(unrelated_hash)
            bind_overall_evidence(
                document, "controlled_rapid_syllable_timing"
            )
            errors = validate_final_governance_decision(document)
            self.assertTrue(
                any("candidate-neutral evidence" in error for error in errors),
                errors,
            )

    def test_candidate_specific_blockers_cannot_import_other_lanes(self):
        document = selection_fixture()
        actor = add_actor(document, "general-blocker", ["professional"])
        record_id = add_role(
            document,
            "general-blocker",
            "independent_adult_motor_speech_cpsp",
            actor,
            ["general_speech"],
            outcome="signed_block",
        )
        document["lane_decisions"]["general_speech"][
            "required_role_decision_ids"
        ] = [record_id]
        bind_closed_lane_evidence(document)
        bind_overall_evidence(
            document, "controlled_rapid_syllable_timing"
        )

        unrelated_hash = document["evidence_manifest"][
            document["lane_decisions"]["voice"]["decision_evidence_id"]
        ]["sha256"]
        role = document["role_decisions"][record_id]
        for field in ("decision_evidence_id", "conflict_evidence_id"):
            evidence = document["evidence_manifest"][role[field]]
            evidence["candidate_question_id"] = (
                "controlled_connected_speech_timing"
            )
            evidence["dependency_sha256"].append(unrelated_hash)
        seal_evidence_graph(document)
        errors = validate_final_governance_decision(document)
        self.assertTrue(
            any("must bind exactly the parent contract" in error for error in errors),
            errors,
        )

    def test_one_owner_must_issue_every_owner_closure(self):
        document = no_selection_fixture()
        owner_two = add_actor(
            document, "owner-two", ["product_owner", "developer"]
        )
        owner_three = add_actor(
            document, "owner-three", ["product_owner", "developer"]
        )
        document["evidence_manifest"]["evidence:overall-decision"][
            "subject_assignment_id"
        ] = owner_two
        for lane in document["lane_decisions"].values():
            document["evidence_manifest"][lane["decision_evidence_id"]][
                "subject_assignment_id"
            ] = owner_three
        document["data_access"]["private_governance_evidence_accessed"] = True
        bind_overall_evidence(document)
        errors = validate_final_governance_decision(document)
        self.assertTrue(
            any("accountable owner assignment" in error for error in errors),
            errors,
        )

        document = selection_fixture()
        other_owner = add_actor(
            document, "other-owner", ["product_owner", "developer"]
        )
        voice_decision_id = document["lane_decisions"]["voice"][
            "decision_evidence_id"
        ]
        document["evidence_manifest"][voice_decision_id][
            "subject_assignment_id"
        ] = other_owner
        bind_overall_evidence(
            document, "controlled_rapid_syllable_timing"
        )
        self.assert_invalid(document)

    def test_second_owner_cannot_supply_a_block_or_project_artifact(self):
        document = no_selection_fixture()
        other_owner = add_actor(
            document, "other-owner", ["product_owner", "developer"]
        )
        record_id = add_role(
            document,
            "other-owner-block",
            "product_owner",
            other_owner,
            ["motor_speech"],
            outcome="signed_block",
        )
        document["lane_decisions"]["motor_speech"][
            "required_role_decision_ids"
        ] = [record_id]
        document["data_access"]["private_governance_evidence_accessed"] = True
        bind_closed_lane_evidence(document)
        bind_overall_evidence(document)
        self.assert_invalid(document)

        document = no_selection_fixture()
        other_owner = add_actor(
            document, "other-owner", ["product_owner", "developer"]
        )
        intended_id = add_evidence(
            document,
            "evidence:other-owner-intended-use",
            "signed_intended_use",
            issuer="owner",
            subject=other_owner,
            scope=["global"],
        )
        document["intended_use"] = exact_intended_use(
            "signed_selection_use", intended_id
        )
        document["data_access"]["private_governance_evidence_accessed"] = True
        bind_overall_evidence(document)
        errors = validate_final_governance_decision(document)
        self.assertTrue(
            any("exactly one product-owner" in error for error in errors),
            errors,
        )

    def test_vendor_organisations_cannot_supply_lane_blockers(self):
        document = no_selection_fixture()
        vendor = add_actor(
            document, "candidate-vendor", ["candidate_vendor", "developer"]
        )
        blocker = add_actor(document, "vendor-blocker", ["professional"])
        document["actor_register"][blocker]["organisation_id"] = document[
            "actor_register"
        ][vendor]["organisation_id"]
        record_id = add_role(
            document,
            "vendor-blocker",
            "independent_adult_motor_speech_cpsp",
            blocker,
            ["motor_speech"],
            outcome="signed_block",
        )
        document["lane_decisions"]["motor_speech"][
            "required_role_decision_ids"
        ] = [record_id]
        document["data_access"]["private_governance_evidence_accessed"] = True
        bind_closed_lane_evidence(document)
        bind_overall_evidence(document)
        errors = validate_final_governance_decision(document)
        self.assertTrue(
            any("vendor organisation" in error for error in errors), errors
        )

    def test_independent_duties_require_distinct_organisations(self):
        document = selection_fixture()
        for field, assignment_id in document["duty_assignments"].items():
            if not field.endswith("_assignment_id"):
                continue
            document["actor_register"][assignment_id]["organisation_id"] = (
                "org:shared-independent-controller"
            )
        errors = validate_final_governance_decision(document)
        self.assertTrue(
            any("distinct organisations" in error for error in errors), errors
        )

        document = selection_fixture()
        document["duty_assignments"]["threshold_assignment_id"] = document[
            "duty_assignments"
        ]["data_custody_assignment_id"]
        self.assert_invalid(document)

    def test_reference_truth_owner_has_an_exact_signed_project_decision(self):
        for mutation in (
            lambda d, appointment, decision: appointment.update(
                {"storage_class": "public_record"}
            ),
            lambda d, appointment, decision: appointment.update(
                {"scope": ["voice"]}
            ),
            lambda d, appointment, decision: decision.update(
                {"subject_assignment_id": "assignment:owner"}
            ),
            lambda d, appointment, decision: decision.update(
                {"scope": ["voice"]}
            ),
            lambda d, appointment, decision: decision.update(
                {"candidate_question_id": None}
            ),
            lambda d, appointment, decision: decision["dependency_sha256"].remove(
                appointment["sha256"]
            ),
        ):
            document = selection_fixture()
            truth_actor = document["actor_register"]["assignment:truth"]
            appointment = document["evidence_manifest"][
                truth_actor["appointment_evidence_id"]
            ]
            decision = document["evidence_manifest"][
                document["duty_assignments"][
                    "reference_truth_decision_evidence_id"
                ]
            ]
            mutation(document, appointment, decision)
            bind_overall_evidence(
                document, "controlled_rapid_syllable_timing"
            )
            self.assert_invalid(document)

        document = selection_fixture()
        add_clinical_reference(document)
        release_organisation = document["actor_register"]["assignment:release"][
            "organisation_id"
        ]
        document["actor_register"]["assignment:clinical-lead"][
            "organisation_id"
        ] = release_organisation
        document["actor_register"]["assignment:ent"][
            "organisation_id"
        ] = release_organisation
        self.assert_invalid(document)

        for main_assignment in (
            "assignment:measurement",
            "assignment:motor",
            "assignment:truth",
            "assignment:statistics",
            "assignment:custodian",
        ):
            document = selection_fixture()
            add_clinical_reference(document)
            document["actor_register"]["assignment:clinical-lead"][
                "organisation_id"
            ] = document["actor_register"][main_assignment]["organisation_id"]
            self.assert_invalid(document)

        document = selection_fixture()
        add_participant_reference(document)
        add_clinical_reference(document)
        rebind_complete_selection_package(document)
        self.assertEqual(validate_final_governance_decision(document), [])
        document["actor_register"]["assignment:clinical-lead"][
            "organisation_id"
        ] = document["actor_register"]["assignment:lived"]["organisation_id"]
        document["actor_register"]["assignment:ent"][
            "organisation_id"
        ] = document["actor_register"]["assignment:measurement"][
            "organisation_id"
        ]
        self.assert_invalid(document)

    def test_conditional_roles_and_manuals_require_exact_dual_scope(self):
        for add_reference, lane_id, deliverable_id in (
            (
                add_participant_reference,
                "participant_report",
                "participant_report_protocol",
            ),
            (
                add_clinical_reference,
                "clinical_laryngeal_reference",
                "clinical_reference_manual",
            ),
        ):
            document = selection_fixture()
            add_reference(document)
            for record_id in document["lane_decisions"][lane_id][
                "required_role_decision_ids"
            ]:
                role = document["role_decisions"][record_id]
                role["scope"] = ["motor_speech", lane_id, "voice"]
                for field in ("decision_evidence_id", "conflict_evidence_id"):
                    document["evidence_manifest"][role[field]]["scope"] = [
                        "motor_speech",
                        lane_id,
                        "voice",
                    ]
            bind_overall_evidence(
                document, "controlled_rapid_syllable_timing"
            )
            self.assert_invalid(document)

            document = selection_fixture()
            add_reference(document)
            deliverable = document["deliverable_evidence"][deliverable_id]
            deliverable["lane_scope"] = ["motor_speech"]
            document["evidence_manifest"][deliverable["evidence_id"]][
                "scope"
            ] = ["motor_speech"]
            bind_overall_evidence(
                document, "controlled_rapid_syllable_timing"
            )
            self.assert_invalid(document)

    def test_conditional_reference_artifacts_reject_broad_scope(self):
        for add_reference, lane_id in (
            (add_participant_reference, "participant_report"),
            (add_clinical_reference, "clinical_laryngeal_reference"),
        ):
            evidence_fields = (
                "selected_construct_evidence_id",
                "selected_task_evidence_id",
                "selected_measure_evidence_id",
                "decision_evidence_id",
            )
            for evidence_field in evidence_fields:
                invalid_scopes = [["global"], [lane_id, "voice"]]
                if evidence_field == "decision_evidence_id":
                    invalid_scopes.append([lane_id])
                for scope in invalid_scopes:
                    document = selection_fixture()
                    add_reference(document)
                    evidence_id = document["lane_decisions"][lane_id][
                        evidence_field
                    ]
                    document["evidence_manifest"][evidence_id]["scope"] = scope
                    bind_overall_evidence(
                        document, "controlled_rapid_syllable_timing"
                    )
                    self.assert_invalid(document)

    def test_site_authorisation_binds_ethics_and_site_determination(self):
        for prerequisite_field in (
            "ethics_decision_evidence_id",
            "site_applicability_determination_evidence_id",
        ):
            document = selection_fixture()
            add_ctn_path(document)
            site_id = document["authority_outcomes"][
                "site_authorisation_evidence_id"
            ]
            prerequisite_id = document["authority_outcomes"][
                prerequisite_field
            ]
            prerequisite_hash = document["evidence_manifest"][
                prerequisite_id
            ]["sha256"]
            document["evidence_manifest"][site_id][
                "dependency_sha256"
            ].remove(prerequisite_hash)
            bind_overall_evidence(
                document, "controlled_rapid_syllable_timing"
            )
            self.assert_invalid(document)

    def test_no_selection_cannot_require_a_conditional_reference(self):
        for lane_id in ("participant_report", "clinical_laryngeal_reference"):
            document = no_selection_fixture()
            document["lane_decisions"][lane_id]["decision"] = "required_reference"
            errors = validate_final_governance_decision(document)
            self.assertTrue(
                any(
                    f"no selection cannot require the conditional lane {lane_id}"
                    in error
                    for error in errors
                )
            )

    def test_privacy_and_regulatory_outcome_combinations_are_consistent(self):
        document = selection_fixture()
        document["authority_outcomes"]["privacy_act_coverage"] = (
            "no_app_entity_qualified_determination"
        )
        self.assert_invalid(document)

        document = selection_fixture()
        document["authority_outcomes"]["clinical_trial_pathway_status"] = (
            "ctn_required"
        )
        errors = validate_final_governance_decision(document)
        self.assertTrue(any("requires HREC" in error for error in errors))
        self.assertTrue(
            any("requires site governance" in error for error in errors)
        )

    def test_score_threshold_data_release_and_downstream_are_always_closed(self):
        for lane_id in EXPECTED_LANE_STATUSES:
            for field, value in (("selected_score", "score"), ("selected_threshold", 0.5)):
                document = selection_fixture()
                document["lane_decisions"][lane_id][field] = value
                self.assert_invalid(document)
        for mutation in (
            lambda d: d["data_access"].update({"held_out_accessed": True}),
            lambda d: d["data_access"].update(
                {"private_governance_evidence_accessed": False}
            ),
            lambda d: d["release_boundaries"].update({"score": True}),
            lambda d: d["release_boundaries"].update({"threshold": True}),
            lambda d: d["downstream"].update({"implementation_may_begin": True}),
            lambda d: d["downstream"].update(
                {"checkpoint_23c_eligible_lanes": ["voice"]}
            ),
        ):
            document = selection_fixture()
            mutation(document)
            self.assert_invalid(document)

    def test_owner_scope_dates_and_reopening_evidence_are_not_optional(self):
        for mutation in (
            lambda d: d["owner_decision"].update({"adults_first_confirmed": False}),
            lambda d: d["owner_decision"].update({"children_excluded": False}),
            lambda d: d.update({"decision_date": "never"}),
            lambda d: d.update({"decision_date": "2099-01-01"}),
            lambda d: d["overall_decision"].update({"evidence_needed_to_reopen": []}),
        ):
            document = no_selection_fixture()
            mutation(document)
            self.assert_invalid(document)

    def test_malformed_nested_json_values_return_errors_without_crashing(self):
        mutations = (
            lambda d: d.update({"intended_use": []}),
            lambda d: d.update({"authority_outcomes": []}),
            lambda d: d.update({"data_access": []}),
            lambda d: d["authority_outcomes"].update({"ethics_pathway": []}),
            lambda d: d["lane_decisions"]["motor_speech"].update(
                {"decision": []}
            ),
            lambda d: d["overall_decision"].update({"decision": {}}),
            lambda d: next(iter(d["evidence_manifest"].values())).update(
                {"issuer_role_id": []}
            ),
            lambda d: next(iter(d["role_decisions"].values())).update(
                {"outcome": []}
            ),
            lambda d: next(iter(d["role_decisions"].values())).update(
                {"scope": [None]}
            ),
        )
        for mutation in mutations:
            document = selection_fixture()
            mutation(document)
            self.assert_invalid(document)

    def test_every_nested_shape_fails_closed_without_raising(self):
        fixtures = [no_selection_fixture(), selection_fixture()]
        participant = selection_fixture()
        add_participant_reference(participant)
        fixtures.append(participant)
        clinical = selection_fixture()
        add_clinical_reference(clinical)
        fixtures.append(clinical)

        def paths(value, prefix=()):
            if prefix:
                yield prefix, value
            if isinstance(value, dict):
                for key, child in value.items():
                    yield from paths(child, prefix + (key,))
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    yield from paths(child, prefix + (index,))

        for fixture_index, fixture in enumerate(fixtures):
            for path, original in paths(fixture):
                with self.subTest(fixture=fixture_index, path=path):
                    document = copy.deepcopy(fixture)
                    parent = document
                    for part in path[:-1]:
                        parent = parent[part]
                    parent[path[-1]] = None if isinstance(original, list) else []
                    self.assert_invalid(document)

    def test_repository_wrapper_rejects_missing_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.json"
            self.assertTrue(
                validate_final_decision_against_repository(
                    no_selection_fixture(), parent_path=missing
                )
            )


if __name__ == "__main__":
    unittest.main()
