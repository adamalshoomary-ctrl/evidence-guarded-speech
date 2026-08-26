"""Feasibility probe for the CC0 Wav2Vec2 CommonPhone recognizer.

Standalone script for the isolated ``commonphone-e856cb9-venv`` environment.
It verifies the pinned safetensors snapshot without ever touching a pickle,
rebuilds the author's CC0 harness architecture (PKlumpp/phd_model, commit
``dfff4848baf1a6698c245e83f8768a577c353558``, CC0-1.0) from its published
definition, and measures output shape, repeatability, runtime and peak memory
on a small label-blind development subset.

Supporting-only role: this model was trained on Common Phone, which derives
from Common Voice, so the project's Common Phone and Australian Common Voice
evidence are non-independent of it and can never count toward its selection.
Outputs are candidate phone evidence, never truth.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import resource
import struct
import time
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
PRIVATE_ROOT = REPOSITORY_ROOT / ".research_data" / "speech_sound_patterns"
MODEL_ROOT = PRIVATE_ROOT / "models" / "commonphone-e856cb9"
MANIFEST_PATH = (
    PRIVATE_ROOT
    / "benchmark"
    / "repair-v1"
    / "expected-only-manifest-v1.0.0.json"
)
MANIFEST_SHA256 = (
    "c918feffa7c0a3a3fa99ce7a9e028621e8fb002980777297f30088e5975331da"
)
OUTPUT_PATH = PRIVATE_ROOT / "feasibility" / "commonphone-e856cb9-probe.json"
CLIP_COUNT = 4
REPEATS = 2

# IPA symbol table copied from the CC0-licensed harness
# github.com/PKlumpp/phd_model, phonetics/ipa.py, commit dfff4848; blank is 0.
SYMBOLS = {
    "r": 1, "ʝ": 2, "ã": 3, "gː": 4, "t": 5, "n": 6, "w": 7, "u": 8,
    "l": 9, "yː": 10, "ʎ": 11, "bʲ": 12, "ə": 13, "ʃʲ": 14, "sː": 15,
    "zʲ": 16, "kː": 17, "y": 18, "ɒ": 19, "fʲ": 20, "ɑ": 21, "ʏ": 22,
    "ɣ": 23, "s": 24, "m": 25, "tː": 26, "xʲ": 27, "vː": 28, "ø": 29,
    "h": 30, "ɨ": 31, "dʲ": 32, "dː": 33, "bː": 34, "ɲː": 35, "ɑː": 36,
    "ɪ": 37, "ɛ": 38, "i": 39, "ʔ": 40, "g": 41, "ʃ": 42, "ɜː": 43,
    "mː": 44, "øː": 45, "fː": 46, "p": 47, "iː": 48, "(...)": 49,
    "v": 50, "ʌ": 51, "b": 52, "k": 53, "x": 54, "ɲ": 55, "ʒ": 56,
    "rː": 57, "eː": 58, "ç": 59, "ŋ": 60, "ɔː": 61, "œ": 62, "ẽ": 63,
    "θ": 64, "a": 65, "rʲ": 66, "vʲ": 67, "ʃː": 68, "æ": 69, "ɶ̃": 70,
    "pː": 71, "nː": 72, "lʲ": 73, "õ": 74, "pʲ": 75, "ɱ": 76, "ð": 77,
    "f": 78, "j": 79, "o": 80, "nʲ": 81, "sʲ": 82, "lː": 83, "e": 84,
    "d": 85, "ʊ": 86, "gʲ": 87, "z": 88, "ɛː": 89, "tʲ": 90, "β": 91,
    "mʲ": 92, "uː": 93, "ɥ": 94, "ʀ": 95, "aː": 96, "ɐ": 97, "ɔ": 98,
    "oː": 99, "ʎː": 100, "kʲ": 101,
}
INDEX_TO_SYMBOL = {index: symbol for symbol, index in SYMBOLS.items()}
CLASS_COUNT = 102


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_safetensors_header(path):
    """Parse the safetensors JSON header without loading any tensor."""
    with open(path, "rb") as handle:
        header_length = struct.unpack("<Q", handle.read(8))[0]
        if header_length > 100_000_000:
            raise ValueError("implausible safetensors header length")
        header = json.loads(handle.read(header_length))
    header.pop("__metadata__", None)
    return header


def greedy_collapse(indices, blank=0):
    result = []
    previous = None
    for index in indices:
        if index != blank and index != previous:
            result.append(int(index))
        previous = index
    return result


def main():
    if os.environ.get("SPEECH_SOUND_OFFLINE") != "1":
        raise SystemExit("probe requires SPEECH_SOUND_OFFLINE=1")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

    if file_sha256(MANIFEST_PATH) != MANIFEST_SHA256:
        raise SystemExit("expected-only manifest checksum changed")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if manifest.get("expert_outcomes_included") is not False:
        raise SystemExit("manifest must remain label blind")
    clips = [
        clip
        for clip in manifest["clips"]
        if clip["project_split"] == "development"
    ][:CLIP_COUNT]

    weights_path = MODEL_ROOT / "model.safetensors"
    config_path = MODEL_ROOT / "xlsr53-config.json"
    model_files = {
        "model.safetensors": file_sha256(weights_path),
        "config.json": file_sha256(MODEL_ROOT / "config.json"),
        "README.md": file_sha256(MODEL_ROOT / "README.md"),
        "xlsr53-config.json": file_sha256(config_path),
    }

    header = read_safetensors_header(weights_path)
    linear_weight = header.get("linear.weight")
    if not linear_weight or linear_weight["shape"] != [CLASS_COUNT, 1024]:
        raise SystemExit("safetensors head shape is not 102 by 1024")
    pickle_free = True

    import numpy as np
    import soundfile
    import torch
    from safetensors.torch import load_file
    from transformers import Wav2Vec2Config, Wav2Vec2Model

    torch.set_num_threads(1)
    torch.manual_seed(0)

    config = Wav2Vec2Config(**json.loads(config_path.read_text()))
    backbone = Wav2Vec2Model(config)
    head = torch.nn.Linear(1024, CLASS_COUNT)
    state = load_file(weights_path)
    backbone_state = {
        key[len("wav2vec."):]: value
        for key, value in state.items()
        if key.startswith("wav2vec.")
    }
    head_state = {
        key[len("linear."):]: value
        for key, value in state.items()
        if key.startswith("linear.")
    }
    if set(state) != {
        *(f"wav2vec.{key}" for key in backbone_state),
        *(f"linear.{key}" for key in head_state),
    }:
        raise SystemExit("unexpected keys in the pinned safetensors state")
    missing, unexpected = backbone.load_state_dict(backbone_state, strict=False)
    unexpected = [key for key in unexpected if "masked_spec_embed" not in key]
    if unexpected or any("masked_spec_embed" not in key for key in missing):
        raise SystemExit(
            f"backbone state mismatch: missing={missing} unexpected={unexpected}"
        )
    head.load_state_dict(head_state)
    backbone.eval()
    head.eval()

    clip_records = []
    total_audio = 0.0
    total_seconds = 0.0
    for clip in clips:
        audio_path = REPOSITORY_ROOT / clip["canonical_audio_path"]
        if file_sha256(audio_path) != clip["canonical_audio_sha256"]:
            raise SystemExit(f"audio checksum changed: {clip['safe_id']}")
        waveform, sample_rate = soundfile.read(audio_path, dtype="float32")
        if sample_rate != 16000 or waveform.ndim != 1:
            raise SystemExit("probe requires 16 kHz mono audio")
        standardized = (waveform - waveform.mean()) / (waveform.std() + 1e-9)
        tensor = torch.tensor(standardized, dtype=torch.float32)[None, :]
        repeats = []
        started = time.perf_counter()
        for _ in range(REPEATS):
            with torch.no_grad():
                hidden = backbone(tensor).last_hidden_state
                logits = head(hidden)[0]
            indices = greedy_collapse(logits.argmax(dim=-1).tolist())
            repeats.append(
                {
                    "frame_count": int(logits.shape[0]),
                    "class_count": int(logits.shape[1]),
                    "logits_sha256": hashlib.sha256(
                        logits.numpy().tobytes()
                    ).hexdigest(),
                    "collapsed_indices": indices,
                    "collapsed_symbols": [
                        INDEX_TO_SYMBOL[index] for index in indices
                    ],
                }
            )
        seconds = time.perf_counter() - started
        exact = repeats[0] == repeats[1]
        if not exact:
            raise SystemExit(f"repeats differ for {clip['safe_id']}")
        clip_records.append(
            {
                "safe_id": clip["safe_id"],
                "input_sha256": clip["canonical_audio_sha256"],
                "duration_s": clip["duration_s"],
                "frame_count": repeats[0]["frame_count"],
                "class_count": repeats[0]["class_count"],
                "collapsed_token_count": len(repeats[0]["collapsed_indices"]),
                "same_input_repeats_exact": True,
                "seconds_for_two_repeats": round(seconds, 6),
            }
        )
        total_audio += clip["duration_s"]
        total_seconds += seconds

    report = {
        "probe_id": "commonphone_feasibility_probe",
        "schema_version": "1.0.0",
        "role": "supporting_only_local_comparator",
        "model_id": "pklumpp/Wav2Vec2_CommonPhone",
        "model_revision": "e856cb96ef8fc5972ba43310d61cb4b3d6bc1e87",
        "harness_provenance": (
            "architecture and IPA symbol table adapted from CC0-1.0 "
            "github.com/PKlumpp/phd_model commit "
            "dfff4848baf1a6698c245e83f8768a577c353558"
        ),
        "weights_licence": "cc0-1.0",
        "pickle_files_downloaded_or_loaded": not pickle_free,
        "non_independent_sources": [
            "common_phone_1_0",
            "common_voice_26_australian_english",
        ],
        "model_files_sha256": model_files,
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "torch_threads": 1,
        "clip_count": len(clip_records),
        "total_audio_seconds": round(total_audio, 6),
        "total_processing_seconds": round(total_seconds, 6),
        "real_time_factor_two_repeats": round(total_seconds / total_audio, 6),
        "peak_maxrss_bytes": resource.getrusage(
            resource.RUSAGE_SELF
        ).ru_maxrss,
        "all_repeats_exact": True,
        "clips": clip_records,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
