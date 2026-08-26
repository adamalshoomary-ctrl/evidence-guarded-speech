"""Extract label-blind constrained CTC features from the frozen Meta ONNX model."""

from __future__ import annotations

import argparse
import copy
import importlib.metadata
import json
import math
import os
import platform
import time
import unicodedata
from pathlib import Path

from .benchmark import (
    PRIVATE_BENCHMARK_ROOT,
    canonical_json_sha256,
    expand_reference_phones,
    load_phone_map,
    target_predictions,
)
from .benchmark_phoneticxeus_ctc import (
    EXPECTED_MANIFEST_PATH,
    EXPECTED_MANIFEST_SHA256,
    _ctc_spans,
    _load_expected_manifest,
    _round_log,
    deterministic_ctc_viterbi,
)
from .feasibility import (
    REPOSITORY_ROOT,
    canonical_json_bytes,
    classify_panphon_token,
    file_sha256,
)


META_CONTRACT_PATH = Path(__file__).with_name(
    "benchmark-repair-meta-contract-v1.0.0.json"
)
META_CONTRACT_SHA256 = (
    "f3f7fcf0b49e7b3ae84fb0578856f4c7bbd59e8305c985cd78905da26f37f446"
)
DEFAULT_MODEL_ROOT = (
    REPOSITORY_ROOT
    / ".research_data"
    / "speech_sound_patterns"
    / "models"
    / "meta-wav2vec2-c69750f"
)
DEFAULT_OUTPUT = (
    PRIVATE_BENCHMARK_ROOT / "repair-v1" / "evidence" / "meta-official"
)


def validate_meta_contract(document):
    errors = []
    if not isinstance(document, dict):
        return ["Meta repair contract must be an object"]
    if document.get("status") != "rules_frozen_before_meta_feature_scoring":
        errors.append("Meta repair status must remain frozen before scoring")
    input_policy = document.get("input_policy", {})
    if input_policy.get("expected_only_clip_count") != 480:
        errors.append("Meta repair expected-only clip count must remain 480")
    if input_policy.get("allowed_project_splits") != [
        "development",
        "threshold_tuning",
    ]:
        errors.append("Meta repair project splits changed")
    if input_policy.get("held_out_access_allowed") is not False:
        errors.append("Meta repair held_out_access_allowed must be false")
    if input_policy.get("candidate_runner_may_read_expert_outcomes") is not False:
        errors.append(
            "Meta repair candidate_runner_may_read_expert_outcomes must be false"
        )
    model = document.get("model", {})
    if model.get("format") != "ONNX":
        errors.append("Meta repair model format must remain ONNX")
    if model.get("executable_or_pickle_weights_allowed") is not False:
        errors.append("Meta repair executable or pickle weights must remain blocked")
    if model.get("network_access_during_inference") is not False:
        errors.append("Meta repair network access must remain false")
    if document.get("prior_repair", {}).get("gates_may_be_lowered") is not False:
        errors.append("Meta repair gates_may_be_lowered must be false")
    calibration = document.get("calibration_policy", {})
    for field in (
        "child_labels_used_for_training_or_thresholds",
        "participant_identity_feature_allowed",
        "source_sex_feature_allowed",
        "word_identity_feature_allowed",
        "reviewer_outcome_feature_allowed",
        "tuning_may_change_features_or_model",
        "coefficients_or_trees_refit_after_tuning",
        "held_out_labels_or_outputs_used",
    ):
        if calibration.get(field) is not False:
            errors.append(f"Meta repair {field} must be false")
    expected_gates = {
        "minimum_precision_point_estimate": 0.75,
        "minimum_precision_wilson_95_lower": 0.5,
        "maximum_false_concerns_per_scorable_opportunity": 0.01,
        "minimum_recall": 0.2,
        "minimum_true_positives": 7,
        "same_input_target_features_exact": True,
        "every_tuning_participant_reported": True,
        "system_selection_if_all_gates_pass": (
            "adult_developer_review_candidate_only"
        ),
        "failure_behavior": "no_system_or_threshold_selected",
    }
    if document.get("selection_gates") != expected_gates:
        errors.append("Meta repair selection gates changed")
    release = document.get("release_boundaries", {})
    if not release or any(value is not False for value in release.values()):
        errors.append("Meta repair release boundaries must all remain false")
    return errors


def load_meta_contract(path=META_CONTRACT_PATH):
    path = Path(path)
    if file_sha256(path) != META_CONTRACT_SHA256:
        raise ValueError("frozen Meta repair contract checksum changed")
    document = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_meta_contract(document)
    if errors:
        raise ValueError("; ".join(errors))
    return document


def _private_output(path):
    resolved = Path(path).resolve(strict=False)
    resolved.relative_to(PRIVATE_BENCHMARK_ROOT.resolve())
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _verify_model(model_root, contract):
    model_root = Path(model_root).resolve()
    files = {
        "weights_sha256": model_root / "onnx" / "model.onnx",
        "config_sha256": model_root / "config.json",
        "preprocessor_config_sha256": model_root / "preprocessor_config.json",
        "vocab_sha256": model_root / "vocab.json",
    }
    for field, path in files.items():
        if not path.is_file():
            raise ValueError(f"frozen Meta model file is missing: {path.name}")
        if file_sha256(path) != contract["model"][field]:
            raise ValueError(f"frozen Meta model checksum changed: {path.name}")
    if files["weights_sha256"].stat().st_size != contract["model"]["weights_bytes"]:
        raise ValueError("frozen Meta model byte count changed")
    return files


def _meta_phone_map(contract, vocab):
    phone_map = copy.deepcopy(load_phone_map())
    phone_map["candidate_inventory"] = (
        "Frozen Meta wav2vec2 multilingual eSpeak phoneme vocabulary"
    )
    for arpabet, tokens in contract["phone_mapping"][
        "model_specific_replacements"
    ].items():
        phone_map["reference_phones"][arpabet]["ipa"] = tokens
    phone_map["declared_equivalents"] = {
        token: {"base": tokens[0], "reason": "frozen English allophone"}
        for tokens in contract["phone_mapping"][
            "expected_consonant_variants"
        ].values()
        for token in tokens[1:]
    }
    phone_map["special_nonphones"] = sorted(
        set(phone_map["special_nonphones"])
        | {"<s>", "<pad>", "</s>", "<unk>"}
    )
    expected_tokens = {
        unicodedata.normalize("NFD", token)
        for mapping in phone_map["reference_phones"].values()
        for token in mapping["ipa"]
    }
    missing = sorted(expected_tokens - set(vocab))
    if missing:
        raise ValueError(f"frozen Meta vocabulary misses expected tokens: {missing}")
    return phone_map


def _log_softmax(values):
    import numpy as np

    values = np.asarray(values, dtype=np.float64)
    maximum = values.max(axis=-1, keepdims=True)
    shifted = values - maximum
    return shifted - np.log(np.exp(shifted).sum(axis=-1, keepdims=True))


def _collapsed_tokens(ids, id_to_token, blank_id=0):
    result = []
    previous = None
    for token_id in ids:
        token_id = int(token_id)
        if token_id != previous and token_id != blank_id:
            result.append(id_to_token[token_id])
        previous = token_id
    return result


def _word_context(expected_manifest):
    result = {}
    for clip in expected_manifest["clips"]:
        grouped = {}
        for target in clip["targets"]:
            grouped.setdefault(target["word_index"], []).append(target)
        for word_index, targets in grouped.items():
            targets = sorted(targets, key=lambda item: item["local_index"])
            for position, target in enumerate(targets):
                if len(targets) == 1:
                    word_position = "single"
                elif position == 0:
                    word_position = "initial"
                elif position == len(targets) - 1:
                    word_position = "final"
                else:
                    word_position = "medial"
                result[
                    (clip["safe_id"], word_index, target["local_index"])
                ] = {
                    "word_position": word_position,
                    "previous_expected_arpabet": (
                        "<boundary>"
                        if position == 0
                        else targets[position - 1]["arpabet"]
                    ),
                    "next_expected_arpabet": (
                        "<boundary>"
                        if position == len(targets) - 1
                        else targets[position + 1]["arpabet"]
                    ),
                }
    return result


def extract_meta_target_features(
    logits,
    clip,
    vocab,
    id_to_token,
    phone_map,
    consonant_ids,
    expected_variants,
    context,
):
    import numpy as np

    logits = np.asarray(logits)
    if logits.ndim != 3 or logits.shape[0] != 1:
        raise ValueError("Meta logits must have shape one by frames by phones")
    if logits.shape[2] != len(vocab):
        raise ValueError("Meta logit vocabulary dimension changed")
    expected_items = expand_reference_phones(
        clip["reference_phones"], phone_map
    )
    expected_tokens = [item["token"] for item in expected_items]
    target_ids = [vocab[token] for token in expected_tokens]
    log_probs = _log_softmax(logits[0])
    path_ids, _ = deterministic_ctc_viterbi(
        log_probs.tolist(), target_ids, blank_id=0
    )
    spans = _ctc_spans(path_ids, target_ids)
    if len(spans) != len(expected_items):
        raise ValueError("Meta forced CTC target span count changed")

    greedy_ids = logits[0].argmax(axis=-1).tolist()
    greedy_tokens = _collapsed_tokens(greedy_ids, id_to_token)
    greedy = target_predictions(
        clip["reference_phones"],
        greedy_tokens,
        phone_map,
        set(clip["word_starts"]),
    )
    greedy_by_target = {
        item["target_index"]: item for item in greedy["targets"]
    }
    expected_by_origin = {}
    for item, span in zip(expected_items, spans):
        expected_by_origin.setdefault(item["origin_index"], []).append(
            (item, span)
        )

    frame_count = int(log_probs.shape[0])
    result = []
    for target in clip["targets"]:
        if target["scorable"] is not True:
            continue
        origin_index = target["global_index"]
        parts = expected_by_origin.get(origin_index, [])
        if not parts:
            raise ValueError("scorable Meta target has no forced CTC span")
        start = max(0, min(span["start"] for _, span in parts) - 1)
        end = min(frame_count, max(span["end"] for _, span in parts) + 1)
        if start >= end:
            raise ValueError("Meta forced target evidence window is empty")

        forced_values = []
        for item, span in parts:
            token_id = vocab[item["token"]]
            forced_values.extend(
                log_probs[span["start"] : span["end"], token_id].tolist()
            )
        arpabet = target["arpabet"]
        mapped_tokens = phone_map["reference_phones"][arpabet]["ipa"]
        variant_tokens = expected_variants.get(arpabet, mapped_tokens)
        variant_ids = [vocab[token] for token in variant_tokens]
        window = log_probs[start:end]
        expected_values = window[:, variant_ids]
        expected_peak = float(expected_values.max())
        competing_ids = [
            token_id for token_id in consonant_ids if token_id not in variant_ids
        ]
        competitor_values = window[:, competing_ids]
        flat_index = int(competitor_values.argmax())
        competitor_column = flat_index % len(competing_ids)
        competitor_id = competing_ids[competitor_column]
        competitor_peak = float(competitor_values.reshape(-1)[flat_index])
        top_ids = window.argmax(axis=-1).tolist()
        top_one_rate = sum(item in variant_ids for item in top_ids) / len(top_ids)
        greedy_target = greedy_by_target[origin_index]
        target_context = context[
            (clip["safe_id"], target["word_index"], target["local_index"])
        ]
        result.append(
            {
                "global_index": origin_index,
                "word_index": target["word_index"],
                "local_index": target["local_index"],
                "arpabet": arpabet,
                "word_position": target_context["word_position"],
                "previous_expected_arpabet": target_context[
                    "previous_expected_arpabet"
                ],
                "next_expected_arpabet": target_context[
                    "next_expected_arpabet"
                ],
                "forced_span_start_frame": min(
                    span["start"] for _, span in parts
                ),
                "forced_span_end_frame": max(span["end"] for _, span in parts),
                "evidence_window_start_frame": start,
                "evidence_window_end_frame": end,
                "forced_path_expected_log_posterior": _round_log(
                    sum(forced_values) / len(forced_values)
                ),
                "best_expected_variant_log_posterior": _round_log(
                    expected_peak
                ),
                "best_competing_consonant_log_posterior": _round_log(
                    competitor_peak
                ),
                "expected_variant_margin": _round_log(
                    expected_peak - competitor_peak
                ),
                "expected_variant_peak_posterior": round(
                    math.exp(expected_peak), 9
                ),
                "expected_variant_top_one_frame_rate": round(
                    top_one_rate, 7
                ),
                "forced_span_frame_count": sum(
                    span["end"] - span["start"] for _, span in parts
                ),
                "forced_span_duration_seconds": round(
                    (
                        max(span["end"] for _, span in parts)
                        - min(span["start"] for _, span in parts)
                    )
                    * clip["duration_s"]
                    / frame_count,
                    7,
                ),
                "best_competing_consonant": id_to_token[competitor_id],
                "expected_competing_pair": (
                    f"{arpabet}|{id_to_token[competitor_id]}"
                ),
                "greedy_alignment_relation_indicator": int(
                    greedy_target["state"] == "coarse_relation_candidate"
                ),
                "greedy_alignment_relation_type": (
                    greedy_target.get("relation_type") or "unavailable"
                ),
                "greedy_observed_phone": greedy_target.get("observed_phone"),
            }
        )
    return result


def _load_waveform(path, expected_sha256):
    import numpy as np
    import soundfile

    path = Path(path)
    if file_sha256(path) != expected_sha256:
        raise ValueError(f"canonical audio checksum changed: {path.name}")
    waveform, sample_rate = soundfile.read(
        path, dtype="float32", always_2d=False
    )
    if sample_rate != 16000:
        raise ValueError("frozen Meta repair requires 16 kHz canonical audio")
    if waveform.ndim != 1 or waveform.size == 0:
        raise ValueError("frozen Meta repair requires nonempty mono audio")
    if not np.isfinite(waveform).all():
        raise ValueError("canonical audio contains nonfinite samples")
    peak = float(np.abs(waveform).max())
    normalized = (waveform - waveform.mean()) / math.sqrt(
        float(waveform.var()) + 1e-7
    )
    return normalized.astype(np.float32)[None, :], peak


def run_extraction(
    expected_manifest_path=EXPECTED_MANIFEST_PATH,
    meta_contract_path=META_CONTRACT_PATH,
    model_root=DEFAULT_MODEL_ROOT,
    output_root=DEFAULT_OUTPUT,
    repeats=2,
    max_new_clips=None,
    shard_count=1,
    shard_index=0,
):
    if os.environ.get("SPEECH_SOUND_OFFLINE") != "1":
        raise ValueError("Meta repair inference requires SPEECH_SOUND_OFFLINE=1")
    if repeats != 2:
        raise ValueError("Meta repair contract requires two identical repeats")
    if max_new_clips is not None and max_new_clips < 1:
        raise ValueError("max new clips must be positive")
    if shard_count < 1 or shard_index < 0 or shard_index >= shard_count:
        raise ValueError("Meta repair shard selection is invalid")

    expected_manifest = _load_expected_manifest(expected_manifest_path)
    contract = load_meta_contract(meta_contract_path)
    files = _verify_model(model_root, contract)
    output_root = _private_output(output_root)
    summary_path = output_root / "meta-ctc-process.json"
    if summary_path.exists():
        raise ValueError("completed Meta constrained CTC evidence already exists")
    clips_root = output_root / "clips"
    clips_root.mkdir(parents=True, exist_ok=True)

    import numpy as np
    import onnxruntime
    import panphon
    import soundfile
    from panphon import FeatureTable

    np.random.seed(0)
    vocab = json.loads(
        files["vocab_sha256"].read_text(encoding="utf-8")
    )
    if len(vocab) != 392 or vocab.get("<pad>") != 0:
        raise ValueError("frozen Meta vocabulary identity changed")
    id_to_token = {value: key for key, value in vocab.items()}
    if set(id_to_token) != set(range(len(vocab))):
        raise ValueError("frozen Meta vocabulary ids are not contiguous")
    phone_map = _meta_phone_map(contract, vocab)
    expected_variants = contract["phone_mapping"][
        "expected_consonant_variants"
    ]
    feature_table = FeatureTable()
    consonant_ids = []
    for raw_token, token_id in vocab.items():
        classification = classify_panphon_token(raw_token, feature_table)
        if (
            classification["decision"] == "identity_nfd"
            and classification["features"]["syl"] == -1
        ):
            consonant_ids.append(token_id)
    if not consonant_ids:
        raise ValueError("frozen Meta vocabulary has no atomic consonants")
    context = _word_context(expected_manifest)

    session_options = onnxruntime.SessionOptions()
    session_options.execution_mode = onnxruntime.ExecutionMode.ORT_SEQUENTIAL
    session_options.intra_op_num_threads = 1
    session_options.inter_op_num_threads = 1
    session_options.graph_optimization_level = (
        onnxruntime.GraphOptimizationLevel.ORT_ENABLE_EXTENDED
    )
    load_started = time.perf_counter()
    session = onnxruntime.InferenceSession(
        str(files["weights_sha256"]),
        sess_options=session_options,
        providers=["CPUExecutionProvider"],
    )
    load_seconds = time.perf_counter() - load_started
    inputs = session.get_inputs()
    outputs = session.get_outputs()
    if len(inputs) != 1 or inputs[0].name != "input_values":
        raise ValueError("frozen Meta ONNX input signature changed")
    if len(outputs) != 1 or outputs[0].name != "logits":
        raise ValueError("frozen Meta ONNX output signature changed")

    clip_index = []
    total_audio_seconds = 0.0
    total_inference_seconds = 0.0
    new_clip_count = 0
    for position, clip in enumerate(expected_manifest["clips"], start=1):
        if (position - 1) % shard_count != shard_index:
            continue
        output_path = clips_root / f"{clip['safe_id']}.json"
        if output_path.exists():
            record = json.loads(output_path.read_text(encoding="utf-8"))
            if (
                record.get("safe_id") != clip["safe_id"]
                or record.get("input_sha256") != clip["canonical_audio_sha256"]
                or record.get("model_revision") != contract["model"]["revision"]
                or record.get("same_input_target_features_exact") is not True
            ):
                raise ValueError(
                    f"existing Meta evidence is invalid for {clip['safe_id']}"
                )
            clip_index.append(
                {
                    "safe_id": clip["safe_id"],
                    "project_split": clip["project_split"],
                    "source_stratum": clip["source_stratum"],
                    "output_path": str(output_path.relative_to(REPOSITORY_ROOT)),
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
        first_features = None
        repeat_records = []
        for repeat_index in range(repeats):
            started = time.perf_counter()
            logits = session.run(["logits"], {"input_values": waveform})[0]
            elapsed = time.perf_counter() - started
            if not np.isfinite(logits).all():
                raise ValueError(f"nonfinite Meta output for {clip['safe_id']}")
            features = extract_meta_target_features(
                logits,
                clip,
                vocab,
                id_to_token,
                phone_map,
                consonant_ids,
                expected_variants,
                context,
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
        if not all(
            item["target_features_exact_match_first"]
            for item in repeat_records
        ):
            raise ValueError(
                f"Meta target features did not repeat for {clip['safe_id']}"
            )
        record = {
            "schema_version": "1.0.0",
            "probe_id": "meta_wav2vec2_expected_phone_ctc_features_v1",
            "safe_id": clip["safe_id"],
            "project_split": clip["project_split"],
            "source_stratum": clip["source_stratum"],
            "input_sha256": clip["canonical_audio_sha256"],
            "duration_s": clip["duration_s"],
            "peak_absolute_amplitude": round(peak, 8),
            "backend": "onnxruntime_cpu",
            "model_revision": contract["model"]["revision"],
            "expected_only_manifest_sha256": EXPECTED_MANIFEST_SHA256,
            "meta_contract_sha256": META_CONTRACT_SHA256,
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
                "output_path": str(output_path.relative_to(REPOSITORY_ROOT)),
                "output_sha256": file_sha256(output_path),
                "target_count": len(first_features),
                "repeatability_passed": True,
            }
        )
        total_audio_seconds += clip["duration_s"]
        new_clip_count += 1
        if position % 25 == 0:
            print(
                f"Meta constrained CTC progress: {position}/"
                f"{len(expected_manifest['clips'])}",
                flush=True,
            )
        if max_new_clips is not None and new_clip_count >= max_new_clips:
            print(
                f"Meta constrained CTC chunk: {len(clip_index)}/"
                f"{len(expected_manifest['clips'])}",
                flush=True,
            )
            return None, {"complete": False, "clips": clip_index}

    if shard_count != 1:
        print(
            f"Meta constrained CTC shard {shard_index + 1}/{shard_count} "
            f"complete: {len(clip_index)} clips",
            flush=True,
        )
        return None, {"complete": False, "clips": clip_index}

    summary = {
        "schema_version": "1.0.0",
        "probe_id": "meta_wav2vec2_expected_phone_ctc_features_v1",
        "expected_only_manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "meta_contract_sha256": META_CONTRACT_SHA256,
        "model_repository": contract["model"]["repository"],
        "model_revision": contract["model"]["revision"],
        "model_weights_sha256": contract["model"]["weights_sha256"],
        "backend": "onnxruntime_cpu",
        "load_seconds": round(load_seconds, 6),
        "versions": {
            "python": platform.python_version(),
            "onnxruntime": onnxruntime.__version__,
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
            "numpy_seed": 0,
            "intra_op_threads": 1,
            "inter_op_threads": 1,
            "sequential_execution": True,
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
        "--meta-contract", type=Path, default=META_CONTRACT_PATH
    )
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--max-new-clips", type=int)
    parser.add_argument("--shard-count", type=int, default=1)
    parser.add_argument("--shard-index", type=int, default=0)
    args = parser.parse_args()
    path, summary = run_extraction(
        args.expected_manifest,
        args.meta_contract,
        args.model,
        args.output,
        args.repeats,
        args.max_new_clips,
        args.shard_count,
        args.shard_index,
    )
    if summary.get("complete") is False:
        print(f"Meta constrained CTC safely paused: {len(summary['clips'])} clips")
    else:
        print(f"Meta constrained CTC complete: {len(summary['clips'])} clips")
        print(f"Private process record: {path.relative_to(REPOSITORY_ROOT)}")


if __name__ == "__main__":
    main()
