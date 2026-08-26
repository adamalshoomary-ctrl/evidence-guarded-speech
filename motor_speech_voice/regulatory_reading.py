"""Validate the checkpoint 23B documented Australian regulatory and privacy reading.

The reading records what the public rules appear to say about this project at
three rungs of an intended purpose ladder.  This validator exists to stop it
quietly becoming advice, a determination or an approval, and to stop the
strictest rung being softened later.

It refuses a record that claims to be advice or to create authority, a record
that rests on nothing read at its source, a record that admits uncertainty
without naming what is unresolved, a record whose only named decider is the
owner in a domain where the owner cannot decide, a ladder that does not get
stricter as the claim gets stronger, a ladder whose occupied rung has moved, a
registry that disagrees with its own records, and any import of this material
into the running pipeline.
"""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator


MODULE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = MODULE_ROOT.parent
READING_ROOT = MODULE_ROOT / "regulatory_reading"
SCHEMA_PATH = READING_ROOT / "regulatory-reading-schema-v1.0.0.json"
REGISTRY_PATH = READING_ROOT / "regulatory-reading-registry-v1.0.0.json"

ACTIVE_PYTHON_ROOTS = ("pipeline",)

P1 = "developer_research_only"
P2 = "consumer_communication_coaching"
P3 = "consumer_screening_referral"

# The ladder in order, weakest claim first.
LADDER_ORDER = [P1, P2, P3]

# How exposed each position is, weakest first.  A later rung may never be
# recorded as less exposed than an earlier one.
POSITION_SEVERITY = {
    "likely_outside_the_definition": 0,
    "may_be_a_device_and_may_be_excluded": 1,
    "device_and_no_exclusion_available": 2,
}

# The strongest rung is the one somebody would later be tempted to soften, so
# its position is pinned.
REQUIRED_TOP_RUNG_POSITION = "device_and_no_exclusion_available"

# Domains where the owner alone cannot settle the question, whatever he decides
# about product scope.
DOMAINS_NEEDING_AN_EXTERNAL_DECIDER = {
    "medical_device_regulation",
    "clinical_trial_regulation",
    "privacy",
    "recording_and_surveillance_law",
    "research_ethics",
    "professional_regulation",
}

CONFIDENCE_REQUIRING_UNRESOLVED = {
    "reading_with_material_uncertainty",
    "unresolved_needs_specialist",
}

# Phrases the standing disclaimer must keep.  Losing any of them would change
# what the artifact claims to be.
REQUIRED_DISCLAIMER_PHRASES = [
    "not legal advice",
    "not an Australian regulatory specialist",
    "classification determination",
]


def load_json(path: Path):
    return json.loads(path.read_text())


def record_paths():
    """Every reading record on disk, schema and registry excluded."""
    return sorted(
        path
        for path in READING_ROOT.glob("*.json")
        if path.name not in {SCHEMA_PATH.name, REGISTRY_PATH.name}
    )


def validate_record(document, schema, filename):
    """Schema plus the rules a schema cannot express."""
    errors = []
    validator = Draft202012Validator(schema)
    for error in sorted(validator.iter_errors(document), key=lambda item: item.path):
        location = "/".join(str(part) for part in error.path) or "(root)"
        errors.append(f"{filename}: schema error at {location}: {error.message}")
    if errors:
        return errors

    question = document["question_id"]

    if document["status"] != "documented_reading_not_a_determination":
        errors.append(f"{filename}: {question} claims to be a determination")
    if document["is_legal_or_regulatory_advice"] is not False:
        errors.append(f"{filename}: {question} claims to be advice")
    if document["creates_any_authority"] is not False:
        errors.append(f"{filename}: {question} claims to create authority")

    read_at_source = [
        source for source in document["primary_sources"] if source["read_at_source"]
    ]
    if not read_at_source:
        errors.append(
            f"{filename}: {question} rests on no source that was read directly. A "
            "reading built only on secondary description is not admissible here."
        )

    if (
        document["confidence"] in CONFIDENCE_REQUIRING_UNRESOLVED
        and not document["unresolved"]
    ):
        errors.append(
            f"{filename}: {question} records uncertainty without naming a single "
            "open question"
        )

    deciders = set(document["decided_by"])
    if document["domain"] in DOMAINS_NEEDING_AN_EXTERNAL_DECIDER and deciders <= {
        "owner"
    }:
        errors.append(
            f"{filename}: {question} names the owner as its only decider in a "
            "domain the owner cannot settle"
        )

    for purpose in document["applies_to_purposes"]:
        if purpose not in LADDER_ORDER:
            errors.append(f"{filename}: {question} names an unknown purpose {purpose}")

    return errors


def validate_ladder(ladder):
    """The ladder must stay honest about which rung is occupied and how it rises."""
    errors = []

    missing = set(LADDER_ORDER) - set(ladder)
    if missing:
        errors.append(
            "registry: the purpose ladder is missing rungs: " + ", ".join(sorted(missing))
        )
    unknown = set(ladder) - set(LADDER_ORDER)
    if unknown:
        errors.append(
            "registry: the purpose ladder has unknown rungs: " + ", ".join(sorted(unknown))
        )
    if missing or unknown:
        return errors

    occupied = [name for name, body in ladder.items() if body.get("occupied_today")]
    if occupied != [P1]:
        errors.append(
            "registry: the occupied rung must be the developer research one and "
            "only that one; found " + (", ".join(occupied) if occupied else "none")
        )

    severities = []
    for name in LADDER_ORDER:
        body = ladder[name]
        position = body.get("medical_device_position")
        if position not in POSITION_SEVERITY:
            errors.append(f"registry: rung {name} has an unknown position {position}")
            return errors
        severities.append(POSITION_SEVERITY[position])
        if not body.get("description"):
            errors.append(f"registry: rung {name} is missing its description")
        if not body.get("what_still_applies"):
            errors.append(f"registry: rung {name} lists nothing that still applies")

    if severities != sorted(severities) or len(set(severities)) != len(severities):
        errors.append(
            "registry: the ladder must get strictly stricter as the claim gets "
            "stronger; a later rung is recorded as no more exposed than an "
            "earlier one"
        )

    if ladder[P3].get("medical_device_position") != REQUIRED_TOP_RUNG_POSITION:
        errors.append(
            "registry: the screening rung no longer records that it is a medical "
            "device with no exclusion available"
        )

    return errors


def validate_registry(registry, records):
    """The summary must not drift away from the records it summarises."""
    errors = []

    if registry.get("schema_version") != "1.0.0":
        errors.append("registry: unexpected schema version")
    if registry.get("registry_id") != "motor_speech_voice_regulatory_reading_v1":
        errors.append("registry: unexpected registry id")
    if registry.get("checkpoint") != "23B":
        errors.append("registry: unexpected checkpoint")
    if registry.get("status") != "documented_reading_recorded_no_determination_made":
        errors.append(
            "registry: status no longer records that no determination was made"
        )

    disclaimer = registry.get("standing_disclaimer", "")
    for phrase in REQUIRED_DISCLAIMER_PHRASES:
        if phrase not in disclaimer:
            errors.append(f"registry: the standing disclaimer no longer says {phrase!r}")

    errors.extend(validate_ladder(registry.get("purpose_ladder", {})))

    listed = [entry["question_id"] for entry in registry.get("records", [])]
    present = [document["question_id"] for document in records]
    if sorted(listed) != sorted(present):
        missing = sorted(set(present) - set(listed))
        extra = sorted(set(listed) - set(present))
        if missing:
            errors.append("registry: records on disk are not listed: " + ", ".join(missing))
        if extra:
            errors.append("registry: listed records do not exist: " + ", ".join(extra))
    if len(listed) != len(set(listed)):
        errors.append("registry: a question is listed more than once")
    if registry.get("record_count") != len(present):
        errors.append("registry: record count does not match the records on disk")

    by_question = {document["question_id"]: document for document in records}
    for entry in registry.get("records", []):
        document = by_question.get(entry["question_id"])
        if document is None:
            continue
        if entry.get("domain") != document["domain"]:
            errors.append(
                f"registry: {entry['question_id']} is listed under a different "
                "domain than its record"
            )
        if entry.get("confidence") != document["confidence"]:
            errors.append(
                f"registry: {entry['question_id']} is listed with a different "
                "confidence than its record"
            )

    counts = registry.get("counts", {})
    if counts.get("questions_read") != len(present):
        errors.append("registry: question count does not match the records on disk")
    for name in ("determinations_made", "approvals_obtained", "advice_received"):
        if counts.get(name) != 0:
            errors.append(f"registry: claims a non zero {name}")

    expected_unresolved = sum(len(document["unresolved"]) for document in records)
    if counts.get("open_questions_recorded") != expected_unresolved:
        errors.append("registry: the open question count does not match the records")
    expected_conflicts = sum(len(document["conflicts"]) for document in records)
    if counts.get("source_conflicts_recorded") != expected_conflicts:
        errors.append("registry: the source conflict count does not match the records")

    expected_domains = {}
    expected_confidence = {}
    expected_purposes = {name: 0 for name in LADDER_ORDER}
    for document in records:
        expected_domains[document["domain"]] = (
            expected_domains.get(document["domain"], 0) + 1
        )
        expected_confidence[document["confidence"]] = (
            expected_confidence.get(document["confidence"], 0) + 1
        )
        for purpose in document["applies_to_purposes"]:
            if purpose in expected_purposes:
                expected_purposes[purpose] += 1
    if counts.get("by_domain") != expected_domains:
        errors.append("registry: the domain counts do not match the records")
    if counts.get("by_confidence") != expected_confidence:
        errors.append("registry: the confidence counts do not match the records")
    if counts.get("by_purpose") != expected_purposes:
        errors.append("registry: the purpose counts do not match the records")

    for field in ("what_this_is_not", "limitations"):
        if not registry.get(field):
            errors.append(f"registry: {field} was removed")

    return errors


def committed_data_leakage():
    """Anything in the reading directory that is not a JSON record."""
    if not READING_ROOT.exists():
        return ["the regulatory reading directory is missing"]
    return sorted(
        str(path.relative_to(REPOSITORY_ROOT))
        for path in READING_ROOT.rglob("*")
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
            if "regulatory_reading" in text or "motor_speech_voice" in text:
                hits.append(str(path.relative_to(REPOSITORY_ROOT)))
    return hits


def validate_reading():
    """Validate every record, the registry and the surrounding boundaries."""
    errors = []
    if not SCHEMA_PATH.exists():
        return [f"missing schema: {SCHEMA_PATH.name}"]
    if not REGISTRY_PATH.exists():
        return [f"missing registry: {REGISTRY_PATH.name}"]

    schema = load_json(SCHEMA_PATH)
    paths = record_paths()
    if not paths:
        return ["the regulatory reading contains no records"]

    records = []
    for path in paths:
        try:
            document = load_json(path)
        except json.JSONDecodeError as error:
            errors.append(f"{path.name}: is not valid JSON: {error}")
            continue
        records.append(document)
        errors.extend(validate_record(document, schema, path.name))

    seen = set()
    for document in records:
        question = document.get("question_id")
        if question in seen:
            errors.append(f"duplicate question id across records: {question}")
        seen.add(question)

    errors.extend(validate_registry(load_json(REGISTRY_PATH), records))

    leaked = committed_data_leakage()
    if leaked:
        errors.append("non record files committed: " + ", ".join(leaked))
    pipeline_hits = active_pipeline_leakage()
    if pipeline_hits:
        errors.append(
            "item 23 regulatory material reached the active pipeline: "
            + ", ".join(pipeline_hits)
        )
    return errors
