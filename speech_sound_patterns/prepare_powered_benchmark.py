"""Prepare the powered checkpoint 22E4B sample without held-out clips.

Checkpoint 22E4 measured every eligible lane against the frozen checkpoint 22D
gates on 8 of the 77 available development adults and 4 of the 25 available
threshold-tuning adults, and recorded ``no_selection`` on 34 positive tuning
opportunities. This module builds the same benchmark on every non held-out
adult, so that result can be replicated at a sample size the gates were not
designed to punish.

Only the participant count changes. The split assignments, the selection seed,
the deterministic ordering, the truth definitions, the phone scope and the
canonical audio treatment are all the frozen checkpoint 22D machinery, reused
rather than reimplemented: this module calls ``prepare_benchmark`` itself with a
different sample policy and a different output root. The three secondary sources
supply non-gate evidence only and their selection has not changed, so the powered
manifest points at the identical canonical files instead of making a second copy,
after verifying every referenced hash.

The held-out participants stay sealed. Nothing here can establish pronunciation
correctness, acceptable variety, Australian performance, scientific validity or
product readiness.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from .benchmark import (
    BENCHMARK_SCHEMA_VERSION,
    FROZEN_BENCHMARK_MANIFEST_SHA256,
    PRIVATE_BENCHMARK_ROOT,
    canonical_json_sha256,
    load_benchmark_contract,
    load_phone_map,
    validate_frozen_private_benchmark_manifest,
    validate_private_benchmark_manifest,
)
from .corpus_manifest import load_registered_manifests, validate_private_evidence
from .feasibility import REPOSITORY_ROOT, canonical_json_bytes, file_sha256
from .prepare_benchmark import (
    BenchmarkPreparationError,
    FFMPEG_DEFAULT,
    MANIFEST_PATH as FROZEN_MANIFEST_PATH,
    _prepare_speechocean,
    _safe_write,
)


MODULE_ROOT = Path(__file__).parent
SAMPLE_CONTRACT_PATH = MODULE_ROOT / "benchmark-powered-sample-contract-v1.0.0.json"
POWERED_ROOT = PRIVATE_BENCHMARK_ROOT / "v2"
POWERED_MANIFEST_PATH = PRIVATE_BENCHMARK_ROOT / "benchmark-manifest-v1.1.0.json"
REUSED_SOURCE_IDS = (
    "acted_clear_speech",
    "common_phone_1_0",
    "common_voice_26_australian_english",
)


def load_sample_contract(path=SAMPLE_CONTRACT_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_sample_contract(document):
    """Return every structural or safety error in the frozen powered sample rules."""
    errors = []
    required = {
        "schema_version",
        "sample_id",
        "checkpoint",
        "status",
        "declared_before_the_sample_existed",
        "purpose",
        "declaration",
        "source_id",
        "split_source",
        "sample_policy",
        "sample_shape",
        "held_out",
        "child_policy",
        "superset_claim",
        "secondary_sources",
        "truth_and_metric_rules",
        "selection_integrity",
        "release_boundaries",
    }
    if not isinstance(document, dict):
        return ["powered sample contract must be an object"]
    if set(document) != required:
        errors.append("powered sample contract fields do not match the frozen schema")
        if not required.issubset(document):
            return errors

    if document["schema_version"] != "1.0.0":
        errors.append("powered sample contract schema is unsupported")
    if document["checkpoint"] != "22E4B":
        errors.append("powered sample contract checkpoint must be 22E4B")
    if document["status"] != "sample_rules_frozen_before_the_sample_was_built":
        errors.append("the powered sample rules must be frozen before the sample")
    if document["declared_before_the_sample_existed"] is not True:
        errors.append(
            "the powered sample contract is only meaningful if it was declared "
            "before the sample existed"
        )
    if document["source_id"] != "speechocean762":
        errors.append("the powered gate sample source must remain speechocean762")

    declaration = document["declaration"]
    for field in (
        "this_replaces_an_underpowered_estimate",
        "whatever_this_produces_is_the_reported_result",
        "a_repeat_until_something_passes_is_prohibited",
    ):
        if declaration.get(field) is not True:
            errors.append(f"declaration.{field} must remain true")
    if declaration.get("gates_may_be_changed") is not False:
        errors.append("declaration.gates_may_be_changed must remain false")

    split_source = document["split_source"]
    for field in (
        "assignments_unchanged",
        "participant_exclusive",
    ):
        if split_source.get(field) is not True:
            errors.append(f"split_source.{field} must remain true")
    if split_source.get("reassignment_of_any_participant_prohibited") is not True:
        errors.append("a participant may never be reassigned to another split")

    held_out = document["held_out"]
    if held_out.get("held_out_access_allowed") is not False:
        errors.append("held_out.held_out_access_allowed must remain false")
    if held_out.get("unsealed_at") != "22H":
        errors.append("the held out set must stay reserved for checkpoint 22H")

    child = document["child_policy"]
    if child.get("child_rows_used_for_selection_or_thresholds") is not False:
        errors.append("child rows may never enter selection or thresholds")

    integrity = document["selection_integrity"]
    if integrity.get("selection_uses_labels_or_model_outputs") is not False:
        errors.append("sample selection cannot use labels or model outputs")
    if integrity.get("sample_may_be_rebuilt_to_change_a_result") is not False:
        errors.append("the sample may not be rebuilt to change a result")
    if integrity.get("seed_changed") is not False:
        errors.append("the selection seed may not change")

    rules = document["truth_and_metric_rules"]
    for field in (
        "expert_label_policy_changed",
        "phone_scope_changed",
        "alignment_changed",
        "metric_definitions_changed",
    ):
        if rules.get(field) is not False:
            errors.append(f"truth_and_metric_rules.{field} must remain false")
    if rules.get("benchmark_contract_sha256") != file_sha256(
        MODULE_ROOT / "benchmark-contract-v1.0.0.json"
    ):
        errors.append("the inherited benchmark contract identity changed")

    if document["secondary_sources"].get("may_enter_selection_gates") is not False:
        errors.append("secondary source evidence may never enter a selection gate")

    for field, value in document["release_boundaries"].items():
        if value is not False:
            errors.append(f"release_boundaries.{field} must remain false")

    policy = document["sample_policy"].get("speechocean762", {})
    if policy.get("clips_per_selected_participant") != 20:
        errors.append("the powered sample keeps twenty clips per participant")
    strata = policy.get("source_strata", [])
    for field in (
        "development_participants_per_source_stratum",
        "threshold_tuning_participants_per_source_stratum",
    ):
        counts = policy.get(field)
        if not isinstance(counts, dict) or set(counts) != set(strata):
            errors.append(f"sample_policy.speechocean762.{field} is malformed")
    return errors


def assert_valid_sample_contract(document=None):
    document = load_sample_contract() if document is None else document
    errors = validate_sample_contract(document)
    if errors:
        raise BenchmarkPreparationError("; ".join(errors))
    return document


def sample_expectation(contract):
    """Translate the frozen powered sample rules into a manifest expectation."""
    policy = contract["sample_policy"]["speechocean762"]
    development = policy["development_participants_per_source_stratum"]
    tuning = policy["threshold_tuning_participants_per_source_stratum"]
    clips_per_participant = policy["clips_per_selected_participant"]
    speechocean_clips = clips_per_participant * (
        sum(development.values()) + sum(tuning.values())
    )
    reused = contract["secondary_sources"]["clip_counts"]
    return {
        "sample_id": contract["sample_id"],
        "clip_counts": {"speechocean762": speechocean_clips, **reused},
        "speechocean_clips_per_participant": clips_per_participant,
        "speechocean_participants": {
            "development": dict(development),
            "threshold_tuning": dict(tuning),
        },
    }


def _frozen_manifest():
    document = json.loads(FROZEN_MANIFEST_PATH.read_text(encoding="utf-8"))
    errors = validate_frozen_private_benchmark_manifest(
        document, FROZEN_BENCHMARK_MANIFEST_SHA256
    )
    if errors:
        raise BenchmarkPreparationError(
            "the frozen checkpoint 22E4 manifest is not intact: " + "; ".join(errors)
        )
    return document


def _reused_sources(frozen):
    """Return the unchanged secondary sources after re-verifying every file."""
    by_id = {source["source_id"]: source for source in frozen["sources"]}
    reused = []
    for source_id in REUSED_SOURCE_IDS:
        source = by_id[source_id]
        reference_path = REPOSITORY_ROOT / source["private_reference_path"]
        if file_sha256(reference_path) != source["private_reference_sha256"]:
            raise BenchmarkPreparationError(
                f"reused source {source_id} reference file changed on disk"
            )
        for clip in source["clips"]:
            for path_field, hash_field in (
                ("canonical_audio_path", "canonical_audio_sha256"),
                ("intended_text_path", "intended_text_sha256"),
            ):
                path = REPOSITORY_ROOT / clip[path_field]
                if file_sha256(path) != clip[hash_field]:
                    raise BenchmarkPreparationError(
                        f"reused clip {clip['safe_id']} {path_field} changed on disk"
                    )
        reused.append(source)
    return reused


def _superset_report(frozen, powered):
    """Prove the powered sample contains every checkpoint 22E4 SpeechOcean clip."""
    frozen_source = next(
        source for source in frozen["sources"] if source["source_id"] == "speechocean762"
    )
    frozen_records = {clip["private_record_id"] for clip in frozen_source["clips"]}
    powered_records = {clip["private_record_id"] for clip in powered["clips"]}
    missing = sorted(frozen_records - powered_records)
    if missing:
        raise BenchmarkPreparationError(
            f"the powered sample dropped {len(missing)} checkpoint 22E4 clips"
        )
    frozen_participants = {
        clip["private_participant_id"] for clip in frozen_source["clips"]
    }
    powered_participants = {
        clip["private_participant_id"] for clip in powered["clips"]
    }
    if not frozen_participants <= powered_participants:
        raise BenchmarkPreparationError(
            "the powered sample dropped a checkpoint 22E4 participant"
        )
    frozen_assignment = {
        clip["private_record_id"]: (clip["project_split"], clip["source_stratum"])
        for clip in frozen_source["clips"]
    }
    powered_assignment = {
        clip["private_record_id"]: (clip["project_split"], clip["source_stratum"])
        for clip in powered["clips"]
    }
    moved = sorted(
        record
        for record, assignment in frozen_assignment.items()
        if powered_assignment[record] != assignment
    )
    if moved:
        raise BenchmarkPreparationError(
            f"{len(moved)} checkpoint 22E4 clips changed split or stratum"
        )
    return {
        "checkpoint_22e4_records": len(frozen_records),
        "checkpoint_22e4_records_retained": len(frozen_records),
        "checkpoint_22e4_participants_retained": len(frozen_participants),
        "powered_records": len(powered_records),
        "records_added": len(powered_records - frozen_records),
        "any_record_moved_split_or_stratum": False,
    }


def _shape_report(powered_source):
    participants = defaultdict(set)
    clips = Counter()
    for clip in powered_source["clips"]:
        key = (clip["project_split"], clip["source_stratum"])
        participants[key].add(clip["private_participant_id"])
        clips[key] += 1
    return {
        "participants": {
            f"{split}:{stratum}": len(value)
            for (split, stratum), value in sorted(participants.items())
        },
        "clips": {
            f"{split}:{stratum}": count for (split, stratum), count in sorted(clips.items())
        },
        "adult_clips": sum(
            count for (_, stratum), count in clips.items() if "adult" in stratum
        ),
        "child_clips": sum(
            count for (_, stratum), count in clips.items() if "child" in stratum
        ),
        "total_audio_seconds": round(
            sum(clip["duration_s"] for clip in powered_source["clips"]), 3
        ),
        "adult_audio_seconds": round(
            sum(
                clip["duration_s"]
                for clip in powered_source["clips"]
                if "adult" in clip["source_stratum"]
            ),
            3,
        ),
    }


def prepare_powered_benchmark(ffmpeg=FFMPEG_DEFAULT):
    sample_contract = assert_valid_sample_contract()
    contract = load_benchmark_contract()
    phone_map = load_phone_map()
    if not Path(ffmpeg).is_file():
        raise BenchmarkPreparationError("ffmpeg executable is unavailable")
    _, manifests = load_registered_manifests()
    private_errors = validate_private_evidence(manifests)
    if private_errors:
        raise BenchmarkPreparationError("; ".join(private_errors))
    if POWERED_ROOT.exists() or POWERED_MANIFEST_PATH.exists():
        raise BenchmarkPreparationError(
            "powered benchmark output already exists; do not overwrite frozen evidence"
        )
    frozen = _frozen_manifest()

    powered_source = _prepare_speechocean(
        Path(ffmpeg),
        contract,
        policy=sample_contract["sample_policy"]["speechocean762"],
        root=POWERED_ROOT,
    )
    superset = _superset_report(frozen, powered_source)
    shape = _shape_report(powered_source)

    manifest = {
        "schema_version": BENCHMARK_SCHEMA_VERSION,
        "protocol_id": "speech_sound_patterns_developer_benchmark_v1",
        "selection_seed": contract["split_policy"]["selection_seed"],
        "benchmark_contract_sha256": canonical_json_sha256(contract),
        "phone_map_sha256": canonical_json_sha256(phone_map),
        "held_out_evaluation_accessed": False,
        "selection_used_labels_or_outputs": False,
        "sources": [powered_source, *_reused_sources(frozen)],
    }
    errors = validate_private_benchmark_manifest(
        manifest, expectation=sample_expectation(sample_contract)
    )
    if errors:
        raise BenchmarkPreparationError("; ".join(errors))
    _safe_write(POWERED_MANIFEST_PATH, canonical_json_bytes(manifest))
    return manifest, superset, shape


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ffmpeg", type=Path, default=FFMPEG_DEFAULT)
    args = parser.parse_args()
    manifest, superset, shape = prepare_powered_benchmark(args.ffmpeg.resolve())
    total = sum(len(source["clips"]) for source in manifest["sources"])
    print(f"Prepared the powered checkpoint 22E4B sample: {total} clips")
    print(f"Private manifest SHA256: {canonical_json_sha256(manifest)}")
    print(f"Adult clips: {shape['adult_clips']}  child clips: {shape['child_clips']}")
    print(
        "Adult audio seconds: "
        f"{shape['adult_audio_seconds']}  total: {shape['total_audio_seconds']}"
    )
    for key, value in shape["participants"].items():
        print(f"  {key}: {value} participants, {shape['clips'][key]} clips")
    print(
        "Checkpoint 22E4 records retained: "
        f"{superset['checkpoint_22e4_records_retained']} of "
        f"{superset['checkpoint_22e4_records']}; added {superset['records_added']}"
    )
    print("Held out evaluation participants were not selected or scored.")


if __name__ == "__main__":
    main()
