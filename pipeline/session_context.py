"""Validate stable account, session, task, context, and consent records."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACT_PATH = REPO_ROOT / "data_model" / "contract-v1.1.0.json"
# 1.1.0 renames the consent purpose "coaching_processing" to
# "speech_measurement_processing" and the capture quality policy value
# "coaching" to "lenient". Neither word described anything this project does:
# there is no coaching audience, and the renamed policy is the lenient one that
# warns where baseline fails. Contexts written under 1.0.0 do not validate
# against this version and are not rewritten.
SESSION_CONTEXT_SCHEMA_VERSION = "1.1.0"
DATA_MODEL_SCHEMA_VERSION = "1.1.0"
SUPERSEDED_CONSENT_PURPOSES = {
    "coaching_processing": "speech_measurement_processing",
}
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
LANGUAGE_TAG = re.compile(r"^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
SPEAKER_LABEL = re.compile(r"^SPEAKER_\d{2}$")
SAFE_REFERENCE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._]{2,127}$")

ID_PREFIXES = {
    "account_id": "acct_",
    "session_id": "sess_",
    "context_id": "ctx_",
    "attempt_id": "attempt_",
    "recording_id": "recording_",
    "participant_id": "participant_",
    "consent_event_id": "consent_",
    "exercise_id": "exercise_",
}
CONTEXT_CATEGORIES = {
    "interview",
    "spoken_exam",
    "presentation",
    "demonstration",
    "important_conversation",
    "social_practice",
    "everyday_confidence",
    "conversation",
    "custom",
}
ATTEMPT_ROLES = {
    "first",
    "matched_repeat",
    "post_exercise_repeat",
    "retention",
    "transfer",
}
PROGRESS_INTENTS = {
    "baseline_observation",
    "change_check",
    "practice",
    "retention",
    "transfer",
}
CONSENT_PURPOSES = {
    "speech_measurement_processing",
    "raw_audio_retention",
    "human_review",
    "research_collection",
    "model_improvement",
    "fairness_metadata",
}
OPTIONAL_CONSENT_PURPOSES = CONSENT_PURPOSES - {"speech_measurement_processing"}
CONSENT_DECISIONS = {"granted", "declined", "withdrawn"}


class DataModelValidationError(ValueError):
    """Raised when a data contract or runtime context is unsafe."""


def load_data_model_contract(path=CONTRACT_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_session_context(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _require_fields(value, required, location, errors):
    if not isinstance(value, dict):
        errors.append(f"{location} must be an object")
        return False
    missing = sorted(required - set(value))
    if missing:
        errors.append(f"{location} missing fields: {', '.join(missing)}")
        return False
    return True


def _is_timestamp(value):
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _check_timestamp(value, location, errors):
    if not _is_timestamp(value):
        errors.append(f"{location} must be an ISO 8601 timestamp with timezone")


def _check_id(value, kind, location, errors, *, nullable=False):
    if nullable and value is None:
        return
    prefix = ID_PREFIXES[kind]
    if (not isinstance(value, str) or not value.startswith(prefix)
            or not SAFE_REFERENCE_ID.fullmatch(value)
            or len(value) < len(prefix) + 8):
        errors.append(f"{location} must be an opaque {prefix} identifier")


def _all_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _all_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _all_keys(child)


def validate_data_model_contract(document):
    """Return safety errors for the committed backend model blueprint."""
    errors = []
    root_fields = {
        "schema_version",
        "model_version",
        "status",
        "purpose",
        "identity",
        "entities",
        "relationships",
        "context_categories",
        "attempt_model",
        "consent",
        "context_and_evidence_boundaries",
        "export_model",
        "deletion_model",
        "correction_model",
        "runtime_session_context",
        "forbidden_shortcuts",
        "sources",
    }
    if not _require_fields(document, root_fields, "$", errors):
        return errors
    if document["schema_version"] != DATA_MODEL_SCHEMA_VERSION:
        errors.append("data model schema_version is unsupported")
    if not SEMVER.fullmatch(str(document["model_version"])):
        errors.append("data model version must use semantic versioning")
    if document["status"] != "backend_contract_not_database":
        errors.append("data model must remain a backend contract, not a database")

    identity = document["identity"]
    if identity.get("speaker_label_is_durable_identity") is not False:
        errors.append("speaker labels cannot be durable identity")
    if identity.get("run_id_is_session_id") is not False:
        errors.append("pipeline run IDs and product session IDs must stay separate")
    if identity.get("account_holder_local_speaker_label") != "SPEAKER_00":
        errors.append("the local account holder label must remain SPEAKER_00")
    if identity.get("identifiers_are_opaque") is not True:
        errors.append("durable identifiers must remain opaque")
    if identity.get("identifiers_must_not_contain_personal_information") is not True:
        errors.append("identifiers cannot contain personal information")

    required_entities = {
        "account",
        "session",
        "communication_context",
        "task_definition",
        "task_attempt",
        "exercise_assignment",
        "recording_asset",
        "analysis_run",
        "consent_event",
        "data_request",
    }
    if not required_entities.issubset(document["entities"]):
        errors.append("data model is missing required entities")
    for name in required_entities & set(document["entities"]):
        if not document["entities"][name].get("required_fields"):
            errors.append(f"entities.{name} must declare required fields")

    if set(document["context_categories"]) != CONTEXT_CATEGORIES:
        errors.append("context categories must contain the approved values exactly")

    attempt = document["attempt_model"]
    if set(attempt.get("roles") or []) != ATTEMPT_ROLES:
        errors.append("attempt roles must contain the approved values exactly")
    if attempt.get("attempts_are_overwritten") is not False:
        errors.append("task attempts cannot be overwritten")
    if attempt.get("later_attempt_requires_parent") is not True:
        errors.append("later attempts must link to an earlier attempt")
    if attempt.get("retention_and_transfer_are_distinct") is not True:
        errors.append("retention and transfer must remain distinct")

    consent = document["consent"]
    if set(consent.get("purposes") or []) != CONSENT_PURPOSES:
        errors.append("consent purposes must contain the approved values exactly")
    if set(consent.get("decisions") or []) != CONSENT_DECISIONS:
        errors.append("consent decisions must contain the approved values exactly")
    if set(consent.get("optional_purposes") or []) != OPTIONAL_CONSENT_PURPOSES:
        errors.append("optional consent purposes are incorrect")
    for field in (
            "every_choice_separate",
            "events_are_immutable",
            "withdrawal_changes_future_use",
            "notice_version_required"):
        if consent.get(field) is not True:
            errors.append(f"consent.{field} must remain true")
    for field in (
            "declining_optional_use_reduces_access",
            "consent_may_be_inferred_from_audio"):
        if consent.get(field) is not False:
            errors.append(f"consent.{field} must remain false")

    boundaries = document["context_and_evidence_boundaries"]
    if boundaries.get("exact_age_collected") is not False:
        errors.append("the backend data model cannot collect exact age")
    if boundaries.get("device_hardware_fingerprint_allowed") is not False:
        errors.append("the backend data model cannot fingerprint devices")
    if boundaries.get("different_context_ids_are_progress_comparable") is not False:
        errors.append("different communication contexts cannot be merged for progress")
    if boundaries.get("declared_and_inferred_values_are_separate") is not True:
        errors.append("declared and inferred context must remain separate")

    export = document["export_model"]
    required_export = {
        "account",
        "sessions",
        "communication_contexts",
        "task_attempts",
        "recording_asset_metadata",
        "analysis_runs_and_provenance",
        "consent_events",
        "data_request_history",
    }
    if export.get("account_scoped") is not True:
        errors.append("exports must be account scoped")
    if not required_export.issubset(export.get("includes") or []):
        errors.append("export model is missing required user records")
    if export.get("identity_verification_required_before_release") is not True:
        errors.append("exports require identity verification before release")

    deletion = document["deletion_model"]
    required_targets = {
        "sessions",
        "communication_contexts",
        "task_attempts",
        "recording_assets",
        "analysis_artifacts",
        "derived_measurements",
        "provider_copies",
        "backup_expiry_tracking",
    }
    if deletion.get("account_scoped_discovery") is not True:
        errors.append("deletion discovery must be account scoped")
    if not required_targets.issubset(deletion.get("targets") or []):
        errors.append("deletion model is missing required targets")
    if deletion.get("retention_periods_defined_here") is not False:
        errors.append("this contract cannot invent public retention periods")
    if deletion.get("completion_requires_target_statuses") is not True:
        errors.append("deletion completion requires per target status")

    correction = document["correction_model"]
    if correction.get("historical_attempt_evidence_is_silently_rewritten") is not False:
        errors.append("historical attempt evidence cannot be silently rewritten")
    if correction.get("correction_statement_can_be_linked") is not True:
        errors.append("correction statements must be linkable")

    runtime = document["runtime_session_context"]
    if runtime.get("artifact_name") != "session_context.json":
        errors.append("runtime context artifact name is unsupported")
    if runtime.get("required_before_durable_history_write") is not True:
        errors.append("durable history requires stable session context")

    if not isinstance(document["sources"], list) or not document["sources"]:
        errors.append("data model must retain its privacy sources")
    return errors


def validate_session_context(document):
    """Validate one immutable task-attempt context supplied by a future app."""
    errors = []
    root_fields = {
        "schema_version",
        "account",
        "session",
        "context",
        "task",
        "attempt",
        "participants",
        "capture",
        "self_report",
        "consent_snapshot",
    }
    if not _require_fields(document, root_fields, "$", errors):
        return errors
    if document["schema_version"] != SESSION_CONTEXT_SCHEMA_VERSION:
        errors.append("session context schema_version is unsupported")

    account = document["account"]
    if _require_fields(account, {"account_id", "status"}, "account", errors):
        _check_id(account["account_id"], "account_id", "account.account_id", errors)
        if account["status"] != "active":
            errors.append("session context requires an active account")
    account_id = account.get("account_id") if isinstance(account, dict) else None

    session = document["session"]
    session_fields = {
        "session_id",
        "account_id",
        "context_id",
        "language",
        "recording_mode",
        "started_at_utc",
    }
    if _require_fields(session, session_fields, "session", errors):
        _check_id(session["session_id"], "session_id", "session.session_id", errors)
        _check_id(session["context_id"], "context_id", "session.context_id", errors)
        if session["account_id"] != account_id:
            errors.append("session.account_id must match account.account_id")
        if session["recording_mode"] not in {"solo", "conversation"}:
            errors.append("session.recording_mode is unsupported")
        if not LANGUAGE_TAG.fullmatch(str(session["language"])):
            errors.append("session.language must be a valid language tag")
        _check_timestamp(session["started_at_utc"], "session.started_at_utc", errors)

    communication = document["context"]
    context_fields = {
        "context_id",
        "account_id",
        "category",
        "declared_goal",
        "audience",
        "environment",
    }
    if _require_fields(communication, context_fields, "context", errors):
        _check_id(communication["context_id"], "context_id", "context.context_id", errors)
        if communication["account_id"] != account_id:
            errors.append("context.account_id must match account.account_id")
        if communication["context_id"] != session.get("context_id"):
            errors.append("context.context_id must match session.context_id")
        if communication["category"] not in CONTEXT_CATEGORIES:
            errors.append("context.category is unsupported")
        if (not isinstance(communication["declared_goal"], str)
                or not communication["declared_goal"].strip()):
            errors.append("context.declared_goal must be nonempty user-declared text")
        environment = communication["environment"]
        if not _require_fields(
                environment, {"setting", "noise", "source"},
                "context.environment", errors):
            pass
        elif environment["source"] != "user_declared":
            errors.append("context environment must remain user declared")

    task = document["task"]
    task_fields = {
        "task_id",
        "task_version",
        "prompt_id",
        "prompt_version",
        "language",
        "preparation",
        "accommodations",
    }
    if _require_fields(task, task_fields, "task", errors):
        if not SAFE_REFERENCE_ID.fullmatch(str(task["task_id"])):
            errors.append("task.task_id is invalid")
        if not SAFE_REFERENCE_ID.fullmatch(str(task["prompt_id"])):
            errors.append("task.prompt_id is invalid")
        if not SEMVER.fullmatch(str(task["task_version"])):
            errors.append("task.task_version must use semantic versioning")
        if not SEMVER.fullmatch(str(task["prompt_version"])):
            errors.append("task.prompt_version must use semantic versioning")
        if task["language"] != session.get("language"):
            errors.append("task.language must match session.language")
        preparation = task["preparation"]
        if _require_fields(
                preparation, {"allowed_s", "actual_s"},
                "task.preparation", errors):
            values = (preparation["allowed_s"], preparation["actual_s"])
            if not all(isinstance(value, (int, float)) and value >= 0
                       for value in values):
                errors.append("task preparation values must be nonnegative numbers")
        if not isinstance(task["accommodations"], list):
            errors.append("task.accommodations must be a list")

    attempt = document["attempt"]
    attempt_fields = {
        "attempt_id",
        "account_id",
        "session_id",
        "context_id",
        "attempt_role",
        "sequence_index",
        "parent_attempt_id",
        "exercise_id",
        "recording_id",
    }
    if _require_fields(attempt, attempt_fields, "attempt", errors):
        _check_id(attempt["attempt_id"], "attempt_id", "attempt.attempt_id", errors)
        _check_id(attempt["recording_id"], "recording_id", "attempt.recording_id", errors)
        _check_id(
            attempt["parent_attempt_id"], "attempt_id",
            "attempt.parent_attempt_id", errors, nullable=True,
        )
        _check_id(
            attempt["exercise_id"], "exercise_id",
            "attempt.exercise_id", errors, nullable=True,
        )
        if attempt["account_id"] != account_id:
            errors.append("attempt.account_id must match account.account_id")
        if attempt["session_id"] != session.get("session_id"):
            errors.append("attempt.session_id must match session.session_id")
        if attempt["context_id"] != session.get("context_id"):
            errors.append("attempt.context_id must match session.context_id")
        role = attempt["attempt_role"]
        if role not in ATTEMPT_ROLES:
            errors.append("attempt.attempt_role is unsupported")
        if (not isinstance(attempt["sequence_index"], int)
                or isinstance(attempt["sequence_index"], bool)
                or attempt["sequence_index"] < 1):
            errors.append("attempt.sequence_index must be a positive integer")
        if role == "first" and attempt["parent_attempt_id"] is not None:
            errors.append("a first attempt cannot have a parent attempt")
        if role != "first" and attempt["parent_attempt_id"] is None:
            errors.append("a later attempt must link to its parent attempt")
        if role == "post_exercise_repeat" and attempt["exercise_id"] is None:
            errors.append("a post exercise repeat must link to an exercise")
        progress_intent = attempt.get("progress_intent")
        if (progress_intent is not None
                and progress_intent not in PROGRESS_INTENTS):
            errors.append("attempt.progress_intent is unsupported")
        if progress_intent == "baseline_observation" and role != "first":
            errors.append("a baseline observation must be a first attempt")
        if progress_intent == "retention" and role != "retention":
            errors.append("retention intent requires a retention attempt")
        if progress_intent == "transfer" and role != "transfer":
            errors.append("transfer intent requires a transfer attempt")
        if (progress_intent == "practice"
                and role not in {"matched_repeat", "post_exercise_repeat"}):
            errors.append("practice intent requires a repeat attempt")

    participants = document["participants"]
    participant_ids = []
    speaker_labels = []
    account_holders = []
    if not isinstance(participants, list) or not participants:
        errors.append("participants must be a nonempty list")
        participants = []
    for index, participant in enumerate(participants):
        location = f"participants[{index}]"
        fields = {"participant_id", "role", "account_id", "speaker_label"}
        if not _require_fields(participant, fields, location, errors):
            continue
        _check_id(
            participant["participant_id"], "participant_id",
            f"{location}.participant_id", errors,
        )
        participant_ids.append(participant["participant_id"])
        label = participant["speaker_label"]
        if not isinstance(label, str) or not SPEAKER_LABEL.fullmatch(label):
            errors.append(f"{location}.speaker_label is invalid")
        speaker_labels.append(label)
        if participant["role"] == "account_holder":
            account_holders.append(participant)
            if participant["account_id"] != account_id:
                errors.append(f"{location}.account_id must match the account")
            if label != "SPEAKER_00":
                errors.append("the account holder must be SPEAKER_00 locally")
        elif participant["role"] == "other_consented_speaker":
            if participant["account_id"] is not None:
                errors.append(
                    f"{location}.account_id must remain null without a separate account"
                )
        else:
            errors.append(f"{location}.role is unsupported")
    if len(set(participant_ids)) != len(participant_ids):
        errors.append("participant IDs must be unique within the session")
    if len(set(speaker_labels)) != len(speaker_labels):
        errors.append("speaker labels must be unique within the recording")
    if len(account_holders) != 1:
        errors.append("the session must have exactly one account holder")
    mode = session.get("recording_mode") if isinstance(session, dict) else None
    if mode == "solo" and len(participants) != 1:
        errors.append("solo mode must contain only the account holder")
    if mode == "conversation" and len(participants) < 2:
        errors.append("conversation mode requires another consented participant")

    capture = document["capture"]
    capture_fields = {
        "recording_id", "device", "environment", "quality_policy",
        "speaker_mapping_source",
    }
    if _require_fields(capture, capture_fields, "capture", errors):
        _check_id(capture["recording_id"], "recording_id", "capture.recording_id", errors)
        if capture["recording_id"] != attempt.get("recording_id"):
            errors.append("capture.recording_id must match attempt.recording_id")
        if capture["quality_policy"] not in {"lenient", "baseline"}:
            errors.append("capture.quality_policy is unsupported")
        if capture["speaker_mapping_source"] not in {
                "account_holder_only_capture", "user_confirmed_after_recording"}:
            errors.append("capture.speaker_mapping_source is unsupported")
        if mode == "solo" and capture["speaker_mapping_source"] != (
                "account_holder_only_capture"):
            errors.append("solo speaker mapping must come from account holder capture")
        if mode == "conversation" and capture["speaker_mapping_source"] != (
                "user_confirmed_after_recording"):
            errors.append("conversation speaker mapping requires user confirmation")
        device = capture["device"]
        if _require_fields(
                device, {"device_class", "platform", "microphone", "source"},
                "capture.device", errors):
            forbidden_device_fields = {
                "hardware_id", "advertising_id", "serial_number", "fingerprint"
            }
            if forbidden_device_fields.intersection(device):
                errors.append("capture.device cannot contain a hardware fingerprint")
        technical_environment = capture["environment"]
        if not _require_fields(
                technical_environment, {"source", "observations"},
                "capture.environment", errors):
            pass
        elif technical_environment["source"] != "technical_observation":
            errors.append("capture environment must remain a technical observation")

    self_report = document["self_report"]
    self_report_fields = {
        "source",
        "representativeness",
        "difficulty",
        "confidence",
        "temporary_context",
    }
    if _require_fields(self_report, self_report_fields, "self_report", errors):
        if self_report["source"] != "user_declared":
            errors.append("self report must remain user declared")
        if not isinstance(self_report["temporary_context"], list):
            errors.append("self_report.temporary_context must be a list")
        usefulness = self_report.get("usefulness")
        if usefulness is not None and (
                not isinstance(usefulness, str) or not usefulness.strip()):
            errors.append("self_report.usefulness must be user declared text")

    outcome_report = document.get("outcome_report")
    if outcome_report is not None:
        outcome_fields = {
            "source", "question_version", "real_world_outcome"
        }
        if _require_fields(
                outcome_report, outcome_fields, "outcome_report", errors):
            if outcome_report["source"] != "user_declared":
                errors.append("outcome report must remain user declared")
            if not SEMVER.fullmatch(str(outcome_report["question_version"])):
                errors.append(
                    "outcome_report.question_version must use semantic versioning"
                )
            if (not isinstance(outcome_report["real_world_outcome"], str)
                    or not outcome_report["real_world_outcome"].strip()):
                errors.append(
                    "outcome_report.real_world_outcome must be user declared text"
                )

    snapshot = document["consent_snapshot"]
    if _require_fields(snapshot, {"as_of_utc", "decisions"},
                       "consent_snapshot", errors):
        _check_timestamp(snapshot["as_of_utc"], "consent_snapshot.as_of_utc", errors)
        decisions = snapshot["decisions"]
        seen = set()
        consent_event_ids = []
        if not isinstance(decisions, list):
            errors.append("consent_snapshot.decisions must be a list")
            decisions = []
        for index, decision in enumerate(decisions):
            location = f"consent_snapshot.decisions[{index}]"
            fields = {
                "consent_event_id",
                "participant_id",
                "purpose",
                "decision",
                "notice_version",
                "recorded_at_utc",
                "source",
            }
            if not _require_fields(decision, fields, location, errors):
                continue
            _check_id(
                decision["consent_event_id"], "consent_event_id",
                f"{location}.consent_event_id", errors,
            )
            consent_event_ids.append(decision["consent_event_id"])
            key = (decision["participant_id"], decision["purpose"])
            if key in seen:
                errors.append(f"{location} duplicates an effective consent choice")
            seen.add(key)
            if decision["participant_id"] not in participant_ids:
                errors.append(f"{location} references an unknown participant")
            if decision["purpose"] not in CONSENT_PURPOSES:
                errors.append(f"{location}.purpose is unsupported")
            if decision["decision"] not in CONSENT_DECISIONS:
                errors.append(f"{location}.decision is unsupported")
            if not SEMVER.fullmatch(str(decision["notice_version"])):
                errors.append(f"{location}.notice_version must use semantic versioning")
            _check_timestamp(decision["recorded_at_utc"],
                             f"{location}.recorded_at_utc", errors)
            if decision["source"] not in {
                    "user_explicit", "authorised_representative"}:
                errors.append(f"{location}.source is unsupported")
        expected = {
            (participant_id, purpose)
            for participant_id in participant_ids
            for purpose in CONSENT_PURPOSES
        }
        if seen != expected:
            errors.append("every participant needs one separate effective choice per purpose")
        if len(consent_event_ids) != len(set(consent_event_ids)):
            errors.append("consent event IDs must be unique")
        for participant_id in participant_ids:
            processing = next(
                (item for item in decisions
                 if item.get("participant_id") == participant_id
                 and item.get("purpose") == "speech_measurement_processing"),
                None,
            )
            if processing is None or processing.get("decision") != "granted":
                errors.append(
                    f"participant {participant_id} has not granted speech "
                    "measurement processing"
                )

    keys = {key.lower() for key in _all_keys(document)}
    for forbidden in {"exact_age", "date_of_birth", "diagnosis"}:
        if forbidden in keys:
            errors.append(f"session context contains forbidden field {forbidden}")
    return errors


def validate_context_for_run(document, recording_mode, history_speaker_label=None,
                             quality_policy=None):
    """Add runner-specific checks to the standalone context validation."""
    errors = validate_session_context(document)
    session = document.get("session") if isinstance(document, dict) else None
    if isinstance(session, dict) and session.get("recording_mode") != recording_mode:
        errors.append("session recording mode does not match the pipeline run")
    capture = document.get("capture") if isinstance(document, dict) else None
    if (quality_policy is not None and isinstance(capture, dict)
            and capture.get("quality_policy") != quality_policy):
        errors.append("capture quality policy does not match the pipeline run")
    if history_speaker_label is not None:
        holder = account_holder_participant(document)
        if holder is None or holder.get("speaker_label") != history_speaker_label:
            errors.append("history speaker label must identify the account holder")
        attempt = document.get("attempt") if isinstance(document, dict) else None
        if not isinstance(attempt, dict) or not attempt.get("progress_intent"):
            errors.append(
                "durable history requires an explicit attempt.progress_intent"
            )
    return errors


def account_holder_participant(document):
    participants = document.get("participants") if isinstance(document, dict) else []
    if not isinstance(participants, list):
        return None
    return next(
        (item for item in participants
         if isinstance(item, dict) and item.get("role") == "account_holder"),
        None,
    )


def session_context_reference(document):
    """Return the non-personal linkage and hash stored in run provenance."""
    encoded = json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return {
        "schema_version": document["schema_version"],
        "account_id": document["account"]["account_id"],
        "session_id": document["session"]["session_id"],
        "context_id": document["context"]["context_id"],
        "attempt_id": document["attempt"]["attempt_id"],
        "recording_id": document["attempt"]["recording_id"],
        "sha256": hashlib.sha256(encoded).hexdigest(),
    }


def assert_valid_data_model(document):
    errors = validate_data_model_contract(document)
    if errors:
        raise DataModelValidationError("\n".join(errors))
    return document


def assert_valid_session_context(document):
    errors = validate_session_context(document)
    if errors:
        raise DataModelValidationError("\n".join(errors))
    return document
