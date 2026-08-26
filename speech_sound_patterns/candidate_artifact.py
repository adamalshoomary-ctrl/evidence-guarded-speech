"""Developer-only speech sound candidate artifact for checkpoint 22G.

The active evidence decision is deliberately negative: no candidate system,
mapping, feature rule or threshold passed the task-matched development and
threshold-tuning requirements. This module therefore does two things only:

* validates and assembles raw research evidence for known prompt-pack words;
* builds the generic repeated-relation data structure while emitting no real
  relation or repeated-relation candidate.

The module is not imported by the normal pipeline. It never calls a provider,
listener, evaluator, claim ledger, coaching, history or progress component.
"""

from __future__ import annotations

import copy
import json
import math
import os
import re
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

from .feasibility import (
    REPOSITORY_ROOT,
    canonical_json_bytes,
    canonical_json_sha256,
    file_sha256,
)
from .prompt_pack_validate import PACK_PATH, validate_pack


MODULE_ROOT = Path(__file__).parent
CONTRACT_PATH = MODULE_ROOT / "candidate-artifact-contract-v1.0.0.json"
CONTRACT_SHA256 = "20ece314254cbbe7eea8c2a175e8ca177a5d85bd8fa2150d18620f0104c26791"
ARTIFACT_FILENAME = "speech_sound_candidates.json"

ALLOWED_CANDIDATE_STATES = {
    "possible_relation_candidate",
    "asr_only_disagreement",
    "candidate_system_conflict",
    "known_reference_variant",
    "insufficient_evidence",
    "unsupported",
    "unavailable",
}
ALLOWED_RELATION_TYPES = {"substitution", "deletion", "insertion"}
ALLOWED_SPLITS = {"development", "threshold_tuning", "functional_integration"}
ALLOWED_QUALITY_STATES = {"pass", "fail", "unavailable"}
ALLOWED_SYSTEM_STATES = {
    "available",
    "unavailable",
    "unsupported",
    "provider_failure",
}
ALLOWED_PROPOSAL_STATES = {
    "proposal",
    "no_proposal",
    "unavailable",
    "unsupported",
}
HEX_64 = re.compile(r"^[0-9a-f]{64}$")
SOURCE_PROFILES = {
    "synthetic_fixture": {
        "project_split": "functional_integration",
        "manifest_state": "synthetic_fixture",
        "licence_state": "not_applicable_synthetic",
        "role": "structural_testing_only",
        "external_transfer": False,
        "selection_evidence_allowed": False,
        "real_evidence_references_required": False,
    },
    "adam_controlled_recordings": {
        "project_split": "functional_integration",
        "manifest_state": "owner_controlled_local",
        "licence_state": "owner_authorised_local_functional_integration",
        "role": "functional_integration_only",
        "external_transfer": False,
        "selection_evidence_allowed": False,
        "real_evidence_references_required": True,
    },
}
SOURCE_RECORD_FIELDS = {
    "source_id",
    "manifest_state",
    "licence_state",
    "role",
    "external_transfer",
}

RULE_STATUS = "no_rule_selected_task_matched_evidence_unavailable"
ARTIFACT_STATUS = "developer_research_only_no_relation_rule_selected"
REVIEW_STATE = "unreviewed"

class CandidateArtifactError(ValueError):
    """Raised when candidate evidence cannot be assembled safely."""


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


def _read_json(path):
    path = Path(path)
    if not path.is_file():
        raise CandidateArtifactError(f"required JSON is missing: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CandidateArtifactError(f"required JSON is unreadable: {path}") from exc


def load_candidate_contract(path=CONTRACT_PATH):
    path = Path(path)
    document = _read_json(path)
    errors = validate_candidate_contract(document, path=path)
    if errors:
        raise CandidateArtifactError("\n".join(errors))
    return document


def validate_candidate_contract(document, *, path=CONTRACT_PATH):
    """Return every structural and safety error in the frozen 22G contract."""
    errors = []
    root_fields = {
        "schema_version",
        "contract_id",
        "contract_version",
        "checkpoint",
        "status",
        "purpose",
        "frozen_inputs",
        "carried_forward",
        "evidence_adequacy_gate",
        "input_manifest_contract",
        "artifact_contract",
        "state_resolution",
        "generic_repeated_relation_policy",
        "evidence_report_policy",
        "output_and_distribution",
        "release_boundaries",
        "acceptance",
    }
    if not _required_fields(
        document, root_fields, "candidate contract", errors, exact=True
    ):
        return errors
    if document["schema_version"] != "1.0.0":
        errors.append("candidate contract schema version is unsupported")
    if document["contract_id"] != (
        "speech_sound_patterns_developer_candidate_artifact_v1"
    ):
        errors.append("candidate contract id is unsupported")
    if document["contract_version"] != "1.0.0":
        errors.append("candidate contract version is unsupported")
    if document["checkpoint"] != "22G":
        errors.append("candidate contract checkpoint must remain 22G")
    if document["status"] != "rules_frozen_before_candidate_extractor_implementation":
        errors.append("candidate rules must remain frozen before implementation")

    path = Path(path)
    if path.resolve() == CONTRACT_PATH.resolve():
        if document != _read_json(CONTRACT_PATH):
            errors.append("candidate contract differs from the frozen document")
        if not path.is_file() or file_sha256(path) != CONTRACT_SHA256:
            errors.append("candidate contract checksum changed")

    frozen = document["frozen_inputs"]
    if isinstance(frozen, dict):
        for label, record in frozen.items():
            if not isinstance(record, dict):
                errors.append(f"frozen input {label} must be an object")
                continue
            rel = record.get("path") or record.get("private_path")
            expected = record.get("sha256")
            if not isinstance(rel, str) or not isinstance(expected, str):
                errors.append(f"frozen input {label} must name a path and sha256")
                continue
            actual_path = (
                MODULE_ROOT / rel
                if "path" in record and not rel.startswith(".research_data/")
                else REPOSITORY_ROOT / rel
            )
            if not actual_path.is_file():
                errors.append(f"frozen input {label} is missing")
            elif file_sha256(actual_path) != expected:
                errors.append(f"frozen input {label} checksum changed")
        previous = frozen.get("previous_research_contract") or {}
        if previous.get("unchanged_historical_contract") is not True:
            errors.append("research contract version 1.5 must remain historical")
        selection = frozen.get("selection_record") or {}
        if (
            selection.get("decision") != "no_selection"
            or selection.get("further_threshold_search_authorised") is not False
        ):
            errors.append("the closed no-selection record cannot be reopened")
        prompt = frozen.get("prompt_pack") or {}
        if (
            prompt.get("pack_id") != "speech_sound_patterns_research_prompt_pack_v1"
            or prompt.get("pack_version") != "1.0.0"
            or prompt.get("word_count") != 20
        ):
            errors.append("candidate contract prompt pack binding changed")
    else:
        errors.append("frozen_inputs must be an object")

    carried = document["carried_forward"]
    if isinstance(carried, dict):
        barred = " ".join(carried.get("not_carried_forward") or []).lower()
        for phrase in (
            "operating point",
            "score threshold",
            "expected to produced phone mapping",
            "feature relation rule",
            "provider configuration",
            "selected candidate system",
        ):
            if phrase not in barred:
                errors.append(f"not-carried-forward record drops {phrase}")
    else:
        errors.append("carried_forward must be an object")

    gate = document["evidence_adequacy_gate"]
    if isinstance(gate, dict):
        if gate.get("runs_before_any_threshold_or_repeated_rule_search") is not True:
            errors.append("evidence adequacy must run before any rule search")
        if gate.get("failure_decision") != RULE_STATUS:
            errors.append("evidence adequacy failure decision changed")
        for field in (
            "threshold_search_after_failure",
            "held_out_access_after_failure",
            "owner_recordings_may_fill_the_evidence_gap",
            "synthetic_fixtures_may_fill_the_evidence_gap",
        ):
            if gate.get(field) is not False:
                errors.append(f"evidence adequacy {field} must remain false")
        gates = gate.get("unchanged_selection_gates") or {}
        expected_gates = {
            "minimum_precision_point_estimate": 0.75,
            "minimum_precision_wilson_95_lower": 0.5,
            "maximum_false_concerns_per_scorable_opportunity": 0.01,
            "minimum_recall": 0.2,
            "minimum_true_positives": 7,
            "development_and_tuning_both_required": True,
        }
        if gates != expected_gates:
            errors.append("the unchanged selection gates moved")
    else:
        errors.append("evidence_adequacy_gate must be an object")

    manifest = document["input_manifest_contract"]
    if isinstance(manifest, dict):
        if manifest.get("manifest_id") != "speech_sound_candidate_trials_v1":
            errors.append("input manifest id changed")
        if set(manifest.get("allowed_project_splits") or []) != ALLOWED_SPLITS:
            errors.append("input manifest split policy changed")
        if set(manifest.get("quality_statuses") or []) != ALLOWED_QUALITY_STATES:
            errors.append("input manifest quality states changed")
        for field in (
            "normal_pipeline_manifest_allowed",
            "normal_master_json_allowed",
            "held_out_split_allowed",
            "asr_may_supply_intended_word",
            "network_access_allowed",
            "provider_request_allowed",
        ):
            if manifest.get(field) is not False:
                errors.append(f"input manifest {field} must remain false")
        if manifest.get("intended_word_source") != "versioned_presented_stimulus":
            errors.append("ASR cannot replace the known presented stimulus")
        if manifest.get("approved_source_profiles") != SOURCE_PROFILES:
            errors.append("input manifest source profiles changed")
        if manifest.get("unregistered_sources_allowed") is not False:
            errors.append("unregistered candidate sources must remain forbidden")
        if manifest.get("speechocean762_trial_extraction_allowed") is not False:
            errors.append(
                "sentence corpus evidence cannot masquerade as the controlled word task"
            )
    else:
        errors.append("input_manifest_contract must be an object")

    artifact = document["artifact_contract"]
    if isinstance(artifact, dict):
        if artifact.get("filename") != ARTIFACT_FILENAME:
            errors.append("candidate artifact filename changed")
        if artifact.get("artifact_id") != "speech_sound_candidates":
            errors.append("candidate artifact id changed")
        if set(artifact.get("allowed_automatic_states") or []) != (
            ALLOWED_CANDIDATE_STATES
        ):
            errors.append("candidate artifact automatic states changed")
        if set(artifact.get("allowed_relation_types") or []) != ALLOWED_RELATION_TYPES:
            errors.append("candidate artifact relation types changed")
        for field in (
            "automatic_error_state_allowed",
            "automatic_reviewed_relation_allowed",
            "confidence_is_probability",
            "insertions_change_expected_opportunity_denominator",
        ):
            if artifact.get(field) is not False:
                errors.append(f"candidate artifact {field} must remain false")
        if artifact.get("review_state") != REVIEW_STATE:
            errors.append("candidate artifact review state must remain unreviewed")
    else:
        errors.append("artifact_contract must be an object")

    resolution = document["state_resolution"]
    if isinstance(resolution, dict):
        if resolution.get("possible_relation_candidate_emission_enabled") is not False:
            errors.append("possible relation candidate emission must remain disabled")
        if set((resolution.get("rules") or {})) != ALLOWED_CANDIDATE_STATES:
            errors.append("candidate state resolution rules are incomplete")
    else:
        errors.append("state_resolution must be an object")

    repeated = document["generic_repeated_relation_policy"]
    if isinstance(repeated, dict):
        if repeated.get("state") != "repeated_relation_candidate":
            errors.append("generic repeated relation state changed")
        if repeated.get("emission_enabled") is not False:
            errors.append("repeated relation emission must remain disabled")
        if repeated.get("minimum_rule") is not None:
            errors.append("a repeated relation minimum cannot be invented")
        if repeated.get("minimum_rule_status") != RULE_STATUS:
            errors.append("repeated relation rule status changed")
        for field in (
            "one_token_can_qualify",
            "one_word_can_qualify",
            "named_clinical_pattern_allowed",
            "threshold_search_allowed",
            "held_out_evaluation_allowed",
        ):
            if repeated.get(field) is not False:
                errors.append(f"repeated relation {field} must remain false")
        if repeated.get("support_may_only_reference_state") != (
            "possible_relation_candidate"
        ):
            errors.append("repeated relation support state changed")
    else:
        errors.append("generic_repeated_relation_policy must be an object")

    output = document["output_and_distribution"]
    if isinstance(output, dict):
        if output.get("artifact_output_root") != (
            ".research_data/speech_sound_patterns/candidates"
        ):
            errors.append("candidate artifact private output root changed")
        if output.get("manifest_input_root") != (
            ".research_data/speech_sound_patterns/candidates/manifests"
        ):
            errors.append("candidate manifest private input root changed")
        if output.get("offline_environment_variable") != "SPEECH_SOUND_OFFLINE=1":
            errors.append("candidate extractor offline requirement changed")
        for field in (
            "existing_artifact_may_be_overwritten",
            "normal_pipeline_output_directory_allowed",
            "existing_pipeline_artifacts_may_be_modified",
            "root_history_or_progress_may_be_modified",
            "derived_lexicon_material_may_be_committed",
            "raw_provider_or_restricted_corpus_evidence_may_be_committed",
        ):
            if output.get(field) is not False:
                errors.append(f"output boundary {field} must remain false")
    else:
        errors.append("output_and_distribution must be an object")

    release = document["release_boundaries"]
    if not isinstance(release, dict) or not release:
        errors.append("release boundaries must be a nonempty object")
    else:
        for field, value in release.items():
            if value is not False:
                errors.append(f"release boundary {field} must remain closed")
    return errors


def _prompt_pack(contract):
    pack = _read_json(PACK_PATH)
    errors = validate_pack(pack)
    if errors:
        raise CandidateArtifactError("prompt pack is invalid:\n" + "\n".join(errors))
    binding = contract["frozen_inputs"]["prompt_pack"]
    if file_sha256(PACK_PATH) != binding["sha256"]:
        raise CandidateArtifactError("prompt pack checksum changed")
    return pack


def _frozen_prompt_pack(contract, supplied=None):
    frozen = _prompt_pack(contract)
    if supplied is not None and supplied != frozen:
        raise CandidateArtifactError(
            "supplied prompt pack differs from the frozen prompt pack"
        )
    return frozen


def _pack_words(pack):
    return {item["word"]: item for item in pack["words"]}


def _source_record(source_id, profile):
    return {
        "source_id": source_id,
        "manifest_state": profile["manifest_state"],
        "licence_state": profile["licence_state"],
        "role": profile["role"],
        "external_transfer": profile["external_transfer"],
    }


def _validate_hash_reference(reference, label, errors, *, required):
    if reference is None and not required:
        return
    if (
        not isinstance(reference, dict)
        or set(reference) != {"path", "sha256"}
        or not isinstance(reference.get("path"), str)
        or not reference["path"]
        or not HEX_64.fullmatch(str(reference.get("sha256", "")))
    ):
        errors.append(
            f"{label} must be a checksum bound private reference"
        )


def _trial_evidence_references(trial):
    quality = trial.get("audio_quality")
    quality = quality if isinstance(quality, dict) else {}
    yield "audio quality evidence", quality.get("evidence_ref"), True
    raw = trial.get("raw_evidence")
    raw = raw if isinstance(raw, dict) else {}
    for lane in ("asr", "alignment"):
        record = raw.get(lane)
        record = record if isinstance(record, dict) else {}
        yield f"{lane} evidence", record.get("raw_output_ref"), True
    systems = raw.get("local_phone_systems")
    systems = systems if isinstance(systems, list) else []
    for system_index, system in enumerate(systems):
        if not isinstance(system, dict):
            continue
        yield (
            f"local system {system_index} evidence",
            system.get("raw_output_ref"),
            True,
        )
        opportunities = system.get("opportunities")
        opportunities = opportunities if isinstance(opportunities, list) else []
        for opportunity_index, opportunity in enumerate(opportunities):
            if not isinstance(opportunity, dict):
                continue
            yield (
                f"local system {system_index} opportunity "
                f"{opportunity_index} evidence",
                opportunity.get("raw_output_ref"),
                False,
            )
    providers = raw.get("cached_providers")
    providers = providers if isinstance(providers, list) else []
    for provider_index, provider in enumerate(providers):
        if not isinstance(provider, dict):
            continue
        yield (
            f"cached provider {provider_index} evidence",
            provider.get("raw_output_ref"),
            True,
        )
    insertions = raw.get("insertions")
    insertions = insertions if isinstance(insertions, list) else []
    for insertion_index, insertion in enumerate(insertions):
        if not isinstance(insertion, dict):
            continue
        yield (
            f"insertion {insertion_index} evidence",
            insertion.get("raw_output_ref"),
            True,
        )


def _validate_source_evidence(trial, label, source_id, errors):
    audio = trial.get("audio")
    audio = audio if isinstance(audio, dict) else {}
    audio_path = audio.get("path")
    references = list(_trial_evidence_references(trial))
    if source_id == "synthetic_fixture":
        if audio_path is not None or any(
            reference is not None for _, reference, _ in references
        ):
            errors.append(
                f"{label} synthetic fixture cannot reference real evidence"
            )
        return
    if source_id == "adam_controlled_recordings":
        if not isinstance(audio_path, str) or not audio_path:
            errors.append(f"{label} real recording needs a private audio path")
        for reference_label, reference, required in references:
            _validate_hash_reference(
                reference,
                f"{label} {reference_label}",
                errors,
                required=required,
            )


def validate_trial_manifest(document, *, contract=None, pack=None):
    """Validate one explicit, non-pipeline candidate trial manifest."""
    errors = []
    contract = contract or load_candidate_contract()
    try:
        pack = _frozen_prompt_pack(contract, pack)
    except CandidateArtifactError as exc:
        return [str(exc)]
    root_fields = {
        "schema_version",
        "manifest_id",
        "manifest_version",
        "scope",
        "project_split",
        "prompt_pack",
        "task",
        "source",
        "trials",
    }
    if not _required_fields(
        document, root_fields, "candidate trial manifest", errors, exact=True
    ):
        return errors
    if document["schema_version"] != "1.0.0":
        errors.append("candidate trial manifest schema version is unsupported")
    if document["manifest_id"] != "speech_sound_candidate_trials_v1":
        errors.append("candidate trial manifest id is unsupported")
    if document["manifest_version"] != "1.0.0":
        errors.append("candidate trial manifest version is unsupported")
    if (
        not isinstance(document["project_split"], str)
        or document["project_split"] not in ALLOWED_SPLITS
    ):
        errors.append("held-out or unknown project split is forbidden")

    scope = document["scope"]
    scope_fields = {
        "developer_only",
        "normal_pipeline",
        "network_access",
        "held_out_access",
    }
    if _required_fields(scope, scope_fields, "manifest scope", errors, exact=True):
        if scope.get("developer_only") is not True:
            errors.append("candidate manifest must remain developer only")
        for field in ("normal_pipeline", "network_access", "held_out_access"):
            if scope.get(field) is not False:
                errors.append(f"manifest scope {field} must remain false")

    prompt = document["prompt_pack"]
    expected_prompt = {
        "pack_id": pack["pack_id"],
        "pack_version": pack["pack_version"],
        "sha256": contract["frozen_inputs"]["prompt_pack"]["sha256"],
    }
    if prompt != expected_prompt:
        errors.append("candidate manifest prompt pack binding changed")

    task = document["task"]
    expected_task = {
        "task_id": "controlled_word_research_en_v1",
        "status": "developer_research_only_not_product",
        "elicitation_mode": "written_word",
        "product_task_active": False,
    }
    if task != expected_task:
        errors.append("candidate manifest task boundary changed")

    source = document["source"]
    source_id = source.get("source_id") if isinstance(source, dict) else None
    profile = (
        SOURCE_PROFILES.get(source_id)
        if isinstance(source_id, str)
        else None
    )
    if profile is None:
        errors.append("candidate manifest source is not registered")
    else:
        expected_source = _source_record(source_id, profile)
        if source != expected_source:
            errors.append("candidate manifest source profile changed")
        if document["project_split"] != profile["project_split"]:
            errors.append(
                "candidate manifest source cannot claim this project split"
            )

    trials = document["trials"]
    if not isinstance(trials, list) or not trials:
        return errors + ["candidate trial manifest must contain trials"]
    words = _pack_words(pack)
    trial_ids = set()
    recording_ids = set()
    for index, trial in enumerate(trials):
        label = f"trial {index}"
        _validate_trial(
            trial,
            label,
            document["project_split"],
            source.get("source_id") if isinstance(source, dict) else None,
            words,
            trial_ids,
            recording_ids,
            errors,
        )
    return errors


def _validate_trial(
    trial,
    label,
    project_split,
    source_id,
    words,
    trial_ids,
    recording_ids,
    errors,
):
    fields = {
        "identifiers",
        "elicitation_mode",
        "intended_word",
        "intended_word_source",
        "audio",
        "audio_quality",
        "source",
        "raw_evidence",
    }
    if not _required_fields(trial, fields, label, errors, exact=True):
        return
    identifiers = trial["identifiers"]
    id_fields = {
        "participant_id",
        "session_id",
        "attempt_id",
        "trial_id",
        "stimulus_id",
    }
    identifiers_valid = _required_fields(
        identifiers,
        id_fields,
        f"{label} identifiers",
        errors,
        exact=True,
    )
    if identifiers_valid:
        for field in id_fields:
            if not isinstance(identifiers.get(field), str) or not identifiers[field]:
                errors.append(f"{label} identifier {field} must be nonempty text")
        trial_id = identifiers.get("trial_id")
        if isinstance(trial_id, str) and trial_id:
            if trial_id in trial_ids:
                errors.append(f"{label} duplicates trial_id {trial_id}")
            trial_ids.add(trial_id)
    if trial["elicitation_mode"] != "written_word":
        errors.append(f"{label} uses an unsupported elicitation mode")
    word = trial["intended_word"]
    if not isinstance(word, str) or word not in words:
        errors.append(f"{label} intended word is not in the frozen prompt pack")
    if trial["intended_word_source"] != "versioned_presented_stimulus":
        errors.append(f"{label} lets ASR or another source invent lexical intent")
    if (
        not isinstance(identifiers, dict)
        or identifiers.get("stimulus_id") != word
    ):
        errors.append(f"{label} stimulus id must equal the intended pack word")

    audio = trial["audio"]
    audio_fields = {
        "recording_id",
        "content_sha256",
        "duration_s",
        "path",
    }
    if _required_fields(audio, audio_fields, f"{label} audio", errors, exact=True):
        recording_id = audio.get("recording_id")
        if not isinstance(recording_id, str) or not recording_id:
            errors.append(f"{label} recording id must be nonempty text")
        else:
            if recording_id in recording_ids:
                errors.append(f"{label} duplicates a recording id")
            recording_ids.add(recording_id)
        if not HEX_64.fullmatch(str(audio.get("content_sha256", ""))):
            errors.append(f"{label} audio content sha256 is invalid")
        if not isinstance(audio.get("duration_s"), (int, float)) or (
            isinstance(audio.get("duration_s"), bool)
            or not math.isfinite(audio["duration_s"])
            or audio["duration_s"] <= 0
        ):
            errors.append(f"{label} audio duration must be positive")
        path = audio.get("path")
        if path is not None and (not isinstance(path, str) or not path):
            errors.append(f"{label} audio path must be null or nonempty text")

    quality = trial["audio_quality"]
    if _required_fields(
        quality, {"status", "reasons", "evidence_ref"}, f"{label} audio quality",
        errors, exact=True
    ):
        if (
            not isinstance(quality.get("status"), str)
            or quality.get("status") not in ALLOWED_QUALITY_STATES
        ):
            errors.append(f"{label} audio quality state is unsupported")
        if not isinstance(quality.get("reasons"), list):
            errors.append(f"{label} audio quality reasons must be a list")
        if quality.get("status") != "pass" and not quality.get("reasons"):
            errors.append(f"{label} unavailable quality must carry a reason")

    source = trial["source"]
    if _required_fields(
        source, {"source_id", "project_split"}, f"{label} source", errors, exact=True
    ):
        if source.get("source_id") != source_id:
            errors.append(f"{label} source id differs from the manifest source")
        if source.get("project_split") != project_split:
            errors.append(f"{label} split differs from the manifest split")

    pack_entry = words.get(word) if isinstance(word, str) else None
    _validate_raw_evidence(
        trial["raw_evidence"],
        label,
        errors,
        opportunity_count=(
            len(pack_entry["opportunities"]) if pack_entry is not None else None
        ),
        duration_s=(
            audio.get("duration_s") if isinstance(audio, dict) else None
        ),
    )
    _validate_source_evidence(trial, label, source_id, errors)


def _validate_raw_evidence(
    raw,
    label,
    errors,
    *,
    opportunity_count=None,
    duration_s=None,
):
    fields = {
        "asr",
        "alignment",
        "local_phone_systems",
        "cached_providers",
        "insertions",
    }
    if not _required_fields(raw, fields, f"{label} raw evidence", errors, exact=True):
        return
    asr = raw["asr"]
    if _required_fields(
        asr,
        {"status", "system_id", "system_version", "word_hypothesis", "raw_output_ref"},
        f"{label} ASR evidence",
        errors,
        exact=True,
    ):
        if (
            not isinstance(asr.get("status"), str)
            or asr.get("status") not in {"available", "unavailable"}
        ):
            errors.append(f"{label} ASR status is unsupported")
        for field in ("system_id", "system_version"):
            if not isinstance(asr.get(field), str) or not asr[field]:
                errors.append(f"{label} ASR {field} must be nonempty text")
        if asr.get("status") == "available" and not isinstance(
            asr.get("word_hypothesis"), str
        ):
            errors.append(f"{label} available ASR needs a word hypothesis")
        if (
            asr.get("status") == "available"
            and isinstance(asr.get("word_hypothesis"), str)
            and not asr["word_hypothesis"].strip()
        ):
            errors.append(f"{label} available ASR word hypothesis may not be empty")

    alignment = raw["alignment"]
    if _required_fields(
        alignment,
        {
            "status",
            "system_id",
            "system_version",
            "source_interval",
            "opportunity_intervals",
            "raw_output_ref",
        },
        f"{label} alignment evidence",
        errors,
        exact=True,
    ):
        if (
            not isinstance(alignment.get("status"), str)
            or alignment.get("status") not in {"available", "unavailable"}
        ):
            errors.append(f"{label} alignment status is unsupported")
        for field in ("system_id", "system_version"):
            if not isinstance(alignment.get(field), str) or not alignment[field]:
                errors.append(f"{label} alignment {field} must be nonempty text")
        intervals = alignment.get("opportunity_intervals")
        if not isinstance(intervals, list):
            errors.append(f"{label} opportunity intervals must be a list")
        else:
            seen_intervals = set()
            for interval in intervals:
                if not isinstance(interval, dict) or set(interval) != {
                    "opportunity_index",
                    "start_s",
                    "end_s",
                }:
                    errors.append(
                        f"{label} alignment interval must name index, start and end"
                    )
                    continue
                index = interval["opportunity_index"]
                valid_index = not (
                    not isinstance(index, int)
                    or isinstance(index, bool)
                    or index < 0
                    or (
                        opportunity_count is not None
                        and index >= opportunity_count
                    )
                )
                if not valid_index:
                    errors.append(f"{label} alignment interval index is invalid")
                else:
                    if index in seen_intervals:
                        errors.append(f"{label} duplicates an alignment interval")
                    seen_intervals.add(index)
                start = interval["start_s"]
                end = interval["end_s"]
                if (
                    not isinstance(start, (int, float))
                    or isinstance(start, bool)
                    or not isinstance(end, (int, float))
                    or isinstance(end, bool)
                    or not math.isfinite(start)
                    or not math.isfinite(end)
                    or start < 0
                    or end <= start
                    or (
                        isinstance(duration_s, (int, float))
                        and end > duration_s
                    )
                ):
                    errors.append(f"{label} alignment interval bounds are invalid")

    systems = raw["local_phone_systems"]
    if not isinstance(systems, list):
        errors.append(f"{label} local phone systems must be a list")
    else:
        seen = set()
        for system_index, system in enumerate(systems):
            system_label = f"{label} local system {system_index}"
            fields = {
                "system_id",
                "status",
                "system_version",
                "mapping_version",
                "raw_output_ref",
                "opportunities",
            }
            if not _required_fields(
                system, fields, system_label, errors, exact=True
            ):
                continue
            system_id = system.get("system_id")
            if not isinstance(system_id, str) or not system_id:
                errors.append(f"{system_label} id must be nonempty text")
            else:
                if system_id in seen:
                    errors.append(f"{label} duplicates a local system")
                seen.add(system_id)
            if (
                not isinstance(system.get("system_version"), str)
                or not system["system_version"]
            ):
                errors.append(f"{system_label} version must be nonempty text")
            mapping_version = system.get("mapping_version")
            if mapping_version is not None and (
                not isinstance(mapping_version, str) or not mapping_version
            ):
                errors.append(f"{system_label} mapping version must be null or text")
            if (
                not isinstance(system.get("status"), str)
                or system.get("status") not in ALLOWED_SYSTEM_STATES
            ):
                errors.append(f"{system_label} status is unsupported")
            opportunities = system.get("opportunities")
            if not isinstance(opportunities, list):
                errors.append(f"{system_label} opportunities must be a list")
                continue
            opportunity_ids = set()
            for item in opportunities:
                _validate_raw_proposal(
                    item,
                    system_label,
                    opportunity_ids,
                    errors,
                    opportunity_count=opportunity_count,
                    system_status=system.get("status"),
                )
            if (
                system.get("status") == "available"
                and opportunity_count is not None
                and opportunity_ids != set(range(opportunity_count))
            ):
                errors.append(
                    f"{system_label} must record every prompt pack opportunity"
                )

    providers = raw["cached_providers"]
    if not isinstance(providers, list):
        errors.append(f"{label} cached providers must be a list")
    else:
        for provider in providers:
            if not isinstance(provider, dict):
                errors.append(f"{label} cached provider evidence must be an object")
                continue
            if set(provider) != {
                "system_id",
                "status",
                "request_made_in_this_run",
                "raw_output_ref",
            }:
                errors.append(f"{label} cached provider evidence changed shape")
            if not isinstance(provider.get("system_id"), str) or not provider["system_id"]:
                errors.append(f"{label} cached provider id must be nonempty text")
            if (
                not isinstance(provider.get("status"), str)
                or provider.get("status") not in ALLOWED_SYSTEM_STATES
            ):
                errors.append(f"{label} cached provider status is unsupported")
            if provider.get("request_made_in_this_run") is not False:
                errors.append(f"{label} may not make a provider request")

    insertions = raw["insertions"]
    if not isinstance(insertions, list):
        errors.append(f"{label} insertions must be a list")
    else:
        for insertion in insertions:
            if not isinstance(insertion, dict):
                errors.append(f"{label} insertion evidence must be an object")
                continue
            if set(insertion) != {
                "relation_type",
                "between_opportunities",
                "alternative_phone",
                "source_interval",
                "raw_output_ref",
            }:
                errors.append(f"{label} insertion evidence changed shape")
            if insertion.get("relation_type") != "insertion":
                errors.append(f"{label} insertion relation type changed")
            between = insertion.get("between_opportunities")
            if (
                not isinstance(between, list)
                or len(between) != 2
                or not all(
                    value is None
                    or (isinstance(value, int) and not isinstance(value, bool))
                    for value in between
                )
            ):
                errors.append(f"{label} insertion location is invalid")
            elif opportunity_count is not None and any(
                value is not None
                and (
                    value < 0
                    or value >= opportunity_count
                )
                for value in between
            ):
                errors.append(f"{label} insertion location leaves the word")
            alternative = insertion.get("alternative_phone")
            if alternative is not None and (
                not isinstance(alternative, str) or not alternative
            ):
                errors.append(f"{label} insertion alternative must be null or text")


def _validate_raw_proposal(
    item,
    label,
    seen,
    errors,
    *,
    opportunity_count=None,
    system_status=None,
):
    fields = {
        "opportunity_index",
        "status",
        "relation_type",
        "alternative_phone",
        "feature_delta",
        "score",
        "uncertainty",
        "raw_output_ref",
    }
    if not _required_fields(item, fields, f"{label} proposal", errors, exact=True):
        return
    index = item.get("opportunity_index")
    valid_index = (
        isinstance(index, int)
        and not isinstance(index, bool)
        and index >= 0
        and (
            opportunity_count is None
            or index < opportunity_count
        )
    )
    if not isinstance(index, int) or isinstance(index, bool) or index < 0:
        errors.append(f"{label} proposal opportunity index is invalid")
    elif opportunity_count is not None and index >= opportunity_count:
        errors.append(f"{label} proposal opportunity index leaves the word")
    if valid_index:
        if index in seen:
            errors.append(f"{label} duplicates opportunity {index}")
        seen.add(index)
    if (
        not isinstance(item.get("status"), str)
        or item.get("status") not in ALLOWED_PROPOSAL_STATES
    ):
        errors.append(f"{label} proposal status is unsupported")
    if item.get("status") == "proposal":
        if system_status != "available":
            errors.append(f"{label} unavailable system cannot carry a proposal")
        if (
            not isinstance(item.get("relation_type"), str)
            or item.get("relation_type") not in {"substitution", "deletion"}
        ):
            errors.append(f"{label} proposal relation type is unsupported")
        if item.get("relation_type") == "substitution" and not isinstance(
            item.get("alternative_phone"), str
        ):
            errors.append(f"{label} substitution needs an alternative phone")
        if item.get("relation_type") == "deletion" and item.get(
            "alternative_phone"
        ) is not None:
            errors.append(f"{label} deletion cannot name an alternative phone")
    elif item.get("relation_type") is not None:
        errors.append(f"{label} non-proposal cannot carry a relation type")
    feature_delta = item.get("feature_delta")
    if not isinstance(feature_delta, list):
        errors.append(f"{label} feature delta must be a list")
    else:
        feature_names = set()
        for feature_index, feature in enumerate(feature_delta):
            if (
                not isinstance(feature, dict)
                or set(feature) != {"feature", "expected", "alternative"}
                or not isinstance(feature.get("feature"), str)
                or not feature["feature"]
                or not isinstance(
                    feature.get("expected"),
                    (str, int, float, bool, type(None)),
                )
                or not isinstance(
                    feature.get("alternative"),
                    (str, int, float, bool, type(None)),
                )
                or (
                    isinstance(feature.get("expected"), float)
                    and not math.isfinite(feature["expected"])
                )
                or (
                    isinstance(feature.get("alternative"), float)
                    and not math.isfinite(feature["alternative"])
                )
            ):
                errors.append(
                    f"{label} feature delta {feature_index} is malformed"
                )
                continue
            if feature["feature"] in feature_names:
                errors.append(f"{label} feature delta names must be unique")
            feature_names.add(feature["feature"])
    score = item.get("score")
    if score is not None and (
        not isinstance(score, (int, float))
        or isinstance(score, bool)
        or not math.isfinite(score)
    ):
        errors.append(f"{label} proposal score must be numeric or null")
    if item.get("status") != "proposal":
        if item.get("alternative_phone") is not None:
            errors.append(f"{label} non-proposal cannot carry an alternative phone")
        if feature_delta not in ([], None):
            errors.append(f"{label} non-proposal cannot carry a feature delta")
        if score is not None:
            errors.append(f"{label} non-proposal cannot carry a score")
    uncertainty = item.get("uncertainty")
    if (
        not isinstance(uncertainty, dict)
        or set(uncertainty)
        != {"confidence_is_probability", "value", "basis"}
        or uncertainty.get("confidence_is_probability") is not False
        or not isinstance(uncertainty.get("basis"), str)
        or not uncertainty["basis"]
        or not isinstance(
            uncertainty.get("value"),
            (str, int, float, bool, type(None)),
        )
        or (
            isinstance(uncertainty.get("value"), float)
            and not math.isfinite(uncertainty["value"])
        )
    ):
        errors.append(f"{label} proposal uncertainty cannot claim probability")


def assert_valid_trial_manifest(document, *, contract=None, pack=None):
    errors = validate_trial_manifest(document, contract=contract, pack=pack)
    if errors:
        raise CandidateArtifactError("\n".join(errors))
    return document


def _raw_proposals(raw, opportunity_index):
    proposals = []
    for system in raw["local_phone_systems"]:
        for item in system["opportunities"]:
            if item["opportunity_index"] != opportunity_index:
                continue
            proposals.append(
                {
                    "system_id": system["system_id"],
                    "system_version": system["system_version"],
                    "mapping_version": system["mapping_version"],
                    "system_status": system["status"],
                    **copy.deepcopy(item),
                }
            )
    return proposals


def _proposal_key(proposal):
    return (
        proposal.get("relation_type"),
        proposal.get("alternative_phone"),
        tuple(
            sorted(
                (
                    item.get("feature"),
                    json.dumps(
                        item.get("expected"),
                        sort_keys=True,
                        ensure_ascii=False,
                        allow_nan=False,
                    ),
                    json.dumps(
                        item.get("alternative"),
                        sort_keys=True,
                        ensure_ascii=False,
                        allow_nan=False,
                    ),
                )
                for item in proposal.get("feature_delta") or []
            )
        ),
    )


def _state_for_opportunity(trial, pack_opportunity, proposals):
    quality = trial["audio_quality"]
    if quality["status"] != "pass":
        return "unavailable", (
            "audio_quality_failed"
            if quality["status"] == "fail"
            else "audio_quality_unavailable"
        )

    if pack_opportunity["state"] == "unscorable":
        if pack_opportunity.get("reason") == "documented_variant_disagreement":
            return "known_reference_variant", "documented_reference_variant"
        return "unsupported", pack_opportunity.get("reason") or "unsupported_context"

    local_systems = trial["raw_evidence"]["local_phone_systems"]
    available_local = [
        system for system in local_systems if system["status"] == "available"
    ]
    if not available_local:
        return "unavailable", "required_local_phone_evidence_unavailable"

    active = [item for item in proposals if item["status"] == "proposal"]
    usable = [
        item
        for item in proposals
        if item["status"] in {"proposal", "no_proposal"}
    ]
    if not usable:
        if any(item["status"] == "unsupported" for item in proposals):
            return "unsupported", "local_phone_opportunity_unsupported"
        return "unavailable", "local_phone_opportunity_unavailable"
    distinct = {_proposal_key(item) for item in active}
    if len(distinct) > 1:
        return "candidate_system_conflict", "automatic_candidate_systems_conflict"

    # No candidate state can be emitted because the frozen rule status is a
    # no-selection. A raw proposal remains visible but is not promoted.
    return "insufficient_evidence", RULE_STATUS


def _interval_for(raw_alignment, opportunity_index, duration_s):
    for item in raw_alignment.get("opportunity_intervals") or []:
        if item.get("opportunity_index") == opportunity_index:
            return {
                "start_s": item.get("start_s"),
                "end_s": item.get("end_s"),
                "kind": "candidate_alignment_interval",
                "availability": "available",
                "source": raw_alignment.get("system_id"),
            }
    return {
        "start_s": 0.0,
        "end_s": duration_s,
        "kind": "whole_trial_fallback_not_phone_boundary",
        "availability": (
            "available"
            if raw_alignment.get("status") == "available"
            else "unavailable"
        ),
        "source": raw_alignment.get("system_id"),
    }


def _downstream_exclusions(contract):
    return sorted(contract["release_boundaries"])


def _candidate_relation(expected_phone, proposals):
    active = [item for item in proposals if item["status"] == "proposal"]
    return {
        "status": (
            "raw_system_proposal_not_selected" if active else "no_relation_selected"
        ),
        "expected_phone": expected_phone,
        "relation_type": None,
        "alternative_phone": None,
        "feature_relation": None,
        "raw_proposals": active,
        "is_error": False,
        "is_reviewed_target_relation": False,
    }


def _alternative_explanations(trial, pack_opportunity, proposals):
    explanations = [
        "automatic model error",
        "recording quality or alignment uncertainty",
        "legitimate language, accent, dialect or allophonic variation",
        "natural within speaker variation",
        "prompt reading, familiarity, memory or task effect",
    ]
    if pack_opportunity.get("reason"):
        explanations.append(
            f"prompt pack refusal or variant rule: {pack_opportunity['reason']}"
        )
    if any(
        provider.get("status") == "provider_failure"
        for provider in trial["raw_evidence"]["cached_providers"]
    ):
        explanations.append("optional cached provider evidence was unavailable")
    if len({_proposal_key(item) for item in proposals if item["status"] == "proposal"}) > 1:
        explanations.append("automatic candidate systems proposed different relations")
    return explanations


def _uncertainty(state, proposals):
    return {
        "status": "not_a_probability",
        "confidence_is_probability": False,
        "value": None,
        "basis": (
            RULE_STATUS
            if state in {"insufficient_evidence", "asr_only_disagreement"}
            else "state_specific_abstention_or_conflict"
        ),
        "raw_proposal_count": sum(
            item["status"] == "proposal" for item in proposals
        ),
    }


def _build_opportunity(
    trial,
    pack_entry,
    pack_opportunity,
    contract,
    manifest_digest,
):
    index = pack_opportunity["opportunity"]
    proposals = _raw_proposals(trial["raw_evidence"], index)
    state, reason = _state_for_opportunity(trial, pack_opportunity, proposals)
    ids = trial["identifiers"]
    return {
        "opportunity_id": f"{ids['trial_id']}:opportunity:{index}",
        "trial_id": ids["trial_id"],
        "stimulus_id": ids["stimulus_id"],
        "opportunity_index": index,
        "expected_phone": pack_opportunity.get("phoneme"),
        "position": pack_opportunity.get("position"),
        "context": {
            "prevocalic": pack_opportunity.get("prevocalic"),
            "postvocalic": pack_opportunity.get("postvocalic"),
            "syllabic": pack_opportunity.get("syllabic"),
        },
        "source_interval": _interval_for(
            trial["raw_evidence"]["alignment"],
            index,
            trial["audio"]["duration_s"],
        ),
        "audio_quality": copy.deepcopy(trial["audio_quality"]),
        "reference_variants": {
            "british_form_count": pack_entry["british_forms"],
            "australian_form_count": pack_entry["australian_forms"],
            "every_documented_form_considered": True,
            "verbatim_forms_private": True,
            "pack_opportunity_state": pack_opportunity["state"],
            "pack_reason": pack_opportunity.get("reason"),
        },
        "raw_evidence": {
            "asr": copy.deepcopy(trial["raw_evidence"]["asr"]),
            "alignment": copy.deepcopy(trial["raw_evidence"]["alignment"]),
            "local_phone_systems": copy.deepcopy(
                trial["raw_evidence"]["local_phone_systems"]
            ),
            "local_phone_proposals": proposals,
            "cached_providers": copy.deepcopy(
                trial["raw_evidence"]["cached_providers"]
            ),
        },
        "candidate_state": state,
        "candidate_relation": _candidate_relation(
            pack_opportunity.get("phoneme"), proposals
        ),
        "alternative_explanations": _alternative_explanations(
            trial, pack_opportunity, proposals
        ),
        "uncertainty": _uncertainty(state, proposals),
        "abstention_reason": reason,
        "review": {
            "state": REVIEW_STATE,
            "automatic_output_is_reference_truth": False,
            "human_review_performed": False,
        },
        "provenance": {
            "candidate_contract_sha256": CONTRACT_SHA256,
            "prompt_pack_sha256": file_sha256(PACK_PATH),
            "trial_manifest_sha256": manifest_digest,
            "source_id": trial["source"]["source_id"],
            "system_versions": sorted(
                {
                    f"{system['system_id']}:{system['system_version']}"
                    for system in trial["raw_evidence"]["local_phone_systems"]
                }
            ),
        },
        "downstream_exclusions": _downstream_exclusions(contract),
    }


def _build_insertion(trial, insertion, contract, manifest_digest, index):
    unavailable = trial["audio_quality"]["status"] != "pass"
    state = "unavailable" if unavailable else "unsupported"
    reason = (
        "audio_quality_unavailable"
        if unavailable
        else "segmentation_free_gop_insertion_variant_not_implemented"
    )
    ids = trial["identifiers"]
    return {
        "insertion_id": f"{ids['trial_id']}:insertion:{index}",
        "trial_id": ids["trial_id"],
        "stimulus_id": ids["stimulus_id"],
        "between_opportunities": copy.deepcopy(
            insertion["between_opportunities"]
        ),
        "source_interval": copy.deepcopy(insertion.get("source_interval")),
        "raw_evidence": copy.deepcopy(insertion),
        "candidate_state": state,
        "candidate_relation": {
            "status": "unsupported_automatic_insertion_lane",
            "expected_phone": None,
            "relation_type": None,
            "alternative_phone": insertion.get("alternative_phone"),
            "feature_relation": None,
            "raw_proposals": [copy.deepcopy(insertion)],
            "is_error": False,
            "is_reviewed_target_relation": False,
        },
        "alternative_explanations": [
            "automatic phone recognition or alignment error",
            "speech, breath or recording noise between expected opportunities",
            "legitimate connected production detail outside this isolated word scope",
        ],
        "uncertainty": {
            "status": "not_a_probability",
            "confidence_is_probability": False,
            "value": None,
            "basis": reason,
            "raw_proposal_count": 1,
        },
        "abstention_reason": reason,
        "review": {
            "state": REVIEW_STATE,
            "automatic_output_is_reference_truth": False,
            "human_review_performed": False,
        },
        "provenance": {
            "candidate_contract_sha256": CONTRACT_SHA256,
            "prompt_pack_sha256": file_sha256(PACK_PATH),
            "trial_manifest_sha256": manifest_digest,
            "source_id": trial["source"]["source_id"],
        },
        "downstream_exclusions": _downstream_exclusions(contract),
    }


def _build_word_evidence(trial, contract, manifest_digest):
    quality = trial["audio_quality"]
    asr = trial["raw_evidence"]["asr"]
    systems = trial["raw_evidence"]["local_phone_systems"]
    active_proposals = [
        item
        for system in systems
        for item in system["opportunities"]
        if system["status"] == "available" and item["status"] == "proposal"
    ]
    if quality["status"] != "pass":
        state = "unavailable"
        reason = (
            "audio_quality_failed"
            if quality["status"] == "fail"
            else "audio_quality_unavailable"
        )
    elif not any(system["status"] == "available" for system in systems):
        state = "unavailable"
        reason = "required_local_phone_evidence_unavailable"
    elif (
        asr["status"] == "available"
        and asr["word_hypothesis"].casefold() != trial["intended_word"].casefold()
        and not active_proposals
    ):
        state = "asr_only_disagreement"
        reason = "asr_word_differs_without_phone_relation_evidence"
    else:
        state = "insufficient_evidence"
        reason = RULE_STATUS
    ids = trial["identifiers"]
    return {
        "unit_id": f"{ids['trial_id']}:word_asr",
        "trial_id": ids["trial_id"],
        "stimulus_id": ids["stimulus_id"],
        "intended_word": trial["intended_word"],
        "raw_asr": copy.deepcopy(asr),
        "candidate_state": state,
        "sound_attribution_allowed": False,
        "manual_review_trigger": state == "asr_only_disagreement",
        "alternative_explanations": [
            "automatic speech recognition error",
            "recording quality or segmentation uncertainty",
            "prompt reading, familiarity, memory or task effect",
            "a word level difference that does not identify any produced sound",
        ],
        "uncertainty": {
            "status": "not_a_probability",
            "confidence_is_probability": False,
            "value": None,
            "basis": reason,
        },
        "abstention_reason": reason,
        "review": {
            "state": REVIEW_STATE,
            "automatic_output_is_reference_truth": False,
            "human_review_performed": False,
        },
        "provenance": {
            "candidate_contract_sha256": CONTRACT_SHA256,
            "prompt_pack_sha256": file_sha256(PACK_PATH),
            "trial_manifest_sha256": manifest_digest,
            "source_id": trial["source"]["source_id"],
        },
        "downstream_exclusions": _downstream_exclusions(contract),
    }


def _relation_group_key(opportunity):
    relation = opportunity.get("candidate_relation")
    if not isinstance(relation, dict):
        return None
    relation_type = relation.get("relation_type")
    expected_phone = relation.get("expected_phone")
    if (
        not isinstance(relation_type, str)
        or relation_type not in {"substitution", "deletion"}
        or not isinstance(expected_phone, str)
        or not expected_phone
        or expected_phone != opportunity.get("expected_phone")
    ):
        return None
    alternative_phone = relation.get("alternative_phone")
    feature = relation.get("feature_relation")
    if relation_type == "deletion":
        if alternative_phone is not None or feature not in (None, []):
            return None
        canonical_feature = []
    elif not isinstance(alternative_phone, str) or not alternative_phone:
        return None
    else:
        if not isinstance(feature, list) or not feature:
            return None
        canonical_feature = []
        names = set()
        for item in feature:
            if (
                not isinstance(item, dict)
                or set(item) != {"feature", "expected", "alternative"}
                or not isinstance(item.get("feature"), str)
                or not item["feature"]
                or item["feature"] in names
            ):
                return None
            values = (item.get("expected"), item.get("alternative"))
            if any(
                not isinstance(value, (str, int, float, bool, type(None)))
                or (
                    isinstance(value, float)
                    and not math.isfinite(value)
                )
                for value in values
            ):
                return None
            names.add(item["feature"])
            canonical_feature.append(copy.deepcopy(item))
        canonical_feature.sort(
            key=lambda item: (
                item["feature"],
                json.dumps(item["expected"], sort_keys=True),
                json.dumps(item["alternative"], sort_keys=True),
            )
        )
    return (
        relation_type,
        expected_phone,
        alternative_phone,
        json.dumps(canonical_feature, sort_keys=True, ensure_ascii=False),
    )


def _repeated_token_identity(item):
    anchor = (
        item.get("audio_content_sha256")
        or item.get("recording_id")
        or item.get("trial_id")
    )
    index = item.get("opportunity_index")
    if (
        not isinstance(anchor, str)
        or not anchor
        or not isinstance(index, int)
        or isinstance(index, bool)
        or index < 0
    ):
        raise CandidateArtifactError(
            "repeated relation input needs a stable recording and opportunity index"
        )
    return anchor, index


def summarize_repeated_relations(opportunities, *, rule=None):
    """Group possible relations without inventing a minimum.

    No rule passed checkpoint 22G, so this implementation is audit-only and
    cannot emit. A later checkpoint must introduce a new checksum-bound rule
    contract and a separately reviewed implementation rather than passing an
    arbitrary dictionary into this function.
    """
    if rule is not None:
        raise CandidateArtifactError(
            "repeated relation emission requires a future frozen rule contract"
        )
    try:
        opportunities = list(opportunities)
    except TypeError as exc:
        raise CandidateArtifactError(
            "repeated relation opportunities must be iterable"
        ) from exc
    if any(not isinstance(item, dict) for item in opportunities):
        raise CandidateArtifactError(
            "repeated relation opportunities must be objects"
        )
    groups = defaultdict(list)
    for item in opportunities:
        if item.get("candidate_state") != "possible_relation_candidate":
            continue
        if (
            item.get("reference_variants", {}).get(
                "pack_opportunity_state"
            )
            != "scorable"
        ):
            continue
        key = (
            item.get("participant_id"),
            item.get("task_id"),
            item.get("pack_id"),
            item.get("elicitation_mode"),
            _relation_group_key(item),
        )
        if (
            key[-1] is None
            or any(not isinstance(value, str) or not value for value in key[:-1])
        ):
            continue
        _repeated_token_identity(item)
        groups[key].append(item)

    audited = []
    for key, support in sorted(groups.items(), key=lambda item: repr(item[0])):
        # Repeated model passes or duplicated rows for the same opportunity
        # count once. Distinct opportunities in one recording remain distinct.
        deduplicated = {}
        for item in support:
            identity = _repeated_token_identity(item)
            deduplicated.setdefault(identity, item)
        support = list(deduplicated.values())
        words = {item.get("stimulus_id") for item in support}
        contexts = {
            json.dumps(
                item.get("context"), sort_keys=True, allow_nan=False
            )
            for item in support
        }
        recordings = {item.get("recording_id") for item in support}
        audio_hashes = {item.get("audio_content_sha256") for item in support}
        positions = {item.get("position") for item in support}
        attempts = {item.get("attempt_id") for item in support}
        trials = {item.get("trial_id") for item in support}
        sessions = {item.get("session_id") for item in support}
        relevant = [
            item
            for item in opportunities
            if item.get("participant_id") == key[0]
            and item.get("task_id") == key[1]
            and item.get("pack_id") == key[2]
            and item.get("elicitation_mode") == key[3]
            and item.get("expected_phone") == key[-1][1]
        ]
        eligible_by_identity = {}
        excluded_by_identity = {}
        for item in relevant:
            identity = _repeated_token_identity(item)
            if (
                item.get("reference_variants", {}).get(
                    "pack_opportunity_state"
                )
                != "scorable"
                or item.get("candidate_state")
                in {"unsupported", "unavailable", "known_reference_variant"}
            ):
                excluded_by_identity.setdefault(identity, item)
                continue
            eligible_by_identity.setdefault(identity, item)
        eligible = list(eligible_by_identity.values())
        eligible_count = len(eligible)
        if len(support) > eligible_count:
            raise CandidateArtifactError(
                "repeated relation support exceeds its eligible denominator"
            )
        consistency = (
            len(support) / eligible_count if eligible_count else None
        )
        record = {
            "relation_key": {
                "relation_type": key[-1][0],
                "expected_phone": key[-1][1],
                "alternative_phone": key[-1][2],
                "feature_relation": json.loads(key[-1][3]),
            },
            "support_count": len(support),
            "distinct_words": len(words),
            "distinct_positions": len(positions),
            "distinct_contexts": len(contexts),
            "distinct_recordings": len(recordings),
            "distinct_audio_sha256": len(audio_hashes),
            "distinct_sessions": len(sessions),
            "distinct_attempts": len(attempts),
            "distinct_trials": len(trials),
            "support_ids": sorted(item["opportunity_id"] for item in support),
            "eligible_opportunity_count": eligible_count,
            "eligible_opportunity_ids": sorted(
                item["opportunity_id"] for item in eligible
            ),
            "consistency": {
                "numerator": len(support),
                "denominator": eligible_count,
                "value": consistency,
                "status": (
                    "available" if consistency is not None else "unavailable"
                ),
            },
            "denominator_exclusion_counts": {
                state: sum(
                    item.get("candidate_state") == state
                    for item in excluded_by_identity.values()
                )
                for state in (
                    "known_reference_variant",
                    "unavailable",
                    "unsupported",
                )
            },
            "eligible": False,
            "minimum_shape_satisfied": (
                len(support) >= 2
                and len(words) >= 2
                and len(contexts) >= 2
                and len(recordings) >= 2
            ),
            "emission_blocker": RULE_STATUS,
        }
        audited.append(record)
    return {
        "rule_status": RULE_STATUS,
        "minimum_rule": None,
        "emission_enabled": False,
        "audited_groups": audited,
        "candidates": [],
    }


def _artifact_denominators(trials):
    opportunities = [
        item for trial in trials for item in trial["opportunities"]
    ]
    state_counts = Counter(item["candidate_state"] for item in opportunities)
    return {
        "presented_word_opportunities": len(trials),
        "word_level_state_counts": {
            state: sum(
                trial["word_evidence"]["candidate_state"] == state
                for trial in trials
            )
            for state in sorted(ALLOWED_CANDIDATE_STATES)
        },
        "expected_sound_opportunities": len(opportunities),
        "scorable_sound_opportunities": sum(
            item["reference_variants"]["pack_opportunity_state"] == "scorable"
            for item in opportunities
        ),
        "unscorable_sound_opportunities": sum(
            item["reference_variants"]["pack_opportunity_state"] == "unscorable"
            for item in opportunities
        ),
        "automatic_state_counts": {
            state: state_counts.get(state, 0)
            for state in sorted(ALLOWED_CANDIDATE_STATES)
        },
        "insertion_observations": sum(
            len(trial["insertions"]) for trial in trials
        ),
        "insertions_in_expected_sound_denominator": 0,
    }


def build_artifact(manifest, *, contract=None, pack=None):
    """Build canonical developer evidence from a validated explicit manifest."""
    contract = contract or load_candidate_contract()
    pack = _frozen_prompt_pack(contract, pack)
    pack_errors = validate_pack(pack)
    if pack_errors:
        raise CandidateArtifactError(
            "prompt pack is invalid:\n" + "\n".join(pack_errors)
        )
    assert_valid_trial_manifest(manifest, contract=contract, pack=pack)
    manifest_digest = canonical_json_sha256(manifest)
    words = _pack_words(pack)
    built_trials = []
    flat_for_repeated = []
    for trial in manifest["trials"]:
        ids = trial["identifiers"]
        pack_entry = words[trial["intended_word"]]
        opportunities = [
            _build_opportunity(
                trial, pack_entry, item, contract, manifest_digest
            )
            for item in pack_entry["opportunities"]
        ]
        insertions = [
            _build_insertion(
                trial, item, contract, manifest_digest, index
            )
            for index, item in enumerate(trial["raw_evidence"]["insertions"])
        ]
        built = {
            "identifiers": copy.deepcopy(ids),
            "elicitation_mode": trial["elicitation_mode"],
            "intended_word": trial["intended_word"],
            "intended_word_source": trial["intended_word_source"],
            "audio": copy.deepcopy(trial["audio"]),
            "audio_quality": copy.deepcopy(trial["audio_quality"]),
            "source": copy.deepcopy(trial["source"]),
            "raw_evidence": copy.deepcopy(trial["raw_evidence"]),
            "word_evidence": _build_word_evidence(
                trial, contract, manifest_digest
            ),
            "opportunities": opportunities,
            "insertions": insertions,
        }
        built_trials.append(built)
        for opportunity in opportunities:
            flat_for_repeated.append(
                {
                    **copy.deepcopy(opportunity),
                    "participant_id": ids["participant_id"],
                    "session_id": ids["session_id"],
                    "attempt_id": ids["attempt_id"],
                    "recording_id": trial["audio"]["recording_id"],
                    "audio_content_sha256": trial["audio"]["content_sha256"],
                    "task_id": manifest["task"]["task_id"],
                    "pack_id": manifest["prompt_pack"]["pack_id"],
                    "elicitation_mode": trial["elicitation_mode"],
                }
            )
    repeated = summarize_repeated_relations(flat_for_repeated, rule=None)
    artifact = {
        "schema_version": "1.0.0",
        "artifact_id": "speech_sound_candidates",
        "artifact_version": "1.0.0",
        "status": ARTIFACT_STATUS,
        "contract": {
            "path": CONTRACT_PATH.name,
            "sha256": CONTRACT_SHA256,
            "version": contract["contract_version"],
        },
        "input_manifest": {
            "manifest_id": manifest["manifest_id"],
            "manifest_version": manifest["manifest_version"],
            "sha256": manifest_digest,
            "project_split": manifest["project_split"],
        },
        "prompt_pack": copy.deepcopy(manifest["prompt_pack"]),
        "task": copy.deepcopy(manifest["task"]),
        "source": copy.deepcopy(manifest["source"]),
        "candidate_rule": {
            "status": RULE_STATUS,
            "selected_system": None,
            "selected_threshold": None,
            "selected_mapping": None,
            "selected_feature_rule": None,
            "selected_provider_configuration": None,
            "possible_relation_candidate_emission_enabled": False,
        },
        "trials": built_trials,
        "repeated_relation_summary": repeated,
        "denominators": _artifact_denominators(built_trials),
        "limitations": [
            "No candidate system, mapping, feature rule or threshold was selected.",
            "The current task matched development and tuning evidence cannot support a repeated relation rule.",
            "Raw automatic proposals are model evidence, not produced phone truth or reviewed target relations.",
            "The prompt pack is unreviewed, inactive and is not the product pronunciation task.",
            "This private developer artifact supports structural engineering only and cannot establish accuracy, fairness, scientific validity or product readiness.",
        ],
        "release_boundaries": copy.deepcopy(contract["release_boundaries"]),
    }
    errors = validate_candidate_artifact(artifact, contract=contract, pack=pack)
    if errors:
        raise CandidateArtifactError("\n".join(errors))
    return artifact


def validate_candidate_artifact(document, *, contract=None, pack=None):
    """Validate an artifact and turn every malformed JSON shape into errors."""
    try:
        return _validate_candidate_artifact(document, contract=contract, pack=pack)
    except (
        AttributeError,
        IndexError,
        KeyError,
        OverflowError,
        TypeError,
        ValueError,
    ) as exc:
        return [f"candidate artifact is structurally invalid: {exc}"]


def _validate_candidate_artifact(document, *, contract=None, pack=None):
    """Validate and recompute every safety-sensitive artifact decision."""
    errors = []
    contract = contract or load_candidate_contract()
    try:
        pack = _frozen_prompt_pack(contract, pack)
    except CandidateArtifactError as exc:
        return [str(exc)]
    pack_errors = validate_pack(pack)
    if pack_errors:
        return ["prompt pack is invalid:\n" + "\n".join(pack_errors)]
    required = set(contract["artifact_contract"]["root_required_fields"])
    if not _required_fields(
        document, required, "candidate artifact", errors, exact=True
    ):
        return errors
    if document["schema_version"] != "1.0.0":
        errors.append("candidate artifact schema version is unsupported")
    if document["artifact_id"] != "speech_sound_candidates":
        errors.append("candidate artifact id is unsupported")
    if document["artifact_version"] != "1.0.0":
        errors.append("candidate artifact version is unsupported")
    if document["status"] != ARTIFACT_STATUS:
        errors.append("candidate artifact status changed")
    if document["contract"] != {
        "path": CONTRACT_PATH.name,
        "sha256": CONTRACT_SHA256,
        "version": "1.0.0",
    }:
        errors.append("candidate artifact contract binding changed")
    input_manifest = document["input_manifest"]
    expected_manifest_fields = {
        "manifest_id",
        "manifest_version",
        "sha256",
        "project_split",
    }
    if not _required_fields(
        input_manifest,
        expected_manifest_fields,
        "candidate artifact input manifest",
        errors,
        exact=True,
    ):
        return errors
    if input_manifest.get("manifest_id") != "speech_sound_candidate_trials_v1":
        errors.append("candidate artifact input manifest id changed")
    if input_manifest.get("manifest_version") != "1.0.0":
        errors.append("candidate artifact input manifest version changed")
    if not HEX_64.fullmatch(str(input_manifest.get("sha256", ""))):
        errors.append("candidate artifact input manifest checksum is invalid")
    if (
        not isinstance(input_manifest.get("project_split"), str)
        or input_manifest.get("project_split") not in ALLOWED_SPLITS
    ):
        errors.append("candidate artifact input manifest split is forbidden")
    if document["prompt_pack"] != {
        "pack_id": pack["pack_id"],
        "pack_version": pack["pack_version"],
        "sha256": file_sha256(PACK_PATH),
    }:
        errors.append("candidate artifact prompt pack binding changed")
    expected_task = {
        "task_id": "controlled_word_research_en_v1",
        "status": "developer_research_only_not_product",
        "elicitation_mode": "written_word",
        "product_task_active": False,
    }
    if document["task"] != expected_task:
        errors.append("candidate artifact task boundary changed")
    source = document["source"]
    source_id = source.get("source_id") if isinstance(source, dict) else None
    profile = (
        SOURCE_PROFILES.get(source_id)
        if isinstance(source_id, str)
        else None
    )
    if profile is None:
        errors.append("candidate artifact source is not registered")
        return errors
    if source != _source_record(source_id, profile):
        errors.append("candidate artifact source profile changed")
    if input_manifest.get("project_split") != profile["project_split"]:
        errors.append("candidate artifact source split changed")

    rule = document["candidate_rule"]
    if not isinstance(rule, dict):
        errors.append("candidate rule must be an object")
    else:
        if rule.get("status") != RULE_STATUS:
            errors.append("candidate rule must record no selection")
        for field in (
            "selected_system",
            "selected_threshold",
            "selected_mapping",
            "selected_feature_rule",
            "selected_provider_configuration",
        ):
            if rule.get(field) is not None:
                errors.append(f"candidate rule {field} must remain null")
        if rule.get("possible_relation_candidate_emission_enabled") is not False:
            errors.append("possible relation candidate emission must remain disabled")

    pack_words = _pack_words(pack)
    trials = document["trials"]
    if not isinstance(trials, list) or not trials:
        return errors + ["candidate artifact must contain trials"]
    trial_ids = set()
    all_opportunity_ids = set()
    for trial_index, trial in enumerate(trials):
        label = f"artifact trial {trial_index}"
        if not isinstance(trial, dict):
            errors.append(f"{label} must be an object")
            continue
        trial_fields = set(contract["artifact_contract"]["trial_required_fields"])
        if not _required_fields(
            trial, trial_fields, label, errors, exact=True
        ):
            continue
        ids = trial.get("identifiers") or {}
        id_fields = {
            "participant_id",
            "session_id",
            "attempt_id",
            "trial_id",
            "stimulus_id",
        }
        if not _required_fields(
            ids, id_fields, f"{label} identifiers", errors, exact=True
        ):
            continue
        if any(not isinstance(ids[field], str) or not ids[field] for field in id_fields):
            errors.append(f"{label} identifiers must be nonempty text")
            continue
        trial_id = ids.get("trial_id")
        if trial_id in trial_ids:
            errors.append(f"{label} duplicates a trial id")
        trial_ids.add(trial_id)
        if trial.get("elicitation_mode") != "written_word":
            errors.append(f"{label} changes the elicitation mode")
        if trial.get("intended_word_source") != "versioned_presented_stimulus":
            errors.append(f"{label} changes the intended word authority")
        if trial.get("source") != {
            "source_id": document["source"].get("source_id"),
            "project_split": document["input_manifest"].get("project_split"),
        }:
            errors.append(f"{label} changes source or split provenance")
        word = trial.get("intended_word")
        pack_entry = (
            pack_words.get(word) if isinstance(word, str) else None
        )
        if pack_entry is None:
            errors.append(f"{label} uses a word outside the prompt pack")
            continue
        if ids.get("stimulus_id") != word:
            errors.append(f"{label} stimulus differs from the intended pack word")
        audio = trial.get("audio")
        if not isinstance(audio, dict) or set(audio) != {
            "recording_id",
            "content_sha256",
            "duration_s",
            "path",
        }:
            errors.append(f"{label} audio record changed shape")
            continue
        if not HEX_64.fullmatch(str(audio.get("content_sha256", ""))):
            errors.append(f"{label} audio checksum is invalid")
        if (
            not isinstance(audio.get("recording_id"), str)
            or not audio["recording_id"]
        ):
            errors.append(f"{label} recording id is invalid")
        if (
            not isinstance(audio.get("duration_s"), (int, float))
            or isinstance(audio.get("duration_s"), bool)
            or not math.isfinite(audio["duration_s"])
            or audio["duration_s"] <= 0
        ):
            errors.append(f"{label} audio duration is invalid")
        quality = trial.get("audio_quality")
        if not isinstance(quality, dict) or set(quality) != {
            "status",
            "reasons",
            "evidence_ref",
        }:
            errors.append(f"{label} audio quality record changed shape")
            continue
        if (
            not isinstance(quality.get("status"), str)
            or quality.get("status") not in ALLOWED_QUALITY_STATES
        ):
            errors.append(f"{label} audio quality state is unsupported")
        raw_error_start = len(errors)
        _validate_raw_evidence(
            trial.get("raw_evidence"),
            label,
            errors,
            opportunity_count=len(pack_entry["opportunities"]),
            duration_s=audio.get("duration_s"),
        )
        _validate_source_evidence(
            trial,
            label,
            document["source"]["source_id"],
            errors,
        )
        if (
            not isinstance(trial.get("raw_evidence"), dict)
            or len(errors) > raw_error_start
        ):
            continue
        _validate_built_word_evidence(
            trial.get("word_evidence"),
            trial,
            contract,
            label,
            document["input_manifest"]["sha256"],
            document["source"]["source_id"],
            errors,
        )
        opportunities = trial.get("opportunities")
        if not isinstance(opportunities, list):
            errors.append(f"{label} opportunities must be a list")
            continue
        if len(opportunities) != len(pack_entry["opportunities"]):
            errors.append(f"{label} does not preserve every pack opportunity")
            continue
        for expected, item in zip(pack_entry["opportunities"], opportunities):
            _validate_built_opportunity(
                item,
                expected,
                pack_entry,
                trial,
                contract,
                label,
                all_opportunity_ids,
                document["input_manifest"]["sha256"],
                document["source"]["source_id"],
                errors,
            )
        insertions = trial.get("insertions")
        raw_insertions = (trial.get("raw_evidence") or {}).get("insertions")
        if not isinstance(insertions, list):
            errors.append(f"{label} insertions must be a list")
        elif not isinstance(raw_insertions, list) or len(insertions) != len(
            raw_insertions
        ):
            errors.append(f"{label} does not preserve every raw insertion")
        else:
            for insertion, raw_insertion in zip(insertions, raw_insertions):
                _validate_built_insertion(
                    insertion,
                    raw_insertion,
                    trial,
                    contract,
                    label,
                    document["input_manifest"]["sha256"],
                    document["source"]["source_id"],
                    errors,
                )

    denominators = document["denominators"]
    expected_counts = _artifact_denominators(trials)
    if denominators != expected_counts:
        errors.append("candidate artifact denominators do not recompute")
    if denominators.get("insertions_in_expected_sound_denominator") != 0:
        errors.append("insertions cannot alter the expected sound denominator")

    repeated = document["repeated_relation_summary"]
    if not isinstance(repeated, dict):
        errors.append("repeated relation summary must be an object")
    else:
        if repeated.get("rule_status") != RULE_STATUS:
            errors.append("repeated relation summary rule status changed")
        if repeated.get("minimum_rule") is not None:
            errors.append("repeated relation minimum must remain null")
        if repeated.get("emission_enabled") is not False:
            errors.append("repeated relation emission must remain disabled")
        if repeated.get("candidates") != []:
            errors.append("no repeated relation candidate may be emitted")
        if repeated.get("audited_groups") != []:
            errors.append(
                "no possible relation candidates exist to support an audited group"
            )

    release = document["release_boundaries"]
    if release != contract["release_boundaries"]:
        errors.append("candidate artifact release boundaries changed")
    elif any(release.values()):
        errors.append("candidate artifact opens a release boundary")

    return errors


def _validate_built_opportunity(
    item,
    pack_item,
    pack_entry,
    trial,
    contract,
    label,
    opportunity_ids,
    manifest_sha256,
    source_id,
    errors,
):
    required = set(contract["artifact_contract"]["opportunity_required_fields"])
    if not _required_fields(
        item, required, f"{label} opportunity", errors, exact=True
    ):
        return
    opportunity_id = item.get("opportunity_id")
    if opportunity_id in opportunity_ids:
        errors.append(f"{label} duplicates an opportunity id")
    opportunity_ids.add(opportunity_id)
    if item.get("opportunity_index") != pack_item["opportunity"]:
        errors.append(f"{label} changes a prompt pack opportunity index")
    if item.get("expected_phone") != pack_item.get("phoneme"):
        errors.append(f"{label} changes the expected broad phone")
    if item.get("position") != pack_item.get("position"):
        errors.append(f"{label} changes the opportunity position")
    expected_context = {
        "prevocalic": pack_item.get("prevocalic"),
        "postvocalic": pack_item.get("postvocalic"),
        "syllabic": pack_item.get("syllabic"),
    }
    if item.get("context") != expected_context:
        errors.append(f"{label} changes the opportunity context")
    if item.get("trial_id") != trial["identifiers"]["trial_id"]:
        errors.append(f"{label} opportunity changes its trial id")
    if item.get("stimulus_id") != trial["identifiers"]["stimulus_id"]:
        errors.append(f"{label} opportunity changes its stimulus id")
    if item.get("audio_quality") != trial["audio_quality"]:
        errors.append(f"{label} opportunity changes its audio quality record")
    expected_variants = {
        "british_form_count": pack_entry["british_forms"],
        "australian_form_count": pack_entry["australian_forms"],
        "every_documented_form_considered": True,
        "verbatim_forms_private": True,
        "pack_opportunity_state": pack_item["state"],
        "pack_reason": pack_item.get("reason"),
    }
    if item.get("reference_variants") != expected_variants:
        errors.append(f"{label} opportunity changes its reference variant record")
    state = item.get("candidate_state")
    if (
        not isinstance(state, str)
        or state not in ALLOWED_CANDIDATE_STATES
    ):
        errors.append(f"{label} has an unsupported candidate state")
    if state == "possible_relation_candidate":
        errors.append(f"{label} emits a possible relation without a selected rule")
    raw_evidence = item.get("raw_evidence") or {}
    raw_fields = {
        "asr",
        "alignment",
        "local_phone_systems",
        "local_phone_proposals",
        "cached_providers",
    }
    if not _required_fields(
        raw_evidence,
        raw_fields,
        f"{label} opportunity raw evidence",
        errors,
        exact=True,
    ):
        return
    proposals = raw_evidence.get("local_phone_proposals") or []
    local_systems = raw_evidence.get("local_phone_systems")
    if not isinstance(local_systems, list):
        errors.append(f"{label} opportunity local systems must be a list")
        return
    expected_proposals = _raw_proposals(
        {"local_phone_systems": local_systems},
        pack_item["opportunity"],
    )
    if proposals != expected_proposals:
        errors.append(f"{label} opportunity proposals do not match raw systems")
    trial_raw = trial.get("raw_evidence") or {}
    for field in (
        "asr",
        "alignment",
        "local_phone_systems",
        "cached_providers",
    ):
        if raw_evidence.get(field) != trial_raw.get(field):
            errors.append(
                f"{label} opportunity {field} differs from trial raw evidence"
            )
    expected_state, expected_reason = _state_for_opportunity(
        {
            "audio_quality": trial["audio_quality"],
            "raw_evidence": {
                "local_phone_systems": local_systems,
                "asr": raw_evidence.get("asr"),
            },
            "intended_word": trial["intended_word"],
        },
        pack_item,
        proposals,
    )
    if state != expected_state or item.get("abstention_reason") != expected_reason:
        errors.append(f"{label} candidate state does not follow frozen precedence")
    relation = item.get("candidate_relation") or {}
    if relation != _candidate_relation(item.get("expected_phone"), proposals):
        errors.append(f"{label} candidate relation does not match raw proposals")
    if relation.get("relation_type") is not None:
        errors.append(f"{label} selects a relation type without a selected rule")
    if relation.get("is_error") is not False:
        errors.append(f"{label} turns a candidate into an error")
    if relation.get("is_reviewed_target_relation") is not False:
        errors.append(f"{label} turns automation into reviewed truth")
    if not item.get("alternative_explanations"):
        errors.append(f"{label} drops alternative explanations")
    if item.get("alternative_explanations") != _alternative_explanations(
        {
            "audio_quality": trial["audio_quality"],
            "raw_evidence": {
                "cached_providers": raw_evidence["cached_providers"],
            },
        },
        pack_item,
        proposals,
    ):
        errors.append(f"{label} changes the recorded alternative explanations")
    uncertainty = item.get("uncertainty") or {}
    if uncertainty != _uncertainty(state, proposals):
        errors.append(f"{label} opportunity uncertainty does not recompute")
    if uncertainty.get("confidence_is_probability") is not False:
        errors.append(f"{label} treats confidence as a probability")
    review = item.get("review") or {}
    if review.get("state") != REVIEW_STATE:
        errors.append(f"{label} review state changed")
    if review.get("automatic_output_is_reference_truth") is not False:
        errors.append(f"{label} treats automation as reference truth")
    if review != {
        "state": REVIEW_STATE,
        "automatic_output_is_reference_truth": False,
        "human_review_performed": False,
    }:
        errors.append(f"{label} opportunity review record changed")
    provenance = item.get("provenance") or {}
    if provenance.get("candidate_contract_sha256") != CONTRACT_SHA256:
        errors.append(f"{label} opportunity contract provenance changed")
    if provenance.get("prompt_pack_sha256") != file_sha256(PACK_PATH):
        errors.append(f"{label} opportunity prompt pack provenance changed")
    if provenance.get("trial_manifest_sha256") != manifest_sha256:
        errors.append(f"{label} opportunity manifest provenance changed")
    if provenance.get("source_id") != source_id:
        errors.append(f"{label} opportunity source provenance changed")
    if set(item.get("downstream_exclusions") or []) != set(
        contract["release_boundaries"]
    ):
        errors.append(f"{label} downstream exclusions are incomplete")


def _validate_built_word_evidence(
    item,
    trial,
    contract,
    label,
    manifest_sha256,
    source_id,
    errors,
):
    required = set(contract["artifact_contract"]["word_evidence_required_fields"])
    if not _required_fields(
        item, required, f"{label} word evidence", errors, exact=True
    ):
        return
    expected = _build_word_evidence(
        {
            "identifiers": trial["identifiers"],
            "intended_word": trial["intended_word"],
            "audio_quality": trial["audio_quality"],
            "source": trial["source"],
            "raw_evidence": {
                "asr": item["raw_asr"],
                "local_phone_systems": trial["raw_evidence"]["local_phone_systems"],
            },
        },
        contract,
        manifest_sha256,
    )
    if item != expected:
        errors.append(f"{label} word evidence does not recompute from raw evidence")
    if item.get("sound_attribution_allowed") is not False:
        errors.append(f"{label} word ASR evidence cannot identify a sound")
    if item.get("provenance", {}).get("source_id") != source_id:
        errors.append(f"{label} word evidence source provenance changed")


def _validate_built_insertion(
    item,
    raw_insertion,
    trial,
    contract,
    label,
    manifest_sha256,
    source_id,
    errors,
):
    required = set(contract["artifact_contract"]["insertion_required_fields"])
    if not _required_fields(
        item, required, f"{label} insertion", errors, exact=True
    ):
        return
    unavailable = trial["audio_quality"]["status"] != "pass"
    expected_state = "unavailable" if unavailable else "unsupported"
    expected_reason = (
        "audio_quality_unavailable"
        if unavailable
        else "segmentation_free_gop_insertion_variant_not_implemented"
    )
    if item.get("trial_id") != trial["identifiers"]["trial_id"]:
        errors.append(f"{label} insertion changes its trial id")
    if item.get("stimulus_id") != trial["identifiers"]["stimulus_id"]:
        errors.append(f"{label} insertion changes its stimulus id")
    if item.get("candidate_state") != expected_state:
        errors.append(f"{label} insertion state does not follow the frozen rule")
    if item.get("abstention_reason") != expected_reason:
        errors.append(f"{label} insertion abstention reason changed")
    raw = item.get("raw_evidence") or {}
    if raw != raw_insertion:
        errors.append(f"{label} insertion changes its raw evidence")
    if raw.get("relation_type") != "insertion":
        errors.append(f"{label} insertion raw relation type changed")
    relation = item.get("candidate_relation") or {}
    if relation.get("relation_type") is not None:
        errors.append(f"{label} selects an insertion relation")
    if relation.get("is_error") is not False:
        errors.append(f"{label} turns an insertion into an error")
    if relation.get("is_reviewed_target_relation") is not False:
        errors.append(f"{label} turns insertion automation into reviewed truth")
    uncertainty = item.get("uncertainty") or {}
    if uncertainty.get("confidence_is_probability") is not False:
        errors.append(f"{label} treats insertion confidence as probability")
    if item.get("review") != {
        "state": REVIEW_STATE,
        "automatic_output_is_reference_truth": False,
        "human_review_performed": False,
    }:
        errors.append(f"{label} insertion review record changed")
    provenance = item.get("provenance") or {}
    if provenance != {
        "candidate_contract_sha256": CONTRACT_SHA256,
        "prompt_pack_sha256": file_sha256(PACK_PATH),
        "trial_manifest_sha256": manifest_sha256,
        "source_id": source_id,
    }:
        errors.append(f"{label} insertion provenance changed")
    if set(item.get("downstream_exclusions") or []) != set(
        contract["release_boundaries"]
    ):
        errors.append(f"{label} insertion downstream exclusions are incomplete")


def write_artifact(artifact, output_path):
    """Write one new private artifact without overwriting existing evidence."""
    output_path = Path(output_path)
    if output_path.exists():
        raise CandidateArtifactError("candidate artifact already exists")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.",
        dir=output_path.parent,
    )
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(canonical_json_bytes(artifact))
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary_name, output_path)
        except FileExistsError as exc:
            raise CandidateArtifactError("candidate artifact already exists") from exc
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
    return output_path
