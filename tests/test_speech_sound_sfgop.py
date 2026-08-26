import itertools
import json
import math
import os
import tempfile
import unittest
from pathlib import Path

import numpy as np

from speech_sound_patterns.sfgop import (
    SFGOP_CONTRACT_PATH,
    SfgopError,
    ctc_backward,
    ctc_forward,
    load_sfgop_contract,
    run_feasibility,
    span_alternative_scores,
)


def collapse(path_ids, blank_id=0):
    result = []
    previous = None
    for token in path_ids:
        if token != blank_id and token != previous:
            result.append(token)
        previous = token
    return result


def brute_force_ll(log_probs, target_ids, blank_id=0):
    """Sum path probabilities over every label path that collapses to target."""
    frame_count, class_count = log_probs.shape
    total = -math.inf
    for path in itertools.product(range(class_count), repeat=frame_count):
        if collapse(list(path), blank_id) != list(target_ids):
            continue
        score = sum(log_probs[t, token] for t, token in enumerate(path))
        total = np.logaddexp(total, score)
    return float(total)


def random_log_probs(frame_count, class_count, seed):
    rng = np.random.default_rng(seed)
    raw = rng.normal(size=(frame_count, class_count))
    raw = raw - raw.max(axis=1, keepdims=True)
    return raw - np.log(np.exp(raw).sum(axis=1, keepdims=True))


class SfgopMathTests(unittest.TestCase):
    def test_forward_matches_brute_force(self):
        log_probs = random_log_probs(5, 4, seed=7)
        for target in ([1], [2, 3], [1, 1], [1, 2, 1]):
            _, ll = ctc_forward(log_probs, list(target))
            self.assertAlmostEqual(
                ll, brute_force_ll(log_probs, target), places=9
            )

    def test_forward_and_backward_agree(self):
        log_probs = random_log_probs(6, 4, seed=11)
        for target in ([1, 2], [3, 3], [1, 2, 3]):
            _, ll = ctc_forward(log_probs, list(target))
            beta = ctc_backward(log_probs, list(target))
            start = np.logaddexp(beta[0, 0], beta[0, 1])
            self.assertAlmostEqual(ll, float(start), places=9)

    def test_substitution_matches_brute_force(self):
        log_probs = random_log_probs(5, 4, seed=13)
        candidates = [1, 2, 3]
        for target in ([1, 2], [2, 2], [1, 2, 3], [3]):
            target = list(target)
            alpha, _ = ctc_forward(log_probs, target)
            beta = ctc_backward(log_probs, target)
            for position in range(len(target)):
                substitution, _ = span_alternative_scores(
                    log_probs,
                    target,
                    position,
                    position + 1,
                    candidates,
                    alpha,
                    beta,
                )
                for index, candidate in enumerate(candidates):
                    modified = list(target)
                    modified[position] = candidate
                    expected = brute_force_ll(log_probs, modified)
                    self.assertAlmostEqual(
                        float(substitution[index]),
                        expected,
                        places=9,
                        msg=(
                            f"target={target} position={position} "
                            f"candidate={candidate}"
                        ),
                    )

    def test_deletion_matches_brute_force(self):
        log_probs = random_log_probs(5, 4, seed=17)
        for target in ([1, 2], [2, 2], [1, 2, 3], [1, 2, 1]):
            target = list(target)
            if len(target) == 1:
                continue
            alpha, _ = ctc_forward(log_probs, target)
            beta = ctc_backward(log_probs, target)
            for position in range(len(target)):
                _, deletion = span_alternative_scores(
                    log_probs,
                    target,
                    position,
                    position + 1,
                    [1, 2, 3],
                    alpha,
                    beta,
                )
                modified = target[:position] + target[position + 1 :]
                expected = brute_force_ll(log_probs, modified)
                self.assertAlmostEqual(
                    float(deletion),
                    expected,
                    places=9,
                    msg=f"target={target} deleted position={position}",
                )

    def test_multi_token_span_matches_brute_force(self):
        log_probs = random_log_probs(6, 4, seed=19)
        target = [1, 2, 3]
        alpha, _ = ctc_forward(log_probs, target)
        beta = ctc_backward(log_probs, target)
        substitution, deletion = span_alternative_scores(
            log_probs, target, 0, 2, [1, 2, 3], alpha, beta
        )
        for index, candidate in enumerate([1, 2, 3]):
            expected = brute_force_ll(log_probs, [candidate, 3])
            self.assertAlmostEqual(
                float(substitution[index]), expected, places=9
            )
        self.assertAlmostEqual(
            float(deletion), brute_force_ll(log_probs, [3]), places=9
        )

    def test_whole_sequence_span_matches_brute_force(self):
        log_probs = random_log_probs(4, 4, seed=23)
        target = [2]
        alpha, _ = ctc_forward(log_probs, target)
        beta = ctc_backward(log_probs, target)
        substitution, deletion = span_alternative_scores(
            log_probs, target, 0, 1, [1, 2, 3], alpha, beta
        )
        for index, candidate in enumerate([1, 2, 3]):
            expected = brute_force_ll(log_probs, [candidate])
            self.assertAlmostEqual(
                float(substitution[index]), expected, places=9
            )
        self.assertEqual(deletion, -math.inf)

    def test_expected_candidate_equals_canonical_likelihood(self):
        log_probs = random_log_probs(6, 5, seed=29)
        target = [1, 4, 2]
        alpha, canonical = ctc_forward(log_probs, target)
        beta = ctc_backward(log_probs, target)
        for position in range(len(target)):
            substitution, _ = span_alternative_scores(
                log_probs, target, position, position + 1,
                [1, 2, 3, 4], alpha, beta,
            )
            index = [1, 2, 3, 4].index(target[position])
            self.assertAlmostEqual(
                float(substitution[index]), canonical, places=9
            )


class SfgopGuardTests(unittest.TestCase):
    def test_contract_checksum_is_enforced(self):
        with tempfile.TemporaryDirectory() as tmp:
            tampered = Path(tmp) / "sfgop-contract-v1.0.0.json"
            document = json.loads(SFGOP_CONTRACT_PATH.read_text())
            document["method"]["speechocean_trained_scoring_heads_allowed"] = True
            tampered.write_text(json.dumps(document))
            with self.assertRaises(SfgopError):
                load_sfgop_contract(tampered)

    def test_offline_environment_is_required(self):
        previous = os.environ.pop("SPEECH_SOUND_OFFLINE", None)
        try:
            with self.assertRaises(SfgopError):
                run_feasibility()
        finally:
            if previous is not None:
                os.environ["SPEECH_SOUND_OFFLINE"] = previous

    def test_committed_contract_loads(self):
        document = load_sfgop_contract()
        self.assertEqual(document["checkpoint"], "22E2")
        self.assertFalse(
            document["method"]["unlicensed_repository_code_allowed"]
        )


if __name__ == "__main__":
    unittest.main()
