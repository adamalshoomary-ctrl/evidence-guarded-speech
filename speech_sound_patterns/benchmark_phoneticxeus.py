"""Run pinned PhoneticXEUS on the frozen private checkpoint 22D sample."""

from __future__ import annotations

import argparse
import gc
import importlib.metadata
import json
import math
import os
import platform
import time
from pathlib import Path

from .benchmark import (
    FROZEN_BENCHMARK_MANIFEST_SHA256,
    PRIVATE_BENCHMARK_ROOT,
    canonical_json_sha256,
    validate_frozen_private_benchmark_manifest,
)
from .feasibility import REPOSITORY_ROOT, canonical_json_bytes, classify_panphon_token, file_sha256
from .panphon_probe import EXPECTED_DATA_HASHES
from .phoneticxeus_probe import (
    MODEL_REVISION,
    MODEL_TREE_SHA256,
    MODEL_WEIGHTS_SHA256,
    _collapsed_ctc,
    _load_waveform,
    verify_model_snapshot,
)


PRIVATE_ROOT = REPOSITORY_ROOT / ".research_data" / "speech_sound_patterns"
DEFAULT_MANIFEST = PRIVATE_ROOT / "benchmark" / "benchmark-manifest-v1.0.0.json"
DEFAULT_MODEL = PRIVATE_ROOT / "models" / "phoneticxeus" / MODEL_REVISION
DEFAULT_OUTPUT = PRIVATE_BENCHMARK_ROOT / "v1" / "evidence" / "phoneticxeus"


def _private_output(path):
    resolved = Path(path).resolve(strict=False)
    resolved.relative_to(PRIVATE_BENCHMARK_ROOT.resolve())
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _verify_panphon():
    import panphon

    if importlib.metadata.version("panphon") != "0.22.2":
        raise ValueError("PanPhon version must remain pinned to 0.22.2")
    data_root = Path(panphon.__file__).resolve().parent / "data"
    actual = {name: file_sha256(data_root / name) for name in EXPECTED_DATA_HASHES}
    if actual != EXPECTED_DATA_HASHES:
        raise ValueError("PanPhon packaged data checksums changed")


def _clips(manifest):
    result = []
    for source in manifest["sources"]:
        for clip in source["clips"]:
            if "phoneticxeus" in clip["eligible_tools"]:
                result.append((source["source_id"], clip))
    if len(result) != 565:
        raise ValueError("frozen PhoneticXEUS benchmark clip count changed")
    return result


def run_benchmark(
    manifest_path,
    model_root,
    output_root,
    backend="mps",
    repeats=2,
    max_new_clips=None,
):
    if os.environ.get("HF_HUB_OFFLINE") != "1" or os.environ.get(
        "TRANSFORMERS_OFFLINE"
    ) != "1":
        raise ValueError("benchmark inference must run with network access disabled")
    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        raise ValueError("pinned model inference must not write Python bytecode")
    if os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK") not in {None, "0"}:
        raise ValueError("silent MPS to CPU fallback is prohibited")
    if repeats != 2:
        raise ValueError("checkpoint 22D requires exactly two same-input runs")
    if max_new_clips is not None and max_new_clips < 1:
        raise ValueError("max new clips must be positive when provided")
    model_root = Path(model_root).resolve()
    verify_model_snapshot(model_root)
    _verify_panphon()
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    errors = validate_frozen_private_benchmark_manifest(
        manifest, FROZEN_BENCHMARK_MANIFEST_SHA256
    )
    if errors:
        raise ValueError("; ".join(errors))
    selected = _clips(manifest)
    output_root = _private_output(output_root)
    summary_path = output_root / "phoneticxeus-benchmark-process.json"
    clips_root = output_root / "clips"
    if summary_path.exists():
        raise ValueError("completed PhoneticXEUS benchmark evidence already exists")
    clips_root.mkdir(parents=True, exist_ok=True)

    import numpy as np
    import panphon
    import safetensors
    import soundfile
    import torch
    import torchaudio
    import transformers
    from huggingface_hub import __version__ as hub_version
    from panphon import FeatureTable
    from transformers import AutoModel

    if backend not in {"cpu", "mps"}:
        raise ValueError("backend must be cpu or mps")
    if backend == "mps" and not torch.backends.mps.is_available():
        raise ValueError("MPS was requested but is unavailable")
    torch.manual_seed(0)
    np.random.seed(0)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    device = torch.device(backend)
    feature_table = FeatureTable()

    vocab = json.loads((model_root / "ipa_vocab.json").read_text(encoding="utf-8"))
    if len(vocab) != 428 or vocab.get("<blank>") != 0:
        raise ValueError("PhoneticXEUS vocabulary identity changed")
    id_to_token = {str(value): key for key, value in vocab.items()}
    load_started = time.perf_counter()
    model = AutoModel.from_pretrained(
        str(model_root),
        trust_remote_code=True,
        local_files_only=True,
        use_safetensors=True,
    ).eval()
    model = model.to(device)
    if backend == "mps":
        torch.mps.synchronize()
    load_seconds = time.perf_counter() - load_started

    clip_index = []
    total_audio_seconds = 0.0
    total_inference_seconds = 0.0
    new_clip_count = 0
    for position, (source_id, clip) in enumerate(selected, start=1):
        output_path = clips_root / f"{clip['safe_id']}.json"
        if output_path.exists():
            record = json.loads(output_path.read_text(encoding="utf-8"))
            if (
                record.get("safe_id") != clip["safe_id"]
                or record.get("source_id") != source_id
                or record.get("input_sha256") != clip["canonical_audio_sha256"]
                or record.get("model_revision") != MODEL_REVISION
                or len(record.get("repeats", [])) != repeats
            ):
                raise ValueError(
                    f"existing private evidence is invalid for {clip['safe_id']}"
                )
            repeat_records = record["repeats"]
            if not all(
                item.get("frame_ids_exact_match_first") is True
                and item.get("collapsed_ids_exact_match_first") is True
                for item in repeat_records
            ):
                raise ValueError(
                    f"existing repeatability evidence failed for {clip['safe_id']}"
                )
            clip_index.append(
                {
                    "safe_id": clip["safe_id"],
                    "source_id": source_id,
                    "project_split": clip["project_split"],
                    "source_stratum": clip["source_stratum"],
                    "duration_s": clip["duration_s"],
                    "output_path": str(output_path.relative_to(REPOSITORY_ROOT)),
                    "output_sha256": file_sha256(output_path),
                    "repeatability_passed": True,
                }
            )
            total_audio_seconds += clip["duration_s"]
            total_inference_seconds += sum(
                item["runtime_s"] for item in repeat_records
            )
            if position % 50 == 0:
                print(
                    f"PhoneticXEUS benchmark resume check: {position}/{len(selected)}",
                    flush=True,
                )
            continue
        audio_path = REPOSITORY_ROOT / clip["canonical_audio_path"]
        waveform, peak = _load_waveform(audio_path, clip["canonical_audio_sha256"])
        waveform = waveform.to(device)
        first_frame_ids = None
        first_collapsed = None
        first_evidence = None
        repeat_records = []
        for repeat_index in range(repeats):
            started = time.perf_counter()
            with torch.inference_mode():
                logits = model(input_values=waveform).logits
            if backend == "mps":
                torch.mps.synchronize()
            elapsed = time.perf_counter() - started
            if not bool(torch.isfinite(logits).all().item()):
                raise ValueError(f"nonfinite model output for {clip['safe_id']}")
            cpu_logits = logits.detach().to("cpu", dtype=torch.float32).contiguous()
            frame_ids = cpu_logits.argmax(dim=-1)[0].tolist()
            collapsed_ids, collapsed_tokens = _collapsed_ctc(frame_ids, id_to_token)
            frame_digest = canonical_json_sha256(frame_ids)
            collapsed_digest = canonical_json_sha256(collapsed_ids)
            if repeat_index == 0:
                first_frame_ids = frame_ids
                first_collapsed = collapsed_ids
                top_values, top_ids = torch.topk(cpu_logits[0], k=5, dim=-1)
                top_frames = [
                    {
                        "frame_index": index,
                        "token_ids": top_ids[index].tolist(),
                        "raw_logits": [round(float(item), 7) for item in top_values[index]],
                    }
                    for index in range(cpu_logits.shape[1])
                ]
                classifications = [
                    classify_panphon_token(token, feature_table)
                    for token in collapsed_tokens
                ]
                if any(item["decision"] != "identity_nfd" for item in classifications):
                    raise ValueError(
                        f"unsupported PhoneticXEUS token in {clip['safe_id']}"
                    )
                first_evidence = {
                    "frame_ids": frame_ids,
                    "collapsed_token_ids": collapsed_ids,
                    "collapsed_tokens": collapsed_tokens,
                    "panphon_classifications": classifications,
                    "top_five_contextual_logits_per_frame": top_frames,
                }
            repeat_records.append(
                {
                    "repeat_index": repeat_index,
                    "runtime_s": round(elapsed, 6),
                    "frame_argmax_sha256": frame_digest,
                    "collapsed_ids_sha256": collapsed_digest,
                    "frame_ids_exact_match_first": frame_ids == first_frame_ids,
                    "collapsed_ids_exact_match_first": collapsed_ids == first_collapsed,
                }
            )
            total_inference_seconds += elapsed
        record = {
            "schema_version": "1.0.0",
            "probe_id": "phoneticxeus_developer_benchmark_v1",
            "safe_id": clip["safe_id"],
            "source_id": source_id,
            "project_split": clip["project_split"],
            "source_stratum": clip["source_stratum"],
            "input_sha256": clip["canonical_audio_sha256"],
            "duration_s": clip["duration_s"],
            "peak_absolute_amplitude": round(peak, 8),
            "logit_shape": [int(item) for item in cpu_logits.shape],
            "backend": backend,
            "model_revision": MODEL_REVISION,
            "output_semantics": (
                "greedy_fixed_inventory_phone_path_and_top_five_uncalibrated_"
                "contextual_ctc_logits_not_phone_timestamps_or_confidence"
            ),
            **first_evidence,
            "repeats": repeat_records,
            "claim_boundaries": {
                "phone_timestamps": False,
                "calibrated_confidence": False,
                "sequence_alternatives": False,
                "produced_phone_truth": False,
                "pronunciation_correctness": False,
            },
        }
        output_path.write_bytes(canonical_json_bytes(record))
        clip_index.append(
            {
                "safe_id": clip["safe_id"],
                "source_id": source_id,
                "project_split": clip["project_split"],
                "source_stratum": clip["source_stratum"],
                "duration_s": clip["duration_s"],
                "output_path": str(output_path.relative_to(REPOSITORY_ROOT)),
                "output_sha256": file_sha256(output_path),
                "repeatability_passed": all(
                    item["frame_ids_exact_match_first"]
                    and item["collapsed_ids_exact_match_first"]
                    for item in repeat_records
                ),
            }
        )
        total_audio_seconds += clip["duration_s"]
        del (
            logits,
            cpu_logits,
            waveform,
            first_evidence,
            top_values,
            top_ids,
            top_frames,
            classifications,
            frame_ids,
            collapsed_ids,
            collapsed_tokens,
        )
        if backend == "mps":
            torch.mps.empty_cache()
        gc.collect()
        new_clip_count += 1
        if position % 50 == 0:
            print(f"PhoneticXEUS benchmark progress: {position}/{len(selected)}", flush=True)
        if max_new_clips is not None and new_clip_count >= max_new_clips:
            print(
                "PhoneticXEUS benchmark chunk complete: "
                f"{new_clip_count} new clips, {len(clip_index)}/{len(selected)} total",
                flush=True,
            )
            return None, {"complete": False, "clips": clip_index}

    summary = {
        "schema_version": "1.0.0",
        "probe_id": "phoneticxeus_developer_benchmark_v1",
        "private_benchmark_manifest_sha256": FROZEN_BENCHMARK_MANIFEST_SHA256,
        "backend": backend,
        "model_revision": MODEL_REVISION,
        "model_tree_sha256": MODEL_TREE_SHA256,
        "model_weights_sha256": MODEL_WEIGHTS_SHA256,
        "model_load_seconds": round(load_seconds, 6),
        "versions": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "torchaudio": torchaudio.__version__,
            "transformers": transformers.__version__,
            "huggingface_hub": hub_version,
            "safetensors": safetensors.__version__,
            "soundfile": soundfile.__version__,
            "numpy": np.__version__,
            "panphon": importlib.metadata.version("panphon"),
        },
        "machine": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "mps_built": torch.backends.mps.is_built(),
            "mps_available": torch.backends.mps.is_available(),
        },
        "execution": {
            "clip_count": len(clip_index),
            "repeats_per_clip": repeats,
            "total_audio_seconds": round(total_audio_seconds, 6),
            "total_inference_seconds": round(total_inference_seconds, 6),
            "real_time_factor_all_repeats": round(
                total_inference_seconds / (total_audio_seconds * repeats), 6
            ),
            "network_access": False,
            "torch_seed": 0,
            "numpy_seed": 0,
            "torch_num_threads": 1,
            "deterministic_algorithms": True,
            "silent_mps_cpu_fallback": False,
        },
        "compact_raw_output": {
            "full_logits_retained": False,
            "frame_argmax_retained": True,
            "top_five_contextual_logits_per_frame_retained": True,
            "collapsed_tokens_retained": True,
            "strict_panphon_classification_retained": True,
            "reason": (
                "Retain auditable model evidence for the full benchmark while "
                "avoiding unnecessary multi-gigabyte duplicate logits."
            ),
        },
        "clips": clip_index,
        "claim_boundaries": {
            "held_out_evaluation": False,
            "calibrated_confidence": False,
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
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--backend", choices=("cpu", "mps"), default="mps")
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--max-new-clips", type=int)
    args = parser.parse_args()
    path, summary = run_benchmark(
        args.manifest.resolve(),
        args.model.resolve(),
        args.output.resolve(),
        args.backend,
        args.repeats,
        args.max_new_clips,
    )
    if summary.get("complete") is False:
        print(f"PhoneticXEUS benchmark safely paused: {len(summary['clips'])} clips")
    else:
        print(f"PhoneticXEUS benchmark complete: {len(summary['clips'])} clips")
        print(f"Private process record: {path.relative_to(REPOSITORY_ROOT)}")


if __name__ == "__main__":
    main()
