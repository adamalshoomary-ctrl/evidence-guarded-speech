"""Task-aware, timestamped voice and prosody primitive extraction.

The legacy renderer tracks are intentionally produced elsewhere. This module
contains the additive Phase C measurement path and has no command-line side
effects so generated controls can exercise it directly.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import parselmouth
from parselmouth.praat import call


SCHEMA_VERSION = "1.0.0"
ALGORITHM_VERSION = "voice-prosody-primitives-1.0.0"
CONTRACT_VERSION = "1.0.0"
ANALYSIS_SAMPLE_RATE_HZ = 48000
FRAME_STEP_S = 0.01
LEVEL_WINDOW_S = 0.02
PITCH_FLOOR_HZ = 50.0
PITCH_CEILING_HZ = 800.0
VOICING_THRESHOLD = 0.45
SILENCE_THRESHOLD = 0.03
OCTAVE_JUMP_RATIO = 1.9
BOUNDARY_MARGIN_RATIO = 0.05
PITCH_REGION_EDGE_MARGIN_S = 3.0 / PITCH_FLOOR_HZ / 2.0
ADAPTIVE_PITCH_RATIO = 3.0
MIN_F0_FRAMES = 50
MIN_F0_S = 1.0
MIN_DISTRIBUTION_FRAMES = 100
MIN_DISTRIBUTION_S = 2.0
MIN_CPPS_TOTAL_S = 5.0
MIN_VOWEL_REPETITIONS = 3
VOWEL_MIDDLE_S = 1.0

PRIMITIVE_NAMES = (
    "f0_median_hz",
    "f0_p05_hz",
    "f0_p25_hz",
    "f0_p75_hz",
    "f0_p95_hz",
    "f0_distribution_span_st",
    "recorder_level_p05_dbfs",
    "recorder_level_p25_dbfs",
    "recorder_level_median_dbfs",
    "recorder_level_p75_dbfs",
    "recorder_level_p95_dbfs",
    "recorder_level_span_db",
    "cpps_db",
    "jitter_local_pct",
    "shimmer_local_pct",
)


def _round(value, digits=3):
    if value is None or not math.isfinite(float(value)):
        return None
    return round(float(value), digits)


def _load_contract(repo_root):
    path = Path(repo_root) / "voice_prosody" / "contract-v1.1.0.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_task_profile(task_id, recording_mode, contract):
    if task_id:
        for name, profile in contract["task_profiles"].items():
            if task_id in profile.get("task_ids", []):
                return name
    if recording_mode == "conversation":
        return "conversation"
    return "unknown_ad_hoc"


def _research_consent_granted(document):
    if not isinstance(document, dict):
        return False
    account_participant_ids = {
        item.get("participant_id")
        for item in document.get("participants", [])
        if item.get("role") == "account_holder"
    }
    return any(
        decision.get("participant_id") in account_participant_ids
        and decision.get("purpose") == "research_collection"
        and decision.get("decision") == "granted"
        for decision in document.get("consent_snapshot", {}).get("decisions", [])
    )


def analysis_context(session_context_path, recording_mode, repo_root):
    """Resolve declared task and nonidentifying capture context."""
    contract = _load_contract(repo_root)
    document = None
    status = "context_missing"
    if session_context_path is not None:
        try:
            document = json.loads(
                Path(session_context_path).read_text(encoding="utf-8")
            )
            status = "declared"
        except (OSError, json.JSONDecodeError):
            status = "context_unreadable"
    task = document.get("task", {}) if isinstance(document, dict) else {}
    capture = document.get("capture", {}) if isinstance(document, dict) else {}
    task_id = task.get("task_id")
    profile_name = _resolve_task_profile(task_id, recording_mode, contract)
    profile = contract["task_profiles"][profile_name]
    device = capture.get("device") if isinstance(capture, dict) else None
    if not isinstance(device, dict):
        device = {
            "device_class": "unknown",
            "platform": "unknown",
            "microphone": "unknown",
            "source": "not_declared",
        }
    return {
        "status": status,
        "task_id": task_id,
        "task_version": task.get("task_version"),
        "prompt_id": task.get("prompt_id"),
        "prompt_version": task.get("prompt_version"),
        "language": task.get("language"),
        "preparation": task.get("preparation"),
        "accommodations": task.get("accommodations", []),
        "task_profile": profile_name,
        "task_comparability": profile["comparability"],
        "supported_primitives": list(profile["supports"]),
        "requires_research_consent": bool(
            profile.get("requires_research_consent")
        ),
        "research_consent_granted": _research_consent_granted(document),
        "device": {
            key: device.get(key, "unknown")
            for key in ("device_class", "platform", "microphone", "source")
        },
        "quality_policy": capture.get("quality_policy")
        if isinstance(capture, dict) else None,
        "capture_processing": {
            "automatic_gain_control": "unknown",
            "noise_suppression": "unknown",
            "echo_cancellation": "unknown",
        },
    }


def _quality_state(audio_quality, dependencies):
    warnings = []
    failure = False
    for check in (audio_quality or {}).get("checks", []):
        if check.get("status") not in {"warn", "fail"}:
            continue
        affects = set(check.get("affects") or [])
        if not affects.intersection(set(dependencies) | {"all_measurements"}):
            continue
        warnings.append({
            "check_id": check.get("id"),
            "status": check.get("status"),
            "reason": check.get("reason"),
        })
        failure = failure or check.get("status") == "fail"
    return failure, warnings


def _regions(diarization, duration_s):
    turns = []
    for index, item in enumerate((diarization or {}).get("turns", []), 1):
        try:
            start = max(0.0, float(item["start_s"]))
            end = min(float(duration_s), float(item["end_s"]))
        except (KeyError, TypeError, ValueError):
            continue
        if end <= start or not item.get("speaker"):
            continue
        turns.append({
            "region_id": f"region_{index:04d}",
            "speaker": item["speaker"],
            "start_s": start,
            "end_s": end,
            "duration_s": end - start,
        })
    return turns


def _owner_at(time_s, regions):
    owners = [region for region in regions
              if region["start_s"] <= time_s <= region["end_s"]]
    if len(owners) != 1:
        return None, None, "overlap" if owners else "outside_attributed_region"
    owner = owners[0]
    if not (owner["start_s"] + PITCH_REGION_EDGE_MARGIN_S <= time_s
            <= owner["end_s"] - PITCH_REGION_EDGE_MARGIN_S):
        return None, None, "region_edge_excluded"
    return owner["speaker"], owner["region_id"], None


def _rms_dbfs_at(samples, sample_rate, times):
    half = max(1, int(round(LEVEL_WINDOW_S * sample_rate / 2)))
    result = []
    for time_s in times:
        center = int(round(float(time_s) * sample_rate))
        start = max(0, center - half)
        end = min(len(samples), center + half)
        window = samples[start:end]
        if not len(window):
            result.append(None)
            continue
        rms = float(np.sqrt(np.mean(np.square(window.astype(np.float64)))))
        result.append(20.0 * math.log10(max(rms, 1e-12)))
    return np.asarray(result, dtype=float)


def _pitch(sound, floor_hz, ceiling_hz):
    return sound.to_pitch_ac(
        time_step=FRAME_STEP_S,
        pitch_floor=floor_hz,
        max_number_of_candidates=15,
        very_accurate=False,
        silence_threshold=SILENCE_THRESHOLD,
        voicing_threshold=VOICING_THRESHOLD,
        octave_cost=0.01,
        octave_jump_cost=0.35,
        voiced_unvoiced_cost=0.14,
        pitch_ceiling=ceiling_hz,
    )


def _nearest_pitch_values(pitch, time_s):
    times = pitch.xs()
    if not len(times):
        return None, None
    index = int(np.argmin(np.abs(times - time_s)))
    if abs(float(times[index]) - float(time_s)) > FRAME_STEP_S * 0.75:
        return None, None
    frequency = float(pitch.selected_array["frequency"][index])
    if frequency <= 0:
        return None, None
    return frequency, float(pitch.selected_array["strength"][index])


def _pitch_frames(samples, sample_rate, regions):
    sound = parselmouth.Sound(
        np.asarray(samples, dtype=np.float64), sampling_frequency=sample_rate
    )
    pitch = _pitch(sound, PITCH_FLOOR_HZ, PITCH_CEILING_HZ)
    times = pitch.xs()
    frequencies = pitch.selected_array["frequency"]
    strengths = pitch.selected_array["strength"]
    levels = _rms_dbfs_at(samples, sample_rate, times)
    frames = []
    for time_s, frequency, strength, level in zip(
            times, frequencies, strengths, levels):
        speaker, region_id, ownership_flag = _owner_at(float(time_s), regions)
        voiced = bool(frequency > 0 and speaker is not None)
        flags = []
        if ownership_flag:
            flags.append(ownership_flag)
        frames.append({
            "time_s": _round(time_s, 3),
            "f0_hz": _round(frequency, 2) if voiced else None,
            "pitch_strength": _round(strength, 4) if voiced else None,
            "recorder_level_dbfs": _round(level, 2),
            "voiced": voiced,
            "speaker": speaker,
            "region_id": region_id,
            "quality_flags": flags,
        })

    pitch_ranges = {}
    speakers = sorted({frame["speaker"] for frame in frames
                       if frame["speaker"] is not None})
    for speaker in speakers:
        broad_values = [
            frame["f0_hz"] for frame in frames
            if frame["speaker"] == speaker and frame["f0_hz"] is not None
        ]
        if not broad_values:
            continue
        broad_median = float(np.median(broad_values))
        floor_hz = max(PITCH_FLOOR_HZ, broad_median / ADAPTIVE_PITCH_RATIO)
        ceiling_hz = min(
            PITCH_CEILING_HZ, broad_median * ADAPTIVE_PITCH_RATIO
        )
        if ceiling_hz <= floor_hz * 1.5:
            floor_hz, ceiling_hz = PITCH_FLOOR_HZ, PITCH_CEILING_HZ
        adaptive = _pitch(sound, floor_hz, ceiling_hz)
        pitch_ranges[speaker] = {
            "initial_broad_median_hz": _round(broad_median, 2),
            "adaptive_floor_hz": _round(floor_hz, 2),
            "adaptive_ceiling_hz": _round(ceiling_hz, 2),
        }
        for frame in frames:
            if frame["speaker"] != speaker:
                continue
            frequency, strength = _nearest_pitch_values(
                adaptive, frame["time_s"]
            )
            frame["f0_hz"] = _round(frequency, 2)
            frame["pitch_strength"] = _round(strength, 4)
            frame["voiced"] = frequency is not None
            if frequency is None:
                continue
            if frequency <= floor_hz * (1 + BOUNDARY_MARGIN_RATIO):
                frame["quality_flags"].append("near_pitch_floor")
            if frequency >= ceiling_hz * (1 - BOUNDARY_MARGIN_RATIO):
                frame["quality_flags"].append("near_pitch_ceiling")
        final_values = [
            frame["f0_hz"] for frame in frames
            if frame["speaker"] == speaker and frame["f0_hz"] is not None
        ]
        if final_values:
            final_median = float(np.median(final_values))
            for frame in frames:
                if frame["speaker"] != speaker or frame["f0_hz"] is None:
                    continue
                distance_st = abs(
                    12.0 * math.log2(frame["f0_hz"] / final_median)
                )
                if 11.0 <= distance_st <= 13.0:
                    frame["quality_flags"].append(
                        "speaker_relative_octave_candidate"
                    )
    previous_by_region = {}
    for frame in frames:
        if not frame["voiced"] or frame["region_id"] is None:
            continue
        previous = previous_by_region.get(frame["region_id"])
        if previous is not None:
            ratio = max(frame["f0_hz"], previous["f0_hz"]) / max(
                min(frame["f0_hz"], previous["f0_hz"]), 1e-12
            )
            if (frame["time_s"] - previous["time_s"] <= FRAME_STEP_S * 1.5
                    and ratio >= OCTAVE_JUMP_RATIO):
                frame["quality_flags"].append("suspected_octave_jump")
        previous_by_region[frame["region_id"]] = frame
    return frames, pitch_ranges


def _availability(status, reason=None, quality="high", warnings=None):
    return {
        "status": status,
        "reason": reason,
        "quality": quality,
        "warnings": list(warnings or []),
    }


def _basic_availability(frame_count, voiced_s, quality_failure, warnings):
    if quality_failure:
        return _availability("unavailable", "audio_quality_failure",
                             "unavailable", warnings)
    if frame_count < MIN_F0_FRAMES or voiced_s < MIN_F0_S:
        return _availability("unavailable", "insufficient_voiced_evidence",
                             "unavailable", warnings)
    quality = "low" if warnings else "high"
    return _availability("available", None, quality, warnings)


def _distribution_availability(frame_count, voiced_s, base):
    if base["status"] != "available":
        return dict(base)
    if frame_count < MIN_DISTRIBUTION_FRAMES or voiced_s < MIN_DISTRIBUTION_S:
        return _availability("unavailable", "insufficient_distribution_evidence",
                             "unavailable", base["warnings"])
    return dict(base)


def _speaker_summary(speaker, frames, regions, context, audio_quality):
    attributed = [frame for frame in frames if frame["speaker"] == speaker]
    voiced = [frame for frame in attributed if frame["voiced"]]
    f0 = np.asarray([frame["f0_hz"] for frame in voiced], dtype=float)
    levels = np.asarray([
        frame["recorder_level_dbfs"] for frame in voiced
        if frame["recorder_level_dbfs"] is not None
    ], dtype=float)
    voiced_s = len(voiced) * FRAME_STEP_S
    pitch_failure, pitch_warnings = _quality_state(
        audio_quality, ("pitch", "voice_quality")
    )
    level_failure, level_warnings = _quality_state(
        audio_quality, ("loudness",)
    )
    pitch_state = _basic_availability(
        len(voiced), voiced_s, pitch_failure, pitch_warnings
    )
    distribution_state = _distribution_availability(
        len(voiced), voiced_s, pitch_state
    )
    level_state = _distribution_availability(
        len(levels), len(levels) * FRAME_STEP_S,
        _basic_availability(len(levels), len(levels) * FRAME_STEP_S,
                            level_failure, level_warnings),
    )
    values = {name: None for name in PRIMITIVE_NAMES}
    if pitch_state["status"] == "available":
        values["f0_median_hz"] = _round(np.median(f0), 2)
    if distribution_state["status"] == "available":
        p05, p25, p75, p95 = np.percentile(f0, [5, 25, 75, 95])
        values.update({
            "f0_p05_hz": _round(p05, 2),
            "f0_p25_hz": _round(p25, 2),
            "f0_p75_hz": _round(p75, 2),
            "f0_p95_hz": _round(p95, 2),
            "f0_distribution_span_st": _round(
                12.0 * math.log2(p95 / p05), 3
            ) if p05 > 0 else None,
        })
    if level_state["status"] == "available":
        lp05, lp25, lp50, lp75, lp95 = np.percentile(
            levels, [5, 25, 50, 75, 95]
        )
        values.update({
            "recorder_level_p05_dbfs": _round(lp05, 2),
            "recorder_level_p25_dbfs": _round(lp25, 2),
            "recorder_level_median_dbfs": _round(lp50, 2),
            "recorder_level_p75_dbfs": _round(lp75, 2),
            "recorder_level_p95_dbfs": _round(lp95, 2),
            "recorder_level_span_db": _round(lp95 - lp05, 2),
        })
    median_f0 = values["f0_median_hz"]
    if median_f0:
        for frame in voiced:
            frame["f0_relative_to_speaker_median_st"] = _round(
                12.0 * math.log2(frame["f0_hz"] / median_f0), 3
            )

    speaker_regions = [region for region in regions
                       if region["speaker"] == speaker]
    boundary_count = sum(
        bool({"near_pitch_floor", "near_pitch_ceiling"}
             .intersection(frame["quality_flags"]))
        for frame in voiced
    )
    jump_count = sum(
        "suspected_octave_jump" in frame["quality_flags"] for frame in voiced
    )
    octave_cluster_count = sum(
        "speaker_relative_octave_candidate" in frame["quality_flags"]
        for frame in voiced
    )
    availability = {
        "f0_median_hz": pitch_state,
        "f0_percentiles_hz": distribution_state,
        "f0_distribution_span_st": distribution_state,
        "recorder_level_percentiles_dbfs": level_state,
        "recorder_level_span_db": level_state,
        "cpps_db": _availability("unavailable", "task_or_processing_not_evaluated",
                                 "unavailable"),
        "jitter_local_pct": _availability("unavailable", "sustained_vowel_only",
                                           "unavailable"),
        "shimmer_local_pct": _availability("unavailable", "sustained_vowel_only",
                                            "unavailable"),
    }
    boundary_fraction = boundary_count / len(voiced) if voiced else None
    jump_fraction = jump_count / len(voiced) if voiced else None
    octave_cluster_fraction = (
        octave_cluster_count / len(voiced) if voiced else None
    )
    if (pitch_state["status"] == "available"
            and boundary_fraction is not None and boundary_fraction > 0.05):
        boundary_state = _availability(
            "unavailable", "pitch_range_boundary_hits", "unavailable", [{
                "code": "pitch_range_boundary_hits",
                "reason": "The distribution tails contain too many estimates near the configured pitch boundary.",
            }]
        )
        availability["f0_percentiles_hz"] = dict(boundary_state)
        availability["f0_distribution_span_st"] = dict(boundary_state)
        for name in (
                "f0_p05_hz", "f0_p25_hz",
                "f0_p75_hz", "f0_p95_hz", "f0_distribution_span_st"):
            values[name] = None
        if boundary_fraction > 0.20:
            availability["f0_median_hz"] = dict(boundary_state)
            values["f0_median_hz"] = None
        else:
            availability["f0_median_hz"] = _availability(
                "available", None, "low",
                pitch_state["warnings"] + boundary_state["warnings"],
            )
    elif (pitch_state["status"] == "available"
          and jump_fraction is not None and jump_fraction > 0.05):
        jump_state = _availability(
            "unavailable", "excessive_suspected_octave_jumps", "unavailable", [{
                "code": "excessive_suspected_octave_jumps",
                "reason": "The contour has too many discontinuities for distribution tails.",
            }]
        )
        availability["f0_percentiles_hz"] = dict(jump_state)
        availability["f0_distribution_span_st"] = dict(jump_state)
        for name in (
                "f0_p05_hz", "f0_p25_hz",
                "f0_p75_hz", "f0_p95_hz", "f0_distribution_span_st"):
            values[name] = None
        availability["f0_median_hz"] = _availability(
            "available", None, "low",
            pitch_state["warnings"] + jump_state["warnings"],
        )
    elif (pitch_state["status"] == "available"
          and octave_cluster_fraction is not None
          and octave_cluster_fraction > 0.05):
        octave_state = _availability(
            "unavailable", "possible_octave_error_cluster", "unavailable", [{
                "code": "possible_octave_error_cluster",
                "reason": "Too much of the contour forms a possible octave error cluster for reliable distribution tails.",
            }]
        )
        availability["f0_percentiles_hz"] = dict(octave_state)
        availability["f0_distribution_span_st"] = dict(octave_state)
        for name in (
                "f0_p05_hz", "f0_p25_hz", "f0_p75_hz", "f0_p95_hz",
                "f0_distribution_span_st"):
            values[name] = None
        availability["f0_median_hz"] = _availability(
            "available", None, "low",
            pitch_state["warnings"] + octave_state["warnings"],
        )

    supported = set(context.get("supported_primitives") or [])
    support_fields = {
        "f0_median_hz": ("f0_median_hz",),
        "f0_percentiles_hz": (
            "f0_p05_hz", "f0_p25_hz", "f0_p75_hz", "f0_p95_hz",
        ),
        "f0_distribution_span_st": ("f0_distribution_span_st",),
        "recorder_level_percentiles_dbfs": (
            "recorder_level_p05_dbfs", "recorder_level_p25_dbfs",
            "recorder_level_median_dbfs", "recorder_level_p75_dbfs",
            "recorder_level_p95_dbfs",
        ),
        "recorder_level_span_db": ("recorder_level_span_db",),
        "cpps_db": ("cpps_db",),
        "jitter_local_pct": ("jitter_local_pct",),
        "shimmer_local_pct": ("shimmer_local_pct",),
    }
    for support_name, fields in support_fields.items():
        if support_name in supported:
            continue
        availability[support_name] = _availability(
            "unavailable", "task_ineligible", "unavailable"
        )
        for field in fields:
            values[field] = None
    if (context.get("requires_research_consent")
            and not context.get("research_consent_granted")):
        for support_name in supported:
            if support_name not in availability:
                continue
            availability[support_name] = _availability(
                "unavailable", "research_consent_not_granted", "unavailable"
            )
            for field in support_fields.get(support_name, ()):
                values[field] = None
    return {
        "speaker": speaker,
        "task_id": context["task_id"],
        "task_version": context["task_version"],
        "task_profile": context["task_profile"],
        "task_comparability": context["task_comparability"],
        "regions": [{
            key: _round(value, 3) if key in {"start_s", "end_s", "duration_s"}
            else value
            for key, value in region.items()
        } for region in speaker_regions],
        "sample": {
            "attributed_frame_count": len(attributed),
            "voiced_frame_count": len(voiced),
            "voiced_s": _round(voiced_s, 3),
            "continuous_region_count": len(speaker_regions),
        },
        "diagnostics": {
            "near_pitch_boundary_frame_count": boundary_count,
            "near_pitch_boundary_fraction": _round(boundary_fraction, 4),
            "suspected_octave_jump_count": jump_count,
            "suspected_octave_jump_fraction": _round(jump_fraction, 4),
            "possible_octave_cluster_frame_count": octave_cluster_count,
            "possible_octave_cluster_fraction": _round(
                octave_cluster_fraction, 4
            ),
            "pitch_strength_median": _round(np.median([
                frame["pitch_strength"] for frame in voiced
                if frame["pitch_strength"] is not None
            ]), 4) if voiced else None,
        },
        "values": values,
        "availability": availability,
        "research_trials": [],
    }


def _sound_from_range(samples, sample_rate, start_s, end_s):
    start = max(0, int(round(start_s * sample_rate)))
    end = min(len(samples), int(round(end_s * sample_rate)))
    if end <= start:
        return None
    return parselmouth.Sound(
        np.asarray(samples[start:end], dtype=np.float64),
        sampling_frequency=sample_rate,
    )


def _cpps(sound):
    try:
        cepstrogram = call(
            sound, "To PowerCepstrogram", 60.0, 0.002, 5000.0, 50.0
        )
        return float(call(
            cepstrogram, "Get CPPS", True, 0.01, 0.001, 60.0, 330.0,
            0.05, "Parabolic", 0.001, 0.05, "Straight", "Robust",
        ))
    except Exception:  # Praat can reject short, quiet or aperiodic regions
        return None


def _add_connected_cpps(summary, samples, sample_rate, audio_quality):
    quality_failure, quality_warnings = _quality_state(
        audio_quality, ("pitch", "voice_quality")
    )
    if quality_failure:
        summary["availability"]["cpps_db"] = _availability(
            "unavailable", "audio_quality_failure", "unavailable",
            quality_warnings,
        )
        return
    eligible = [region for region in summary["regions"]
                if region["duration_s"] >= 1.0]
    results = []
    for region in eligible:
        sound = _sound_from_range(
            samples, sample_rate, region["start_s"], region["end_s"]
        )
        value = _cpps(sound) if sound is not None else None
        if value is not None:
            results.append((value, region["duration_s"], region["region_id"]))
    total_s = sum(duration for _, duration, _ in results)
    if total_s < MIN_CPPS_TOTAL_S:
        summary["availability"]["cpps_db"] = _availability(
            "unavailable", "insufficient_continuous_speech_for_cpps",
            "unavailable",
        )
        return
    summary["values"]["cpps_db"] = _round(
        sum(value * duration for value, duration, _ in results) / total_s, 3
    )
    summary["availability"]["cpps_db"] = _availability(
        "available", None, "low" if quality_warnings else "moderate",
        quality_warnings + [{
            "code": "research_only",
            "reason": "CPPS has no released interpretation in item 20, clinical or otherwise.",
        }]
    )
    summary["research_trials"] = [{
        "region_id": region_id,
        "analysed_s": _round(duration, 3),
        "cpps_db": _round(value, 3),
    } for value, duration, region_id in results]


def _vowel_trial_ranges(vad, speaker_regions):
    result = []
    for chunk in (vad or {}).get("speech_chunks", []):
        try:
            start = float(chunk.get("start", chunk.get("start_s")))
            end = float(chunk.get("end", chunk.get("end_s")))
        except (TypeError, ValueError):
            continue
        if end - start < 3.0:
            continue
        midpoint = (start + end) / 2.0
        trial_start = midpoint - VOWEL_MIDDLE_S / 2.0
        trial_end = midpoint + VOWEL_MIDDLE_S / 2.0
        if not any(region["start_s"] <= trial_start
                   and trial_end <= region["end_s"]
                   for region in speaker_regions):
            continue
        result.append((trial_start, trial_end, start, end))
    return result


def _perturbation(sound):
    try:
        broad = sound.to_pitch_cc(
            pitch_floor=PITCH_FLOOR_HZ, pitch_ceiling=PITCH_CEILING_HZ
        )
        voiced = broad.selected_array["frequency"]
        voiced = voiced[voiced > 0]
        if not len(voiced):
            return None
        median = float(np.median(voiced))
        floor = max(40.0, median / 2.5)
        ceiling = min(1000.0, median * 2.5)
        point = call(sound, "To PointProcess (periodic, cc)", floor, ceiling)
        jitter = call(point, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3)
        shimmer = call(
            [sound, point], "Get shimmer (local)", 0, 0, 0.0001,
            0.02, 1.3, 1.6,
        )
        pulses = int(call(point, "Get number of points"))
        if not (math.isfinite(jitter) and math.isfinite(shimmer)):
            return None
        return {
            "f0_median_hz": _round(median, 2),
            "pitch_floor_hz": _round(floor, 2),
            "pitch_ceiling_hz": _round(ceiling, 2),
            "valid_pulse_count": pulses,
            "jitter_local_pct": _round(100.0 * jitter, 4),
            "shimmer_local_pct": _round(100.0 * shimmer, 4),
            "cpps_db": _round(_cpps(sound), 3),
        }
    except Exception:
        return None


def _add_vowel_research(summary, samples, sample_rate, vad, context,
                        audio_quality):
    if not context["research_consent_granted"]:
        for name in ("cpps_db", "jitter_local_pct", "shimmer_local_pct"):
            summary["availability"][name] = _availability(
                "unavailable", "research_consent_not_granted", "unavailable"
            )
        return
    quality_failure, quality_warnings = _quality_state(
        audio_quality, ("pitch", "voice_quality", "loudness")
    )
    if quality_failure:
        for name in ("cpps_db", "jitter_local_pct", "shimmer_local_pct"):
            summary["availability"][name] = _availability(
                "unavailable", "audio_quality_failure", "unavailable",
                quality_warnings,
            )
        return
    trial_ranges = _vowel_trial_ranges(vad, summary["regions"])
    trials = []
    for trial_start, trial_end, source_start, source_end in trial_ranges:
        sound = _sound_from_range(
            samples, sample_rate, trial_start, trial_end
        )
        result = _perturbation(sound) if sound is not None else None
        trials.append({
            "source_start_s": _round(source_start, 3),
            "source_end_s": _round(source_end, 3),
            "analysed_start_s": _round(trial_start, 3),
            "analysed_end_s": _round(trial_end, 3),
            "status": "valid" if result else "algorithm_failed",
            "values": result,
        })
    valid = [trial["values"] for trial in trials if trial["values"]]
    summary["research_trials"] = trials
    if len(valid) < MIN_VOWEL_REPETITIONS:
        for name in ("cpps_db", "jitter_local_pct", "shimmer_local_pct"):
            summary["availability"][name] = _availability(
                "unavailable", "fewer_than_three_valid_vowel_repetitions",
                "unavailable",
            )
        return
    selected = valid[:MIN_VOWEL_REPETITIONS]
    for name in ("cpps_db", "jitter_local_pct", "shimmer_local_pct"):
        values = [item[name] for item in selected if item.get(name) is not None]
        if len(values) != MIN_VOWEL_REPETITIONS:
            summary["availability"][name] = _availability(
                "unavailable", "algorithm_failed", "unavailable"
            )
            continue
        summary["values"][name] = _round(float(np.mean(values)), 4)
        summary["availability"][name] = _availability(
            "available", None,
            "low" if quality_warnings else "moderate",
            quality_warnings + [{
                "code": "research_only",
                "reason": "This value cannot support interpretation, progress or diagnosis.",
            }]
        )


def extract_voice_prosody(samples, sample_rate, diarization, vad, context,
                          audio_quality, recording_type, input_audio):
    """Return the complete additive primitive artifact section."""
    samples = np.asarray(samples, dtype=np.float64).reshape(-1)
    duration_s = len(samples) / float(sample_rate)
    regions = _regions(diarization, duration_s)
    frames, pitch_ranges = _pitch_frames(samples, sample_rate, regions)
    speakers = sorted({region["speaker"] for region in regions})
    summaries = {
        speaker: _speaker_summary(
            speaker, frames, regions, context, audio_quality
        ) for speaker in speakers
    }
    for summary in summaries.values():
        if context["task_profile"] == "fixed_reading":
            _add_connected_cpps(
                summary, samples, sample_rate, audio_quality
            )
        elif context["task_profile"] == "sustained_vowel_research":
            _add_vowel_research(
                summary, samples, sample_rate, vad, context, audio_quality
            )
    unattributed = sum(frame["speaker"] is None for frame in frames)
    overlap = sum("overlap" in frame["quality_flags"] for frame in frames)
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "algorithm_version": ALGORITHM_VERSION,
        "analysis_context": context,
        "input_audio": dict(input_audio or {}),
        "analysis_derivative": {
            "sample_rate_hz": sample_rate,
            "channels": 1,
            "sample_format": "float64_normalized",
            "duration_s": _round(duration_s, 3),
            "decoded_from_original": True,
            "decoding_does_not_restore_lossy_information": True,
        },
        "configuration": {
            "frame_step_s": FRAME_STEP_S,
            "level_window_s": LEVEL_WINDOW_S,
            "pitch_method": "praat_raw_autocorrelation_two_pass_adaptive",
            "pitch_floor_hz": PITCH_FLOOR_HZ,
            "pitch_ceiling_hz": PITCH_CEILING_HZ,
            "adaptive_pitch_ratio": ADAPTIVE_PITCH_RATIO,
            "pitch_ranges_by_speaker": pitch_ranges,
            "voicing_threshold": VOICING_THRESHOLD,
            "silence_threshold": SILENCE_THRESHOLD,
            "pitch_strength_is_calibrated_probability": False,
            "pitch_region_edge_margin_s": PITCH_REGION_EDGE_MARGIN_S,
            "recorder_level_method": "rms_dbfs",
            "recorder_level_is_sound_pressure_level": False,
            "original_timestamps_preserved": True,
            "cycle_metrics_cross_region_boundaries": False,
        },
        "recording_type": recording_type,
        "frame_count": len(frames),
        "unattributed_frame_count": unattributed,
        "overlap_excluded_frame_count": overlap,
        "frames": frames,
        "speakers": summaries,
        "whole_recording_person_level_use": (
            "unavailable_blended_speakers"
            if recording_type == "conversation" else
            "not_exposed_use_per_speaker_summary"
        ),
        "release_limits": {
            "released_interpretation": "blocked_pending_separate_validation",
            "personal_progress": "blocked",
            "cross_device_progress": "blocked",
            "combined_index": "blocked",
            "ranking": "blocked",
            "screening": "blocked",
            "diagnosis": "blocked",
        },
    }
