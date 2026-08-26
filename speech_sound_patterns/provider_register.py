"""Load and validate the checkpoint 22E provider, model and acquisition
lane register.

The register is the fail-closed authority for which candidate systems may be
implemented, credentialed or sent audio during checkpoint 22E. A lane whose
status, permissions, lineage or audio policy is unknown, weakened or missing
is an error, never a default allowance. Secrets never appear in the register;
credentials are referenced only by gitignored ``.env`` variable name.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from jsonschema import Draft202012Validator

from speech_sound_patterns.corpus_manifest import (
    REQUIRED_SOURCE_IDS,
    SOURCE_PROFILES,
)


PACKAGE_ROOT = Path(__file__).resolve().parent
REGISTER_ROOT = PACKAGE_ROOT / "provider_register"
REGISTER_PATH = REGISTER_ROOT / "provider-register-v1.2.0.json"
SCHEMA_PATH = REGISTER_ROOT / "provider-register-schema-v1.2.0.json"

SCHEMA_VERSION = "1.2.0"

# Earlier registers stay on disk exactly as committed. Each is the frozen record
# of what was known at its own checkpoint, and the tests keep every one valid
# against its own schema so a later edit cannot quietly rewrite that history.
HISTORICAL_REGISTERS = {
    "1.0.0": (
        REGISTER_ROOT / "provider-register-v1.0.0.json",
        REGISTER_ROOT / "provider-register-schema-v1.0.0.json",
    ),
    "1.1.0": (
        REGISTER_ROOT / "provider-register-v1.1.0.json",
        REGISTER_ROOT / "provider-register-schema-v1.1.0.json",
    ),
}

# Which checkpoint wrote each register version. Checked by the tests so a
# historical file cannot be relabelled.
HISTORICAL_REGISTER_CHECKPOINTS = {
    "1.0.0": "22E1",
    "1.1.0": "22E3",
}

EXTERNAL_STATUSES_ALLOWED_AUDIO = {"ready"}
STATUSES_REQUIRING_BLOCKERS = {"conditional", "blocked", "owner_declined"}
SECRET_LIKE = re.compile(r"^(?=.*\d)[A-Za-z0-9+/=]{24,}$")
SECRET_KEY_NAMES = {"value", "secret", "token", "password", "api_key", "key"}
REVISION_KEYS = {"revision"}

# Sources whose manifests block provider transfer may never be eligible for
# any external lane.
TRANSFER_BLOCKED_SOURCES = {
    source_id
    for source_id, profile in SOURCE_PROFILES.items()
    if profile.get("provider_transfer") == "blocked"
}

# How well a lane's training-data claim is supported. Checkpoint 22E6 added
# ``disproved`` because the Bookbot lane named a WikiPron Australian dataset
# that does not exist, and "unverified" made that read like unfinished homework
# rather than a closed question.
TRAINING_DATA_CLAIM_STATES = {
    "documented",
    "unverified",
    "disproved",
    "not_applicable",
}

# Standing owner decisions the register must keep. Dropping one would let a
# later agent propose work the owner has already declined.
REQUIRED_OWNER_DECISION_IDS = {
    "no_acquisition_enquiries",
    "no_isle_purchase",
    "openly_licensed_sources_only",
}

REQUIRED_REJECTION_CANDIDATE_KEYWORDS = (
    "multimodal",
    "Google Cloud",
    "AWS",
    "MMS",
    "Allosaurus",
    "L2-ARCTIC",
    "Language Confidence",
)

# The approved role-based comparison, frozen by the revised engineering plan.
# Every entry pins the expected role, status and audio policy; the register
# cannot silently promote, demote or re-purpose a lane.
LANE_PROFILES = {
    "azure_speech": {
        "kind": "external_api",
        "role": "core_external_score_comparator",
        "status": "ready",
        "audio_policy": "corpus_transfer_review_required",
        "benchmark_publication": "permitted_by_public_terms",
        "env_var_names": {
            "AZURE_SPEECH_KEY",
            "AZURE_SPEECH_REGION",
            "AZURE_SPEECH_ENDPOINT",
        },
        "requires_verified_credential": True,
        "requires_privacy": True,
    },
    "elsa_scripted_v3": {
        "kind": "external_api",
        "role": "conditional_external_exact_substitution",
        "status": "conditional",
        "audio_policy": "corpus_transfer_review_required",
        "benchmark_publication": "written_permission_required",
        "env_var_names": {"ELSA_API_TOKEN"},
        "requires_verified_credential": False,
        "requires_privacy": True,
    },
    # Adam declined this lane on 2026-07-25, before checkpoint 22E3 sent any
    # audio anywhere. The decline is pinned here so the lane cannot drift back
    # to ready without an explicit owner decision and a code change.
    "iflytek_ise_global": {
        "kind": "external_api",
        "role": "experimental_public_corpus_comparator",
        "status": "owner_declined",
        "audio_policy": "blocked",
        "benchmark_publication": "permitted_by_public_terms",
        "env_var_names": {
            "IFLYTEK_APP_ID",
            "IFLYTEK_API_KEY",
            "IFLYTEK_API_SECRET",
        },
        "requires_verified_credential": True,
        "requires_privacy": True,
    },
    "segmentation_free_gop": {
        "kind": "local_method",
        "role": "core_local_repair",
        "status": "ready",
        "audio_policy": "no_audio",
        "benchmark_publication": "not_applicable_local",
        "requires_lineage": True,
        "training_data_claim_state": "documented",
        "required_prohibited_keywords": ("frank613", "GOPT"),
    },
    "powsm": {
        "kind": "local_model",
        "role": "core_local_free_phone_comparator",
        "status": "ready",
        "audio_policy": "no_audio",
        "benchmark_publication": "not_applicable_local",
        "requires_lineage": True,
        "training_data_claim_state": "documented",
        "required_prohibited_keywords": ("ZIPA", "IPAPack"),
    },
    "zipa": {
        "kind": "local_model",
        "role": "conditional_local_free_phone",
        "status": "conditional",
        "audio_policy": "no_audio",
        "benchmark_publication": "not_applicable_local",
        "requires_lineage": True,
        "training_data_claim_state": "documented",
        "required_prohibited_keywords": ("loading", "POWSM"),
    },
    "wav2vec2_commonphone": {
        "kind": "local_model",
        "role": "supporting_only_local_comparator",
        "status": "supporting_only",
        "audio_policy": "no_audio",
        "benchmark_publication": "not_applicable_local",
        "requires_lineage": True,
        "training_data_claim_state": "documented",
        "required_non_independent_sources": {
            "common_phone_1_0",
            "common_voice_26_australian_english",
        },
        "required_prohibited_keywords": ("selection gates",),
    },
    "unsw_speech_attributes": {
        "kind": "local_model",
        "role": "research_only_articulatory",
        "status": "blocked",
        "audio_policy": "no_audio",
        "benchmark_publication": "not_applicable_local",
        "requires_lineage": True,
        "training_data_claim_state": "unverified",
        "required_prohibited_keywords": ("licence", "truth"),
    },
    "child_phoneme_model": {
        "kind": "local_model",
        "role": "conditional_child_feasibility",
        "status": "blocked",
        "audio_policy": "no_audio",
        "benchmark_publication": "not_applicable_local",
        "requires_lineage": True,
        "training_data_claim_state": "documented",
        "required_prohibited_keywords": ("OpenRAIL", "child validity"),
    },
    "auskidtalk": {
        "kind": "acquisition_path",
        "role": "australian_child_acquisition_collaboration",
        "status": "conditional",
        "audio_policy": "no_audio",
        "benchmark_publication": "written_permission_required",
    },
    "bookbot_au_g2p": {
        "kind": "local_model",
        "role": "conditional_prompt_target_support",
        "status": "conditional",
        "audio_policy": "no_audio",
        "benchmark_publication": "not_applicable_local",
        "requires_lineage": True,
        "training_data_claim_state": "disproved",
        "required_prohibited_keywords": ("truth",),
    },
    "soapbox": {
        "kind": "external_api",
        "role": "rejected_unobtainable",
        "status": "rejected",
        "audio_policy": "blocked",
        "benchmark_publication": "prohibited_without_waiver",
    },
    "speechace": {
        "kind": "external_api",
        "role": "conditional_reserve",
        "status": "blocked",
        "audio_policy": "blocked",
        "benchmark_publication": "prohibited_without_waiver",
    },
    "speechsuper": {
        "kind": "external_api",
        "role": "rejected_by_terms",
        "status": "rejected",
        "audio_policy": "blocked",
        "benchmark_publication": "prohibited_without_waiver",
    },
}

REQUIRED_LANE_IDS = set(LANE_PROFILES)


class ProviderRegisterValidationError(RuntimeError):
    """Raised when the provider register cannot be trusted."""


def _load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_register():
    return _load_json(REGISTER_PATH)


def _schema_validator() -> Draft202012Validator:
    return Draft202012Validator(_load_json(SCHEMA_PATH))


def _iter_strings(node, key=None):
    if isinstance(node, dict):
        for child_key, value in node.items():
            yield from _iter_strings(value, child_key)
    elif isinstance(node, list):
        for value in node:
            yield from _iter_strings(value, key)
    elif isinstance(node, str):
        yield key, node


def _secret_scan(register) -> list[str]:
    errors = []
    for key, value in _iter_strings(register):
        if key in REVISION_KEYS:
            continue
        if key in SECRET_KEY_NAMES:
            errors.append(
                f"field named {key!r} may hold a secret value and is forbidden"
            )
            continue
        for token in value.split():
            if "://" in token or "/" in token:
                continue
            if SECRET_LIKE.fullmatch(token):
                errors.append(
                    f"string under {key!r} looks like a credential value; "
                    "secrets belong only in the gitignored .env"
                )
                break
    return errors


def _validate_lane(lane, profile) -> list[str]:
    errors = []
    lane_id = lane["lane_id"]

    for field in ("kind", "role", "status", "audio_policy"):
        if lane[field] != profile[field]:
            errors.append(
                f"{lane_id}: {field} is {lane[field]!r} but the approved plan "
                f"requires {profile[field]!r}"
            )

    expected_permission = profile["benchmark_publication"]
    actual_permission = lane["permissions"]["benchmark_publication"]
    if actual_permission != expected_permission:
        errors.append(
            f"{lane_id}: benchmark_publication is {actual_permission!r} but "
            f"the approved plan requires {expected_permission!r}"
        )

    if lane["status"] in STATUSES_REQUIRING_BLOCKERS and not lane[
        "blocked_pending"
    ]:
        errors.append(
            f"{lane_id}: status {lane['status']!r} requires a non-empty "
            "blocked_pending list"
        )

    if lane["audio_policy"] in {"no_audio", "blocked"} and lane[
        "eligible_sources"
    ]:
        errors.append(
            f"{lane_id}: audio_policy {lane['audio_policy']!r} cannot list "
            "eligible sources"
        )

    for source_id in lane["eligible_sources"]:
        if source_id not in REQUIRED_SOURCE_IDS:
            errors.append(
                f"{lane_id}: eligible source {source_id!r} is not a "
                "registered corpus"
            )
        if source_id in TRANSFER_BLOCKED_SOURCES:
            errors.append(
                f"{lane_id}: source {source_id!r} blocks provider transfer "
                "in its corpus manifest and can never be eligible"
            )

    if lane["kind"] == "external_api":
        if lane["eligible_sources"] and lane["status"] not in (
            EXTERNAL_STATUSES_ALLOWED_AUDIO | {"conditional"}
        ):
            errors.append(
                f"{lane_id}: only ready or conditional external lanes may "
                "declare eligible sources"
            )
        if profile.get("requires_privacy") and "privacy" not in lane:
            errors.append(f"{lane_id}: external lane requires a privacy record")

    expected_env = profile.get("env_var_names")
    if expected_env is not None:
        credentials = lane.get("credentials")
        if credentials is None:
            errors.append(f"{lane_id}: credentials record is required")
        else:
            if set(credentials["env_var_names"]) != expected_env:
                errors.append(
                    f"{lane_id}: credential env var names must be exactly "
                    f"{sorted(expected_env)}"
                )
            if profile.get("requires_verified_credential") and not credentials[
                "verified"
            ]:
                errors.append(
                    f"{lane_id}: a ready external lane requires a dated, "
                    "harmless credential verification record"
                )
    elif "credentials" in lane:
        errors.append(
            f"{lane_id}: this lane must not declare credentials"
        )

    if profile.get("requires_lineage"):
        lineage = lane.get("lineage")
        if lineage is None:
            errors.append(f"{lane_id}: lineage record is required")
        else:
            claim_state = lineage.get("training_data_claim_state")
            expected_claim_state = profile["training_data_claim_state"]
            if claim_state not in TRAINING_DATA_CLAIM_STATES:
                errors.append(
                    f"{lane_id}: training_data_claim_state {claim_state!r} is "
                    "not a supported value"
                )
            elif claim_state != expected_claim_state:
                errors.append(
                    f"{lane_id}: training_data_claim_state is {claim_state!r} "
                    f"but the recorded evidence says {expected_claim_state!r}; "
                    "a claim state is a finding, not a preference"
                )
            if claim_state == "disproved":
                # A lane whose named training source does not exist cannot be
                # ready, and cannot leave its blockers empty, whatever its
                # licence says.
                if lane["status"] == "ready":
                    errors.append(
                        f"{lane_id}: a lane with a disproved training-data "
                        "claim cannot be ready"
                    )
                if not lane["blocked_pending"]:
                    errors.append(
                        f"{lane_id}: a lane with a disproved training-data "
                        "claim must record what is still outstanding"
                    )
            required_overlap = profile.get("required_non_independent_sources")
            if required_overlap is not None and set(
                lineage["non_independent_sources"]
            ) != required_overlap:
                errors.append(
                    f"{lane_id}: non_independent_sources must be exactly "
                    f"{sorted(required_overlap)}; source overlap cannot be "
                    "weakened"
                )
            for source_id in lineage["non_independent_sources"]:
                if source_id not in REQUIRED_SOURCE_IDS:
                    errors.append(
                        f"{lane_id}: non-independent source {source_id!r} is "
                        "not a registered corpus"
                    )
    elif "lineage" in lane and lane["kind"] in {
        "external_api",
        "acquisition_path",
    }:
        errors.append(
            f"{lane_id}: {lane['kind']} lanes do not carry model lineage"
        )

    prohibited_text = " ".join(lane["prohibited_uses"]).lower()
    for keyword in profile.get("required_prohibited_keywords", ()):
        if keyword.lower() not in prohibited_text:
            errors.append(
                f"{lane_id}: prohibited_uses must retain the "
                f"{keyword!r} prohibition"
            )

    return errors


def _validate_transfer_review_pins(register) -> list[str]:
    """Check every pinned transfer review claim against the live review.

    Each lane pins the review version and permitted sources it was written
    against. That pin is a snapshot, so it can age: the review moved to 1.1.0 at
    checkpoint 22E4 while the register stayed the frozen 22E3 record. Rather than
    trusting the snapshot, the pin is verified against the review on disk. An
    unknown version, or a source the current review no longer permits, is an
    error instead of a silent stale allowance.
    """
    from speech_sound_patterns.external_smoke import (
        HISTORICAL_TRANSFER_REVIEWS,
        TRANSFER_REVIEW_VERSION,
        transfer_permitted,
    )

    known_versions = {TRANSFER_REVIEW_VERSION} | set(HISTORICAL_TRANSFER_REVIEWS)
    errors = []
    for lane in register.get("lanes", []):
        pin = lane.get("transfer_review")
        if pin is None:
            continue
        lane_id = lane["lane_id"]
        if pin.get("review_version") not in known_versions:
            errors.append(
                f"{lane_id}: pinned transfer review version "
                f"{pin.get('review_version')!r} is not a version this code knows "
                "about"
            )
        for source_id in pin.get("permitted_sources", []):
            if not transfer_permitted(lane_id, source_id):
                errors.append(
                    f"{lane_id}: pins {source_id!r} as permitted but the current "
                    "corpus to provider transfer review does not permit that pair"
                )
    return errors


def _validate_owner_decisions(register) -> list[str]:
    """Keep the standing owner decisions in the register and unweakened.

    Checkpoint 22E6 added these because they were living in prose only. A
    decision that exists only in a planning document is one a later agent
    reasonably proposes undoing, having never seen it.
    """
    decisions = {
        decision["decision_id"]: decision
        for decision in register.get("owner_decisions", [])
    }
    errors = []
    if len(decisions) != len(register.get("owner_decisions", [])):
        errors.append("duplicate owner decision ids are forbidden")
    missing = REQUIRED_OWNER_DECISION_IDS - set(decisions)
    if missing:
        errors.append(
            "the register is missing standing owner decisions: "
            + ", ".join(sorted(missing))
        )
    for decision_id in sorted(set(decisions) & REQUIRED_OWNER_DECISION_IDS):
        if decisions[decision_id]["date"] != "2026-07-28":
            errors.append(
                f"{decision_id}: this decision was taken on 2026-07-28 and its "
                "date cannot be moved"
            )
    return errors


def validate_register(register=None) -> list[str]:
    if register is None:
        register = load_register()

    errors = [
        f"schema: {error.json_path}: {error.message}"
        for error in sorted(
            _schema_validator().iter_errors(register), key=str
        )
    ]
    if errors:
        return errors

    errors.extend(_secret_scan(register))

    lanes = {lane["lane_id"]: lane for lane in register["lanes"]}
    if len(lanes) != len(register["lanes"]):
        errors.append("duplicate lane_id entries are forbidden")

    missing = REQUIRED_LANE_IDS - set(lanes)
    if missing:
        errors.append(
            "register is missing approved lanes: " + ", ".join(sorted(missing))
        )
    unknown = set(lanes) - REQUIRED_LANE_IDS
    if unknown:
        errors.append(
            "register contains lanes outside the approved plan: "
            + ", ".join(sorted(unknown))
        )

    for lane_id in sorted(set(lanes) & REQUIRED_LANE_IDS):
        errors.extend(_validate_lane(lanes[lane_id], LANE_PROFILES[lane_id]))

    errors.extend(_validate_transfer_review_pins(register))

    errors.extend(_validate_owner_decisions(register))

    rejection_text = " ".join(
        item["candidate"] for item in register["recorded_rejections"]
    )
    for keyword in REQUIRED_REJECTION_CANDIDATE_KEYWORDS:
        if keyword.lower() not in rejection_text.lower():
            errors.append(
                f"recorded_rejections must retain the {keyword!r} rejection"
            )

    return errors


def assert_valid_register(register=None) -> None:
    errors = validate_register(register)
    if errors:
        raise ProviderRegisterValidationError(
            "provider register failed fail-closed validation:\n- "
            + "\n- ".join(errors)
        )


def assert_historical_register(register) -> None:
    """Validate a superseded register against the schema it was written to.

    Later checkpoints add fields, so a historical register cannot be judged by
    the current schema. It is still held to its own, and to the checkpoint that
    wrote it, so an earlier record cannot be quietly relabelled or edited.
    """
    version = register.get("schema_version")
    entry = HISTORICAL_REGISTERS.get(version)
    if entry is None:
        raise ProviderRegisterValidationError(
            f"register schema version {version!r} is not a superseded version "
            "this code keeps on disk"
        )
    _, schema_path = entry
    errors = [
        f"schema: {error.json_path}: {error.message}"
        for error in sorted(
            Draft202012Validator(_load_json(schema_path)).iter_errors(register),
            key=str,
        )
    ]
    expected_checkpoint = HISTORICAL_REGISTER_CHECKPOINTS[version]
    if register.get("checkpoint") != expected_checkpoint:
        errors.append(
            f"register {version} was written at checkpoint "
            f"{expected_checkpoint} and cannot be relabelled"
        )
    if errors:
        raise ProviderRegisterValidationError(
            f"superseded provider register {version} failed validation:\n- "
            + "\n- ".join(errors)
        )


def lane_status(lane_id: str, register=None) -> str:
    """Return the validated status for one lane, failing closed on any error."""
    if register is None:
        register = load_register()
    assert_valid_register(register)
    for lane in register["lanes"]:
        if lane["lane_id"] == lane_id:
            return lane["status"]
    raise ProviderRegisterValidationError(
        f"lane {lane_id!r} is not in the approved register"
    )


def audio_permitted(lane_id: str, source_id: str, register=None) -> bool:
    """True only when a validated lane may receive audio from a source.

    Anything unknown is False. This is the single decision point later
    subcheckpoints must use before any upload. Being listed as an eligible
    source is necessary but not sufficient: checkpoint 22E3 added the separate
    corpus to provider transfer review that every corpus manifest demands, and
    a lane whose audio policy requires that review cannot receive audio until
    the exact pair has been reviewed and permitted.
    """
    if register is None:
        register = load_register()
    assert_valid_register(register)
    for lane in register["lanes"]:
        if lane["lane_id"] != lane_id:
            continue
        if lane["status"] != "ready":
            return False
        if lane["audio_policy"] not in {
            "public_corpus_only",
            "corpus_transfer_review_required",
        }:
            return False
        if source_id not in lane["eligible_sources"]:
            return False
        # Imported here so the register stays importable on its own.
        from speech_sound_patterns.external_smoke import transfer_permitted

        return transfer_permitted(lane_id, source_id)
    return False
