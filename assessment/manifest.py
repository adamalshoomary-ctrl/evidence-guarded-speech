"""Load and validate the versioned onboarding assessment manifest."""

from __future__ import annotations

import json
import re
from pathlib import Path

from pipeline.measurement_evidence import (
    METRIC_DEFINITIONS,
    VOICE_DEFINITIONS,
    VOICE_PROSODY_DEFINITIONS,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "assessment" / "manifest-v1.1.0.json"
SUPPORTED_SCHEMA_VERSION = "1.1.0"
TASK_STATUSES = {
    "core",
    "core_alternative",
    "adaptive_optional",
    "optional_research",
    "future_locked",
}
REQUIRED_TASK_FIELDS = {
    "task_id",
    "task_version",
    "status",
    "kind",
    "language",
    "purpose",
    "constructs",
    "prompt",
    "expected_text_asset",
    "duration_s",
    "recording",
    "measurements_enabled",
    "measurement_use",
    "preparation",
    "repetitions",
    "accommodations",
    "retry_policy",
    "stop_conditions",
    "comparison",
}
SAFE_PROGRESS_POLICIES = {
    "blocked",
    "blocked_until_reliability_release",
    "not_a_speech_measurement",
    "not_a_speech_skill",
    "separate_from_speech_measurements",
}
KNOWN_MEASUREMENTS = {
    *(f"computed_metrics.{name}" for name in METRIC_DEFINITIONS),
    *(f"voice_quality.{name}" for name in VOICE_DEFINITIONS),
    *(f"voice_prosody.{name}" for name in VOICE_PROSODY_DEFINITIONS),
    "audio_quality.*",
    "self_report.goal",
    "self_report.context",
    "self_report.representativeness",
    "self_report.accommodations",
    "self_report.difficulty",
    "self_report.confidence",
    "self_report.temporary_context",
}
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
LANGUAGE_TAG = re.compile(r"^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")


class ManifestValidationError(ValueError):
    """Raised when the assessment manifest violates its safety contract."""


def load_manifest(path=MANIFEST_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _word_count(text):
    return len(re.findall(r"\b[\w']+\b", text or ""))


def _normalise_text(text):
    return " ".join(re.findall(r"[\w']+", (text or "").lower()))


def _require_fields(value, required, location, errors):
    if not isinstance(value, dict):
        errors.append(f"{location} must be an object")
        return
    missing = sorted(required - set(value))
    if missing:
        errors.append(f"{location} missing fields: {', '.join(missing)}")


def _validate_task(task, launch_languages, assets, errors):
    task_id = task.get("task_id", "<unknown>")
    location = f"tasks.{task_id}"
    _require_fields(task, REQUIRED_TASK_FIELDS, location, errors)
    if not REQUIRED_TASK_FIELDS.issubset(task):
        return

    if not SEMVER.fullmatch(str(task["task_version"])):
        errors.append(f"{location}.task_version must use semantic versioning")
    if task["status"] not in TASK_STATUSES:
        errors.append(f"{location}.status is unsupported")
    if task["language"] not in launch_languages:
        errors.append(f"{location}.language is not a launch language")
    if not LANGUAGE_TAG.fullmatch(str(task["language"])):
        errors.append(f"{location}.language is not a valid language tag")
    if not task["constructs"]:
        errors.append(f"{location}.constructs cannot be empty")

    prompt = task["prompt"]
    _require_fields(prompt, {"version", "source", "instruction"},
                    f"{location}.prompt", errors)
    if isinstance(prompt, dict) and not SEMVER.fullmatch(
            str(prompt.get("version"))):
        errors.append(f"{location}.prompt.version must use semantic versioning")

    expected = task["expected_text_asset"]
    if expected is not None and expected not in assets:
        errors.append(f"{location}.expected_text_asset does not exist")
    elif expected is not None and assets[expected].get("language") != task["language"]:
        errors.append(f"{location}.expected_text_asset language does not match")
    if (task["kind"] in {"fixed_reading", "listen_and_repeat", "fixed_repeat"}
            and expected is None):
        errors.append(f"{location} requires expected text")

    duration = task["duration_s"]
    _require_fields(duration, {"target", "minimum", "maximum"},
                    f"{location}.duration_s", errors)
    if isinstance(duration, dict) and {"target", "minimum", "maximum"}.issubset(
            duration):
        minimum = duration["minimum"]
        target = duration["target"]
        maximum = duration["maximum"]
        if not all(isinstance(item, (int, float)) for item in
                   (minimum, target, maximum)):
            errors.append(f"{location}.duration_s values must be numeric")
        elif not minimum <= target <= maximum:
            errors.append(f"{location}.duration_s must satisfy minimum <= target <= maximum")
        if task["status"] == "future_locked" and any(
                item != 0 for item in (minimum, target, maximum)):
            errors.append(f"{location} is locked but has a nonzero duration")

    recording = task["recording"]
    _require_fields(recording, {"required", "quality_policy", "silence_lead_s"},
                    f"{location}.recording", errors)
    if isinstance(recording, dict) and recording.get("required"):
        if recording.get("quality_policy") != "baseline":
            errors.append(f"{location} recording must use baseline quality policy")
    if task["status"] == "future_locked" and recording.get("required"):
        errors.append(f"{location} is locked but requires recording")

    unknown = sorted(set(task["measurements_enabled"]) - KNOWN_MEASUREMENTS)
    if unknown:
        errors.append(f"{location} enables unknown measurements: {', '.join(unknown)}")
    if task["status"] == "future_locked" and task["measurements_enabled"]:
        errors.append(f"{location} is locked but enables measurements")

    measurement_use = task["measurement_use"]
    _require_fields(
        measurement_use,
        {"single_session_interpretation", "progress", "ranking", "diagnosis"},
        f"{location}.measurement_use",
        errors,
    )
    if isinstance(measurement_use, dict):
        if measurement_use.get("ranking") != "blocked":
            errors.append(f"{location} must block ranking")
        if measurement_use.get("diagnosis") != "blocked":
            errors.append(f"{location} must block diagnosis")
        if measurement_use.get("progress") not in SAFE_PROGRESS_POLICIES:
            errors.append(f"{location} has an unsafe progress policy")

    if task["status"] in {"optional_research", "future_locked"}:
        if task.get("required_consent") != "research_collection":
            errors.append(f"{location} requires separate research consent")
    if task["status"] == "optional_research" and (
            task["measurement_use"].get("single_session_interpretation") != "blocked"):
        errors.append(f"{location} cannot affect the released interpretation")

    if not task["accommodations"]:
        errors.append(f"{location}.accommodations cannot be empty")
    if not task["stop_conditions"]:
        errors.append(f"{location}.stop_conditions cannot be empty")
    comparison = task["comparison"]
    _require_fields(comparison, {"comparable_with", "limitations"},
                    f"{location}.comparison", errors)


def validate_manifest(document):
    """Return human-readable errors; an empty list means the protocol is valid."""
    errors = []
    _require_fields(
        document,
        {
            "schema_version",
            "protocol_id",
            "protocol_version",
            "status",
            "title",
            "purpose",
            "protocol_scope",
            "eligibility",
            "session",
            "consent",
            "progression_handoff",
            "content_assets",
            "tasks",
        },
        "$",
        errors,
    )
    if errors:
        return errors
    if document["schema_version"] != SUPPORTED_SCHEMA_VERSION:
        errors.append("schema_version is unsupported")
    if not SEMVER.fullmatch(str(document["protocol_version"])):
        errors.append("protocol_version must use semantic versioning")
    if document["status"] != "pilot_not_validated":
        errors.append("protocol must remain pilot_not_validated")

    scope = document["protocol_scope"]
    if scope.get("recording_mode") != "solo":
        errors.append("assessment recording mode must be solo")
    if set(scope.get("claim_authority") or []) != {
            "measured_observation", "interpretation"}:
        errors.append("claim authority must remain observation and interpretation")
    required_forbidden = {
        "diagnosis",
        "ranking_between_people",
        "global_communication_score",
        "accent_quality",
    }
    if not required_forbidden.issubset(scope.get("forbidden_claims", [])):
        errors.append("product_scope is missing required forbidden claims")

    age = document["eligibility"].get("age") or {}
    if age.get("gate") != "none":
        errors.append("the approved protocol has no backend age gate")
    if age.get("exact_age_collected") is not False:
        errors.append("the assessment must not collect exact age")
    if age.get("age_norms_used") is not False:
        errors.append("the assessment must not use age norms")
    launch_languages = document["eligibility"].get("launch_languages") or []
    if launch_languages != ["en"]:
        errors.append("version 1 launch language must be English only")

    consent = document["consent"]
    required_consents = {
        "speech_measurement_processing",
        "raw_audio_retention",
        "human_review",
        "research_collection",
        "model_improvement",
        "fairness_metadata",
    }
    missing_consents = sorted(required_consents - set(consent))
    if missing_consents:
        errors.append("missing consent choices: " + ", ".join(missing_consents))
    for name in required_consents & set(consent):
        choice = consent[name]
        if choice.get("separate_choice") is not True:
            errors.append(f"consent.{name} must be a separate choice")
        if choice.get("default") is not False:
            errors.append(f"consent.{name} must default to false")
    if consent.get("speech_measurement_processing", {}).get("required_for_session") is not True:
        errors.append("speech measurement processing consent is required for the session")
    for name in required_consents - {"speech_measurement_processing"}:
        if consent.get(name, {}).get("required_for_session") is not False:
            errors.append(f"consent.{name} cannot be required for the session")

    handoff = document["progression_handoff"]
    if handoff.get("overall_score_allowed") is not False:
        errors.append("progression handoff cannot create an overall score")
    if "later day" not in handoff.get("mastery_rule", ""):
        errors.append("mastery rule must require later-day evidence")
    if "new prompt" not in handoff.get("mastery_rule", ""):
        errors.append("mastery rule must require transfer to a new prompt")

    assets = document["content_assets"]
    for name, asset in assets.items():
        if asset.get("language") not in launch_languages:
            errors.append(f"content_assets.{name} has an unsupported language")
        if not SEMVER.fullmatch(str(asset.get("version"))):
            errors.append(f"content_assets.{name}.version must use semantic versioning")
        if "text" in asset and asset.get("declared_word_count") != _word_count(
                asset["text"]):
            errors.append(f"content_assets.{name}.declared_word_count is wrong")

    tasks = document["tasks"]
    if not isinstance(tasks, list) or not tasks:
        errors.append("tasks must be a nonempty list")
        return errors
    task_ids = [task.get("task_id") for task in tasks]
    duplicates = sorted({item for item in task_ids if task_ids.count(item) > 1})
    if duplicates:
        errors.append("duplicate task ids: " + ", ".join(duplicates))
    by_id = {task.get("task_id"): task for task in tasks}
    for task in tasks:
        _validate_task(task, launch_languages, assets, errors)
        comparison = task.get("comparison") or {}
        for compared_task in comparison.get("comparable_with", []):
            if compared_task not in by_id:
                errors.append(
                    f"tasks.{task.get('task_id')}.comparison references "
                    f"missing task {compared_task}"
                )
        source_asset_name = comparison.get("source_task_text_asset")
        segment_asset_name = comparison.get("source_segment_asset")
        if source_asset_name is not None or segment_asset_name is not None:
            source_asset = assets.get(source_asset_name)
            segment_asset = assets.get(segment_asset_name)
            if source_asset is None:
                errors.append(
                    f"tasks.{task.get('task_id')}.comparison references "
                    "a missing source text asset"
                )
            if segment_asset is None:
                errors.append(
                    f"tasks.{task.get('task_id')}.comparison references "
                    "a missing source segment asset"
                )
            if task.get("expected_text_asset") != segment_asset_name:
                errors.append(
                    f"tasks.{task.get('task_id')} repeat text must match its "
                    "source segment"
                )
            if source_asset is not None and segment_asset is not None:
                source_text = source_asset.get("text") or " ".join(
                    source_asset.get("sentences") or []
                )
                segment_text = segment_asset.get("text") or " ".join(
                    segment_asset.get("sentences") or []
                )
                if _normalise_text(segment_text) not in _normalise_text(
                        source_text):
                    errors.append(
                        f"tasks.{task.get('task_id')} repeat text is not a "
                        "segment of its source task"
                    )

    session = document["session"]
    duration_range = session.get("acceptable_duration_s") or {}
    target = session.get("target_duration_s")
    if not (duration_range.get("minimum", 0) <= target
            <= duration_range.get("maximum", -1)):
        errors.append("session target duration is outside its acceptable range")
    if duration_range.get("maximum") > 660:
        errors.append("core assessment may not exceed eleven minutes")
    if session.get("quality_policy") != "baseline":
        errors.append("assessment session must use baseline quality policy")

    seen_steps = set()
    selected_duration = 0
    for step in session.get("core_sequence") or []:
        step_id = step.get("step_id")
        if step_id in seen_steps:
            errors.append(f"duplicate core step: {step_id}")
        seen_steps.add(step_id)
        options = step.get("task_options") or []
        if step.get("required") is not True:
            errors.append(f"core step {step_id} must be required")
        if not options:
            errors.append(f"core step {step_id} has no task option")
            continue
        for task_id in options:
            task = by_id.get(task_id)
            if task is None:
                errors.append(f"core step {step_id} references missing task {task_id}")
            elif task.get("status") not in {"core", "core_alternative"}:
                errors.append(f"core step {step_id} includes noncore task {task_id}")
        first = by_id.get(options[0])
        if first:
            selected_duration += first["duration_s"]["target"]
            first_target = first["duration_s"]["target"]
            for task_id in options[1:]:
                option = by_id.get(task_id)
                if option and option["duration_s"]["target"] != first_target:
                    errors.append(
                        f"core step {step_id} alternatives need equal target duration"
                    )
    if selected_duration != target:
        errors.append(
            f"core task targets total {selected_duration}, expected {target}"
        )

    steps_by_id = {
        step.get("step_id"): set(step.get("task_options") or [])
        for step in session.get("core_sequence") or []
    }
    standard_options = steps_by_id.get("standard_sample", set())
    repeat_options = steps_by_id.get("repeat_sample", set())
    paired_rules = session.get("paired_task_rules")
    if not isinstance(paired_rules, dict):
        errors.append("session must define paired standard and repeat tasks")
    else:
        if set(paired_rules) != standard_options:
            errors.append(
                "every standard sample option needs exactly one paired repeat"
            )
        if set(paired_rules.values()) != repeat_options:
            errors.append(
                "every repeat sample option needs exactly one standard source"
            )
        for source_id, repeat_id in paired_rules.items():
            source = by_id.get(source_id)
            repeat = by_id.get(repeat_id)
            if source is None or repeat is None:
                errors.append(
                    f"paired task rule {source_id} to {repeat_id} references "
                    "a missing task"
                )
                continue
            comparable = (repeat.get("comparison") or {}).get(
                "comparable_with", []
            )
            if comparable != [source_id]:
                errors.append(
                    f"paired repeat {repeat_id} must compare only with "
                    f"{source_id}"
                )
            if ((repeat.get("comparison") or {}).get(
                    "source_task_text_asset") !=
                    source.get("expected_text_asset")):
                errors.append(
                    f"paired repeat {repeat_id} must use the expected text "
                    f"from {source_id}"
                )
    follow_up = by_id.get(session.get("optional_follow_up_task"))
    if follow_up is None or follow_up.get("status") != "adaptive_optional":
        errors.append("optional follow-up must reference an adaptive task")
    elif any("skill" in item or "score" in item
             for item in follow_up.get("trigger_conditions", [])):
        errors.append("adaptive follow-up cannot be triggered by a skill score")

    return errors


def assert_valid_manifest(document):
    errors = validate_manifest(document)
    if errors:
        raise ManifestValidationError("\n".join(errors))
    return document
