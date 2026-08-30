"""Segmentation-free GOP evidence from the frozen Meta CTC phone model.

This is an independent implementation of the published segmentation-free
goodness-of-pronunciation equations (arXiv 2507.16838, CC BY 4.0). It does not
copy code from the authors' unlicensed repository and it does not use any
SpeechOcean-trained scoring head. For every scorable expected consonant span
it computes, without forcing phone boundaries:

- the CTC log likelihood of the canonical expected sequence;
- the log likelihood of the sequence with the span replaced by every candidate
  phone (substitution lattice) or removed entirely (deletion);
- the resulting GOP-AF and GOP-AF-SD scores, which are log posteriors of the
  expected phone against those alternatives; and
- the highest-posterior alternative candidate phones.

All outputs are developer research evidence about expected phones. They are
never reference truth, never a score for users and never a selection.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import time
import unicodedata
from pathlib import Path

from .benchmark import expand_reference_phones
from .benchmark_meta_ctc import (
    DEFAULT_MODEL_ROOT,
    _load_waveform,
    _meta_phone_map,
    _verify_model,
    load_meta_contract,
)
from .benchmark_phoneticxeus_ctc import (
    EXPECTED_MANIFEST_PATH,
    EXPECTED_MANIFEST_SHA256,
    _load_expected_manifest,
    _private_output,
    _round_log,
)
from .feasibility import REPOSITORY_ROOT, canonical_json_bytes, file_sha256

try:
    import resource
except ModuleNotFoundError:  # Windows has no resource module
    resource = None


SFGOP_CONTRACT_PATH = Path(__file__).with_name("sfgop-contract-v1.0.0.json")
SFGOP_CONTRACT_SHA256 = "229f811fb16eca666248377b62c1cbcf2d5f8bd8d0d85517f643e3947a87f6d2"
META_CONTRACT_PATH = Path(__file__).with_name(
    "benchmark-repair-meta-contract-v1.0.0.json"
)
DEFAULT_OUTPUT = (
    REPOSITORY_ROOT
    / ".research_data"
    / "speech_sound_patterns"
    / "benchmark"
    / "repair-v1"
    / "evidence"
    / "sfgop-feasibility"
)

NEG_INF = float("-inf")


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


class SfgopError(RuntimeError):
    """Raised when segmentation-free GOP evidence cannot be trusted."""


def load_sfgop_contract(path=SFGOP_CONTRACT_PATH):
    path = Path(path)
    if file_sha256(path) != SFGOP_CONTRACT_SHA256:
        raise SfgopError("segmentation-free GOP contract checksum changed")
    document = json.loads(path.read_text(encoding="utf-8"))
    method = document.get("method", {})
    if (
        document.get("status") != "method_frozen_before_feasibility"
        or method.get("unlicensed_repository_code_allowed") is not False
        or method.get("speechocean_trained_scoring_heads_allowed") is not False
    ):
        raise SfgopError("segmentation-free GOP contract policy changed")
    if document["input_policy"]["expected_only_manifest_sha256"] != (
        EXPECTED_MANIFEST_SHA256
    ):
        raise SfgopError("contract does not pin the expected-only manifest")
    return document


def _log_softmax(logits):
    import numpy as np

    logits = logits.astype(np.float64)
    shifted = logits - logits.max(axis=-1, keepdims=True)
    return shifted - np.log(np.exp(shifted).sum(axis=-1, keepdims=True))


def _logsumexp_pair(left, right):
    import numpy as np

    return np.logaddexp(left, right)


def _extended_states(target_ids, blank_id=0):
    extended = [blank_id]
    for token_id in target_ids:
        extended.extend((token_id, blank_id))
    return extended


def ctc_forward(log_probs, target_ids, blank_id=0):
    """Return the alpha lattice and total log likelihood for one sequence."""
    import numpy as np

    frame_count, _ = log_probs.shape
    extended = _extended_states(target_ids, blank_id)
    state_count = len(extended)
    alpha = np.full((frame_count, state_count), NEG_INF)
    alpha[0, 0] = log_probs[0, blank_id]
    if state_count > 1:
        alpha[0, 1] = log_probs[0, extended[1]]
    for t in range(1, frame_count):
        stay = alpha[t - 1]
        step = np.full(state_count, NEG_INF)
        step[1:] = alpha[t - 1, :-1]
        merged = np.logaddexp(stay, step)
        skip = np.full(state_count, NEG_INF)
        for s in range(2, state_count):
            if extended[s] != blank_id and extended[s] != extended[s - 2]:
                skip[s] = alpha[t - 1, s - 2]
        merged = np.logaddexp(merged, skip)
        emissions = np.array([log_probs[t, token] for token in extended])
        alpha[t] = merged + emissions
    total = float(
        np.logaddexp(alpha[frame_count - 1, state_count - 1],
                     alpha[frame_count - 1, state_count - 2])
        if state_count > 1
        else alpha[frame_count - 1, state_count - 1]
    )
    if not math.isfinite(total):
        raise SfgopError("canonical CTC forward likelihood is not finite")
    return alpha, total


def ctc_backward(log_probs, target_ids, blank_id=0):
    """Return the beta lattice (emission-inclusive) for one sequence."""
    import numpy as np

    frame_count, _ = log_probs.shape
    extended = _extended_states(target_ids, blank_id)
    state_count = len(extended)
    beta = np.full((frame_count, state_count), NEG_INF)
    beta[frame_count - 1, state_count - 1] = log_probs[
        frame_count - 1, blank_id
    ]
    if state_count > 1:
        beta[frame_count - 1, state_count - 2] = log_probs[
            frame_count - 1, extended[state_count - 2]
        ]
    for t in range(frame_count - 2, -1, -1):
        stay = beta[t + 1]
        step = np.full(state_count, NEG_INF)
        step[:-1] = beta[t + 1, 1:]
        merged = np.logaddexp(stay, step)
        skip = np.full(state_count, NEG_INF)
        for s in range(state_count - 2):
            if (
                extended[s + 2] != blank_id
                and extended[s + 2] != extended[s]
            ):
                skip[s] = beta[t + 1, s + 2]
        merged = np.logaddexp(merged, skip)
        emissions = np.array([log_probs[t, token] for token in extended])
        beta[t] = merged + emissions
    return beta


def span_alternative_scores(
    log_probs,
    target_ids,
    span_start,
    span_end,
    candidate_ids,
    alpha,
    beta,
    blank_id=0,
):
    """Exact log likelihoods for replacing or deleting one expected span.

    ``span_start``/``span_end`` are token indices into ``target_ids``. The
    substitution lattice replaces the span with one candidate token; the
    deletion lattice removes it. Both reuse the canonical alpha and beta
    lattices, joined across the span, which is exact because states outside
    the span have identical transition structure in the modified sequences.
    """
    import numpy as np

    frame_count, _ = log_probs.shape
    token_count = len(target_ids)
    extended = _extended_states(target_ids, blank_id)
    candidate_ids = np.asarray(candidate_ids, dtype=np.int64)
    pre_blank = 2 * span_start
    pre_label = 2 * span_start - 1
    post_blank = 2 * span_end
    post_label = 2 * span_end + 1
    left_token = extended[pre_label] if span_start > 0 else None
    right_token = (
        extended[post_label] if span_end < token_count else None
    )

    candidate_lp = log_probs[:, candidate_ids]
    left_allowed = (
        np.ones(len(candidate_ids), dtype=bool)
        if left_token is None
        else candidate_ids != left_token
    )
    right_allowed = (
        np.ones(len(candidate_ids), dtype=bool)
        if right_token is None
        else candidate_ids != right_token
    )

    gamma = np.full(len(candidate_ids), NEG_INF)
    if span_start == 0:
        gamma = candidate_lp[0].copy()
    substitution = np.full(len(candidate_ids), NEG_INF)
    for t in range(frame_count):
        if t > 0:
            entry = np.full(len(candidate_ids), alpha[t - 1, pre_blank])
            if left_token is not None:
                entry[left_allowed] = np.logaddexp(
                    entry[left_allowed], alpha[t - 1, pre_label]
                )
            gamma = candidate_lp[t] + np.logaddexp(gamma, entry)
        if t + 1 < frame_count:
            exit_scores = np.full(
                len(candidate_ids), beta[t + 1, post_blank]
            ) if span_end < token_count else np.full(
                len(candidate_ids), NEG_INF
            )
            if span_end < token_count:
                exit_scores[right_allowed] = np.logaddexp(
                    exit_scores[right_allowed], beta[t + 1, post_label]
                )
            else:
                exit_scores = np.full(
                    len(candidate_ids), beta[t + 1, post_blank]
                )
            substitution = np.logaddexp(substitution, gamma + exit_scores)
        else:
            if span_end == token_count:
                substitution = np.logaddexp(substitution, gamma)
    if span_end == token_count and frame_count > 1:
        # Paths may also finish in the trailing blank after the candidate.
        # Those are already covered by beta[t + 1, post_blank] above because
        # post_blank is the final state.
        pass

    deletion = NEG_INF
    if 0 < token_count - (span_end - span_start):
        left_right_differ = (
            left_token is None
            or right_token is None
            or left_token != right_token
        )
        if span_start == 0 and span_end < token_count:
            deletion = np.logaddexp(deletion, beta[0, post_label])
        for t in range(frame_count):
            if t + 1 < frame_count and span_end < token_count:
                deletion = np.logaddexp(
                    deletion, alpha[t, pre_blank] + beta[t + 1, post_label]
                )
                if span_start > 0 and left_right_differ:
                    deletion = np.logaddexp(
                        deletion,
                        alpha[t, pre_label] + beta[t + 1, post_label],
                    )
        if span_end == token_count:
            deletion = np.logaddexp(
                deletion, alpha[frame_count - 1, pre_blank]
            )
            if span_start > 0:
                deletion = np.logaddexp(
                    deletion, alpha[frame_count - 1, pre_label]
                )
    return substitution, float(deletion)


def _logsumexp_vector(values):
    import numpy as np

    values = np.asarray(values, dtype=np.float64)
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return NEG_INF
    peak = finite.max()
    return float(peak + np.log(np.exp(values[np.isfinite(values)] - peak).sum()))


def score_clip_targets(
    log_probs, clip, vocab, candidate_ids, id_to_token, phone_map
):
    """Score every scorable expected span of one clip, label blind."""
    import numpy as np

    expected_items = expand_reference_phones(
        clip["reference_phones"], phone_map
    )
    token_ids = []
    span_bounds = {}
    for position, item in enumerate(expected_items):
        token = unicodedata.normalize("NFD", item["token"])
        if token not in vocab:
            raise SfgopError(
                f"expected token {item['token']!r} is missing from the "
                "frozen vocabulary"
            )
        token_ids.append(vocab[token])
        start, _ = span_bounds.get(item["origin_index"], (position, position))
        span_bounds[item["origin_index"]] = (start, position + 1)
    spans = []
    for target in clip["targets"]:
        if target["global_index"] not in span_bounds:
            raise SfgopError("manifest target has no expected token span")
        start, end = span_bounds[target["global_index"]]
        spans.append((target, start, end))
    if not token_ids:
        raise SfgopError("clip has no expected tokens")

    alpha, ll_canonical = ctc_forward(log_probs, token_ids)
    beta = ctc_backward(log_probs, token_ids)
    consistency = abs(
        ll_canonical
        - _logsumexp_vector([beta[0, 0], beta[0, 1]])
    )
    if consistency > 1e-6:
        raise SfgopError("CTC forward and backward likelihoods disagree")

    results = []
    for target, start, end in spans:
        if not target["scorable"]:
            results.append(
                {
                    "global_index": target["global_index"],
                    "arpabet": target["arpabet"],
                    "state": "unscorable",
                    "unscorable_reason": target.get("unscorable_reason")
                    or "not_a_supported_consonant_target",
                }
            )
            continue
        substitution, deletion = span_alternative_scores(
            log_probs, token_ids, start, end, candidate_ids, alpha, beta
        )
        self_check = None
        expected_ll = ll_canonical
        if end - start == 1:
            expected_positions = np.where(
                np.asarray(candidate_ids) == token_ids[start]
            )[0]
            if expected_positions.size != 1:
                raise SfgopError(
                    "expected token is not a candidate substitution"
                )
            junction_expected = float(substitution[expected_positions[0]])
            self_check = abs(junction_expected - ll_canonical)
            if self_check > 1e-6:
                raise SfgopError(
                    "junction likelihood for the expected phone does not "
                    "match the canonical likelihood"
                )
        denominator_s = _logsumexp_vector(substitution)
        denominator_sd = _logsumexp_vector(
            list(substitution) + [deletion]
        )
        order = np.argsort(substitution)[::-1]
        alternatives = []
        for index in order[:6]:
            token_id = int(candidate_ids[index])
            if token_id == token_ids[start] and end - start == 1:
                continue
            alternatives.append(
                {
                    "token": id_to_token[token_id],
                    "log_likelihood": _round_log(substitution[index]),
                    "posterior_sd": _round_log(
                        substitution[index] - denominator_sd
                    ),
                }
            )
            if len(alternatives) == 5:
                break
        results.append(
            {
                "global_index": target["global_index"],
                "arpabet": target["arpabet"],
                "state": "scored",
                "expected_span_tokens": [
                    id_to_token[token_ids[i]] for i in range(start, end)
                ],
                "gop_af_s": _round_log(expected_ll - denominator_s),
                "gop_af_sd": _round_log(expected_ll - denominator_sd),
                "expected_log_likelihood": _round_log(expected_ll),
                "deletion_log_likelihood": (
                    _round_log(deletion) if math.isfinite(deletion) else None
                ),
                "deletion_posterior_sd": (
                    _round_log(deletion - denominator_sd)
                    if math.isfinite(deletion)
                    else None
                ),
                "junction_self_check_abs_diff": (
                    _round_log(self_check) if self_check is not None else None
                ),
                "alternatives": alternatives,
            }
        )
    return {
        "expected_token_count": len(token_ids),
        "ll_canonical": _round_log(ll_canonical),
        "forward_backward_abs_diff": _round_log(consistency),
        "targets": results,
    }


def _candidate_ids(vocab):
    candidates = []
    for token, token_id in sorted(vocab.items(), key=lambda item: item[1]):
        if token_id == 0 or token.startswith("<") or token == "|":
            continue
        candidates.append(token_id)
    if len(candidates) < 100:
        raise SfgopError("frozen vocabulary candidate set is implausibly small")
    return candidates


def run_feasibility(
    expected_manifest_path=EXPECTED_MANIFEST_PATH,
    contract_path=SFGOP_CONTRACT_PATH,
    model_root=DEFAULT_MODEL_ROOT,
    output_root=DEFAULT_OUTPUT,
):
    if os.environ.get("SPEECH_SOUND_OFFLINE") != "1":
        raise SfgopError(
            "segmentation-free GOP requires SPEECH_SOUND_OFFLINE=1"
        )
    contract = load_sfgop_contract(contract_path)
    meta_contract = load_meta_contract(META_CONTRACT_PATH)
    if (
        file_sha256(META_CONTRACT_PATH)
        != contract["model"]["reference_contract_sha256"]
    ):
        raise SfgopError("meta model reference contract checksum changed")
    files = _verify_model(model_root, meta_contract)
    manifest = _load_expected_manifest(expected_manifest_path)
    subset_policy = contract["input_policy"]["feasibility_subset"]
    clips = [
        clip
        for clip in manifest["clips"]
        if clip["project_split"] == subset_policy["project_split"]
    ][: subset_policy["clip_count"]]
    if len(clips) != subset_policy["clip_count"]:
        raise SfgopError("feasibility subset selection changed size")

    output_root = _private_output(output_root)
    summary_path = output_root / "sfgop-feasibility-process.json"
    if summary_path.exists():
        raise SfgopError("completed feasibility evidence already exists")
    clips_root = output_root / "clips"
    clips_root.mkdir(parents=True, exist_ok=True)

    import numpy as np
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

    clip_records = []
    total_audio_seconds = 0.0
    total_seconds = 0.0
    for clip in clips:
        waveform, _ = _load_waveform(
            REPOSITORY_ROOT / clip["canonical_audio_path"],
            clip["canonical_audio_sha256"],
        )
        repeats = []
        clip_started = time.perf_counter()
        for _ in range(contract["extractor_policy"]["same_input_repeats"]):
            logits = session.run(
                None, {"input_values": waveform}
            )[0][0]
            log_probs = _log_softmax(logits)
            repeats.append(
                score_clip_targets(
                    log_probs,
                    clip,
                    vocab,
                    candidate_ids,
                    id_to_token,
                    phone_map,
                )
            )
        clip_seconds = time.perf_counter() - clip_started
        exact = canonical_json_bytes(repeats[0]) == canonical_json_bytes(
            repeats[1]
        )
        if not exact:
            raise SfgopError(
                f"repeat outputs differ for {clip['safe_id']}"
            )
        record = {
            "safe_id": clip["safe_id"],
            "input_sha256": clip["canonical_audio_sha256"],
            "project_split": clip["project_split"],
            "model_revision": meta_contract["model"]["revision"],
            "contract_sha256": SFGOP_CONTRACT_SHA256,
            "same_input_repeats_exact": True,
            "duration_s": clip["duration_s"],
            "evidence": repeats[0],
        }
        (clips_root / f"{clip['safe_id']}.json").write_bytes(
            canonical_json_bytes(record)
        )
        total_audio_seconds += clip["duration_s"]
        total_seconds += clip_seconds
        scored = sum(
            1
            for target in repeats[0]["targets"]
            if target["state"] == "scored"
        )
        clip_records.append(
            {
                "safe_id": clip["safe_id"],
                "scored_targets": scored,
                "unscorable_targets": len(repeats[0]["targets"]) - scored,
                "seconds": round(clip_seconds, 6),
            }
        )

    summary = {
        "summary_id": "sfgop_feasibility_process",
        "schema_version": "1.0.0",
        "contract_sha256": SFGOP_CONTRACT_SHA256,
        "expected_only_manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "model_revision": meta_contract["model"]["revision"],
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "clip_count": len(clip_records),
        "total_audio_seconds": round(total_audio_seconds, 6),
        "total_processing_seconds": round(total_seconds, 6),
        "real_time_factor": round(total_seconds / total_audio_seconds, 6),
        "peak_maxrss_bytes": peak_maxrss_bytes(),
        "all_repeats_exact": True,
        "clips": clip_records,
    }
    summary_path.write_bytes(canonical_json_bytes(summary))
    return summary


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Run the label-blind segmentation-free GOP feasibility "
            "extraction on the frozen development subset."
        )
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    summary = run_feasibility(output_root=arguments.output_root)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
