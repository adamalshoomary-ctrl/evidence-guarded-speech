"""Run the supporting-only Wav2Vec2 CommonPhone lane over a frozen sample.

Standalone script for the isolated ``commonphone-e856cb9-venv`` environment, in
the same style as ``commonphone_probe.py``: the pinned safetensors snapshot is
verified without ever touching a pickle, and every heavy import happens inside
``main``.

This lane is supporting only and can never contribute to a selection gate. It
was trained on Common Phone, which derives from Common Voice, so this project's
Common Phone and Australian Common Voice evidence are not independent of it.
It is run here on the SpeechOcean clips alone, where that overlap does not
apply, purely as a third opinion for system disagreement evidence.

    env SPEECH_SOUND_OFFLINE=1 \\
      "$CP_ENV/bin/python" speech_sound_patterns/comparison_commonphone.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import struct
import sys
import time
from pathlib import Path

try:
    import resource
except ModuleNotFoundError:  # Windows has no resource module
    resource = None


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
PRIVATE_ROOT = REPOSITORY_ROOT / ".research_data" / "speech_sound_patterns"
MODEL_ROOT = PRIVATE_ROOT / "models" / "commonphone-e856cb9"
# This runner lives in an isolated environment and cannot import the package, so
# the frozen identities are restated here. ``tests/test_speech_sound_powered_sample``
# asserts this table equals ``comparison.COMPARISON_VERSIONS`` field for field, so
# the two copies cannot drift apart.
COMPARISON_VERSIONS = {
    "1.0.0": {
        "checkpoint": "22E4",
        "expected_manifest_path": (
            PRIVATE_ROOT
            / "benchmark"
            / "repair-v1"
            / "expected-only-manifest-v1.0.0.json"
        ),
        "expected_only_manifest_sha256": (
            "c918feffa7c0a3a3fa99ce7a9e028621e8fb002980777297f30088e5975331da"
        ),
        "private_root": PRIVATE_ROOT / "benchmark" / "comparison-v1",
        "expected_only_clip_count": 480,
    },
    "1.1.0": {
        "checkpoint": "22E4B",
        "expected_manifest_path": (
            PRIVATE_ROOT / "benchmark" / "v2" / "expected-only-manifest-v1.1.0.json"
        ),
        "expected_only_manifest_sha256": (
            "a609994485db13e4d61b76c635459f26709bf8031f551de0c610a27b4816eace"
        ),
        "private_root": PRIVATE_ROOT / "benchmark" / "comparison-v2",
        "expected_only_clip_count": 2280,
    },
}
ACTIVE_COMPARISON_VERSION = "1.1.0"

LANE_ID = "wav2vec2_commonphone"
MODEL_REVISION = "e856cb96ef8fc5972ba43310d61cb4b3d6bc1e87"
SAME_INPUT_REPEATS = 2

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


def peak_maxrss_bytes():
    """Peak resident memory, or a refusal where the platform cannot report it.

    The resource module is Unix only. Windows offers no standard library
    equivalent, and a provenance summary that quietly recorded nothing would
    state a measurement this project cannot support. Refusing keeps the record
    honest and keeps the module importable everywhere, which matters because a
    bare import of resource failed the whole test module on Windows.
    """
    if resource is None:
        raise RuntimeError(
            "peak memory cannot be recorded on this platform because the "
            "resource module is Unix only, so no provenance summary is written"
        )
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(document):
    return (
        json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def read_safetensors_header(path):
    """Parse the safetensors JSON header without loading any tensor."""
    with open(path, "rb") as handle:
        header_length = struct.unpack("<Q", handle.read(8))[0]
        if header_length > 100_000_000:
            raise SystemExit("implausible safetensors header length")
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


def _load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def comparison_profile(version):
    profile = COMPARISON_VERSIONS.get(version)
    if profile is None:
        raise SystemExit(f"unknown comparison version: {version}")
    return profile


def gate_clips(version=ACTIVE_COMPARISON_VERSION):
    profile = comparison_profile(version)
    if file_sha256(profile["expected_manifest_path"]) != profile[
        "expected_only_manifest_sha256"
    ]:
        raise SystemExit("expected-only manifest checksum changed")
    manifest = _load_json(profile["expected_manifest_path"])
    if manifest.get("expert_outcomes_included") is not False:
        raise SystemExit("the candidate input manifest is not label blind")
    if manifest.get("held_out_participants") != 0:
        raise SystemExit("the candidate input manifest holds held-out clips")
    if len(manifest["clips"]) != profile["expected_only_clip_count"]:
        raise SystemExit("the candidate input manifest changed size")
    return [
        {
            "safe_id": clip["safe_id"],
            "source_id": "speechocean762",
            "project_split": clip["project_split"],
            "source_stratum": clip["source_stratum"],
            "canonical_audio_path": clip["canonical_audio_path"],
            "canonical_audio_sha256": clip["canonical_audio_sha256"],
            "duration_s": clip["duration_s"],
        }
        for clip in manifest["clips"]
    ]


def existing_records(output_root):
    clips_root = Path(output_root) / "clips"
    if not clips_root.is_dir():
        return {}
    records = {}
    for path in sorted(clips_root.glob("*.json")):
        record = _load_json(path)
        records[record["safe_id"]] = (path, record)
    return records


def verify_existing(records, wanted):
    for safe_id, (path, record) in records.items():
        clip = wanted.get(safe_id)
        if clip is None:
            raise SystemExit(f"{safe_id} is not in the frozen comparison set")
        if record["input_sha256"] != clip["canonical_audio_sha256"]:
            raise SystemExit(f"{safe_id} audio identity changed")
        if record.get("same_input_repeats_exact") is not True:
            raise SystemExit(f"{safe_id} did not repeat exactly")
        if record.get("expert_outcomes_read") is not False:
            raise SystemExit(f"{safe_id} claims an expert outcome was read")
        if record.get("selection_eligible") is not False:
            raise SystemExit(f"{safe_id} claims selection eligibility")
        if canonical_json_bytes(record) != path.read_bytes():
            raise SystemExit(f"{safe_id} record is not canonical")


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Run the supporting-only CommonPhone lane over a frozen comparison "
            "sample. The default is the powered checkpoint 22E4B sample; pass "
            "--comparison-version 1.0.0 for the checkpoint 22E4 record."
        )
    )
    parser.add_argument("--output-root", type=Path, default=None)
    parser.add_argument("--max-new-clips", type=int, default=None)
    parser.add_argument("--comparison-version", default=ACTIVE_COMPARISON_VERSION)
    arguments = parser.parse_args()
    profile = comparison_profile(arguments.comparison_version)
    if arguments.output_root is None:
        arguments.output_root = profile["private_root"] / "evidence" / "commonphone"

    if os.environ.get("SPEECH_SOUND_OFFLINE") != "1":
        raise SystemExit("this lane requires SPEECH_SOUND_OFFLINE=1")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

    output_root = Path(arguments.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    summary_path = output_root / "commonphone-comparison-process.json"
    if summary_path.exists():
        raise SystemExit("completed CommonPhone comparison evidence already exists")

    clips = gate_clips(arguments.comparison_version)
    wanted = {clip["safe_id"]: clip for clip in clips}
    records = existing_records(output_root)
    verify_existing(records, wanted)
    remaining = [clip for clip in clips if clip["safe_id"] not in records]
    if arguments.max_new_clips is not None:
        remaining = remaining[: arguments.max_new_clips]

    weights_path = MODEL_ROOT / "model.safetensors"
    config_path = MODEL_ROOT / "xlsr53-config.json"
    model_files = {
        "model.safetensors": file_sha256(weights_path),
        "config.json": file_sha256(MODEL_ROOT / "config.json"),
        "xlsr53-config.json": file_sha256(config_path),
    }
    header = read_safetensors_header(weights_path)
    linear_weight = header.get("linear.weight")
    if not linear_weight or linear_weight["shape"] != [CLASS_COUNT, 1024]:
        raise SystemExit("safetensors head shape is not 102 by 1024")

    clips_root = output_root / "clips"
    clips_root.mkdir(parents=True, exist_ok=True)

    if remaining:
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
            key[len("wav2vec.") :]: value
            for key, value in state.items()
            if key.startswith("wav2vec.")
        }
        head_state = {
            key[len("linear.") :]: value
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
            raise SystemExit("backbone state mismatch")
        head.load_state_dict(head_state)
        backbone.eval()
        head.eval()

    for clip in remaining:
        audio_path = REPOSITORY_ROOT / clip["canonical_audio_path"]
        if file_sha256(audio_path) != clip["canonical_audio_sha256"]:
            raise SystemExit(f"audio checksum changed: {clip['safe_id']}")
        waveform, sample_rate = soundfile.read(audio_path, dtype="float32")
        if sample_rate != 16000 or waveform.ndim != 1:
            raise SystemExit("this lane requires 16 kHz mono audio")
        standardized = (waveform - waveform.mean()) / (waveform.std() + 1e-9)
        tensor = torch.tensor(standardized, dtype=torch.float32)[None, :]
        repeats = []
        started = time.perf_counter()
        for _ in range(SAME_INPUT_REPEATS):
            with torch.no_grad():
                hidden = backbone(tensor).last_hidden_state
                logits = head(hidden)[0]
            indices = greedy_collapse(logits.argmax(dim=-1).tolist())
            repeats.append(
                {
                    "frame_count": int(logits.shape[0]),
                    "logits_sha256": hashlib.sha256(
                        logits.numpy().tobytes()
                    ).hexdigest(),
                    "phones": [INDEX_TO_SYMBOL[index] for index in indices],
                }
            )
        seconds = time.perf_counter() - started
        if repeats[0] != repeats[1]:
            raise SystemExit(f"repeats differ for {clip['safe_id']}")

        record = {
            "safe_id": clip["safe_id"],
            "lane_id": LANE_ID,
            "source_id": clip["source_id"],
            "evidence_role": "supporting_only_disagreement",
            "selection_eligible": False,
            "project_split": clip["project_split"],
            "source_stratum": clip["source_stratum"],
            "input_sha256": clip["canonical_audio_sha256"],
            "duration_s": clip["duration_s"],
            "model_revision": MODEL_REVISION,
            "same_input_repeats": SAME_INPUT_REPEATS,
            "same_input_repeats_exact": True,
            "expert_outcomes_read": False,
            "target_given_to_model": False,
            "seconds_for_all_repeats": round(seconds, 6),
            "frame_count": repeats[0]["frame_count"],
            "logits_sha256": repeats[0]["logits_sha256"],
            "phones": repeats[0]["phones"],
            "phone_token_count": len(repeats[0]["phones"]),
        }
        (clips_root / f"{clip['safe_id']}.json").write_bytes(
            canonical_json_bytes(record)
        )

    finished = existing_records(output_root)
    verify_existing(finished, wanted)
    if set(finished) != set(wanted):
        print(
            json.dumps(
                {
                    "status": "paused_incomplete",
                    "completed_clips": len(finished),
                    "expected_clips": len(wanted),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return

    total_audio = 0.0
    total_seconds = 0.0
    phone_tokens = 0
    for safe_id in sorted(finished):
        _, record = finished[safe_id]
        total_audio += record["duration_s"]
        total_seconds += record["seconds_for_all_repeats"]
        phone_tokens += record["phone_token_count"]

    summary = {
        "summary_id": "commonphone_comparison_process",
        "schema_version": "1.0.0",
        "checkpoint": profile["checkpoint"],
        "lane_id": LANE_ID,
        "role": "supporting_only_local_comparator",
        "selection_eligible": False,
        "model_id": "pklumpp/Wav2Vec2_CommonPhone",
        "model_revision": MODEL_REVISION,
        "weights_licence": "cc0-1.0",
        "harness_provenance": (
            "architecture and IPA symbol table adapted from CC0-1.0 "
            "github.com/PKlumpp/phd_model commit "
            "dfff4848baf1a6698c245e83f8768a577c353558"
        ),
        "expected_only_manifest_sha256": profile["expected_only_manifest_sha256"],
        "model_files_sha256": model_files,
        "pickle_files_downloaded_or_loaded": False,
        "non_independent_sources": [
            "common_phone_1_0",
            "common_voice_26_australian_english",
        ],
        "execution": {
            "clip_count": len(finished),
            "held_out_participants": 0,
            "expert_outcomes_read_by_candidate_runner": False,
            "target_given_to_model": False,
            "same_input_repeats": SAME_INPUT_REPEATS,
            "all_repeats_exact": True,
            "network_access": False,
        },
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "phone_tokens": phone_tokens,
        "total_audio_seconds": round(total_audio, 6),
        "total_processing_seconds": round(total_seconds, 6),
        "real_time_factor_all_repeats": round(total_seconds / total_audio, 6),
        "peak_maxrss_bytes": peak_maxrss_bytes(),
    }
    summary_path.write_bytes(canonical_json_bytes(summary))
    print(
        json.dumps(
            {
                "status": "complete",
                "clip_count": summary["execution"]["clip_count"],
                "real_time_factor_all_repeats": summary[
                    "real_time_factor_all_repeats"
                ],
                "summary_path": summary_path.relative_to(REPOSITORY_ROOT).as_posix(),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
