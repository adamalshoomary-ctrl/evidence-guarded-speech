"""Fail-closed rules for the checkpoint 22E3 external schema smoke test.

Checkpoint 22E3 is the first point in item 22 where audio leaves this machine.
Two documents gate it and both must pass before a single request is built:

* the corpus to provider transfer review, which decides one named corpus and
  one named external lane at a time, and
* the external smoke contract, which is declared before any request and fixes
  what may be asked, what counts as a present field, what counts as repeatable
  and what each outcome permits checkpoint 22E4 to do.

Everything here fails closed. A pair that is not reviewed is prohibited, a
field that cannot be located is absent, and a configuration whose requests did
not succeed advances nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

from speech_sound_patterns.corpus_manifest import REQUIRED_SOURCE_IDS, SOURCE_PROFILES


PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parent
TRANSFER_REVIEW_PATH = (
    PACKAGE_ROOT / "corpus_manifests" / "provider-transfer-review-v1.2.0.json"
)
SMOKE_CONTRACT_PATH = PACKAGE_ROOT / "external-smoke-contract-v1.0.0.json"
SMOKE_REPORT_PATH = PACKAGE_ROOT / "external-schema-smoke-v1.0.0.json"

SCHEMA_VERSION = "1.0.0"
CHECKPOINT = "22E3"

# The transfer review outlives the subcheckpoint that first needed it, so its
# version and checkpoint move while the smoke contract and report stay pinned to
# 22E3. Superseded versions stay on disk exactly as committed: they are the
# record of what was decided before each transmission, and the tests keep them
# valid so a later edit cannot quietly rewrite that history.
TRANSFER_REVIEW_VERSION = "1.2.0"
TRANSFER_REVIEW_CHECKPOINTS = {"22E3", "22E4", "22E4B"}
HISTORICAL_TRANSFER_REVIEWS = {
    "1.0.0": PACKAGE_ROOT
    / "corpus_manifests"
    / "provider-transfer-review-v1.0.0.json",
    "1.1.0": PACKAGE_ROOT
    / "corpus_manifests"
    / "provider-transfer-review-v1.1.0.json",
}

TRANSFER_DECISIONS = {"permitted", "not_permitted"}
FIELD_STATES = {"present", "partial", "absent"}
REPEATABILITY_STATES = {"exact", "stable_schema_only", "unstable", "not_measured"}
ADVANCEMENT_STATES = {"exact_relation_capable", "score_only", "failed"}

# The expected-only manifest frozen at checkpoint 22D and reused unchanged by
# 22E2. Reusing it is what keeps the smoke sample label blind.
EXPECTED_ONLY_MANIFEST_SHA256 = (
    "c918feffa7c0a3a3fa99ce7a9e028621e8fb002980777297f30088e5975331da"
)

# Outputs that may never be carried into any later comparison, whatever a
# provider returns.
PROHIBITED_OUTPUT_KEYS = {
    "PronScore",
    "FluencyScore",
    "CompletenessScore",
    "ProsodyScore",
}

CHILD_STRATA = {"source_child_f", "source_child_m"}


class ExternalSmokeValidationError(RuntimeError):
    """Raised when the transfer review, contract or report cannot be trusted."""


def _load_json(path: Path):
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_transfer_review():
    return _load_json(TRANSFER_REVIEW_PATH)


def load_smoke_contract():
    return _load_json(SMOKE_CONTRACT_PATH)


def load_smoke_report():
    return _load_json(SMOKE_REPORT_PATH)


def _pair_key(decision):
    return (decision["lane_id"], decision["source_id"])


def validate_transfer_review(review=None) -> list[str]:
    """Return every reason the corpus to provider transfer review is untrusted."""
    if review is None:
        review = load_transfer_review()

    errors = []
    if not isinstance(review, dict):
        return ["transfer review must be a JSON object"]

    if review.get("schema_version") != SCHEMA_VERSION:
        errors.append("transfer review schema_version must be 1.0.0")
    if review.get("review_id") != "speech_sound_corpus_provider_transfer_review":
        errors.append("transfer review review_id is wrong")
    if review.get("checkpoint") not in TRANSFER_REVIEW_CHECKPOINTS:
        errors.append(
            "transfer review checkpoint must be a known item 22E subcheckpoint"
        )
    known_versions = {TRANSFER_REVIEW_VERSION} | set(HISTORICAL_TRANSFER_REVIEWS)
    if review.get("review_version") not in known_versions:
        errors.append(
            "transfer review review_version is not a version this code knows about"
        )
    errors.extend(_validate_supersession(review))
    if review.get("unlisted_pairs_are_prohibited") is not True:
        errors.append(
            "transfer review must state that an unlisted pair is prohibited; "
            "absence can never become permission"
        )
    if not review.get("personal_audio_statement"):
        errors.append(
            "transfer review must exclude owner and personal audio explicitly"
        )

    errors.extend(_validate_owner_audio(review))

    decisions = review.get("decisions")
    if not isinstance(decisions, list) or not decisions:
        return errors + ["transfer review must carry at least one decision"]

    seen = set()
    for decision in decisions:
        key = _pair_key(decision)
        if key in seen:
            errors.append(f"{key}: duplicate transfer decision")
        seen.add(key)

        lane_id, source_id = key
        if source_id not in REQUIRED_SOURCE_IDS:
            errors.append(f"{key}: {source_id!r} is not a registered corpus")
            continue

        state = decision.get("decision")
        if state not in TRANSFER_DECISIONS:
            errors.append(f"{key}: decision {state!r} is not supported")
            continue

        for field in (
            "licence_basis",
            "attribution_obligation",
            "provider_terms_basis",
            "privacy_basis",
            "sensitivity_notes",
        ):
            if not decision.get(field):
                errors.append(f"{key}: {field} must be recorded")

        if not decision.get("conditions"):
            errors.append(f"{key}: conditions must be recorded")
        if not decision.get("evidence"):
            errors.append(f"{key}: at least one dated evidence item is required")

        blocked_by_manifest = (
            SOURCE_PROFILES[source_id].get("provider_transfer") == "blocked"
        )
        if state == "permitted" and blocked_by_manifest:
            errors.append(
                f"{key}: the corpus manifest blocks provider transfer, so this "
                "pair can never be permitted"
            )

    errors.extend(_unreviewed_eligible_pairs(seen))
    return errors


def _validate_supersession(review) -> list[str]:
    """A newer review may narrow a decision but never lose one silently.

    Withdrawing a permission is a safe direction and stays allowed. Dropping a
    pair from the record is not: the next reader would see an unlisted pair,
    which this review treats as prohibited, and would lose the reasoning that
    once justified it.
    """
    supersedes = review.get("supersedes")
    if supersedes is None:
        return []
    if not isinstance(supersedes, dict):
        return ["supersedes must name the earlier review version and path"]
    earlier_version = supersedes.get("review_version")
    earlier_path = HISTORICAL_TRANSFER_REVIEWS.get(earlier_version)
    if earlier_path is None:
        return [
            f"superseded review version {earlier_version!r} is not on disk, so the "
            "earlier decisions cannot be checked"
        ]
    if supersedes.get("path") != str(earlier_path.relative_to(REPOSITORY_ROOT)):
        return ["supersedes path does not point at the superseded review on disk"]
    try:
        earlier = _load_json(earlier_path)
    except (OSError, ValueError):  # pragma: no cover - unreadable history
        return ["the superseded transfer review could not be read"]
    current_pairs = {_pair_key(item) for item in review.get("decisions", [])}
    missing = sorted(
        _pair_key(item)
        for item in earlier.get("decisions", [])
        if _pair_key(item) not in current_pairs
    )
    return [
        f"{pair}: the superseded review recorded this pair and the current review "
        "drops it; a decision may be narrowed but never forgotten"
        for pair in missing
    ]


OWNER_AUDIO_REQUIRED_FIELDS = (
    "decision_id",
    "granted",
    "granted_by",
    "lane_id",
    "file_path",
    "file_sha256",
    "purpose",
    "scope_note",
    "single_use",
    "evidence_class",
)


def _validate_owner_audio(review) -> list[str]:
    """Owner audio leaves the machine only under an exact, scoped grant.

    The default is prohibition. A grant names one file by hash, one lane and
    one purpose, so it cannot quietly widen into a standing permission for
    every recording Adam ever makes.
    """
    errors = []
    policy = review.get("owner_audio_policy")
    if not isinstance(policy, dict):
        return ["transfer review must carry an owner audio policy"]
    if policy.get("default") != "prohibited":
        errors.append("the owner audio default must be prohibited")
    for field in ("granting_authority", "scope_rule", "user_audio_rule"):
        if not policy.get(field):
            errors.append(f"owner audio policy must record {field}")

    grants = review.get("owner_audio_decisions")
    if not isinstance(grants, list):
        return errors + ["owner_audio_decisions must be a list, empty if none"]

    seen = set()
    for grant in grants:
        decision_id = grant.get("decision_id", "<unnamed>")
        for field in OWNER_AUDIO_REQUIRED_FIELDS:
            if grant.get(field) in (None, "", []):
                errors.append(f"{decision_id}: owner audio grant must record {field}")
        if decision_id in seen:
            errors.append(f"{decision_id}: duplicate owner audio grant")
        seen.add(decision_id)

        digest = grant.get("file_sha256")
        if not isinstance(digest, str) or len(digest) != 64:
            errors.append(
                f"{decision_id}: a grant must pin one exact file by SHA256, so "
                "it cannot be reused for a different recording"
            )
        if grant.get("single_use") is not True:
            errors.append(
                f"{decision_id}: an owner audio grant is single use; a standing "
                "permission for personal audio is not available here"
            )
        if grant.get("evidence_class") != "development_demonstration_only":
            errors.append(
                f"{decision_id}: owner audio is development demonstration "
                "evidence only and can never become accuracy, threshold or "
                "validation evidence"
            )
        if grant.get("lane_id") not in {
            lane for lane, _ in (_pair_key(item) for item in review.get("decisions", []))
        }:
            errors.append(
                f"{decision_id}: lane {grant.get('lane_id')!r} is not a lane this "
                "review knows about"
            )
    return errors


def owner_audio_permitted(lane_id: str, file_sha256: str, review=None) -> bool:
    """True only for an exact file hash under an exact recorded owner grant."""
    if review is None:
        review = load_transfer_review()
    if validate_transfer_review(review):
        return False
    for grant in review.get("owner_audio_decisions", []):
        if grant["lane_id"] == lane_id and grant["file_sha256"] == file_sha256:
            return True
    return False


def _unreviewed_eligible_pairs(reviewed_pairs) -> list[str]:
    """Every source a lane declares eligible must carry a written decision.

    Without this, a lane could gain an eligible source in the register and
    quietly inherit permission it was never granted. Imported lazily so the
    two modules stay independently importable.
    """
    from speech_sound_patterns.provider_register import load_register

    errors = []
    try:
        register = load_register()
    except (OSError, ValueError):  # pragma: no cover - register absent
        return ["the provider register could not be read to check review coverage"]

    for lane in register.get("lanes", []):
        for source_id in lane.get("eligible_sources", []):
            if (lane["lane_id"], source_id) not in reviewed_pairs:
                errors.append(
                    f"{lane['lane_id']} declares {source_id!r} eligible but the "
                    "transfer review records no decision for that pair"
                )
    return errors


def transfer_permitted(lane_id: str, source_id: str, review=None) -> bool:
    """True only when this exact pair was reviewed and permitted.

    Anything unreviewed, unknown or failing validation is False.
    """
    if review is None:
        review = load_transfer_review()
    if validate_transfer_review(review):
        return False
    for decision in review["decisions"]:
        if _pair_key(decision) == (lane_id, source_id):
            return decision["decision"] == "permitted"
    return False


def validate_smoke_contract(contract=None) -> list[str]:
    """Return every reason the predeclared smoke contract is untrusted."""
    if contract is None:
        contract = load_smoke_contract()

    errors = []
    if not isinstance(contract, dict):
        return ["smoke contract must be a JSON object"]

    if contract.get("schema_version") != SCHEMA_VERSION:
        errors.append("smoke contract schema_version must be 1.0.0")
    if contract.get("checkpoint") != CHECKPOINT:
        errors.append("smoke contract checkpoint must be 22E3")
    if contract.get("declared_before_any_request") is not True:
        errors.append(
            "the smoke contract is only meaningful if it was declared before "
            "any request was sent"
        )
    if not contract.get("release_lock"):
        errors.append("smoke contract must restate the release lock")

    policy = contract.get("input_policy")
    if not isinstance(policy, dict):
        return errors + ["smoke contract must carry an input policy"]

    if policy.get("expected_only_manifest_sha256") != EXPECTED_ONLY_MANIFEST_SHA256:
        errors.append(
            "the smoke sample must come from the frozen expected-only manifest, "
            "which carries no expert outcome"
        )
    if policy.get("source_id") != "speechocean762":
        errors.append("the checkpoint 22E3 sample source must be speechocean762")
    if policy.get("project_split") != "development":
        errors.append("the checkpoint 22E3 sample must be development split only")
    if policy.get("selection_used_expert_labels_or_model_outputs") is not False:
        errors.append("clip selection must not use expert labels or model outputs")

    strata = set(policy.get("permitted_strata") or ())
    if not strata:
        errors.append("permitted strata must be recorded")
    if strata & CHILD_STRATA:
        errors.append(
            "child strata are excluded from checkpoint 22E3 under data "
            "minimisation; the schema question does not require child speech"
        )

    never = set(policy.get("never_transmitted_fields") or ())
    for required in (
        "expert reviewer phone strings",
        "aggregate mispronunciation labels",
        "any held out participant or clip",
        "any owner or personal recording",
    ):
        if required not in never:
            errors.append(f"never_transmitted_fields must retain {required!r}")

    prohibited = set(contract.get("prohibited_outputs") or ())
    for key in sorted(PROHIBITED_OUTPUT_KEYS):
        if key not in prohibited:
            errors.append(f"prohibited_outputs must retain {key}")

    rules = contract.get("advancement_rules")
    if not isinstance(rules, dict):
        errors.append("advancement rules must be predeclared")
    else:
        for state in sorted(ADVANCEMENT_STATES):
            if state not in rules:
                errors.append(f"advancement rules must define {state!r}")
        if "no_lane_advances_on_marketing" not in rules:
            errors.append(
                "advancement rules must bar qualifying a lane on documentation, "
                "marketing or overall scores"
            )

    repeat = contract.get("repeatability_rules")
    if not isinstance(repeat, dict):
        errors.append("repeatability rules must be predeclared")
    elif repeat.get("numeric_tolerance") != 0.0:
        errors.append(
            "no numeric tolerance may be granted; a provider that returns "
            "different numbers for an identical request must be recorded as such"
        )

    request_policy = contract.get("azure_request_policy")
    if not isinstance(request_policy, dict):
        errors.append("the Azure request policy must be predeclared")
    else:
        if request_policy.get("prosody_assessment_enabled") is not False:
            errors.append("prosody assessment is a prohibited output and is never requested")
        parameters = request_policy.get("assessment_parameters") or {}
        if parameters.get("Granularity") != "Phoneme":
            errors.append("phoneme granularity is required to answer the question")

    return errors


def validate_smoke_report(report=None, contract=None, review=None) -> list[str]:
    """Return every reason the committed smoke report is untrusted."""
    if report is None:
        report = load_smoke_report()
    if contract is None:
        contract = load_smoke_contract()
    if review is None:
        review = load_transfer_review()

    errors = validate_smoke_contract(contract) + validate_transfer_review(review)
    if errors:
        return errors

    if not isinstance(report, dict):
        return ["smoke report must be a JSON object"]

    if report.get("schema_version") != SCHEMA_VERSION:
        errors.append("smoke report schema_version must be 1.0.0")
    if report.get("checkpoint") != CHECKPOINT:
        errors.append("smoke report checkpoint must be 22E3")
    if report.get("smoke_contract_sha256") is None:
        errors.append("the smoke report must bind the contract it ran under")
    if report.get("no_selection_notice") is None:
        errors.append(
            "the smoke report must restate that a schema smoke test selects "
            "no system and measures no accuracy"
        )

    configurations = report.get("configurations")
    if not isinstance(configurations, list) or not configurations:
        return errors + ["smoke report must carry at least one configuration"]

    declared = {
        item["configuration_id"] for item in contract.get("azure_configurations", [])
    }
    for configuration in configurations:
        configuration_id = configuration.get("configuration_id")
        if configuration_id not in declared:
            errors.append(
                f"{configuration_id!r} was not declared in the smoke contract; "
                "a configuration cannot be added after seeing results"
            )

        lane_id = configuration.get("lane_id")
        source_id = configuration.get("source_id")
        if not transfer_permitted(lane_id, source_id, review):
            errors.append(
                f"{configuration_id!r}: the transfer review does not permit "
                f"sending {source_id!r} to {lane_id!r}"
            )

        outcome = configuration.get("advancement")
        if outcome not in ADVANCEMENT_STATES:
            errors.append(f"{configuration_id!r}: advancement {outcome!r} is not supported")

        repeatability = configuration.get("repeatability")
        if repeatability not in REPEATABILITY_STATES:
            errors.append(
                f"{configuration_id!r}: repeatability {repeatability!r} is not supported"
            )

        fields = configuration.get("field_presence") or {}
        for name, state in sorted(fields.items()):
            if state not in FIELD_STATES:
                errors.append(
                    f"{configuration_id!r}: field {name!r} state {state!r} is not "
                    "supported; an unlocatable field is absent"
                )

        capabilities = configuration.get("capabilities") or {}
        named_phone = capabilities.get("phoneme_name")
        candidates = capabilities.get("spoken_phoneme_candidates")
        if outcome == "exact_relation_capable" and not (
            named_phone == "present" and candidates == "present"
        ):
            errors.append(
                f"{configuration_id!r}: exact_relation_capable requires both an "
                "expected phone name and named produced candidates to be present"
            )
        if outcome == "score_only" and named_phone == "present" and candidates == "present":
            errors.append(
                f"{configuration_id!r}: a configuration exposing named produced "
                "candidates must not be understated as score_only"
            )
        if configuration.get("requests_succeeded") == 0 and outcome != "failed":
            errors.append(
                f"{configuration_id!r}: a configuration with no successful "
                "request advances nothing"
            )

    locales = [item.get("locale") for item in configurations]
    if len(locales) != len(set(locales)):
        errors.append("each locale is a separate configuration and is never pooled")

    if report.get("locales_pooled") is not False:
        errors.append("the report must state explicitly that locales were not pooled")

    for key in sorted(PROHIBITED_OUTPUT_KEYS):
        if key in json.dumps(report.get("configurations")):
            errors.append(
                f"{key} is a prohibited output class and must not appear in the "
                "committed report"
            )

    return errors


def assert_valid_smoke_evidence(report=None, contract=None, review=None) -> None:
    errors = validate_smoke_report(report, contract, review)
    if errors:
        raise ExternalSmokeValidationError(
            "checkpoint 22E3 external smoke evidence failed fail-closed "
            "validation:\n- " + "\n- ".join(errors)
        )
