"""Item R2 uncertainty for the checkpoint 22E8 reference variety probe.

The probe reported means and differences and nothing beside them. This module
computes what those numbers are worth: speaker clustered intervals, permutation
tests, and a correction for having tested many consonants at once.

Every rule that could be bent to rescue a finding is frozen in
`variety-probe-uncertainty-contract-v1.0.0.json` and read from it here rather
than written in this file. The multiple comparison family and the consonant
inclusion rule in particular were declared before any interval was computed,
because choosing either afterwards is the same failure mode as choosing a
threshold after seeing the scores.

Three things about the shape of the computation are methodological:

- **The speaker is the unit.** Two clips by one contributor are one cluster,
  everywhere: in the mean, in the resample, and in the permutation.
- **One resample serves every quantity.** The same drawn speakers are rescored
  under both references, at all five thresholds, for every consonant, so a
  difference between references stays paired within speaker as the design
  intended.
- **Resampling is stratified by source.** Group sizes and the American group's
  male and female balance are design decisions, not observations, so a resample
  that varied them would vary accent with gender.

Nothing here reads audio, loads a model, or calls a provider. It reads stored
per target scores only.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from .variety_probe import PRIVATE_ROOT, REPORTING_GROUPS, load_contract
from .variety_probe_score import EVIDENCE_ROOT, load_evidence

CONTRACT_PATH = Path(__file__).with_name(
    "variety-probe-uncertainty-contract-v1.0.0.json"
)

REFERENCES = ("american", "british")
# Ordered so the control group is last and a differential always reads
# "group minus control".
GROUPS = ("australian", "british", "american")


class VarietyUncertaintyError(RuntimeError):
    """Raised when the evidence cannot support the uncertainty it is asked for."""


def load_uncertainty_contract(path=CONTRACT_PATH):
    contract = json.loads(Path(path).read_text(encoding="utf-8"))
    boundaries = contract["release_boundaries"]
    opened = [flag for flag, value in boundaries.items() if value is not False]
    if opened:
        raise VarietyUncertaintyError(
            "the uncertainty contract must keep every release boundary closed, "
            f"but these are open: {', '.join(sorted(opened))}"
        )
    if contract["multiple_comparison_families"]["declared_before_computing"] is not True:
        raise VarietyUncertaintyError(
            "the multiple comparison family must be declared before it is computed"
        )
    return contract


def _reporting_group(source_id):
    for name, members in REPORTING_GROUPS.items():
        if source_id in members:
            return name
    raise VarietyUncertaintyError(f"{source_id} belongs to no reporting group")


class SpeakerEvidence:
    """Per speaker counts, which is the only level anything here aggregates at.

    Built once from the stored per target scores. Every interval, test and
    correction downstream is arithmetic on these arrays, so the expensive part
    of the computation happens exactly once and a resample costs an index.
    """

    def __init__(self, records, thresholds):
        self.thresholds = tuple(float(t) for t in thresholds)

        keys = sorted({(r["source_id"], r["participant"]) for r in records})
        self.speaker_index = {key: i for i, key in enumerate(keys)}
        self.speakers = keys
        n = len(keys)

        self.source_of_speaker = [source for source, _ in keys]
        self.group_of_speaker = [
            _reporting_group(source) for source in self.source_of_speaker
        ]

        tokens = sorted(
            {
                target["token"]
                for record in records
                for reference in REFERENCES
                for target in record["references"][reference]["targets"]
            }
        )
        self.tokens = tuple(tokens)
        token_index = {token: i for i, token in enumerate(tokens)}
        t_count = len(tokens)
        r_count = len(REFERENCES)
        h_count = len(self.thresholds)

        # opportunities do not depend on the threshold; flags do.
        self.opportunities = np.zeros((r_count, n), dtype=np.int64)
        self.flagged = np.zeros((r_count, h_count, n), dtype=np.int64)
        self.token_opportunities = np.zeros((r_count, t_count, n), dtype=np.int64)
        self.token_flagged = np.zeros((r_count, h_count, t_count, n), dtype=np.int64)

        thresholds_array = np.asarray(self.thresholds)
        for record in records:
            speaker = self.speaker_index[(record["source_id"], record["participant"])]
            for r, reference in enumerate(REFERENCES):
                targets = record["references"][reference]["targets"]
                if not targets:
                    continue
                scores = np.fromiter(
                    (target["gop_af_sd"] for target in targets),
                    dtype=np.float64,
                    count=len(targets),
                )
                columns = np.fromiter(
                    (token_index[target["token"]] for target in targets),
                    dtype=np.int64,
                    count=len(targets),
                )
                below = scores[None, :] < thresholds_array[:, None]
                self.opportunities[r, speaker] += len(targets)
                self.flagged[r, :, speaker] += below.sum(axis=1)
                np.add.at(self.token_opportunities[r, :, speaker], columns, 1)
                for h in range(h_count):
                    hit = columns[below[h]]
                    if hit.size:
                        np.add.at(self.token_flagged[r, h, :, speaker], hit, 1)

        if not self.opportunities.any():
            raise VarietyUncertaintyError("no speaker has a scoring opportunity")

    # -- views the statistics layer works from -----------------------------

    def group_members(self, group):
        """Speaker row indices belonging to one reporting group."""
        return np.array(
            [i for i, name in enumerate(self.group_of_speaker) if name == group],
            dtype=np.int64,
        )

    def source_members(self, source):
        """Speaker row indices belonging to one source, the resampling stratum."""
        return np.array(
            [i for i, name in enumerate(self.source_of_speaker) if name == source],
            dtype=np.int64,
        )

    def speaker_rates(self, reference, threshold):
        """Per speaker flag rate over every consonant, and who has evidence."""
        r = REFERENCES.index(reference)
        h = self.thresholds.index(float(threshold))
        opportunities = self.opportunities[r]
        present = opportunities > 0
        rates = np.zeros(len(opportunities), dtype=np.float64)
        np.divide(
            self.flagged[r, h], opportunities, out=rates, where=present
        )
        return rates, present

    def token_rates(self, reference, threshold, token):
        """Per speaker flag rate for one consonant, and who was ever given it.

        A speaker with no opportunity for this consonant is reported as absent
        rather than as a zero. They were never given the chance to be flagged,
        which is missing evidence and not a clean production.
        """
        r = REFERENCES.index(reference)
        h = self.thresholds.index(float(threshold))
        t = self.tokens.index(token)
        opportunities = self.token_opportunities[r, t]
        present = opportunities > 0
        rates = np.zeros(len(opportunities), dtype=np.float64)
        np.divide(
            self.token_flagged[r, h, t], opportunities, out=rates, where=present
        )
        return rates, present

    def token_speaker_counts(self, token):
        """Opportunities and covered speakers per group, for the inclusion rule.

        Denominators only. This is what the inclusion rule was frozen against
        and it carries no information about any flag rate.
        """
        r = REFERENCES.index("american")
        t = self.tokens.index(token)
        opportunities = self.token_opportunities[r, t]
        return {
            group: {
                "opportunities": int(opportunities[self.group_members(group)].sum()),
                "speakers": int((opportunities[self.group_members(group)] > 0).sum()),
            }
            for group in GROUPS
        }


def load_speaker_evidence(evidence_root=EVIDENCE_ROOT, contract=None):
    contract = contract or load_contract()
    records = load_evidence(evidence_root)
    return SpeakerEvidence(records, contract["scoring"]["reported_thresholds"])


def mean_rate(rates, present, members):
    """Unweighted mean across the members of a group who have evidence."""
    selected = present[members]
    if not selected.any():
        return None
    return float(rates[members][selected].mean())


# ---------------------------------------------------------------------------
# Statistics
#
# Every quantity this item reports is a signed sum of group means of one per
# speaker vector. Writing them that way means one bootstrap engine, one
# jackknife and one permutation engine serve the group level analysis and the
# per consonant analysis alike, so the two cannot drift apart in how they were
# computed. That drift is exactly the defect this item is repairing.
# ---------------------------------------------------------------------------

from statistics import NormalDist  # noqa: E402  (kept beside its only users)

_NORMAL = NormalDist()


class Term:
    """One signed group mean of one per speaker vector."""

    __slots__ = ("sign", "group", "values", "present")

    def __init__(self, sign, group, values, present):
        self.sign = sign
        self.group = group
        self.values = values
        self.present = present


def point_estimate(terms, evidence):
    total = 0.0
    for term in terms:
        mean = mean_rate(term.values, term.present, evidence.group_members(term.group))
        if mean is None:
            return None
        total += term.sign * mean
    return total


def _group_columns(strata, group):
    """Resampled speaker rows for one reporting group, stratified by source."""
    return np.concatenate([strata[source] for source in REPORTING_GROUPS[group]], axis=1)


def bootstrap_replicates(terms, strata, chunk=2000):
    """Recompute the statistic on every resample of speakers.

    The same drawn speakers serve every statistic in the report, so a
    difference between two references stays paired within speaker exactly as
    the design intended.
    """
    columns = {term.group: _group_columns(strata, term.group) for term in terms}
    total_draws = next(iter(columns.values())).shape[0]
    out = np.zeros(total_draws, dtype=np.float64)
    for start in range(0, total_draws, chunk):
        stop = min(start + chunk, total_draws)
        running = np.zeros(stop - start, dtype=np.float64)
        for term in terms:
            index = columns[term.group][start:stop]
            weight = term.present.astype(np.float64)
            numerator = (term.values * weight)[index].sum(axis=1)
            denominator = weight[index].sum(axis=1)
            mean = np.divide(
                numerator,
                denominator,
                out=np.full(stop - start, np.nan),
                where=denominator > 0,
            )
            running += term.sign * mean
        out[start:stop] = running
    return out


def jackknife_values(terms, evidence):
    """Leave one speaker out, for the BCa acceleration.

    A speaker outside every group the statistic reads leaves it unchanged,
    which is correct: the jackknife runs over all clusters in the sample.
    """
    n = len(evidence.speakers)
    out = np.zeros(n, dtype=np.float64)
    for term in terms:
        members = evidence.group_members(term.group)
        weight = term.present.astype(np.float64)
        numerator = float((term.values * weight)[members].sum())
        denominator = float(weight[members].sum())
        base = numerator / denominator if denominator else np.nan
        contribution = np.full(n, base, dtype=np.float64)
        member_numerator = numerator - (term.values * weight)[members]
        member_denominator = denominator - weight[members]
        contribution[members] = np.divide(
            member_numerator,
            member_denominator,
            out=np.full(len(members), np.nan),
            where=member_denominator > 0,
        )
        out += term.sign * contribution
    return out


def bca_interval(observed, replicates, jackknife, level=0.95):
    """Bias corrected and accelerated interval, with its percentile twin.

    Falls back to the percentile interval, and says so in the returned record,
    when the bootstrap distribution is degenerate enough that the bias and
    acceleration corrections are undefined.
    """
    replicates = replicates[np.isfinite(replicates)]
    draws = len(replicates)
    if draws < 100 or observed is None:
        return None
    alpha = (1.0 - level) / 2.0
    percentile = [
        float(np.percentile(replicates, 100 * alpha)),
        float(np.percentile(replicates, 100 * (1 - alpha))),
    ]

    below = float(np.count_nonzero(replicates < observed))
    equal = float(np.count_nonzero(replicates == observed))
    proportion = (below + 0.5 * equal) / draws
    method = "bca"
    if proportion <= 0.0 or proportion >= 1.0:
        method = "percentile_fallback_bias_undefined"
        return {
            "low": percentile[0],
            "high": percentile[1],
            "percentile_low": percentile[0],
            "percentile_high": percentile[1],
            "method": method,
            "resamples": draws,
        }
    z0 = _NORMAL.inv_cdf(proportion)

    jackknife = jackknife[np.isfinite(jackknife)]
    deviation = jackknife.mean() - jackknife
    denominator = 6.0 * (float((deviation ** 2).sum()) ** 1.5)
    acceleration = (
        float((deviation ** 3).sum()) / denominator if denominator > 0 else 0.0
    )

    def endpoint(z_alpha):
        adjusted = z0 + (z0 + z_alpha) / (1.0 - acceleration * (z0 + z_alpha))
        return float(np.clip(_NORMAL.cdf(adjusted), 1e-6, 1 - 1e-6))

    low_q = endpoint(_NORMAL.inv_cdf(alpha))
    high_q = endpoint(_NORMAL.inv_cdf(1 - alpha))
    return {
        "low": float(np.percentile(replicates, 100 * low_q)),
        "high": float(np.percentile(replicates, 100 * high_q)),
        "percentile_low": percentile[0],
        "percentile_high": percentile[1],
        "method": method,
        "bias_correction": float(z0),
        "acceleration": float(acceleration),
        "resamples": draws,
    }


def draw_strata(evidence, resamples, seed):
    """Resample speakers with replacement, within source.

    Group sizes and the American group's male and female balance are design
    decisions of the parent contract rather than observations. A resample that
    varied them would vary accent with speaker gender, which is the confound
    the parent contract pooled the two American subsets to avoid.
    """
    rng = np.random.default_rng(
        int.from_bytes(seed.encode("utf-8"), "big") % (2 ** 63 - 1)
    )
    strata = {}
    for source in sorted({s for s in evidence.source_of_speaker}):
        members = evidence.source_members(source)
        strata[source] = members[
            rng.integers(0, len(members), size=(resamples, len(members)), dtype=np.int64)
        ].astype(np.int32)
    return strata


def permutation_p_between_groups(
    evidence, values, present, left, right, permutations, seed
):
    """Two sided speaker label permutation test for a between group difference.

    Whole speakers are relabelled, never individual opportunities, so the
    clustering the design has is the clustering the test respects.

    Only speakers who had at least one opportunity are permuted. The groups
    read different prompts, so coverage of a given consonant differs between
    them by lexical accident. Conditioning on who was given the chance keeps
    the test measuring the flag rate rather than the prompt list.
    """
    left_members = evidence.group_members(left)
    right_members = evidence.group_members(right)
    left_members = left_members[present[left_members]]
    right_members = right_members[present[right_members]]
    if len(left_members) < 2 or len(right_members) < 2:
        return None
    pooled = np.concatenate([left_members, right_members])
    weight = present.astype(np.float64)
    weighted = values * weight

    left_n = len(left_members)
    observed_left = weighted[left_members].sum() / max(weight[left_members].sum(), 1e-12)
    observed_right = weighted[right_members].sum() / max(
        weight[right_members].sum(), 1e-12
    )
    observed = observed_left - observed_right

    rng = np.random.default_rng(
        int.from_bytes(seed.encode("utf-8"), "big") % (2 ** 63 - 1)
    )
    pooled_weighted = weighted[pooled]
    pooled_weight = weight[pooled]
    total_weighted = pooled_weighted.sum()
    total_weight = pooled_weight.sum()

    extreme = 0
    counted = 0
    chunk = 2000
    for start in range(0, permutations, chunk):
        size = min(chunk, permutations - start)
        # A partial partition is enough: the left_n smallest uniform draws
        # are a uniformly random subset, and sorting the rest is wasted work.
        order = np.argpartition(rng.random((size, len(pooled))), left_n - 1, axis=1)
        chosen = order[:, :left_n]
        left_weighted = pooled_weighted[chosen].sum(axis=1)
        left_weight = pooled_weight[chosen].sum(axis=1)
        right_weighted = total_weighted - left_weighted
        right_weight = total_weight - left_weight
        usable = (left_weight > 0) & (right_weight > 0)
        difference = np.full(size, np.nan)
        difference[usable] = (
            left_weighted[usable] / left_weight[usable]
            - right_weighted[usable] / right_weight[usable]
        )
        extreme += int(
            np.count_nonzero(np.abs(difference[usable]) >= abs(observed) - 1e-12)
        )
        counted += int(usable.sum())
    return {
        "observed": float(observed),
        "p_value": (extreme + 1) / (counted + 1),
        "permutations": counted,
        "test": "speaker_label_permutation",
        "conditioned_on_coverage": True,
        "left_speakers": int(len(left_members)),
        "right_speakers": int(len(right_members)),
    }


def permutation_p_paired_reference(
    evidence, group, american_values, american_present, british_values,
    british_present, permutations, seed
):
    """Two sided paired sign flip test for the change under the repair.

    The same speakers, clips and posteriors are scored under both references,
    so the test flips each speaker's two reference labels rather than treating
    the conditions as independent samples.
    """
    members = evidence.group_members(group)
    usable = members[american_present[members] & british_present[members]]
    if len(usable) < 2:
        return None
    difference = british_values[usable] - american_values[usable]
    observed = float(difference.mean())
    rng = np.random.default_rng(
        int.from_bytes(seed.encode("utf-8"), "big") % (2 ** 63 - 1)
    )
    extreme = 0
    chunk = 2000
    for start in range(0, permutations, chunk):
        size = min(chunk, permutations - start)
        signs = rng.choice(np.array([-1.0, 1.0]), size=(size, len(usable)))
        means = (signs * difference).mean(axis=1)
        extreme += int(np.count_nonzero(np.abs(means) >= abs(observed) - 1e-12))
    return {
        "observed": observed,
        "p_value": (extreme + 1) / (permutations + 1),
        "permutations": permutations,
        "speakers": int(len(usable)),
        "test": "paired_sign_flip_permutation",
    }


def benjamini_hochberg(p_values):
    """Step up false discovery rate adjusted p values, order preserved."""
    values = np.asarray(p_values, dtype=np.float64)
    n = len(values)
    if n == 0:
        return values
    order = np.argsort(values)
    ranked = values[order]
    adjusted = ranked * n / (np.arange(n) + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    out = np.empty(n, dtype=np.float64)
    out[order] = np.minimum(adjusted, 1.0)
    return out


def bonferroni(p_values):
    values = np.asarray(p_values, dtype=np.float64)
    return np.minimum(values * len(values), 1.0)


def minimum_detectable_effect(evidence, values, present, left, right, power=0.80,
                              alpha=0.05):
    """The smallest true difference this design could reliably have detected.

    Computed from the observed between speaker spread rather than assumed, so
    a null result can be read as either a small effect or an underpowered look
    instead of being left ambiguous.
    """
    left_members = evidence.group_members(left)
    right_members = evidence.group_members(right)
    left_values = values[left_members][present[left_members]]
    right_values = values[right_members][present[right_members]]
    if len(left_values) < 2 or len(right_values) < 2:
        return None
    standard_error = float(
        np.sqrt(
            left_values.var(ddof=1) / len(left_values)
            + right_values.var(ddof=1) / len(right_values)
        )
    )
    multiplier = _NORMAL.inv_cdf(1 - alpha / 2) + _NORMAL.inv_cdf(power)
    return {
        "standard_error": standard_error,
        "minimum_detectable_difference": multiplier * standard_error,
        "power": power,
        "alpha": alpha,
        "left_speakers": int(len(left_values)),
        "right_speakers": int(len(right_values)),
    }


# ---------------------------------------------------------------------------
# The analysis itself
# ---------------------------------------------------------------------------

RESAMPLES = 10000
PERMUTATIONS = 10000
BASE_SEED = "speech_sound_patterns_variety_probe_uncertainty_v1"
PRIMARY_THRESHOLD = -1.0

CONTRASTS = {
    "australian_minus_american": ("australian", "american"),
    "british_minus_american": ("british", "american"),
}


def admitted_consonants(evidence, uncertainty_contract, contrast):
    """Apply the frozen inclusion rule, which was set from denominators alone.

    Returns the consonants a family may contain and, separately, the ones that
    are reported with their counts and explicitly marked untested. A consonant
    is never silently dropped, because a reader cannot audit an absence.
    """
    rule = uncertainty_contract["consonant_inclusion_rule"]
    minimum_opportunities = 100
    minimum_speakers = 50
    assert "at least 100 scoring opportunities" in rule["rule"]
    assert "at least 50 speakers" in rule["rule"]

    left, right = CONTRASTS[contrast]
    admitted, untested = [], {}
    for token in evidence.tokens:
        counts = evidence.token_speaker_counts(token)
        qualifies = all(
            counts[group]["opportunities"] >= minimum_opportunities
            and counts[group]["speakers"] >= minimum_speakers
            for group in (left, right)
        )
        if qualifies:
            admitted.append(token)
        else:
            untested[token] = {
                group: counts[group] for group in (left, right)
            }
    return admitted, untested


def _statistic(evidence, terms, strata, name):
    """Point estimate and speaker clustered interval for one quantity."""
    observed = point_estimate(terms, evidence)
    if observed is None:
        return None
    replicates = bootstrap_replicates(terms, strata)
    jackknife = jackknife_values(terms, evidence)
    interval = bca_interval(observed, replicates, jackknife)
    record = {"point": round(observed, 6), "name": name}
    if interval:
        record["ci_low"] = round(interval["low"], 6)
        record["ci_high"] = round(interval["high"], 6)
        record["percentile_ci_low"] = round(interval["percentile_low"], 6)
        record["percentile_ci_high"] = round(interval["percentile_high"], 6)
        record["interval_method"] = interval["method"]
        record["crosses_zero"] = bool(interval["low"] <= 0.0 <= interval["high"])
    return record


def build_uncertainty(evidence=None, contract=None, uncertainty_contract=None,
                      resamples=RESAMPLES, permutations=PERMUTATIONS,
                      evidence_root=EVIDENCE_ROOT):
    """Compute every interval, test and correction this item promised.

    The families were frozen in the contract before any of this ran. Nothing
    below chooses a family, a threshold or a consonant; it fills in what the
    contract already fixed.
    """
    contract = contract or load_contract()
    uncertainty_contract = uncertainty_contract or load_uncertainty_contract()
    evidence = evidence if evidence is not None else load_speaker_evidence(
        evidence_root=evidence_root, contract=contract
    )
    strata = draw_strata(evidence, resamples, BASE_SEED)
    thresholds = [float(t) for t in contract["scoring"]["reported_thresholds"]]

    vectors = {
        (reference, threshold): evidence.speaker_rates(reference, threshold)
        for reference in REFERENCES
        for threshold in thresholds
    }

    # -- group level -------------------------------------------------------
    group_level = {}
    for threshold in thresholds:
        entry = {}
        for reference in REFERENCES:
            values, present = vectors[(reference, threshold)]
            entry[reference] = {
                group: _statistic(
                    evidence,
                    [Term(1, group, values, present)],
                    strata,
                    f"{reference}_reference_{group}_flag_rate_at_{threshold}",
                )
                for group in GROUPS
            }
        differentials = {}
        for reference in REFERENCES:
            values, present = vectors[(reference, threshold)]
            differentials[reference] = {}
            for group in ("australian", "british"):
                name = f"{group}_minus_american_{reference}_reference_at_{threshold}"
                record = _statistic(
                    evidence,
                    [Term(1, group, values, present), Term(-1, "american", values, present)],
                    strata,
                    name,
                )
                test = permutation_p_between_groups(
                    evidence, values, present, group, "american", permutations,
                    BASE_SEED + name,
                )
                if test:
                    record["p_value"] = round(test["p_value"], 6)
                    record["test"] = test["test"]
                    record["permutations"] = test["permutations"]
                differentials[reference][group] = record
        entry["differential_against_the_american_group"] = differentials

        change = {}
        for group in GROUPS:
            american_values, american_present = vectors[("american", threshold)]
            british_values, british_present = vectors[("british", threshold)]
            name = f"{group}_change_under_the_repair_at_{threshold}"
            record = _statistic(
                evidence,
                [
                    Term(1, group, british_values, british_present),
                    Term(-1, group, american_values, american_present),
                ],
                strata,
                name,
            )
            test = permutation_p_paired_reference(
                evidence, group, american_values, american_present, british_values,
                british_present, permutations, BASE_SEED + name,
            )
            if test:
                record["p_value"] = round(test["p_value"], 6)
                record["test"] = test["test"]
                record["speakers"] = test["speakers"]
            change[group] = record
        entry["change_under_the_repair"] = change
        group_level[str(threshold)] = entry

    # -- per consonant, per speaker then averaged --------------------------
    admitted = {
        contrast: admitted_consonants(evidence, uncertainty_contract, contrast)
        for contrast in CONTRASTS
    }
    per_consonant = {}
    for reference in REFERENCES:
        per_consonant[reference] = {}
        for contrast, (left, right) in CONTRASTS.items():
            tokens = admitted[contrast][0]
            per_consonant[reference][contrast] = {}
            for threshold in thresholds:
                by_token = {}
                for token in tokens:
                    values, present = evidence.token_rates(reference, threshold, token)
                    name = f"{contrast}_{token}_{reference}_reference_at_{threshold}"
                    record = _statistic(
                        evidence,
                        [Term(1, left, values, present), Term(-1, right, values, present)],
                        strata,
                        name,
                    )
                    if record is None:
                        continue
                    test = permutation_p_between_groups(
                        evidence, values, present, left, right, permutations,
                        BASE_SEED + name,
                    )
                    if test:
                        record["p_value"] = round(test["p_value"], 6)
                        record["test"] = test["test"]
                        record["left_speakers"] = test["left_speakers"]
                        record["right_speakers"] = test["right_speakers"]
                    by_token[token] = record
                per_consonant[reference][contrast][str(threshold)] = by_token
    return {
        "evidence": evidence,
        "strata": strata,
        "thresholds": thresholds,
        "group_level": group_level,
        "per_consonant": per_consonant,
        "admitted": admitted,
        "vectors": vectors,
    }


def _family_rows(records):
    """Order a family's members deterministically, so a rerun reads the same."""
    return sorted(records, key=lambda row: row["name"])


def _corrected(rows, family_name, level=0.05):
    """Apply both corrections and record what each one decides.

    All three columns are published together. A finding that fails correction
    is recorded as having failed; it may not be rescued by quoting its
    uncorrected p value as though that were the result.
    """
    tested = [row for row in rows if "p_value" in row]
    p_values = [row["p_value"] for row in tested]
    bh = benjamini_hochberg(p_values)
    bonf = bonferroni(p_values)
    members = []
    for row, adjusted, strict in zip(tested, bh, bonf):
        members.append(
            {
                **{key: row[key] for key in row if key != "name"},
                "name": row["name"],
                "p_uncorrected": row["p_value"],
                "p_benjamini_hochberg": round(float(adjusted), 6),
                "p_bonferroni": round(float(strict), 6),
                "survives_uncorrected": bool(row["p_value"] < level),
                "survives_benjamini_hochberg": bool(adjusted < level),
                "survives_bonferroni": bool(strict < level),
            }
        )
    members = _family_rows(members)
    return {
        "family": family_name,
        "tests": len(members),
        "level": level,
        "members": members,
        "survivors_uncorrected": [
            row["name"] for row in members if row["survives_uncorrected"]
        ],
        "survivors_benjamini_hochberg": [
            row["name"] for row in members if row["survives_benjamini_hochberg"]
        ],
        "survivors_bonferroni": [
            row["name"] for row in members if row["survives_bonferroni"]
        ],
    }


def assemble_families(analysis, uncertainty_contract):
    """Fill in the families the contract froze before any of this was computed."""
    thresholds = analysis["thresholds"]
    primary = str(PRIMARY_THRESHOLD)
    group_level = analysis["group_level"]
    per_consonant = analysis["per_consonant"]

    family_g = []
    for group in ("australian", "british"):
        family_g.append(
            group_level[primary]["differential_against_the_american_group"]["american"][
                group
            ]
        )
    for group in GROUPS:
        family_g.append(group_level[primary]["change_under_the_repair"][group])

    family_a = list(
        per_consonant["american"]["australian_minus_american"][primary].values()
    )
    family_b = list(
        per_consonant["american"]["british_minus_american"][primary].values()
    )
    family_s = [
        row
        for reference in REFERENCES
        for contrast in CONTRASTS
        for threshold in thresholds
        for row in per_consonant[reference][contrast][str(threshold)].values()
    ]
    return {
        "declared_before_computing": True,
        "G_pre_registered_group_level": _corrected(
            family_g, "G_pre_registered_group_level"
        ),
        "A_primary_per_consonant": _corrected(family_a, "A_primary_per_consonant"),
        "B_secondary_per_consonant": _corrected(family_b, "B_secondary_per_consonant"),
        "S_sceptical_sensitivity": _corrected(family_s, "S_sceptical_sensitivity"),
        "family_definitions": uncertainty_contract["multiple_comparison_families"],
    }


def aggregation_comparison(analysis):
    """Show the per consonant estimates before and after the aggregation fix.

    The old figure pooled every token in the group; the new one averages
    speakers. Publishing both means the movement can be read as the correction
    it is, rather than mistaken for new evidence.
    """
    evidence = analysis["evidence"]
    reference = "american"
    r = REFERENCES.index(reference)
    h = evidence.thresholds.index(PRIMARY_THRESHOLD)
    rows = {}
    for contrast, (left, right) in CONTRASTS.items():
        rows[contrast] = {}
        for token, record in analysis["per_consonant"][reference][contrast][
            str(PRIMARY_THRESHOLD)
        ].items():
            t = evidence.tokens.index(token)
            pooled = {}
            for group in (left, right):
                members = evidence.group_members(group)
                opportunities = int(evidence.token_opportunities[r, t][members].sum())
                flagged = int(evidence.token_flagged[r, h, t][members].sum())
                pooled[group] = flagged / opportunities if opportunities else None
            rows[contrast][token] = {
                "pooled_tokens_as_in_version_1_1_0": round(
                    pooled[left] - pooled[right], 6
                ),
                "per_speaker_then_averaged": record["point"],
            }
    return rows


def detectable_effects(analysis):
    """What this design could have detected, from the observed spread."""
    evidence = analysis["evidence"]
    values, present = analysis["vectors"][("american", PRIMARY_THRESHOLD)]
    group_level = {
        contrast: minimum_detectable_effect(evidence, values, present, left, right)
        for contrast, (left, right) in CONTRASTS.items()
    }
    consonant = {}
    for contrast, (left, right) in CONTRASTS.items():
        rows = {}
        for token in analysis["per_consonant"]["american"][contrast][
            str(PRIMARY_THRESHOLD)
        ]:
            token_values, token_present = evidence.token_rates(
                "american", PRIMARY_THRESHOLD, token
            )
            estimate = minimum_detectable_effect(
                evidence, token_values, token_present, left, right
            )
            if estimate:
                rows[token] = round(estimate["minimum_detectable_difference"], 6)
        consonant[contrast] = rows
    return {
        "group_level": {
            contrast: {
                key: round(value, 6) if isinstance(value, float) else value
                for key, value in estimate.items()
            }
            for contrast, estimate in group_level.items()
            if estimate
        },
        "per_consonant_minimum_detectable_difference": consonant,
        "power": 0.80,
        "alpha": 0.05,
        "what_this_means": "The smallest true difference this design would detect four times in five. A differential smaller than this is not evidence of no difference; it is a look too small to tell.",
        "standing_limit": "The Australian eligible pool is 674 speakers and the probe already samples about 45 percent of it, so this is not fixable by collecting more Australian speakers.",
    }


def build_uncertainty_block(analysis=None, uncertainty_contract=None, **kwargs):
    """The serialisable uncertainty record that goes into the report."""
    uncertainty_contract = uncertainty_contract or load_uncertainty_contract()
    analysis = analysis or build_uncertainty(
        uncertainty_contract=uncertainty_contract, **kwargs
    )
    families = assemble_families(analysis, uncertainty_contract)
    admitted, untested = analysis["admitted"]["australian_minus_american"]
    admitted_b, untested_b = analysis["admitted"]["british_minus_american"]
    return {
        "contract_id": uncertainty_contract["contract_id"],
        "item": "R2",
        "method": {
            "unit_of_analysis": "the speaker",
            "interval": "speaker clustered bias corrected and accelerated bootstrap, percentile interval reported beside it",
            "resamples": RESAMPLES,
            "stratification": "within source, at the observed 300 speakers per source",
            "pairing": "one resample serves every reference, threshold and consonant",
            "between_group_test": "speaker label permutation, conditioned on which speakers had an opportunity",
            "within_group_test": "paired sign flip permutation across the two references",
            "permutations": PERMUTATIONS,
            "seed": BASE_SEED,
            "corrections": ["uncorrected", "benjamini_hochberg", "bonferroni"],
            "re_inference": "none. Stored per target scores only.",
        },
        "aggregation_change": {
            "what_changed": "The per consonant analysis now computes a rate per speaker and then averages, matching the group level analysis. Version 1.1.0 pooled every token in the group and applied no speaker clustering at all.",
            "before_and_after": aggregation_comparison(analysis),
        },
        "consonant_inclusion": {
            "rule": uncertainty_contract["consonant_inclusion_rule"]["rule"],
            "admitted": {
                "australian_minus_american": admitted,
                "british_minus_american": admitted_b,
            },
            "not_tested_for_want_of_denominator": {
                "australian_minus_american": untested,
                "british_minus_american": untested_b,
            },
            "a_consequence_worth_stating_plainly": uncertainty_contract[
                "consonant_inclusion_rule"
            ]["a_consequence_worth_stating_plainly"],
        },
        "reference_opportunity_parity": reference_opportunity_parity(analysis),
        "group_level": analysis["group_level"],
        "per_consonant": analysis["per_consonant"],
        "families": families,
        "detectable_effect": detectable_effects(analysis),
        "training_lineage_declaration": uncertainty_contract[
            "training_lineage_declaration"
        ],
        "what_this_cannot_establish": uncertainty_contract["what_this_cannot_establish"],
    }


def reference_opportunity_parity(analysis):
    """Do the two references create the same scoring opportunities?

    They do not, and the answer differs by consonant. Swapping the reference
    changes the expected phone sequence, so a consonant can gain or lose
    opportunities, and a cross reference comparison for such a consonant is not
    comparing like with like. A consonant whose opportunity count is stable
    across references is comparable across them; one whose count moves is not,
    and any apparent effect there may be the changed denominator rather than
    the speakers.
    """
    evidence = analysis["evidence"]
    american = REFERENCES.index("american")
    british = REFERENCES.index("british")
    rows = {}
    for token in evidence.tokens:
        t = evidence.tokens.index(token)
        entry = {}
        for group in GROUPS:
            members = evidence.group_members(group)
            a = int(evidence.token_opportunities[american, t][members].sum())
            b = int(evidence.token_opportunities[british, t][members].sum())
            entry[group] = {
                "american_reference": a,
                "british_reference": b,
                "change": b - a,
                "relative_change": round((b - a) / a, 4) if a else None,
            }
        largest = max(
            abs(entry[group]["relative_change"] or 0.0) for group in GROUPS
        )
        entry["comparable_across_references"] = bool(largest <= 0.02)
        rows[token] = entry
    return {
        "rule": "A consonant is treated as comparable across references only when neither group's opportunity count moves by more than two percent. Above that the denominator itself changed and a cross reference difference cannot be attributed to the speakers.",
        "by_consonant": rows,
        "comparable": sorted(
            token for token, entry in rows.items()
            if entry["comparable_across_references"]
        ),
        "not_comparable": sorted(
            token for token, entry in rows.items()
            if not entry["comparable_across_references"]
        ),
    }
