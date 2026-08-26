"""Validate the checkpoint 23B measurement and sampling input package.

The package records what an independent statistician would need before a study
could be designed for each provisional construct.  This validator exists to stop
it quietly becoming a statistical plan, a selection or a result.

Its central rule is blunt: a record may contain no JSON number.  Every
legitimate quantity in this material lives inside a citation or a formula
written as words, so a bare number would be something computed, and this package
computes nothing.  Beside that it refuses a selection, a sample size, a missing
honest blocker, a reference availability claim that disagrees with the
checkpoint 23B source survey, a registry that disagrees with its own records,
and any import of this material into the running pipeline.
"""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator


MODULE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = MODULE_ROOT.parent
PLAN_ROOT = MODULE_ROOT / "measurement_plan"
SCHEMA_PATH = PLAN_ROOT / "measurement-plan-schema-v1.0.0.json"
REGISTRY_PATH = PLAN_ROOT / "measurement-plan-registry-v1.0.0.json"

SURVEY_ROOT = MODULE_ROOT / "source_survey"

ACTIVE_PYTHON_ROOTS = ("pipeline",)

# Blockers every record must keep.  Deleting one would make the package look
# closer to usable than it is, which is the failure this artifact exists to
# prevent.
REQUIRED_BLOCKER_CLASSES = {
    "no_task_or_construct_selected",
    "statistician_absent",
    "no_pilot_variance",
    "professional_governance_absent",
    "no_legal_entity",
    "ethics_review_absent",
}

# Availability values that must rest on named source survey records, and those
# that must not, because there is nothing surveyed for them to rest on.
AVAILABILITY_REQUIRING_SURVEY_BASIS = {
    "no_qualifying_public_source",
    "one_candidate_unresolved",
    "sources_exist_none_lawfully_usable",
}
AVAILABILITY_FORBIDDING_SURVEY_BASIS = {
    "not_surveyed_public_availability_unknown",
    "not_applicable_computational_truth",
}

REQUIRED_GOVERNANCE_LANES = {
    "motor_speech",
    "general_speech",
    "voice",
    "participant_report",
    "controlled_intelligibility",
    "clinical_or_laryngeal_reference",
    "unassigned_requires_governance",
}


def load_json(path: Path):
    return json.loads(path.read_text())


def record_paths():
    """Every construct record on disk, schema and registry excluded."""
    return sorted(
        path
        for path in PLAN_ROOT.glob("*.json")
        if path.name not in {SCHEMA_PATH.name, REGISTRY_PATH.name}
    )


def numeric_locations(node, trail=""):
    """Every place a JSON number appears, as a readable path.

    Booleans are excluded deliberately: ``True`` is an ``int`` subclass in
    Python but is not a quantity.
    """
    found = []
    if isinstance(node, bool):
        return found
    if isinstance(node, (int, float)):
        return [trail or "(root)"]
    if isinstance(node, dict):
        for key, value in node.items():
            found.extend(numeric_locations(value, f"{trail}/{key}" if trail else key))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            found.extend(numeric_locations(value, f"{trail}[{index}]"))
    return found


def survey_source_states():
    """Map each surveyed source id to the two facts this validator needs.

    A source's truth requirement status, its access state and its licence answer
    different questions and must not be conflated.  The one located set carrying
    two independent annotators on rapid syllable material is ``unresolved`` on
    truth adequacy and simultaneously has no public release at all.  The closest
    openly visible intelligibility collection is downloadable and carries no
    licence, so nothing about it has been permitted.  Neither is a candidate for
    anybody, and neither can be recognised from its truth status alone.

    The survey already reaches that combined judgement in its own eligibility
    decision, so this reads that field rather than recomputing it, which keeps
    the two artifacts from drifting apart on the definition.
    """
    states = {}
    if not SURVEY_ROOT.exists():
        return states
    for path in sorted(SURVEY_ROOT.glob("*.json")):
        if path.name in {
            "source-survey-schema-v1.0.0.json",
            "source-survey-registry-v1.0.0.json",
        }:
            continue
        try:
            document = load_json(path)
        except json.JSONDecodeError:
            continue
        source_id = document.get("source_id")
        if not source_id:
            continue
        states[source_id] = {
            "requirement_status": document.get("reference_truth", {}).get(
                "requirement_status"
            ),
            "access_state": document.get("access", {}).get("state"),
            "eligibility_decision": document.get("eligibility", {}).get("decision"),
        }
    return states


# The survey's decision for a source that is openly licensed, obtainable with no
# contact, and still an open question on whether it meets a truth requirement.
OPEN_CANDIDATE_DECISION = "open_but_truth_class_unresolved"


def is_live_candidate(state):
    """A source the survey itself recorded as an open, obtainable candidate."""
    return state is not None and state["eligibility_decision"] == OPEN_CANDIDATE_DECISION


def validate_record(document, schema, filename, survey_states):
    """Schema plus the rules a schema cannot express."""
    errors = []
    validator = Draft202012Validator(schema)
    for error in sorted(validator.iter_errors(document), key=lambda item: item.path):
        location = "/".join(str(part) for part in error.path) or "(root)"
        errors.append(f"{filename}: schema error at {location}: {error.message}")
    if errors:
        # Later rules assume a well formed record.
        return errors

    candidate = document["candidate_id"]

    numbers = numeric_locations(document)
    if numbers:
        errors.append(
            f"{filename}: {candidate} contains a computed quantity at "
            + ", ".join(sorted(numbers))
            + ". This package records inputs, never results, so a bare number is "
            "refused."
        )

    if document["selected"] is not False:
        errors.append(f"{filename}: {candidate} records a selection")

    if document["estimand_shape"]["status"] != "candidate_shape_not_selected":
        errors.append(f"{filename}: {candidate} claims a selected estimand")

    if document["observation"]["claim_level"] != (
        "measured_observation_candidate_not_selected"
    ):
        errors.append(f"{filename}: {candidate} claims a higher claim level")

    sample_size = document["sample_size"]
    if sample_size["computed_value"] is not None:
        errors.append(f"{filename}: {candidate} records a computed sample size")
    if sample_size["state"] != "not_computable_without_the_inputs_above":
        errors.append(
            f"{filename}: {candidate} claims its sample size question is settled"
        )

    if document["agreement_and_reliability"]["measurement_error_required"] is not True:
        errors.append(
            f"{filename}: {candidate} drops the measurement error requirement"
        )

    if document["missingness_and_abstention"]["reported_separately"] is not True:
        errors.append(
            f"{filename}: {candidate} stops reporting abstention separately"
        )

    if document["split_and_clustering"]["minimum_split_unit"] != "participant":
        errors.append(f"{filename}: {candidate} weakens the participant split unit")

    present_blockers = {item["blocker_class"] for item in document["blockers"]}
    missing_blockers = REQUIRED_BLOCKER_CLASSES - present_blockers
    if missing_blockers:
        errors.append(
            f"{filename}: {candidate} dropped required blockers: "
            + ", ".join(sorted(missing_blockers))
        )

    reference = document["reference_requirement"]
    availability = reference["public_availability"]
    basis = reference["source_survey_basis"]

    if availability in AVAILABILITY_REQUIRING_SURVEY_BASIS and not basis:
        errors.append(
            f"{filename}: {candidate} states a surveyed availability outcome "
            "without naming the source survey records it rests on"
        )
    if availability in AVAILABILITY_FORBIDDING_SURVEY_BASIS and basis:
        errors.append(
            f"{filename}: {candidate} cites source survey records while claiming "
            "the question was not surveyed or needs no external source"
        )

    unknown = [source for source in basis if source not in survey_states]
    if unknown:
        errors.append(
            f"{filename}: {candidate} cites sources that are not in the "
            "checkpoint 23B source survey: " + ", ".join(sorted(unknown))
        )

    live = sorted(
        source for source in basis if is_live_candidate(survey_states.get(source))
    )
    if availability == "one_candidate_unresolved" and not live:
        errors.append(
            f"{filename}: {candidate} claims an open candidate while no source it "
            "cites is both an open truth question and obtainable without contact"
        )
    if availability in {
        "no_qualifying_public_source",
        "sources_exist_none_lawfully_usable",
    } and live:
        errors.append(
            f"{filename}: {candidate} claims nothing usable exists while citing a "
            "source the survey recorded as obtainable without contact with its "
            "truth question still open: " + ", ".join(live)
        )

    return errors


def validate_registry(registry, records):
    """The summary must not drift away from the records it summarises."""
    errors = []

    if registry.get("schema_version") != "1.0.0":
        errors.append("registry: unexpected schema version")
    if registry.get("registry_id") != "motor_speech_voice_measurement_plan_v1":
        errors.append("registry: unexpected registry id")
    if registry.get("checkpoint") != "23B":
        errors.append("registry: unexpected checkpoint")
    if registry.get("status") != "measurement_inputs_recorded_nothing_selected":
        errors.append("registry: status no longer records that nothing was selected")

    listed = [entry["candidate_id"] for entry in registry.get("records", [])]
    present = [document["candidate_id"] for document in records]
    if sorted(listed) != sorted(present):
        missing = sorted(set(present) - set(listed))
        extra = sorted(set(listed) - set(present))
        if missing:
            errors.append("registry: records on disk are not listed: " + ", ".join(missing))
        if extra:
            errors.append("registry: listed records do not exist: " + ", ".join(extra))
    if len(listed) != len(set(listed)):
        errors.append("registry: a construct is listed more than once")
    if registry.get("record_count") != len(present):
        errors.append("registry: record count does not match the records on disk")

    by_candidate = {document["candidate_id"]: document for document in records}
    for entry in registry.get("records", []):
        document = by_candidate.get(entry["candidate_id"])
        if document is None:
            continue
        if entry.get("governance_lane") != document["governance_lane"]:
            errors.append(
                f"registry: {entry['candidate_id']} is listed under a different "
                "governance lane than its record"
            )
        if entry.get("public_availability") != document["reference_requirement"][
            "public_availability"
        ]:
            errors.append(
                f"registry: {entry['candidate_id']} is listed with a different "
                "reference availability than its record"
            )

    counts = registry.get("counts", {})
    if counts.get("constructs_recorded") != len(present):
        errors.append("registry: construct count does not match the records on disk")
    for name in ("selected", "sample_sizes_computed", "thresholds_recorded"):
        if counts.get(name) != 0:
            errors.append(f"registry: claims a non zero {name}")

    expected_lanes = {}
    for document in records:
        lane = document["governance_lane"]
        expected_lanes[lane] = expected_lanes.get(lane, 0) + 1
    if counts.get("by_governance_lane") != expected_lanes:
        errors.append("registry: the governance lane counts do not match the records")

    summaries = registry.get("lane_summaries", {})
    missing_lanes = REQUIRED_GOVERNANCE_LANES - set(summaries)
    if missing_lanes:
        errors.append(
            "registry: missing lane summaries: " + ", ".join(sorted(missing_lanes))
        )
    for lane, body in summaries.items():
        for field in ("questions", "reference_position", "consequence"):
            if field not in body or (field != "questions" and not body[field]):
                errors.append(f"registry: lane {lane} is missing {field}")
        listed_questions = set(body.get("questions", []))
        actual_questions = {
            document["candidate_id"]
            for document in records
            if document["governance_lane"] == lane
        }
        if listed_questions != actual_questions:
            errors.append(
                f"registry: lane {lane} lists questions that do not match the "
                "records assigned to it"
            )

    for field in ("method_notes", "what_this_is_not", "limitations"):
        if not registry.get(field):
            errors.append(f"registry: {field} was removed")

    return errors


def committed_data_leakage():
    """Anything in the package directory that is not a JSON record."""
    if not PLAN_ROOT.exists():
        return ["the measurement plan directory is missing"]
    return sorted(
        str(path.relative_to(REPOSITORY_ROOT))
        for path in PLAN_ROOT.rglob("*")
        if path.is_file() and path.suffix != ".json"
    )


def active_pipeline_leakage():
    """The running pipeline must not import or name this material."""
    hits = []
    for root in ACTIVE_PYTHON_ROOTS:
        directory = REPOSITORY_ROOT / root
        if not directory.exists():
            continue
        for path in sorted(directory.rglob("*.py")):
            text = path.read_text(errors="ignore")
            if "measurement_plan" in text or "motor_speech_voice" in text:
                hits.append(str(path.relative_to(REPOSITORY_ROOT)))
    return hits


def validate_plan():
    """Validate every record, the registry and the surrounding boundaries."""
    errors = []
    if not SCHEMA_PATH.exists():
        return [f"missing schema: {SCHEMA_PATH.name}"]
    if not REGISTRY_PATH.exists():
        return [f"missing registry: {REGISTRY_PATH.name}"]

    schema = load_json(SCHEMA_PATH)
    paths = record_paths()
    if not paths:
        return ["the measurement plan contains no records"]

    survey_states = survey_source_states()
    if not survey_states:
        errors.append(
            "the checkpoint 23B source survey is missing, so reference "
            "availability claims cannot be cross checked against it"
        )

    records = []
    for path in paths:
        try:
            document = load_json(path)
        except json.JSONDecodeError as error:
            errors.append(f"{path.name}: is not valid JSON: {error}")
            continue
        records.append(document)
        errors.extend(validate_record(document, schema, path.name, survey_states))

    seen = set()
    for document in records:
        candidate = document.get("candidate_id")
        if candidate in seen:
            errors.append(f"duplicate candidate id across records: {candidate}")
        seen.add(candidate)

    errors.extend(validate_registry(load_json(REGISTRY_PATH), records))

    leaked = committed_data_leakage()
    if leaked:
        errors.append("non record files committed: " + ", ".join(leaked))
    pipeline_hits = active_pipeline_leakage()
    if pipeline_hits:
        errors.append(
            "item 23 measurement material reached the active pipeline: "
            + ", ".join(pipeline_hits)
        )
    return errors
