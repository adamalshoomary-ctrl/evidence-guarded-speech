"""Feasibility probe for the pinned POWSM phonetic foundation model.

Standalone script for the isolated ``powsm-21ffa41-venv`` environment. Before
any weight is loaded it audits the checkpoint's pickle serialization opcode by
opcode and fails closed on any global outside a known-safe tensor
reconstruction set. It then runs the documented phone-recognition task on a
small label-blind development subset and measures output shape, repeatability,
runtime and peak memory.

POWSM outputs are candidate phone evidence from a CC BY 4.0 model trained on
IPAPack++ with G2P-derived labels. They are never truth, and agreement with
other IPAPack++-family models is never independent confirmation.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import pickletools
import platform
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
MANIFEST_PATH = (
    PRIVATE_ROOT
    / "benchmark"
    / "repair-v1"
    / "expected-only-manifest-v1.0.0.json"
)
MANIFEST_SHA256 = (
    "c918feffa7c0a3a3fa99ce7a9e028621e8fb002980777297f30088e5975331da"
)
OUTPUT_PATH = PRIVATE_ROOT / "feasibility" / "powsm-21ffa41-probe.json"
CLIP_COUNT = 4
REPEATS = 2
SAMPLE_RATE = 16000
WINDOW_SECONDS = 20

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
                elif opcode.name in {"REDUCE", "BUILD", "INST", "OBJ"}:
                    continue
    unexpected = sorted(observed - SAFE_PICKLE_GLOBALS)
    if unexpected:
        raise SystemExit(
            "checkpoint pickle requests unexpected globals, refusing to "
            f"load: {unexpected}"
        )
    return sorted(observed)


def main():
    if os.environ.get("SPEECH_SOUND_OFFLINE") != "1":
        raise SystemExit("probe requires SPEECH_SOUND_OFFLINE=1")
    os.environ["HF_HUB_OFFLINE"] = "1"

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

    model_files = {
        "config.yaml": file_sha256(CONFIG_PATH),
        "weights.pth": file_sha256(WEIGHTS_PATH),
        "bpe.model": file_sha256(BPE_PATH),
    }
    audited_globals = audit_torch_pickle(WEIGHTS_PATH)

    import numpy as np
    import soundfile
    import torch

    torch.set_num_threads(1)
    torch.manual_seed(0)

    from espnet2.bin.s2t_inference import Speech2Text

    # The pinned config.yaml references its statistics and BPE files with
    # paths relative to the snapshot root, so inference must run from there.
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
    clip_records = []
    total_audio = 0.0
    total_seconds = 0.0
    for clip in clips:
        audio_path = REPOSITORY_ROOT / clip["canonical_audio_path"]
        if file_sha256(audio_path) != clip["canonical_audio_sha256"]:
            raise SystemExit(f"audio checksum changed: {clip['safe_id']}")
        waveform, sample_rate = soundfile.read(audio_path, dtype="float32")
        if sample_rate != SAMPLE_RATE or waveform.ndim != 1:
            raise SystemExit("probe requires 16 kHz mono audio")
        if waveform.shape[0] < window_samples:
            padded = np.zeros(window_samples, dtype=np.float32)
            padded[: waveform.shape[0]] = waveform
        else:
            padded = waveform[:window_samples]
        repeats = []
        started = time.perf_counter()
        for _ in range(REPEATS):
            with torch.no_grad():
                results = speech2text(padded, text_prev="<na>")
            text = results[0][0]
            if "<notimestamps>" in text:
                text = text.split("<notimestamps>", 1)[1].strip()
            phones = [
                token
                for token in text.split("/")
                if token and not token.isspace()
            ]
            repeats.append(
                {
                    "raw_sha256": hashlib.sha256(
                        results[0][0].encode("utf-8")
                    ).hexdigest(),
                    "phone_token_count": len(phones),
                    "phones": phones,
                }
            )
        seconds = time.perf_counter() - started
        if repeats[0] != repeats[1]:
            raise SystemExit(f"repeats differ for {clip['safe_id']}")
        clip_records.append(
            {
                "safe_id": clip["safe_id"],
                "input_sha256": clip["canonical_audio_sha256"],
                "duration_s": clip["duration_s"],
                "phone_token_count": repeats[0]["phone_token_count"],
                "raw_output_sha256": repeats[0]["raw_sha256"],
                "same_input_repeats_exact": True,
                "seconds_for_two_repeats": round(seconds, 6),
            }
        )
        total_audio += clip["duration_s"]
        total_seconds += seconds

    report = {
        "probe_id": "powsm_feasibility_probe",
        "schema_version": "1.0.0",
        "role": "core_local_free_phone_comparator",
        "model_id": "espnet/powsm",
        "model_revision": "21ffa410432ace159f3c1fdeed304c70eddf7d34",
        "weights_licence": "cc-by-4.0",
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
        "environment_notes": [
            "espnet imports downloaded nltk tagger data once during "
            "environment setup; no network access occurs during inference "
            "(SPEECH_SOUND_OFFLINE and HF_HUB_OFFLINE enforced)"
        ],
        "lineage_note": (
            "IPAPack++ training with G2P-derived labels; SpeechOcean762 and "
            "L2-ARCTIC are evaluation-only for this model; agreement with "
            "ZIPA is not independent confirmation"
        ),
        "model_files_sha256": model_files,
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "model_load_seconds": round(load_seconds, 6),
        "clip_count": len(clip_records),
        "total_audio_seconds": round(total_audio, 6),
        "total_processing_seconds": round(total_seconds, 6),
        "real_time_factor_two_repeats": round(total_seconds / total_audio, 6),
        "peak_maxrss_bytes": peak_maxrss_bytes(),
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
