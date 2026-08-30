"""Run the segmentation-free GOP lane over every frozen comparison clip.

Checkpoint 22E2 established that this independent implementation runs, repeats
exactly and is legally usable. Checkpoint 22E4 asks the different question the
gates need: what does it score on all 480 frozen clips, adults and children,
development and tuning?

The runner is label blind by construction. It reads only the expected-only
manifest, which carries no expert outcome, and it writes only scores. The expert
relations are joined in a separate scoring step that runs after every candidate
output is complete.

Run inside the pinned Meta ONNX environment, offline:

    env SPEECH_SOUND_OFFLINE=1 PYTHONPATH="$REPO_ROOT" \\
      "$META_ENV/bin/python" -m speech_sound_patterns.comparison_sfgop
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import time
from pathlib import Path

from .benchmark_meta_ctc import (
    DEFAULT_MODEL_ROOT,
    _load_waveform,
    _meta_phone_map,
    _verify_model,
    load_meta_contract,
)
from .comparison import (
    ACTIVE_COMPARISON_VERSION,
    ComparisonError,
    comparison_profile,
    load_expected_manifest,
)
from .feasibility import REPOSITORY_ROOT, canonical_json_bytes, file_sha256
from .sfgop import (

try:
    import resource
except ModuleNotFoundError:  # Windows has no resource module
    resource = None
    META_CONTRACT_PATH,
    SFGOP_CONTRACT_SHA256,
    _candidate_ids,
    _log_softmax,
    load_sfgop_contract,
    score_clip_targets,
)


LANE_ID = "segmentation_free_gop"
SAME_INPUT_REPEATS = 2


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


def default_output(version=ACTIVE_COMPARISON_VERSION):
    return comparison_profile(version)["private_root"] / "evidence" / "sfgop"


def _clip_records(output_root):
    clips_root = output_root / "clips"
    if not clips_root.is_dir():
        return {}
    records = {}
    for path in sorted(clips_root.glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        records[record["safe_id"]] = (path, record)
    return records


def _verify_existing(records, expected):
    """Re-verify every finished clip before adding another one.

    A resumable run is only trustworthy if the earlier parts are still exactly
    what they were, so each existing record is checked against the manifest and
    against its own declared boundaries on every invocation.
    """
    for safe_id, (path, record) in records.items():
        clip = expected.get(safe_id)
        if clip is None:
            raise ComparisonError(f"{safe_id} is not in the frozen manifest")
        if record["input_sha256"] != clip["canonical_audio_sha256"]:
            raise ComparisonError(f"{safe_id} audio identity changed")
        if record.get("same_input_repeats_exact") is not True:
            raise ComparisonError(f"{safe_id} did not repeat exactly")
        if record.get("contract_sha256") != SFGOP_CONTRACT_SHA256:
            raise ComparisonError(f"{safe_id} used another method contract")
        if record.get("expert_outcomes_read") is not False:
            raise ComparisonError(f"{safe_id} claims an expert outcome was read")
        if canonical_json_bytes(record) != path.read_bytes():
            raise ComparisonError(f"{safe_id} record is not canonical")


def run_comparison(
    expected_manifest_path=None,
    model_root=DEFAULT_MODEL_ROOT,
    output_root=None,
    max_new_clips=None,
    version=ACTIVE_COMPARISON_VERSION,
):
    profile = comparison_profile(version)
    if expected_manifest_path is None:
        expected_manifest_path = profile["expected_manifest_path"]
    if output_root is None:
        output_root = default_output(version)
    if os.environ.get("SPEECH_SOUND_OFFLINE") != "1":
        raise ComparisonError(
            "the segmentation-free GOP lane requires SPEECH_SOUND_OFFLINE=1"
        )
    contract = load_sfgop_contract()
    meta_contract = load_meta_contract(META_CONTRACT_PATH)
    if file_sha256(META_CONTRACT_PATH) != contract["model"][
        "reference_contract_sha256"
    ]:
        raise ComparisonError("the Meta model reference contract changed")
    files = _verify_model(model_root, meta_contract)
    manifest = load_expected_manifest(expected_manifest_path, version=version)
    expected = {clip["safe_id"]: clip for clip in manifest["clips"]}

    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    summary_path = output_root / "sfgop-comparison-process.json"
    if summary_path.exists():
        raise ComparisonError("completed segmentation-free GOP evidence already exists")
    existing = _clip_records(output_root)
    _verify_existing(existing, expected)
    remaining = [
        clip for clip in manifest["clips"] if clip["safe_id"] not in existing
    ]
    if max_new_clips is not None:
        remaining = remaining[:max_new_clips]

    import onnxruntime

    vocab = json.loads(files["vocab_sha256"].read_text(encoding="utf-8"))
    id_to_token = {value: key for key, value in vocab.items()}
    candidate_ids = _candidate_ids(vocab)
    phone_map = _meta_phone_map(meta_contract, vocab)

    session_options = onnxruntime.SessionOptions()
    session_options.execution_mode = onnxruntime.ExecutionMode.ORT_SEQUENTIAL
    session_options.intra_op_num_threads = 1
    session_options.inter_op_num_threads = 1
    session_options.graph_optimization_level = (
        onnxruntime.GraphOptimizationLevel.ORT_ENABLE_EXTENDED
    )
    session = onnxruntime.InferenceSession(
        str(files["weights_sha256"]),
        sess_options=session_options,
        providers=["CPUExecutionProvider"],
    )

    clips_root = output_root / "clips"
    clips_root.mkdir(parents=True, exist_ok=True)
    processed = 0
    for clip in remaining:
        waveform, _ = _load_waveform(
            REPOSITORY_ROOT / clip["canonical_audio_path"],
            clip["canonical_audio_sha256"],
        )
        repeats = []
        started = time.perf_counter()
        for _ in range(SAME_INPUT_REPEATS):
            logits = session.run(None, {"input_values": waveform})[0][0]
            repeats.append(
                score_clip_targets(
                    _log_softmax(logits),
                    clip,
                    vocab,
                    candidate_ids,
                    id_to_token,
                    phone_map,
                )
            )
        seconds = time.perf_counter() - started
        if canonical_json_bytes(repeats[0]) != canonical_json_bytes(repeats[1]):
            raise ComparisonError(f"repeat outputs differ for {clip['safe_id']}")
        record = {
            "safe_id": clip["safe_id"],
            "lane_id": LANE_ID,
            "input_sha256": clip["canonical_audio_sha256"],
            "project_split": clip["project_split"],
            "source_stratum": clip["source_stratum"],
            "duration_s": clip["duration_s"],
            "model_revision": meta_contract["model"]["revision"],
            "contract_sha256": SFGOP_CONTRACT_SHA256,
            "same_input_repeats": SAME_INPUT_REPEATS,
            "same_input_repeats_exact": True,
            "expert_outcomes_read": False,
            "seconds_for_all_repeats": round(seconds, 6),
            "evidence": repeats[0],
        }
        (clips_root / f"{clip['safe_id']}.json").write_bytes(
            canonical_json_bytes(record)
        )
        processed += 1

    finished = _clip_records(output_root)
    _verify_existing(finished, expected)
    if set(finished) != set(expected):
        return {
            "status": "paused_incomplete",
            "completed_clips": len(finished),
            "expected_clips": len(expected),
            "new_clips_this_invocation": processed,
        }

    total_audio = 0.0
    total_seconds = 0.0
    scored_targets = 0
    unscorable_targets = 0
    clip_summaries = []
    for safe_id in sorted(finished):
        _, record = finished[safe_id]
        scored = sum(
            1 for target in record["evidence"]["targets"] if target["state"] == "scored"
        )
        unscorable = len(record["evidence"]["targets"]) - scored
        scored_targets += scored
        unscorable_targets += unscorable
        total_audio += record["duration_s"]
        total_seconds += record["seconds_for_all_repeats"]
        clip_summaries.append(
            {
                "safe_id": safe_id,
                "scored_targets": scored,
                "unscorable_targets": unscorable,
                "forward_backward_abs_diff": record["evidence"][
                    "forward_backward_abs_diff"
                ],
            }
        )

    worst_consistency = max(
        abs(item["forward_backward_abs_diff"]) for item in clip_summaries
    )
    summary = {
        "summary_id": "sfgop_comparison_process",
        "schema_version": "1.0.0",
        "checkpoint": profile["checkpoint"],
        "lane_id": LANE_ID,
        "contract_sha256": SFGOP_CONTRACT_SHA256,
        "expected_only_manifest_sha256": file_sha256(expected_manifest_path),
        "model_revision": meta_contract["model"]["revision"],
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "execution": {
            "clip_count": len(finished),
            "held_out_participants": 0,
            "expert_outcomes_read_by_candidate_runner": False,
            "same_input_repeats": SAME_INPUT_REPEATS,
            "all_repeats_exact": True,
            "network_access": False,
        },
        "scored_targets": scored_targets,
        "unscorable_targets": unscorable_targets,
        "total_audio_seconds": round(total_audio, 6),
        "total_processing_seconds": round(total_seconds, 6),
        "real_time_factor_all_repeats": round(total_seconds / total_audio, 6),
        "peak_maxrss_bytes": peak_maxrss_bytes(),
        "worst_forward_backward_abs_diff": worst_consistency,
        "clips": clip_summaries,
    }
    summary_path.write_bytes(canonical_json_bytes(summary))
    return {
        "status": "complete",
        "summary_path": summary_path.relative_to(REPOSITORY_ROOT).as_posix(),
        **{key: summary[key] for key in ("scored_targets", "unscorable_targets")},
        "clip_count": len(finished),
        "real_time_factor_all_repeats": summary["real_time_factor_all_repeats"],
    }


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Run the label-blind segmentation-free GOP lane over a frozen "
            "comparison sample. The default is the powered checkpoint 22E4B "
            "sample; pass --comparison-version 1.0.0 for the checkpoint 22E4 "
            "record."
        )
    )
    parser.add_argument("--output-root", type=Path, default=None)
    parser.add_argument("--max-new-clips", type=int, default=None)
    parser.add_argument(
        "--comparison-version", default=ACTIVE_COMPARISON_VERSION
    )
    arguments = parser.parse_args()
    result = run_comparison(
        output_root=arguments.output_root,
        max_new_clips=arguments.max_new_clips,
        version=arguments.comparison_version,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
