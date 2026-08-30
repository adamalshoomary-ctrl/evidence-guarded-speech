"""Build the aggregate, commit-safe report for checkpoint 22C.

All clip-level evidence stays in ignored private storage.  This command fails
closed if repeatability or boundary checks fail and emits only aggregate facts.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import Counter
from pathlib import Path

from .feasibility import (
    REPOSITORY_ROOT,
    FROZEN_SAMPLE_MANIFEST_SHA256,
    canonical_json_bytes,
    file_sha256,
    validate_frozen_private_sample_manifest,
    validate_safe_feasibility_report,
)
from .mfa_probe import ACOUSTIC_SHA256, DICTIONARY_SHA256
from .panphon_probe import EXPECTED_DATA_HASHES
from .phoneticxeus_probe import (
    MODEL_REVISION,
    MODEL_TREE_SHA256,
    MODEL_WEIGHTS_SHA256,
    MODEL_WEIGHTS_SIZE,
)


EXPECTED_SOURCES = {
    "acted_clear_speech_2013": {
        "clip_count": 3,
        "role": "hand_corrected_timing_fixture_only",
    },
    "common_phone_1_0": {
        "clip_count": 3,
        "role": "broad_phone_engineering_development_only",
    },
    "common_voice_26_australian_english": {
        "clip_count": 3,
        "role": "australian_robustness_development_only",
    },
    "owner_controlled_integration": {
        "clip_count": 1,
        "role": "functional_integration_only_unknown_intended_text",
    },
    "speechocean762": {
        "clip_count": 3,
        "role": "expert_corpus_development_audio_only_in_this_checkpoint",
    },
}


def _read(path, probe_id=None):
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if probe_id is not None and document.get("probe_id") != probe_id:
        raise ValueError(f"private evidence is not {probe_id}")
    return document


def _all_exact_within(document, digest_field):
    return all(
        len({repeat[digest_field] for repeat in clip["repeats"]}) == 1
        for clip in document["clips"]
    )


def _percentile_middle(values):
    return float(statistics.median(values))


def _expected_probe_clips(manifest, tool):
    expected = {}
    for source in manifest["sources"]:
        for clip in source["clips"]:
            if tool not in clip["eligible_tools"]:
                continue
            item = {
                "source_id": source["source_id"],
                "input_sha256": clip["canonical_audio_sha256"],
                "duration_s": float(clip["duration_s"]),
            }
            if tool == "mfa":
                item["intended_text_sha256"] = clip["intended_text_sha256"]
            expected[clip["safe_id"]] = item
    return expected


def _bind_probe_clips(document, expected, *, require_text=False):
    actual = {}
    for clip in document["clips"]:
        safe_id = clip.get("safe_id")
        if safe_id in actual:
            raise ValueError("probe evidence repeats a private sample")
        item = {
            "source_id": clip.get("source_id"),
            "input_sha256": clip.get("input_sha256"),
            "duration_s": float(clip.get("duration_s")),
        }
        if require_text:
            item["intended_text_sha256"] = clip.get("intended_text_sha256")
        actual[safe_id] = item
    if actual != expected:
        raise ValueError("probe evidence is not bound to the frozen private sample")


def _source_summary(manifest):
    actual = {}
    total_duration = 0.0
    for source in manifest["sources"]:
        source_id = source["source_id"]
        clips = source["clips"]
        actual[source_id] = len(clips)
        total_duration += sum(float(clip["duration_s"]) for clip in clips)
    expected_counts = {
        source_id: item["clip_count"] for source_id, item in EXPECTED_SOURCES.items()
    }
    if actual != expected_counts:
        raise ValueError("private feasibility sample composition changed")
    return {
        "private_sample_manifest_sha256": FROZEN_SAMPLE_MANIFEST_SHA256,
        "selection": (
            "fixed_hash_selection_from_frozen_development_participants_without_"
            "using_labels_scores_or_outputs"
        ),
        "development_only": True,
        "independent_accuracy_evidence": False,
        "source_count": len(actual),
        "clip_count": sum(actual.values()),
        "total_audio_s": round(total_duration, 6),
        "sources": [
            {
                "source": source_id,
                "clip_count": EXPECTED_SOURCES[source_id]["clip_count"],
                "role": EXPECTED_SOURCES[source_id]["role"],
            }
            for source_id in sorted(EXPECTED_SOURCES)
        ],
        "held_out_participants_or_labels_inspected": False,
        "owner_clip_used_for_accuracy": False,
    }


def _phonetic_summary(
    mps_documents, cpu_document, evidence_root, expected_all, expected_cpu
):
    if len(mps_documents) != 3:
        raise ValueError("three fresh MPS process records are required")
    expected_versions = {
        "python": "3.10.20",
        "torch": "2.6.0",
        "torchaudio": "2.6.0",
        "transformers": "4.57.6",
        "huggingface_hub": "0.35.3",
        "safetensors": "0.8.0",
        "soundfile": "0.14.0",
        "numpy": "2.2.6",
    }
    expected_determinism = {
        "torch_seed": 0,
        "numpy_seed": 0,
        "torch_num_threads": 1,
        "deterministic_algorithms": True,
        "silent_mps_cpu_fallback": False,
    }
    expected_vocabulary = {
        "total_tokens": 428,
        "special_tokens": 4,
        "phone_tokens": 424,
        "sha256": "96c70e0f72c02aa882a6cf9083b2e1a007c37ff5890a94afc3bf0039748654c3",
    }
    for index, document in enumerate([*mps_documents, cpu_document]):
        if document["model_revision"] != MODEL_REVISION:
            raise ValueError("PhoneticXEUS model revision changed")
        if document["model_tree_sha256"] != MODEL_TREE_SHA256:
            raise ValueError("PhoneticXEUS model tree changed")
        if document["model_weights_sha256"] != MODEL_WEIGHTS_SHA256:
            raise ValueError("PhoneticXEUS model weights changed")
        expected_backend = "mps" if index < 3 else "cpu"
        if document.get("backend") != expected_backend:
            raise ValueError("PhoneticXEUS backend evidence changed")
        if document.get("versions") != expected_versions:
            raise ValueError("PhoneticXEUS dependency versions changed")
        if document.get("determinism") != expected_determinism:
            raise ValueError("PhoneticXEUS determinism settings changed")
        if document.get("vocabulary") != expected_vocabulary:
            raise ValueError("PhoneticXEUS vocabulary evidence changed")
        machine = document.get("machine", {})
        if (
            machine.get("machine") != "arm64"
            or machine.get("platform") != "macOS-26.5.2-arm64-arm-64bit"
            or machine.get("mps_built") is not True
            or machine.get("mps_available") is not True
        ):
            raise ValueError("PhoneticXEUS machine evidence changed")
        boundaries = document.get("claim_boundaries", {})
        if any(boundaries.values()) or set(boundaries) != {
            "phone_timestamps",
            "calibrated_confidence",
            "sequence_alternatives",
            "produced_phone_truth",
            "pronunciation_correctness",
        }:
            raise ValueError("PhoneticXEUS claim boundaries changed")
    first_mps = mps_documents[0]
    for document in mps_documents:
        _bind_probe_clips(document, expected_all)
    _bind_probe_clips(cpu_document, expected_cpu)
    expected_repeats = (10, 1, 1)
    for document, repeat_count in zip(mps_documents, expected_repeats):
        if any(len(clip["repeats"]) != repeat_count for clip in document["clips"]):
            raise ValueError("MPS repeat design changed")
        if not _all_exact_within(document, "logits_sha256"):
            raise ValueError("MPS logits were not exact within a process")
        if not all(
            repeat["frame_ids_exact_match_first"]
            and repeat["collapsed_ids_exact_match_first"]
            for clip in document["clips"]
            for repeat in clip["repeats"]
        ):
            raise ValueError("MPS repeat flags are not exact")
    if any(len(clip["repeats"]) != 3 for clip in cpu_document["clips"]):
        raise ValueError("CPU repeat design changed")
    if not _all_exact_within(cpu_document, "logits_sha256"):
        raise ValueError("CPU logits were not exact within the warm process")
    if not all(
        repeat["frame_ids_exact_match_first"]
        and repeat["collapsed_ids_exact_match_first"]
        for clip in cpu_document["clips"]
        for repeat in clip["repeats"]
    ):
        raise ValueError("CPU repeat flags are not exact")

    mps_maps = [
        {clip["safe_id"]: clip for clip in document["clips"]}
        for document in mps_documents
    ]
    if not all(set(item) == set(mps_maps[0]) for item in mps_maps[1:]):
        raise ValueError("MPS process clip sets differ")
    for safe_id in mps_maps[0]:
        logit_hashes = {
            item[safe_id]["repeats"][0]["logits_sha256"] for item in mps_maps
        }
        frame_hashes = {
            item[safe_id]["repeats"][0]["frame_argmax_sha256"] for item in mps_maps
        }
        collapsed = {
            tuple(item[safe_id]["collapsed_token_ids"]) for item in mps_maps
        }
        if len(logit_hashes) != 1 or len(frame_hashes) != 1 or len(collapsed) != 1:
            raise ValueError("PhoneticXEUS MPS fresh-process output changed")

    import torch
    from safetensors.torch import load_file

    cpu_map = {clip["safe_id"]: clip for clip in cpu_document["clips"]}
    cross_backend_deltas = []
    for safe_id, cpu_clip in cpu_map.items():
        mps_clip = mps_maps[0].get(safe_id)
        if mps_clip is None:
            raise ValueError("CPU comparison clip is missing from MPS evidence")
        cpu_path = evidence_root / "phoneticxeus" / "cpu-source-subset" / "logits" / f"cpu-{safe_id}.safetensors"
        mps_path = evidence_root / "phoneticxeus" / "mps-full-warm" / "logits" / f"mps-{safe_id}.safetensors"
        if file_sha256(cpu_path) != cpu_clip["logits_artifact_sha256"]:
            raise ValueError("CPU safetensors evidence identity changed")
        if file_sha256(mps_path) != mps_clip["logits_artifact_sha256"]:
            raise ValueError("MPS safetensors evidence identity changed")
        cpu_logits = load_file(str(cpu_path))["ctc_logits"]
        mps_logits = load_file(str(mps_path))["ctc_logits"]
        if cpu_logits.shape != mps_logits.shape:
            raise ValueError("CPU and MPS logit shapes differ")
        if not torch.equal(cpu_logits.argmax(-1), mps_logits.argmax(-1)):
            raise ValueError("CPU and MPS frame argmax paths differ")
        if cpu_clip["collapsed_token_ids"] != mps_clip["collapsed_token_ids"]:
            raise ValueError("CPU and MPS collapsed token paths differ")
        cross_backend_deltas.append(float((cpu_logits - mps_logits).abs().max()))

    mps_runtimes = [
        repeat["runtime_s"]
        for clip in first_mps["clips"]
        for repeat in clip["repeats"]
    ]
    cpu_runtimes = [
        repeat["runtime_s"]
        for clip in cpu_document["clips"]
        for repeat in clip["repeats"]
    ]
    mps_audio = sum(
        clip["duration_s"] * len(clip["repeats"])
        for clip in first_mps["clips"]
    )
    cpu_audio = sum(
        clip["duration_s"] * len(clip["repeats"])
        for clip in cpu_document["clips"]
    )
    return {
        "repeatability": {
            "mps_fresh_process_count": len(mps_documents),
            "mps_warm_inference_count": len(mps_runtimes),
            "mps_raw_logits_exact_within_and_across_processes": True,
            "cpu_clip_count": len(cpu_document["clips"]),
            "cpu_warm_inference_count": len(cpu_runtimes),
            "cpu_raw_logits_exact_within_process": True,
            "cpu_mps_comparison_clip_count": len(cpu_map),
            "cpu_mps_frame_argmax_exact": True,
            "cpu_mps_collapsed_tokens_exact": True,
            "cpu_mps_max_absolute_raw_logit_difference": round(
                max(cross_backend_deltas), 10
            ),
        },
        "runtime": {
            "mps_model_load_s_range": [
                round(min(item["model_load_seconds"] for item in mps_documents), 6),
                round(max(item["model_load_seconds"] for item in mps_documents), 6),
            ],
            "mps_inference_s_min": round(min(mps_runtimes), 6),
            "mps_inference_s_median": round(_percentile_middle(mps_runtimes), 6),
            "mps_inference_s_max": round(max(mps_runtimes), 6),
            "mps_inference_real_time_factor": round(sum(mps_runtimes) / mps_audio, 6),
            "cpu_inference_s_min": round(min(cpu_runtimes), 6),
            "cpu_inference_s_median": round(_percentile_middle(cpu_runtimes), 6),
            "cpu_inference_s_max": round(max(cpu_runtimes), 6),
            "cpu_inference_real_time_factor": round(sum(cpu_runtimes) / cpu_audio, 6),
        },
    }


def _mfa_summary(document, expected_clips):
    if document["mfa_version"] != "3.4.1":
        raise ValueError("MFA evidence version changed")
    if document["acoustic_model"]["sha256"] != ACOUSTIC_SHA256:
        raise ValueError("MFA acoustic evidence identity changed")
    if document["dictionary"]["sha256"] != DICTIONARY_SHA256:
        raise ValueError("MFA dictionary evidence identity changed")
    if document.get("mfa_environment_python_version") != "Python 3.11.15":
        raise ValueError("MFA environment Python changed")
    if document.get("execution") != {
        "num_jobs": 1,
        "multiprocessing": False,
        "threading": False,
        "speaker_adaptation": False,
        "textgrid_cleanup": False,
        "fresh_directory_each_repeat": True,
        "credential_free_environment": True,
    }:
        raise ValueError("MFA execution settings changed")
    if document.get("claim_boundaries") != {
        "expected_sequence_conditioned": True,
        "produced_phone_truth": False,
        "pronunciation_correctness": False,
        "australian_variant_truth": False,
        "product_timing_release": False,
    }:
        raise ValueError("MFA claim boundaries changed")
    _bind_probe_clips(document, expected_clips, require_text=True)
    if any(len(clip["repeats"]) != 3 for clip in document["clips"]):
        raise ValueError("MFA repeat design changed")
    if not _all_exact_within(document, "canonical_alignment_sha256"):
        raise ValueError("MFA alignment output was not repeatable")
    repeats = [repeat for clip in document["clips"] for repeat in clip["repeats"]]
    if len(repeats) != 36:
        raise ValueError("MFA repeat count changed")
    runtimes = [item["runtime_s"] for item in repeats]
    audio = sum(
        clip["duration_s"] * len(clip["repeats"])
        for clip in document["clips"]
    )
    first_repeats = [clip["repeats"][0] for clip in document["clips"]]
    return {
        "repeatability": {
            "clip_count": len(document["clips"]),
            "fresh_alignment_count": len(repeats),
            "canonical_alignment_exact_across_repeats": True,
        },
        "runtime": {
            "alignment_s_min": round(min(runtimes), 6),
            "alignment_s_median": round(_percentile_middle(runtimes), 6),
            "alignment_s_max": round(max(runtimes), 6),
            "alignment_real_time_factor": round(sum(runtimes) / audio, 6),
        },
        "intervals": {
            "word_count": sum(item["word_interval_count"] for item in first_repeats),
            "phone_count": sum(item["phone_interval_count"] for item in first_repeats),
            "lexical_phone_count": sum(
                item["lexical_phone_interval_count"] for item in first_repeats
            ),
            "silence_count": sum(item["silence_interval_count"] for item in first_repeats),
            "unknown_count": sum(item["unknown_phone_interval_count"] for item in first_repeats),
            "unlabeled_count": sum(item["unlabeled_interval_count"] for item in first_repeats),
            "clips_with_unknown": sum(
                item["unknown_phone_interval_count"] > 0 for item in first_repeats
            ),
            "clips_with_unlabeled": sum(
                item["unlabeled_interval_count"] > 0 for item in first_repeats
            ),
        },
        "max_rss_bytes": max(
            item["resource_use"]["maximum_resident_set_bytes"] for item in repeats
        ),
        "max_peak_footprint_bytes": max(
            item["resource_use"]["peak_memory_footprint_bytes"] for item in repeats
        ),
        "max_swaps": max(item["resource_use"]["swaps"] for item in repeats),
    }


def build_report(manifest_path, evidence_root, outer_metrics_path):
    manifest = _read(manifest_path)
    errors = validate_frozen_private_sample_manifest(manifest, REPOSITORY_ROOT)
    if errors:
        raise ValueError("; ".join(errors))
    source_summary = _source_summary(manifest)
    expected_phonetic = _expected_probe_clips(manifest, "phoneticxeus")
    expected_mfa = _expected_probe_clips(manifest, "mfa")
    mps_paths = (
        evidence_root / "phoneticxeus" / "mps-full-warm" / "phoneticxeus-mps-process.json",
        evidence_root / "phoneticxeus" / "mps-cold-2" / "phoneticxeus-mps-process.json",
        evidence_root / "phoneticxeus" / "mps-cold-3" / "phoneticxeus-mps-process.json",
    )
    mps_documents = [_read(path, "phoneticxeus_local_feasibility_v1") for path in mps_paths]
    cpu_document = _read(
        evidence_root / "phoneticxeus" / "cpu-source-subset" / "phoneticxeus-cpu-process.json",
        "phoneticxeus_local_feasibility_v1",
    )
    expected_cpu = {
        safe_id: item
        for safe_id, item in expected_phonetic.items()
        if safe_id.endswith("_001")
    }
    if len(expected_cpu) != 5:
        raise ValueError("CPU source subset identity changed")
    phonetic = _phonetic_summary(
        mps_documents,
        cpu_document,
        evidence_root,
        expected_phonetic,
        expected_cpu,
    )
    mfa_document = _read(
        evidence_root / "mfa" / "full-three-repeats-v2" / "mfa-process.json",
        "mfa_local_feasibility_v1",
    )
    mfa = _mfa_summary(mfa_document, expected_mfa)
    panphon = _read(
        evidence_root / "panphon" / "measured" / "observed-token-mapping.json",
        "panphon_observed_inventory_probe_v1",
    )
    if panphon["panphon_version"] != "0.22.2":
        raise ValueError("PanPhon evidence version changed")
    if panphon["packaged_data_sha256"] != EXPECTED_DATA_HASHES:
        raise ValueError("PanPhon packaged data identity changed")
    expected_panphon_inputs = sorted(
        [
            {
                "sha256": file_sha256(mps_paths[0]),
                "backend": "mps",
                "clip_count": len(expected_phonetic),
                "model_revision": MODEL_REVISION,
            },
            {
                "sha256": file_sha256(
                    evidence_root
                    / "phoneticxeus"
                    / "cpu-source-subset"
                    / "phoneticxeus-cpu-process.json"
                ),
                "backend": "cpu",
                "clip_count": len(expected_cpu),
                "model_revision": MODEL_REVISION,
            },
        ],
        key=lambda item: (item["backend"], item["sha256"]),
    )
    if panphon.get("input_documents") != expected_panphon_inputs:
        raise ValueError("PanPhon evidence is not bound to the PhoneticXEUS outputs")
    decisions = Counter(item["decision"] for item in panphon["classifications"])
    if decisions != {"identity_nfd": 55}:
        raise ValueError("observed PanPhon mapping is no longer exact and complete")
    outer = _read(outer_metrics_path)
    if set(outer) != {
        "schema_version",
        "measurement_tool",
        "units",
        "machine",
        "phoneticxeus_mps_full_warm",
        "phoneticxeus_mps_cold_2",
        "phoneticxeus_mps_cold_3",
        "phoneticxeus_cpu_source_subset",
        "panphon_observed_mapping",
    } or outer.get("schema_version") != "1.0.0" or outer.get(
        "measurement_tool"
    ) != "/usr/bin/time -l" or outer.get("units") != "bytes_and_seconds":
        raise ValueError("outer resource measurement identity changed")
    evidence_hashes = {
        "phoneticxeus_mps_full_warm": file_sha256(mps_paths[0]),
        "phoneticxeus_mps_cold_2": file_sha256(mps_paths[1]),
        "phoneticxeus_mps_cold_3": file_sha256(mps_paths[2]),
        "phoneticxeus_cpu_source_subset": file_sha256(
            evidence_root
            / "phoneticxeus"
            / "cpu-source-subset"
            / "phoneticxeus-cpu-process.json"
        ),
        "panphon_observed_mapping": file_sha256(
            evidence_root
            / "panphon"
            / "measured"
            / "observed-token-mapping.json"
        ),
    }
    for key, expected_hash in evidence_hashes.items():
        metrics = outer.get(key, {})
        if set(metrics) != {
            "exit_status",
            "evidence_sha256",
            "real_s",
            "maximum_resident_set_bytes",
            "peak_memory_footprint_bytes",
            "swaps",
        }:
            raise ValueError("outer process metric shape changed")
        if metrics["exit_status"] != 0 or metrics["evidence_sha256"] != expected_hash:
            raise ValueError("outer process metrics are not bound to successful evidence")
        for metric in (
            "real_s",
            "maximum_resident_set_bytes",
            "peak_memory_footprint_bytes",
            "swaps",
        ):
            value = metrics[metric]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError("outer process metric is not numeric")
            if not math.isfinite(value) or value < 0:
                raise ValueError("outer process metric is invalid")
    machine = outer.get("machine")
    if set(machine or {}) != {
        "hardware",
        "architecture",
        "physical_memory_bytes",
        "operating_system",
        "mps_available",
    }:
        raise ValueError("outer machine evidence shape changed")
    if (
        machine["architecture"] != mps_documents[0]["machine"]["machine"]
        or machine["operating_system"].replace(" ", "-")
        not in mps_documents[0]["machine"]["platform"]
        or machine["mps_available"] is not True
        or not isinstance(machine["physical_memory_bytes"], int)
        or machine["physical_memory_bytes"] <= 0
    ):
        raise ValueError("outer machine evidence conflicts with the model probe")

    mfa_lock = REPOSITORY_ROOT / "speech_sound_patterns" / "environments" / "mfa-3.4.1-osx-arm64-explicit.txt"
    phonetic_lock = REPOSITORY_ROOT / "speech_sound_patterns" / "environments" / "phoneticxeus-8d83dee-osx-arm64-explicit.txt"
    pip_lock = REPOSITORY_ROOT / "speech_sound_patterns" / "environments" / "phoneticxeus-8d83dee-pip.txt"
    report = {
        "schema_version": "1.0.0",
        "checkpoint": "22C",
        "status": "local_feasibility_complete_release_locked",
        "machine": machine,
        "tools": {
            "montreal_forced_aligner": {
                "version": "3.4.1",
                "environment_python": "3.11.15",
                "environment_lock": mfa_lock.relative_to(REPOSITORY_ROOT).as_posix(),
                "environment_lock_sha256": file_sha256(mfa_lock),
                "acoustic_model": "english_us_arpa_v3.0.0",
                "acoustic_model_sha256": ACOUSTIC_SHA256,
                "acoustic_model_bytes": 91_928_208,
                "dictionary": "english_us_arpa_v3.0.0",
                "dictionary_sha256": DICTIONARY_SHA256,
                "dictionary_bytes": 7_186_498,
                "model_and_dictionary_license_metadata": "CC_BY_4.0",
                "selected_role": "expected_text_conditioned_timing_feasibility_only",
            },
            "phoneticxeus": {
                "revision": MODEL_REVISION,
                "environment_python": "3.10.20",
                "environment_lock": phonetic_lock.relative_to(REPOSITORY_ROOT).as_posix(),
                "environment_lock_sha256": file_sha256(phonetic_lock),
                "pip_lock": pip_lock.relative_to(REPOSITORY_ROOT).as_posix(),
                "pip_lock_sha256": file_sha256(pip_lock),
                "model_tree_sha256": MODEL_TREE_SHA256,
                "weights_sha256": MODEL_WEIGHTS_SHA256,
                "weights_bytes": MODEL_WEIGHTS_SIZE,
                "model_card_license_metadata": "Apache_2.0",
                "commercial_release_status": "blocked_pending_complete_training_provenance_and_license_review",
                "selected_role": "reference_text_independent_phone_candidate_feasibility_only",
            },
            "panphon": {
                "version": "0.22.2",
                "locked_wheel_sha256": "a4c65113430d0699054cb00df978c02712d3c80913a1ef67697f888d96f3a00a",
                "license_metadata": "MIT",
                "packaged_data_sha256": EXPECTED_DATA_HASHES,
                "selected_role": "strict_atomic_ipa_identity_to_24_feature_mapping_only",
            },
        },
        "source_summary": source_summary,
        "repeatability": {
            "montreal_forced_aligner": mfa["repeatability"],
            "phoneticxeus": phonetic["repeatability"],
            "panphon": {
                "observed_unique_phone_tokens": panphon["observed_unique_token_count"],
                "strict_atomic_identity_mappings": decisions["identity_nfd"],
                "unsupported_observed_tokens": 0,
            },
        },
        "resource_use": {
            "measurement_note": (
                "macOS maximum resident set and peak memory footprint are different kernel metrics and are reported separately"
            ),
            "montreal_forced_aligner": {
                **mfa["runtime"],
                "maximum_resident_set_bytes": mfa["max_rss_bytes"],
                "peak_memory_footprint_bytes": mfa["max_peak_footprint_bytes"],
                "swaps": mfa["max_swaps"],
            },
            "phoneticxeus": {
                **phonetic["runtime"],
                "mps_maximum_resident_set_bytes": max(
                    outer[key]["maximum_resident_set_bytes"]
                    for key in (
                        "phoneticxeus_mps_full_warm",
                        "phoneticxeus_mps_cold_2",
                        "phoneticxeus_mps_cold_3",
                    )
                ),
                "mps_peak_memory_footprint_bytes": max(
                    outer[key]["peak_memory_footprint_bytes"]
                    for key in (
                        "phoneticxeus_mps_full_warm",
                        "phoneticxeus_mps_cold_2",
                        "phoneticxeus_mps_cold_3",
                    )
                ),
                "cpu_maximum_resident_set_bytes": outer[
                    "phoneticxeus_cpu_source_subset"
                ]["maximum_resident_set_bytes"],
                "cpu_peak_memory_footprint_bytes": outer[
                    "phoneticxeus_cpu_source_subset"
                ]["peak_memory_footprint_bytes"],
                "swaps": max(
                    outer[key]["swaps"]
                    for key in (
                        "phoneticxeus_mps_full_warm",
                        "phoneticxeus_mps_cold_2",
                        "phoneticxeus_mps_cold_3",
                        "phoneticxeus_cpu_source_subset",
                    )
                ),
            },
            "panphon": {
                "observed_mapping_process_s": outer["panphon_observed_mapping"]["real_s"],
                "maximum_resident_set_bytes": outer["panphon_observed_mapping"]["maximum_resident_set_bytes"],
                "peak_memory_footprint_bytes": outer["panphon_observed_mapping"]["peak_memory_footprint_bytes"],
                "swaps": outer["panphon_observed_mapping"]["swaps"],
            },
        },
        "mapping": {
            "montreal_forced_aligner": {
                "input": "known_source_transcript_plus_audio",
                "output": "ARPA_word_and_phone_intervals_conditioned_on_expected_sequence",
                "nonphones": ["empty_unlabeled_interval", "eps", "sil", "sp", "spn"],
                "observed_interval_aggregates": mfa["intervals"],
                "may_establish_produced_phone": False,
            },
            "phoneticxeus": {
                "input": "mono_16_kHz_audio_without_reference_text",
                "vocabulary_total": 428,
                "special_tokens": 4,
                "phone_tokens": 424,
                "output": "greedy_phone_sequence_plus_contextual_frame_CTC_logits",
                "official_phone_timestamps": False,
                "calibrated_confidence": False,
                "sequence_alternatives": False,
                "top_frame_logits_are_sequence_alternatives": False,
            },
            "panphon": {
                "input": "one_observed_PhoneticXEUS_token_at_a_time",
                "normalization": "NFD_only",
                "atomic_identity_required": True,
                "feature_count": 24,
                "unknown_or_composite_behavior": "unsupported_without_partial_mapping",
                "weighted_distance_enabled": False,
            },
            "cross_system_agreement_is_truth": False,
            "accuracy_or_relation_scoring_performed": False,
        },
        "release_boundaries": {
            "scientific_release": False,
            "product_release": False,
            "normal_pipeline_activation": False,
            "coaching": False,
            "personal_progress": False,
            "screening": False,
            "diagnosis": False,
        },
        "limitations": [
            "This small development sample establishes local execution output shape mapping and repeatability only not accuracy.",
            "No held out participant expert relation label or population result was inspected or scored.",
            "The MFA model is General American read speech and conditions on expected text so it cannot establish produced phones Australian variants or correctness.",
            "MFA emitted unknown phone intervals in three clips and an unlabeled interval in one clip; neither is silently repaired.",
            "PhoneticXEUS emits a greedy token sequence and contextual CTC logits but no official phone timestamps calibrated confidence or sequence alternatives.",
            "PhoneticXEUS training or evaluation lineage overlaps SpeechOcean Common Voice and LibriSpeech; Common Phone is related to Common Voice; these sources cannot provide independent model accuracy evidence.",
            "The PhoneticXEUS model card says Apache 2.0 but the pinned snapshot lacks a complete license and training data provenance bundle; commercial or product use remains blocked.",
            "PanPhon does not listen to audio and can only encode a supplied supported IPA token.",
            "PanPhon weighted distance is prohibited because version 0.22.2 has a feature weight count and ordering mismatch.",
            "The exact environment locks are macOS arm64 specific and do not establish repeatability on other hardware or software stacks.",
            "No task detector candidate artifact score coaching progress screening diagnosis severity cause or treatment output was created.",
        ],
    }
    errors = validate_safe_feasibility_report(report)
    if errors:
        raise ValueError("; ".join(errors))
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--evidence-root", required=True, type=Path)
    parser.add_argument("--outer-metrics", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = build_report(
        args.manifest.resolve(),
        args.evidence_root.resolve(),
        args.outer_metrics.resolve(),
    )
    output = args.output.resolve()
    expected_output = (
        REPOSITORY_ROOT / "speech_sound_patterns" / "local-feasibility-v1.0.0.json"
    ).resolve()
    if output != expected_output:
        raise ValueError("committed feasibility output path is fixed")
    output.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Safe checkpoint 22C report: {output.relative_to(REPOSITORY_ROOT)}")
    print("Raw clip evidence remains in ignored private storage.")


if __name__ == "__main__":
    main()
