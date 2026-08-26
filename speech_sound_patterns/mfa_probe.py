"""Version-locked, developer-only Montreal Forced Aligner feasibility probe.

The probe preserves raw alignments in ignored private storage.  Its summaries
describe timing and repeatability only; an expected-text alignment is never
treated as evidence of the phones a speaker actually produced.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import subprocess
import time
from pathlib import Path

from .feasibility import (
    REPOSITORY_ROOT,
    canonical_json_bytes,
    file_sha256,
    validate_frozen_private_sample_manifest,
)


PRIVATE_ROOT = REPOSITORY_ROOT / ".research_data" / "speech_sound_patterns"
ACOUSTIC_SHA256 = "d35ce271ded357d833d2f4b8d1041dc3748b9538567ba13f2c697f4e4126711b"
ACOUSTIC_SIZE = 91_928_208
DICTIONARY_SHA256 = "e8c6c7b036ae2b7c78d2768b8dc6b1f9359175b842956d00b48c53c9c332e6b0"
DICTIONARY_SIZE = 7_186_498
NONPHONE_LABELS = {"", "<eps>", "sil", "sp", "spn"}


def _inside_private(path, *, create=False):
    resolved = Path(path).resolve(strict=False)
    resolved.relative_to(PRIVATE_ROOT.resolve())
    if create:
        resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def verify_models(acoustic_model, dictionary):
    checks = (
        (Path(acoustic_model), ACOUSTIC_SIZE, ACOUSTIC_SHA256, "acoustic model"),
        (Path(dictionary), DICTIONARY_SIZE, DICTIONARY_SHA256, "dictionary"),
    )
    for path, expected_size, expected_hash, label in checks:
        if not path.is_file():
            raise ValueError(f"pinned MFA {label} is missing")
        if path.stat().st_size != expected_size or file_sha256(path) != expected_hash:
            raise ValueError(f"pinned MFA {label} identity changed")


def _selected_clips(manifest, safe_ids):
    wanted = set(safe_ids or [])
    selected = []
    for source in manifest["sources"]:
        for clip in source["clips"]:
            if "mfa" not in clip["eligible_tools"]:
                continue
            if wanted and clip["safe_id"] not in wanted:
                continue
            if clip["intended_text_state"] != "source_transcript":
                raise ValueError("MFA eligibility requires a known source transcript")
            selected.append((source["source_id"], clip))
    found = {clip["safe_id"] for _, clip in selected}
    if wanted and wanted != found:
        raise ValueError(f"requested MFA samples are unavailable: {sorted(wanted - found)}")
    if not selected:
        raise ValueError("no eligible MFA clips were selected")
    return selected


def _parse_time_metrics(stderr):
    def integer_for(label):
        match = re.search(rf"^\s*(-?\d+)\s+{re.escape(label)}$", stderr, re.MULTILINE)
        return int(match.group(1)) if match else None

    return {
        "maximum_resident_set_bytes": integer_for("maximum resident set size"),
        "peak_memory_footprint_bytes": integer_for("peak memory footprint"),
        "page_faults": integer_for("page faults"),
        "swaps": integer_for("swaps"),
    }


def _validate_tier(entries, output_start, output_end, tier_name):
    if not isinstance(entries, list) or not entries:
        raise ValueError(f"MFA {tier_name} tier is empty")
    previous_end = output_start
    normalized = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, list) or len(entry) != 3:
            raise ValueError(f"MFA {tier_name} entry has an unexpected shape")
        start, end, label = entry
        if not isinstance(label, str):
            raise ValueError(f"MFA {tier_name} entry label is not text")
        if start < output_start or end > output_end or start > end:
            raise ValueError(f"MFA {tier_name} entry has invalid boundaries")
        if index and start < previous_end:
            raise ValueError(f"MFA {tier_name} entries overlap")
        previous_end = end
        normalized.append([round(float(start), 6), round(float(end), 6), label])
    return normalized


def _alignment_summary(raw_document):
    if set(raw_document) != {"start", "end", "tiers"}:
        raise ValueError("MFA JSON top-level shape changed")
    output_start = float(raw_document["start"])
    output_end = float(raw_document["end"])
    tiers = raw_document["tiers"]
    if set(tiers) != {"words", "phones"}:
        raise ValueError("MFA JSON tier set changed")
    words = _validate_tier(
        tiers["words"].get("entries"), output_start, output_end, "words"
    )
    phones = _validate_tier(
        tiers["phones"].get("entries"), output_start, output_end, "phones"
    )
    normalized = {
        "start": round(output_start, 6),
        "end": round(output_end, 6),
        "words": words,
        "phones": phones,
    }
    labels = [item[2] for item in phones]
    return {
        "canonical_alignment_sha256": hashlib.sha256(
            canonical_json_bytes(normalized)
        ).hexdigest(),
        "word_interval_count": len(words),
        "phone_interval_count": len(phones),
        "lexical_phone_interval_count": sum(
            label not in NONPHONE_LABELS for label in labels
        ),
        "silence_interval_count": sum(
            label in {"<eps>", "sil", "sp"} for label in labels
        ),
        "unknown_phone_interval_count": labels.count("spn"),
        "unlabeled_interval_count": labels.count(""),
        "output_start_s": normalized["start"],
        "output_end_s": normalized["end"],
    }


def _child_environment(mfa_binary, mfa_root, scratch_home, matplotlib_root):
    Path(scratch_home).mkdir(parents=True, exist_ok=True)
    Path(matplotlib_root).mkdir(parents=True, exist_ok=True)
    environment = {
        "HOME": str(scratch_home),
        "PATH": f"{Path(mfa_binary).parent}:/usr/bin:/bin",
        "MFA_ROOT_DIR": str(mfa_root),
        "MPLCONFIGDIR": str(matplotlib_root),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
        "VECLIB_MAXIMUM_THREADS": "1",
        "LC_ALL": "C",
    }
    return environment


def run_probe(
    manifest_path,
    mfa_binary,
    mfa_root,
    acoustic_model,
    dictionary,
    output_root,
    repeats,
    safe_ids,
):
    if repeats < 1 or repeats > 10:
        raise ValueError("MFA repeats must be between one and ten")
    mfa_binary = Path(mfa_binary).resolve()
    if not mfa_binary.is_file():
        raise ValueError("MFA executable is missing")
    mfa_root = _inside_private(mfa_root, create=True)
    output_root = _inside_private(output_root, create=True)
    verify_models(acoustic_model, dictionary)
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    errors = validate_frozen_private_sample_manifest(manifest, REPOSITORY_ROOT)
    if errors:
        raise ValueError("; ".join(errors))
    clips = _selected_clips(manifest, safe_ids)

    version_result = subprocess.run(
        [str(mfa_binary), "version"],
        check=True,
        capture_output=True,
        text=True,
        env=_child_environment(
            mfa_binary,
            mfa_root,
            output_root / "sandbox-home",
            output_root / "matplotlib",
        ),
    )
    if version_result.stdout.strip() != "3.4.1":
        raise ValueError("MFA version is not pinned to 3.4.1")
    python_result = subprocess.run(
        [str(mfa_binary.parent / "python"), "--version"],
        check=True,
        capture_output=True,
        text=True,
        env=_child_environment(
            mfa_binary,
            mfa_root,
            output_root / "sandbox-home",
            output_root / "matplotlib",
        ),
    )

    clip_results = []
    for source_id, clip in clips:
        audio_path = REPOSITORY_ROOT / clip["canonical_audio_path"]
        lab_path = audio_path.with_suffix(".lab")
        if file_sha256(audio_path) != clip["canonical_audio_sha256"]:
            raise ValueError("canonical audio checksum changed")
        if not lab_path.is_file() or file_sha256(lab_path) != clip["intended_text_sha256"]:
            raise ValueError("private intended-text file identity changed")
        repeat_results = []
        first_digest = None
        for repeat_index in range(repeats):
            repeat_root = output_root / "runs" / clip["safe_id"] / f"repeat-{repeat_index + 1}"
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
                env=_child_environment(
                    mfa_binary,
                    mfa_root,
                    output_root / "sandbox-home",
                    output_root / "matplotlib",
                ),
            )
            runtime = time.perf_counter() - started
            (repeat_root / "stdout.log").write_text(process.stdout, encoding="utf-8")
            (repeat_root / "stderr-and-time.log").write_text(
                process.stderr, encoding="utf-8"
            )
            if process.returncode != 0 or not raw_output.is_file():
                raise RuntimeError(
                    f"MFA failed for {clip['safe_id']} repeat {repeat_index + 1}; "
                    "inspect the private log"
                )
            raw_document = json.loads(raw_output.read_text(encoding="utf-8"))
            summary = _alignment_summary(raw_document)
            digest = summary["canonical_alignment_sha256"]
            if repeat_index == 0:
                first_digest = digest
            repeat_results.append(
                {
                    "repeat_index": repeat_index,
                    "runtime_s": round(runtime, 6),
                    "raw_output_sha256": file_sha256(raw_output),
                    "canonical_exact_match_first": digest == first_digest,
                    "resource_use": _parse_time_metrics(process.stderr),
                    **summary,
                }
            )
        clip_results.append(
            {
                "safe_id": clip["safe_id"],
                "source_id": source_id,
                "input_sha256": clip["canonical_audio_sha256"],
                "intended_text_sha256": clip["intended_text_sha256"],
                "duration_s": clip["duration_s"],
                "repeats": repeat_results,
            }
        )

    result = {
        "schema_version": "1.0.0",
        "probe_id": "mfa_local_feasibility_v1",
        "mfa_version": "3.4.1",
        "probe_python_version": platform.python_version(),
        "mfa_environment_python_version": python_result.stdout.strip(),
        "acoustic_model": {
            "name": "english_us_arpa",
            "sha256": ACOUSTIC_SHA256,
            "training_domain": "General American read speech",
            "fitness": "provisional timing feasibility only",
        },
        "dictionary": {
            "name": "english_us_arpa",
            "sha256": DICTIONARY_SHA256,
            "g2p_fallback": False,
        },
        "execution": {
            "num_jobs": 1,
            "multiprocessing": False,
            "threading": False,
            "speaker_adaptation": False,
            "textgrid_cleanup": False,
            "fresh_directory_each_repeat": True,
            "credential_free_environment": True,
        },
        "clips": clip_results,
        "claim_boundaries": {
            "expected_sequence_conditioned": True,
            "produced_phone_truth": False,
            "pronunciation_correctness": False,
            "australian_variant_truth": False,
            "product_timing_release": False,
        },
    }
    result_path = output_root / "mfa-process.json"
    result_path.write_bytes(canonical_json_bytes(result))
    return result_path, result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--mfa", required=True, type=Path)
    parser.add_argument("--mfa-root", required=True, type=Path)
    parser.add_argument("--acoustic-model", required=True, type=Path)
    parser.add_argument("--dictionary", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--repeats", required=True, type=int)
    parser.add_argument("--safe-id", action="append", default=[])
    args = parser.parse_args()
    path, result = run_probe(
        args.manifest.resolve(),
        args.mfa.resolve(),
        args.mfa_root.resolve(),
        args.acoustic_model.resolve(),
        args.dictionary.resolve(),
        args.output.resolve(),
        args.repeats,
        args.safe_id,
    )
    print(f"MFA timing probe: {len(result['clips'])} clips")
    print(f"Private raw evidence: {path.relative_to(REPOSITORY_ROOT)}")


if __name__ == "__main__":
    main()
