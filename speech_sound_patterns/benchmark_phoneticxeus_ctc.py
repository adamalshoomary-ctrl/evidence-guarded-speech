"""Extract label-blind, expected-phone-constrained PhoneticXEUS features."""

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
    PRIVATE_BENCHMARK_ROOT,
    canonical_json_sha256,
    expand_reference_phones,
    load_phone_map,
    target_predictions,
)
from .benchmark_phoneticxeus import _verify_panphon
from .feasibility import (
    REPOSITORY_ROOT,
    canonical_json_bytes,
    classify_panphon_token,
    file_sha256,
)
from .phoneticxeus_probe import (
    MODEL_REVISION,
    MODEL_TREE_SHA256,
    MODEL_WEIGHTS_SHA256,
    _collapsed_ctc,
    _load_waveform,
    verify_model_snapshot,
)


PRIVATE_ROOT = REPOSITORY_ROOT / ".research_data" / "speech_sound_patterns"
EXPECTED_MANIFEST_PATH = (
    PRIVATE_BENCHMARK_ROOT / "repair-v1" / "expected-only-manifest-v1.0.0.json"
)
EXPECTED_MANIFEST_SHA256 = (
    "c918feffa7c0a3a3fa99ce7a9e028621e8fb002980777297f30088e5975331da"
)
REPAIR_CONTRACT_PATH = (
    Path(__file__).with_name("benchmark-repair-contract-v1.0.0.json")
)
DEFAULT_MODEL = PRIVATE_ROOT / "models" / "phoneticxeus" / MODEL_REVISION
DEFAULT_OUTPUT = PRIVATE_BENCHMARK_ROOT / "repair-v1" / "evidence" / "ctc-official"


def _private_output(path):
    resolved = Path(path).resolve(strict=False)
    resolved.relative_to(PRIVATE_BENCHMARK_ROOT.resolve())
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _load_expected_manifest(path):
    path = Path(path)
    if file_sha256(path) != EXPECTED_MANIFEST_SHA256:
        raise ValueError("expected-only repair manifest checksum changed")
    document = json.loads(path.read_text(encoding="utf-8"))
    if (
        document.get("expert_outcomes_included") is not False
        or document.get("held_out_participants") != 0
        or len(document.get("clips", [])) != 480
    ):
        raise ValueError("expected-only repair manifest violates the frozen scope")
    if any(
        clip.get("project_split") not in {"development", "threshold_tuning"}
        for clip in document["clips"]
    ):
        raise ValueError("repair feature extraction cannot access held-out clips")
    return document


def _load_contract(path):
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if document.get("status") != "rules_frozen_before_repair_feature_scoring":
        raise ValueError("repair rules are not frozen")
    policy = document["feature_extractor"]
    if (
        policy.get("same_input_repeats") != 2
        or policy.get("backend") != "mps"
        or policy.get("network_access") is not False
        or policy.get("silent_cpu_fallback") is not False
    ):
        raise ValueError("repair feature extractor policy changed")
    if document["input_policy"]["expected_only_manifest_sha256"] != (
        EXPECTED_MANIFEST_SHA256
    ):
        raise ValueError("repair contract does not pin the expected-only input")
    return document


def _ctc_spans(path_ids, target_ids, blank_id=0):
    """Return ordered nonblank spans from one forced CTC path."""
    spans = []
    index = 0
    while index < len(path_ids):
        token_id = path_ids[index]
        if token_id == blank_id:
            index += 1
            continue
        end = index + 1
        while end < len(path_ids) and path_ids[end] == token_id:
            end += 1
        spans.append({"token_id": token_id, "start": index, "end": end})
        index = end
    if [item["token_id"] for item in spans] != list(target_ids):
        raise ValueError("forced CTC path does not preserve the expected sequence")
    return spans


def deterministic_ctc_viterbi(log_probs, target_ids, blank_id=0):
    """Align a known token sequence with a deterministic CTC Viterbi path."""
    if (
        not isinstance(log_probs, list)
        or not log_probs
        or not all(isinstance(row, list) and row for row in log_probs)
    ):
        raise ValueError("CTC log probabilities must have frames by phones shape")
    frame_count = len(log_probs)
    class_count = len(log_probs[0])
    if any(len(row) != class_count for row in log_probs):
        raise ValueError("CTC log probability rows have inconsistent shapes")
    if not target_ids:
        raise ValueError("CTC target sequence cannot be empty")
    if any(
        not isinstance(item, int) or item <= 0 or item >= class_count
        for item in target_ids
    ):
        raise ValueError("CTC target sequence contains an invalid token")
    required_frames = len(target_ids) + sum(
        left == right for left, right in zip(target_ids, target_ids[1:])
    )
    if frame_count < required_frames:
        raise ValueError("CTC input has too few frames for the expected sequence")

    extended = [blank_id]
    for token_id in target_ids:
        extended.extend((token_id, blank_id))
    state_count = len(extended)
    previous = [float("-inf")] * state_count
    previous[0] = log_probs[0][blank_id]
    previous[1] = log_probs[0][target_ids[0]]
    backpointers = [[-1] * state_count]

    for frame_index in range(1, frame_count):
        current = [float("-inf")] * state_count
        backpointer = [-1] * state_count
        for state_index, token_id in enumerate(extended):
            candidates = [(previous[state_index], state_index)]
            if state_index >= 1:
                candidates.append((previous[state_index - 1], state_index - 1))
            if (
                state_index >= 2
                and token_id != blank_id
                and token_id != extended[state_index - 2]
            ):
                candidates.append((previous[state_index - 2], state_index - 2))
            best_score, best_state = max(
                candidates,
                key=lambda item: (item[0], -item[1]),
            )
            if math.isfinite(best_score):
                current[state_index] = (
                    best_score + log_probs[frame_index][token_id]
                )
                backpointer[state_index] = best_state
        previous = current
        backpointers.append(backpointer)

    final_candidates = [
        (previous[state_count - 2], state_count - 2),
        (previous[state_count - 1], state_count - 1),
    ]
    final_score, state_index = max(
        final_candidates, key=lambda item: (item[0], -item[1])
    )
    if not math.isfinite(final_score):
        raise ValueError("CTC Viterbi alignment has no finite complete path")
    state_path = [state_index]
    for frame_index in range(frame_count - 1, 0, -1):
        state_index = backpointers[frame_index][state_index]
        if state_index < 0:
            raise ValueError("CTC Viterbi backtrace is incomplete")
        state_path.append(state_index)
    state_path.reverse()
    path_ids = [extended[item] for item in state_path]
    _ctc_spans(path_ids, target_ids, blank_id)
    return path_ids, _round_log(final_score)


def _feature_difference_rate(left, right):
    if not isinstance(left, dict) or not isinstance(right, dict):
        return None
    names = sorted(set(left) | set(right))
    if not names or set(left) != set(right):
        return None
    return round(sum(left[name] != right[name] for name in names) / len(names), 7)


def _round_log(value):
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("repair feature contains a nonfinite log posterior")
    return round(value, 7)


def extract_target_features(
    logits,
    reference_phones,
    word_starts,
    targets,
    vocab,
    id_to_token,
    phone_map,
    feature_table,
    expected_variants,
    duration_s,
    classification_cache=None,
):
    """Extract deterministic target evidence from one full logit tensor."""
    import torch
    if logits.ndim != 3 or logits.shape[0] != 1:
        raise ValueError("PhoneticXEUS logits must have shape one by frames by phones")
    expected_items = expand_reference_phones(reference_phones, phone_map)
    expected_tokens = [item["token"] for item in expected_items]
    missing = sorted(set(expected_tokens) - set(vocab))
    if missing:
        raise ValueError("expected IPA tokens are absent from the pinned vocabulary")
    target_ids = [vocab[token] for token in expected_tokens]
    log_probs = logits.to("cpu", dtype=torch.float32).log_softmax(dim=-1)
    path_ids, _ = deterministic_ctc_viterbi(
        log_probs[0].tolist(), target_ids, blank_id=0
    )
    spans = _ctc_spans(path_ids, target_ids)
    if len(spans) != len(expected_items):
        raise ValueError("forced CTC target span count changed")

    classifications = classification_cache or {}
    consonant_ids = []
    for raw_token, token_id in vocab.items():
        if token_id not in classifications:
            classifications[token_id] = classify_panphon_token(
                raw_token, feature_table
            )
        classification = classifications[token_id]
        if (
            classification["decision"] == "identity_nfd"
            and classification["features"].get("syl") == -1
        ):
            consonant_ids.append(token_id)
    if not consonant_ids:
        raise ValueError("pinned vocabulary has no classifiable consonants")

    greedy_ids = logits.argmax(dim=-1)[0].tolist()
    _, greedy_tokens = _collapsed_ctc(greedy_ids, id_to_token)
    greedy = target_predictions(
        reference_phones, greedy_tokens, phone_map, set(word_starts)
    )
    greedy_by_target = {
        item["target_index"]: item for item in greedy["targets"]
    }

    expected_by_origin = {}
    for item, span in zip(expected_items, spans):
        expected_by_origin.setdefault(item["origin_index"], []).append((item, span))

    frame_count = int(log_probs.shape[1])
    result = []
    for target in targets:
        if target["scorable"] is not True:
            continue
        origin_index = target["global_index"]
        parts = expected_by_origin.get(origin_index, [])
        if not parts:
            raise ValueError("scorable target has no forced CTC span")
        start = max(0, min(span["start"] for _, span in parts) - 1)
        end = min(frame_count, max(span["end"] for _, span in parts) + 1)
        if start >= end:
            raise ValueError("forced CTC target window is empty")

        forced_values = []
        for item, span in parts:
            token_id = vocab[item["token"]]
            forced_values.extend(
                log_probs[0, span["start"] : span["end"], token_id].tolist()
            )
        arpabet = target["arpabet"]
        variant_tokens = expected_variants.get(arpabet, target["ipa_parts"])
        variant_ids = [vocab[token] for token in variant_tokens if token in vocab]
        if not variant_ids:
            raise ValueError(f"no expected model token exists for {arpabet}")
        window = log_probs[0, start:end]
        expected_values = window[:, variant_ids]
        expected_peak = float(expected_values.max().item())
        competing_ids = [
            token_id for token_id in consonant_ids if token_id not in variant_ids
        ]
        competitor_values = window[:, competing_ids]
        flat_competitor_index = int(competitor_values.argmax().item())
        competitor_frame_index = flat_competitor_index // len(competing_ids)
        competitor_column = flat_competitor_index % len(competing_ids)
        competitor_id = competing_ids[competitor_column]
        competitor_peak = float(
            competitor_values[competitor_frame_index, competitor_column].item()
        )
        top_ids = window.argmax(dim=-1).tolist()
        top_one_rate = sum(item in variant_ids for item in top_ids) / len(top_ids)
        expected_base = target["ipa_parts"][0]
        expected_classification = classifications[vocab[expected_base]]
        competitor_classification = classifications[competitor_id]
        greedy_target = greedy_by_target[origin_index]
        observed_token = greedy_target.get("observed_phone")
        if observed_token is None:
            greedy_difference = None
        else:
            observed_id = vocab.get(observed_token)
            observed_classification = classifications.get(observed_id, {})
            greedy_difference = _feature_difference_rate(
                expected_classification.get("features"),
                observed_classification.get("features"),
            )
        result.append(
            {
                "global_index": origin_index,
                "word_index": target["word_index"],
                "local_index": target["local_index"],
                "arpabet": arpabet,
                "forced_span_start_frame": min(
                    span["start"] for _, span in parts
                ),
                "forced_span_end_frame": max(span["end"] for _, span in parts),
                "evidence_window_start_frame": start,
                "evidence_window_end_frame": end,
                "forced_path_expected_log_posterior": _round_log(
                    sum(forced_values) / len(forced_values)
                ),
                "best_expected_variant_log_posterior": _round_log(expected_peak),
                "best_competing_consonant_log_posterior": _round_log(
                    competitor_peak
                ),
                "expected_variant_margin": _round_log(
                    expected_peak - competitor_peak
                ),
                "expected_variant_peak_posterior": round(
                    math.exp(expected_peak), 9
                ),
                "expected_variant_top_one_frame_rate": round(top_one_rate, 7),
                "forced_span_frame_count": sum(
                    span["end"] - span["start"] for _, span in parts
                ),
                "forced_span_duration_seconds": round(
                    (
                        max(span["end"] for _, span in parts)
                        - min(span["start"] for _, span in parts)
                    )
                    * duration_s
                    / frame_count,
                    7,
                ),
                "best_competing_consonant": id_to_token[str(competitor_id)],
                "competing_panphon_feature_difference_rate": (
                    _feature_difference_rate(
                        expected_classification.get("features"),
                        competitor_classification.get("features"),
                    )
                ),
                "greedy_alignment_relation_indicator": int(
                    greedy_target["state"] == "coarse_relation_candidate"
                ),
                "greedy_alignment_relation_type": greedy_target.get(
                    "relation_type"
                ),
                "greedy_observed_phone": observed_token,
                "greedy_observed_panphon_feature_difference_rate": (
                    greedy_difference
                ),
            }
        )
    return result


def run_extraction(
    expected_manifest_path=EXPECTED_MANIFEST_PATH,
    repair_contract_path=REPAIR_CONTRACT_PATH,
    model_root=DEFAULT_MODEL,
    output_root=DEFAULT_OUTPUT,
    backend="mps",
    repeats=2,
    max_new_clips=None,
):
    if (
        os.environ.get("HF_HUB_OFFLINE") != "1"
        or os.environ.get("TRANSFORMERS_OFFLINE") != "1"
    ):
        raise ValueError("repair inference must run with network access disabled")
    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        raise ValueError("pinned model inference must not write Python bytecode")
    if os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK") not in {None, "0"}:
        raise ValueError("silent MPS to CPU fallback is prohibited")
    if backend != "mps" or repeats != 2:
        raise ValueError("repair contract requires two MPS repeats")
    if max_new_clips is not None and max_new_clips < 1:
        raise ValueError("max new clips must be positive")

    expected_manifest = _load_expected_manifest(expected_manifest_path)
    repair_contract = _load_contract(repair_contract_path)
    model_root = Path(model_root).resolve()
    verify_model_snapshot(model_root)
    _verify_panphon()
    output_root = _private_output(output_root)
    summary_path = output_root / "phoneticxeus-ctc-process.json"
    if summary_path.exists():
        raise ValueError("completed constrained CTC evidence already exists")
    clips_root = output_root / "clips"
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

    if not torch.backends.mps.is_available():
        raise ValueError("repair contract requires an available MPS backend")
    torch.manual_seed(0)
    np.random.seed(0)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    device = torch.device("mps")
    feature_table = FeatureTable()
    phone_map = load_phone_map()
    expected_variants = repair_contract["feature_extractor"][
        "expected_phone_variants"
    ]
    vocab = json.loads((model_root / "ipa_vocab.json").read_text(encoding="utf-8"))
    if len(vocab) != 428 or vocab.get("<blank>") != 0:
        raise ValueError("PhoneticXEUS vocabulary identity changed")
    id_to_token = {str(value): key for key, value in vocab.items()}
    classification_cache = {
        token_id: classify_panphon_token(raw_token, feature_table)
        for raw_token, token_id in vocab.items()
    }
    load_started = time.perf_counter()
    model = AutoModel.from_pretrained(
        str(model_root),
        trust_remote_code=True,
        local_files_only=True,
        use_safetensors=True,
    ).eval()
    model = model.to(device)
    torch.mps.synchronize()
    load_seconds = time.perf_counter() - load_started

    clip_index = []
    total_audio_seconds = 0.0
    total_inference_seconds = 0.0
    new_clip_count = 0
    for position, clip in enumerate(expected_manifest["clips"], start=1):
        output_path = clips_root / f"{clip['safe_id']}.json"
        if output_path.exists():
            record = json.loads(output_path.read_text(encoding="utf-8"))
            if (
                record.get("safe_id") != clip["safe_id"]
                or record.get("input_sha256") != clip["canonical_audio_sha256"]
                or record.get("model_revision") != MODEL_REVISION
                or record.get("same_input_target_features_exact") is not True
            ):
                raise ValueError(
                    f"existing constrained evidence is invalid for {clip['safe_id']}"
                )
            clip_index.append(
                {
                    "safe_id": clip["safe_id"],
                    "project_split": clip["project_split"],
                    "source_stratum": clip["source_stratum"],
                    "output_path": output_path.relative_to(REPOSITORY_ROOT).as_posix(),
                    "output_sha256": file_sha256(output_path),
                    "target_count": len(record["target_features"]),
                    "repeatability_passed": True,
                }
            )
            total_audio_seconds += clip["duration_s"]
            total_inference_seconds += sum(
                item["runtime_s"] for item in record["repeats"]
            )
            continue

        waveform, peak = _load_waveform(
            REPOSITORY_ROOT / clip["canonical_audio_path"],
            clip["canonical_audio_sha256"],
        )
        waveform = waveform.to(device)
        first_features = None
        repeat_records = []
        for repeat_index in range(repeats):
            started = time.perf_counter()
            with torch.inference_mode():
                logits = model(input_values=waveform).logits
            torch.mps.synchronize()
            elapsed = time.perf_counter() - started
            if not bool(torch.isfinite(logits).all().item()):
                raise ValueError(f"nonfinite model output for {clip['safe_id']}")
            cpu_logits = logits.detach().to("cpu", dtype=torch.float32).contiguous()
            features = extract_target_features(
                cpu_logits,
                clip["reference_phones"],
                clip["word_starts"],
                clip["targets"],
                vocab,
                id_to_token,
                phone_map,
                feature_table,
                expected_variants,
                clip["duration_s"],
                classification_cache,
            )
            feature_hash = canonical_json_sha256(features)
            if first_features is None:
                first_features = features
                exact = True
            else:
                exact = features == first_features
            repeat_records.append(
                {
                    "repeat_index": repeat_index,
                    "runtime_s": round(elapsed, 6),
                    "target_features_sha256": feature_hash,
                    "target_features_exact_match_first": exact,
                }
            )
            total_inference_seconds += elapsed
            del logits, cpu_logits, features
        if not all(
            item["target_features_exact_match_first"] for item in repeat_records
        ):
            raise ValueError(
                f"constrained features did not repeat for {clip['safe_id']}"
            )
        record = {
            "schema_version": "1.0.0",
            "probe_id": "phoneticxeus_expected_phone_ctc_features_v1",
            "safe_id": clip["safe_id"],
            "project_split": clip["project_split"],
            "source_stratum": clip["source_stratum"],
            "input_sha256": clip["canonical_audio_sha256"],
            "duration_s": clip["duration_s"],
            "peak_absolute_amplitude": round(peak, 8),
            "backend": backend,
            "model_revision": MODEL_REVISION,
            "expected_only_manifest_sha256": EXPECTED_MANIFEST_SHA256,
            "repair_contract_sha256": file_sha256(repair_contract_path),
            "target_features": first_features,
            "same_input_target_features_exact": True,
            "repeats": repeat_records,
            "claim_boundaries": {
                "candidate_runner_read_expert_outcomes": False,
                "forced_alignment_verifies_production": False,
                "features_are_calibrated_confidence": False,
                "held_out_evaluation": False,
                "scientific_or_product_release": False,
            },
        }
        output_path.write_bytes(canonical_json_bytes(record))
        clip_index.append(
            {
                "safe_id": clip["safe_id"],
                "project_split": clip["project_split"],
                "source_stratum": clip["source_stratum"],
                "output_path": output_path.relative_to(REPOSITORY_ROOT).as_posix(),
                "output_sha256": file_sha256(output_path),
                "target_count": len(first_features),
                "repeatability_passed": True,
            }
        )
        total_audio_seconds += clip["duration_s"]
        new_clip_count += 1
        del waveform, first_features
        torch.mps.empty_cache()
        gc.collect()
        if position % 25 == 0:
            print(
                f"Constrained CTC progress: {position}/{len(expected_manifest['clips'])}",
                flush=True,
            )
        if max_new_clips is not None and new_clip_count >= max_new_clips:
            print(
                f"Constrained CTC chunk: {len(clip_index)}/"
                f"{len(expected_manifest['clips'])}",
                flush=True,
            )
            return None, {"complete": False, "clips": clip_index}

    summary = {
        "schema_version": "1.0.0",
        "probe_id": "phoneticxeus_expected_phone_ctc_features_v1",
        "expected_only_manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "repair_contract_sha256": file_sha256(repair_contract_path),
        "model_revision": MODEL_REVISION,
        "model_tree_sha256": MODEL_TREE_SHA256,
        "model_weights_sha256": MODEL_WEIGHTS_SHA256,
        "backend": backend,
        "load_seconds": round(load_seconds, 6),
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
        "execution": {
            "clip_count": len(clip_index),
            "same_input_repeats": repeats,
            "total_audio_seconds": round(total_audio_seconds, 6),
            "total_inference_seconds": round(total_inference_seconds, 6),
            "network_access": False,
            "torch_seed": 0,
            "numpy_seed": 0,
            "torch_num_threads": 1,
            "deterministic_algorithms": True,
            "silent_mps_cpu_fallback": False,
            "expert_outcomes_read_by_candidate_runner": False,
            "held_out_participants": 0,
        },
        "clips": clip_index,
        "claim_boundaries": {
            "forced_alignment_verifies_production": False,
            "features_are_calibrated_confidence": False,
            "candidate_artifact": False,
            "scientific_or_product_release": False,
        },
    }
    summary_path.write_bytes(canonical_json_bytes(summary))
    return summary_path, summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--expected-manifest", type=Path, default=EXPECTED_MANIFEST_PATH
    )
    parser.add_argument(
        "--repair-contract", type=Path, default=REPAIR_CONTRACT_PATH
    )
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--backend", choices=("mps",), default="mps")
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--max-new-clips", type=int)
    args = parser.parse_args()
    path, summary = run_extraction(
        args.expected_manifest,
        args.repair_contract,
        args.model,
        args.output,
        args.backend,
        args.repeats,
        args.max_new_clips,
    )
    if summary.get("complete") is False:
        print(f"Constrained CTC safely paused: {len(summary['clips'])} clips")
    else:
        print(f"Constrained CTC complete: {len(summary['clips'])} clips")
        print(f"Private process record: {path.relative_to(REPOSITORY_ROOT)}")


if __name__ == "__main__":
    main()
