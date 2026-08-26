"""Frozen rules and scoring primitives for the checkpoint 22E4 comparison.

Checkpoint 22E4 runs every eligible checkpoint 22E lane over the same frozen
participant-exclusive clips and asks one question of each: does it pass the
unchanged checkpoint 22D selection gates on the development adults and, again,
on the separate threshold-tuning adults?

Everything measured here is developer evidence. Nothing in this module can
establish pronunciation correctness, acceptable language variety, Australian
performance, scientific validity or product readiness, and a documented
no-selection is a correct completed outcome rather than a reason to search for a
weaker threshold.

The metric definitions are deliberately not reimplemented. Binary scoring reuses
``benchmark.score_binary_rows`` and the gates reuse
``benchmark_repair.selection_gate_results``, so a continuous candidate at one
threshold is measured by exactly the same code that measured the frozen 22D
baseline. ``tests/test_speech_sound_comparison.py`` reproduces the committed 22D
greedy numbers through this module to prove that.
"""

from __future__ import annotations

import json
import unicodedata
from collections import defaultdict
from pathlib import Path

from .benchmark import (
    PRIVATE_BENCHMARK_ROOT,
    align_phone_sequences,
    load_phone_map,
    ratio_record,
    score_binary_rows,
    strip_stress,
    target_predictions,
)
from .benchmark_repair import selection_gate_results
from .feasibility import REPOSITORY_ROOT, file_sha256


MODULE_ROOT = Path(__file__).parent

# Two frozen comparisons exist. Version 1.0.0 is checkpoint 22E4, the first look,
# and it is never edited or rerun. Version 1.1.0 is checkpoint 22E4B, the powered
# replication: the same rules, the same gates and the same candidates on the full
# non held-out adult pool. Everything that differs between them is data identity
# and file location, which is what this registry holds. Anything that would
# change a measurement is validated identically for both.
COMPARISON_VERSIONS = {
    "1.0.0": {
        "checkpoint": "22E4",
        "contract_path": MODULE_ROOT / "comparison-contract-v1.0.0.json",
        "report_path": MODULE_ROOT / "frozen-comparison-v1.0.0.json",
        "private_root": PRIVATE_BENCHMARK_ROOT / "comparison-v1",
        "sample_root": PRIVATE_BENCHMARK_ROOT / "v1",
        "secondary_clip_count": 85,
        "relation_path": (
            PRIVATE_BENCHMARK_ROOT
            / "v1"
            / "evidence"
            / "scoring"
            / "speechocean-relation-evidence.json"
        ),
        "expected_manifest_path": (
            PRIVATE_BENCHMARK_ROOT / "repair-v1" / "expected-only-manifest-v1.0.0.json"
        ),
        "benchmark_manifest_sha256": (
            "e856b2fef404cd28c9d09c6748797e1c6b888361c83c8d62f47ebf2560e03b98"
        ),
        "expected_only_manifest_sha256": (
            "c918feffa7c0a3a3fa99ce7a9e028621e8fb002980777297f30088e5975331da"
        ),
        "relation_evidence_sha256": (
            "571e04f1850e9889b9f5d0145765782162113b108bee6cfca6ed4e56ee344d96"
        ),
        "expected_only_clip_count": 480,
        "adult_scorable_counts": {"development": 1971, "threshold_tuning": 984},
        "extra_contract_fields": frozenset(),
        "transmitted_clips": 240,
    },
    "1.1.0": {
        "checkpoint": "22E4B",
        "contract_path": MODULE_ROOT / "comparison-contract-v1.1.0.json",
        "report_path": MODULE_ROOT / "frozen-comparison-v1.1.0.json",
        "private_root": PRIVATE_BENCHMARK_ROOT / "comparison-v2",
        "sample_root": PRIVATE_BENCHMARK_ROOT / "v2",
        "secondary_clip_count": 85,
        "relation_path": (
            PRIVATE_BENCHMARK_ROOT
            / "v2"
            / "evidence"
            / "scoring"
            / "speechocean-relation-evidence.json"
        ),
        "expected_manifest_path": (
            PRIVATE_BENCHMARK_ROOT / "v2" / "expected-only-manifest-v1.1.0.json"
        ),
        "benchmark_manifest_sha256": (
            "1b5599962c8ae9905dd740dcd6a91737dcf38b712492eb1fce9f3b6704f7ef30"
        ),
        "expected_only_manifest_sha256": (
            "a609994485db13e4d61b76c635459f26709bf8031f551de0c610a27b4816eace"
        ),
        "relation_evidence_sha256": (
            "34e4d1fcc725542583e22798a0b590ac01c0a2c6fdc3211cad008d8c5d83d564"
        ),
        "expected_only_clip_count": 2280,
        "adult_scorable_counts": {"development": 18565, "threshold_tuning": 5976},
        "extra_contract_fields": frozenset({"replication_declaration"}),
        "transmitted_clips": 2040,
    },
}

# The committed checkpoint 22E4 record stays this module's default, so every
# existing caller and test keeps guarding it unchanged. ACTIVE_VERSION is what
# checkpoint 22E4B runs.
DEFAULT_COMPARISON_VERSION = "1.0.0"
ACTIVE_COMPARISON_VERSION = "1.1.0"

COMPARISON_CONTRACT_PATH = COMPARISON_VERSIONS["1.0.0"]["contract_path"]
COMPARISON_REPORT_PATH = COMPARISON_VERSIONS["1.0.0"]["report_path"]
COMPARISON_SCHEMA_VERSION = "1.0.0"
CHECKPOINT = "22E4"

PRIVATE_COMPARISON_ROOT = COMPARISON_VERSIONS["1.0.0"]["private_root"]
RELATION_PATH = COMPARISON_VERSIONS["1.0.0"]["relation_path"]
EXPECTED_MANIFEST_PATH = COMPARISON_VERSIONS["1.0.0"]["expected_manifest_path"]

FROZEN_EXPECTED_MANIFEST_SHA256 = COMPARISON_VERSIONS["1.0.0"][
    "expected_only_manifest_sha256"
]
FROZEN_RELATION_EVIDENCE_SHA256 = COMPARISON_VERSIONS["1.0.0"][
    "relation_evidence_sha256"
]
FROZEN_BENCHMARK_MANIFEST_SHA256 = COMPARISON_VERSIONS["1.0.0"][
    "benchmark_manifest_sha256"
]


def comparison_profile(version=DEFAULT_COMPARISON_VERSION):
    """Return the frozen identity and file locations for one comparison version."""
    profile = COMPARISON_VERSIONS.get(version)
    if profile is None:
        raise ComparisonError(f"unknown comparison version: {version!r}")
    return profile

# The five gates are inherited unchanged from the frozen 22D exact-threshold
# contract. 22E4 has no authority to move any of them.
FROZEN_SELECTION_GATES = {
    "minimum_precision_point_estimate": 0.75,
    "minimum_precision_wilson_95_lower": 0.5,
    "maximum_false_concerns_per_scorable_opportunity": 0.01,
    "minimum_recall": 0.2,
    "minimum_true_positives": 7,
}

# Adult opportunity counts in the frozen sample. Recorded so a silent change to
# the private truth file or the manifest cannot pass unnoticed.
ADULT_SCORABLE_COUNTS = COMPARISON_VERSIONS["1.0.0"]["adult_scorable_counts"]

# Every field a comparison contract must carry, in every version.
BASE_CONTRACT_FIELDS = frozenset(
    {
        "schema_version",
        "comparison_id",
        "checkpoint",
        "status",
        "declared_before_any_run",
        "purpose",
        "frozen_inputs",
        "input_policy",
        "truth_policy",
        "selection_gates",
        "threshold_policy",
        "alignment_policy",
        "candidates",
        "baseline_reference",
        "excluded_lanes",
        "external_transmission_policy",
        "prohibited_inputs_and_outputs",
        "report_policy",
        "release_boundaries",
        "acceptance",
    }
)

RELEASE_BOUNDARIES = {
    "normal_pipeline",
    "candidate_artifact",
    "coaching",
    "personal_progress",
    "scientific_release",
    "product_release",
    "screening",
    "diagnosis",
    "severity",
    "cause",
    "treatment",
}

PROHIBITED_PROVIDER_SCORES = {
    "PronScore",
    "FluencyScore",
    "CompletenessScore",
    "ProsodyScore",
}

# Every candidate the approved plan permits in this checkpoint, with the role it
# must keep. A contract that adds, drops or re-purposes a candidate fails.
CANDIDATE_PROFILES = {
    "sfgop_af": {
        "lane_id": "segmentation_free_gop",
        "decision_rule": "continuous_threshold",
        "selection_eligible": True,
        "exact_relation_capable": False,
    },
    "sfgop_af_sd": {
        "lane_id": "segmentation_free_gop",
        "decision_rule": "continuous_threshold",
        "selection_eligible": True,
        "exact_relation_capable": False,
    },
    "powsm_free_phone_relation": {
        "lane_id": "powsm",
        "decision_rule": "binary_alignment_relation",
        "selection_eligible": True,
        "exact_relation_capable": True,
    },
    "azure_en_us_phone_score": {
        "lane_id": "azure_speech",
        "decision_rule": "continuous_threshold",
        "selection_eligible": True,
        "exact_relation_capable": False,
    },
    "azure_en_us_named_relation": {
        "lane_id": "azure_speech",
        "decision_rule": (
            "binary_named_candidate_differs_from_provider_expected_phone"
        ),
        "selection_eligible": True,
        "exact_relation_capable": True,
    },
    "azure_en_au_phone_score": {
        "lane_id": "azure_speech",
        "decision_rule": "continuous_threshold",
        "selection_eligible": True,
        "exact_relation_capable": False,
    },
    "wav2vec2_commonphone_free_phone_relation": {
        "lane_id": "wav2vec2_commonphone",
        "decision_rule": "binary_alignment_relation",
        "selection_eligible": False,
        "exact_relation_capable": True,
    },
}

CONTINUOUS_CANDIDATES = {
    candidate_id
    for candidate_id, profile in CANDIDATE_PROFILES.items()
    if profile["decision_rule"] == "continuous_threshold"
}

EXCLUDED_LANE_IDS = {
    "elsa_scripted_v3",
    "iflytek_ise_global",
    "zipa",
    "unsw_speech_attributes",
    "child_phoneme_model",
    "auskidtalk",
    "bookbot_au_g2p",
    "soapbox",
    "speechace",
    "speechsuper",
}

# The closest reported operating point when nothing passes. Copied verbatim from
# the 22D repair so a failing candidate is described the same way it was then.
CLOSEST_POINT_RULE = (
    "most frozen gate checks passed, then highest worst partition precision, "
    "then recall, then fewest false positives"
)

SCORE_ROUNDING = 9


class ComparisonError(RuntimeError):
    """Raised when checkpoint 22E4 evidence cannot be trusted."""


def _load_json(path):
    path = Path(path)
    if not path.is_file():
        raise ComparisonError(f"comparison evidence is missing: {path.name}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_comparison_contract(path=None, version=DEFAULT_COMPARISON_VERSION):
    if path is None:
        path = comparison_profile(version)["contract_path"]
    return _load_json(path)


def validate_comparison_contract(document, version=None):
    """Return every structural or safety error in the frozen comparison rules.

    The version is read from the document itself unless one is given, so the
    checkpoint 22E4 record and the checkpoint 22E4B replication are both held to
    their own frozen input identity and to the identical safety rules.
    """
    errors = []
    if not isinstance(document, dict):
        return ["comparison contract must be an object"]
    if version is None:
        version = document.get("schema_version")
    if version not in COMPARISON_VERSIONS:
        return ["comparison contract schema is unsupported"]
    profile = COMPARISON_VERSIONS[version]
    required = set(BASE_CONTRACT_FIELDS | profile["extra_contract_fields"])
    if set(document) != required:
        errors.append("comparison contract fields do not match the frozen schema")
        if not required.issubset(document):
            return errors

    if document["checkpoint"] != profile["checkpoint"]:
        errors.append(
            f"comparison contract checkpoint must be {profile['checkpoint']}"
        )
    if document["status"] != "rules_frozen_before_any_lane_scoring":
        errors.append("comparison rules must remain frozen before lane scoring")
    if document["declared_before_any_run"] is not True:
        errors.append(
            "the comparison contract is only meaningful if it was declared "
            "before any lane ran"
        )

    frozen = document["frozen_inputs"]
    for field, expected in (
        (
            "private_benchmark_manifest_sha256",
            profile["benchmark_manifest_sha256"],
        ),
        (
            "expected_only_manifest_sha256",
            profile["expected_only_manifest_sha256"],
        ),
        ("relation_evidence_sha256", profile["relation_evidence_sha256"]),
        ("expected_only_clip_count", profile["expected_only_clip_count"]),
    ):
        if frozen.get(field) != expected:
            errors.append(f"frozen_inputs.{field} changed")
    if frozen.get("frozen_inputs_may_be_rewritten") is not False:
        errors.append("frozen_inputs_may_be_rewritten must remain false")

    inputs = document["input_policy"]
    if set(inputs.get("allowed_project_splits", [])) != {
        "development",
        "threshold_tuning",
    }:
        errors.append("comparison inputs must remain development and tuning only")
    if inputs.get("gate_population") != "source_adults_only":
        errors.append("the frozen gates remain adult only")
    if inputs.get("same_input_repeats") != 2:
        errors.append("two exact repeats per input are required")
    if inputs.get("repeat_numeric_tolerance") != 0.0:
        errors.append(
            "no numeric tolerance may be granted for an identical repeated input"
        )
    for field in (
        "child_rows_used_for_selection_or_thresholds",
        "held_out_access_allowed",
        "candidate_runner_may_read_expert_outcomes",
        "secondary_source_evidence_may_enter_selection_gates",
    ):
        if inputs.get(field) is not False:
            errors.append(f"input_policy.{field} must remain false")
    if inputs.get(
        "expert_outcome_read_only_after_every_candidate_output_is_complete"
    ) is not True:
        errors.append(
            "expert outcomes may be read only after every candidate output is "
            "complete"
        )

    truth = document["truth_policy"]
    if truth.get("source_id") != "speechocean762":
        errors.append("the gate truth source must remain speechocean762")
    for field in (
        "model_output_is_reference_truth",
        "cross_system_agreement_is_confirmation",
        "reviewer_records_overwritten_by_consensus",
    ):
        if truth.get(field) is not False:
            errors.append(f"truth_policy.{field} must remain false")
    if truth.get("unscorable_rows_excluded_from_every_metric") is not True:
        errors.append("unscorable reference rows must stay out of every metric")

    gates = document["selection_gates"]
    for field, expected in FROZEN_SELECTION_GATES.items():
        if gates.get(field) != expected:
            errors.append(f"selection_gates.{field} changed")
    if gates.get("development_and_tuning_both_required") is not True:
        errors.append("both partitions must still be required")
    for field in (
        "gates_may_be_changed_in_this_checkpoint",
        "expert_agreement_band_may_lower_a_gate",
    ):
        if gates.get(field) is not False:
            errors.append(f"selection_gates.{field} must remain false")

    thresholds = document["threshold_policy"]
    if thresholds.get("positive_comparison") != (
        "concern_score_greater_than_or_equal_to_threshold"
    ):
        errors.append("the threshold comparison direction changed")
    if thresholds.get("selection") != (
        "highest tuning recall meeting every development and tuning gate, then "
        "highest tuning precision, then highest threshold"
    ):
        errors.append("the predeclared threshold selection procedure changed")
    if thresholds.get("closest_point_reporting_rule") != CLOSEST_POINT_RULE:
        errors.append("the closest point reporting rule changed")
    for field in (
        "candidate_thresholds_use_labels",
        "model_fitted_on_labels",
        "features_or_scores_may_be_recomputed_after_seeing_labels",
        "held_out_labels_or_outputs_used",
    ):
        if thresholds.get(field) is not False:
            errors.append(f"threshold_policy.{field} must remain false")
    for field in (
        "development_and_tuning_both_must_pass",
        "closest_point_is_not_a_selection",
    ):
        if thresholds.get(field) is not True:
            errors.append(f"threshold_policy.{field} must remain true")

    alignment = document["alignment_policy"]
    free = alignment.get("free_phone_lanes", {})
    if free.get("algorithm") != "deterministic_unit_cost_levenshtein":
        errors.append("the frozen alignment algorithm changed")
    if free.get("weighted_panphon_distance_used") is not False:
        errors.append("weighted PanPhon distance remains disabled")
    for field in (
        "out_of_inventory_observed_token_behavior",
        "unsupported_candidate_detail_behavior",
        "insertion_only_alignment_behavior",
    ):
        if free.get(field) != "abstain":
            errors.append(f"free_phone_lanes.{field} must remain abstain")
    external = alignment.get("external_score_lanes", {})
    if external.get("locales_pooled") is not False:
        errors.append("provider locales are separate models and are never pooled")
    for field in ("reference_disagreement_behavior", "missing_word_or_phone_behavior"):
        if external.get(field) != "abstain":
            errors.append(f"external_score_lanes.{field} must remain abstain")

    candidates = document["candidates"]
    if not isinstance(candidates, list):
        errors.append("candidates must be a list")
        return errors
    seen = {}
    for candidate in candidates:
        candidate_id = candidate.get("candidate_id")
        profile = CANDIDATE_PROFILES.get(candidate_id)
        if profile is None:
            errors.append(
                f"{candidate_id!r} is not a candidate the approved plan permits"
            )
            continue
        if candidate_id in seen:
            errors.append(f"{candidate_id!r} is declared twice")
        seen[candidate_id] = candidate
        for field, expected in profile.items():
            if candidate.get(field) != expected:
                errors.append(
                    f"{candidate_id}: {field} is {candidate.get(field)!r} but the "
                    f"approved plan requires {expected!r}"
                )
        if candidate.get("independent_of_truth_source") is not True:
            errors.append(
                f"{candidate_id}: a candidate trained on the truth source cannot "
                "be measured against it"
            )
        if profile["selection_eligible"] is False and candidate.get(
            "gates_evaluated"
        ) is not False:
            errors.append(
                f"{candidate_id}: a supporting only candidate must not carry gate "
                "results"
            )
    missing = set(CANDIDATE_PROFILES) - set(seen)
    if missing:
        errors.append(
            "comparison contract is missing candidates: " + ", ".join(sorted(missing))
        )

    excluded = {item.get("lane_id") for item in document["excluded_lanes"]}
    if excluded != EXCLUDED_LANE_IDS:
        errors.append(
            "every lane outside the comparison must be listed with its reason"
        )
    if any(
        item.get("audio_sent") is not False for item in document["excluded_lanes"]
    ):
        errors.append("an excluded lane cannot have received audio")

    transmission = document["external_transmission_policy"]
    if transmission.get("lane_id") != "azure_speech":
        errors.append("azure_speech is the only lane permitted to receive audio")
    if transmission.get("source_id") != "speechocean762":
        errors.append("speechocean762 is the only source permitted to be sent")
    if set(transmission.get("permitted_strata", [])) != {
        "source_adult_f",
        "source_adult_m",
    }:
        errors.append("only adult strata may be transmitted")
    for field in (
        "child_strata_transmitted",
        "held_out_clips_transmitted",
        "owner_or_personal_audio_transmitted",
        "australian_common_voice_transmitted",
    ):
        if transmission.get(field) is not False:
            errors.append(f"external_transmission_policy.{field} must remain false")

    prohibited = set(document["prohibited_inputs_and_outputs"])
    for key in sorted(PROHIBITED_PROVIDER_SCORES):
        if key not in prohibited:
            errors.append(f"prohibited_inputs_and_outputs must retain {key}")

    report = document["report_policy"]
    for field in (
        "committed_report_aggregate_only",
        "development_and_tuning_separate",
        "adult_and_child_separate",
        "locales_separate",
        "evidence_classes_separate",
        "visible_denominators",
        "coverage_abstention_and_failure_required",
        "baseline_comparison_required",
        "limitations_required",
    ):
        if report.get(field) is not True:
            errors.append(f"report_policy.{field} must remain true")
    for field in (
        "private_rows_committed",
        "held_out_fields_allowed",
        "one_combined_headline_score_allowed",
    ):
        if report.get(field) is not False:
            errors.append(f"report_policy.{field} must remain false")

    boundaries = document["release_boundaries"]
    if set(boundaries) != RELEASE_BOUNDARIES or any(
        boundaries.get(field) is not False for field in RELEASE_BOUNDARIES
    ):
        errors.append("every comparison release boundary must remain false")

    acceptance = document["acceptance"]
    if acceptance.get("documented_no_selection_is_a_valid_outcome") is not True:
        errors.append("a documented no-selection must remain a valid outcome")
    for field in (
        "all_denominators_and_failures_visible",
        "no_held_out_participant_or_label_accessed",
        "no_provider_output_becomes_reference_truth",
    ):
        if acceptance.get(field) is not True:
            errors.append(f"acceptance.{field} must remain true")

    if "replication_declaration" in required:
        errors.extend(_replication_errors(document))
    return errors


def _replication_errors(document):
    """Rules that only a replication of an earlier frozen comparison must keep."""
    errors = []
    declaration = document["replication_declaration"]
    for field in (
        "replaces_an_underpowered_estimate",
        "whatever_this_produces_is_the_reported_result",
        "a_retry_until_something_passes_is_prohibited",
        "version_1_0_0_remains_the_record_of_the_first_look",
    ):
        if declaration.get(field) is not True:
            errors.append(f"replication_declaration.{field} must remain true")
    if declaration.get("version_1_0_0_files_edited") is not False:
        errors.append(
            "the superseded comparison version must not have been edited"
        )
    unchanged = set(declaration.get("what_did_not_change", []))
    for required_claim in (
        "every selection gate",
        "the threshold search and selection procedure",
        "the closest point reporting rule",
        "the truth definition, the four of five consensus and the unscorable scope",
        "the split assignments and the sealed held out participants",
        "the two exact repeats and the zero numeric tolerance",
    ):
        if required_claim not in unchanged:
            errors.append(
                f"replication_declaration must still declare unchanged: {required_claim}"
            )
    if document["acceptance"].get("gates_unchanged") is not True:
        errors.append("acceptance.gates_unchanged must remain true")
    if document["acceptance"].get("single_reported_run") is not True:
        errors.append("acceptance.single_reported_run must remain true")
    report = document["report_policy"]
    for field in (
        "checkpoint_22e4_comparison_required",
        "explicit_statement_whether_the_near_miss_survived_required",
    ):
        if report.get(field) is not True:
            errors.append(f"report_policy.{field} must remain true")
    return errors


def assert_valid_comparison_contract(
    document=None, version=DEFAULT_COMPARISON_VERSION
):
    if document is None:
        document = load_comparison_contract(version=version)
    errors = validate_comparison_contract(document)
    if errors:
        checkpoint = COMPARISON_VERSIONS.get(
            document.get("schema_version"), {}
        ).get("checkpoint", "unknown checkpoint")
        raise ComparisonError(
            f"{checkpoint} comparison contract failed fail-closed validation:\n- "
            + "\n- ".join(errors)
        )
    return document


def verify_frozen_inputs(contract=None, version=DEFAULT_COMPARISON_VERSION):
    """Confirm the private truth and label-blind input files are unchanged."""
    contract = assert_valid_comparison_contract(contract, version)
    profile = comparison_profile(contract["schema_version"])
    frozen = contract["frozen_inputs"]
    for path, expected, name in (
        (
            profile["expected_manifest_path"],
            frozen["expected_only_manifest_sha256"],
            "expected-only manifest",
        ),
        (
            profile["relation_path"],
            frozen["relation_evidence_sha256"],
            "expert relation evidence",
        ),
    ):
        if file_sha256(path) != expected:
            raise ComparisonError(f"{name} no longer matches its frozen hash")
    return contract


# --------------------------------------------------------------------------
# Phone inventory and normalization
# --------------------------------------------------------------------------

_COMBINING_TO_STRIP = {
    "͡",  # combining double inverted breve, the IPA tie bar
    "͜",  # combining double breve below
    "ː",  # length mark
    "ˈ",  # primary stress
    "ˌ",  # secondary stress
    "̆",  # breve, used by some IPA renderings of non-syllabic parts
}


def normalized_ipa(token):
    """Normalize one IPA string for provider reference comparison.

    Providers publish their own lexicons, so the same phone can arrive with a
    tie bar, a length mark or a stress mark this project does not use. Removing
    those marks compares the phone, not its typography. It never merges two
    different phones: only the marks listed above are removed.
    """
    if not isinstance(token, str):
        raise ComparisonError("a provider phone name must be text")
    decomposed = unicodedata.normalize("NFD", token)
    return "".join(
        character
        for character in decomposed
        if character not in _COMBINING_TO_STRIP
    )


def reference_ipa_string(arpabet, phone_map):
    """Return the normalized IPA string this project expects for one ARPAbet."""
    base = strip_stress(arpabet)
    mapping = phone_map["reference_phones"].get(base)
    if mapping is None:
        raise ComparisonError(f"unmapped reference phone: {base}")
    return normalized_ipa("".join(mapping["ipa"]))


def candidate_inventory(phone_map):
    """Every observed token this project can interpret at all.

    The frozen phone map states that an unknown candidate phone is unscorable.
    A free-phone model has no fixed inventory, so this set is what makes that
    rule enforceable: a target aligned to a token outside it abstains rather
    than becoming a concern nobody can interpret.
    """
    tokens = set()
    for mapping in phone_map["reference_phones"].values():
        for token in mapping["ipa"]:
            tokens.add(unicodedata.normalize("NFD", token))
    for token in phone_map["declared_equivalents"]:
        tokens.add(unicodedata.normalize("NFD", token))
    for token in phone_map["unsupported_candidate_details"]:
        tokens.add(unicodedata.normalize("NFD", token))
    return tokens


# --------------------------------------------------------------------------
# Per candidate row construction
# --------------------------------------------------------------------------


def free_phone_target_states(clip, observed_tokens, phone_map, inventory):
    """Per target relation states for one unconstrained free-phone output.

    The alignment itself is the frozen 22D aligner, unchanged. The one addition
    declared by the 22E4 contract is the out-of-inventory rule: a target that
    aligns to a token this project cannot interpret abstains, because calling it
    a substitution would invent a relation from an unreadable symbol.
    """
    word_starts = set(clip["word_starts"])
    predictions = target_predictions(
        clip["reference_phones"], observed_tokens, phone_map, word_starts
    )
    states = {}
    for prediction in predictions["targets"]:
        state = prediction["state"]
        reason = prediction.get("reason")
        observed = prediction.get("observed_phone")
        if state != "abstain" and observed is not None:
            if unicodedata.normalize("NFD", observed) not in inventory:
                state = "abstain"
                reason = "out_of_inventory_candidate_token"
        states[prediction["target_index"]] = {
            "state": state,
            "relation_type": prediction.get("relation_type"),
            "observed_phone": observed,
            "reason": reason,
        }
    return states


_BARE_ALIGNER_MAP = {
    "special_nonphones": [],
    "unsupported_candidate_details": {},
    "declared_equivalents": {},
}


def comparable_word(word):
    """Compare words by their letters alone, ignoring case and punctuation."""
    if not isinstance(word, str):
        return ""
    return "".join(
        character for character in word.casefold() if character.isalnum()
    )


def provider_word_alignment(reference_words, provider_words):
    """Map reference word positions to provider word positions.

    The provider's word list is not this project's word list. With miscue
    detection enabled it inserts words the speaker said but the reference does
    not contain, which shifts every position after them, so matching by index
    would quietly score the wrong word. Inserted words are dropped first, then
    the remaining sequence is aligned by the same deterministic algorithm used
    everywhere else. A reference word that does not match one to one is absent
    from the result, and the caller abstains for all of its targets.
    """
    kept = [
        (position, word)
        for position, word in enumerate(provider_words)
        if word.get("error_type") != "Insertion"
    ]
    expected_items = [
        {"token": comparable_word(word) or "<empty_reference_word>"}
        for word in reference_words
    ]
    observed = [
        comparable_word(word.get("word")) or "<empty_provider_word>"
        for _, word in kept
    ]
    aligned = align_phone_sequences(expected_items, observed, _BARE_ALIGNER_MAP)
    matched = {}
    for operation in aligned["operations"]:
        if operation["kind"] != "match":
            continue
        matched[operation["expected_index"]] = kept[operation["observed_index"]][0]
    return matched


def azure_word_alignment(reference_arpabet, provider_phones, phone_map):
    """Align one word's reference phones against a provider's expected phones.

    Returns a mapping from this project's local phone index to the provider
    position that carries the same expected phone. Positions where the two
    lexicons disagree, or where the alignment is not one to one, are simply
    absent, which the caller turns into an abstention. A provider that expects a
    different phone was not scoring this project's target.
    """
    expected_items = [
        {"token": reference_ipa_string(phone, phone_map)}
        for phone in reference_arpabet
    ]
    observed = [normalized_ipa(phone) for phone in provider_phones]
    # A provider phone name may legitimately be empty, as the en-AU locale
    # emits. An empty string can never equal a reference phone, so it aligns as
    # a substitution and the target abstains.
    aligned = align_phone_sequences(
        expected_items,
        [
            token if token else "<empty_provider_phone_name>"
            for token in observed
        ],
        _BARE_ALIGNER_MAP,
    )
    matched = {}
    for operation in aligned["operations"]:
        if operation["kind"] != "match":
            continue
        matched[operation["expected_index"]] = operation["observed_index"]
    return matched


# --------------------------------------------------------------------------
# Metrics, thresholds and gates
# --------------------------------------------------------------------------


def partition_metrics(rows, gates=None):
    """Score one partition with the frozen binary scorer and the frozen gates."""
    gates = gates or FROZEN_SELECTION_GATES
    metrics = score_binary_rows(
        [{"truth": row["truth"], "prediction": row["prediction"]} for row in rows]
    )
    metrics["selection_gates"] = selection_gate_results(metrics, gates)
    return metrics


def participant_metrics(rows):
    """Report every participant separately, never pooled into one number."""
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["private_participant_id"]].append(row)
    return [
        {
            "private_participant_id": participant_id,
            **score_binary_rows(
                [
                    {"truth": row["truth"], "prediction": row["prediction"]}
                    for row in grouped[participant_id]
                ]
            ),
        }
        for participant_id in sorted(grouped)
    ]


def _decided(row, threshold):
    if row["state"] != "scored":
        return "abstain"
    return "positive" if row["concern_score"] >= threshold else "negative"


def predictions_at_threshold(rows, threshold):
    return [{**row, "prediction": _decided(row, threshold)} for row in rows]


def candidate_thresholds(*row_groups):
    """Every distinct observed concern score, plus one point above the maximum.

    Including a point above the maximum guarantees the empty positive set is
    examined, so a candidate that only passes by predicting nothing is visible
    rather than hidden by the grid.
    """
    scores = sorted(
        {
            row["concern_score"]
            for rows in row_groups
            for row in _scorable(rows)
            if row["state"] == "scored"
        }
    )
    if not scores:
        return []
    return scores + [round(scores[-1] + 1.0, SCORE_ROUNDING)]


def _gate_check_count(record):
    return sum(
        1
        for partition in ("development", "threshold_tuning")
        for passed in record[partition]["selection_gates"]["checks"].values()
        if passed
    )


def _worst_partition_value(record, name):
    values = []
    for partition in ("development", "threshold_tuning"):
        value = record[partition][name]["value"]
        values.append(-1.0 if value is None else value)
    return min(values)


def threshold_search(development_rows, tuning_rows, gates=None):
    """Evaluate every candidate threshold under the predeclared procedure."""
    gates = gates or FROZEN_SELECTION_GATES
    records = []
    for threshold in candidate_thresholds(development_rows, tuning_rows):
        development = partition_metrics(
            predictions_at_threshold(development_rows, threshold), gates
        )
        tuning = partition_metrics(
            predictions_at_threshold(tuning_rows, threshold), gates
        )
        records.append(
            {
                "threshold": threshold,
                "development": development,
                "threshold_tuning": tuning,
                "both_partitions_pass": (
                    development["selection_gates"]["passed"]
                    and tuning["selection_gates"]["passed"]
                ),
            }
        )
    eligible = [record for record in records if record["both_partitions_pass"]]
    selected = None
    if eligible:
        selected = min(
            eligible,
            key=lambda record: (
                -(
                    record["threshold_tuning"]["recall"]["value"]
                    if record["threshold_tuning"]["recall"]["value"] is not None
                    else -1
                ),
                -(
                    record["threshold_tuning"]["precision"]["value"]
                    if record["threshold_tuning"]["precision"]["value"] is not None
                    else -1
                ),
                -record["threshold"],
            ),
        )
    closest = None
    if records:
        closest = min(
            records,
            key=lambda record: (
                -_gate_check_count(record),
                -_worst_partition_value(record, "precision"),
                -_worst_partition_value(record, "recall"),
                record["development"]["false_positive"]
                + record["threshold_tuning"]["false_positive"],
                -record["threshold"],
            ),
        )
    return {
        "candidate_threshold_count": len(records),
        "records": records,
        "selected": selected,
        "closest": closest,
        "closest_point_reporting_rule": CLOSEST_POINT_RULE,
    }


def average_precision(rows):
    """Ranking quality of a continuous concern score, gates aside.

    This is descriptive only. It cannot pass a gate, and a candidate that ranks
    well while failing every operating point has not earned anything.
    """
    scored = [row for row in _scorable(rows) if row["state"] == "scored"]
    if not scored:
        return None
    positives = sum(1 for row in scored if row["label"] == 1)
    if positives == 0:
        return None
    ordered = sorted(scored, key=lambda row: (-row["concern_score"],))
    seen = 0
    hits = 0
    total = 0.0
    previous_score = None
    pending = []
    for row in ordered:
        # Ties share one operating point, so they are consumed together.
        if previous_score is not None and row["concern_score"] != previous_score:
            seen, hits, total = _consume_tie(pending, seen, hits, total)
            pending = []
        pending.append(row)
        previous_score = row["concern_score"]
    seen, hits, total = _consume_tie(pending, seen, hits, total)
    return round(total / positives, 9)


def _consume_tie(pending, seen, hits, total):
    if not pending:
        return seen, hits, total
    seen += len(pending)
    tie_hits = sum(1 for row in pending if row["label"] == 1)
    hits += tie_hits
    if tie_hits:
        total += tie_hits * (hits / seen)
    return seen, hits, total


def _scorable(rows):
    """Rows the reference can judge at all.

    A target the five expert reviewers left disputed or out of scope is not an
    opportunity for anyone. It is excluded here for exactly the same reason the
    frozen scorer excludes it from every denominator, so coverage and ranking
    describe the same population the gates do.
    """
    return [row for row in rows if row.get("truth") != "unscorable"]


def coverage_record(rows):
    """Availability of one candidate over the rows it was asked to judge."""
    rows = _scorable(rows)
    scored = sum(1 for row in rows if row["state"] == "scored")
    return {
        "reference_scorable_opportunities": len(rows),
        "scored": scored,
        "abstained": len(rows) - scored,
        "coverage": ratio_record(scored, len(rows)),
        "abstention_reasons": _reason_counts(rows),
    }


def _reason_counts(rows):
    counts = defaultdict(int)
    for row in rows:
        if row["state"] == "scored":
            continue
        counts[row.get("abstention_reason") or "unrecorded"] += 1
    return dict(sorted(counts.items()))


def load_relation_rows(relation_path=None, version=DEFAULT_COMPARISON_VERSION):
    """Load the frozen expert relation truth, refusing held-out evidence."""
    profile = comparison_profile(version)
    if relation_path is None:
        relation_path = profile["relation_path"]
    document = _load_json(relation_path)
    if document.get("held_out_evaluation") is not False:
        raise ComparisonError("the relation evidence claims held-out evaluation")
    if document.get("private_benchmark_manifest_sha256") != (
        profile["benchmark_manifest_sha256"]
    ):
        raise ComparisonError("the relation evidence belongs to another benchmark")
    return document["target_rows"]


def load_expected_manifest(path=None, version=DEFAULT_COMPARISON_VERSION):
    profile = comparison_profile(version)
    if path is None:
        path = profile["expected_manifest_path"]
    document = _load_json(path)
    if document.get("expert_outcomes_included") is not False:
        raise ComparisonError("the candidate input manifest is not label blind")
    if document.get("held_out_participants") != 0:
        raise ComparisonError("the candidate input manifest holds held-out clips")
    if len(document["clips"]) != profile["expected_only_clip_count"]:
        raise ComparisonError("the candidate input manifest changed size")
    return document


FORBIDDEN_REPORT_KEYS = {
    "safe_id",
    "private_participant_id",
    "private_utterance_id",
    "private_record_id",
    "canonical_audio_path",
    "canonical_audio_sha256",
    "output_path",
    "threshold_grid",
    "private_details",
    "participants",
    "observation",
    "phones",
    "nbest",
    "logits",
    "logits_sha256",
    "reference_phones",
    "word_index",
    "target_index",
    "concern_score",
    "audio",
}


def validate_comparison_report(document, version=None):
    """Reject private evidence, weakened gates or an unsupported claim.

    Like the contract validator, the version is read from the document unless one
    is given, so both frozen comparisons are held to their own sample identity
    and to the identical safety rules.
    """
    errors = []
    required = {
        "schema_version",
        "report_id",
        "report_version",
        "checkpoint",
        "status",
        "purpose",
        "comparison_contract_sha256",
        "sample",
        "selection_gates",
        "candidates",
        "baseline_comparison",
        "secondary_source_evidence",
        "runtime_and_cost",
        "excluded_lanes",
        "external_transmission",
        "decision",
        "private_evidence",
        "limitations",
        "release_boundaries",
        "next_checkpoint",
    }
    if not isinstance(document, dict):
        return ["comparison report must be an object"]
    if set(document) != required:
        errors.append("comparison report fields do not match the aggregate schema")
        if not required.issubset(document):
            return errors

    if version is None:
        version = document.get("schema_version")
    if version not in COMPARISON_VERSIONS:
        errors.append("comparison report schema is unsupported")
        return errors
    version_profile = COMPARISON_VERSIONS[version]
    checkpoint = version_profile["checkpoint"]
    if document["checkpoint"] != checkpoint:
        errors.append(f"comparison report checkpoint must be {checkpoint}")
    if document["status"] != "frozen_comparison_complete_release_locked":
        errors.append("comparison report must remain release locked")

    counts = version_profile["adult_scorable_counts"]
    sample = document["sample"]
    for field, expected in (
        ("clips", version_profile["expected_only_clip_count"]),
        ("gate_population", "source_adults_only"),
        ("development_adult_scorable_opportunities", counts["development"]),
        (
            "threshold_tuning_adult_scorable_opportunities",
            counts["threshold_tuning"],
        ),
        ("held_out_participants", 0),
        ("expert_outcomes_read_by_candidate_runners", False),
        ("same_input_repeats", 2),
    ):
        if sample.get(field) != expected:
            errors.append(f"comparison report sample.{field} changed")

    gates = document["selection_gates"]
    for field, expected in FROZEN_SELECTION_GATES.items():
        if gates.get(field) != expected:
            errors.append(f"comparison report selection_gates.{field} changed")
    if gates.get("development_and_tuning_both_required") is not True:
        errors.append("both partitions must still be required")
    if gates.get("inherited_unchanged_from_checkpoint_22d") is not True:
        errors.append("the report must state that the gates were inherited unchanged")

    candidates = document["candidates"]
    reported = {candidate.get("candidate_id") for candidate in candidates}
    if reported != set(CANDIDATE_PROFILES):
        errors.append("every approved candidate must appear in the report")
    passing = []
    for candidate in candidates:
        candidate_id = candidate.get("candidate_id")
        profile = CANDIDATE_PROFILES.get(candidate_id)
        if profile is None:
            continue
        if candidate.get("selection_eligible") != profile["selection_eligible"]:
            errors.append(f"{candidate_id}: selection eligibility changed")
        if candidate.get("exact_relation_capable") != profile[
            "exact_relation_capable"
        ]:
            errors.append(f"{candidate_id}: exact relation capability changed")
        point = candidate.get("reported_operating_point")
        if profile["selection_eligible"] is False:
            if candidate.get("gates_evaluated") is not False:
                errors.append(
                    f"{candidate_id}: a supporting only candidate cannot be gated"
                )
            if candidate.get("any_operating_point_passes_both_partitions") is not None:
                errors.append(
                    f"{candidate_id}: a supporting only candidate cannot report a "
                    "gate outcome"
                )
            if point and (
                "selection_gates" in point.get("development", {})
                or "selection_gates" in point.get("threshold_tuning", {})
            ):
                errors.append(
                    f"{candidate_id}: a supporting only candidate cannot carry gate "
                    "results"
                )
            continue
        if candidate.get("any_operating_point_passes_both_partitions") is True:
            passing.append(candidate_id)
        if point is not None and point.get("is_a_selection") is True and candidate.get(
            "any_operating_point_passes_both_partitions"
        ) is not True:
            errors.append(
                f"{candidate_id}: an operating point cannot be a selection unless "
                "both partitions passed"
            )

    decision = document["decision"]
    if decision.get("selection_recorded_in_this_checkpoint") is not False:
        errors.append(
            f"checkpoint {checkpoint} measures; the selection record is 22E5"
        )
    if decision.get("gates_changed_in_this_checkpoint") is not False:
        errors.append("the gates cannot have changed in this checkpoint")
    if decision.get("no_selection_is_a_valid_completed_outcome") is not True:
        errors.append("a documented no-selection must remain a valid outcome")
    if sorted(decision.get("candidates_passing_every_unchanged_gate", [])) != sorted(
        passing
    ):
        errors.append("the decision does not match the reported candidate outcomes")
    if not passing and decision.get("decision") != "no_selection":
        errors.append("no candidate passed, so the decision must be no_selection")
    for field in (
        "children_supported",
        "insertions_supported",
        "australian_variety_exact_relation_evidence_available",
    ):
        if decision.get(field) is not False:
            errors.append(f"decision.{field} must remain false")

    transmission = document["external_transmission"]
    for field in (
        "child_strata_transmitted",
        "held_out_clips_transmitted",
        "owner_or_personal_audio_transmitted",
        "australian_common_voice_transmitted",
    ):
        if transmission.get(field) is not False:
            errors.append(f"external_transmission.{field} must remain false")

    if document["private_evidence"].get("raw_or_row_level_evidence_committed") is not (
        False
    ):
        errors.append("row level evidence must stay private")
    if document["private_evidence"].get("provider_responses_committed") is not False:
        errors.append("provider responses must stay private")

    if not document["limitations"]:
        errors.append("the report must carry its limitations")

    boundaries = document["release_boundaries"]
    if set(boundaries) != RELEASE_BOUNDARIES or any(
        boundaries.get(field) is not False for field in RELEASE_BOUNDARIES
    ):
        errors.append("every comparison release boundary must remain false")
    if document["next_checkpoint"] != (
        "22E5_selection_and_rejection_record_after_owner_commit"
    ):
        errors.append("the next checkpoint bypasses owner approval")

    serialized = json.dumps(document, ensure_ascii=False)
    for key in sorted(PROHIBITED_PROVIDER_SCORES):
        if key in serialized:
            errors.append(f"{key} is a prohibited output class and cannot be reported")

    def inspect(value):
        if isinstance(value, dict):
            if FORBIDDEN_REPORT_KEYS & set(value):
                return False
            return all(inspect(item) for item in value.values())
        if isinstance(value, list):
            return all(inspect(item) for item in value)
        return True

    if not inspect(document):
        errors.append("comparison report contains private or row-level evidence")
    return errors


def private_root(subdirectory=None, version=DEFAULT_COMPARISON_VERSION):
    """Resolve a private evidence directory, refusing anything outside it."""
    base = comparison_profile(version)["private_root"]
    root = base
    if subdirectory is not None:
        root = root / subdirectory
    resolved = root.resolve(strict=False)
    resolved.relative_to(base.resolve(strict=False).parent)
    return resolved


def relative_to_repository(path):
    return str(Path(path).resolve(strict=False).relative_to(REPOSITORY_ROOT))


def phone_map():
    return load_phone_map()
