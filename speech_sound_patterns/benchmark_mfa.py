"""Run pinned MFA timing evidence on the frozen cross-system benchmark subset."""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import time
from pathlib import Path

from .benchmark import (
    FROZEN_BENCHMARK_MANIFEST_SHA256,
    PRIVATE_BENCHMARK_ROOT,
    validate_frozen_private_benchmark_manifest,
)
from .feasibility import REPOSITORY_ROOT, canonical_json_bytes, file_sha256
from .mfa_probe import (
    ACOUSTIC_SHA256,
    DICTIONARY_SHA256,
    _alignment_summary,
    _child_environment,
    _parse_time_metrics,
    verify_models,
)


PRIVATE_ROOT = REPOSITORY_ROOT / ".research_data" / "speech_sound_patterns"
DEFAULT_MANIFEST = PRIVATE_ROOT / "benchmark" / "benchmark-manifest-v1.0.0.json"
DEFAULT_MFA = PRIVATE_ROOT / "environments" / "mfa-3.4.1-osx-arm64" / "bin" / "mfa"
DEFAULT_ACOUSTIC = (
    PRIVATE_ROOT
    / "models"
    / "mfa"
    / "pretrained_models"
    / "acoustic"
    / "english_us_arpa.zip"
)
DEFAULT_DICTIONARY = (
    PRIVATE_ROOT
    / "models"
    / "mfa"
    / "pretrained_models"
    / "dictionary"
    / "english_us_arpa.dict"
)
DEFAULT_OUTPUT = PRIVATE_BENCHMARK_ROOT / "v1" / "evidence" / "mfa"


def _inside_benchmark(path, create=False):
    resolved = Path(path).resolve(strict=False)
    resolved.relative_to(PRIVATE_BENCHMARK_ROOT.resolve())
    if create:
        resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _selected_clips(manifest):
    selected = []
    for source in manifest["sources"]:
        for clip in source["clips"]:
            if clip["same_clip_local_system_subset"]:
                selected.append((source["source_id"], clip))
    if len(selected) != 109:
        raise ValueError("frozen MFA cross-system subset count changed")
    return selected


def _repeat_ids(selected):
    acted = {}
    for source_id, clip in selected:
        if source_id != "acted_clear_speech":
            continue
        acted.setdefault(clip["source_stratum"], []).append(clip["safe_id"])
    if len(acted) != 5:
        raise ValueError("Acted Clear condition set changed")
    return {min(values) for values in acted.values()}


def _load_existing(path, clip, source_id, repeats):
    document = json.loads(path.read_text(encoding="utf-8"))
    if (
        document.get("safe_id") != clip["safe_id"]
        or document.get("source_id") != source_id
        or document.get("input_sha256") != clip["canonical_audio_sha256"]
        or len(document.get("repeats", [])) != repeats
    ):
        raise ValueError(f"existing MFA evidence is invalid for {clip['safe_id']}")
    if not all(item["canonical_exact_match_first"] for item in document["repeats"]):
        raise ValueError(f"existing MFA repeatability failed for {clip['safe_id']}")
    return document


def run_benchmark(
    manifest_path=DEFAULT_MANIFEST,
    mfa_binary=DEFAULT_MFA,
    acoustic_model=DEFAULT_ACOUSTIC,
    dictionary=DEFAULT_DICTIONARY,
    output_root=DEFAULT_OUTPUT,
):
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    errors = validate_frozen_private_benchmark_manifest(
        manifest, FROZEN_BENCHMARK_MANIFEST_SHA256
    )
    if errors:
        raise ValueError("; ".join(errors))
    selected = _selected_clips(manifest)
    repeated = _repeat_ids(selected)
    mfa_binary = Path(mfa_binary).resolve()
    if not mfa_binary.is_file():
        raise ValueError("pinned MFA executable is missing")
    verify_models(acoustic_model, dictionary)
    output_root = _inside_benchmark(output_root, create=True)
    clips_root = output_root / "clips"
    clips_root.mkdir(exist_ok=True)
    summary_path = output_root / "mfa-benchmark-process.json"
    if summary_path.exists():
        raise ValueError("completed MFA benchmark evidence already exists")
    mfa_root = _inside_benchmark(output_root / "mfa-root", create=True)
    sandbox_home = _inside_benchmark(output_root / "sandbox-home", create=True)
    matplotlib_root = _inside_benchmark(output_root / "matplotlib", create=True)
    environment = _child_environment(
        mfa_binary, mfa_root, sandbox_home, matplotlib_root
    )
    version = subprocess.run(
        [str(mfa_binary), "version"],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    if version.stdout.strip() != "3.4.1":
        raise ValueError("MFA version changed")
    python_version = subprocess.run(
        [str(mfa_binary.parent / "python"), "--version"],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    ).stdout.strip()

    clip_index = []
    for position, (source_id, clip) in enumerate(selected, start=1):
        repeat_count = 2 if clip["safe_id"] in repeated else 1
        clip_summary_path = clips_root / f"{clip['safe_id']}.json"
        if clip_summary_path.exists():
            document = _load_existing(
                clip_summary_path, clip, source_id, repeat_count
            )
            clip_index.append(
                {
                    "safe_id": clip["safe_id"],
                    "source_id": source_id,
                    "project_split": clip["project_split"],
                    "source_stratum": clip["source_stratum"],
                    "output_path": str(
                        clip_summary_path.relative_to(REPOSITORY_ROOT)
                    ),
                    "output_sha256": file_sha256(clip_summary_path),
                    "repeatability_passed": True,
                }
            )
            continue
        audio_path = REPOSITORY_ROOT / clip["canonical_audio_path"]
        lab_path = REPOSITORY_ROOT / clip["intended_text_path"]
        if file_sha256(audio_path) != clip["canonical_audio_sha256"]:
            raise ValueError(f"MFA input audio changed for {clip['safe_id']}")
        if file_sha256(lab_path) != clip["intended_text_sha256"]:
            raise ValueError(f"MFA intended text changed for {clip['safe_id']}")
        repeat_records = []
        first_digest = None
        for repeat_index in range(repeat_count):
            repeat_root = clips_root / clip["safe_id"] / f"repeat-{repeat_index + 1}"
            repeat_root.mkdir(parents=True, exist_ok=False)
            raw_output = repeat_root / "alignment.json"
            temporary = repeat_root / "temporary"
            temporary.mkdir()
            command = [
                "/usr/bin/time",
                "-l",
                str(mfa_binary),
                "align_one",
                str(audio_path),
                str(lab_path),
                str(Path(dictionary).resolve()),
                str(Path(acoustic_model).resolve()),
                str(raw_output),
                "--output_format",
                "json",
                "--temporary_directory",
                str(temporary),
                "--num_jobs",
                "1",
                "--no_use_mp",
                "--no_use_threading",
                "--no_use_postgres",
                "--single_speaker",
                "--no_textgrid_cleanup",
                "--clean",
                "--final_clean",
                "--overwrite",
                "--quiet",
            ]
            started = time.perf_counter()
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                env=environment,
            )
            runtime = time.perf_counter() - started
            (repeat_root / "stdout.log").write_text(
                process.stdout, encoding="utf-8"
            )
            (repeat_root / "stderr-and-time.log").write_text(
                process.stderr, encoding="utf-8"
            )
            if process.returncode != 0 or not raw_output.is_file():
                raise RuntimeError(
                    f"MFA failed for {clip['safe_id']}; inspect the private log"
                )
            raw_document = json.loads(raw_output.read_text(encoding="utf-8"))
            summary = _alignment_summary(raw_document)
            digest = summary["canonical_alignment_sha256"]
            if first_digest is None:
                first_digest = digest
            repeat_records.append(
                {
                    "repeat_index": repeat_index,
                    "runtime_s": round(runtime, 6),
                    "raw_output_sha256": file_sha256(raw_output),
                    "canonical_exact_match_first": digest == first_digest,
                    "resource_use": _parse_time_metrics(process.stderr),
                    **summary,
                }
            )
            shutil.rmtree(temporary)
        document = {
            "schema_version": "1.0.0",
            "probe_id": "mfa_developer_benchmark_v1",
            "safe_id": clip["safe_id"],
            "source_id": source_id,
            "project_split": clip["project_split"],
            "source_stratum": clip["source_stratum"],
            "input_sha256": clip["canonical_audio_sha256"],
            "intended_text_sha256": clip["intended_text_sha256"],
            "duration_s": clip["duration_s"],
            "repeats": repeat_records,
            "claim_boundaries": {
                "expected_sequence_conditioned": True,
                "produced_phone_truth": False,
                "pronunciation_correctness": False,
                "australian_variant_truth": False,
                "product_timing_release": False,
            },
        }
        clip_summary_path.write_bytes(canonical_json_bytes(document))
        clip_index.append(
            {
                "safe_id": clip["safe_id"],
                "source_id": source_id,
                "project_split": clip["project_split"],
                "source_stratum": clip["source_stratum"],
                "output_path": clip_summary_path.relative_to(REPOSITORY_ROOT).as_posix(),
                "output_sha256": file_sha256(clip_summary_path),
                "repeatability_passed": all(
                    item["canonical_exact_match_first"] for item in repeat_records
                ),
            }
        )
        if position % 10 == 0:
            print(f"MFA benchmark progress: {position}/{len(selected)}", flush=True)

    summary = {
        "schema_version": "1.0.0",
        "probe_id": "mfa_developer_benchmark_v1",
        "private_benchmark_manifest_sha256": FROZEN_BENCHMARK_MANIFEST_SHA256,
        "mfa_version": "3.4.1",
        "probe_python_version": platform.python_version(),
        "mfa_environment_python_version": python_version,
        "acoustic_model": {
            "name": "english_us_arpa",
            "sha256": ACOUSTIC_SHA256,
            "training_domain": "General American read speech",
            "fitness": "developer timing evidence only",
        },
        "dictionary": {
            "name": "english_us_arpa",
            "sha256": DICTIONARY_SHA256,
            "g2p_fallback": False,
        },
        "execution": {
            "clip_count": len(clip_index),
            "same_input_repeat_clips": len(repeated),
            "temporary_alignment_databases_retained": False,
            "raw_alignment_json_and_logs_retained": True,
            "credential_free_environment": True,
        },
        "clips": clip_index,
        "claim_boundaries": {
            "held_out_evaluation": False,
            "expected_sequence_conditioned": True,
            "produced_phone_truth": False,
            "pronunciation_correctness": False,
            "scientific_or_product_release": False,
        },
    }
    summary_path.write_bytes(canonical_json_bytes(summary))
    return summary_path, summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--mfa", type=Path, default=DEFAULT_MFA)
    parser.add_argument("--acoustic-model", type=Path, default=DEFAULT_ACOUSTIC)
    parser.add_argument("--dictionary", type=Path, default=DEFAULT_DICTIONARY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    path, summary = run_benchmark(
        args.manifest.resolve(),
        args.mfa.resolve(),
        args.acoustic_model.resolve(),
        args.dictionary.resolve(),
        args.output.resolve(),
    )
    print(f"MFA benchmark complete: {len(summary['clips'])} clips")
    print(f"Private process record: {path.relative_to(REPOSITORY_ROOT)}")


if __name__ == "__main__":
    main()
