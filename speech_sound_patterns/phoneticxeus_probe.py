"""Offline, version-locked PhoneticXEUS feasibility probe.

This module is executed only inside the ignored research environment. It emits
private raw model evidence and does not create a product speech-sound artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import time
from pathlib import Path

from .feasibility import (
    REPOSITORY_ROOT,
    canonical_json_bytes,
    file_sha256,
    validate_frozen_private_sample_manifest,
)


MODEL_REVISION = "8d83dee94817a07dc150f87d08f7e0ee01bdb66d"
MODEL_FILE_COUNT = 41
MODEL_TREE_SHA256 = "a3d1ee69e9dd4e2926c48f44d1765e0c11489e78ce9d3e06d49f5a3bd0a2ed3e"
MODEL_WEIGHTS_SHA256 = "ad58bf20a60e9d0380327bd8b2d0e8e90a9b8de2adccbfb479f9b21ea85eda18"
MODEL_WEIGHTS_SIZE = 2_300_089_432
PRIVATE_ROOT = REPOSITORY_ROOT / ".research_data" / "speech_sound_patterns"


def _model_tree_identity(model_root):
    rows = []
    for path in sorted(model_root.rglob("*")):
        if not path.is_file() or ".cache" in path.parts:
            continue
        if path.suffix == ".pyc" or "__pycache__" in path.parts:
            raise ValueError("pinned model snapshot contains generated Python cache")
        relative = path.relative_to(model_root).as_posix()
        rows.append(
            f"{relative}\0{path.stat().st_size}\0{file_sha256(path)}\n"
        )
    digest = hashlib.sha256("".join(rows).encode("utf-8")).hexdigest()
    return len(rows), digest


def verify_model_snapshot(model_root):
    model_root = model_root.resolve()
    if model_root.name != MODEL_REVISION:
        raise ValueError("PhoneticXEUS model directory is not the pinned revision")
    weights = model_root / "model.safetensors"
    if not weights.is_file():
        raise ValueError("pinned safetensors model is missing")
    if weights.stat().st_size != MODEL_WEIGHTS_SIZE:
        raise ValueError("PhoneticXEUS weights size does not match")
    if file_sha256(weights) != MODEL_WEIGHTS_SHA256:
        raise ValueError("PhoneticXEUS weights checksum does not match")
    if (model_root / "phoneticxeus_state_dict.pt").exists():
        raise ValueError("pickle checkpoint is prohibited")
    count, digest = _model_tree_identity(model_root)
    if count != MODEL_FILE_COUNT or digest != MODEL_TREE_SHA256:
        raise ValueError("PhoneticXEUS pinned source tree does not match")


def _private_output_root(path):
    resolved = path.resolve(strict=False)
    resolved.relative_to(PRIVATE_ROOT.resolve())
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _selected_clips(manifest, safe_ids):
    selected = []
    wanted = set(safe_ids or [])
    for source in manifest["sources"]:
        for clip in source["clips"]:
            if "phoneticxeus" not in clip["eligible_tools"]:
                continue
            if wanted and clip["safe_id"] not in wanted:
                continue
            selected.append((source["source_id"], clip))
    if wanted and wanted != {clip["safe_id"] for _, clip in selected}:
        missing = sorted(wanted - {clip["safe_id"] for _, clip in selected})
        raise ValueError(f"requested private samples are unavailable: {missing}")
    if not selected:
        raise ValueError("no eligible PhoneticXEUS clips were selected")
    return selected


def _load_waveform(path, expected_sha256):
    import numpy as np
    import soundfile as sf
    import torch

    if file_sha256(path) != expected_sha256:
        raise ValueError(f"canonical audio checksum changed: {path.name}")
    waveform, sample_rate = sf.read(path, dtype="float32", always_2d=True)
    if sample_rate != 16000 or waveform.shape[1] != 1:
        raise ValueError("PhoneticXEUS input must be mono 16 kHz audio")
    waveform = waveform[:, 0]
    if waveform.size == 0 or not np.isfinite(waveform).all():
        raise ValueError("PhoneticXEUS input contains no finite samples")
    peak = float(np.max(np.abs(waveform)))
    if not math.isfinite(peak) or peak > 1.00001:
        raise ValueError("PhoneticXEUS input amplitude is invalid")
    return torch.from_numpy(waveform.copy()), peak


def _collapsed_ctc(frame_ids, id_to_token, blank_id=0):
    collapsed = []
    previous = None
    for item in frame_ids:
        if item != previous and item != blank_id:
            collapsed.append(item)
        previous = item
    return collapsed, [id_to_token[str(item)] for item in collapsed]


def run_probe(manifest_path, model_root, output_root, backend, repeats, safe_ids):
    if os.environ.get("HF_HUB_OFFLINE") != "1" or os.environ.get(
        "TRANSFORMERS_OFFLINE"
    ) != "1":
        raise ValueError("PhoneticXEUS inference must run with network access disabled")
    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        raise ValueError("pinned model source must run without writing bytecode")
    if os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK") not in {None, "0"}:
        raise ValueError("silent MPS to CPU fallback is prohibited")
    verify_model_snapshot(model_root)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors = validate_frozen_private_sample_manifest(manifest, REPOSITORY_ROOT)
    if errors:
        raise ValueError("; ".join(errors))
    clips = _selected_clips(manifest, safe_ids)
    output_root = _private_output_root(output_root)

    import numpy as np
    import safetensors
    import soundfile
    import torch
    import torchaudio
    import transformers
    from huggingface_hub import __version__ as hub_version
    from safetensors.torch import save_file
    from transformers import AutoModel

    if backend not in {"cpu", "mps"}:
        raise ValueError("backend must be cpu or mps")
    if backend == "mps" and not torch.backends.mps.is_available():
        raise ValueError("MPS was requested but is unavailable")
    if repeats < 1 or repeats > 20:
        raise ValueError("repeats must be between one and twenty")
    torch.manual_seed(0)
    np.random.seed(0)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    device = torch.device(backend)

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

    clip_results = []
    for source_id, clip in clips:
        audio_path = REPOSITORY_ROOT / clip["canonical_audio_path"]
        waveform, peak = _load_waveform(
            audio_path, clip["canonical_audio_sha256"]
        )
        waveform = waveform.to(device)
        repeat_results = []
        first_frame_ids = None
        first_collapsed = None
        for repeat_index in range(repeats):
            started = time.perf_counter()
            with torch.inference_mode():
                logits = model(input_values=waveform).logits
            if backend == "mps":
                torch.mps.synchronize()
            elapsed = time.perf_counter() - started
            if not bool(torch.isfinite(logits).all().item()):
                raise ValueError(f"non-finite model output for {clip['safe_id']}")
            cpu_logits = logits.detach().to("cpu", dtype=torch.float32).contiguous()
            frame_ids = cpu_logits.argmax(dim=-1)[0].tolist()
            collapsed_ids, collapsed_tokens = _collapsed_ctc(
                frame_ids, id_to_token
            )
            raw_bytes = cpu_logits.numpy().tobytes(order="C")
            logit_digest = hashlib.sha256(raw_bytes).hexdigest()
            frame_digest = hashlib.sha256(
                json.dumps(frame_ids, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            if repeat_index == 0:
                first_frame_ids = frame_ids
                first_collapsed = collapsed_ids
                logits_path = (
                    output_root
                    / "logits"
                    / f"{backend}-{clip['safe_id']}.safetensors"
                )
                logits_path.parent.mkdir(parents=True, exist_ok=True)
                save_file(
                    {"ctc_logits": cpu_logits},
                    str(logits_path),
                    metadata={
                        "safe_id": clip["safe_id"],
                        "backend": backend,
                        "model_revision": MODEL_REVISION,
                        "evidence_class": "uncalibrated_contextual_ctc_logits",
                    },
                )
                top_values, top_ids = torch.topk(cpu_logits[0], k=5, dim=-1)
                top_frames = [
                    {
                        "frame_index": index,
                        "token_ids": top_ids[index].tolist(),
                        "raw_logits": [
                            round(float(item), 7) for item in top_values[index]
                        ],
                    }
                    for index in range(cpu_logits.shape[1])
                ]
                first_evidence = {
                    "frame_ids": frame_ids,
                    "collapsed_token_ids": collapsed_ids,
                    "collapsed_tokens": collapsed_tokens,
                    "top_five_per_frame": top_frames,
                    "logits_artifact": logits_path.relative_to(REPOSITORY_ROOT).as_posix(),
                    "logits_artifact_sha256": file_sha256(logits_path),
                }
            repeat_results.append(
                {
                    "repeat_index": repeat_index,
                    "runtime_s": round(elapsed, 6),
                    "logits_sha256": logit_digest,
                    "frame_argmax_sha256": frame_digest,
                    "frame_ids_exact_match_first": frame_ids == first_frame_ids,
                    "collapsed_ids_exact_match_first": collapsed_ids == first_collapsed,
                }
            )
        clip_results.append(
            {
                "safe_id": clip["safe_id"],
                "source_id": source_id,
                "input_sha256": clip["canonical_audio_sha256"],
                "duration_s": clip["duration_s"],
                "peak_absolute_amplitude": round(peak, 8),
                "logit_shape": [int(item) for item in cpu_logits.shape],
                "output_semantics": (
                    "greedy_fixed_inventory_phone_tokens_and_uncalibrated_"
                    "contextual_ctc_logits_not_phone_timestamps_or_confidence"
                ),
                **first_evidence,
                "repeats": repeat_results,
            }
        )

    result = {
        "schema_version": "1.0.0",
        "probe_id": "phoneticxeus_local_feasibility_v1",
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
        },
        "machine": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "mps_built": torch.backends.mps.is_built(),
            "mps_available": torch.backends.mps.is_available(),
        },
        "determinism": {
            "torch_seed": 0,
            "numpy_seed": 0,
            "torch_num_threads": 1,
            "deterministic_algorithms": True,
            "silent_mps_cpu_fallback": False,
        },
        "vocabulary": {
            "total_tokens": len(vocab),
            "special_tokens": 4,
            "phone_tokens": len(vocab) - 4,
            "sha256": file_sha256(model_root / "ipa_vocab.json"),
        },
        "clips": clip_results,
        "claim_boundaries": {
            "phone_timestamps": False,
            "calibrated_confidence": False,
            "sequence_alternatives": False,
            "produced_phone_truth": False,
            "pronunciation_correctness": False,
        },
    }
    result_path = output_root / f"phoneticxeus-{backend}-process.json"
    result_path.write_bytes(canonical_json_bytes(result))
    return result_path, result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--backend", required=True, choices=("cpu", "mps"))
    parser.add_argument("--repeats", required=True, type=int)
    parser.add_argument("--safe-id", action="append", default=[])
    args = parser.parse_args()
    path, result = run_probe(
        args.manifest.resolve(),
        args.model.resolve(),
        args.output.resolve(),
        args.backend,
        args.repeats,
        args.safe_id,
    )
    print(f"PhoneticXEUS {args.backend} probe: {len(result['clips'])} clips")
    print(f"Private raw evidence: {path.relative_to(REPOSITORY_ROOT)}")


if __name__ == "__main__":
    main()
