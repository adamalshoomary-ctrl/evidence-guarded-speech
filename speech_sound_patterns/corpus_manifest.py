"""Load and validate speech sound corpus manifests without trusting raw data."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from jsonschema import Draft202012Validator, FormatChecker


PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parent
MANIFEST_ROOT = PACKAGE_ROOT / "corpus_manifests"
REGISTRY_PATH = MANIFEST_ROOT / "registry-v1.0.0.json"
SCHEMA_PATH = MANIFEST_ROOT / "corpus-manifest-schema-v1.0.0.json"
REGISTRY_SCHEMA_PATH = MANIFEST_ROOT / "corpus-registry-schema-v1.0.0.json"

SCHEMA_VERSION = "1.0.0"
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
HEX = re.compile(r"^[0-9a-f]+$")
SOURCE_ID = re.compile(r"^[a-z0-9_]+$")
SPLITS = ("development", "threshold_tuning", "held_out_evaluation")

ACCESS_STATES = {"available", "access_pending", "rejected", "unavailable"}
LICENCE_STATES = {
    "verified_for_declared_role",
    "pending_review",
    "restricted_role_only",
    "rejected",
}
TRUTH_CLASSES = {
    "expert_phone_relations",
    "human_corrected_phone_boundaries",
    "automatic_forced_alignments",
    "validated_sentence_audio",
    "transcript_only_robustness",
    "functional_integration_only",
    "unavailable",
}
TERMS_STATES = {"accepted", "not_required", "pending", "rejected"}
PROVIDER_TRANSFER_STATES = {
    "blocked",
    "requires_separate_provider_terms_review",
    "permitted_for_declared_role",
}
SPLIT_STATUSES = {"audited", "fixture_not_population_split", "not_applicable"}
INDEPENDENCE_CLAIMS = {
    "candidate_model_overlap_must_be_audited",
    "fixture_only_not_population_evidence",
    "not_independent_of_lineage",
    "not_independent_of_common_voice_family",
    "no_evidence_claim_permitted",
}

REQUIRED_SOURCE_IDS = {
    "speechocean762",
    "acted_clear_speech",
    "common_phone_1_0",
    "common_voice_26_australian_english",
    "librispeech_slr12_small",
    "macquarie_australian_pronunciation_data",
    "timit_ldc93s1",
    "l2_arctic",
    "talkbank_research",
    # Checkpoint 22E6 added the sources the open evidence search of 2026-07-28
    # found. Six are recorded so nobody rediscovers them as though they were
    # new, and three are the openly licensed stack checkpoint 22E7 acquires.
    "andosl",
    "austalk",
    "isle_elra_s0083",
    "mitchell_delbridge",
    "speech_accent_archive",
    "coanzse",
    "wikipron_eng_latn_uk_broad",
    "wiktionary_australian_kaikki",
    "mfa_english_dictionary",
    # Checkpoint 22E7 acquired the open stack and added the matched American
    # scrape. A British reference that is only claimed to be non-rhotic proves
    # nothing; a British reference measured beside its American counterpart from
    # the same lexicon, the same commit and the same contributors does.
    "wikipron_eng_latn_us_broad",
    # The comparison accent subsets of the same Common Voice release. Comparing
    # accent groups collected on one platform, from one prompt pool, under one
    # validation process is what controls the recording quality confound that
    # comparing two different corpora never could.
    "common_voice_26_british_english",
    "common_voice_26_american_english_male",
    "common_voice_26_american_english_female",
}

UNIVERSAL_PROHIBITED_ROLES = {
    "scientific_release_truth",
    "product_release_truth",
    "clinical_inference",
    "accent_quality_judgment",
}

SOURCE_PROFILES = {
    "speechocean762": {
        "access_state": "available",
        "licence_state": "verified_for_declared_role",
        "truth_class": "expert_phone_relations",
        "required_permitted_role": "developer_phone_relation_benchmark",
        "required_prohibited_roles": {
            "native_likeness_truth",
            "acceptable_variety_truth",
            "scalar_score_as_error_label",
        },
        "provider_transfer": "requires_separate_provider_terms_review",
    },
    "acted_clear_speech": {
        "access_state": "available",
        "licence_state": "verified_for_declared_role",
        "truth_class": "human_corrected_phone_boundaries",
        "required_permitted_role": "phone_boundary_regression_fixture",
        "required_prohibited_roles": {"population_accuracy_estimate"},
        "provider_transfer": "requires_separate_provider_terms_review",
    },
    "common_phone_1_0": {
        "access_state": "available",
        "licence_state": "verified_for_declared_role",
        "truth_class": "automatic_forced_alignments",
        "required_permitted_role": "automatic_phone_engineering",
        "required_prohibited_roles": {
            "phone_relation_truth",
            "substitution_deletion_or_insertion_truth",
        },
        "provider_transfer": "requires_separate_provider_terms_review",
    },
    "common_voice_26_australian_english": {
        "access_state": "available",
        "licence_state": "verified_for_declared_role",
        "truth_class": "validated_sentence_audio",
        "required_permitted_role": "australian_robustness_stress_test",
        "required_prohibited_roles": {
            "phone_truth",
            "australian_lexical_variant_truth",
        },
        "provider_transfer": "blocked",
    },
    "librispeech_slr12_small": {
        "access_state": "available",
        "licence_state": "verified_for_declared_role",
        "truth_class": "transcript_only_robustness",
        "required_permitted_role": "runtime_and_determinism_regression",
        "required_prohibited_roles": {"phone_production_truth"},
        "provider_transfer": "requires_separate_provider_terms_review",
    },
    "macquarie_australian_pronunciation_data": {
        "access_state": "access_pending",
        "licence_state": "pending_review",
        "truth_class": "unavailable",
        "required_permitted_role": "manifest_only",
        "required_prohibited_roles": {"use_before_written_licence"},
        "provider_transfer": "blocked",
    },
    "timit_ldc93s1": {
        "access_state": "rejected",
        "licence_state": "rejected",
        "truth_class": "unavailable",
        "required_permitted_role": "manifest_only",
        "required_prohibited_roles": {
            "torrent_download",
            "current_engineering_use",
        },
        "provider_transfer": "blocked",
    },
    "l2_arctic": {
        "access_state": "unavailable",
        "licence_state": "restricted_role_only",
        "truth_class": "unavailable",
        "required_permitted_role": "manifest_only",
        "required_prohibited_roles": {"commercial_product_engineering"},
        "provider_transfer": "blocked",
    },
    "talkbank_research": {
        "access_state": "unavailable",
        "licence_state": "restricted_role_only",
        "truth_class": "unavailable",
        "required_permitted_role": "manifest_only",
        "required_prohibited_roles": {"use_without_corpus_specific_rights"},
        "provider_transfer": "blocked",
    },
    # Checkpoint 22E6. Sources the 2026-07-28 open evidence search ruled out.
    # Each one is recorded with the ground that closed it, so a later agent
    # reads a decision rather than an unexplored lead.
    "andosl": {
        "access_state": "rejected",
        "licence_state": "restricted_role_only",
        "truth_class": "unavailable",
        "required_permitted_role": "manifest_only",
        "required_prohibited_roles": {
            "commercial_product_engineering",
            "use_without_written_permission",
        },
        "provider_transfer": "blocked",
    },
    "austalk": {
        "access_state": "unavailable",
        "licence_state": "pending_review",
        "truth_class": "unavailable",
        "required_permitted_role": "manifest_only",
        "required_prohibited_roles": {
            "use_before_an_access_route_exists",
            "assuming_annotation_content_that_cannot_be_inspected",
        },
        "provider_transfer": "blocked",
    },
    "isle_elra_s0083": {
        "access_state": "rejected",
        "licence_state": "restricted_role_only",
        "truth_class": "unavailable",
        "required_permitted_role": "manifest_only",
        "required_prohibited_roles": {
            "use_without_a_purchased_commercial_licence",
            "treating_a_declined_purchase_as_an_unknown",
        },
        "provider_transfer": "blocked",
    },
    "mitchell_delbridge": {
        "access_state": "rejected",
        "licence_state": "restricted_role_only",
        "truth_class": "unavailable",
        "required_permitted_role": "manifest_only",
        "required_prohibited_roles": {
            "commercial_product_engineering",
            "non_commercial_source_in_a_commercial_product",
        },
        "provider_transfer": "blocked",
    },
    "speech_accent_archive": {
        "access_state": "rejected",
        "licence_state": "restricted_role_only",
        "truth_class": "unavailable",
        "required_permitted_role": "manifest_only",
        "required_prohibited_roles": {
            "commercial_product_engineering",
            "non_commercial_source_in_a_commercial_product",
        },
        "provider_transfer": "blocked",
    },
    "coanzse": {
        "access_state": "rejected",
        "licence_state": "restricted_role_only",
        "truth_class": "unavailable",
        "required_permitted_role": "manifest_only",
        "required_prohibited_roles": {
            "commercial_product_engineering",
            "american_aligned_timing_as_australian_evidence",
        },
        "provider_transfer": "blocked",
    },
    # The openly licensed stack, acquired at checkpoint 22E7.
    #
    # Every one of these is a pronunciation lexicon. A lexicon proposes how a
    # word may be said; it never observes how anybody said it. Their truth class
    # therefore stays `unavailable` after acquisition exactly as it was before,
    # and the reason changed rather than the value: not "we could not get it"
    # but "this kind of source cannot carry that kind of truth". `is_lexicon`
    # exempts them from the participant split rules, because a word list has no
    # speakers to keep apart, and nothing else may claim that exemption.
    "wikipron_eng_latn_uk_broad": {
        "access_state": "available",
        "licence_state": "verified_for_declared_role",
        "truth_class": "unavailable",
        "is_lexicon": True,
        "required_permitted_role": "british_reference_variant_supplement",
        "required_prohibited_roles": {
            "australian_variety_truth",
            "accepted_variant_truth",
            "distribution_of_a_derived_lexicon_without_meeting_sharealike",
            # Measured at acquisition rather than assumed: 6.85 percent of its
            # entries carry a post-vocalic rhotic, against 0.01 percent in the
            # MFA British dictionary, and its inventory holds 239 symbols
            # including sounds English does not use. It supplements the British
            # reference. It is not fit to be the British reference.
            "primary_british_reference_without_an_inventory_repair",
        },
        "provider_transfer": "blocked",
    },
    "wikipron_eng_latn_us_broad": {
        "access_state": "available",
        "licence_state": "verified_for_declared_role",
        "truth_class": "unavailable",
        "is_lexicon": True,
        "required_permitted_role": "american_reference_contrast_measurement",
        "required_prohibited_roles": {
            "australian_variety_truth",
            "accepted_variant_truth",
            "distribution_of_a_derived_lexicon_without_meeting_sharealike",
            "reference_for_australian_or_british_speakers",
        },
        "provider_transfer": "blocked",
    },
    "wiktionary_australian_kaikki": {
        "access_state": "available",
        "licence_state": "verified_for_declared_role",
        "truth_class": "unavailable",
        "is_lexicon": True,
        "required_permitted_role": "australian_reference_variant_overlay",
        "required_prohibited_roles": {
            "accepted_variant_truth",
            "acoustic_judgement",
            "distribution_of_a_derived_lexicon_without_meeting_sharealike",
        },
        "provider_transfer": "blocked",
    },
    "mfa_english_dictionary": {
        "access_state": "available",
        "licence_state": "verified_for_declared_role",
        "truth_class": "unavailable",
        "is_lexicon": True,
        "required_permitted_role": "british_referenced_expected_phone_path",
        "required_prohibited_roles": {
            "australian_variety_truth",
            "accepted_variant_truth",
        },
        "provider_transfer": "blocked",
    },
    # The comparison groups. Every one of these derives from Common Voice, so
    # every one is barred from qualifying the model that was trained on it.
    "common_voice_26_british_english": {
        "access_state": "available",
        "licence_state": "verified_for_declared_role",
        "truth_class": "validated_sentence_audio",
        "required_permitted_role": "british_variety_comparison_group",
        "required_prohibited_roles": {
            "phone_truth",
            "australian_lexical_variant_truth",
            "selection_evidence_for_a_common_voice_trained_model",
        },
        "provider_transfer": "blocked",
    },
    # Neither American subset may stand as the American group alone. One is male
    # only and one is female only, so either by itself would make accent and
    # speaker gender vary together, which is the confound this checkpoint was
    # told not to proceed past quietly.
    "common_voice_26_american_english_male": {
        "access_state": "available",
        "licence_state": "verified_for_declared_role",
        "truth_class": "validated_sentence_audio",
        "required_permitted_role": "american_variety_control_group",
        "required_prohibited_roles": {
            "phone_truth",
            "australian_lexical_variant_truth",
            "selection_evidence_for_a_common_voice_trained_model",
            "american_comparison_from_one_gender_alone",
        },
        "provider_transfer": "blocked",
    },
    "common_voice_26_american_english_female": {
        "access_state": "available",
        "licence_state": "verified_for_declared_role",
        "truth_class": "validated_sentence_audio",
        "required_permitted_role": "american_variety_control_group",
        "required_prohibited_roles": {
            "phone_truth",
            "australian_lexical_variant_truth",
            "selection_evidence_for_a_common_voice_trained_model",
            "american_comparison_from_one_gender_alone",
        },
        "provider_transfer": "blocked",
    },
}


class CorpusManifestValidationError(ValueError):
    """Raised when corpus provenance or use boundaries fail closed."""


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_registry(path: Path = REGISTRY_PATH):
    return _load_json(Path(path))


def load_manifest(path: Path):
    return _load_json(Path(path))


def load_registered_manifests(registry_path: Path = REGISTRY_PATH):
    registry_path = Path(registry_path)
    registry = load_registry(registry_path)
    base = registry_path.parent.resolve()
    manifests = []
    for item in registry.get("manifests", []):
        if isinstance(item, dict) and isinstance(item.get("path"), str):
            relative = Path(item["path"])
            candidate = (base / relative).resolve()
            if (
                relative.name != item["path"]
                or relative.suffix != ".json"
                or candidate.parent != base
            ):
                raise CorpusManifestValidationError(
                    f"unsafe registered manifest path: {item['path']}"
                )
            manifests.append(load_manifest(candidate))
    return registry, manifests


def _object(value, label, required, errors):
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return False
    missing = sorted(set(required) - set(value))
    if missing:
        errors.append(f"{label} missing fields: {', '.join(missing)}")
        return False
    return True


def _nonempty_strings(value):
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and item.strip() for item in value)
    )


def _valid_url(value):
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def _valid_checksum(value, algorithm):
    lengths = {"md5": 32, "sha256": 64}
    return (
        isinstance(value, str)
        and len(value) == lengths[algorithm]
        and bool(HEX.fullmatch(value))
    )


def _inside_private_root(relative_path, repository_root=REPOSITORY_ROOT):
    if not isinstance(relative_path, str):
        return False
    private_root = (Path(repository_root) / ".research_data").resolve()
    candidate = (Path(repository_root) / relative_path).resolve(strict=False)
    try:
        candidate.relative_to(private_root)
    except ValueError:
        return False
    return True


def canonical_json_sha256(value):
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _schema_errors(document, schema_path, label):
    schema = _load_json(schema_path)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = []
    for issue in sorted(validator.iter_errors(document), key=lambda item: list(item.path)):
        location = ".".join(str(part) for part in issue.absolute_path)
        prefix = f"{label}.{location}" if location else label
        errors.append(f"{prefix}: {issue.message}")
    return errors


def _validate_archive(archive, location, errors):
    required = {
        "filename",
        "size_bytes",
        "canonical_download_url",
        "upstream_checksum",
        "local_sha256",
        "local_verification_status",
    }
    if not _object(archive, location, required, errors):
        return
    if not isinstance(archive["filename"], str) or not archive["filename"]:
        errors.append(f"{location}.filename must be nonempty")
    if not isinstance(archive["size_bytes"], int) or archive["size_bytes"] <= 0:
        errors.append(f"{location}.size_bytes must be positive")
    if not _valid_url(archive["canonical_download_url"]):
        errors.append(f"{location}.canonical_download_url must be HTTPS")
    upstream = archive["upstream_checksum"]
    if not _object(upstream, f"{location}.upstream_checksum", {"algorithm", "value"}, errors):
        return
    algorithm = upstream.get("algorithm")
    if algorithm == "none":
        if upstream.get("value") is not None:
            errors.append(f"{location} unpublished checksum value must be null")
    elif algorithm not in {"md5", "sha256"}:
        errors.append(f"{location} has an unsupported upstream checksum")
    elif not _valid_checksum(upstream.get("value"), algorithm):
        errors.append(f"{location} has a malformed upstream checksum")
    if archive["local_verification_status"] != "verified":
        errors.append(f"{location} must be locally verified")
    if not _valid_checksum(archive["local_sha256"], "sha256"):
        errors.append(f"{location}.local_sha256 must be a verified SHA256")


def _validate_split(split, location, access_state, errors, is_lexicon=False):
    required = {
        "status",
        "unit",
        "source_split_provenance",
        "project_strategy",
        "frozen_held_out",
        "assignment_artifact",
        "assignment_sha256",
        "participant_counts",
        "cross_split_overlap_count",
        "strata",
    }
    if not _object(split, location, required, errors):
        return
    status = split["status"]
    if status not in SPLIT_STATUSES:
        errors.append(f"{location}.status is unsupported")
    if access_state == "available" and status == "not_applicable" and not is_lexicon:
        errors.append(f"{location} cannot skip split handling for available data")
    if is_lexicon and status != "not_applicable":
        errors.append(f"{location} a lexicon has no participants to split")
    if status == "audited":
        if split["unit"] != "participant":
            errors.append(f"{location}.unit must be participant")
        if split["frozen_held_out"] is not True:
            errors.append(f"{location} must freeze held out participants")
        if split["cross_split_overlap_count"] != 0:
            errors.append(f"{location} has participant overlap")
        if not isinstance(split["assignment_artifact"], str) or not split[
            "assignment_artifact"
        ].startswith(".research_data/"):
            errors.append(f"{location} must use a private assignment artifact")
        elif not _inside_private_root(split["assignment_artifact"]):
            errors.append(f"{location} assignment artifact escapes private storage")
        if not _valid_checksum(split["assignment_sha256"], "sha256"):
            errors.append(f"{location}.assignment_sha256 must be a SHA256")
        counts = split["participant_counts"]
        if set(counts) != set(SPLITS) or not all(
            isinstance(counts[item], int) and counts[item] > 0 for item in SPLITS
        ):
            errors.append(f"{location}.participant_counts are incomplete")
        if not isinstance(split["strata"], dict) or not split["strata"]:
            errors.append(f"{location}.strata must be an object")
        elif set(counts) == set(SPLITS):
            stratum_totals = {project_split: 0 for project_split in SPLITS}
            for stratum, values in split["strata"].items():
                if not isinstance(stratum, str) or not isinstance(values, dict):
                    errors.append(f"{location}.strata entries must be split objects")
                    continue
                if set(values) != set(SPLITS) or not all(
                    isinstance(values[item], int) and values[item] >= 0
                    for item in SPLITS
                ):
                    errors.append(
                        f"{location}.strata.{stratum} must count every project split"
                    )
                    continue
                for project_split in SPLITS:
                    stratum_totals[project_split] += values[project_split]
            if stratum_totals != counts:
                errors.append(
                    f"{location}.participant_counts must equal aggregate strata"
                )
    elif status == "fixture_not_population_split":
        if split["frozen_held_out"] is not False:
            errors.append(f"{location} fixture cannot claim a held out population")
        if split["cross_split_overlap_count"] != 0:
            errors.append(f"{location} fixture overlap count must be zero")


def validate_manifest(document):
    """Return structural, licence, truth-role and split errors for one source."""
    errors = _schema_errors(document, SCHEMA_PATH, "manifest_schema")
    required = {
        "schema_version",
        "manifest_id",
        "source_id",
        "title",
        "version",
        "citation",
        "canonical_source",
        "access",
        "licence",
        "governance",
        "population",
        "annotation",
        "capability_audit",
        "participant_split",
        "lineage",
        "archives",
    }
    if not _object(document, "manifest", required, errors):
        return errors
    if document["schema_version"] != SCHEMA_VERSION:
        errors.append("manifest schema_version is unsupported")
    source_id = document["source_id"]
    if not isinstance(source_id, str) or not SOURCE_ID.fullmatch(source_id):
        errors.append("source_id must be a stable lower case identifier")
        return errors
    profile = SOURCE_PROFILES.get(source_id)
    if profile is None:
        errors.append(f"source_id {source_id} is not approved by the register")
        return errors
    if document["manifest_id"] != f"{source_id}_manifest_v1":
        errors.append("manifest_id must bind source_id and manifest version")
    version = document["version"]
    if not _object(version, "version", {"label", "release_date", "immutable_id"}, errors):
        return errors
    if not all(isinstance(version[field], str) and version[field] for field in version):
        errors.append("version fields must be nonempty strings")
    if not isinstance(document["citation"], str) or not document["citation"].strip():
        errors.append("citation must be nonempty")

    canonical = document["canonical_source"]
    if _object(canonical, "canonical_source", {"landing_page", "licence_url"}, errors):
        for field in ("landing_page", "licence_url"):
            if not _valid_url(canonical[field]):
                errors.append(f"canonical_source.{field} must be HTTPS")

    access = document["access"]
    access_required = {
        "state",
        "retrieved_at",
        "account_required",
        "terms_state",
        "terms_url",
        "terms_version",
        "terms_snapshot_sha256",
    }
    if not _object(access, "access", access_required, errors):
        return errors
    if access["state"] not in ACCESS_STATES:
        errors.append("access.state is unsupported")
    if access["terms_state"] not in TERMS_STATES:
        errors.append("access.terms_state is unsupported")
    if access["terms_state"] == "accepted":
        if not _valid_url(access["terms_url"]):
            errors.append("accepted access terms require an HTTPS URL")
        if not _valid_checksum(access["terms_snapshot_sha256"], "sha256"):
            errors.append("accepted access terms require a snapshot SHA256")

    licence = document["licence"]
    licence_required = {
        "state",
        "spdx_id",
        "commercial_use_permitted",
        "verified_at",
        "attribution_required",
        "attribution_text",
    }
    if not _object(licence, "licence", licence_required, errors):
        return errors
    if licence["state"] not in LICENCE_STATES:
        errors.append("licence.state is unsupported")
    if licence["state"] == "verified_for_declared_role":
        if licence["commercial_use_permitted"] is not True:
            errors.append("verified sources must permit the declared commercial role")
        if not isinstance(licence["spdx_id"], str) or not licence["spdx_id"]:
            errors.append("verified sources require an SPDX licence identifier")
    if licence["attribution_required"] is True and not licence["attribution_text"]:
        errors.append("attribution text is required")

    governance = document["governance"]
    governance_required = {
        "permitted_roles",
        "prohibited_roles",
        "raw_data_committed",
        "local_storage",
        "rehosting_permitted",
        "reidentification_prohibited",
        "provider_transfer",
        "retention_or_deletion_duties",
    }
    if not _object(governance, "governance", governance_required, errors):
        return errors
    if not _nonempty_strings(governance["permitted_roles"]):
        errors.append("governance.permitted_roles must be nonempty")
    if not _nonempty_strings(governance["prohibited_roles"]):
        errors.append("governance.prohibited_roles must be nonempty")
    permitted = set(governance["permitted_roles"])
    prohibited = set(governance["prohibited_roles"])
    if permitted & prohibited:
        errors.append("permitted and prohibited roles must be disjoint")
    if not UNIVERSAL_PROHIBITED_ROLES.issubset(prohibited):
        errors.append("every source must preserve universal prohibited roles")
    if governance["raw_data_committed"] is not False:
        errors.append("raw corpus data may never be committed")
    if governance["reidentification_prohibited"] is not True:
        errors.append("speaker reidentification must remain prohibited")
    if governance["provider_transfer"] not in PROVIDER_TRANSFER_STATES:
        errors.append("governance.provider_transfer is unsupported")
    elif governance["provider_transfer"] != profile["provider_transfer"]:
        errors.append(f"{source_id} must preserve its provider transfer boundary")
    if access["state"] == "available":
        if governance["rehosting_permitted"] is not False:
            errors.append("available raw data may not be rehosted by this project")
        storage = governance["local_storage"]
        if not isinstance(storage, str) or not storage.startswith(".research_data/"):
            errors.append("available raw data must use private gitignored storage")
        elif not _inside_private_root(storage):
            errors.append("available raw data storage escapes the private root")
    elif governance["local_storage"] is not None:
        errors.append("unavailable or rejected sources cannot claim local storage")

    population = document["population"]
    if not _object(population, "population", {"description", "known_strata", "limitations"}, errors):
        return errors
    if not isinstance(population["description"], str) or not population["description"]:
        errors.append("population.description must be nonempty")
    if not _nonempty_strings(population["limitations"]):
        errors.append("population.limitations must be nonempty")

    annotation = document["annotation"]
    annotation_required = {
        "truth_class",
        "provenance",
        "fields_retained",
        "original_records_retained",
        "scalar_scores_are_relation_truth",
        "limitations",
    }
    if not _object(annotation, "annotation", annotation_required, errors):
        return errors
    if annotation["truth_class"] not in TRUTH_CLASSES:
        errors.append("annotation.truth_class is unsupported")
    if annotation["scalar_scores_are_relation_truth"] is not False:
        errors.append("scalar scores cannot become phone relation truth")
    if not _nonempty_strings(annotation["limitations"]):
        errors.append("annotation.limitations must be nonempty")

    audit = document["capability_audit"]
    if not _object(audit, "capability_audit", {"status", "inspected_materials", "findings"}, errors):
        return errors
    expected_audit = "complete" if access["state"] == "available" else "blocked_or_pending"
    if audit["status"] != expected_audit:
        errors.append("capability_audit.status does not match source access")
    if not _nonempty_strings(audit["inspected_materials"]):
        errors.append("capability_audit.inspected_materials must be nonempty")
    if not _nonempty_strings(audit["findings"]):
        errors.append("capability_audit.findings must be nonempty")

    _validate_split(
        document["participant_split"],
        "participant_split",
        access["state"],
        errors,
        is_lexicon=profile.get("is_lexicon", False),
    )

    lineage = document["lineage"]
    lineage_required = {
        "lineage_group",
        "derived_from",
        "independence_claim",
        "duplicate_detection",
        "candidate_model_overlap_status",
    }
    if not _object(lineage, "lineage", lineage_required, errors):
        return errors
    if not isinstance(lineage["derived_from"], list):
        errors.append("lineage.derived_from must be a list")
    if lineage["independence_claim"] not in INDEPENDENCE_CLAIMS:
        errors.append("lineage.independence_claim is unsupported")
    if lineage["candidate_model_overlap_status"] not in {
        "not_applicable",
        "unknown_requires_model_specific_audit",
        "audited_no_known_overlap",
        "known_overlap_not_independent",
    }:
        errors.append("lineage candidate model overlap status is unsupported")
    if lineage["candidate_model_overlap_status"] == "unknown_requires_model_specific_audit" and lineage[
        "independence_claim"
    ] == "independent_accuracy_evidence":
        errors.append("unknown model training overlap cannot be called independent")

    archives = document["archives"]
    if not isinstance(archives, list):
        errors.append("archives must be a list")
    elif access["state"] == "available":
        if not archives:
            errors.append("available public sources require verified archives")
        for index, archive in enumerate(archives):
            _validate_archive(archive, f"archives[{index}]", errors)
    elif archives:
        errors.append("blocked, rejected or owner recordings cannot declare archives")

    for field, expected in (
        ("access_state", access["state"]),
        ("licence_state", licence["state"]),
        ("truth_class", annotation["truth_class"]),
    ):
        if expected != profile[field]:
            errors.append(f"{source_id} must preserve profile {field}")
    if profile["required_permitted_role"] not in permitted:
        errors.append(f"{source_id} is missing its required permitted role")
    if not profile["required_prohibited_roles"].issubset(prohibited):
        errors.append(f"{source_id} is missing source specific prohibited roles")
    if access["state"] == "available" and access["terms_state"] not in {
        "accepted",
        "not_required",
    }:
        errors.append("available source terms must be accepted or not required")
    return errors


def validate_registry(registry, manifests):
    """Validate the register and cross-source independence boundaries."""
    errors = _schema_errors(registry, REGISTRY_SCHEMA_PATH, "registry_schema")
    required = {
        "schema_version",
        "registry_id",
        "status",
        "manifest_schema",
        "raw_data_root",
        "raw_data_committed",
        "manifests",
        "cross_source_rules",
    }
    if not _object(registry, "registry", required, errors):
        return errors
    if registry["schema_version"] != SCHEMA_VERSION:
        errors.append("registry schema_version is unsupported")
    if registry["status"] != "engineering_sources_manifested_release_locked":
        errors.append("registry status must keep release locked")
    if registry["manifest_schema"] != SCHEMA_PATH.name:
        errors.append("registry must name the active manifest schema")
    if not str(registry["raw_data_root"]).startswith(".research_data/"):
        errors.append("registry raw data root must be private")
    if registry["raw_data_committed"] is not False:
        errors.append("registry cannot permit committed raw data")
    entries = registry["manifests"]
    if not isinstance(entries, list):
        errors.append("registry.manifests must be a list")
        return errors
    entry_ids = [item.get("source_id") for item in entries if isinstance(item, dict)]
    document_ids = [item.get("source_id") for item in manifests if isinstance(item, dict)]
    if len(entry_ids) != len(set(entry_ids)) or len(document_ids) != len(set(document_ids)):
        errors.append("source ids must be unique")
    if set(entry_ids) != set(document_ids):
        errors.append("registry entries and manifest documents must match")
    if set(document_ids) != REQUIRED_SOURCE_IDS:
        errors.append("registry must contain the complete approved source set")
    manifest_by_id = {item["source_id"]: item for item in manifests if isinstance(item, dict) and "source_id" in item}
    common_phone = manifest_by_id.get("common_phone_1_0", {})
    common_voice = manifest_by_id.get("common_voice_26_australian_english", {})
    cp_lineage = common_phone.get("lineage", {})
    cv_lineage = common_voice.get("lineage", {})
    if "common_voice_7" not in cp_lineage.get("derived_from", []):
        errors.append("Common Phone must record its Common Voice 7 lineage")
    if cp_lineage.get("lineage_group") != cv_lineage.get("lineage_group"):
        errors.append("Common Phone and Common Voice must share a lineage group")
    if cp_lineage.get("independence_claim") != "not_independent_of_lineage":
        errors.append("Common Phone cannot claim independence from Common Voice")
    # Every accent subset of the same release shares one lineage and one bar.
    # A comparison group is still Common Voice derived, so it can never become
    # the evidence that qualifies a model trained on Common Voice.
    for source_id in (
        "common_voice_26_british_english",
        "common_voice_26_american_english_male",
        "common_voice_26_american_english_female",
    ):
        subset = manifest_by_id.get(source_id, {})
        lineage = subset.get("lineage", {})
        if lineage.get("lineage_group") != cv_lineage.get("lineage_group"):
            errors.append(f"{source_id} must share the Common Voice lineage group")
        if lineage.get("independence_claim") != "not_independent_of_common_voice_family":
            errors.append(f"{source_id} cannot claim independence from Common Voice")
    american = [
        manifest_by_id.get("common_voice_26_american_english_male", {}),
        manifest_by_id.get("common_voice_26_american_english_female", {}),
    ]
    if not all(american):
        errors.append(
            "the American comparison needs both gender subsets or it is confounded"
        )
    rules = registry["cross_source_rules"]
    if not _object(
        rules,
        "cross_source_rules",
        {
            "duplicate_participant_or_clip_across_splits",
            "related_sources_count_as_independent",
            "model_seen_data_count_as_independent",
            "truth_classes_may_be_pooled",
        },
        errors,
    ):
        return errors
    expected = {
        "duplicate_participant_or_clip_across_splits": "blocked",
        "related_sources_count_as_independent": False,
        "model_seen_data_count_as_independent": False,
        "truth_classes_may_be_pooled": False,
    }
    for field, value in expected.items():
        if rules[field] != value:
            errors.append(f"cross_source_rules.{field} must remain {value}")
    return errors


def validate_registered_manifests(registry_path: Path = REGISTRY_PATH):
    try:
        registry, manifests = load_registered_manifests(registry_path)
    except (CorpusManifestValidationError, FileNotFoundError, json.JSONDecodeError) as exc:
        return [f"registered manifest load failed: {exc}"]
    errors = []
    for manifest in manifests:
        source_id = manifest.get("source_id", "unknown") if isinstance(manifest, dict) else "unknown"
        errors.extend(f"{source_id}: {error}" for error in validate_manifest(manifest))
    errors.extend(validate_registry(registry, manifests))
    return errors


def _sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_private_evidence(
    manifests, repository_root=REPOSITORY_ROOT, rehash_archives=False
):
    """Recheck ignored split artifacts and optional archive bytes on this machine."""
    repository_root = Path(repository_root).resolve()
    errors = []
    for manifest in manifests:
        source_id = manifest.get("source_id", "unknown")
        split = manifest.get("participant_split", {})
        if split.get("status") == "audited":
            relative = split.get("assignment_artifact")
            if not _inside_private_root(relative, repository_root):
                errors.append(f"{source_id}: private assignment path is unsafe")
            else:
                path = (repository_root / relative).resolve()
                if not path.is_file():
                    errors.append(f"{source_id}: private assignment is missing")
                else:
                    try:
                        document = _load_json(path)
                    except (OSError, json.JSONDecodeError) as exc:
                        errors.append(
                            f"{source_id}: private assignment cannot be read: {exc}"
                        )
                        document = None
                    if isinstance(document, dict):
                        if document.get("source_id") != source_id:
                            errors.append(
                                f"{source_id}: private assignment source does not match"
                            )
                        if document.get("contains_exact_age") is not False:
                            errors.append(
                                f"{source_id}: private assignment retains exact age"
                            )
                        actual_hash = canonical_json_sha256(document)
                        if actual_hash != split.get("assignment_sha256"):
                            errors.append(
                                f"{source_id}: private assignment SHA256 does not match"
                            )
                        assignments = document.get("assignments")
                        if not isinstance(assignments, dict) or not assignments:
                            errors.append(
                                f"{source_id}: private assignments are missing"
                            )
                        else:
                            counts = {name: 0 for name in SPLITS}
                            strata = {}
                            for participant_id, item in assignments.items():
                                if not isinstance(participant_id, str) or not isinstance(
                                    item, dict
                                ):
                                    errors.append(
                                        f"{source_id}: private assignment row is malformed"
                                    )
                                    continue
                                project_split = item.get("project_split")
                                stratum = item.get("source_stratum")
                                if project_split not in SPLITS or not isinstance(
                                    stratum, str
                                ):
                                    errors.append(
                                        f"{source_id}: private assignment row is invalid"
                                    )
                                    continue
                                counts[project_split] += 1
                                values = strata.setdefault(
                                    stratum, {name: 0 for name in SPLITS}
                                )
                                values[project_split] += 1
                            if counts != split.get("participant_counts"):
                                errors.append(
                                    f"{source_id}: private participant counts do not match"
                                )
                            if dict(sorted(strata.items())) != split.get("strata"):
                                errors.append(
                                    f"{source_id}: private split strata do not match"
                                )
        if manifest.get("access", {}).get("state") != "available":
            continue
        storage = manifest.get("governance", {}).get("local_storage")
        if not _inside_private_root(storage, repository_root):
            errors.append(f"{source_id}: private corpus storage is unsafe")
            continue
        storage_path = (repository_root / storage).resolve()
        for archive in manifest.get("archives", []):
            path = (storage_path / archive.get("filename", "")).resolve()
            try:
                path.relative_to(storage_path)
            except ValueError:
                errors.append(f"{source_id}: archive path escapes private storage")
                continue
            if not path.is_file():
                errors.append(f"{source_id}: private archive {path.name} is missing")
                continue
            if path.stat().st_size != archive.get("size_bytes"):
                errors.append(f"{source_id}: private archive {path.name} size differs")
            if rehash_archives and _sha256_file(path) != archive.get("local_sha256"):
                errors.append(f"{source_id}: private archive {path.name} SHA256 differs")
    return errors


def assert_valid_registered_manifests(registry_path: Path = REGISTRY_PATH):
    errors = validate_registered_manifests(registry_path)
    if errors:
        raise CorpusManifestValidationError("\n".join(errors))
    return load_registered_manifests(registry_path)
