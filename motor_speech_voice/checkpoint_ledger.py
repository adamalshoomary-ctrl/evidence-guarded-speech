"""Validate the checkpoint 23B deliverable ledger.

The ledger's whole job is to stop a large body of honest public research being
mistaken for progress toward acceptance.  This validator keeps it honest.

It refuses a ledger that has lost a deliverable, that marks the checkpoint
anything other than in progress, that claims a selection, a contact, a spend or
an acquisition, that marks a deliverable complete without evidence that exists
on disk, that marks one partial or blocked without naming who has to finish it,
or that leaves nothing blocked at all, because a checkpoint with nothing blocked
would be one public research could close by itself, and this one cannot be.
"""

from __future__ import annotations

import json
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = MODULE_ROOT.parent
LEDGER_PATH = MODULE_ROOT / "checkpoint-23b-ledger-v1.0.0.json"

COMPLETE = "public_research_complete"
PARTIAL = "public_research_partial"
BLOCKED = "blocked_requires_named_human"
VALID_STATUSES = {COMPLETE, PARTIAL, BLOCKED}

EXPECTED_NUMBERS = [
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
    "thirteen",
]

KNOWN_ROLES = {
    "owner",
    "australian_regulatory_specialist",
    "australian_privacy_lawyer",
    "queensland_lawyer",
    "human_research_ethics_committee_or_review_body",
    "responsible_institution",
    "independent_professional_governance_group",
    "paid_lived_experience_governance_group",
}

REQUIRED_FALSE_FLAGS = (
    "selection_recorded",
    "external_party_contacted",
    "money_spent",
    "data_acquired",
)


def load_json(path: Path):
    return json.loads(path.read_text())


def validate_deliverable(deliverable, index):
    errors = []
    number = deliverable.get("number", f"position {index}")

    for field in ("number", "title", "status", "evidence", "what_remains", "who_supplies_it", "note"):
        if field not in deliverable:
            errors.append(f"deliverable {number}: missing {field}")
    if errors:
        return errors

    status = deliverable["status"]
    if status not in VALID_STATUSES:
        errors.append(f"deliverable {number}: unknown status {status}")
        return errors

    if not deliverable["title"]:
        errors.append(f"deliverable {number}: has no title")
    if not deliverable["what_remains"]:
        errors.append(f"deliverable {number}: does not say what remains")
    if not deliverable["note"]:
        errors.append(f"deliverable {number}: has no note")

    for role in deliverable["who_supplies_it"]:
        if role not in KNOWN_ROLES:
            errors.append(f"deliverable {number}: names an unknown role {role}")

    if status == COMPLETE:
        if not deliverable["evidence"]:
            errors.append(
                f"deliverable {number}: is marked complete with no evidence"
            )
        if deliverable["who_supplies_it"]:
            errors.append(
                f"deliverable {number}: is marked complete while still naming "
                "someone who has to supply it"
            )
    else:
        if not deliverable["who_supplies_it"]:
            errors.append(
                f"deliverable {number}: is not complete and names nobody who has "
                "to finish it"
            )

    for path in deliverable["evidence"]:
        if not (REPOSITORY_ROOT / path).exists():
            errors.append(
                f"deliverable {number}: cites evidence that does not exist: {path}"
            )

    return errors


def validate_ledger():
    errors = []
    if not LEDGER_PATH.exists():
        return [f"missing ledger: {LEDGER_PATH.name}"]

    try:
        ledger = load_json(LEDGER_PATH)
    except json.JSONDecodeError as error:
        return [f"{LEDGER_PATH.name}: is not valid JSON: {error}"]

    if ledger.get("schema_version") != "1.0.0":
        errors.append("ledger: unexpected schema version")
    if ledger.get("ledger_id") != "motor_speech_voice_checkpoint_23b_ledger_v1":
        errors.append("ledger: unexpected ledger id")
    if ledger.get("checkpoint") != "23B":
        errors.append("ledger: unexpected checkpoint")
    if ledger.get("checkpoint_status") != "in_progress":
        errors.append(
            "ledger: the checkpoint is no longer recorded as in progress"
        )

    for flag in REQUIRED_FALSE_FLAGS:
        if ledger.get(flag) is not False:
            errors.append(f"ledger: {flag} is no longer false")

    deliverables = ledger.get("deliverables", [])
    if len(deliverables) != len(EXPECTED_NUMBERS):
        errors.append(
            f"ledger: expected {len(EXPECTED_NUMBERS)} deliverables, found "
            f"{len(deliverables)}"
        )
    if ledger.get("deliverable_count") != len(deliverables):
        errors.append("ledger: deliverable count does not match the list")

    numbers = [item.get("number") for item in deliverables]
    if numbers != EXPECTED_NUMBERS:
        errors.append(
            "ledger: the deliverables are not the thirteen the checkpoint lists, "
            "in order"
        )

    for index, deliverable in enumerate(deliverables):
        errors.extend(validate_deliverable(deliverable, index))

    statuses = [item.get("status") for item in deliverables]
    if BLOCKED not in statuses:
        errors.append(
            "ledger: nothing is blocked, which would mean public research could "
            "close this checkpoint by itself. It cannot."
        )

    expected_counts = {}
    for status in statuses:
        if status in VALID_STATUSES:
            expected_counts[status] = expected_counts.get(status, 0) + 1
    if ledger.get("counts") != expected_counts:
        errors.append("ledger: the counts do not match the deliverables")

    if not ledger.get("acceptance_rule"):
        errors.append("ledger: the acceptance rule was removed")
    elif "written review" not in ledger["acceptance_rule"]:
        errors.append(
            "ledger: the acceptance rule no longer says acceptance is written "
            "review"
        )
    if not ledger.get("what_public_research_changed"):
        errors.append("ledger: what public research changed was removed")

    return errors
