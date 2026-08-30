"""Run the POWSM free-phone lane over a frozen comparison sample.

Standalone script for the isolated ``powsm-21ffa41-venv`` environment, in the
same style as ``powsm_probe.py``: the pinned checkpoint's pickle is audited
opcode by opcode before any weight is loaded, and every import that needs the
isolated environment happens inside ``main``.

POWSM is given no target. It listens and writes down the phones it hears, which
is why it is the one lane that could in principle name a produced sound without
being told what to expect. That also means its output is a candidate phone
sequence and never truth, and agreement with another IPAPack++ family model is
never independent confirmation.

Two sets of clips are processed and kept apart:

* the frozen SpeechOcean clips, which carry expert phone relations and are the
  only clips the selection gates may use, 480 at checkpoint 22E4 and 2,280 in
  the powered checkpoint 22E4B sample; and
* the 85 Acted Clear, Common Phone and Australian Common Voice clips, which
  carry no phone relation truth and are recorded as availability, repeatability
  and system disagreement evidence only.

This runner never reads an expert outcome. The relations are joined later, by a
separate scoring step, after every candidate output is complete.

    env SPEECH_SOUND_OFFLINE=1 \\
      "$POWSM_ENV/bin/python" speech_sound_patterns/comparison_powsm.py

The default sample is the powered checkpoint 22E4B one. Pass
``--comparison-version 1.0.0`` to address the checkpoint 22E4 record instead.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import pickletools
import platform
import sys
import time
import zipfile
from pathlib import Path

try:
    import resource
except ModuleNotFoundError:  # Windows has no resource module
    resource = None


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
PRIVATE_ROOT = REPOSITORY_ROOT / ".research_data" / "speech_sound_patterns"
MODEL_ROOT = PRIVATE_ROOT / "models" / "powsm-21ffa41"
CONFIG_PATH = MODEL_ROOT / (
    "exp/s2t_train_s2t_ebf_conv2d_size768_e9_d9_piecewise_lr5e-4_"
    "warmup60k_flashattn_raw_bpe40000/config.yaml"
)
WEIGHTS_PATH = MODEL_ROOT / (
    "exp/s2t_train_s2t_ebf_conv2d_size768_e9_d9_piecewise_lr5e-4_"
    "warmup60k_flashattn_raw_bpe40000/valid.acc.ave_5best.till45epoch.pth"
)
BPE_PATH = MODEL_ROOT / "data/token_list/bpe_unigram40000/bpe.model"
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
        "benchmark_manifest_path": (
            PRIVATE_ROOT / "benchmark" / "benchmark-manifest-v1.0.0.json"
        ),
        "benchmark_manifest_sha256": (
            "e856b2fef404cd28c9d09c6748797e1c6b888361c83c8d62f47ebf2560e03b98"
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
        "benchmark_manifest_path": (
            PRIVATE_ROOT / "benchmark" / "benchmark-manifest-v1.1.0.json"
        ),
        "benchmark_manifest_sha256": (
            "1b5599962c8ae9905dd740dcd6a91737dcf38b712492eb1fce9f3b6704f7ef30"
        ),
        "private_root": PRIVATE_ROOT / "benchmark" / "comparison-v2",
        "expected_only_clip_count": 2280,
    },
}
ACTIVE_COMPARISON_VERSION = "1.1.0"

LANE_ID = "powsm"
MODEL_REVISION = "21ffa410432ace159f3c1fdeed304c70eddf7d34"
SAME_INPUT_REPEATS = 2
SAMPLE_RATE = 16000
WINDOW_SECONDS = 20
SECONDARY_SOURCE_IDS = (
    "acted_clear_speech",
    "common_phone_1_0",
    "common_voice_26_australian_english",
)

SAFE_PICKLE_GLOBALS = {
    "collections OrderedDict",
    "torch._utils _rebuild_tensor_v2",
    "torch._utils _rebuild_parameter",
    "torch FloatStorage",
    "torch HalfStorage",
    "torch BFloat16Storage",
    "torch DoubleStorage",
    "torch LongStorage",
    "torch IntStorage",
    "torch ShortStorage",
    "torch CharStorage",
    "torch ByteStorage",
    "torch BoolStorage",
}


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


def audit_torch_pickle(path):
    """Collect every pickle global in a torch zip checkpoint, fail closed."""
    observed = set()
    with zipfile.ZipFile(path) as archive:
        pickle_members = [
            name for name in archive.namelist() if name.endswith(".pkl")
        ]
        if not pickle_members:
            raise SystemExit("checkpoint contains no pickle member to audit")
        for name in pickle_members:
            data = archive.read(name)
            recent_strings = []
            for opcode, argument, _ in pickletools.genops(io.BytesIO(data)):
                if opcode.name in {
                    "SHORT_BINUNICODE",
                    "BINUNICODE",
                    "BINUNICODE8",
                    "UNICODE",
                }:
                    recent_strings.append(argument)
                    recent_strings = recent_strings[-2:]
                elif opcode.name == "GLOBAL":
                    observed.add(str(argument))
                elif opcode.name == "STACK_GLOBAL":
                    if len(recent_strings) < 2:
                        raise SystemExit(
                            "unresolvable STACK_GLOBAL in checkpoint pickle"
                        )
                    observed.add(" ".join(recent_strings[-2:]))
    unexpected = sorted(observed - SAFE_PICKLE_GLOBALS)
    if unexpected:
        raise SystemExit(
            "checkpoint pickle requests unexpected globals, refusing to load: "
            f"{unexpected}"
        )
    return sorted(observed)


def _load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def comparison_profile(version):
    profile = COMPARISON_VERSIONS.get(version)
    if profile is None:
        raise SystemExit(f"unknown comparison version: {version}")
    return profile


def gate_clips(version=ACTIVE_COMPARISON_VERSION):
    """The label-blind clips the selection gates may use."""
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
            "evidence_role": "selection_gate_eligible",
            "project_split": clip["project_split"],
            "source_stratum": clip["source_stratum"],
            "canonical_audio_path": clip["canonical_audio_path"],
            "canonical_audio_sha256": clip["canonical_audio_sha256"],
            "duration_s": clip["duration_s"],
        }
        for clip in manifest["clips"]
    ]


def secondary_clips(version=ACTIVE_COMPARISON_VERSION):
    """The 85 clips that carry no phone relation truth.

    Only the fields needed to locate and verify audio are copied out, so no
    reference text, alignment or reviewer material can travel with them. Their
    evidence role is fixed here, in the runner, so nothing downstream can
    mistake them for gate evidence.
    """
    profile = comparison_profile(version)
    if file_sha256(profile["benchmark_manifest_path"]) != profile[
        "benchmark_manifest_sha256"
    ]:
        raise SystemExit("private benchmark manifest checksum changed")
    manifest = _load_json(profile["benchmark_manifest_path"])
    if manifest.get("held_out_evaluation_accessed") is not False:
        raise SystemExit("the private benchmark manifest claims held-out access")
    clips = []
    for source in manifest["sources"]:
        if source["source_id"] not in SECONDARY_SOURCE_IDS:
            continue
        for clip in source["clips"]:
            clips.append(
                {
                    "safe_id": clip["safe_id"],
                    "source_id": source["source_id"],
                    "evidence_role": "non_gate_availability_and_disagreement",
                    "project_split": clip["project_split"],
                    "source_stratum": clip["source_stratum"],
                    "canonical_audio_path": clip["canonical_audio_path"],
                    "canonical_audio_sha256": clip["canonical_audio_sha256"],
                    "duration_s": clip["duration_s"],
                }
            )
    return clips


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
        # A clip the model cannot accept has no repeats to compare. It must say
        # so explicitly; it may never claim an exact repeat it never performed.
        if record.get("processed", True) is False:
            if record.get("unprocessable_reason") != (
                "clip_exceeds_model_declared_speech_length"
            ):
                raise SystemExit(f"{safe_id} claims an unsupported failure reason")
            if record.get("phone_token_count") != 0:
                raise SystemExit(f"{safe_id} is unprocessed but carries output")
        elif record.get("same_input_repeats_exact") is not True:
            raise SystemExit(f"{safe_id} did not repeat exactly")
        if record.get("expert_outcomes_read") is not False:
            raise SystemExit(f"{safe_id} claims an expert outcome was read")
        if record.get("model_revision") != MODEL_REVISION:
            raise SystemExit(f"{safe_id} used another model revision")
        if canonical_json_bytes(record) != path.read_bytes():
            raise SystemExit(f"{safe_id} record is not canonical")


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Run the POWSM free-phone lane over a frozen comparison sample. The "
            "default is the powered checkpoint 22E4B sample; pass "
            "--comparison-version 1.0.0 for the checkpoint 22E4 record."
        )
    )
    parser.add_argument("--output-root", type=Path, default=None)
    parser.add_argument("--max-new-clips", type=int, default=None)
    parser.add_argument("--comparison-version", default=ACTIVE_COMPARISON_VERSION)
    arguments = parser.parse_args()
    profile = comparison_profile(arguments.comparison_version)
    if arguments.output_root is None:
        arguments.output_root = profile["private_root"] / "evidence" / "powsm"

    if os.environ.get("SPEECH_SOUND_OFFLINE") != "1":
        raise SystemExit("the POWSM lane requires SPEECH_SOUND_OFFLINE=1")
    os.environ["HF_HUB_OFFLINE"] = "1"

    # Inference has to run from the snapshot root, so every path here is made
    # absolute before anything changes the working directory.
    output_root = Path(arguments.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    summary_path = output_root / "powsm-comparison-process.json"
    if summary_path.exists():
        raise SystemExit("completed POWSM comparison evidence already exists")

    version = arguments.comparison_version
    clips = gate_clips(version) + secondary_clips(version)
    wanted = {clip["safe_id"]: clip for clip in clips}
    if len(wanted) != len(clips):
        raise SystemExit("duplicate safe identifiers in the comparison set")
    records = existing_records(output_root)
    verify_existing(records, wanted)
    remaining = [clip for clip in clips if clip["safe_id"] not in records]
    if arguments.max_new_clips is not None:
        remaining = remaining[: arguments.max_new_clips]

    model_files = {
        "config.yaml": file_sha256(CONFIG_PATH),
        "weights.pth": file_sha256(WEIGHTS_PATH),
        "bpe.model": file_sha256(BPE_PATH),
    }
    audited_globals = audit_torch_pickle(WEIGHTS_PATH)

    clips_root = output_root / "clips"
    clips_root.mkdir(parents=True, exist_ok=True)

    load_seconds = None
    speech2text = None
    if remaining:
        # espnet still imports distutils, which Python 3.12 removed. The pinned
        # setuptools carries the replacement, but its import hook only resolves
        # the name once setuptools itself has been imported, so this import must
        # come first. It changes no pinned version and loads no new package.
        import setuptools  # noqa: F401
        import numpy as np
        import soundfile
        import torch

        torch.set_num_threads(1)
        torch.manual_seed(0)

        from espnet2.bin.s2t_inference import Speech2Text

        # The pinned config references its statistics and BPE files with paths
        # relative to the snapshot root, and the tokenizer resolves them lazily
        # on first use, so the working directory has to stay there for the whole
        # inference loop rather than only for the load.
        working_directory = Path.cwd()
        os.chdir(MODEL_ROOT)
        load_started = time.perf_counter()
        speech2text = Speech2Text(
            s2t_train_config=str(CONFIG_PATH),
            s2t_model_file=str(WEIGHTS_PATH),
            device="cpu",
            beam_size=1,
            lang_sym="<eng>",
            task_sym="<pr>",
        )
        load_seconds = time.perf_counter() - load_started

    window_samples = SAMPLE_RATE * WINDOW_SECONDS
    for clip in remaining:
        audio_path = REPOSITORY_ROOT / clip["canonical_audio_path"]
        if file_sha256(audio_path) != clip["canonical_audio_sha256"]:
            raise SystemExit(f"audio checksum changed: {clip['safe_id']}")
        waveform, sample_rate = soundfile.read(audio_path, dtype="float32")
        if sample_rate != SAMPLE_RATE or waveform.ndim != 1:
            raise SystemExit("this lane requires 16 kHz mono audio")
        if waveform.shape[0] > window_samples:
            # The pinned checkpoint's own config declares
            # preprocessor_conf.speech_length: 20, so a longer clip is outside
            # what this model accepts. Truncating it would drop real speech and
            # turn the dropped region into invented deletion concerns at every
            # target in it, which is worse than having no evidence. The clip is
            # therefore recorded as unprocessable by this lane, with its reason,
            # and the scorer abstains on its targets for this lane alone. Every
            # other lane still sees the clip. The powered checkpoint 22E4B sample
            # holds exactly one such clip; the checkpoint 22E4 sample held none.
            record = {
                "safe_id": clip["safe_id"],
                "lane_id": LANE_ID,
                "source_id": clip["source_id"],
                "evidence_role": clip["evidence_role"],
                "project_split": clip["project_split"],
                "source_stratum": clip["source_stratum"],
                "input_sha256": clip["canonical_audio_sha256"],
                "duration_s": clip["duration_s"],
                "model_revision": MODEL_REVISION,
                "processed": False,
                "unprocessable_reason": "clip_exceeds_model_declared_speech_length",
                "model_declared_speech_length_s": WINDOW_SECONDS,
                "same_input_repeats": 0,
                "expert_outcomes_read": False,
                "target_given_to_model": False,
                "phones": [],
                "phone_token_count": 0,
            }
            (clips_root / f"{clip['safe_id']}.json").write_bytes(
                canonical_json_bytes(record)
            )
            continue
        padded = np.zeros(window_samples, dtype=np.float32)
        padded[: waveform.shape[0]] = waveform

        repeats = []
        started = time.perf_counter()
        for _ in range(SAME_INPUT_REPEATS):
            with torch.no_grad():
                results = speech2text(padded, text_prev="<na>")
            raw = results[0][0]
            text = raw
            if "<notimestamps>" in text:
                text = text.split("<notimestamps>", 1)[1].strip()
            phones = [
                token.strip()
                for token in text.split("/")
                if token and not token.isspace()
            ]
            repeats.append(
                {
                    "raw_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
                    "phones": phones,
                }
            )
        seconds = time.perf_counter() - started
        if repeats[0] != repeats[1]:
            raise SystemExit(f"repeats differ for {clip['safe_id']}")

        record = {
            "safe_id": clip["safe_id"],
            "lane_id": LANE_ID,
            "source_id": clip["source_id"],
            "evidence_role": clip["evidence_role"],
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
            "raw_output_sha256": repeats[0]["raw_sha256"],
            "phones": repeats[0]["phones"],
            "phone_token_count": len(repeats[0]["phones"]),
        }
        (clips_root / f"{clip['safe_id']}.json").write_bytes(
            canonical_json_bytes(record)
        )

    if remaining:
        os.chdir(working_directory)

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

    by_role = {}
    total_audio = 0.0
    total_seconds = 0.0
    clip_summaries = []
    unprocessable = []
    for safe_id in sorted(finished):
        _, record = finished[safe_id]
        key = (record["source_id"], record["evidence_role"])
        bucket = by_role.setdefault(
            key,
            {
                "source_id": record["source_id"],
                "evidence_role": record["evidence_role"],
                "clips": 0,
                "clips_with_output": 0,
                "clips_unprocessable": 0,
                "phone_tokens": 0,
                "audio_seconds": 0.0,
            },
        )
        bucket["clips"] += 1
        bucket["clips_with_output"] += 1 if record["phone_token_count"] else 0
        bucket["phone_tokens"] += record["phone_token_count"]
        bucket["audio_seconds"] += record["duration_s"]
        if record.get("processed", True) is False:
            # Counted as a clip and as audio the lane was given, but never as
            # processing time, so the real time factor stays honest.
            bucket["clips_unprocessable"] += 1
            unprocessable.append(
                {
                    "source_id": record["source_id"],
                    "evidence_role": record["evidence_role"],
                    "project_split": record["project_split"],
                    "duration_s": record["duration_s"],
                    "reason": record["unprocessable_reason"],
                    "model_declared_speech_length_s": record[
                        "model_declared_speech_length_s"
                    ],
                }
            )
        else:
            total_audio += record["duration_s"]
            total_seconds += record["seconds_for_all_repeats"]
        clip_summaries.append(
            {
                "safe_id": safe_id,
                "source_id": record["source_id"],
                "phone_token_count": record["phone_token_count"],
            }
        )

    summary = {
        "summary_id": "powsm_comparison_process",
        "schema_version": "1.0.0",
        "checkpoint": profile["checkpoint"],
        "lane_id": LANE_ID,
        "model_id": "espnet/powsm",
        "model_revision": MODEL_REVISION,
        "weights_licence": "cc-by-4.0",
        "expected_only_manifest_sha256": profile["expected_only_manifest_sha256"],
        "private_benchmark_manifest_sha256": profile["benchmark_manifest_sha256"],
        "model_files_sha256": model_files,
        "pickle_audit": {
            "audited_before_load": True,
            "observed_globals": audited_globals,
            "unexpected_globals": [],
        },
        "inference_settings": {
            "task": "<pr>",
            "lang": "<eng>",
            "beam_size": 1,
            "device": "cpu",
            "window_seconds": WINDOW_SECONDS,
            "text_prev": "<na>",
        },
        "execution": {
            "clip_count": len(finished),
            "gate_eligible_clips": sum(
                1
                for _, record in finished.values()
                if record["evidence_role"] == "selection_gate_eligible"
            ),
            "held_out_participants": 0,
            "expert_outcomes_read_by_candidate_runner": False,
            "target_given_to_model": False,
            "same_input_repeats": SAME_INPUT_REPEATS,
            "all_repeats_exact": True,
            "network_access": False,
            "clips_processed": len(finished) - len(unprocessable),
            "clips_unprocessable": len(unprocessable),
        },
        "unprocessable_clips": unprocessable,
        "lineage_note": (
            "IPAPack++ training with G2P-derived labels; SpeechOcean762 and "
            "L2-ARCTIC are evaluation-only for this model; agreement with ZIPA "
            "is not independent confirmation"
        ),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "model_load_seconds": None if load_seconds is None else round(load_seconds, 6),
        "total_audio_seconds": round(total_audio, 6),
        "total_processing_seconds": round(total_seconds, 6),
        "real_time_factor_all_repeats": round(total_seconds / total_audio, 6),
        "peak_maxrss_bytes": peak_maxrss_bytes(),
        "by_source_and_role": [
            {**value, "audio_seconds": round(value["audio_seconds"], 6)}
            for _, value in sorted(by_role.items())
        ],
        "clips": clip_summaries,
    }
    summary_path.write_bytes(canonical_json_bytes(summary))
    print(
        json.dumps(
            {
                "status": "complete",
                "clip_count": summary["execution"]["clip_count"],
                "gate_eligible_clips": summary["execution"]["gate_eligible_clips"],
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
