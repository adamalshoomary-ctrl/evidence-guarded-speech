"""Deterministic, review-only candidates for observable speech events."""

from __future__ import annotations

import math
import re
import statistics
from collections import defaultdict
from copy import deepcopy

from .contract import load_contract


ALGORITHM_VERSION = "fluency-event-candidates-1.1.0"
ARTIFACT_SCHEMA_VERSION = "1.1.0"
_TOKEN_EDGE = re.compile(r"^[^a-z0-9']+|[^a-z0-9']+$", re.IGNORECASE)
_LEADING_ELONGATION = re.compile(r"^([a-z])\1{2,}([a-z].+)$", re.IGNORECASE)
_FORBIDDEN_REVIEW_WORDS = {
    "diagnosis", "diagnostic_label", "severity", "severity_score",
    "stuttering_score",
}


def _normalise(text):
    return _TOKEN_EDGE.sub("", str(text or "").lower())


def _number(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(float(value)))


def _word_start(word):
    return float(word.get("start_s", 0.0))


def _word_end(word):
    return float(word.get("end_s", _word_start(word)))


def _asr_confidence(word):
    value = word.get("asr_confidence", word.get("confidence"))
    return float(value) if _number(value) else None


def _speaker_confidence(word):
    return word.get("confidence", word.get("speaker_confidence"))


def _word_is_eligible(word, minimum_asr):
    confidence = _asr_confidence(word)
    return (word.get("speaker") is not None
            and confidence is not None
            and confidence >= minimum_asr
            and _word_end(word) > _word_start(word))


def _same_speaker(words):
    speakers = {word.get("speaker") for word in words}
    return len(speakers) == 1 and None not in speakers


def _gaps_within(words, maximum_gap):
    return all(
        _word_start(right) - _word_end(left) <= maximum_gap
        for left, right in zip(words, words[1:])
    )


def _event(candidate_type, words, evidence, contract, *,
           start_s=None, end_s=None, uncertainty_reasons=()):
    event_contract = contract["event_types"][candidate_type]
    speaker_confidences = [_speaker_confidence(word) for word in words]
    reasons = list(uncertainty_reasons)
    if any(value not in {"high", "smoothed", "referee"}
           for value in speaker_confidences):
        reasons.append("speaker_attribution_uncertain")
    alternatives = deepcopy(event_contract["important_alternatives"])
    return {
        "event_id": None,
        "candidate_type": candidate_type,
        "start_s": round(
            float(start_s if start_s is not None else _word_start(words[0])), 3
        ),
        "end_s": round(
            float(end_s if end_s is not None else _word_end(words[-1])), 3
        ),
        "speaker": words[0].get("speaker"),
        "evidence": evidence,
        "alternatives": alternatives,
        "uncertainty": {
            "level": "high" if reasons else "moderate",
            "reasons": sorted(set(reasons)),
            "is_probability": False,
            "candidate_is_not_confirmed_event": True,
        },
        "review": {
            "state": "unreviewed",
            "required_review": event_contract["required_review"],
            "manual_confirmation_required": True,
            "reviews": [],
            "reference_truth_status": "not_reference_truth",
        },
    }


def _word_evidence(words, source, indices):
    return {
        "source": source,
        "word_indices": list(indices),
        "transcript_tokens": [word.get("text") for word in words],
        "asr_confidences": [_asr_confidence(word) for word in words],
        "speaker_confidences": [_speaker_confidence(word) for word in words],
        "timing_source": "provider_word_timestamps",
    }


def _phrase_repetitions(words, contract):
    configuration = contract["algorithm"]["whole_word_repetition"]
    minimum_asr = float(configuration["minimum_asr_confidence"])
    maximum_gap = float(configuration["maximum_inter_word_gap_s"])
    tokens = [_normalise(word.get("text")) for word in words]
    candidates = []
    occupied = set()
    for length in range(4, 1, -1):
        index = 0
        while index + 2 * length <= len(words):
            positions = range(index, index + 2 * length)
            span = words[index:index + 2 * length]
            left = tokens[index:index + length]
            right = tokens[index + length:index + 2 * length]
            if (left == right and all(left)
                    and not occupied.intersection(positions)
                    and _same_speaker(span)
                    and all(_word_is_eligible(word, minimum_asr)
                            for word in span)
                    and _gaps_within(span, maximum_gap)):
                evidence = _word_evidence(
                    span, "verbatim_asr_repeated_phrase_pattern", positions
                )
                evidence["phrase_length_words"] = length
                candidates.append(_event(
                    "phrase_repetition", span, evidence, contract,
                    uncertainty_reasons=(
                        "phrase_repetition_is_context_not_stuttering_like_class",
                    ),
                ))
                occupied.update(positions)
                index += 2 * length
            else:
                index += 1
    return candidates


def _whole_word_repetitions(words, contract):
    configuration = contract["algorithm"]["whole_word_repetition"]
    minimum_asr = float(configuration["minimum_asr_confidence"])
    maximum_gap = float(configuration["maximum_inter_word_gap_s"])
    tokens = [_normalise(word.get("text")) for word in words]
    candidates = []
    index = 0
    while index < len(words) - 1:
        token = tokens[index]
        end = index + 1
        while end < len(words) and tokens[end] == token and token:
            end += 1
        span = words[index:end]
        if (len(span) >= 2 and _same_speaker(span)
                and all(_word_is_eligible(word, minimum_asr) for word in span)
                and _gaps_within(span, maximum_gap)):
            positions = range(index, end)
            evidence = _word_evidence(
                span, "verbatim_asr_adjacent_word_pattern", positions
            )
            evidence["repetition_units"] = len(span) - 1
            evidence["syllable_classification"] = "manual_only"
            candidates.append(_event(
                "whole_word_repetition_unclassified", span, evidence, contract,
                uncertainty_reasons=(
                    "single_syllable_status_not_automatically_established",
                ),
            ))
        index = max(end, index + 1)
    return candidates


def _hyphenated_fragment(token):
    core = _normalise(token)
    if "-" not in str(token):
        return None
    raw = re.sub(r"^[^a-z]+|[^a-z]+$", "", str(token).lower())
    parts = [part for part in raw.split("-") if part]
    if len(parts) < 2:
        return None
    target = parts[-1]
    fragments = parts[:-1]
    if (not target or not all(fragment == fragments[0] for fragment in fragments)
            or len(fragments[0]) > 4 or len(fragments[0]) >= len(target)
            or not target.startswith(fragments[0])):
        return None
    return {"fragment": fragments[0], "iterations": len(fragments),
            "target": target, "normalised_token": core}


def _sound_repetitions(words, contract):
    configuration = contract["algorithm"]["sound_repetition"]
    minimum_asr = float(configuration["minimum_asr_confidence"])
    maximum_gap = float(configuration["maximum_fragment_gap_s"])
    candidates = []

    for index, word in enumerate(words):
        if not _word_is_eligible(word, minimum_asr):
            continue
        pattern = _hyphenated_fragment(word.get("text"))
        if pattern:
            evidence = _word_evidence(
                [word], "verbatim_asr_hyphenated_prefix_pattern", [index]
            )
            evidence["fragment_pattern"] = pattern
            candidates.append(_event(
                "sound_or_syllable_repetition", [word], evidence, contract,
                uncertainty_reasons=(
                    "orthography_is_not_a_phonetic_annotation",
                ),
            ))

    index = 0
    tokens = [_normalise(word.get("text")) for word in words]
    while index < len(words) - 1:
        fragment = tokens[index]
        if not fragment or len(fragment) > 4:
            index += 1
            continue
        target_index = index + 1
        while target_index < len(words) and tokens[target_index] == fragment:
            target_index += 1
        if target_index >= len(words):
            break
        target = tokens[target_index]
        span = words[index:target_index + 1]
        if (target.startswith(fragment) and len(target) > len(fragment)
                and _same_speaker(span)
                and all(_word_is_eligible(word, minimum_asr) for word in span)
                and _gaps_within(span, maximum_gap)):
            evidence = _word_evidence(
                span, "verbatim_asr_adjacent_prefix_pattern",
                range(index, target_index + 1),
            )
            evidence["fragment_pattern"] = {
                "fragment": fragment,
                "iterations": target_index - index,
                "target": target,
            }
            candidates.append(_event(
                "sound_or_syllable_repetition", span, evidence, contract,
                uncertainty_reasons=(
                    "separate_asr_tokens_may_be_word_or_fragment_errors",
                    "orthography_is_not_a_phonetic_annotation",
                ),
            ))
            index = target_index + 1
        else:
            index += 1
    return candidates


def _orthographic_prolongations(words, contract):
    configuration = contract["algorithm"]["whole_word_repetition"]
    minimum_asr = float(configuration["minimum_asr_confidence"])
    candidates = []
    for index, word in enumerate(words):
        if not _word_is_eligible(word, minimum_asr):
            continue
        core = _normalise(word.get("text"))
        match = _LEADING_ELONGATION.match(core)
        if not match:
            continue
        repeated_character = match.group(1).lower()
        count = len(core) - len(core.lstrip(repeated_character))
        evidence = _word_evidence(
            [word], "verbatim_asr_elongated_spelling_pattern", [index]
        )
        evidence["orthographic_pattern"] = {
            "character": repeated_character,
            "written_repetitions": count,
        }
        candidates.append(_event(
            "prolonged_sound", [word], evidence, contract,
            uncertainty_reasons=(
                "orthographic_lengthening_is_not_measured_sound_duration",
            ),
        ))
    return candidates


def _overlap(start_a, end_a, start_b, end_b):
    return max(0.0, min(end_a, end_b) - max(start_a, start_b))


def _attributed_word_for_interval(start, end, words):
    matches = [
        (_overlap(start, end, _word_start(word), _word_end(word)), index, word)
        for index, word in enumerate(words)
        if _word_end(word) > start and _word_start(word) < end
    ]
    if not matches:
        return None
    overlap_s, index, word = max(matches, key=lambda item: item[0])
    return (index, word) if overlap_s > 0 else None


def _alignment_characters(alignment, words):
    result = []
    for segment in (alignment or {}).get("segments") or []:
        for character in segment.get("chars") or []:
            start = character.get("start")
            end = character.get("end")
            text = str(character.get("char") or "")
            if (not _number(start) or not _number(end)
                    or float(end) <= float(start)
                    or not text.strip().isalpha()):
                continue
            match = _attributed_word_for_interval(float(start), float(end), words)
            if match is None:
                continue
            word_index, word = match
            result.append({
                "char": text.strip(),
                "start_s": float(start),
                "end_s": float(end),
                "duration_s": float(end) - float(start),
                "score": (float(character["score"])
                          if _number(character.get("score")) else None),
                "word_index": word_index,
                "word": word,
            })
    return result


def _prolonged_sound_candidates(words, alignment, contract):
    configuration = contract["algorithm"]["prolonged_sound"]
    minimum_duration = float(configuration["minimum_character_duration_s"])
    minimum_observations = int(configuration["minimum_baseline_observations"])
    minimum_ratio = float(
        configuration["minimum_ratio_to_speaker_character_median"]
    )
    minimum_robust_z = float(configuration["minimum_robust_z"])
    minimum_score = float(configuration["minimum_alignment_score"])
    characters = _alignment_characters(alignment, words)
    by_speaker = defaultdict(list)
    for item in characters:
        speaker = item["word"].get("speaker")
        if speaker is not None:
            by_speaker[speaker].append(item["duration_s"])
    baselines = {}
    for speaker, durations in by_speaker.items():
        if len(durations) < minimum_observations:
            continue
        median = statistics.median(durations)
        mad = statistics.median(abs(value - median) for value in durations)
        baselines[speaker] = (median, mad, len(durations))

    candidates = []
    for item in characters:
        word = item["word"]
        speaker = word.get("speaker")
        if speaker not in baselines:
            continue
        if item["score"] is not None and item["score"] < minimum_score:
            continue
        median, mad, count = baselines[speaker]
        duration = item["duration_s"]
        ratio = duration / max(median, 1e-6)
        robust_z = (0.6745 * (duration - median) / mad
                    if mad > 1e-6 else math.inf)
        if (duration < minimum_duration or ratio < minimum_ratio
                or robust_z < minimum_robust_z):
            continue
        reasons = ["aligned_character_is_not_a_confirmed_phone"]
        if item["score"] is None:
            reasons.append("alignment_score_missing")
        transcript_token = _normalise(word.get("text"))
        character_matches_token = item["char"].lower() in transcript_token
        if not character_matches_token:
            reasons.append("aligned_character_not_present_in_transcript_token")
        if (_asr_confidence(word) is not None
                and _asr_confidence(word) < 0.5):
            reasons.append("attributed_word_asr_confidence_below_0_50")
        evidence = {
            "source": "forced_alignment_character_duration_outlier",
            "word_indices": [item["word_index"]],
            "transcript_tokens": [word.get("text")],
            "asr_confidences": [_asr_confidence(word)],
            "speaker_confidences": [_speaker_confidence(word)],
            "aligned_character": item["char"],
            "aligned_character_present_in_transcript_token": (
                character_matches_token
            ),
            "aligned_character_duration_s": round(duration, 3),
            "alignment_score": item["score"],
            "speaker_character_duration_baseline": {
                "median_s": round(median, 4),
                "mad_s": round(mad, 4),
                "observation_count": count,
            },
            "duration_ratio": round(ratio, 2),
            "robust_z": (round(robust_z, 2) if math.isfinite(robust_z)
                         else "infinite_zero_mad"),
            "timing_source": "whisperx_forced_alignment_character_interval",
        }
        candidates.append(_event(
            "prolonged_sound", [word], evidence, contract,
            start_s=item["start_s"], end_s=item["end_s"],
            uncertainty_reasons=reasons,
        ))
    return candidates, baselines


def _quality_limitations(audio_quality, master):
    limitations = []
    for check in (audio_quality or {}).get("checks") or []:
        if check.get("status") in {"warn", "fail"}:
            limitations.append({
                "source": "audio_quality",
                "code": check.get("id"),
                "status": check.get("status"),
                "reason": check.get("reason"),
            })
    contamination = (master.get("meta", {}).get("contamination") or {})
    if contamination.get("status") not in {None, "clear"}:
        limitations.append({
            "source": "speaker_contamination",
            "code": "possible_additional_speaker",
            "status": contamination.get("status"),
            "reason": contamination.get("warning"),
        })
    return limitations


def extract_candidates(words, alignment, master, audio_quality,
                       contract=None):
    """Build a complete artifact; candidates never become clinical claims."""
    contract = contract or load_contract()
    task_context = (master.get("meta", {}).get("voice_prosody_context") or {})
    task_profile = task_context.get("task_profile") or (
        "conversation" if master.get("meta", {}).get("recording_type")
        == "conversation" else "unknown_ad_hoc"
    )
    limitations = _quality_limitations(audio_quality, master)
    rejected = (audio_quality or {}).get("decision") == "reject"
    task_excluded = task_profile in set(contract["task_policy"]["excluded"])

    # Four of the five families refuse a word whose ASR confidence falls below
    # the contract's floor. A transcript that carries no ASR confidence at all
    # cannot have that rule applied to it, and running them anyway would return
    # zero candidates: a silent "none found" where the truth is "not measured".
    # The local transcription path is exactly such a transcript.
    asr_confidence_available = any(
        _asr_confidence(word) is not None for word in words
    )
    candidates = []
    baselines = {}
    if not rejected and not task_excluded:
        if asr_confidence_available:
            candidates.extend(_phrase_repetitions(words, contract))
            candidates.extend(_whole_word_repetitions(words, contract))
            candidates.extend(_sound_repetitions(words, contract))
            candidates.extend(_orthographic_prolongations(words, contract))
        duration_candidates, baselines = _prolonged_sound_candidates(
            words, alignment, contract
        )
        candidates.extend(duration_candidates)
    candidates.sort(key=lambda item: (
        item["start_s"], item["end_s"], item["candidate_type"]
    ))
    for index, candidate in enumerate(candidates, 1):
        candidate["event_id"] = f"FE{index:04d}"
        if limitations:
            candidate["uncertainty"]["level"] = "high"
            candidate["uncertainty"]["reasons"].append(
                "recording_level_quality_or_contamination_warning"
            )
            candidate["uncertainty"]["reasons"] = sorted(set(
                candidate["uncertainty"]["reasons"]
            ))

    unavailable_reasons = []
    if rejected:
        unavailable_reasons.append("audio_quality_rejected")
    if task_excluded:
        unavailable_reasons.append("task_profile_excluded")
    return {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "contract_version": contract["contract_version"],
        "algorithm_version": ALGORITHM_VERSION,
        "status": ("unavailable" if unavailable_reasons
                   else "engineering_candidates_only"),
        "claim_boundary": {
            "candidate_is_not_confirmed_event": True,
            "candidate_absence_does_not_establish_fluency": True,
            "diagnosis": "blocked",
            "severity": "blocked",
            "released_interpretation": "blocked",
            "personal_progress": "blocked",
        },
        "analysis_context": {
            "recording_type": master.get("meta", {}).get("recording_type"),
            "task_id": task_context.get("task_id"),
            "task_profile": task_profile,
            "task_comparability": task_context.get(
                "task_comparability", "not_comparable"
            ),
            "language_scope": contract["algorithm"]["language_scope"],
        },
        "availability": {
            "candidate_extraction": ("unavailable" if unavailable_reasons
                                     else "available_for_engineering_review"),
            "reasons": unavailable_reasons,
            "text_derived_families": (
                "available_for_engineering_review" if asr_confidence_available
                else "unavailable"
            ),
            "text_derived_families_reason": (
                None if asr_confidence_available else
                "The transcript carries no word level ASR confidence, so the "
                "contract's eligibility floor cannot be applied to the "
                "repetition and orthographic families. They are reported as "
                "unavailable rather than as zero candidates, because zero here "
                "would mean not measured and would read as none found."
            ),
            "duration_derived_families": (
                "unavailable" if unavailable_reasons
                else "available_for_engineering_review"
            ),
            "possible_block_automation": "unavailable",
            "possible_block_reason": contract["algorithm"]["possible_block"][
                "reason"
            ],
            "single_syllable_classification": "manual_only",
        },
        "source_summary": {
            "attributed_word_count": len(words),
            "aligned_character_count": len(_alignment_characters(alignment, words)),
            "speaker_character_baseline_observations": {
                speaker: count for speaker, (_, _, count) in baselines.items()
            },
        },
        "recording_limitations": limitations,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "review_summary": {
            "state": "unreviewed",
            "reviewed_candidate_count": 0,
            "reference_truth_status": "not_reference_truth",
            "manual_additions": [],
        },
        "release_limits": deepcopy(contract["release_limits"]),
    }


def validate_artifact(artifact, contract=None):
    """Return every structural or safety error in a generated artifact."""
    contract = contract or load_contract()
    errors = []
    required_root = {
        "schema_version", "contract_version", "algorithm_version", "status",
        "claim_boundary", "analysis_context", "availability",
        "source_summary", "recording_limitations", "candidate_count",
        "candidates", "review_summary", "release_limits",
    }
    if not isinstance(artifact, dict):
        return ["artifact must be an object"]
    missing = sorted(required_root - set(artifact))
    if missing:
        return ["artifact is missing: " + ", ".join(missing)]
    if artifact.get("algorithm_version") != ALGORITHM_VERSION:
        errors.append("artifact algorithm version is unsupported")
    boundaries = artifact.get("claim_boundary") or {}
    if boundaries.get("candidate_is_not_confirmed_event") is not True:
        errors.append("artifact must say candidates are not confirmed events")
    if boundaries.get("candidate_absence_does_not_establish_fluency") is not True:
        errors.append("artifact cannot use candidate absence as fluency")
    for field in ("diagnosis", "severity", "released_interpretation",
                  "personal_progress"):
        if boundaries.get(field) != "blocked":
            errors.append(f"artifact claim boundary {field} must be blocked")
    availability = artifact.get("availability") or {}
    if availability.get("possible_block_automation") != "unavailable":
        errors.append("possible block automation must remain unavailable")
    if availability.get("single_syllable_classification") != "manual_only":
        errors.append("single syllable classification must remain manual")

    candidates = artifact.get("candidates")
    if not isinstance(candidates, list):
        errors.append("candidates must be a list")
        candidates = []
    if artifact.get("candidate_count") != len(candidates):
        errors.append("candidate_count does not match candidates")
    expected_ids = [f"FE{index:04d}" for index in range(1, len(candidates) + 1)]
    actual_ids = [candidate.get("event_id") for candidate in candidates
                  if isinstance(candidate, dict)]
    if actual_ids != expected_ids:
        errors.append("candidate event IDs must be unique and sequential")
    required_fields = set(contract["candidate_contract"]["required_fields"])
    allowed_types = set(contract["event_types"])
    allowed_uncertainty = set(
        contract["candidate_contract"]["allowed_uncertainty_levels"]
    )
    for index, candidate in enumerate(candidates):
        label = f"candidate {index + 1}"
        if not isinstance(candidate, dict):
            errors.append(f"{label} must be an object")
            continue
        missing_fields = sorted(required_fields - set(candidate))
        if missing_fields:
            errors.append(f"{label} is missing: {', '.join(missing_fields)}")
            continue
        if candidate.get("candidate_type") not in allowed_types:
            errors.append(f"{label} has an unknown type")
        if candidate.get("candidate_type") == "possible_block":
            errors.append("automatic candidates cannot be possible blocks")
        if (not _number(candidate.get("start_s"))
                or not _number(candidate.get("end_s"))
                or float(candidate["end_s"]) <= float(candidate["start_s"])):
            errors.append(f"{label} has invalid timestamps")
        if not candidate.get("speaker"):
            errors.append(f"{label} needs a speaker")
        uncertainty = candidate.get("uncertainty") or {}
        if uncertainty.get("level") not in allowed_uncertainty:
            errors.append(f"{label} has an unsupported uncertainty level")
        if uncertainty.get("is_probability") is not False:
            errors.append(f"{label} cannot claim a probability")
        if uncertainty.get("candidate_is_not_confirmed_event") is not True:
            errors.append(f"{label} must remain unconfirmed")
        review = candidate.get("review") or {}
        if review.get("state") not in set(contract["review_contract"]["states"]):
            errors.append(f"{label} has an unsupported review state")
        if review.get("reference_truth_status") != "not_reference_truth":
            errors.append(f"{label} cannot claim reference truth")
    review_summary = artifact.get("review_summary") or {}
    if review_summary.get("reference_truth_status") != "not_reference_truth":
        errors.append("review summary cannot claim reference truth")
    reviewed_count = sum(
        isinstance(candidate, dict)
        and (candidate.get("review") or {}).get("state") != "unreviewed"
        for candidate in candidates
    )
    if review_summary.get("reviewed_candidate_count") != reviewed_count:
        errors.append("reviewed_candidate_count does not match candidates")
    additions = review_summary.get("manual_additions")
    if not isinstance(additions, list):
        errors.append("manual_additions must be a list")
        additions = []
    for index, addition in enumerate(additions):
        label = f"manual addition {index + 1}"
        if not isinstance(addition, dict):
            errors.append(f"{label} must be an object")
            continue
        if addition.get("manual_event_id") != f"FM{index + 1:04d}":
            errors.append("manual addition IDs must be unique and sequential")
        if addition.get("observed_type") not in allowed_types:
            errors.append(f"{label} has an unknown type")
        if (not _number(addition.get("start_s"))
                or not _number(addition.get("end_s"))
                or float(addition["end_s"]) <= float(addition["start_s"])):
            errors.append(f"{label} has invalid timestamps")
        if not addition.get("speaker"):
            errors.append(f"{label} needs a speaker")
        if addition.get("state") not in {
                "confirmed_observable_event", "uncertain"}:
            errors.append(f"{label} has an unsupported state")
        if addition.get("reference_truth_status") != "not_reference_truth":
            errors.append(f"{label} cannot claim reference truth")
        if not addition.get("reviewed_at_utc"):
            errors.append(f"{label} needs a review time")
        if not isinstance(addition.get("blind_to_automation"), bool):
            errors.append(f"{label} needs a blinding record")
    expected_review_state = (
        "partially_reviewed" if reviewed_count or additions else "unreviewed"
    )
    if review_summary.get("state") != expected_review_state:
        errors.append("review summary state does not match review records")
    for use, required in contract["release_limits"].items():
        if artifact.get("release_limits", {}).get(use) != required:
            errors.append(f"artifact release limit {use} must be {required}")
    return errors


def _contains_forbidden_review_field(value):
    if isinstance(value, dict):
        return any(
            str(key).lower() in _FORBIDDEN_REVIEW_WORDS
            or _contains_forbidden_review_field(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_forbidden_review_field(item) for item in value)
    return False


def apply_review_packet(artifact, packet, contract=None):
    """Apply one human review without promoting it to reference truth."""
    contract = contract or load_contract()
    artifact_errors = validate_artifact(artifact, contract)
    if artifact_errors:
        raise ValueError("cannot review an invalid artifact: "
                         + "; ".join(artifact_errors))
    if not isinstance(packet, dict):
        raise ValueError("review packet must be an object")
    if _contains_forbidden_review_field(packet):
        raise ValueError("review packets cannot contain diagnosis or severity fields")
    reviewer = packet.get("reviewer") or {}
    role = reviewer.get("role")
    if role not in set(contract["review_contract"]["reviewer_roles"]):
        raise ValueError("reviewer role is not permitted by the contract")
    if not reviewer.get("opaque_id"):
        raise ValueError("reviewer.opaque_id is required")
    if not packet.get("review_id"):
        raise ValueError("review_id is required")
    if not packet.get("reviewed_at_utc"):
        raise ValueError("reviewed_at_utc is required")
    if not isinstance(packet.get("blind_to_automation"), bool):
        raise ValueError("blind_to_automation must be true or false")
    decisions = packet.get("decisions") or []
    additions_input = packet.get("additions") or []
    if not isinstance(decisions, list) or not isinstance(additions_input, list):
        raise ValueError("decisions and additions must be lists")
    if not decisions and not additions_input:
        raise ValueError("review packet must contain a decision or addition")
    decision_ids = [
        decision.get("event_id") for decision in decisions
        if isinstance(decision, dict)
    ]
    if len(decision_ids) != len(decisions):
        raise ValueError("every decision must be an object")
    if len(set(decision_ids)) != len(decision_ids):
        raise ValueError("one review cannot decide the same event twice")
    allowed_states = set(contract["review_contract"]["states"]) - {"unreviewed"}
    allowed_types = set(contract["event_types"])
    events = {item["event_id"]: item for item in artifact.get("candidates") or []}
    existing_review_ids = {
        review.get("review_id")
        for event in events.values()
        for review in event.get("review", {}).get("reviews", [])
    }
    existing_review_ids.update(
        addition.get("review_id")
        for addition in artifact.get("review_summary", {}).get(
            "manual_additions", []
        )
    )
    if packet["review_id"] in existing_review_ids:
        raise ValueError("review_id has already been applied")
    for decision in decisions:
        event_id = decision.get("event_id")
        if event_id not in events:
            raise ValueError(f"unknown event_id: {event_id}")
        state = decision.get("state")
        if state not in allowed_states:
            raise ValueError(f"unsupported review state: {state}")
        observed_type = decision.get("observed_type")
        if state in {"confirmed_observable_event", "relabeled"}:
            if observed_type not in allowed_types:
                raise ValueError("confirmed or relabeled events need an allowed type")
        boundary = decision.get("boundary")
        if boundary is not None:
            if (not isinstance(boundary, dict)
                    or not _number(boundary.get("start_s"))
                    or not _number(boundary.get("end_s"))
                    or float(boundary["end_s"]) <= float(boundary["start_s"])):
                raise ValueError("review boundaries need valid start_s and end_s")
        record = {
            "review_id": packet["review_id"],
            "reviewer": deepcopy(reviewer),
            "reviewed_at_utc": packet.get("reviewed_at_utc"),
            "blind_to_automation": packet.get("blind_to_automation"),
            "state": state,
            "observed_type": observed_type,
            "boundary": deepcopy(boundary),
            "reason_code": decision.get("reason_code"),
        }
        event = events[event_id]
        event["review"]["reviews"].append(record)
        states = {item["state"] for item in event["review"]["reviews"]}
        event["review"]["state"] = (
            states.pop() if len(states) == 1 else "uncertain"
        )
        event["review"]["reference_truth_status"] = "not_reference_truth"

    additions = artifact.setdefault("review_summary", {}).setdefault(
        "manual_additions", []
    )
    for addition in additions_input:
        if not isinstance(addition, dict):
            raise ValueError("every manual addition must be an object")
        observed_type = addition.get("observed_type")
        if observed_type not in allowed_types:
            raise ValueError("manual additions need an allowed observed_type")
        if not (_number(addition.get("start_s"))
                and _number(addition.get("end_s"))
                and float(addition["end_s"]) > float(addition["start_s"])):
            raise ValueError("manual additions need valid start_s and end_s")
        if not addition.get("speaker"):
            raise ValueError("manual additions need a speaker")
        addition_state = addition.get("state", "uncertain")
        if addition_state not in {"confirmed_observable_event", "uncertain"}:
            raise ValueError("manual additions need a confirmed or uncertain state")
        additions.append({
            "manual_event_id": f"FM{len(additions) + 1:04d}",
            "observed_type": observed_type,
            "start_s": round(float(addition["start_s"]), 3),
            "end_s": round(float(addition["end_s"]), 3),
            "speaker": addition["speaker"],
            "source": "human_review",
            "review_id": packet["review_id"],
            "reviewer": deepcopy(reviewer),
            "reviewed_at_utc": packet["reviewed_at_utc"],
            "blind_to_automation": packet["blind_to_automation"],
            "state": addition_state,
            "reference_truth_status": "not_reference_truth",
        })
    reviewed = sum(
        candidate["review"]["state"] != "unreviewed"
        for candidate in artifact.get("candidates") or []
    )
    artifact["review_summary"].update({
        "state": "partially_reviewed" if reviewed or additions else "unreviewed",
        "reviewed_candidate_count": reviewed,
        "reference_truth_status": "not_reference_truth",
    })
    errors = validate_artifact(artifact, contract)
    if errors:
        raise ValueError("review produced an invalid artifact: " + "; ".join(errors))
    return artifact
