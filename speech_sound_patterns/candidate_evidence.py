"""Safe aggregate evidence audit for the checkpoint 22G candidate extractor.

The audit runs before any threshold or repeated-relation rule search. It asks
whether the already permitted development and tuning evidence can support the
controlled-word task defined by the prompt pack. It cannot: the few prompt-pack
word occurrences are embedded in sentences, no participant supplies two
different pack words, and the available expert truth is coarse rather than an
exact produced-phone feature relation.

Only aggregate counts leave the private research directory. Participant,
recording, utterance and row identifiers never enter the committed report.
"""

from __future__ import annotations

import copy
import json
from collections import Counter, defaultdict
from pathlib import Path

from .candidate_artifact import (
    CONTRACT_PATH,
    CONTRACT_SHA256,
    RULE_STATUS,
    CandidateArtifactError,
    load_candidate_contract,
)
from .feasibility import canonical_json_bytes, file_sha256
from .prompt_pack_validate import PACK_PATH, validate_pack


MODULE_ROOT = Path(__file__).resolve().parent
REPORT_PATH = MODULE_ROOT / "candidate-evidence-v1.0.0.json"
REPORT_ID = "speech_sound_candidate_evidence"
REPORT_VERSION = "1.0.0"
REPORT_STATUS = "adequacy_failed_before_any_rule_search"

PRIVATE_IDENTIFIER_KEYS = {
    "private_participant_id",
    "private_utterance_id",
    "safe_id",
    "canonical_audio_path",
    "participant_id",
    "session_id",
    "attempt_id",
    "trial_id",
    "recording_id",
}


def _read_json(path):
    path = Path(path)
    if not path.is_file():
        raise CandidateArtifactError(f"required evidence is missing: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CandidateArtifactError(f"required evidence is unreadable: {path}") from exc


def _frozen_path(record):
    relative = record.get("private_path") or record.get("path")
    if not isinstance(relative, str):
        raise CandidateArtifactError("frozen evidence path is invalid")
    if relative.startswith(".research_data/"):
        return MODULE_ROOT.parent / relative
    return MODULE_ROOT / relative


def _load_frozen(contract, key):
    record = contract["frozen_inputs"][key]
    path = _frozen_path(record)
    if file_sha256(path) != record["sha256"]:
        raise CandidateArtifactError(f"frozen {key} checksum changed")
    return _read_json(path)


def _pack_words(contract):
    pack = _read_json(PACK_PATH)
    errors = validate_pack(pack)
    if errors:
        raise CandidateArtifactError("prompt pack is invalid:\n" + "\n".join(errors))
    if file_sha256(PACK_PATH) != contract["frozen_inputs"]["prompt_pack"]["sha256"]:
        raise CandidateArtifactError("frozen prompt pack checksum changed")
    return {item["word"].casefold(): item for item in pack["words"]}


def _assert_source_bindings(expected, relations, source, registry, corpus):
    if {
        "source_id": "speechocean762",
        "path": "speechocean762-v1.2.0.json",
    } not in registry.get("manifests", []):
        raise CandidateArtifactError(
            "corpus registry no longer binds the SpeechOcean manifest"
        )
    if (
        corpus.get("source_id") != "speechocean762"
        or corpus.get("access", {}).get("state") != "available"
        or corpus.get("licence", {}).get("state")
        != "verified_for_declared_role"
        or corpus.get("licence", {}).get("spdx_id") != "CC-BY-4.0"
        or corpus.get("licence", {}).get("commercial_use_permitted") is not True
        or corpus.get("participant_split", {}).get("frozen_held_out") is not True
    ):
        raise CandidateArtifactError(
            "SpeechOcean access, licence or split provenance changed"
        )
    required_roles = {
        "participant_exclusive_development",
        "participant_exclusive_threshold_tuning",
    }
    if not required_roles <= set(
        corpus.get("governance", {}).get("permitted_roles", [])
    ):
        raise CandidateArtifactError(
            "SpeechOcean development or tuning role is no longer permitted"
        )
    if expected.get("held_out_participants") != 0:
        raise CandidateArtifactError("expected manifest accesses held-out participants")
    if relations.get("held_out_evaluation") is not False:
        raise CandidateArtifactError("relation evidence accesses held-out evaluation")
    if set(record.get("project_split") for record in source.get("records", [])) - {
        "development",
        "threshold_tuning",
    }:
        raise CandidateArtifactError("source reference contains a forbidden split")
    for document in (expected, relations, source):
        if document.get("source_id") != "speechocean762":
            raise CandidateArtifactError("candidate evidence source identity changed")
    expected_ids = {item["safe_id"] for item in expected.get("clips", [])}
    relation_ids = {item["safe_id"] for item in relations.get("target_rows", [])}
    source_ids = {item["safe_id"] for item in source.get("records", [])}
    if (
        len(expected_ids) != len(expected.get("clips", []))
        or len(source_ids) != len(source.get("records", []))
        or expected_ids != source_ids
        or not relation_ids <= source_ids
    ):
        raise CandidateArtifactError("frozen source rows no longer join exactly")
    expected_by_id = {item["safe_id"]: item for item in expected["clips"]}
    source_by_id = {item["safe_id"]: item for item in source["records"]}
    for safe_id in expected_ids:
        expected_row = expected_by_id[safe_id]
        source_row = source_by_id[safe_id]
        for field in (
            "private_participant_id",
            "project_split",
            "source_stratum",
        ):
            if expected_row.get(field) != source_row.get(field):
                raise CandidateArtifactError(
                    f"frozen source {field} join changed"
                )
        words = source_row.get("words")
        targets = expected_row.get("targets")
        if not isinstance(words, list) or not isinstance(targets, list):
            raise CandidateArtifactError(
                "frozen source word or target collection is invalid"
            )
        if any(
            not isinstance(word, dict)
            or word.get("word_index") != index
            for index, word in enumerate(words)
        ):
            raise CandidateArtifactError(
                "frozen source word indexes are not contiguous"
            )
        target_keys = [
            (target.get("word_index"), target.get("local_index"))
            for target in targets
        ]
        if len(target_keys) != len(set(target_keys)):
            raise CandidateArtifactError(
                "frozen expected target indexes are duplicated"
            )
        if any(
            not isinstance(target.get("word_index"), int)
            or isinstance(target.get("word_index"), bool)
            or target["word_index"] < 0
            or target["word_index"] >= len(words)
            for target in targets
        ):
            raise CandidateArtifactError(
                "frozen expected target leaves its source words"
            )
    for row in relations["target_rows"]:
        expected_row = expected_by_id[row["safe_id"]]
        source_row = source_by_id[row["safe_id"]]
        for field in (
            "private_participant_id",
            "project_split",
            "source_stratum",
        ):
            if row.get(field) != source_row.get(field):
                raise CandidateArtifactError(
                    f"frozen relation {field} join changed"
                )
        matching_targets = [
            target
            for target in expected_row["targets"]
            if target.get("word_index") == row.get("word_index")
            and target.get("local_index") == row.get("target_index")
        ]
        if len(matching_targets) != 1:
            raise CandidateArtifactError(
                "frozen relation target index join changed"
            )


def _partition_record(split, occurrences, relation_rows):
    word_counts = Counter(item["word"] for item in occurrences)
    participants_to_words = defaultdict(set)
    for item in occurrences:
        participants_to_words[item["participant"]].add(item["word"])
    truth = Counter(item["truth"] for item in relation_rows)
    return {
        "project_split": split,
        "adult_prompt_pack_word_occurrences": len(occurrences),
        "adult_distinct_recordings": len({item["recording"] for item in occurrences}),
        "adult_distinct_participants": len(
            {item["participant"] for item in occurrences}
        ),
        "distinct_prompt_pack_words_observed": len(word_counts),
        "prompt_pack_word_occurrences": {
            word: word_counts[word] for word in sorted(word_counts)
        },
        "prompt_pack_expected_sound_opportunities": sum(
            item["expected_sound_opportunities"] for item in occurrences
        ),
        "prompt_pack_scorable_sound_opportunities": sum(
            item["scorable_sound_opportunities"] for item in occurrences
        ),
        "prompt_pack_unscorable_sound_opportunities": sum(
            item["unscorable_sound_opportunities"] for item in occurrences
        ),
        "repeated_support_denominator_available": False,
        "participants_with_two_distinct_prompt_pack_words": sum(
            len(words) >= 2 for words in participants_to_words.values()
        ),
        "expert_target_truth": {
            "positive": truth["positive"],
            "negative": truth["negative"],
            "unscorable": truth["unscorable"],
        },
        "exact_feature_relation_truth_rows": 0,
        "isolated_controlled_word_recordings": 0,
    }


def build_candidate_evidence_report(*, contract=None):
    """Recompute the safe adequacy result from the frozen private evidence."""
    contract = contract or load_candidate_contract()
    expected = _load_frozen(contract, "powered_expected_manifest")
    relations = _load_frozen(contract, "powered_expert_relations")
    source = _load_frozen(contract, "powered_source_reference")
    registry = _load_frozen(contract, "corpus_registry")
    corpus = _load_frozen(contract, "speechocean762_corpus_manifest")
    _assert_source_bindings(
        expected,
        relations,
        source,
        registry,
        corpus,
    )
    words = _pack_words(contract)

    adult_occurrences = defaultdict(list)
    occurrence_keys = set()
    for record in source["records"]:
        if not str(record.get("source_stratum", "")).startswith("source_adult_"):
            continue
        split = record["project_split"]
        for word in record.get("words", []):
            normalized = str(word.get("text", "")).casefold()
            if normalized not in words:
                continue
            key = (record["safe_id"], word["word_index"])
            occurrence_keys.add(key)
            adult_occurrences[split].append(
                {
                    "word": normalized,
                    "participant": record["private_participant_id"],
                    "recording": record["safe_id"],
                    "expected_sound_opportunities": len(
                        words[normalized]["opportunities"]
                    ),
                    "scorable_sound_opportunities": sum(
                        opportunity["state"] == "scorable"
                        for opportunity in words[normalized]["opportunities"]
                    ),
                    "unscorable_sound_opportunities": sum(
                        opportunity["state"] == "unscorable"
                        for opportunity in words[normalized]["opportunities"]
                    ),
                }
            )

    relation_rows = defaultdict(list)
    for row in relations["target_rows"]:
        if row.get("age_stratum") != "adult":
            continue
        if (row["safe_id"], row["word_index"]) not in occurrence_keys:
            continue
        relation_rows[row["project_split"]].append(row)

    partitions = [
        _partition_record(
            split,
            adult_occurrences[split],
            relation_rows[split],
        )
        for split in ("development", "threshold_tuning")
    ]
    totals = {
        "adult_prompt_pack_word_occurrences": sum(
            item["adult_prompt_pack_word_occurrences"] for item in partitions
        ),
        "adult_distinct_participants": sum(
            item["adult_distinct_participants"] for item in partitions
        ),
        "participants_with_two_distinct_prompt_pack_words": sum(
            item["participants_with_two_distinct_prompt_pack_words"]
            for item in partitions
        ),
        "expert_target_truth": {
            truth: sum(item["expert_target_truth"][truth] for item in partitions)
            for truth in ("positive", "negative", "unscorable")
        },
        "prompt_pack_expected_sound_opportunities": sum(
            item["prompt_pack_expected_sound_opportunities"]
            for item in partitions
        ),
        "prompt_pack_scorable_sound_opportunities": sum(
            item["prompt_pack_scorable_sound_opportunities"]
            for item in partitions
        ),
        "prompt_pack_unscorable_sound_opportunities": sum(
            item["prompt_pack_unscorable_sound_opportunities"]
            for item in partitions
        ),
        "repeated_support_denominator_available": False,
    }
    checks = [
        {
            "check": "task_matched_controlled_isolated_word_recordings",
            "passed": False,
            "evidence": "All matching words are embedded in multiword source utterances.",
        },
        {
            "check": "participant_exclusive_development_and_threshold_tuning",
            "passed": True,
            "evidence": "The frozen expected manifest preserves its participant exclusive split.",
        },
        {
            "check": "independent_exact_produced_feature_relation_truth",
            "passed": False,
            "evidence": "The frozen expert truth is coarse target relation truth, not an exact produced feature relation.",
        },
        {
            "check": "two_distinct_prompt_pack_words_for_an_eligible_participant",
            "passed": False,
            "evidence": "No adult participant supplies two different prompt pack words in either permitted partition.",
        },
        {
            "check": "minimum_true_positives_attainable_in_both_partitions",
            "passed": False,
            "evidence": "Development has one positive target and tuning has none, below the unchanged minimum of seven in each partition.",
        },
        {
            "check": "support_and_opportunity_denominators_visible",
            "passed": False,
            "evidence": "Prompt pack opportunity counts can be reconstructed, but no task matched candidate system and exact relation truth exist from which to calculate a repeated support denominator.",
        },
    ]
    return {
        "schema_version": "1.0.0",
        "report_id": REPORT_ID,
        "report_version": REPORT_VERSION,
        "checkpoint": "22G",
        "status": REPORT_STATUS,
        "contract": {
            "path": CONTRACT_PATH.name,
            "sha256": CONTRACT_SHA256,
            "version": contract["contract_version"],
        },
        "frozen_inputs": {
            key: {
                "sha256": contract["frozen_inputs"][key]["sha256"],
                "held_out_accessed": False,
            }
            for key in (
                "prompt_pack",
                "selection_record",
                "corpus_registry",
                "speechocean762_corpus_manifest",
                "powered_expected_manifest",
                "powered_expert_relations",
                "powered_source_reference",
            )
        },
        "source_provenance": {
            "source_id": "speechocean762",
            "corpus_registry_sha256": contract["frozen_inputs"][
                "corpus_registry"
            ]["sha256"],
            "corpus_manifest_sha256": contract["frozen_inputs"][
                "speechocean762_corpus_manifest"
            ]["sha256"],
            "development_tuning_whitelist_sha256": contract["frozen_inputs"][
                "powered_expected_manifest"
            ]["sha256"],
            "source_reference_sha256": contract["frozen_inputs"][
                "powered_source_reference"
            ]["sha256"],
            "expert_relations_sha256": contract["frozen_inputs"][
                "powered_expert_relations"
            ]["sha256"],
            "full_held_out_split_assignment_accessed": False,
        },
        "sample": {
            "population": "adults_only_for_rule_adequacy",
            "project_splits": ["development", "threshold_tuning"],
            "prompt_pack_word_count": len(words),
            "held_out_participants_or_labels_accessed": 0,
            "owner_recordings_used_for_selection": 0,
            "synthetic_fixtures_used_for_selection": 0,
            "source_truth_class": relations["truth_class"],
            "source_relation_class": relations["relation_class"],
        },
        "partitions": partitions,
        "totals": totals,
        "evidence_adequacy": {
            "runs_before_any_threshold_or_repeated_rule_search": True,
            "checks": checks,
            "passed": False,
            "failed_checks": [
                item["check"] for item in checks if item["passed"] is False
            ],
        },
        "decision": {
            "status": RULE_STATUS,
            "threshold_search_performed": False,
            "repeated_rule_search_performed": False,
            "held_out_evaluation_performed": False,
            "candidate_system_selected": False,
            "possible_relation_candidate_emission_enabled": False,
            "repeated_relation_candidate_emission_enabled": False,
        },
        "frozen_candidate_rule": {
            "system": None,
            "threshold": None,
            "mapping": None,
            "feature_relation": None,
            "provider_configuration": None,
            "repeated_relation_minimum": None,
        },
        "limitations": [
            "The available matching words were not elicited with the controlled isolated word task.",
            "The expert labels describe coarse concern at an expected target and do not establish the exact produced phone or feature relation.",
            "No adult participant supplies two distinct prompt pack words, so within participant repetition cannot be measured.",
            "The prompt pack is unreviewed and inactive for product use.",
            "This adequacy failure is a stop, not permission to tune against sparse evidence or inspect held out participants.",
        ],
        "release_boundaries": copy.deepcopy(contract["release_boundaries"]),
    }


def _walk_keys(value):
    if isinstance(value, dict):
        for key, nested in value.items():
            yield key
            yield from _walk_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_keys(nested)


def validate_candidate_evidence_report(document, *, contract=None):
    """Validate the report by recomputing it from every frozen private input."""
    errors = []
    if not isinstance(document, dict):
        return ["candidate evidence report must be an object"]
    try:
        expected = build_candidate_evidence_report(contract=contract)
    except (CandidateArtifactError, KeyError, TypeError, ValueError) as exc:
        return [str(exc)]
    if document != expected:
        errors.append("candidate evidence report does not match the frozen evidence")
    leaked = sorted(PRIVATE_IDENTIFIER_KEYS & set(_walk_keys(document)))
    if leaked:
        errors.append(
            "candidate evidence report leaks private or row level fields: "
            + ", ".join(leaked)
        )
    release_boundaries = document.get("release_boundaries")
    if not isinstance(release_boundaries, dict):
        errors.append("candidate evidence report release boundaries are invalid")
    elif any(release_boundaries.values()):
        errors.append("candidate evidence report opens a release boundary")
    return errors


def assert_valid_candidate_evidence_report(document, *, contract=None):
    errors = validate_candidate_evidence_report(document, contract=contract)
    if errors:
        raise CandidateArtifactError("\n".join(errors))
    return document


def write_candidate_evidence_report(path=REPORT_PATH):
    """Write a new report; a committed report is never silently overwritten."""
    path = Path(path)
    if path.exists():
        raise CandidateArtifactError("candidate evidence report already exists")
    report = build_candidate_evidence_report()
    path.write_bytes(canonical_json_bytes(report))
    return path


def validate_committed_candidate_evidence_report(path=REPORT_PATH):
    document = _read_json(path)
    return validate_candidate_evidence_report(document)
