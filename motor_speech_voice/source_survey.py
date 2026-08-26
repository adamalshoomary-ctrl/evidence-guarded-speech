"""Validate the checkpoint 23B candidate reference source survey.

The survey records what public sources could supply the independent human
reference evidence item 23 needs.  This validator exists to stop the survey
quietly becoming something stronger than that.

It refuses a record that claims a source satisfies a truth requirement, a
record that calls a non commercial or unobtainable source open, a registry
whose summary disagrees with its own records, any acquired data inside the
repository, and any import of this material into the running pipeline.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from jsonschema import Draft202012Validator


MODULE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = MODULE_ROOT.parent
SURVEY_ROOT = MODULE_ROOT / "source_survey"
SCHEMA_PATH = SURVEY_ROOT / "source-survey-schema-v1.0.0.json"
REGISTRY_PATH = SURVEY_ROOT / "source-survey-registry-v1.0.0.json"

# The runbook plans this root for future approved private evidence.  Nothing
# may create or populate it while checkpoint 23B remains in progress.
PRIVATE_EVIDENCE_ROOT = REPOSITORY_ROOT / ".research_data" / "motor_speech_voice" / "23b"

ACTIVE_PYTHON_ROOTS = ("pipeline",)

# A direct verification claim has to name when it was made.  Availability and
# licence statements change, so an undated claim cannot be rechecked and must
# not be trusted later.
DATED_MATERIAL = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")

# A source may only be described as open when it is genuinely obtainable with
# no contact and its licence genuinely permits this project's use.
OPEN_DECISION = "open_but_truth_class_unresolved"
OBTAINABLE_WITHOUT_CONTACT = "obtainable_without_contact"

REQUIRED_CROSS_SOURCE_RULES = {
    "truth_classes_may_be_pooled": False,
    "diagnosis_is_numeric_ground_truth": False,
    "consensus_may_replace_retained_disagreement": False,
    "public_visibility_implies_a_licence": False,
    "single_rater_may_substitute_for_multiple_raters": False,
    "agreement_between_two_systems_is_evidence": False,
    "a_source_may_be_recorded_as_meeting_a_truth_requirement": False,
    "acquisition_authorised_by_this_survey": False,
}

REQUIRED_LANES = {
    "motor_task_timing_and_accuracy",
    "perceptual_voice",
    "intelligibility",
    "australian_english",
}


def load_json(path: Path):
    return json.loads(path.read_text())


def record_paths():
    """Every survey record file on disk, registry excluded."""
    return sorted(
        path
        for path in SURVEY_ROOT.glob("*.json")
        if path.name not in {SCHEMA_PATH.name, REGISTRY_PATH.name}
    )


def validate_record(document, schema, filename):
    """Schema plus the safety rules a schema cannot express."""
    errors = []
    validator = Draft202012Validator(schema)
    for error in sorted(validator.iter_errors(document), key=lambda item: item.path):
        location = "/".join(str(part) for part in error.path) or "(root)"
        errors.append(f"{filename}: schema error at {location}: {error.message}")
    if errors:
        # Later rules assume a well formed record.
        return errors

    source_id = document["source_id"]
    if document["eligibility"]["selected"] is not False:
        errors.append(f"{filename}: {source_id} records a selection")

    if document["reference_truth"]["requirement_status"] not in {"fails", "unresolved"}:
        errors.append(
            f"{filename}: {source_id} claims a truth requirement outcome this "
            "survey may not decide"
        )

    licence = document["licence"]
    access = document["access"]
    decision = document["eligibility"]["decision"]

    if decision == OPEN_DECISION:
        if licence["commercial_use_permitted"] is not True:
            errors.append(
                f"{filename}: {source_id} is described as open while its licence "
                "does not clearly permit commercial use"
            )
        if access["state"] != OBTAINABLE_WITHOUT_CONTACT:
            errors.append(
                f"{filename}: {source_id} is described as open while it cannot be "
                "obtained without contact or agreement"
            )

    if access["state"] == OBTAINABLE_WITHOUT_CONTACT:
        blocking = [
            name
            for name in (
                "contact_with_a_person_required",
                "organisation_signatory_required",
                "account_required",
                "agreement_signature_required",
            )
            if access[name]
        ]
        if blocking:
            errors.append(
                f"{filename}: {source_id} claims it needs no contact while also "
                "requiring " + ", ".join(blocking)
            )

    governance = document["governance"]
    if governance["raw_data_committed"] is not False:
        errors.append(f"{filename}: {source_id} claims committed raw data")
    if governance["acquisition_authorised"] is not False:
        errors.append(f"{filename}: {source_id} claims authorised acquisition")
    if governance["transfer_to_any_provider"] != "blocked":
        errors.append(f"{filename}: {source_id} does not block provider transfer")

    audit = document["capability_audit"]
    if audit["verification_level"] == "verified_directly":
        if not any(
            DATED_MATERIAL.search(material) for material in audit["inspected_materials"]
        ):
            errors.append(
                f"{filename}: {source_id} claims direct verification without "
                "recording a dated inspected material"
            )
    elif audit["verification_level"] == "reported_not_verified":
        if decision == OPEN_DECISION:
            errors.append(
                f"{filename}: {source_id} is described as open on unverified "
                "reporting"
            )

    return errors


def validate_registry(registry, records):
    """The summary must not drift away from the records it summarises."""
    errors = []

    if registry.get("schema_version") != "1.0.0":
        errors.append("registry: unexpected schema version")
    if registry.get("registry_id") != "motor_speech_voice_source_survey_v1":
        errors.append("registry: unexpected registry id")
    if registry.get("checkpoint") != "23B":
        errors.append("registry: unexpected checkpoint")
    if registry.get("status") != "evidence_survey_complete_no_source_selected":
        errors.append("registry: status no longer records that nothing was selected")
    if registry.get("raw_data_committed") is not False:
        errors.append("registry: claims committed raw data")
    if registry.get("acquisition_authorised") is not False:
        errors.append("registry: claims authorised acquisition")

    rules = registry.get("cross_source_rules", {})
    for name, expected in REQUIRED_CROSS_SOURCE_RULES.items():
        if name not in rules:
            errors.append(f"registry: missing cross source rule {name}")
        elif rules[name] is not expected:
            errors.append(f"registry: cross source rule {name} was weakened")
    for name in rules:
        if name not in REQUIRED_CROSS_SOURCE_RULES:
            errors.append(f"registry: unknown cross source rule {name}")

    listed = [entry["source_id"] for entry in registry.get("records", [])]
    present = [document["source_id"] for document in records]
    if sorted(listed) != sorted(present):
        missing = sorted(set(present) - set(listed))
        extra = sorted(set(listed) - set(present))
        if missing:
            errors.append("registry: records on disk are not listed: " + ", ".join(missing))
        if extra:
            errors.append("registry: listed records do not exist: " + ", ".join(extra))
    if len(listed) != len(set(listed)):
        errors.append("registry: a source is listed more than once")
    if registry.get("record_count") != len(present):
        errors.append("registry: record count does not match the records on disk")

    expected_open = sorted(
        document["source_id"]
        for document in records
        if document["access"]["state"] == OBTAINABLE_WITHOUT_CONTACT
    )
    if registry.get("obtainable_without_contact") != expected_open:
        errors.append(
            "registry: the obtainable without contact list does not match the records"
        )
    expected_commercial = sorted(
        document["source_id"]
        for document in records
        if document["licence"]["commercial_use_permitted"] is True
    )
    if registry.get("commercial_use_permitted") != expected_commercial:
        errors.append(
            "registry: the commercial use list does not match the records"
        )

    counts = registry.get("counts", {})
    if counts.get("obtainable_without_any_contact_account_or_agreement") != len(
        expected_open
    ):
        errors.append("registry: open count does not match the records")
    if counts.get("licence_permits_commercial_use") != len(expected_commercial):
        errors.append("registry: commercial count does not match the records")
    if counts.get("recorded_as_meeting_an_item_23_truth_requirement") != 0:
        errors.append(
            "registry: claims a source meets an item 23 truth requirement"
        )
    if counts.get("selected") != 0:
        errors.append("registry: claims a selection")

    lanes = registry.get("lane_conclusions", {})
    missing_lanes = REQUIRED_LANES - set(lanes)
    if missing_lanes:
        errors.append("registry: missing lane conclusions: " + ", ".join(sorted(missing_lanes)))
    for lane, body in lanes.items():
        for field in ("question", "answer", "conclusion", "consequences"):
            if not body.get(field):
                errors.append(f"registry: lane {lane} is missing {field}")

    if not registry.get("limitations"):
        errors.append("registry: limitations were removed")

    return errors


def committed_data_leakage():
    """Anything in the survey directory that is not a JSON record."""
    if not SURVEY_ROOT.exists():
        return ["the survey directory is missing"]
    return sorted(
        str(path.relative_to(REPOSITORY_ROOT))
        for path in SURVEY_ROOT.rglob("*")
        if path.is_file() and path.suffix != ".json"
    )


def private_evidence_root_present():
    """The planned private root must not exist while 23B is in progress."""
    return PRIVATE_EVIDENCE_ROOT.exists()


def active_pipeline_leakage():
    """The running pipeline must not import or name this survey."""
    hits = []
    for root in ACTIVE_PYTHON_ROOTS:
        directory = REPOSITORY_ROOT / root
        if not directory.exists():
            continue
        for path in sorted(directory.rglob("*.py")):
            text = path.read_text(errors="ignore")
            if "source_survey" in text or "motor_speech_voice" in text:
                hits.append(str(path.relative_to(REPOSITORY_ROOT)))
    return hits


def validate_survey():
    """Validate every record, the registry and the surrounding boundaries."""
    errors = []
    if not SCHEMA_PATH.exists():
        return [f"missing schema: {SCHEMA_PATH.name}"]
    if not REGISTRY_PATH.exists():
        return [f"missing registry: {REGISTRY_PATH.name}"]

    schema = load_json(SCHEMA_PATH)
    paths = record_paths()
    if not paths:
        return ["the survey contains no records"]

    records = []
    for path in paths:
        try:
            document = load_json(path)
        except json.JSONDecodeError as error:
            errors.append(f"{path.name}: is not valid JSON: {error}")
            continue
        records.append(document)
        errors.extend(validate_record(document, schema, path.name))

    seen = {}
    for document in records:
        source_id = document.get("source_id")
        if source_id in seen:
            errors.append(f"duplicate source id across records: {source_id}")
        seen[source_id] = True

    errors.extend(validate_registry(load_json(REGISTRY_PATH), records))

    leaked = committed_data_leakage()
    if leaked:
        errors.append("acquired or non record files committed: " + ", ".join(leaked))
    if private_evidence_root_present():
        errors.append(
            "the planned private evidence root exists before it is authorised: "
            + str(PRIVATE_EVIDENCE_ROOT.relative_to(REPOSITORY_ROOT))
        )
    pipeline_hits = active_pipeline_leakage()
    if pipeline_hits:
        errors.append(
            "item 23 survey material reached the active pipeline: "
            + ", ".join(pipeline_hits)
        )
    return errors
