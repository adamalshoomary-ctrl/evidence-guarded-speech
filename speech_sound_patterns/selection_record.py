"""The checkpoint 22E5 selection and rejection record.

Checkpoints 22E1 through 22E4B asked whether any candidate system can decide,
reliably enough to build on, that a person produced a particular expected
consonant. Two frozen comparisons answered no. This module holds the record of
what was decided about every lane as a result, and refuses to let that record
drift.

Three properties make the record trustworthy rather than a summary:

1. Every lane in the fail-closed provider register must appear exactly once,
   with a decision this module pins in code. Changing a verdict therefore
   requires a code change and a test change, exactly like promoting a lane in
   the register.
2. A verdict cannot contradict the lane's register status. Nothing conditional,
   blocked, declined or rejected can be recorded as selected or carried into
   later research.
3. ``selected_candidate`` is only reachable when the committed powered
   comparison actually reports a candidate on that lane passing every unchanged
   gate on both partitions. No candidate does, so the recorded decision is
   ``no_selection`` and this module cannot be talked out of it by editing the
   record alone: the evidence files are pinned by hash.

The record is an aggregate. Row level evidence, provider responses, private
paths and the prohibited overall provider scores are rejected here exactly as
they are in the comparison reports.

The record is issued once per state of the evidence it rests on. Checkpoint
22E6 corrected the provider register, which correctly invalidated the record
that pinned the old one, so version 1.1.0 restates the same decision against
the corrected register while version 1.0.0 stays on disk unedited. No verdict
moved between them.
"""

from __future__ import annotations

import json
from pathlib import Path

from .comparison import (
    CANDIDATE_PROFILES,
    FORBIDDEN_REPORT_KEYS,
    FROZEN_SELECTION_GATES,
    PROHIBITED_PROVIDER_SCORES,
    RELEASE_BOUNDARIES,
    comparison_profile,
)
from .feasibility import REPOSITORY_ROOT, file_sha256
from .provider_register import REGISTER_PATH, REGISTER_ROOT, REQUIRED_LANE_IDS

MODULE_ROOT = Path(__file__).resolve().parent

SELECTION_SCHEMA_VERSION = "1.0.0"

# The record is issued once per state of the evidence it depends on. Version
# 1.0.0 is the checkpoint 22E5 decision as written against the register of that
# day. Version 1.1.0 restates the same decision against the register checkpoint
# 22E6 corrected: no verdict moved, and the Bookbot reason changed from an
# undocumented training source to a disproved one. Both stay on disk and both
# stay valid, each pinned to the register it was actually written against.
SELECTION_VERSIONS = {
    "1.0.0": {
        "checkpoint": "22E5",
        "record_path": MODULE_ROOT / "selection-record-v1.0.0.json",
        "register_path": REGISTER_ROOT / "provider-register-v1.1.0.json",
        "next_checkpoint": (
            "22F_conservative_research_prompt_pack_after_owner_commit"
        ),
    },
    "1.1.0": {
        "checkpoint": "22E6",
        "record_path": MODULE_ROOT / "selection-record-v1.1.0.json",
        "register_path": REGISTER_PATH,
        "next_checkpoint": "22E7_acquire_the_open_stack_after_owner_commit",
    },
}

ACTIVE_SELECTION_VERSION = "1.1.0"


def selection_profile(version=ACTIVE_SELECTION_VERSION):
    """Return the identity and evidence paths for one record version."""
    profile = SELECTION_VERSIONS.get(version)
    if profile is None:
        raise SelectionRecordError(f"unknown selection record version: {version!r}")
    return profile


SELECTION_RECORD_PATH = SELECTION_VERSIONS[ACTIVE_SELECTION_VERSION]["record_path"]

# The checkpoint 22D repair is the local baseline every later lane is measured
# against for incremental value. Its closest operating point passed nine of ten
# checks and still selected nothing.
BASELINE_REPORT_PATH = MODULE_ROOT / "local-benchmark-repair-v1.0.0.json"
BASELINE_CANDIDATE_ID = "meta_wav2vec2_constrained_contextual"
BASELINE_GATE_CHECKS_PASSED_OF_TEN = 9


def pinned_evidence(version=ACTIVE_SELECTION_VERSION):
    """Every file whose content the record depends on.

    A record that no longer matches the evidence it cites is invalid, so an
    edit to any report or to the register cannot silently leave a stale verdict
    standing. The register differs by version, because each record was written
    against the register of its own day.
    """
    return {
        "provider_register": selection_profile(version)["register_path"],
        "frozen_comparison_22e4": comparison_profile("1.0.0")["report_path"],
        "frozen_comparison_22e4b": comparison_profile("1.1.0")["report_path"],
        "local_benchmark_22d": MODULE_ROOT / "local-benchmark-v1.0.0.json",
        "local_benchmark_repair_22d": BASELINE_REPORT_PATH,
    }


# The five verdicts the engineering plan permits at this checkpoint.
DECISIONS = {
    "selected_candidate",
    "supporting_only",
    "research_only",
    "blocked",
    "rejected",
}

# Why a verdict was reached. Kept separate from the verdict itself so a lane
# rejected on measured evidence is never confused with one blocked by somebody
# else's rights, and so the record shows how many lanes were actually measured.
DECISION_BASES = {
    "measured_evidence",
    "access_or_permission",
    "provider_terms",
    "owner_decision",
    "source_overlap",
    "not_a_detector",
    "unobtainable",
}

MEASURED_BASES = {"measured_evidence"}

# A verdict may never contradict the register. The register is the fail-closed
# authority on what each lane is permitted to be; this record decides only what
# was done with that permission.
DECISIONS_ALLOWED_BY_REGISTER_STATUS = {
    "ready": {"selected_candidate", "research_only", "supporting_only", "rejected"},
    "conditional": {"blocked", "rejected"},
    "blocked": {"blocked", "rejected"},
    "supporting_only": {"supporting_only", "rejected"},
    "rejected": {"rejected"},
    "owner_declined": {"blocked", "rejected"},
}

# The decision for every lane, pinned so the record cannot be rewritten without
# a code change. Each entry states the verdict, why it was reached, and whether
# the lane may still be reopened by new evidence or a new permission.
LANE_DECISION_PROFILES = {
    "azure_speech": {
        "decision": "rejected",
        "basis": "measured_evidence",
        "reopenable": True,
    },
    "elsa_scripted_v3": {
        "decision": "blocked",
        "basis": "access_or_permission",
        "reopenable": True,
    },
    "iflytek_ise_global": {
        "decision": "rejected",
        "basis": "owner_decision",
        "reopenable": True,
    },
    "segmentation_free_gop": {
        "decision": "research_only",
        "basis": "measured_evidence",
        "reopenable": True,
    },
    "powsm": {
        "decision": "rejected",
        "basis": "measured_evidence",
        "reopenable": True,
    },
    "zipa": {
        "decision": "blocked",
        "basis": "access_or_permission",
        "reopenable": True,
    },
    "wav2vec2_commonphone": {
        "decision": "supporting_only",
        "basis": "source_overlap",
        "reopenable": False,
    },
    "unsw_speech_attributes": {
        "decision": "blocked",
        "basis": "access_or_permission",
        "reopenable": True,
    },
    "child_phoneme_model": {
        "decision": "blocked",
        "basis": "access_or_permission",
        "reopenable": True,
    },
    "auskidtalk": {
        "decision": "blocked",
        "basis": "access_or_permission",
        "reopenable": True,
    },
    "bookbot_au_g2p": {
        "decision": "blocked",
        "basis": "not_a_detector",
        "reopenable": True,
    },
    "soapbox": {
        "decision": "rejected",
        "basis": "unobtainable",
        "reopenable": True,
    },
    "speechace": {
        "decision": "blocked",
        "basis": "provider_terms",
        "reopenable": True,
    },
    "speechsuper": {
        "decision": "rejected",
        "basis": "provider_terms",
        "reopenable": True,
    },
}

# Every limitation class the checkpoint requires for every lane. A missing or
# empty class is an error, because "not recorded" is how a limitation quietly
# disappears.
REQUIRED_LIMITATION_CLASSES = (
    "cost",
    "privacy",
    "legal",
    "operational",
    "australian_variety",
    "child_and_adult",
)

RECORD_FIELDS = frozenset(
    {
        "schema_version",
        "record_id",
        "record_version",
        "checkpoint",
        "status",
        "purpose",
        "evidence_sources",
        "selection_gates",
        "measured_candidate_outcomes",
        "lanes",
        "decision",
        "frozen_for_later_checkpoints",
        "limitations",
        "release_boundaries",
        "next_checkpoint",
    }
)

LANE_FIELDS = frozenset(
    {
        "lane_id",
        "display_name",
        "kind",
        "register_role",
        "register_status",
        "audio_policy",
        "decision",
        "decision_basis",
        "reason",
        "incremental_value_beyond_22d_baseline",
        "limitations",
        "blocked_pending",
        "reopen_requires",
    }
)

RECORD_STATUS = "selection_record_complete_release_locked"


class SelectionRecordError(RuntimeError):
    """Raised when the checkpoint 22E5 record cannot be trusted."""


def _load_json(path):
    path = Path(path)
    if not path.is_file():
        raise SelectionRecordError(f"selection evidence is missing: {path.name}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_selection_record(path=None, version=ACTIVE_SELECTION_VERSION):
    if path is None:
        path = selection_profile(version)["record_path"]
    return _load_json(path)


def evidence_pins(version=ACTIVE_SELECTION_VERSION):
    """Hash every file the record depends on, as it stands on disk now."""
    return {
        name: {
            "path": path.resolve().relative_to(REPOSITORY_ROOT).as_posix(),
            "sha256": file_sha256(path),
        }
        for name, path in sorted(pinned_evidence(version).items())
    }


def gate_eligible_lane_ids():
    """Lanes that had at least one candidate measured against the gates."""
    return {
        profile["lane_id"]
        for profile in CANDIDATE_PROFILES.values()
        if profile["selection_eligible"]
    }


def _passing_lane_ids(comparison_report):
    passing = set()
    for candidate in comparison_report.get("candidates", []):
        profile = CANDIDATE_PROFILES.get(candidate.get("candidate_id"))
        if profile is None or not profile["selection_eligible"]:
            continue
        if candidate.get("any_operating_point_passes_both_partitions") is True:
            passing.add(profile["lane_id"])
    return passing


def _lane_errors(lane, register_lane, passing_lane_ids, measured_lane_ids):
    lane_id = lane["lane_id"]
    errors = []

    if set(lane) != LANE_FIELDS:
        errors.append(f"{lane_id}: lane fields do not match the record schema")
        if not LANE_FIELDS.issubset(lane):
            return errors

    profile = LANE_DECISION_PROFILES[lane_id]
    if lane["decision"] != profile["decision"]:
        errors.append(
            f"{lane_id}: decision is {lane['decision']!r} but the committed "
            f"checkpoint 22E5 verdict is {profile['decision']!r}"
        )
    if lane["decision_basis"] != profile["basis"]:
        errors.append(
            f"{lane_id}: decision basis is {lane['decision_basis']!r} but the "
            f"committed verdict rests on {profile['basis']!r}"
        )
    if lane["decision"] not in DECISIONS:
        errors.append(f"{lane_id}: {lane['decision']!r} is not a permitted verdict")
    if lane["decision_basis"] not in DECISION_BASES:
        errors.append(
            f"{lane_id}: {lane['decision_basis']!r} is not a permitted basis"
        )

    for field in ("kind", "audio_policy"):
        if lane[field] != register_lane[field]:
            errors.append(f"{lane_id}: {field} disagrees with the provider register")
    if lane["register_role"] != register_lane["role"]:
        errors.append(f"{lane_id}: register_role disagrees with the provider register")
    if lane["register_status"] != register_lane["status"]:
        errors.append(
            f"{lane_id}: register_status disagrees with the provider register"
        )
    if lane["blocked_pending"] != register_lane["blocked_pending"]:
        errors.append(
            f"{lane_id}: blocked_pending disagrees with the provider register"
        )

    allowed = DECISIONS_ALLOWED_BY_REGISTER_STATUS.get(lane["register_status"], set())
    if lane["decision"] not in allowed:
        errors.append(
            f"{lane_id}: a lane whose register status is "
            f"{lane['register_status']!r} cannot be recorded as "
            f"{lane['decision']!r}"
        )

    if lane["decision"] == "selected_candidate" and lane_id not in passing_lane_ids:
        errors.append(
            f"{lane_id}: cannot be selected because no candidate on this lane "
            "passes every unchanged gate on both partitions"
        )

    if lane["decision_basis"] in MEASURED_BASES and lane_id not in measured_lane_ids:
        errors.append(
            f"{lane_id}: claims a measured basis but no gate eligible candidate "
            "ran on this lane"
        )

    if len(lane["reason"]) < 40:
        errors.append(f"{lane_id}: the written reason is too short to be a record")

    value = lane["incremental_value_beyond_22d_baseline"]
    if set(value) != {"measured", "summary", "gate_checks_passed_of_ten"}:
        errors.append(f"{lane_id}: incremental value fields do not match the schema")
    else:
        if value["measured"] is not (lane_id in measured_lane_ids):
            errors.append(
                f"{lane_id}: incremental value claims measured="
                f"{value['measured']} which the comparison does not support"
            )
        if value["measured"] is False and value["gate_checks_passed_of_ten"] is not (
            None
        ):
            errors.append(
                f"{lane_id}: an unmeasured lane cannot report a gate check count"
            )
        if not value["summary"]:
            errors.append(f"{lane_id}: incremental value needs a written summary")

    limitations = lane["limitations"]
    if set(limitations) != set(REQUIRED_LIMITATION_CLASSES):
        errors.append(
            f"{lane_id}: every limitation class must be recorded: "
            + ", ".join(REQUIRED_LIMITATION_CLASSES)
        )
    else:
        for name, text in sorted(limitations.items()):
            if not isinstance(text, str) or len(text) < 10:
                errors.append(f"{lane_id}: the {name} limitation is not recorded")

    if lane["blocked_pending"] and not lane["reopen_requires"]:
        errors.append(
            f"{lane_id}: a lane with outstanding blockers must say what would "
            "reopen it"
        )
    if profile["reopenable"] and not lane["reopen_requires"]:
        errors.append(f"{lane_id}: this verdict is reopenable but says nothing reopens it")
    if not profile["reopenable"] and lane["reopen_requires"]:
        errors.append(
            f"{lane_id}: this verdict is a permanent role and cannot list reopening "
            "conditions"
        )

    return errors


def validate_selection_record(document, register=None, comparisons=None):
    """Return every structural, consistency or safety error in the record.

    ``register`` and ``comparisons`` are read from disk unless supplied, so a
    test can prove the record fails closed against an altered input without
    touching a committed file.
    """
    if not isinstance(document, dict):
        return ["selection record must be an object"]

    errors = []
    if set(document) != RECORD_FIELDS:
        errors.append("selection record fields do not match the schema")
        if not RECORD_FIELDS.issubset(document):
            return errors

    if document["schema_version"] != SELECTION_SCHEMA_VERSION:
        errors.append("selection record schema is unsupported")
    if document["record_id"] != "speech_sound_selection_record":
        errors.append("selection record identity changed")
    if document["status"] != RECORD_STATUS:
        errors.append("the selection record must remain release locked")

    version = document["record_version"]
    profile = SELECTION_VERSIONS.get(version)
    if profile is None:
        errors.append(
            f"selection record version {version!r} is not a version this code "
            "issued; a record cannot introduce itself"
        )
        return errors
    if document["checkpoint"] != profile["checkpoint"]:
        errors.append(
            f"a version {version} selection record was written at checkpoint "
            f"{profile['checkpoint']}"
        )

    if register is None:
        register = _load_json(profile["register_path"])
    if comparisons is None:
        comparisons = {
            "1.0.0": _load_json(comparison_profile("1.0.0")["report_path"]),
            "1.1.0": _load_json(comparison_profile("1.1.0")["report_path"]),
        }

    # The record is only meaningful beside the evidence it was written from.
    pins = document["evidence_sources"]
    if set(pins) != set(pinned_evidence(version)):
        errors.append("the record must pin exactly the evidence it depends on")
    else:
        for name, actual in sorted(evidence_pins(version).items()):
            pinned = pins[name]
            if pinned.get("sha256") != actual["sha256"]:
                errors.append(
                    f"{name} has changed since the selection record was written; "
                    "the record and its evidence no longer agree"
                )
            if pinned.get("path") != actual["path"]:
                errors.append(f"{name} is pinned at the wrong path")

    gates = document["selection_gates"]
    for field, expected in FROZEN_SELECTION_GATES.items():
        if gates.get(field) != expected:
            errors.append(f"selection_gates.{field} changed")
    if gates.get("development_and_tuning_both_required") is not True:
        errors.append("both partitions must still be required")
    if gates.get("inherited_unchanged_from_checkpoint_22d") is not True:
        errors.append("the record must state that the gates were inherited unchanged")
    if gates.get("changed_in_this_checkpoint") is not False:
        errors.append("checkpoint 22E5 records verdicts; it cannot move a gate")

    passing_lane_ids = _passing_lane_ids(comparisons["1.1.0"]) | _passing_lane_ids(
        comparisons["1.0.0"]
    )
    measured_lane_ids = gate_eligible_lane_ids()

    outcomes = document["measured_candidate_outcomes"]
    reported = {outcome.get("candidate_id") for outcome in outcomes}
    if reported != set(CANDIDATE_PROFILES):
        errors.append("every measured candidate must appear in the record")
    powered = {
        candidate["candidate_id"]: candidate
        for candidate in comparisons["1.1.0"]["candidates"]
    }
    for outcome in outcomes:
        candidate_id = outcome.get("candidate_id")
        candidate = powered.get(candidate_id)
        if candidate is None:
            continue
        point = candidate.get("reported_operating_point") or {}
        expected = {
            "candidate_id": candidate_id,
            "lane_id": candidate["lane_id"],
            "selection_eligible": candidate["selection_eligible"],
            "evidence_available": candidate["evidence_available"],
            "passes_every_unchanged_gate": candidate.get(
                "any_operating_point_passes_both_partitions"
            ),
            "gate_checks_passed_of_ten": point.get("gate_checks_passed_of_ten"),
        }
        for field, value in sorted(expected.items()):
            if outcome.get(field) != value:
                errors.append(
                    f"{candidate_id}: {field} does not match the committed powered "
                    "comparison"
                )

    lanes = {lane.get("lane_id"): lane for lane in document["lanes"]}
    if len(lanes) != len(document["lanes"]):
        errors.append("duplicate lane entries are forbidden")
    register_lanes = {lane["lane_id"]: lane for lane in register["lanes"]}
    missing = REQUIRED_LANE_IDS - set(lanes)
    if missing:
        errors.append(
            "the record is missing a decision for: " + ", ".join(sorted(missing))
        )
    unknown = set(lanes) - REQUIRED_LANE_IDS
    if unknown:
        errors.append(
            "the record decides lanes outside the register: "
            + ", ".join(sorted(unknown))
        )
    for lane_id in sorted(set(lanes) & REQUIRED_LANE_IDS & set(register_lanes)):
        errors.extend(
            _lane_errors(
                lanes[lane_id],
                register_lanes[lane_id],
                passing_lane_ids,
                measured_lane_ids,
            )
        )

    decision = document["decision"]
    selected = sorted(
        lane_id
        for lane_id, lane in lanes.items()
        if lane.get("decision") == "selected_candidate"
    )
    if sorted(decision.get("selected_lane_ids", [])) != selected:
        errors.append("the overall decision does not match the per lane verdicts")
    if not selected and decision.get("decision") != "no_selection":
        errors.append("no lane was selected, so the decision must be no_selection")
    if selected and decision.get("decision") != "selection_recorded":
        errors.append("a selected lane must be reported as a selection")
    if decision.get("no_selection_is_a_valid_completed_outcome") is not True:
        errors.append("a documented no-selection must remain a valid outcome")
    for field in (
        "gates_changed_in_this_checkpoint",
        "further_threshold_search_authorised",
        "remote_provider_required",
        "australian_variety_exact_relation_evidence_available",
        "children_supported",
        "held_out_set_accessed",
    ):
        if decision.get(field) is not False:
            errors.append(f"decision.{field} must remain false")
    if decision.get("local_only_decision_permitted") is not True:
        errors.append("a local only outcome must remain permitted")
    if len(decision.get("reason", "")) < 40:
        errors.append("the overall decision needs a written reason")

    frozen = document["frozen_for_later_checkpoints"]
    required_frozen = {
        "selected_mapping",
        "selected_feature",
        "selected_threshold",
        "selected_provider_configuration",
        "carried_forward",
        "not_carried_forward",
    }
    if set(frozen) != required_frozen:
        errors.append("the freeze block fields do not match the schema")
    else:
        if not selected:
            for field in (
                "selected_mapping",
                "selected_feature",
                "selected_threshold",
                "selected_provider_configuration",
            ):
                if frozen[field] is not None:
                    errors.append(
                        f"frozen_for_later_checkpoints.{field} must be null when "
                        "nothing was selected"
                    )
        if not frozen["carried_forward"] or not frozen["not_carried_forward"]:
            errors.append(
                "the freeze block must say what is carried forward and what is not"
            )

    if not document["limitations"]:
        errors.append("the record must carry its limitations")

    boundaries = document["release_boundaries"]
    if set(boundaries) != RELEASE_BOUNDARIES or any(
        boundaries.get(field) is not False for field in RELEASE_BOUNDARIES
    ):
        errors.append("every release boundary must remain false")

    if document["next_checkpoint"] != profile["next_checkpoint"]:
        errors.append("the next checkpoint bypasses owner approval")

    serialized = json.dumps(document, ensure_ascii=False)
    for key in sorted(PROHIBITED_PROVIDER_SCORES):
        if key in serialized:
            errors.append(f"{key} is a prohibited output class and cannot be recorded")

    def inspect(value):
        if isinstance(value, dict):
            if FORBIDDEN_REPORT_KEYS & set(value):
                return False
            return all(inspect(item) for item in value.values())
        if isinstance(value, list):
            return all(inspect(item) for item in value)
        return True

    if not inspect(document):
        errors.append("the selection record contains private or row level evidence")

    return errors


def assert_valid_selection_record(document=None):
    if document is None:
        document = load_selection_record()
    errors = validate_selection_record(document)
    if errors:
        raise SelectionRecordError(
            "checkpoint 22E5 selection record failed fail-closed validation:\n- "
            + "\n- ".join(errors)
        )


def lane_decision(lane_id, document=None):
    """Return one lane's recorded verdict, failing closed on any error."""
    if document is None:
        document = load_selection_record()
    assert_valid_selection_record(document)
    for lane in document["lanes"]:
        if lane["lane_id"] == lane_id:
            return lane["decision"]
    raise SelectionRecordError(f"lane {lane_id!r} has no checkpoint 22E5 decision")


def selected_lane_ids(document=None):
    """Lanes selected for later checkpoints. Empty is the committed outcome."""
    if document is None:
        document = load_selection_record()
    assert_valid_selection_record(document)
    return list(document["decision"]["selected_lane_ids"])
