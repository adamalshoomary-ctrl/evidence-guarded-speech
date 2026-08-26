"""Checkpoint 22E8 scoring run for the reference variety probe.

Reuses the existing segmentation-free GOP implementation unchanged. Only the
source of the expected phone sequence is new: instead of an American ARPAbet
annotation, it is a documented variety read out of a pronunciation dictionary.
That is the whole point of the checkpoint, so the published equations are
imported rather than reimplemented beside them.

The model is run once per clip. Its frame posteriors do not depend on which
reference we are asking about, so both references are scored against the same
inference. Two references scored against two separate inferences of the same
audio would introduce a difference that has nothing to do with variety.

Results are written per clip so a long run resumes instead of restarting, and
nothing here selects a system, moves a gate or reads a sealed speaker.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from .benchmark_meta_ctc import DEFAULT_MODEL_ROOT, _verify_model, load_meta_contract
from .sfgop import (
    META_CONTRACT_PATH,
    SfgopError,
    _candidate_ids,
    ctc_backward,
    ctc_forward,
    span_alternative_scores,
)
from .variety_probe import (
    CANONICAL_ROOT,
    PRIVATE_ROOT,
    VarietyProbeError,
    load_contract,
)
from .variety_reference import SCORABLE_CONSONANTS, normalise

EVIDENCE_ROOT = PRIVATE_ROOT / "variety-probe" / "evidence"
SAMPLE_PATH = PRIVATE_ROOT / "variety-probe" / "sample.json"


def _logsumexp(values):
    import numpy as np

    array = np.asarray(values, dtype=float)
    finite = array[np.isfinite(array)]
    if finite.size == 0:
        return float("-inf")
    ceiling = float(finite.max())
    return ceiling + float(np.log(np.exp(finite - ceiling).sum()))


def _load_waveform(path):
    import numpy as np
    import soundfile

    waveform, rate = soundfile.read(path, dtype="float32", always_2d=False)
    if rate != 16000 or waveform.ndim != 1 or waveform.size == 0:
        raise VarietyProbeError(f"{Path(path).name} is not 16 kHz mono audio")
    normalised = (waveform - waveform.mean()) / float(
        np.sqrt(waveform.var() + 1e-7)
    )
    return normalised.astype(np.float32)[None, :]


def _log_softmax(logits):
    import numpy as np

    shifted = logits - logits.max(axis=-1, keepdims=True)
    return shifted - np.log(np.exp(shifted).sum(axis=-1, keepdims=True))


def score_sequence(log_probs, tokens, vocab, candidate_ids):
    """Score every consonant opportunity in one expected sequence."""
    import numpy as np

    token_ids = []
    for token in tokens:
        key = normalise(token)
        if key not in vocab:
            raise SfgopError(f"expected token {token!r} is outside the vocabulary")
        token_ids.append(vocab[key])
    alpha, ll_canonical = ctc_forward(log_probs, token_ids)
    beta = ctc_backward(log_probs, token_ids)
    targets = []
    for position, token in enumerate(tokens):
        if token not in SCORABLE_CONSONANTS:
            continue
        substitution, deletion = span_alternative_scores(
            log_probs, token_ids, position, position + 1, candidate_ids, alpha, beta
        )
        denominator = _logsumexp(list(substitution) + [deletion])
        targets.append(
            {
                "index": position,
                "token": token,
                "gop_af_sd": round(float(ll_canonical - denominator), 6),
            }
        )
    return {"ll_canonical": round(float(ll_canonical), 6), "targets": targets}


def _session(model_root=DEFAULT_MODEL_ROOT):
    import onnxruntime

    meta_contract = load_meta_contract(META_CONTRACT_PATH)
    files = _verify_model(model_root, meta_contract)
    options = onnxruntime.SessionOptions()
    options.execution_mode = onnxruntime.ExecutionMode.ORT_SEQUENTIAL
    options.intra_op_num_threads = 1
    options.inter_op_num_threads = 1
    session = onnxruntime.InferenceSession(
        str(files["weights_sha256"]),
        sess_options=options,
        providers=["CPUExecutionProvider"],
    )
    vocab = json.loads(files["vocab_sha256"].read_text(encoding="utf-8"))
    return session, {normalise(key): value for key, value in vocab.items()}, vocab


def run(sample_path=SAMPLE_PATH, evidence_root=EVIDENCE_ROOT, limit=None):
    """Score every sampled clip under both references, resuming if interrupted."""
    load_contract()
    sample = json.loads(Path(sample_path).read_text(encoding="utf-8"))
    session, vocab, raw_vocab = _session()
    candidate_ids = _candidate_ids(raw_vocab)
    Path(evidence_root).mkdir(parents=True, exist_ok=True)
    done = 0
    started = time.perf_counter()
    for source_id, group in sample["groups"].items():
        directory = Path(evidence_root) / source_id
        directory.mkdir(parents=True, exist_ok=True)
        for item in group["clips"]:
            stem = Path(item["clip"]).stem
            destination = directory / f"{stem}.json"
            if destination.is_file():
                done += 1
                continue
            if limit is not None and done >= limit:
                return {"scored": done, "seconds": time.perf_counter() - started}
            audio = CANONICAL_ROOT / source_id / f"{stem}.wav"
            waveform = _load_waveform(audio)
            logits = session.run(None, {"input_values": waveform})[0][0]
            log_probs = _log_softmax(logits)
            record = {
                "source_id": source_id,
                "participant": item["participant"],
                "clip": item["clip"],
                "frames": int(log_probs.shape[0]),
                "references": {
                    name: score_sequence(log_probs, tokens, vocab, candidate_ids)
                    for name, tokens in sorted(item["expected"].items())
                },
            }
            destination.write_text(
                json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            done += 1
    return {"scored": done, "seconds": time.perf_counter() - started}


if __name__ == "__main__":
    print(run())
